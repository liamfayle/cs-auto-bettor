from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import * 
import numpy as np
from sqlalchemy import select, and_, text
from typing import List, Dict, Union, Tuple
from multiprocessing import Pool
from sqlalchemy.sql import exists, func
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import case
from scraper.constants import WINDOWS
from tqdm import tqdm


def averages_player(player_id: int) -> None:
    """
    Calculate moving averages for a player's stats and update the database.

    :param int player_id: The unique identifier of the player.
    :return: None
    """
    session = Session()

    # Construct the query
    subquery = aliased(CustomStatsMA)
    result = (
        session.query(CustomPlayerStatsGame)
        .filter(CustomPlayerStatsGame.player_id == player_id)
        .join(Games, Games.id == CustomPlayerStatsGame.game_id)
        .order_by(Games.begin_at.asc())
        .all()
    )


    # Check if no games are found
    if not result:
        return

    # Convert the result to a list of dictionaries for easier processing
    games_data = [{column: getattr(row, column) for column in row.__table__.columns.keys()} for row in result]

    moving_averages(games_data, session)

    session.close()


def moving_averages(data: List[Dict[str, Union[int, float, None]]], session: Session, windows: List[Union[int, str]] = WINDOWS) -> None:
    """
    Calculate moving averages over specified window sizes for player's game data and update the database.

    :param List[Dict[str, Union[int, float, None]]] data: A list of dictionaries where each dictionary contains player's game stats.
    :param Session session: A SQLAlchemy session object to interact with the database.
    :param List[Union[int, str]] windows: A list of window sizes for which to calculate moving averages. 'inf' can be used for infinite window size.
    :return: None
    """
    exclude_keys = {'id', 'game_id', 'player_id', 'num_rounds'}
    windows = list(windows) 
    
    # Iterate over each dictionary in the input data
    for i in range(len(data)): #each game

        # Iterate over each window size
        for window in windows:

            # Initialize dictionaries to store moving averages and non-NaN counts
            results = {key: [] for key in data[0] if key not in exclude_keys}

            # Calculate moving average for each key
            for key in results:
                # Handle infinite window size as a special case
                if window == 'inf':
                    values = [d[key] for d in data[:i+1] if d[key] is not None and d['num_rounds'] > 12]
                else:
                    values = [d[key] for d in data[max(0, i-int(window)+1):i+1] if d[key] is not None and d['num_rounds'] > 12]
                
                # Calculate the moving average and non-NaN count
                if values:
                    mean_val = np.mean(values)
                    non_nan_count = len(values)
                    results[key].append((mean_val, non_nan_count))
                else:
                    results[key].append((None, 0))

            for ex_key in exclude_keys:
                if ex_key == "id":
                    continue
                results[ex_key] = data[i][ex_key]
            
            add_data_to_custom_stats_ma(results, session, str(window))


def add_data_to_custom_stats_ma(data_dict: Dict[str, Union[List[Tuple[Union[int, float, None], int]], Union[int, float, str, None]]], session: Session, window: str) -> None:
    """
    Add player's game stats and moving averages to the CustomStatsMA table in the database.

    :param Dict[str, Union[List[Tuple[Union[int, float, None], int]], Union[int, float, str, None]]] data_dict: 
        A dictionary containing player's game stats and moving averages. The values can be a list of tuples (for moving averages and counts) 
        or single values (for other game stats).
    :param Session session: A SQLAlchemy session object to interact with the database.
    :param str window: A string representing the window size for moving averages.
    :return: None
    """
    # Preparing the data for creating an instance of CustomStatsMA
    prepared_data = {'ma': window}

    for key, value in data_dict.items():
        if isinstance(value, list) and len(value) == 1 and len(value[0]) == 2:
            prepared_data[key] = value[0][0]
            prepared_data[key + '_N'] = value[0][1]
        else:
            prepared_data[key] = value

    # Creating an instance of CustomStatsMA
    custom_stats_ma_instance = CustomStatsMA(**prepared_data)
    
    # Adding and committing the instance to the database
    session.add(custom_stats_ma_instance)
    session.commit()


def calculate_averages(args: List[int], num_processes: int) -> None:
    """
    Calculate moving averages for multiple players in parallel.

    :param List[int] args: A list of player IDs for whom to calculate moving averages.
    :param int num_processes: The number of parallel processes to use for calculation.
    :return: None
    """
    with Pool(processes=num_processes) as pool:
        pool.map(averages_player, [player_id for player_id in args])


