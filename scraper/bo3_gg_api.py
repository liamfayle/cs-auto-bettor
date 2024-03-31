from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from copy import deepcopy
from datetime import datetime
import json
import requests
from sqlalchemy import  JSON
from scraper.constants import *
from typing import Union


def datetime_serializer(o):
    if isinstance(o, datetime):
        return o.strftime('%Y-%m-%d %H:%M:%S')


def print_dict_to_file_pretty(dictionary: dict, filename: str = "output.json") -> None:
    """
    Prints a dictionary to a file with nice indentation.

    :param dictionary: The dictionary to be printed (dict).
    :param filename: The name of the output file (str, default is "output.json").

    :return: None
    """
    json_string = json.dumps(dictionary, indent=4, default=datetime_serializer) 
    with open(filename, 'w') as file:
        file.write(json_string)


def fetch_json_from_url(url: str, headers: dict = None) -> Union[dict, None]:
    """
    Fetches and returns formatted JSON data from a given URL.

    :param url: The URL from which to fetch the JSON data (str).

    :return:
    - dict: The parsed JSON data if the request is successful.
    - None: If the request fails or if the response is not valid JSON.

    :raises:
    - requests.RequestException: For any network-related errors.
    - ValueError: If the response cannot be parsed as JSON.

    # Example usage:
    url = "https://api.example.com/data"
    data = fetch_json_from_url(url)
    if data:
        print(data)
    else:
        print("Failed to fetch or parse JSON data.")
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        if response.headers.get('Content-Encoding', '').lower() == "br":
            return json.loads(response.content.decode('utf-8'))

        # Parse and return the JSON data
        return response.json() #TODO consider checks that ensure data isnt empty etc...

    except requests.RequestException as e:
        print(f"Network error: {e}")
    except ValueError:
        print("Response content is not valid JSON.")

    return None


def parse_event_json(data: JSON) -> dict:
    """
    Parses the provided JSON data to extract relevant information about the event and its prize distribution.

    :param data: The input JSON data containing event and prize distribution details (dict).

    :return:
    - dict: A dictionary containing parsed details based on the 'event_schema' and 'prize_distribution_schema'.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_event_json]")
    
    # Extracting event details
    event = {
        'id': data.get('id'),  # The unique identifier for the event
        'slug': data.get('slug'),  # URL slug for the event
        'name': data.get('name'),  # Properly formatted event name
        'start_date': data.get('start_date'),  # Start date of the event
        'end_date': data.get('end_date'),  # End date of the event
        'prize': data.get('prize'),  # Total prize money for the event
        'event_type': data.get('event_type'),  # Type of event (e.g., online, lan)
        'tier': data.get('tier'),  # Tier classification of the event (e.g., s, a, b)
        'tier_rank': data.get('tier_rank'),  # Numeric rank based on tier (e.g., s=1, a=2)
        'status': data.get('status'),  # Current status of the event (e.g., upcoming, finished, ongoing)
        'country_id': data.get('country_id'),  # country details
        'region_id': data.get('region_id'),    # region details
        'city': data.get('city', {}).get("name") if data.get('city') else None,    # city details
        'number_matches': None,  # The number of matches in the event 
        'matches_parsed': False,  # Flag indicating if all matches from event have been parsed and stored in db
        'prize_distribution': []  # Placeholder for prize distribution details
    }
    
    
    return event


