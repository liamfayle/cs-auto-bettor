from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
import numpy as np
from sqlalchemy.orm import aliased
from sqlalchemy import func
from sqlalchemy.sql import exists
from typing import List, Tuple
from multiprocessing import Pool
import warnings
from tqdm import tqdm


#config
warnings.simplefilter("error", RuntimeWarning)


def get_g(phi: float) -> float:
    '''
    get_g returns the computed g(phi) required for several steps in the glicko implementation

    :param phi: rating deviation parameter scaled for glicko2
    :return: g(phi) result
    '''
    return 1 / ( np.sqrt( 1 + ( ( 3 * ( np.power(phi,2) ) ) / ( np.pi**2 ) ) ) )


def get_E(mu: float, mu_j: np.array(float), phi_j: np.array(float)) -> float:
    '''
    get_E computes and returns the expectation of a win given your mu (scaled rating), opponents mu, and oppoenents phi (scaled deviation)
    
    :param mu: is current player rating
    :param mu_j: is oppoennt j rating
    :param phi_j: is opponent j rating deviation
    :return: Expecation result
    '''
    return 1 / ( 1 + np.exp( -1 * get_g(phi_j) * (mu - mu_j) ) )


def f_of_x(x: int, delta: float, phi: float, v: float, a: float, tau: float) -> float:
    '''
    f_of_x is function required for step 5 of glicko2 process

    :param x: value to be set during iteration
    :param delta: value calculated in step 4
    :param phi: scaled rating deviation of user
    :param a: set to the natural logarithm of the rating volatiltiy squared
    :param tau: global scale parameter that impacts how "fast" ratings and their deviations change
    '''
    num1 = np.exp(x) * (delta**2 - phi**2 - v - np.exp(x))
    num2 = x - a

    denom1 = 2 * (phi**2 + v + np.exp(x))**2
    denom2 = tau**2

    return (num1/denom1) - (num2/denom2)


def games_to_process() -> List[int]:
    """
    Query the database to find all game IDs from the Games table 
    that are not present in the PlayerGlicko table, 
    sorted by the begin_at column in ascending order (earliest first).
    
    :return: A list of game IDs that need to be processed.
    :rtype: List[int]
    """
    session = Session()

    # Use an alias for PlayerGlicko to be able to exclude its game_id in the main query
    pg_alias = aliased(PlayerGlicko)

    # Use a LEFT OUTER JOIN to find all records in Games with no corresponding record in PlayerGlicko
    games = session.query(Games) \
        .outerjoin(pg_alias, Games.id == pg_alias.game_id) \
        .filter(pg_alias.game_id.is_(None)) \
        .filter(Games.winner_team_id != None) \
        .filter(Games.loser_team_id != None) \
        .filter(Games.rounds_count != None) \
        .filter(exists().where(CustomPlayerStatsGame.game_id == Games.id)) \
        .order_by(Games.begin_at.asc()) \
        .all()

    session.close()

    # Extract just the game_id values from the result set and return as a list
    #games = [game[0] for game in games]

    return games


