from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)


from models.models import *
from odds_pipeline.pinnacle_api import get_line_info
from resources import feature_moments
import pandas as pd
import re
import numpy as np
import requests
from bs4 import BeautifulSoup
from bo3_stats.glicko import glicko2_win_prob
import pickle
from math import comb
from scipy.stats import binom
from sqlalchemy import desc, or_
from datetime import datetime
from typing import Union, Tuple


FEATURES = [
    "A_glicko_win_prob", 
    "percent_diff_inf_rwpr",
    "z_inf_kdr_CT",
    "z_inf_tdp",
    "percent_diff_inf_mis_T",
    "delta_inf_kpr",
    "ratio_inf_rwpr_CT",
    "z_inf_mis",
    "ratio_inf_dpr",
    "z_inf_kdr",
    "ratio_inf_mis_CT",
    "delta_30_dpr",
    "ratio_inf_spr",
    "OD_inf_mis",
    "DO_inf_mis",
    "ratio_30_spr",
    "z_inf_kast_CT",
    "ratio_inf_adr_CT",
    "z_inf_adr",
    "percent_diff_inf_tdp_CT",
    "delta_inf_kast",
    "z_inf_dpr_CT",
    "delta_inf_evspr",
    "z_inf_spr_CT",
    "delta_inf_kpr_CT",
    "percent_diff_inf_evspr_CT",
    "delta_inf_rwpr_T",
    "percent_diff_30_tdp",
    "delta_inf_evsos",
    "percent_diff_inf_spr_T",
    "z_25_tdp",
    "z_25_spr",
    "delta_30_rwpr",
    "OD_inf_rwpr",
    "percent_diff_20_spr",
    "z_inf_odwr",
    "delta_30_kdr",
]


def bayes_shrink(value: float, N: int, stat: str, module, A: int = 10) -> float:
    """
    Applies Bayesian shrinkage to adjust a value based on a prior and the number of observations.

    The function computes a weighted average of the given value and a prior. The prior is determined by
    a statistic (mean) associated with the given stat parameter. This approach is typically used in
    statistical models to adjust estimates towards a prior to prevent overfitting, especially with small sample sizes.

    :param value: The observed value to be adjusted. Typically a statistic like a mean.
    :param N: The number of observations or samples corresponding to the value.
    :param stat: The name of the statistic (e.g., 'batting') used to identify the correct prior from the module.
    :param module: A module or object that contains the prior statistics, accessed using getattr.
    :param A: The weight given to the prior. A higher value gives more weight to the prior, shrinking the value more towards the prior. Defaults to 10.
    :return: The adjusted value after applying Bayesian shrinkage.
    """
    prior = getattr(module, stat + "_mean")  # Fetch the prior mean from the module using the stat parameter.

    if N == 0:
        value = 0  # If there are no observations, reset the value to 0.

    return (A * prior + N * value) / (A + N)  # Compute the weighted average of the value and the prior.