def parse_prize_json(data: JSON) -> dict:
    """
    Parses the provided JSON data to extract relevant prize distribution.

    :param data: The input JSON data containing prize distribution details (dict).

    :return:
    - dict: A dictionary containing parsed details based on the 'prize_distribution_schema'.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_prize_json]")

    # Extracting prize distribution details for each prize in the event
    prize_distribution = {
        'id': data.get('id'),  # Unique identifier for the data distribution
        'money': data.get('money'),  # data amount for this particular distribution
        'place': data.get('place'),  # Rank or position associated with the data (e.g., 1st, 2nd)
        'team_id': data.get('team_id'),  # Identifier for the team associated with the data
        'event_id': data.get('tournament_id'),  # Identifier for the tournament or event
    }

    return prize_distribution


def parse_region_json(data: JSON) -> dict:
    """
    Extracts data from the given input and returns dictionaries based on region_schema and country_schema.

    :param data: Input data containing information about a region and its countries (dict).

    :return:
    - dict: Dictionary based on region_schema.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """

    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_region_json]")
    
    # Extracting data based on region_schema
    region = {
        'id': data.get('id'),
        'slug': data.get('slug'),
        'name': data.get('name'),
        'countries': []  # Initializing with an empty list. This will be populated later.
    }
    
    return region


def parse_country_json(data: JSON) -> dict:
    """
    Extracts data from the given input and returns dictionaries based on region_schema and country_schema.

    :param data: Input data containing information about a region and its countries (dict).

    :return:
    - dict: Dictionary based on region_schema.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_country_json]")

    # Extracting data for each country based on country_schema
    country = {
        'id': data.get('id'),
        'code': data.get('code'),
        'name': data.get('name'),
        'region_id': data.get('region_id')
    }

    return country


def parse_team_json(data: JSON) -> dict:
    """
    Parses the provided match JSON data into a predefined match schema.

    :param data: A dictionary containing match details (dict).

    :return:
    - dict: A dictionary with the match details in the `match_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_team_json]")

    team_schema = {
        'id': data.get("id"),
        'name': data.get("name"), #:string: team name
        'slug': data.get("slug"), 
        'players': [],
    }

    return team_schema


def parse_match_json(data: JSON) -> dict:
    """
    Parses the provided match JSON data into a predefined match schema.

    :param data: A dictionary containing match details (dict).

    :return:
    - dict: A dictionary with the match details in the `match_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_match_json]")

    # Extract and assign values from the input data to the match schema directly.
    # The .get() method is used to retrieve values safely. If a key is not present,
    # it will default to None (or any default value provided).
    match_schema = {
        'id': data.get('id'),  # Extract match ID
        'slug': data.get('slug'),  # Extract match slug (typically a URL-friendly name)
        'away_team_id': data.get('team1_id'),  # Extract away team's ID
        'home_team_id': data.get('team2_id'),  # Extract home team's ID
        'winner_team_id': data.get('winner_team_id'),  # Extract the ID of the winning team
        'loser_team_id': data.get('loser_team_id'),  # Extract the ID of the losing team
        'event_id': data.get('tournament_id'),  # Extract the ID of the associated tournament
        'away_score': data.get('team1_score'),  # Extract the score of the away team
        'home_score': data.get('team2_score'),  # Extract the score of the home team
        'bo_type': data.get('bo_type'),  # Extract the type of match (e.g., Best of 3, Best of 5, etc.)
        'start_date': data.get('start_date'),  # Extract the start date/time of the match
        'end_date': data.get('end_date'),  # Extract the end date/time of the match
        'tier': data.get('tier'),  # Extract the tier (classification) of the match
        'tier_rank': data.get('tier_rank'),  # Extract the rank within the tier
        'game_version': data.get('game_version'),  # 1 for csgo and 2 for cs2
        'games': [] # Placeholder for games
    }

    return match_schema


def parse_match_betting_json(data: JSON) -> dict:
    """
    Parses the provided match JSON data into a predefined match schema.

    :param data: A dictionary containing match details (dict).

    :return:
    - dict: A dictionary with the match details in the `match_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_match_json]")

    # Extract and assign values from the input data to the match schema directly.
    # The .get() method is used to retrieve values safely. If a key is not present,
    # it will default to None (or any default value provided).
    away = data.get('team1')
    home = data.get('team2')
    if away is None or home is None:
        away = {}
        home = {}
    
    tournament = data.get('tournament')
    if tournament is None:
        tournament = {}

    match_schema = {
        'id': data.get('id'),  # Extract match ID
        'slug': data.get('slug'),
        'away_team_id': away.get('id'),  # Extract away team's ID
        'home_team_id': home.get('id'),  # Extract home team's ID
        'away_team_name': away.get('name'),  # Extract away team's ID
        'home_team_name': home.get('name'),  # Extract home team's ID
        'event_id': data.get('tournament_id'),  # Extract the ID of the associated tournament
        'event_name': tournament.get("name"),
        'bo_type': data.get('bo_type'),  # Extract the type of match (e.g., Best of 3, Best of 5, etc.)
        'date': data.get('start_date'),  # Extract the start date/time of the match
        'tier': data.get('tier'),  # Extract the tier (classification) of the match
    }

    return match_schema