def get_game_details(game: object) -> dict:
    """
    Retrieves details of a game, including information about the winner and loser teams and their players.

    :param game: The game object containing game details.

    :return:
    - dict: A dictionary containing game details for the winner team.
    - dict: A dictionary containing game details for the loser team.
    
    Example:
    get_game_details(game) returns:
    ({'id': winner_team_id, 'score': winner_team_score_normalized, 'players': [{'mu_pre': mu_pre, 'sigma_pre': sigma_pre, 'tdp': tdp}, ...]},
     {'id': loser_team_id, 'score': loser_team_score_normalized, 'players': [{'mu_pre': mu_pre, 'sigma_pre': sigma_pre, 'tdp': tdp}, ...]})
    """
    session = Session()

    games = {
        'winner': {
            'id': game.winner_team_id,
            'score': game.winner_team_score / (game.winner_team_score + game.loser_team_score) if game.winner_team_score is not None and (game.winner_team_score + game.loser_team_score) > 0 else 1,
            'players': []
        },
        'loser': {
            'id': game.loser_team_id,
            'score': game.loser_team_score / (game.winner_team_score + game.loser_team_score) if game.winner_team_score is not None and (game.winner_team_score + game.loser_team_score) > 0 else 0,
            'players': []
        }
    }

    # Query to get player stats, glicko ratings, and team_id
    # Create an alias for PlayerGlicko for the subquery
    player_glicko_alias = aliased(PlayerGlicko)

    # Subquery to get the most recent PlayerGlicko entry per player
    subquery = (
        session.query(
            player_glicko_alias.player_id,
            func.max(player_glicko_alias.begin_at).label('max_begin_at')
        )
        .group_by(player_glicko_alias.player_id)
        .subquery()
    )

    # Main query
    player_game_stats = (
        session.query(
            CustomPlayerStatsGame, 
            PlayerGlicko, 
            GamePlayerStats.team_id
        )
        .outerjoin(
            subquery,
            (subquery.c.player_id == CustomPlayerStatsGame.player_id)
        )
        .outerjoin(
            PlayerGlicko,
            (PlayerGlicko.player_id == subquery.c.player_id) & (PlayerGlicko.begin_at == subquery.c.max_begin_at)
        )
        .outerjoin(
            GamePlayerStats, 
            (GamePlayerStats.game_id == CustomPlayerStatsGame.game_id) & (GamePlayerStats.player_id == CustomPlayerStatsGame.player_id)
        )
        .filter(CustomPlayerStatsGame.game_id == game.id)
        .distinct(CustomPlayerStatsGame.player_id)
        .all()
    )

    session.close()

    # Process the results
    for player_stats, player_glicko, team_id in player_game_stats:
        p = {
            'player_id': player_stats.player_id,
            'game_id': game.id,
            'begin_at': game.begin_at,
            'rating_pre': player_glicko.rating_post if player_glicko else 1500,
            'deviation_pre': player_glicko.deviation_post if player_glicko else 350,
            'vol_pre': player_glicko.vol_post if player_glicko else 0.06,
            'tdp': player_stats.tdp if player_stats.num_rounds >= 12 else 0, #setting cutoff to cut out some bad data (some games only have a few rounds of data and doesnt make sense to include)
            'team_id': team_id  # Add team_id to the dictionary
        }

        if team_id == games['winner']['id']:
            games['winner']['players'].append(p)
        elif team_id == games['loser']['id']:
            games['loser']['players'].append(p)
        else: #fix for bug wherte team id is wrong for some reason: game id = 34884
            session = Session()
            new_glicko = PlayerGlicko(
                game_id=p['game_id'], player_id=p['player_id'], begin_at=p['begin_at'], 
                rating_pre=p['rating_pre'], deviation_pre=p['deviation_pre'], vol_pre=p['vol_pre'],
                rating_post=p['rating_pre'], deviation_post=p['deviation_pre'], vol_post=p['vol_pre'],
            )
            session.add(new_glicko)
            session.commit()
            session.close()

    return games


def gamma_multipliers(game_details: dict, gamma: int = 1) -> None:
    """
    Calculates and assigns gamma multipliers to players in the game details.

    :param game_details: A tuple containing game details for the winner and loser teams.
    :param gamma: Gamma parameter for multiplier calculation (default is 1).

    Example:
    gamma_multipliers(game_details, gamma=1) modifies the 'game_details' dictionary to include player multipliers.
    """
    win_denom = 0
    lose_denom = 0
    try:
        win_denom = sum(d['tdp'] ** gamma if d['tdp'] > 0 else 1/0 for d in game_details['winner']['players']) #hacky exception raise
        lose_denom = sum(1 / (d['tdp'] ** gamma) for d in game_details['loser']['players'])
    except: #hacky fix for bad data
        for player in game_details['winner']['players']:
            player['multiplier'] = 1

        for player in game_details['loser']['players']:
            player['multiplier'] = 1

        return

    for player in game_details['winner']['players']:
        player['multiplier'] = 5 * (player['tdp'] ** gamma) / win_denom

    for player in game_details['loser']['players']:
            player['multiplier'] = 5 * (1 / (player['tdp'] ** gamma)) / lose_denom
        