def fetch_stats_for_player(player_slug: str, session) -> dict:
    """
    Fetches statistical data for a player identified by their slug.

    This function retrieves player-specific statistics from a database using SQLAlchemy. It first identifies
    the player's ID, then fetches their latest Glicko rating and deviation. It also gathers a range of 
    custom player statistics from games they have participated in.

    :param player_slug: Unique identifier (slug) for the player.
    :param session: SQLAlchemy session for database queries. The exact type depends on the SQLAlchemy setup.
    :return: A dictionary containing averaged statistics and Glicko rating information for the player.
    """
    # Retrieve the player ID from the Players table using the provided slug.
    player_id = session.query(Players)\
        .filter(Players.slug == player_slug)\
        .first()
    
    # Set player_id to the ID if found, else -1. (impossible id value)
    if player_id != None:
        player_id = player_id.id
    else:
        player_id = -1

    #get rating + rd
    latest_entry = session.query(PlayerGlicko)\
        .filter(PlayerGlicko.player_id == player_id)\
        .filter(PlayerGlicko.begin_at != None)\
        .order_by(PlayerGlicko.begin_at.desc())\
        .first()

    rating = 1500
    RD = 350
    if latest_entry:
        rating = latest_entry.rating_post
        RD = latest_entry.deviation_post

    #Get most recent stats from customplayerstats for player
    result = session.query(CustomPlayerStatsGame)\
        .join(Games, CustomPlayerStatsGame.game_id == Games.id)\
        .filter(CustomPlayerStatsGame.player_id == player_id)\
        .filter(Games.begin_at != None)\
        .with_entities(
            CustomPlayerStatsGame.num_rounds, 
            CustomPlayerStatsGame.rwpr, 
            CustomPlayerStatsGame.kdr_CT, 
            CustomPlayerStatsGame.tdp, 
            CustomPlayerStatsGame.mis_T, 
            CustomPlayerStatsGame.kpr, 
            CustomPlayerStatsGame.rwpr_CT, 
            CustomPlayerStatsGame.mis, 
            CustomPlayerStatsGame.dpr, 
            CustomPlayerStatsGame.kdr, 
            CustomPlayerStatsGame.mis_CT, 
            CustomPlayerStatsGame.spr, 
            CustomPlayerStatsGame.kast_CT, 
            CustomPlayerStatsGame.adr_CT, 
            CustomPlayerStatsGame.adr, 
            CustomPlayerStatsGame.tdp_CT, 
            CustomPlayerStatsGame.kast, 
            CustomPlayerStatsGame.evspr, 
            CustomPlayerStatsGame.spr_CT, 
            CustomPlayerStatsGame.dpr_CT, 
            CustomPlayerStatsGame.kpr_CT, 
            CustomPlayerStatsGame.evspr_CT, 
            CustomPlayerStatsGame.rwpr_T, 
            CustomPlayerStatsGame.evsos, 
            CustomPlayerStatsGame.spr_T, 
            CustomPlayerStatsGame.odwr)\
        .order_by(Games.begin_at.asc())\
        .all()

    # List of feature components to be used in calculating averages.
    feature_components = [
        '20_spr',
        '25_spr',
        '25_tdp',
        '30_dpr',
        '30_kdr',
        '30_rwpr',
        '30_spr',
        '30_tdp',
        'inf_adr',
        'inf_adr_CT',
        'inf_dpr',
        'inf_dpr_CT',
        'inf_evsos',
        'inf_evspr',
        'inf_evspr_CT',
        'inf_kast',
        'inf_kast_CT',
        'inf_kdr',
        'inf_kdr_CT',
        'inf_kpr',
        'inf_kpr_CT',
        'inf_mis',
        'inf_mis_CT',
        'inf_mis_T',
        'inf_odwr',
        'inf_rwpr',
        'inf_rwpr_CT',
        'inf_rwpr_T',
        'inf_spr',
        'inf_spr_CT',
        'inf_spr_T',
        'inf_tdp',
        'inf_tdp_CT'
    ]

    # Convert the query result to a pandas DataFrame.
    df = pd.DataFrame(result, columns=[
        'num_rounds', 'rwpr', 'kdr_CT', 'tdp', 'mis_T', 'kpr', 'rwpr_CT', 'mis', 'dpr', 'kdr',
        'mis_CT', 'spr', 'kast_CT', 'adr_CT', 'adr', 'tdp_CT', 'kast', 'evspr', 'dpr_CT',
        'spr_CT', 'kpr_CT', 'evspr_CT', 'rwpr_T', 'evsos', 'spr_T', 'odwr'
    ])

    # Calculate averages of the player's statistics.
    averages = calculate_averages(df, feature_components)

    # Add Glicko rating and RD to the averages dictionary.
    averages['Rating'] = rating
    averages['RD'] = RD

    return averages