def calculate_all_averages(window: int = 10, num_processes: int = 8) -> None:
    """
    Calculate moving averages for all players in the database, processing them in chunks.

    :param int window: The number of players to process in each chunk. Default is 100.
    :param int num_processes: The number of parallel processes to use for calculations. Default is 8.
    :return: None
    """
    session = Session()
    subquery = aliased(CustomStatsMA)
    result = (
        session.query(
            CustomPlayerStatsGame.player_id,
            Games.begin_at,
            func.array_agg(CustomPlayerStatsGame.game_id).over(
                partition_by=CustomPlayerStatsGame.player_id,
                order_by=Games.begin_at.asc()
            ).label('game_ids_ordered')
        )
        .join(Games, Games.id == CustomPlayerStatsGame.game_id)
        .filter(~exists().where(
            (subquery.game_id == CustomPlayerStatsGame.game_id) &
            (subquery.player_id == CustomPlayerStatsGame.player_id)
        ))
        .order_by(CustomPlayerStatsGame.player_id, Games.begin_at.asc())
        .all()
    )
    player_ids = list(set([player_id for player_id, date, games in result]))
    session.close()

    to_process = len(player_ids)

    print(f"Need to process {to_process} instances.")
    
    for i in tqdm(range(0, to_process, window), desc="Processing"):
        if (i+window) < to_process:
            calculate_averages(player_ids[i:i+window], num_processes)
        else:
            calculate_averages(player_ids[i:to_process], num_processes)


def weighted_mean(stats: np.ndarray, Ns: np.ndarray) -> float:
    """
    Calculate the weighted mean of a set of statistics.

    :param np.ndarray stats: A NumPy array containing the statistics values.
    :param np.ndarray Ns: A NumPy array of the same length as `stats`, containing the weights for each statistic.
    :return: The calculated weighted mean.
    :rtype: float
    """
    weighted_mean = (stats * Ns).sum() / Ns.sum()
    return weighted_mean


def weighted_var(stats: np.ndarray, Ns: np.ndarray, weighted_mean: float) -> float:
    """
    Calculate the weighted variance of a set of statistics.

    :param np.ndarray stats: A NumPy array containing the statistics values.
    :param np.ndarray Ns: A NumPy array of the same length as `stats`, containing the weights for each statistic.
    :param float weighted_mean: The pre-calculated weighted mean of the statistics.
    :return: The calculated weighted variance.
    :rtype: float
    """
    weighted_var = (Ns * (stats - weighted_mean)**2).sum() / (Ns.sum() - (Ns**2).sum()/Ns.sum())
    return weighted_var


def get_weighted_stats(game_ids, filename: str = "model resources/feature_moments.py") -> None:
    """
    Retrieve custom statistics from a database, calculate their weighted mean and variance, and save the results to a file.
    Fetches most recent stats from CustomStatsMA with inf window (if used in CV make sure the CV is not shuffled (time series CV only)).

    :param str filename: The path to the file where the calculated statistics should be saved.
    :return: None
    """
    session = Session()

    if game_ids is None:
        # Query to get all unique game IDs
        game_ids = session.query(Games.id).distinct().all()
        game_ids = [id for (id,) in game_ids]

    # Define subquery to get the most recent game_id for each player
    subquery = (session.query(
        CustomStatsMA.player_id.label('player_id'),
        func.max(Games.id).label('most_recent_game_id')
    ).join(Games, and_(
        Games.id == CustomStatsMA.game_id,
        Games.id.in_(game_ids)
        ))
    .group_by(CustomStatsMA.player_id)
    .subquery())

    # Define an aliased version of CustomStatsMA for joining
    csma_alias = aliased(CustomStatsMA, name='csma_alias')

    # Query to get the required information for all players at once
    custom_stats = (session.query(
        subquery.c.player_id,
        csma_alias
    ).join(csma_alias, and_(
        csma_alias.player_id == subquery.c.player_id,
        csma_alias.game_id == subquery.c.most_recent_game_id,
        csma_alias.ma == 'inf'
    ))
    .all())

    # Get all attribute names from CustomStatsMA that don't have '_N' in them
    stat_names = [column.name for column in CustomStatsMA.__table__.columns if not column.name.endswith('_N') and column.name not in ['id', 'game_id', 'player_id', 'num_rounds', 'ma']]
    stat_dict = {stat_name: [] for stat_name in stat_names for stat_name in [stat_name, f'{stat_name}_N']}

    for player_id, player_stats in custom_stats:
        for stat in stat_names:
            stat_value = getattr(player_stats, stat)
            if stat_value == None:
                continue
            stat_dict[stat].append(stat_value)
            stat_dict[stat + "_N"].append(getattr(player_stats, stat + "_N"))

    with open(filename, 'w') as f:
        for stat in stat_names:
            w_mean = weighted_mean(np.array(stat_dict[stat]), np.array(stat_dict[stat + "_N"]))
            w_var = weighted_var(np.array(stat_dict[stat]), np.array(stat_dict[stat + "_N"]), w_mean)  #weighted is more optimistic (it cuts out most of the players who only played a few matches match)
            mean = np.mean(np.array(stat_dict[stat]))
            var = np.var(np.array(stat_dict[stat]))
            f.write(f'{stat}_w_mean = {w_mean}\n')
            f.write(f'{stat}_w_var = {w_var}\n')
            f.write(f'{stat}_mean = {mean}\n')
            f.write(f'{stat}_var = {var}\n')



if __name__ == "__main__":
    init_db()

    '''session = Session()
    CustomStatsMA.__table__.drop(session.bind) #remove
    session.close()''' #CODE FOR DELETING TABLE OF STATS

    calculate_all_averages()


    '''
    TODO this file is broken live

    Worked for creating dataset but when live trading i will likely calculate necessary values at run time
    
    '''