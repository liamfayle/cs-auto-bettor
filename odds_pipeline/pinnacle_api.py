from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from selenium import webdriver
from bs4 import BeautifulSoup, NavigableString
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from scraper.bo3_gg_api import fetch_json_from_url, parse_match_betting_json
from models.models import *
from thefuzz import fuzz
from datetime import datetime, timedelta
from sqlalchemy import func
import unicodedata
from scraper.constants import PINNY_PASS, PINNY_USERNAME, TWOCAPTCHA_API_KEY
import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent
import requests
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import traceback
from typing import Tuple, Union, List, Dict
from odds_pipeline.log import log, LEVEL_ERROR, LEVEL_WARNING

CAPTCHA_SITE_KEY = "6LdQsj0UAAAAAAuxOxGkO5EZdZIQDk_b8d6gK8e0"


class PinnyAPI():
    """A web scraping class to interact with the Pinnacle website and fetch esports betting lines."""

    def __init__(self):
        self.driver_live_since = None
        self.driver = None
        self.current_url = None


    def create_driver(self, headless=True):
        """Creates a new instance of the Chrome web driver with specified options."""
        if self.driver is not None:
            self.kill_driver()
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode

        # Use a fake user agent
        ua = UserAgent()
        user_agent = ua.random
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")  # Suppress logs
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Set up driver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver_live_since = datetime.now()


    def load_url(self):
        try:
            url = 'https://www.pinnacle.ca/en/esports-hub/cs2'
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.flex-column'))
            )
            self.current_url = url
        except Exception as e:
            log(f"Failed to load url PinnyAPI @load_url: {e}", LEVEL_WARNING)
            self.url = None
            return False
        return True


    refresh = load_url


    def kill_driver(self):
        """Quits the driver and sets the instance to None."""
        self.driver.quit()
        self.driver = None
        self.driver_live_since = None
        self.current_url = None


    def execute_captcha_callback(self, code):
        #self.driver.execute_script(f"___grecaptcha_cfg.clients[0].L.L.callback('{captcha_code}');")
        js_code = f"""
            var findTargetBranch = function(obj, siteKey) {{
                for (var key in obj) {{
                    if (obj.hasOwnProperty(key)) {{
                        var val = obj[key];
                        if (typeof val === 'object' && val !== null) {{
                            if ('sitekey' in val && val.sitekey === siteKey) {{
                                return val; // Return the branch if sitekey matches
                            }}
                            var found = findTargetBranch(val, siteKey);
                            if (found) return found; // Recursive search in child objects
                        }}
                    }}
                }}
                return null; // Return null if not found
            }};

            var target = findTargetBranch(___grecaptcha_cfg.clients[0], '{CAPTCHA_SITE_KEY}');
            target.callback('{code}');
            """

        self.driver.execute_script(js_code)


    def login(self):
        try:
            username_field = self.driver.find_element(By.ID, 'username')
            for char in PINNY_USERNAME:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            time.sleep(random.uniform(0.3, 0.8))
            password_field = self.driver.find_element(By.ID, 'password')
            for char in PINNY_PASS:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
            actions = ActionChains(self.driver)
            actions.move_to_element(login_button)
            time.sleep(random.uniform(0.4, 1))
            actions.click(login_button)
            actions.perform()

            WebDriverWait(self.driver, 30).until( #Wait for captcha modal
                EC.presence_of_element_located((By.CLASS_NAME, "modalContentContainer"))
            )

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[@title="reCAPTCHA"]'))
            )

            captcha_code = solve_captcha()
            if captcha_code is None:
                return False

            self.driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_code}';")
            self.execute_captcha_callback(captcha_code)

            button = self.driver.find_element(By.XPATH, '//button[@data-test-id="Button"][.//span[text()="Log in"]]')
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", button)

            WebDriverWait(self.driver, 60).until( #Wait for login
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="QuickCashier-BankRoll"]'))
            )

            time.sleep(5) #Ensure logged in session

            return True
        except Exception as e:
            #traceback.print_exc()
            log(f"An error occurred in PinnyAPI @login: {e}", LEVEL_WARNING)
            return False


    def get_lines_html(self):
        """Navigates to the Pinnacle esports page and returns the HTML content of betting lines."""
        try:
            html_content = BeautifulSoup(self.driver.page_source, 'html.parser')
            to_return = html_content.find_all('div', class_="flex-column")

            return to_return
        except Exception as e:
            log(f"An error occurred in PinnyAPI @get_lines_html: {e}", LEVEL_WARNING)
            return None


    def is_logged_in(self):
        try:
            WebDriverWait(self.driver, 15).until( #Wait for login
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="QuickCashier-BankRoll"]'))
            )
            return True
        except:
            return False
            
    
    def get_available_balance(self):
        try:
            bank = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="QuickCashier-BankRoll"]'))
            )
            currency = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, ".//span[contains(text(), 'CAD')]"))
            )
            currency_text = currency.text.strip()
            currency_value = currency_text.replace("CAD", "").replace("\xa0", "").replace(",", "").strip()
            return float(currency_value)
        except Exception as e:
            print("Exception occurred:", e)  # Print the exception for debugging
            return 0


    def get_line(self, away_search, home_search, event_search): #this cannot distinguish if there are  identical lines at different times (account for somewhere)
        try:
            bet_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.flex-column")
            for card in bet_cards:
                child_elements = card.find_elements(By.XPATH, ".//*[not(*)]")
                text = []
                for child in child_elements:
                    if child.text:
                        text.append(child.text)
                event = away = home = None
                if len(text) == 8: #No draw
                    event, _, away, _, _, home, _, _ = text
                elif len(text) == 9: #draw
                    event, _, away, _, _, _, home, _, _ = text
                if event == event_search and away == away_search and home == home_search:
                    return card
        except Exception as e:
            #traceback.print_exc()
            log(f"An error occurred in PinnyAPI @get_line: {e}", LEVEL_ERROR)
            return None
        

    def clear_bet_slip(self):
        try:
            self.driver.find_element(By.CSS_SELECTOR, '[data-test-id="Betslip-RemoveAllButton"]').click()
            self.driver.find_element(By.CSS_SELECTOR, '[data-test-id="Betslip-RemoveAllModal-ConfirmButton"]').click()
        except:
            pass


    def bet_line(self, line_card, bet_side, bet_team, bet_odds, bet_amount: float):
        try:
            money_line_divs = self.get_money_line_divs(line_card)
            selected_div = self.select_bet_div(money_line_divs, bet_side)
            team, odds = self.get_team_and_odds(selected_div)

            if float(odds) != float(bet_odds):
                log("Odds did not match for bet.", LEVEL_WARNING)
                return -1

            if team != bet_team and bet_side != "draw":
                log("Team names did not match for bet", LEVEL_WARNING)
                return -2

            bet_amount = self.place_bet(selected_div, bet_amount)

            return self.confirm_bet(bet_amount)
        except Exception as e:
            #traceback.print_exc()
            log(f"An error occurred in PinnyAPI @bet_line: {e}", LEVEL_ERROR)
            return 0


    def get_money_line_divs(self, line_card):
        divs = line_card.find_elements(By.CSS_SELECTOR, "div[aria-label*='Money Line']")
        if len(divs) not in [2, 3]:
            raise ValueError("Unexpected number of money line divs found")
        return divs


    def select_bet_div(self, divs, bet_side):
        bet_side_index = {"away": 0, "draw": 1, "home": -1}.get(bet_side)
        if bet_side_index is None:
            raise ValueError(f"Invalid bet side: {bet_side}")
        return divs[bet_side_index]


    def get_team_and_odds(self, div):
        child_elements = div.find_elements(By.XPATH, ".//*[not(*)]")
        text_elements = [child.text for child in child_elements if child.text]
        if len(text_elements) != 2:
            raise ValueError("Could not find team and odds in the div")
        return text_elements


    def place_bet(self, div, bet_amount):
        button = div.find_element(By.TAG_NAME, 'button')
        self.driver.execute_script("arguments[0].click();", button)
        max_wager_element = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="Betslip-StakeWinInput-MaxWagerLimit"]'))
        )
        max_wager = float(max_wager_element.text.replace(" ", "").replace("CAD", ""))
        bet_amount = min(float(bet_amount), max_wager)
        available_balance = self.get_available_balance()
        bet_amount = min(float(bet_amount), float(available_balance))
        stake_element = self.driver.find_element(By.CSS_SELECTOR, "[placeholder='Stake']")
        stake_element.send_keys(bet_amount)
        return bet_amount


    def confirm_bet(self, bet_amount):
        button = self.driver.find_element(By.CSS_SELECTOR, '[data-test-id="Betslip-ConfirmBetButton"]')
        if button.is_displayed() and button.is_enabled():
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".card-warning")
                log("Odds changed before bet was placed.", LEVEL_WARNING)
                return -4  # Odds changed
            except NoSuchElementException: #no warning presented
                button.click()
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "header.betslip-bet-accepted"))
                )
                return bet_amount
        log("Bet button was not clickable.", LEVEL_WARNING)
        return -3  # Bet button not clickable