def calculate_averages(df: pd.DataFrame, columns: list) -> dict:
    """
    Calculates the moving averages for specified columns in a DataFrame, applying Bayesian shrinkage.

    This function iterates over a list of column names, each potentially prefixed with a number 
    indicating the window size for a moving average, or 'inf' for considering all available data.
    It calculates the moving average for each column and applies Bayesian shrinkage to adjust the values.

    :param df: DataFrame containing the data from which averages need to be calculated.
    :param columns: A list of strings representing the column names in the DataFrame. Each string 
                    can have a prefix like '30_' or 'inf_' indicating the window size for the moving average.
    :return: A dictionary with keys as column names and values as the calculated averages.
    """
    averages = {}

    # Replace values with NaN where num_rounds <= 12
    for col in columns:
        match = re.match(r'(\d+|inf)_(\w+)', col)
        if match:
            _, base_stat = match.groups()
            if base_stat in df.columns:
                df.loc[df['num_rounds'] <= 12, base_stat] = np.nan


    for col in columns:
        # Remove prefixes and extract window size
        match = re.match(r'(\d+|inf)_(\w+)', col)
        if match:
            window, base_stat = match.groups()
            window_size = len(df) if window == 'inf' else int(window)

        # Calculate moving average
        if base_stat in df.columns:
            # Select the appropriate window of data.
            if window_size == 'inf':
                series = df[base_stat].iloc[0:]
            else:
                series = df[base_stat].iloc[max(0, len(df[base_stat])-window_size):len(df[base_stat])]

            # Calculate non-null count and moving average.
            non_null_count = len(series) - series.isna().sum()
            moving_avg = series.mean()

            # Apply Bayesian shrinkage and add to averages.
            averages[col] = bayes_shrink(moving_avg, non_null_count, base_stat, feature_moments)
        else:
            averages[col] = None

    return averages


def fetch_match_info(match_slug: str) -> Union[dict, None]:
    """
    Fetches information about a match identified by its slug.

    This function makes an HTTP GET request to a specific URL constructed using the match_slug.
    It then parses the HTML response to extract player information for both the away and home teams.

    :param match_slug: The slug identifying the match. Used to construct the URL for the GET request.
    :return: A dictionary with keys 'away' and 'home', each containing a list of player slugs for the respective teams.
             Returns None if the HTTP request fails or if the response status is not 200.
    """
    # Make an HTTP GET request to the specified URL.
    response = requests.get(f"https://bo3.gg/matches/{match_slug}")  # Use the session to make requests

    if response.status_code != 200:
        return None
    
    match_html = BeautifulSoup(response.content, 'html.parser')

    # Efficiently find both away and home divs
    lineups = match_html.select(".c-widget-match-lineup--a, .c-widget-match-lineup--b")

    # Extract player links for away and home teams using list comprehensions
    away_players = [link['href'].split('/')[-1] for link in lineups[0].find_all('a', class_="player-info", href=True)]
    home_players = [link['href'].split('/')[-1] for link in lineups[1].find_all('a', class_="player-info", href=True)]

    return {'away': away_players, 'home': home_players}