def parse_game_json(data: JSON) -> dict:
    """
    Parses the provided game JSON data into a predefined game schema.

    :param data: A dictionary containing game details (dict).

    :return:
    - dict: A dictionary with the game details in the `game_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_game_json]")

    # Extract and assign values from the input data to the game schema directly.
    game_schema = {
        'id': data.get('id'),  # Extract the game ID
        'match_id': data.get('match_id'),  # Extract the match ID the game belongs to
        'begin_at': data.get('begin_at'),  # Extract the start date/time of the game
        'map_name': data.get('map_name'),  # Extract the map name where the game was played
        'duration': data.get('duration'),  # Extract the game duration (divide by a million to get ms)
        'winner_team_score': data.get('winner_clan_score'),  # Extract the score of the winning team
        'loser_team_score': data.get('loser_clan_score'),  # Extract the score of the losing team
        'status': data.get('status'),  # Extract the game's status (e.g., 'finished')
        'number': data.get('number'),  # Extract the sequence number of the map in the series
        'rounds_count': data.get('rounds_count'),  # Extract the total number of rounds played
        'winner_team_id': data.get('winner_team_clan', {}).get('team_id') if data.get('winner_team_clan') else None,  # Extract the ID of the winning team
        'loser_team_id': data.get('loser_team_clan', {}).get('team_id') if data.get('winner_team_clan') else None,  # Extract the ID of the losing team
        'rounds': [], # Extract round results
        'player_stats': []  # Placeholder for player stats, as it's not provided in the example JSON
    }

    return game_schema


def parse_player_json(data: JSON) -> dict:
    """
    Parses the provided player JSON data into a predefined player schema.

    :param data: A dictionary containing player details (dict).

    :return:
    - dict: A dictionary with the player details in the `player_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """

    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_player_json]")

    # Extract and assign values from the input data to the player schema directly.
    player_schema = {
        'id': data.get('id'),  # Extract the player ID
        'slug': data.get('slug'),  # Extract the player slug (URL-friendly name)
        'nickname': data.get('nickname'),  # Extract the player's in-game nickname
        'first_name': data.get('first_name'),  # Extract the player's first name
        'last_name': data.get('last_name'),  # Extract the player's last name
        'team_id': data.get('team_id'),  # Extract the ID of the player's team
        'country_id': data.get('country', {}).get("id") if data.get('country') else None,  # Extract the ID of the player's country
    }

    return player_schema


def parse_player_stats_json(data: JSON) -> dict:
    """
    Parses the provided player JSON data into a predefined player schema.

    :param data: A dictionary containing player details (dict).

    :return:
    - dict: A dictionary with the player details in the `player_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_player_stats_json]")
    
    # Initialize the schema with the data extracted from the input JSON.

    # General stats.
    player_stats_schema = {
        'id': data.get('id'),  # Extracting the 'id' field from the input data.
        'game_id': data.get('game_id'),  # Extracting the 'game_id' field.

        # Extracting nested player information using multiple dictionary key accesses.
        'player_id': data.get('steam_profile', {}).get('player', {}).get('id') if data.get('steam_profile') and data.get('steam_profile', {}).get('player') else None,
        
        # Extracting team details.
        'team_name': data['team_clan'].get('clan_name'),  # Name of the team from the nested 'team_clan' field.
        'team_id': data['team_clan'].get('team_id'),  # ID of the team from the same nested field.

        # Basic in-game stats.
        'win': data.get('win'),
        'kills': data.get('kills'),
        'deaths': data.get('death'),
        'assists': data.get('assists'),
        'headshots': data.get('headshots'),
        'first_kills': data.get('first_kills'),
        'first_death': data.get('first_death'),
        'trade_kills': data.get('trade_kills'),
        'traded_death': data.get('trade_death'),
        
        # Advanced in-game stats.
        'kast': data.get('kast'),
        'player_rating': data.get('player_rating'),
        
        # Multikill stats are nested in another dictionary. Accessing each key of that dictionary for 2k, 3k, 4k, 5k.
        'two_k': data.get('multikills', {}).get('2') if data.get('multikills') else None,
        'three_k': data.get('multikills', {}).get('3') if data.get('multikills') else None,
        'four_k': data.get('multikills', {}).get('4') if data.get('multikills') else None,
        'five_k': data.get('multikills', {}).get('5') if data.get('multikills') else None,

        # Other advanced stats.
        'adr': data.get('adr'),
        'hits': data.get('hits'),
        'shots': data.get('shots'),
        'got_damage': data.get('got_damage'),
        'damage': data.get('damage'),
        'utility_value': data.get('utility_value'),
        'money_spent': data.get('money_spent'),
        'money_save': data.get('money_save'),
        'clutches': data.get('clutches'),
    }

    return player_stats_schema