def compute_glicko2_player(args: Tuple[dict, dict]) -> None:
    """
    Calculate and update a player's Glicko-2 rating and other parameters based on match results.

    :param args: A tuple containing two dictionaries: player dictionary and opponent team dictionary.
                 The player dictionary should have keys: 'rating_pre', 'deviation_pre', 'vol_pre',
                 'game_id', 'player_id', 'begin_at', 'multiplier'.
                 The opponent team dictionary should have a key: 'players' which is a list of dictionaries
                 with keys: 'rating_pre', 'deviation_pre'.
    :type args: Tuple[dict, dict]

    :return: None
    """
    #step 1
    player, opp_team = args

    tau = 0.5 #Constant

    #Step 2
    mu = (player['rating_pre'] - 1500) / 173.7178
    phi = player['deviation_pre'] / 173.7178
    vol = player['vol_pre']

    #Step 3
    opp_phis = np.array([d['deviation_pre'] / 173.7178 for d in opp_team['players']])
    opp_mus = np.array([(d['rating_pre'] - 1500) / 173.7178 for d in opp_team['players']])

    if len(opp_mus) == 0: #handling bad data (gameid = 27443) where all players were stored as one team
        session = Session()
        new_glicko = PlayerGlicko(
            game_id=player['game_id'], player_id=player['player_id'], begin_at=player['begin_at'], 
            rating_pre=player['rating_pre'], deviation_pre=player['deviation_pre'], vol_pre=player['vol_pre'],
            rating_post=player['rating_pre'], deviation_post=player['deviation_pre'], vol_post=player['vol_pre'],
        )
        session.add(new_glicko)
        session.commit()
        session.close()
        return

    v = 1 / (np.sum((get_g(opp_phis)**2) * get_E(mu, opp_mus, opp_phis) * (1 - get_E(mu, opp_mus, opp_phis))))

    #Step 4
    match_results = np.array([(1-opp_team['score'])] * len(opp_team['players']))
    delta = np.sum( get_g(opp_phis) * ( match_results - get_E(mu, opp_mus, opp_phis) ) ) * v

    #Step 5
    A = np.log(vol**2)
    a = np.log(vol**2)
    B = 0
    if (delta**2) <= (phi**2 + v):
        k = 1
        while f_of_x(a - k*tau, delta, phi, v, a, tau) < 0:
            k += 1
        B = a - k*tau
    else:
        B = np.log(delta**2 - phi**2 - v)

    Fa = f_of_x(A, delta, phi, v, a, tau)
    Fb = f_of_x(B, delta, phi, v, a, tau)
    while np.abs(B - A) > 0.0001:  #Suggested as 0.000001 (reduced to test if speeds up)
        C = A + (((A - B) * Fa) / (Fb - Fa))
        Fc = f_of_x(C, delta, phi, v, a, tau)
        if Fb * Fc <= 0:
            A = B
            Fa = Fb
        else:
            Fa = Fa / 2
        B = C
        Fb = Fc

    sigma_prime = np.exp(A / 2)

    #Step 6
    phi_star = np.sqrt(phi**2 + sigma_prime**2)

    #Step 7
    phi_prime = 1 / np.sqrt((1 / phi_star**2) + (1 / v))

    mu_prime = mu + (phi_prime**2 * player['multiplier'] * np.sum( get_g(opp_phis) * ( match_results - get_E(mu, opp_mus, opp_phis) ) ))
    
    #Step 8
    rating_prime = (173.7178 * mu_prime) + 1500
    RD_prime = (173.7178 * phi_prime)

    player['rating_post'] = rating_prime
    player['deviation_post'] = RD_prime
    player['vol_post'] = sigma_prime

    session = Session()

    new_glicko = PlayerGlicko(
        game_id=player['game_id'], player_id=player['player_id'], begin_at=player['begin_at'], 
        rating_pre=player['rating_pre'], deviation_pre=player['deviation_pre'], vol_pre=player['vol_pre'],
        rating_post=player['rating_post'], deviation_post=player['deviation_post'], vol_post=player['vol_post'],
    )

    session.add(new_glicko)
    session.commit()
    session.close()