def solve_captcha(num_retry: int = 30) -> str:
    """
    Attempts to solve a captcha using the 2Captcha service.

    The function sends a captcha request to the 2Captcha service and then polls for the solution.
    If the captcha is successfully solved, it returns the solution. Otherwise, it indicates failure or returns None after exhausting retries.

    Example:
    1. To solve a captcha with a default of 30 retries, simply call the function without arguments:
       Example usage: solve_captcha()

    2. To solve a captcha with a custom number of retries, for instance, 10 retries:
       Example usage: solve_captcha(num_retry=10)

    :param num_retry: Number of times to retry polling for the captcha solution. Default is 30 retries.
    :return: The solved captcha response as a string, a failure message, or None if retries are exhausted.
    """
    # Sending the captcha for solving
    response = requests.post(f'http://2captcha.com/in.php?key={TWOCAPTCHA_API_KEY}&method=userrecaptcha&googlekey={CAPTCHA_SITE_KEY}&pageurl={"https://www.pinnacle.ca/en/esports-hub/cs2"}&invisible=1')
    log(f"Sending captcha request: {response.text}")
    if response.text[0:2] != 'OK':
        return 'Failed to send captcha for solving'
    captcha_id = response.text[3:]

    time.sleep(20)  # Initial wait for average poll time

    # Polling for the captcha solution
    for i in range(num_retry):
        time.sleep(5)  # Wait for 5 seconds before each retry
        result = requests.get(f'http://2captcha.com/res.php?key={TWOCAPTCHA_API_KEY}&action=get&id={captcha_id}')
        log(f"Polling captcha result: {result.text}")
        if result.text[0:2] == 'OK':
            return result.text[3:]
    
    return None