def create_features(away: dict, home: dict) -> pd.DataFrame:
    """
    Creates a feature set for a model based on statistics of two teams, 'away' and 'home'.

    The function calculates different types of features like win probability, percent differences, 
    deltas, ratios, z-scores, and others based on the statistics provided in the 'away' and 'home' dictionaries. 
    It uses predefined feature names from the global FEATURES list to determine what calculations to perform.

    :param away: A dictionary containing statistics for the away team.
    :param home: A dictionary containing statistics for the home team.
    :return: A pandas DataFrame with a single row containing the calculated features.
    """
    model_features = {}

    model_features[FEATURES[0]] = glicko2_win_prob(away['Rating'], away['RD'], home['Rating'], home['RD'])

    for feature in FEATURES[1:]:
        if feature.startswith("percent_diff_"):
            base_stat = feature.replace("percent_diff_", "")
            model_features[feature] = (away[base_stat] - home[base_stat]) / ((away[base_stat] + home[base_stat]) / 2)

        if feature.startswith("delta_"):
            base_stat = feature.replace("delta_", "")
            model_features[feature] = away[base_stat] - home[base_stat]

        if feature.startswith("ratio_"):
            base_stat = feature.replace("ratio_", "")
            model_features[feature] = away[base_stat] / home[base_stat]

        if feature.startswith("z_"):
            base_stat = feature.replace("z_", "")
            underscore_pos = base_stat.find("_")
            model_features[feature] = (away[base_stat] - home[base_stat]) / np.sqrt(getattr(feature_moments, base_stat[underscore_pos + 1:] + "_var"))

        if feature.startswith("OD_"):
            base_stat = feature.replace("OD_", "")
            model_features[feature] = away[base_stat + "_T"] / home[base_stat +"_CT"]

        if feature.startswith("DO_"):
            base_stat = feature.replace("DO_", "")
            model_features[feature] = away[base_stat + "_CT"] / home[base_stat +"_T"]

    return pd.DataFrame(model_features, index=[0])


def get_bo1_prob(line_dict: dict) -> Tuple[float, float]:
    """
    Calculates the probability of winning for both away and home teams in a match.

    This function fetches the most recent match information for both teams and then computes the win probability
    for each team. It uses a pre-trained logistic regression model to predict the probabilities based on various features.

    :param line_dict: A dictionary containing information about the match, including team IDs and match slug generated from pinnacle api.
    :return: A tuple containing the win probabilities for the away and home teams, respectively.
    """
    session = Session()

    # For the most recent match involving the away team
    away_last_match = session.query(Matches)\
        .filter(or_(Matches.home_team_id == line_dict['away_team_id'], 
                    Matches.away_team_id == line_dict['away_team_id']))\
        .order_by(desc(Matches.start_date)).first()

    # For the most recent match involving the home team
    home_last_match = session.query(Matches)\
        .filter(or_(Matches.home_team_id == line_dict['home_team_id'], 
                    Matches.away_team_id == line_dict['home_team_id']))\
        .order_by(desc(Matches.start_date)).first()
    
    home_last_match_id = None
    away_last_match_id = None

    if home_last_match != None:
        home_last_match_id = home_last_match.id
    if away_last_match != None:
        away_last_match_id = away_last_match.id

    #Check if line already calucalted in db
    my_line = session.query(MyMoneylines)\
        .filter(
            MyMoneylines.away_last_match_id == away_last_match_id,
            MyMoneylines.home_last_match_id == home_last_match_id,
            MyMoneylines.match_id == line_dict['match_id']
            )\
        .first()

    if my_line:
        return 1/my_line.away_line, 1/my_line.home_line

    # Fetch player stats for both teams.
    players = fetch_match_info(line_dict['match_slug'])
    away_player_stats = pd.DataFrame([fetch_stats_for_player(p, session) for p in players['away']]).mean()
    home_player_stats = pd.DataFrame([fetch_stats_for_player(p, session) for p in players['home']]).mean()

    # Create features for the model.
    features = create_features(away_player_stats, home_player_stats)
    
    # Load the pre-trained model and predict probabilities.
    model = None
    with open('resources/logreg.pkl', 'rb') as file:
        model = pickle.load(file)
    probs = model.predict_proba(features)

    # Extract probabilities for away and home teams.
    away_prob = probs[:, 1][0]  # Class 1 (win from away team's perspective) probability.
    home_prob = probs[:, 0][0]  # Class 0 (win from home team's perspective) probability.

    #Commit my line to db
    existing_entry = session.query(MyMoneylines).filter_by(match_id=line_dict['match_id']).first()

    if existing_entry:
        existing_entry.home_team=line_dict['home_team_name']
        existing_entry.home_team_id=line_dict['home_team_id']  # Assuming this ID exists in your 'teams' table
        existing_entry.away_team=line_dict['away_team_name']
        existing_entry.away_team_id=line_dict['away_team_id']  # Assuming this ID exists in your 'teams' table
        existing_entry.match_id=line_dict['match_id']  # Assuming this ID exists in your 'matches' table
        existing_entry.date=datetime.now()
        existing_entry.home_last_match_id=home_last_match_id  # Assuming this ID exists in your 'matches' table
        existing_entry.away_last_match_id=away_last_match_id  # Assuming this ID exists in your 'matches' table
        existing_entry.away_line=1/away_prob
        existing_entry.home_line=1/home_prob
        existing_entry.bo_type=line_dict['bo_type']
        existing_entry.tier=line_dict['tier']
    else:
        # Create an instance of MyMoneylines
        moneyline_instance = MyMoneylines(
            home_team=line_dict['home_team_name'],
            home_team_id=line_dict['home_team_id'],  # Assuming this ID exists in your 'teams' table
            away_team=line_dict['away_team_name'],
            away_team_id=line_dict['away_team_id'],  # Assuming this ID exists in your 'teams' table
            match_id=line_dict['match_id'],  # Assuming this ID exists in your 'matches' table
            date=datetime.now(),
            home_last_match_id=home_last_match_id,  # Assuming this ID exists in your 'matches' table
            away_last_match_id=away_last_match_id,  # Assuming this ID exists in your 'matches' table
            away_line=1/away_prob,
            home_line=1/home_prob,
            bo_type=line_dict['bo_type'],
            tier=line_dict['tier']
        )
        session.add(moneyline_instance)

    session.commit()

    session.close()

    return away_prob, home_prob