def compute_glicko2_pool(args: List[Tuple[dict, dict]], num_processes: int) -> None:
    """
    Calculate Glicko-2 ratings for a pool of players concurrently using multiprocessing.

    :param args: A list of tuples, each containing two dictionaries: player dictionary and opponent team dictionary.
                 The player dictionary should have keys: 'rating_pre', 'deviation_pre', 'vol_pre',
                 'game_id', 'player_id', 'begin_at', 'multiplier'.
                 The opponent team dictionary should have a key: 'players' which is a list of dictionaries
                 with keys: 'rating_pre', 'deviation_pre'.
    :type args: List[Tuple[dict, dict]]

    :param num_processes: The number of processes to use for parallel computation.
    :type num_processes: int

    :return: None
    """
    with Pool(processes=num_processes) as pool:
        pool.map(compute_glicko2_player, [(player, opp_team) for player, opp_team in args])


def compute_glicko2(window: int = 10, num_processes: int = 8) -> None:
    """
    Calculate Glicko-2 ratings for a batch of games.

    :param window: The number of games to process before printing progress.
    :type window: int, optional

    :param num_processes: The number of processes to use for parallel computation.
    :type num_processes: int, optional

    :return: None
    """
    games = games_to_process()

    to_process = len(games)
    print(f"Need to process {to_process} instances.")

    with tqdm(total=to_process, desc="Processing") as pbar:
        i = 0
        while i < to_process:
            game_details = get_game_details(games[i])

            gamma_multipliers(game_details)

            args = format_args(game_details)

            compute_glicko2_pool(args, num_processes)

            # Update the progress bar manually
            pbar.update(1)
            i += 1


def format_args(game_details: dict) -> List[Tuple[dict, dict]]:
    """
    Format game details into a list of player-opponent team tuples for Glicko-2 calculation.

    :param game_details: A dictionary containing details of a game, including winner and loser teams.
    :type game_details: dict

    :return: A list of tuples, each containing a player dictionary and an opponent team dictionary.
    :rtype: List[Tuple[dict, dict]]
    """
    formatted_data = []

    winner_team = game_details['winner']
    loser_team = game_details['loser']

    for player in winner_team['players']:
        formatted_data.append((player, loser_team))

    for player in loser_team['players']:
        formatted_data.append((player, winner_team))

    return formatted_data


def glicko2_win_prob(p1_Rating, p1_RD, p2_Rating, p2_RD) -> Float:
    '''
    calculates the win probability for player 1 

    :param p1_Rating: Player 1's rating
    :param p1_RD: Player 1's rating deviation
    :param p2_Rating: Player 2's rating
    :param p2_RD: Player 2's rating deviation
    :return: Player 1's win probability
    '''
    A = get_g(np.sqrt(p1_RD**2 + p2_RD**2)) * (p1_Rating - p2_Rating)
    return 1 / (1 + np.exp(-1 * A))


if __name__ == "__main__":
    init_db()

    '''session = Session()
    PlayerGlicko.__table__.drop(session.bind) #remove
    session.close()''' #CODE FOR DELETING TABLE OF STATS


    compute_glicko2() #change back to defailt later
    

    
        