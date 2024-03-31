from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from bo3_gg_api import *
from models.models import *
from sqlalchemy import asc, desc, inspect
from sqlalchemy.sql import select, exists
from constants import *
import traceback
import time
from typing import TypeVar, Type, List
from odds_pipeline.log import log, LEVEL_ERROR, LEVEL_WARNING


#Declare type
Table = TypeVar("Table", bound=Base)


#DB INTERSCTION FUNCTIONS
def add_row_by_id(session: Session, data: dict, table: Type[Table]) -> None:
    """
    Adds a new record to the table in the database.

    :param session: An SQLAlchemy session object.
    :param data: A dictionary containing the necessary fields to create a new record.
                 Expects 'id' key in data to be related to 'id' key in table.
                 Expected keys are determined by the `Table.add_instance` method.
    :param table: The SQLAlchemy table class in the database.

    :return: None.
    """
    record = session.query(table).filter_by(id=data.get('id')).first()

    if record:
        for key, value in data.items():
            setattr(record, key, value)
    else:
        new_record = table.add_instance(data)
        session.add(new_record)

def id_exists(session: Session, record_id: int, my_table: Type[Table]) -> bool:
    """
    Check if a record with the given ID exists in the table.

    :param session: The SQLAlchemy session object.
    :param record_id: The ID to check for existence.
    :param my_table: The SQLAlchemy table class representing the table.

    :return: True if the ID exists, False otherwise.
    """

    return session.query(exists().where(my_table.id == record_id)).scalar()

def truncate_all_tables(session: Session) -> None:
    """
    Delete all rows from all tables using the given SQLAlchemy session. Table structures remain intact.

    :param session: SQLAlchemy session object.
    """

    # This line ensures all pending operations are flushed and current transaction is committed
    session = Session() # Open a new session
    
    session.query(RoundPlayerStats).delete()
    session.query(RoundTeamStats).delete()
    session.query(GamePlayerStats).delete()
    session.query(Players).delete()
    session.query(Rounds).delete()
    session.query(Games).delete()
    session.query(Matches).delete()
    session.query(Prizes).delete()
    session.query(Teams).delete()
    session.query(Events).delete()
    session.query(Regions).delete()
    session.query(Countries).delete()
    
    # Commit the changes
    session.commit()
    session.close()

def drop_all_tables() -> None:
    """
    Drop all tables associated with the given classes. The entire table structures will be removed.
    """
    session = Session()  # Open a new session

    # Drop each table
    RoundPlayerStats.__table__.drop(session.bind)
    RoundTeamStats.__table__.drop(session.bind)
    GamePlayerStats.__table__.drop(session.bind)
    Players.__table__.drop(session.bind)
    Rounds.__table__.drop(session.bind)
    Games.__table__.drop(session.bind)
    Matches.__table__.drop(session.bind)
    Prizes.__table__.drop(session.bind)
    Teams.__table__.drop(session.bind)
    Events.__table__.drop(session.bind)
    Countries.__table__.drop(session.bind)
    Regions.__table__.drop(session.bind)

    session.commit()
    session.close()

def update_table_parameter(session: Session, table: Type, id: int, parameter_name: str, new_value, commit: bool = False) -> None:
    """
    Finds an instance of the table using the provided ID and updates a specific parameter.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param table: The SQLAlchemy table class you want to update (Type).
    :param id: The ID of the event instance to be updated (int).
    :param parameter_name: The name of the parameter to be updated (str).
    :param new_value: The new value to set for the specified parameter.
    :param commit: Boolean flag indicating whether to commit changes to the database (bool, optional).

    :return: None
    """
    event = session.query(table).filter(table.id == id).first()

    if not event:
        log(f"Event with ID {id} not found.", LEVEL_ERROR)
        return

    setattr(event, parameter_name, new_value)

    if commit:
        session.commit()

#SCRAPER LOGIC FUNCTIONS
def events_link_new_data(status: int = STATUS_FINISHED + STATUS_ONGOING, offset: int = 0) -> str:
    """
    Get the formatted link for retrieving new data when running the scraper.

    :param status: The status of events to retrieve data for (int, optional).
                   Default is STATUS_FINISHED + STATUS_ONGOING.
    :param offset: The offset for pagination (int, optional). Default is 0.

    :return: The URL for retrieving new data from the API (str).
    """
    session = Session() # Open a new session

    event = None

    if status == STATUS_FINISHED:
        event = session.query(Events).filter(Events.matches_parsed == False).order_by(asc(Events.start_date)).first()

    start_date = event.start_date if event else "2012-01-01"
    url = f"https://api.bo3.gg/api/v1/tournaments?page[offset]={offset}&page[limit]=100&sort={SORT_OLDEST_FIRST}&filter[tournaments.status][in]={status}&filter[tournaments.start_date][gte]={start_date}&with=tournament_prizes,locations,matches"

    session.close()

    return url