def parse_round_json(round_data: JSON, game_data: JSON) -> dict:
    """
    Parses the provided round JSON data into a predefined round schema.

    :param round_data: A dictionary containing round details (dict).
    :param game_data: A dictionary containing game details (dict).

    :return:
    - dict: A dictionary with the round details in the `round_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in round_data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_round_json]")

    winner_id = None
    loser_id = None
    try:
        game_winner_team = (game_data.get("winner_team_clan", {}).get("clan_name"), game_data.get("winner_team_clan", {}).get("team_id") )
        game_loser_team = (game_data.get("loser_team_clan", {}).get("clan_name"), game_data.get("loser_team_clan", {}).get("team_id") )

        if round_data.get('winner_clan_name') == game_winner_team[0]:
            winner_id = game_winner_team[1]
            loser_id = game_loser_team[1]
        elif round_data.get('winner_clan_name') == game_loser_team[0]:
            loser_id = game_winner_team[1]
            winner_id = game_loser_team[1]
    except Exception as e:
        print("failed with exception in parse_round_json (bo3_gg_api.py)")
        print(e)
        print()

    
    # Initialize the schema with the data extracted from the input JSON.
    round_schema = {
        'id': round_data.get('id'),  # Extracting the 'id' field from the input data.
        'game_id': round_data.get('game_id'),  # Extracting the 'game_id' field.
        'round_number': round_data.get('round_number'),  # Extracting the 'round_number' field.
        'round_duration': round_data.get('round_duration'),  # Extracting the 'round_duration' field.
        'end_reason': round_data.get('end_reason'),  # Extracting the 'end_reason' field.
        
        # Winner team details.
        'winner_team_side': round_data.get('winner_clan_side'),
        'winner_team_score': round_data.get('winner_clan_score'),
        'winner_team_name': round_data.get('winner_clan_name'),

        #ids
        'winner_team_id': winner_id,
        'loser_team_id': loser_id,

        # Loser team details.
        'loser_team_side': round_data.get('loser_clan_side'),
        'loser_team_score': round_data.get('loser_clan_score'),
        'loser_team_name': round_data.get('loser_clan_name'),

        # For this example, the 'round_team_stats' and 'round_player_stats' are initialized as empty lists 
        # because the provided JSON does not have matching fields. If more data becomes available, 
        # you would parse and fill these lists accordingly.
        'round_team_stats': [],
        'round_player_stats': []
    }

    return round_schema


def parse_round_team_stats_json(round_data: JSON, game_data: JSON) -> dict:
    """
    Parses the provided round team stats JSON data into a predefined schema.

    :param round_data: A dictionary containing round team stats details (dict).
    :param game_data: A dictionary containing game details (dict).

    :return:
    - dict: A dictionary with the round team stats details in the `round_team_stats_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in round_data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_round_team_stats_json]")

    enemy_id = None
    team_id = None
    try:
        game_winner_team = (game_data.get("winner_team_clan", {}).get("clan_name"), game_data.get("winner_team_clan", {}).get("team_id") )
        game_loser_team = (game_data.get("loser_team_clan", {}).get("clan_name"), game_data.get("loser_team_clan", {}).get("team_id") )

        if round_data.get('clan_name') == game_winner_team[0]:
            team_id = game_winner_team[1]
            enemy_id = game_loser_team[1]
        elif round_data.get('clan_name') == game_loser_team[0]:
            enemy_id = game_winner_team[1]
            team_id = game_loser_team[1]
    except Exception as e:
        print("failed with exception in parse_round_json (bo3_gg_api.py) [error based on missing team names]")
        print(e)
        print()


    # Extract data and populate the schema.
    round_team_stats_schema = {
        'id': round_data.get('id'),
        'team_side': round_data.get('team_side'),
        'round_number': round_data.get('round_number'),
        'win': round_data.get('win'),
        'equipment_value': round_data.get('equipment_value'),
        'win_streak': round_data.get('win_streak'),
        'game_id': round_data.get('game_id'),
        'game_round_id': round_data.get('game_round_id'),
        'team_name': round_data.get('clan_name'),
        'team_id': team_id,  
        'damage': round_data.get('damage'),
        'kast_scores_sum': round_data.get('kast_scores_sum'),
        'players_count': round_data.get('players_count'),
        'kills': round_data.get('kills'),
        'death': round_data.get('death'),
        'assists': round_data.get('assists'),
        'headshots': round_data.get('headshots'),
        'first_kills': round_data.get('first_kills'),
        'first_death': round_data.get('first_death'),
        'trade_kills': round_data.get('trade_kills'),
        'traded_death': round_data.get('trade_death'),
        'lose_streak': round_data.get('lose_streak'),
        'got_damage': round_data.get('got_damage'),
        'clutches': round_data.get('clutches'),
        'utility_value': round_data.get('utility_value'),
        'flash_assists': round_data.get('flash_assists'),
        'hits': round_data.get('hits'),
        'shots': round_data.get('shots'),
        'grenades_damage': round_data.get('grenades_damage'),
        'money_spent': round_data.get('money_spent'),
        'money_save': round_data.get('money_save'),
        'bomb_plant_attempts': round_data.get('bomb_plant_attempts'),
        'bomb_plants': round_data.get('bomb_plants'),
        'bomb_plant_fakes': round_data.get('bomb_plant_fakes'),
        'bomb_plant_deaths': round_data.get('bomb_plant_deaths'),
        'bomb_defuse_attempts': round_data.get('bomb_defuse_attempts'),
        'bomb_defuses': round_data.get('bomb_defuses'),
        'bomb_defuse_fakes': round_data.get('bomb_defuse_fakes'),
        'bomb_defuse_deaths': round_data.get('bomb_defuse_deaths'),
        'smoke_covered_enemies': round_data.get('smoke_covered_enemies'),
        'got_grenades_damage': round_data.get('got_grenades_damage'),
        'cumulative_wins': round_data.get('cumulative_wins'),
        'cumulative_kills': round_data.get('cumulative_kills'),
        'cumulative_deaths': round_data.get('cumulative_deaths'),
        'cumulative_damage': round_data.get('cumulative_damage'),
        'cumulative_assists': round_data.get('cumulative_assists'),
        'enemy_equipment_value': round_data.get('enemy_equipment_value'),
        'enemy_team_name': round_data.get('enemy_clan_name'),
        'enemy_team_id': enemy_id,  
        'clutch_attempts': round_data.get('clutch_attempts'),
        'clutch_attempts_vs': round_data.get('clutch_attempts_vs'),
        'clutches_vs': round_data.get('clutches_vs'),
        'pistol_round': round_data.get('pistol_round')
    }

    return round_team_stats_schema


def parse_round_player_stats_json(data: JSON) -> dict:
    """
    Parses the provided round player stats JSON data into a predefined schema.

    :param data: A dictionary containing round player stats details (dict).

    :return:
    - dict: A dictionary with the round player stats details in the `round_player_stats_schema` format.

    :raises:
    - KeyError: If the required 'id' field is missing in the input data.
    """
    # Ensuring that 'id' exists in the data
    if 'id' not in data:
        raise KeyError("The required 'id' field is missing in the input data. [parse_round_player_stats_json]")

    # Extract data and populate the schema.
    round_player_stats_schema = {
        "id": data.get("id"),
        "round_number": data.get("round_number"),
        "win": data.get("win"),
        "kills": data.get("kills"),
        "death": data.get("death"),
        "assists": data.get("assists"),
        "headshots": data.get("headshots"),
        "first_kills": data.get("first_kills"),
        "first_death": data.get("first_death"),
        "trade_kills": data.get("trade_kills"),
        "traded_death": data.get("trade_death"), #his death was traded by teammate
        "kast_score": data.get("kast_score"),
        "game_id": data.get("game_id"),
        "game_round_id": data.get("game_round_id"),
        "player_id": data.get("steam_profile", {}).get("player", {}).get("id") if data.get('steam_profile') and data.get('steam_profile', {}).get('player') else None,
        "team_name": data.get("clan_name"),
        'team_id': data.get("team_clan", {}).get("team_id") if data.get('team_clan') else None,
        'enemy_team_name':data.get("enemy_clan_name"),  # TODO
        "damage": data.get("damage"),
        "multikills_2k": data.get("multikills", {}).get("2") if data.get('multikills') else None,
        "multikills_3k": data.get("multikills", {}).get("3") if data.get('multikills') else None,
        "multikills_4k": data.get("multikills", {}).get("4") if data.get('multikills') else None,
        "multikills_5k": data.get("multikills", {}).get("5") if data.get('multikills') else None,
        "hits": data.get("hits"),
        "shots": data.get("shots"),
        "cumulative_damage": data.get("cumulative_damage"),
        "got_damage": data.get("got_damage"),
        "utility_value": data.get("utility_value"),
        "money_spent": data.get("money_spent"),
        "money_save": data.get("money_save"),
        "team_side": data.get("team_side"),
        "cumulative_kills": data.get("cumulative_kills"),
        "cumulative_death": data.get("cumulative_death"),
        "cumulative_assists": data.get("cumulative_assists"),
        "cumulative_kast_score": data.get("cumulative_kast_score"),
        "cumulative_kast": data.get("cumulative_kast"),
        "clutches": data.get("clutches"),
        "pistol_round": data.get("pistol_round"),
        "clutches_1v1": data.get("clutches_stats", {}).get("1") if data.get('clutches_stats') else None,
        "clutches_1v2": data.get("clutches_stats", {}).get("2") if data.get('clutches_stats') else None,
        "clutches_1v3": data.get("clutches_stats", {}).get("3") if data.get('clutches_stats') else None,
        "clutches_1v4": data.get("clutches_stats", {}).get("4") if data.get('clutches_stats') else None,
        "clutches_1v5": data.get("clutches_stats", {}).get("5") if data.get('clutches_stats') else None,
        "movement_distance": data.get("movement_distance"),
        "avg_team_distance": data.get("avg_team_distance"),
        "bomb_plant_attempts": data.get("bomb_plant_attempts"),
        "bomb_plants": data.get("bomb_plants"),
        "bomb_plant_fakes": data.get("bomb_plant_fakes"),
        "bomb_plant_deaths": data.get("bomb_plant_deaths"),
        "bomb_defuse_attempts": data.get("bomb_defuse_attempts"),
        "bomb_defuses": data.get("bomb_defuses"),
        "bomb_defuse_fakes": data.get("bomb_defuse_fakes"),
        "bomb_defuse_deaths": data.get("bomb_defuse_deaths"),
        "smoke_covered_enemies": data.get("smoke_covered_enemies"),
        "grenades_damage": data.get("grenades_damage"),
        "flash_assists": data.get("flash_assists"),
        "got_grenades_damage": data.get("got_grenades_damage"),
        "avg_enemy_equipment_value": data.get("avg_enemy_equipment_value"),
        "cumulative_wins": data.get("cumulative_wins"),
        "wall_bang_kills": data.get("wall_bang_kills"),
        "no_scope_kills": data.get("no_scope_kills"),
        "flash_assisted_kills": data.get("flash_assisted_kills"),
        "blinded_kills": data.get("blinded_kills"),
        "clutch_attempts": data.get("clutch_attempts"),
        "clutch_attempts_vs": data.get("clutch_attempts_vs"),
        "clutches_vs": data.get("clutches_vs"),
    }

    return round_player_stats_schema


def retrieve_headers_and_data(json_data: JSON) -> tuple:
    """
    Extracts the 'total' and 'results' fields from the provided JSON data.

    The function returns the 'total' and 'results' values from the input JSON if both are present.
    If either 'total' or 'results' is missing, it returns the entire input JSON data.

    :param json_data: The input JSON in dictionary format (dict).

    :return:
    - tuple: A tuple containing the 'total' and 'results' values if both are present in the input JSON.
    - dict: The original input JSON data if either 'total' or 'results' is not present.

    Example:
    For input:
    {"total": 5, "results": ["A", "B"], "other": "value"}
    Returns:
    (5, ["A", "B"])

    For input:
    {"results": ["A", "B"], "other": "value"}
    Returns:
    {"results": ["A", "B"], "other": "value"}
    """
    if json_data.get('total') != None and json_data.get('results') != None:
        return json_data['total'], json_data['results']
    return None, json_data


'''

https://api.bo3.gg/api/v1/tournaments?page[offset]=0&page[limit]=1&sort=start_date&filter[tournaments.status][in]=current,upcoming,defwin,finished&with=teams,tournament_prizes,locations,matches
https://api.bo3.gg/api/v1/tournaments?page[offset]=0&page[limit]=50&sort=-end_date&filter[tournaments.status][in]=finished&filter[tournaments.end_date][gte]=2023-04-10&filter[tournaments.start_date][lte]=2023-10-10&filter[tournaments.discipline_id][eq]=1&with=teams,tournament_prizes,locations

https://api.bo3.gg/api/v1/matches?page[offset]=0&page[limit]=50&sort=-start_date&filter[matches.status][in]=current,upcoming&filter[matches.tournament_id][eq]=2176&with=teams,tournament,games,stage,tournament_deep

https://api.bo3.gg/api/v1/games?sort=number&filter[games.match_id][eq]=36256&with=winner_team_clan,loser_team_clan,game_side_results,game_rounds

https://api.bo3.gg/api/v1/games/70003/players_stats

https://api.bo3.gg/api/v1/games/70003/rounds/1/players_stats



https://api.bo3.gg/api/v1/countries?&filter[id][eq]=2

https://api.bo3.gg/api/v1/players?&filter[id][eq]=20684&with=country

https://api.bo3.gg/api/v1/teams?&filter[teams.id][eq]=1

https://api.bo3.gg/api/v1/matches?&filter[matches.status][in]=current&sort=start_date     #Matches upcoming in order

'''