def probability_specific_score(p: float, wins_required: int, total_games: int) -> float:
    """
    Calculates the probability of achieving a specific score in a series of games.

    This function computes the probability of a player/team winning a specific number of games 
    out of a total number of games played, given the probability of winning a single game. It 
    considers the order of wins and losses, using the binomial coefficient to calculate the number 
    of sequences leading to the specific score.

    Examples:
    1. (2-1) In a best-of-3 series (total_games=3) where a player needs 2 wins to win the series 
       (wins_required=2) and has a 60% chance (p=0.6) of winning any single game, the function 
       would calculate the probability of winning with a score of 2-1.
       Example usage: probability_specific_score(0.6, 2, 3)

    2. (3-2) For a scenario where a player needs 3 wins in a best-of-5 series (total_games=5) with a 
       50% chance (p=0.5) of winning each game, the probability of achieving a score of 3-2 
       would be calculated.
       Example usage: probability_specific_score(0.5, 3, 5)

    3. (2-0) In a best-of-3 series where a player needs 2 wins and has 
       a 70% chance (p=0.7) of winning any single game, the probability of achieving a score of 2-0 (2 total games)
       is calculated.
       Example usage: probability_specific_score(0.7, 2, 2)

    :param p: Probability of winning a single game.
    :param wins_required: Number of wins required to win the series.
    :param total_games: Total number of games played in the series.
    :return: Probability of achieving the specific score.
    """
    # Calculate the number of ways to achieve the specific score.
    number_of_sequences = comb(total_games - 1, wins_required - 1)

    # Calculate the probability of achieving the specific score.
    probability = number_of_sequences * (p ** wins_required) * ((1 - p) ** (total_games - wins_required))
    return probability