def get_prize_data(session: Session, prizes: List[dict]) -> None:
    """
    Processes a list of prizes, fetching team data if necessary and adding the prizes to the database.

    For each prize in the provided list, this function:
    1. Parses the prize's JSON representation.
    2. Checks if the associated team is already in the database.
    3. If the team isn't in the database, fetches and adds the team data.
    4. Adds the parsed prize data to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param prizes: A list of JSON representations of prizes (List[dict]).

    :return: None
    """
    for prize in prizes:
        prize_data = parse_prize_json(prize)
        
        if prize_data['team_id'] is not None and not id_exists(session, prize_data['team_id'], Teams):
            get_team_data(session, prize_data['team_id'])

        add_row_by_id(session, prize_data, Prizes)


def get_team_data(session: Session, team_id: int) -> None:
    """
    Fetches team data for a given team ID from the API and adds it to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param team_id: The ID of the team to fetch data for (int)

    :return: None
    """
    team_data = fetch_json_from_url("https://api.bo3.gg/api/v1/teams?&filter[teams.id][eq]={}".format(team_id))['results']
    if len(team_data) == 0:
        add_row_by_id(session, {'id': team_id, 'name': 'undefined', 'slug': 'undefined'}, Teams)
    for team in team_data:
        add_row_by_id(session, parse_team_json(team), Teams)
    

def get_region_data(session: Session, region_id: int) -> None:
    """
    Fetches region data for a given region ID from the API and adds it to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param region_id: The ID of the region to fetch data for (int).

    :return: None
    """
    region_data = fetch_json_from_url("https://api.bo3.gg/api/v1/regions?&filter[id][eq]={}".format(region_id))['results']
    for region in region_data:
        add_row_by_id(session, parse_region_json(region), Regions)


def get_country_data(session: Session, country_id: int) -> None:
    """
    Fetches country data for a given country ID from the API and adds it to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param country_id: The ID of the country to fetch data for (int).

    :return: None
    """
    country_data = fetch_json_from_url("https://api.bo3.gg/api/v1/countries?&filter[id][eq]={}".format(country_id))['results']
    for country in country_data:
        if not id_exists(session, country['region_id'], Regions):
            get_region_data(session, country['region_id'])

        add_row_by_id(session, parse_country_json(country), Countries)


def get_match_data(session: Session, matches: List[dict]) -> int: #TODO Multithread match fetching
    """
    Processes a list of match data, adds it to the database, and fetches associated game data.

    For each match in the provided list, this function:
    1. Parses the match's JSON representation.
    2. Checks if the match status is "done" or "partially_done."
    3. Skips matches already stored in the database.
    4. Ensures that team data for the home and away teams exists in the database.
    5. Adds the parsed match data to the database.
    6. Calls get_game_data to fetch and add associated game data.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param matches: A list of JSON representations of matches (List[dict]).

    :return: The number of matches processed (int).
    """
    for match in matches: 
        match_data = parse_match_json(match)

        if match['status'] != "finished":
            continue

        if match['parsed_status'] != 'done' and match['parsed_status'] != 'partially_done':
            continue

        if id_exists(session, match['id'], Matches): #skip matches already stored in db
            continue
        
        if match_data['away_team_id'] is not None and not id_exists(session, match_data['away_team_id'], Teams):
            get_team_data(session, match_data['away_team_id'])

        if match_data['home_team_id'] is not None and not id_exists(session, match_data['home_team_id'], Teams):
            get_team_data(session, match_data['home_team_id'])

        if match_data['winner_team_id'] is not None and not id_exists(session, match_data['winner_team_id'], Teams):
            get_team_data(session, match_data['winner_team_id'])

        if match_data['loser_team_id'] is not None and not id_exists(session, match_data['loser_team_id'], Teams):
            get_team_data(session, match_data['loser_team_id'])

        add_row_by_id(session, match_data, Matches)

        get_game_data(session, match_data['id'])
    return len(matches)