def find_all_text_in_children(element) -> list:
    """
    Recursively extracts all text content from a BeautifulSoup element and its children.

    This function navigates through a BeautifulSoup element and its child elements to extract all text content,
    returning it as a list of strings. Each string in the list corresponds to the text from an individual element
    or NavigableString within the original element.

    Examples:
    1. To extract text from an entire HTML document parsed by BeautifulSoup:
       Example usage: text_list = find_all_text_in_children(soup)
       Here, 'soup' is a BeautifulSoup object created from an entire HTML document.

    2. To extract text from a specific tag or element within a BeautifulSoup-parsed HTML document:
       Example usage: text_list = find_all_text_in_children(soup.find('div', {'class': 'example'}))
       Here, the function extracts text from a specific 'div' element with class 'example'.

    :param element: A BeautifulSoup element from which to extract text.
    :return: A list of strings, each containing the text of a child element or NavigableString.
    """
    text_content = []

    # Check if the element is a NavigableString and, if so, add its text to the list.
    if isinstance(element, NavigableString):
        text_content.append(element.strip())
    else:
        # Recursively call the function on each child element.
        for child in element.children:
            text_content.extend(find_all_text_in_children(child))

    return text_content


def parse_lines(lines_html: List) -> List[Dict[str, Union[str, bool]]]:
    """
    Parses a list of HTML elements to extract betting line data.

    :param lines_html: A list of BeautifulSoup Tag objects, each representing a row of betting line data.
    :return: A list of dictionaries, where each dictionary contains data about a betting line, including event name, date, URLs for all lines, team names, line values, and a flag indicating if lines are swapped.

    Each dictionary in the returned list has the following keys:
        - 'event_name': Name of the event.
        - 'date': Date and time of the event, formatted as a string in ISO 8601 format.
        - 'all_lines': URL string pointing to all lines for the event.
        - 'away_team_name': Name of the away team.
        - 'away_line': Betting line for the away team.
        - 'home_team_name': Name of the home team.
        - 'home_line': Betting line for the home team.
        - 'draw_line': Betting line for a draw (if applicable).
        - 'swapped': Boolean flag indicating whether the lines are swapped (always False in the current implementation).
    """

    lines_data = []

    for line in lines_html:
        rows = line.contents  # Get children of the line element
        # Skip the row if it doesn't have exactly 2 elements (ie its a map bet)
        if rows is None or len(rows) != 2:
            continue

        event, date = find_all_text_in_children(rows[0])  # Extract event and date information

        formatted_date_time = "Live"
        if date != "Live":
            # Parse and adjust the date and time
            date_time_obj = None
            try:
                date_time_obj = datetime.strptime(date, "%m/%d/%Y - %H:%M")
                adjusted_date_time = date_time_obj + timedelta(hours=5)
            except:
                pass
            if date_time_obj is None:
                try:
                    date_time_obj = datetime.strptime(date, "%Y/%m/%d - %H:%M")
                    adjusted_date_time = date_time_obj + timedelta(hours=3)
                except:
                    pass
            
            formatted_date_time = adjusted_date_time.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
        
        odds_data = find_all_text_in_children(rows[1])  # Extract odds data
        all_lines = rows[1].find('a', href=True)  # Find the hyperlink for all lines

        # Process the odds data based on its length
        if len(odds_data) == 6:
            # Standard match with no draw line
            away_team, away_line, _, home_team, home_line, _ = odds_data
            lines_data.append(
                {
                    'event_name': event,
                    'date': formatted_date_time,
                    'all_lines': 'https://www.pinnacle.com/' + all_lines['href'],
                    'away_team_name': away_team,
                    'away_line': away_line,
                    'home_team_name': home_team,
                    'home_line': home_line,
                    'draw_line': None,
                    'swapped': False,
                }
            )
        
        elif len(odds_data) == 7:
            # Match with a draw line
            away_team, away_line, _, draw_line, home_team, home_line, _ = odds_data
            lines_data.append(
                {
                    'event_name': event,
                    'date': formatted_date_time,
                    'all_lines': 'https://www.pinnacle.com/' + all_lines['href'],
                    'away_team_name': away_team,
                    'away_line': away_line,
                    'home_team_name': home_team,
                    'home_line': home_line,
                    'draw_line': draw_line,
                    'swapped': False,
                }
            )

    return lines_data