def probability_A_wins_series(p: float, n: int) -> tuple:
    """
    Calculates the probabilities of player A winning and losing a best-of-n series.

    Given the probability of player A winning a single game (p) and the total number of games in the series (n),
    this function computes the probability of player A winning and losing the series. The series is won by the 
    first player to win more than half of the total games.

    Examples:
    1. For a best-of-3 series (n=3) with player A having a 60% chance (p=0.6) of winning any single game, 
       the function calculates the probabilities of player A winning and losing the series.
       Example usage: probability_A_wins_series(0.6, 3)

    2. In a best-of-5 series (n=5) where player A has a 50% chance (p=0.5) of winning each game, the function 
       computes the probabilities of player A winning and losing the entire series.
       Example usage: probability_A_wins_series(0.5, 5)

    :param p: Probability of player A winning a single game.
    :param n: Total number of games in the best-of-n series.
    :return: A tuple containing the probabilities of player A winning and losing the series.
    """
    # Number of games required to win the series.
    games_to_win = (n // 2) + 1

    # Calculate the probability of winning the series.
    win_probability = sum(binom.pmf(k, n, p) for k in range(games_to_win, n+1))

    # Calculate the probability of losing the series.
    loss_probability = 1 - win_probability

    return win_probability, loss_probability


def probability_A_series_with_draw(p: float, n: int) -> tuple:
    """
    Calculates the probabilities of player A winning, losing, and drawing in a best-of-n series with the possibility of a draw.

    This function is applicable for series where 'n' is even and at least 2. It computes the probabilities of player A winning,
    losing, or the series ending in a draw, given the probability of winning a single game (p).

    Examples:
    1. For a best-of-2 series (n=2) with player A having a 60% chance (p=0.6) of winning any single game, 
       the function calculates the probabilities of player A winning, losing, and drawing the series.
       Example usage: probability_A_series_with_draw(0.6, 2)

    :param p: Probability of player A winning a single game.
    :param n: Total number of games in the best-of-n series. Must be even and at least 2.
    :return: A tuple containing the probabilities of player A winning, losing, and drawing the series.
    """
    # Number of games required to win the series.
    games_to_win = (n // 2) + 1

    # Calculate the probability of winning the series.
    win_probability = sum(binom.pmf(k, n, p) for k in range(games_to_win, n + 1))

    # Calculate the probability of losing the series.
    loss_probability = sum(binom.pmf(k, n, p) for k in range(games_to_win - 1))

    # Calculate the probability of a draw.
    draw_probability = binom.pmf(n // 2, n, p)

    return win_probability, loss_probability, draw_probability


def compute_moneyline_prob(away_prob: float, bo_type: int) -> Union[tuple, None]:
    """
    Computes the moneyline odds for a series based on the probability of the away team winning and the series format.

    The function determines the format of the series (best-of-1, best-of-3, best-of-5, etc.) and calculates the corresponding
    probabilities using either a win/loss model or a win/loss/draw model.

    Examples:
    1. For a best-of-1 (bo_type=1) series where the away team has a 60% chance (away_prob=0.6) of winning, 
       the function calculates the win/loss probabilities.
       Example usage: compute_moneyline(0.6, 1)

    2. In a best-of-3 (bo_type=3) series with the away team having a 50% chance (away_prob=0.5) of winning,
       the function computes the win/loss probabilities.
       Example usage: compute_moneyline(0.5, 3)

    3. For a best-of-2 (bo_type=2) series where the away team has a 70% chance (away_prob=0.7) of winning, 
       the function calculates the win/loss/draw probabilities.
       Example usage: compute_moneyline(0.7, 2)

    :param away_prob: Probability of the away team winning a single game.
    :param bo_type: Series format (e.g., best-of-1, best-of-3, best-of-5, etc.).
    :return: A tuple containing the calculated probabilities or None if the series format is not recognized.
    """
    # Compute win/loss probabilities for odd-numbered series formats.
    if bo_type in [1, 3, 5]:
        return probability_A_wins_series(away_prob, bo_type)
    
    # Compute win/loss/draw probabilities for even-numbered series formats.
    if bo_type in [2, 4]:
        return probability_A_series_with_draw(away_prob, bo_type)

    # Return None for unrecognized series formats.
    return None