def get_game_data(session: Session, match_id: int) -> None:
    """
    Fetches game data for a given match ID from the API and adds it to the database.

    For each game associated with the provided match ID, this function:
    1. Fetches the game's JSON representation.
    2. Parses the game data.
    3. Ensures that winner and loser team data exists in the database.
    4. Adds the parsed game data to the database.
    5. Calls get_game_player_stats to fetch and add player statistics for the game.
    6. Calls get_round_data to fetch and add round data for the game.
    7. Calls get_round_player_data to fetch and add player data for each round of the game.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param match_id: The ID of the match for which game data should be fetched (int).

    :return: None
    """
    games = fetch_json_from_url(f"https://api.bo3.gg/api/v1/games?sort=number&filter[games.match_id][eq]={match_id}&with=winner_team_clan,loser_team_clan,game_side_results,game_rounds")['results']
    for game in games:
        game_data = parse_game_json(game)

        if game_data['winner_team_id'] is not None and not id_exists(session, game_data['winner_team_id'], Teams):
            get_team_data(session, game_data['winner_team_id']) #add team if not in player table

        if game_data['loser_team_id'] is not None and not id_exists(session, game_data['loser_team_id'], Teams):
            get_team_data(session, game_data['loser_team_id']) #add team if not in player table

        add_row_by_id(session, game_data, Games)

        get_game_player_stats(session, game['id'])

        get_round_data(session, game)

        get_round_player_data(session, game['id'], game['rounds_count'])


def get_round_player_data(session: Session, game_id: int, num_rounds: int) -> None:
    """
    Fetches player data for each round of a game from the API and adds it to the database.

    For each round of the game with the provided game ID, this function:
    1. Fetches player statistics data for that round.
    2. For each player in the round, checks if their team and player data exists in the database.
    3. Adds the parsed player statistics data to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param game_id: The ID of the game for which round player data should be fetched (int).
    :param num_rounds: The number of rounds in the game (int).

    :return: None
    """
    if num_rounds is None:
        return

    for i in range(1,num_rounds+1):
        player_data = fetch_json_from_url(f"https://api.bo3.gg/api/v1/games/{game_id}/rounds/{i}/players_stats")
        
        for player in player_data:
            if player is None or player['steam_profile'] is None or player['steam_profile']['player'] is None:
                continue

            if player['steam_profile']['player']['team_id'] is not None and not id_exists(session, player['steam_profile']['player']['team_id'], Teams):
                get_team_data(session, player['steam_profile']['player']['team_id'])
            
            if player['steam_profile']['player']['id'] is not None and not id_exists(session, player['steam_profile']['player']['id'], Players):
                get_player_data(session, player['steam_profile']['player']['id'])
            
            add_row_by_id(session, parse_round_player_stats_json(player), RoundPlayerStats)


def get_player_data(session: Session, player_id: int) -> None:
    """
    Fetches player data for a given player ID from the API and adds it to the database.

    For the provided player ID, this function:
    1. Fetches the player's JSON representation.
    2. Adds the parsed player data to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param player_id: The ID of the player to fetch data for (int).

    :return: None
    """
    player_data = fetch_json_from_url(f"https://api.bo3.gg/api/v1/players?&filter[id][eq]={player_id}&with=country")['results']
    for player in player_data:
        add_row_by_id(session, parse_player_json(player), Players)


def get_game_player_stats(session: Session, game_id: int) -> None:
    """
    Fetches player statistics for a given game ID from the API and updates the player and player statistics tables.

    For the provided game ID, this function:
    1. Fetches player statistics data for the game.
    2. Parses player statistics data and player data.
    3. Ensures that the player's country, team, and team associated with the statistics exist in the database.
    4. Updates the player data in the database.
    5. Adds the parsed player statistics data to the database.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param game_id: The ID of the game for which player statistics should be fetched and updated (int).

    :return: None
    """
    players_stats = fetch_json_from_url(f"https://api.bo3.gg/api/v1/games/{game_id}/players_stats")
    for p_stats in players_stats:
        p_stats_data = parse_player_stats_json(p_stats)

        if p_stats['steam_profile']['player'] is None:
            continue

        player_data = parse_player_json(p_stats['steam_profile']['player'])

        if player_data['country_id'] is not None and not id_exists(session, player_data['country_id'], Countries):
            get_country_data(session, player_data['country_id']) #add country if not in player table

        if player_data['team_id'] is not None and not id_exists(session, player_data['team_id'], Teams):
            get_team_data(session, player_data['team_id']) #add team if not in player table

        if p_stats_data['team_id'] is not None and not id_exists(session, p_stats_data['team_id'], Teams):
            get_team_data(session, p_stats_data['team_id']) #add team if not in player table

        add_row_by_id(session, player_data, Players) #update player data

        add_row_by_id(session, p_stats_data, GamePlayerStats)