def create_acronym(phrase: str) -> str:
    """
    Creates an acronym from the given phrase.

    :param phrase: A string representing a phrase from which the acronym will be created.
    :return: A string representing the acronym. If the phrase contains only one word, the word itself is returned in lowercase. 
             Otherwise, the acronym is formed by concatenating the first letters of each word in the phrase, converted to lowercase.

    Example:
    create_acronym("National Aeronautics and Space Administration") will return "naasa".
    """

    # Split the phrase into individual words
    words = phrase.split()

    # If the phrase consists of only one word, return that word in lowercase
    if len(words) == 1:
        return words[0].lower()

    # If the phrase has multiple words, create an acronym
    else:
        # Concatenate the first letter of each word and convert to lowercase
        acronym = ''.join(word[0] for word in words).lower()

    return acronym


def normalize_event(name: str) -> str:
    """
    Normalizes an event name by removing accented characters, converting to lowercase, 
    excluding non-alphanumeric characters (except spaces), and removing specific words.

    :param name: A string representing the original event name.
    :return: A normalized string of the event name.

    The function performs the following steps:
    1. Converts accented characters to their closest ASCII representation.
    2. Converts the name to lowercase.
    3. Removes any characters that are not letters or spaces.
    4. Splits the name into words and removes specific unwanted words (e.g., 'season', 'fall').
    5. Reconstructs and returns the modified name as a single string.

    Example:
    normalize_event("Summer CS2 Open") will return "cs".
    """

    # Normalize the accented characters to their closest ASCII representation
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    # Convert the name to lowercase
    name = name.lower()
    # Remove any characters that are not letters or spaces
    name = ''.join(e for e in name if e.isalpha() or e.isspace())

    # Split the name into words for further processing
    words = name.split()
    # Define words to be removed from the names
    words_to_remove = ['season', 'fall', 'spring', 'winter', 'summer', 'cs2', 'cs', 'open', 'closed', 'qualifier']
    # Remove the specified words and reconstruct the name
    name = ' '.join(word for word in words if word.lower() not in words_to_remove)

    return name


