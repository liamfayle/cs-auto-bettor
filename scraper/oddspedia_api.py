from bo3_gg_api import fetch_json_from_url
from constants import ODDS_HEADERS
import pandas as pd
from tqdm import tqdm


def parse_match_date(date: str) -> None:
    #date expects yyyy-mm-dd format

    all_match_data = []

    page = 1
    total_pages = 2

    while page < total_pages:
        url = f"https://oddspedia.com/api/v1/getMatchList?excludeSpecialStatus=0&sortBy=date&perPageDefault=50&startDate={date}T00:00:00Z&endDate={date}T23:59:59Z&geoCode=CA&status=all&sport=counter-strike-global-offensive&popularLeaguesOnly=0&r=wv&page={page}&perPage=50&language=ca"
        json = fetch_json_from_url(url, headers=ODDS_HEADERS)['data']
        total_pages = json['total_pages']

        #parse_odds
        matches = json['matchList']

        for match in matches:
            match_data = parse_match(match)
            parse_moneyline_odds(match_data)
            all_match_data.append(match_data)
        
        page += 1

    return all_match_data


def parse_match(match: dict) -> None:
    data = {}

    data['id'] = match.get("id")

    data['date'] = match.get("md") #match date
    data['home'] = match.get('ht') #home team
    data['away'] = match.get('at') #away team

    data['home_moneyline_open'] = None
    data['home_moneyline_close'] = None

    data['away_moneyline_open'] = None
    data['away_moneyline_close'] = None

    data['hold_open'] = None
    data['hold_close'] = None

    return data


def parse_moneyline_odds(match_data):
    url = f"https://oddspedia.com/api/v1/getOddsMovements?ot=201&matchId={match_data['id']}&inplay=0&wettsteuer=0"
    json = fetch_json_from_url(url, headers=ODDS_HEADERS)['data']

    if len(json) == 0:
        return

    if json.get('error') == "#NOFTM":
        return

    match_data['home_moneyline_open'] = float(json.get('1', {}).get('average', {}).get('moves', [])[0]['y'])
    match_data['home_moneyline_close'] = float(json.get('1', {}).get('average', {}).get('moves', [])[-1]['y'])

    match_data['away_moneyline_open'] = float(json.get('2', {}).get('average', {}).get('moves', [])[0]['y'])
    match_data['away_moneyline_close'] = float(json.get('2', {}).get('average', {}).get('moves', [])[-1]['y'])

    match_data['hold_open'] = (1 / match_data['home_moneyline_open']) + (1 / match_data['away_moneyline_open']) - 1.0
    match_data['hold_close'] = (1 / match_data['home_moneyline_close']) + (1 / match_data['away_moneyline_close']) - 1.0


def parse_odds_date_range(date_range):
    # Accepts list of dates in format yyyy-mm-dd
    odds_df = None

    # Wrap date_range with tqdm to display a progress bar
    for date in tqdm(date_range, desc='Processing dates'):
        date_data_dict = parse_match_date(date)  # Assuming this returns a list of dictionaries

        # Convert the list of dictionaries to a DataFrame
        date_df = pd.DataFrame(date_data_dict)

        # If odds_df is None, it means it's the first iteration, so assign date_df to odds_df
        if odds_df is None:
            odds_df = date_df
        else:
            # Otherwise, concatenate the new DataFrame to the existing odds_df
            odds_df = pd.concat([odds_df, date_df], ignore_index=True)

    # Return the concatenated DataFrame
    return odds_df


def generate_date_range(input_path, date_column_name):
    #takes a df from datasets folder generated for ml building and extracts unique dates
    date_df = pd.read_csv(input_path)

    unique_dates = date_df[date_column_name].dropna().unique()

    # Parse the unique date strings to datetime objects and then format them as strings 'yyyy-mm-dd'
    unique_dates_formatted = sorted(list(set(pd.to_datetime(unique_dates).date.astype(str))))

    return unique_dates_formatted




if __name__ == "__main__":
    dates = generate_date_range("datasets/games.csv", "begin_at")
    odds_df = parse_odds_date_range(dates)
    odds_df.to_csv("datasets/odds.csv")



'''see network json for https://oddspedia.com/ca/counter-strike-global-offensive

It has odds for match winner, handicap, and map over/under

#TODO
https://oddspedia.com/api/v1/getMatchList?excludeSpecialStatus=0&sortBy=date&perPageDefault=50&startDate=2023-10-27T00:00:00Z&endDate=2023-10-27T23:59:59Z&geoCode=CA&status=all&sport=counter-strike-global-offensive&popularLeaguesOnly=0&r=wv&page=1&perPage=50&language=ca
https://oddspedia.com/api/v1/getMatchOdds?wettsteuer=0&geoCode=CA&bookmakerGeoCode=CA&bookmakerGeoState=&matchId=8147156&language=en
https://oddspedia.com/api/v1/getOddsMovements?ot=201&matchId=8147156&inplay=0&wettsteuer=0&geoCode=CA&geoState=&language=en

https://oddspedia.com/api/v1/getMatchOdds?wettsteuer=0&geoCode=CA&bookmakerGeoCode=CA&bookmakerGeoState=&matchId=8116421&language=en
'''