def get_round_data(session: Session, game_data: dict) -> None:
    """
    Fetches round data for a given game data dictionary and adds it to the database.

    For each round in the provided game data dictionary, this function:
    1. Adds the parsed round data to the database.
    2. Checks if there are team round statistics for the round and adds them to the database if available.

    :param session: SQLAlchemy session object for database interactions (sqlalchemy.orm.session.Session).
    :param game_data: The game data dictionary containing information about rounds and team round statistics (dict).

    :return: None
    """
    for round in game_data['game_rounds']:
        add_row_by_id(session, parse_round_json(round, game_data), Rounds)

        if len(round['game_round_team_clans']) == 2: #hadnling error where there was no data of team stats for round game_id = 1394
            add_row_by_id(session, parse_round_team_stats_json(round['game_round_team_clans'][0], game_data), RoundTeamStats)
            add_row_by_id(session, parse_round_team_stats_json(round['game_round_team_clans'][1], game_data), RoundTeamStats)


def parse_finished_events() -> None:
    """
    Parses all finished events and stores them in the database.

    This function iterates through finished events, retrieves event data, and adds it to the database.
    It also fetches and adds region, country, prize, match, and other related data to the database.

    :return: None
    """
    offset = 0
    count = 100

    while offset < count:
        event_link_finished = events_link_new_data(status=STATUS_FINISHED, offset=offset) #grabs events marked finished (filtered by earliest start date of event that i have in my db that has matches_parsed=false)

        json_data = fetch_json_from_url(event_link_finished)

        headers, event_data = retrieve_headers_and_data(json_data)
        count = headers['count']
        offset += headers['limit']

        i = 0
        while i < len(event_data):
            session = Session()

            event = event_data[i]

            '''print(f"Fetching data for finished event {event['id']}")
            print()''' 

            try:
                if id_exists(session, event.get('id'), Events) and session.query(Events).filter_by(id=event.get('id')).first().matches_parsed:
                    continue #match already fully parsed in db

                if event['region_id'] is not None and not id_exists(session, event['region_id'], Regions): 
                    get_region_data(session, event['region_id']) #add region if its not in table

                if event['country_id'] is not None and not id_exists(session, event['country_id'], Countries):
                    get_country_data(session, event['country_id']) #add country if not in table

                add_row_by_id(session, parse_event_json(event), Events) #add / update event

                get_prize_data(session, event['tournament_prizes']) #add prize data from finished event

                num_matches = get_match_data(session, event['matches']) #Get match data

                update_table_parameter(session, Events, event['id'], "number_matches", num_matches) #update values to show that this event is fully processed
                update_table_parameter(session, Events, event['id'], "matches_parsed", True)

                session.commit()  # Commit changes if all operations were successful
            except Exception as e:
                session.rollback()  # Rollback changes if any operation failed
                log(f"Failed to process event {event['id']} due to: {e}", LEVEL_WARNING)
                #traceback.print_exc()
                #print()
                i -= 1 
                time.sleep(30)
            finally:
                session.close()  # Close the session
                i += 1
            

def parse_ongoing_events() -> None:
    """
    Parses all ongoing events and stores them in the database.

    This function iterates through ongoing events, retrieves event data, and adds it to the database.
    It also fetches and adds region, country, prize, match, and other related data to the database.

    :return: None
    """
    offset = 0
    count = 100

    while offset < count:
        event_link_finished = events_link_new_data(status=STATUS_ONGOING, offset=offset) #grabs events marked ongoing (filtered by earliest start date of event that i have in my db that has matches_parsed=false)

        json_data = fetch_json_from_url(event_link_finished)

        headers, event_data = retrieve_headers_and_data(json_data)
        count = headers['count']
        offset += headers['limit']

        i = 0
        while i < len(event_data):
            session = Session()

            event = event_data[i]

            '''print(f"Fetching data for ongoing event {event['id']}")
            print() '''

            try:
                if id_exists(session, event.get('id'), Events) and session.query(Events).filter_by(id=event.get('id')).first().matches_parsed:
                    continue #match already fully parsed in db

                if event['region_id'] is not None and not id_exists(session, event['region_id'], Regions): 
                    get_region_data(session, event['region_id']) #add region if its not in table

                if event['country_id'] is not None and not id_exists(session, event['country_id'], Countries):
                    get_country_data(session, event['country_id']) #add country if not in table

                add_row_by_id(session, parse_event_json(event), Events) #add / update event

                num_matches = get_match_data(session, event['matches']) #Get match data

                update_table_parameter(session, Events, event['id'], "number_matches", num_matches) #update values to show that this event is fully processed

                session.commit()  # Commit changes if all operations were successful
            except Exception as e:
                session.rollback()  # Rollback changes if any operation failed
                log(f"Failed to process event {event['id']} due to: {e}", LEVEL_WARNING)
                #traceback.print_exc()
                #print()
                i -= 1
            finally:
                session.close()  # Close the session
                i += 1



if __name__ == "__main__":
    #drop_all_tables() #remove

    init_db()

    #Update & get finished events
    parse_finished_events()
    
    #Updated and get ongoing events
    parse_ongoing_events()






#TODO add oddspedia keys to the match object/table