def normalize_name(name: str) -> str:
    """
    Normalizes a name by removing accented characters, converting to lowercase, 
    excluding non-alphanumeric characters (except spaces), and removing specific words.

    :param name: A string representing the original name to be normalized.
    :return: A normalized string of the name.

    The function performs the following operations:
    1. Converts accented characters to their closest ASCII representation.
    2. Converts the name to lowercase.
    3. Removes any characters that are not letters, numbers, or spaces.
    4. Splits the name into words and removes specific unwanted words (e.g., 'team', 'esports').
    5. Reconstructs and returns the modified name as a single string.

    Example:
    normalize_name("Team Liquid eSports") will return "liquid".
    """
    if name == "BB Team":
        name = "BetBoom"

    # Normalize accented characters to their ASCII equivalents
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    # Convert the name to lowercase
    name = name.lower()
    # Remove any characters that are not alphanumeric or spaces
    name = ''.join(e for e in name if e.isalnum() or e.isspace())

    # Split the name into words for further processing
    words = name.split()
    # Define words to be removed from the names
    words_to_remove = ['team', 'esports', 'gaming', 'esport', 'fe', 'female', 'club']
    # Remove the specified words and reconstruct the name
    name = ' '.join(word for word in words if word.lower() not in words_to_remove)

    return name


# Fuzzy match function
def is_fuzzy_match(name1, name2, threshold=90, type='name'):
    if type=='name':
        if fuzz.partial_ratio(normalize_name(name1), normalize_name(name2)) >= threshold:
            return True
        return fuzz.partial_ratio(normalize_name(create_acronym(name1)), normalize_name(create_acronym(name2))) >= threshold
    if fuzz.partial_ratio(normalize_event(name1), normalize_event(name2)) >= threshold:
            return True
    return fuzz.ratio(normalize_event(create_acronym(name1)), normalize_event(create_acronym(name2))) >= threshold

# Time comparison function with a tolerance
def is_time_match(time1, time2, tolerance_minutes=90):
    time_format = "%Y-%m-%dT%H:%M:%S.000+00:00"
    datetime1 = datetime.strptime(time1, time_format)
    datetime2 = datetime.strptime(time2, time_format)
    return abs(datetime1 - datetime2) <= timedelta(minutes=tolerance_minutes)

# Check if matches are the same
def is_same_match(match1, match2):
    team1_match = is_fuzzy_match(match1['away_team_name'], match2['away_team_name'], threshold=80)
    team2_match = is_fuzzy_match(match1['home_team_name'], match2['home_team_name'], threshold=80)
    tournament_match = is_fuzzy_match(match1['event_name'], match2['event_name'], threshold=80, type='event')
    time_match = is_time_match(match1['date'], match2['date'])
    
    if team1_match and team2_match and tournament_match and time_match:
        return True

    #Handle away / home being swapped
    team1_match = is_fuzzy_match(match1['away_team_name'], match2['home_team_name'], threshold=80)
    team2_match = is_fuzzy_match(match1['home_team_name'], match2['away_team_name'], threshold=80)

    if team1_match and team2_match and tournament_match and time_match:
        match2['swapped'] = True
        return True

# Function to determine if one datetime is at least 10 hours past another
def is_date_n_hours_past(date1, date2, n=10):
    # Convert both dates into datetime objects
    datetime1 = datetime.strptime(date1, "%Y-%m-%dT%H:%M:%S.000+00:00")
    datetime2 = datetime.strptime(date2, "%Y-%m-%dT%H:%M:%S.000+00:00")

    # Check if date1 is at least 10 hours past date2
    return (datetime2 - datetime1) >= timedelta(hours=n)

# Function to determine if one datetime is at least 10 hours past another
def is_date_n_hours_before(date1, date2, n=10):
    # Convert both dates into datetime objects
    datetime1 = datetime.strptime(date1, "%Y-%m-%dT%H:%M:%S.000+00:00")
    datetime2 = datetime.strptime(date2, "%Y-%m-%dT%H:%M:%S.000+00:00")

    # Check if date1 is at least 10 hours past date2
    return (datetime1 - datetime2) >= timedelta(hours=n)


def match_line(line_dict, debug=False):
    page = 1
    num_pages = 2
    limit = 50
    offset = 0

    while num_pages > page:
        json_data = fetch_json_from_url(f"https://api.bo3.gg/api/v1/matches?page[offset]={offset}&page[limit]={limit}&sort=start_date&filter[matches.status][in]=upcoming&with=teams,tournament,tournament_deep")
        num_pages = json_data['total']['pages']

        for match in json_data['results']:
            match_data = parse_match_betting_json(match)

            if match_data['away_team_name'] is None or match_data['home_team_name'] is None or match_data['date'] is None or match_data['event_name'] is None:
                continue

            if is_date_n_hours_before(line_dict['date'], match_data['date'], n=1.1): #Change in accordance with my time tolerance on games (ie above i wrap time matching in 60 min on each side window)
                continue

            #Check if i definelty have missed it
            if is_date_n_hours_past(line_dict['date'], match_data['date'], n=1.1):
                if debug:
                    print(f"Failed to find match for game: \n {line_dict['away_team_name']}  {line_dict['home_team_name']}  {line_dict['date']}  {line_dict['event_name']}")
                    print() 
                return False

            if is_same_match(match_data, line_dict):
                if debug:
                    print("MATCHED:")
                    print(f"{match_data['away_team_name']}  {match_data['home_team_name']}  {match_data['date']}  {match_data['event_name']}")
                    print(f"{line_dict['away_team_name']}  {line_dict['home_team_name']}  {line_dict['date']}  {line_dict['event_name']}")
                    print(line_dict['swapped'])
                    print()
                line_dict['match_id'] = match_data['id']
                line_dict['match_slug'] = match_data['slug']
                line_dict['away_team_id'] = match_data['away_team_id']
                line_dict['home_team_id'] = match_data['home_team_id']
                line_dict['bo_type'] = match_data['bo_type']
                line_dict['tier'] = match_data['tier']

                if line_dict['swapped']:
                    temp_away = line_dict['away_team_name']
                    line_dict['away_team_name'] = line_dict['home_team_name']
                    line_dict['home_team_name'] = temp_away

                    temp_away = line_dict['away_line']
                    line_dict['away_line'] = line_dict['home_line']
                    line_dict['home_line'] = temp_away

                return True

        page += 1
        offset += limit


def get_line_info(pinny_api, debug=False):
    lines_html = pinny_api.get_lines_html()
    lines = [line for line in parse_lines(lines_html) if line['date'] != "Live"]

    # Filter lines to only include matched ones
    lines = [line for line in lines if match_line(line, debug=debug)]

    session = Session()

    for line in lines:
        if line['draw_line'] is None:
            hold=(1/float(line['away_line']) + 1/float(line['home_line']) - 1) if float(line['home_line']) > 0 and float(line['away_line']) > 0 else None
        else:
            hold=(1/float(line['away_line']) + 1/float(line['home_line']) + 1/float(line['draw_line']) - 1) if float(line['home_line']) > 0 and float(line['away_line']) > 0 and float(line['draw_line']) > 0 else None

        line['hold'] = hold

         # Create a PinnacleMoneylines instance
        pinny_line = PinnacleMoneylines(
            home_team=line['home_team_name'],
            home_team_id=line['home_team_id'],
            away_team=line['away_team_name'],
            away_team_id=line['away_team_id'],
            match_id=line['match_id'],
            date=datetime.now(),  # Ensure this is a datetime object or formatted correctly
            away_line=line['away_line'],
            home_line=line['home_line'],
            draw_line=line['draw_line'],  # Assuming 'draw_line' might be in line_dict and optional
            hold=hold,
            bo_type=line['bo_type'],
            tier=line['tier'],
            swapped=line['swapped']
        )

        session.add(pinny_line)
    
    session.commit()
    session.close()

    return lines



if __name__ == "__main__":
    #get_line_info(debug=True)
    '''pinny_api = PinnyAPI()
    pinny_api.create_driver(headless=False)
    pinny_api.load_url()
    pinny_api.login()
    pinny_api.refresh()
    print(pinny_api.is_logged_in())
    print(pinny_api.get_available_balance())
    
    answer = "n"
    while answer != "y":
        answer = input("'y' to quit': ")

    pinny_api.kill_driver()'''