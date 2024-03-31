from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
import numpy as np
import pandas as pd
from sqlalchemy import asc, desc, or_
from scraper.constants import WINDOWS
from multiprocessing import Pool
import os
import concurrent.futures
from sklearn.model_selection import KFold
from bo3_stats.glicko import glicko2_win_prob
from bo3_stats.stats_over_time import get_weighted_stats
import importlib
import traceback



def games_to_csv(filename="datasets/games.csv"):
    session = Session()

    # Query the Games table and order by begin_at
    games_query = session.query(Games).order_by(asc(Games.begin_at))

    games_df = pd.read_sql(games_query.statement, session.bind)

    # Close the session
    session.close()

    games_df.to_csv(filename, index=False)


def add_glicko_to_csv(read_filename="datasets/games.csv", write_filename="datasets/games_glicko.csv"):
    # Read the dataset
    df = pd.read_csv(read_filename)
    
    # Create a new DataFrame to store results
    results = df.copy()

    # Add columns for glicko ratings and deviations
    results['winner_team_rating'] = None
    results['loser_team_rating'] = None
    results['winner_team_deviation'] = None
    results['loser_team_deviation'] = None
    results['winner_glicko_win_prob'] = None
    
    # Create a database session
    session = Session()

    total = len(df.index)

    for index, row in df.iterrows():
        # Get player IDs for the teams
        teams = get_players_ids(row['id'], session)
        
        # Get the player Glicko ratings and deviations
        winning_team_rating, winning_team_deviation = (None, None)
        losing_team_rating, losing_team_deviation = (None, None)

        try:
            winning_team_rating, winning_team_deviation = get_team_glicko(teams[row['winner_team_id']], row['id'], session)
            losing_team_rating, losing_team_deviation = get_team_glicko(teams[row['loser_team_id']], row['id'], session)
        except:
            pass
        
        # Store the results
        results.at[index, 'winner_team_rating'] = winning_team_rating
        results.at[index, 'loser_team_rating'] = losing_team_rating
        results.at[index, 'winner_team_deviation'] = winning_team_deviation
        results.at[index, 'loser_team_deviation'] = losing_team_deviation

        if winning_team_rating is not None and losing_team_rating is not None and winning_team_deviation is not None and losing_team_deviation is not None:
            results.at[index, 'winner_glicko_win_prob'] = glicko2_win_prob(winning_team_rating, winning_team_deviation, losing_team_rating, losing_team_deviation)

        if index == total-1:
            print("Processed 100.00%")
        elif index % 100 == 0:
            print(f"Processed {round(index / total * 100, 2)}%")


    # Close the database session
    session.close()

    # Write the results to a new CSV file
    results.to_csv(write_filename, index=False)


def get_team_glicko(player_ids, game_id, session):
    # Query the Glicko ratings and deviations for the players
    query_result = session.query(
        PlayerGlicko.player_id, 
        PlayerGlicko.rating_pre, 
        PlayerGlicko.deviation_pre
    ).filter(
        PlayerGlicko.player_id.in_(player_ids),
        PlayerGlicko.game_id == game_id
    ).all()
    
    # Calculate the average rating and deviation
    total_rating = 0
    total_deviation = 0
    for player in query_result:
        total_rating += player.rating_pre
        total_deviation += player.deviation_pre
    average_rating = total_rating / len(player_ids)
    average_deviation = total_deviation / len(player_ids)
    
    return average_rating, average_deviation


def get_players_ids(game_id, session):
    # Query only the necessary columns
    player_stats = session.query(
            GamePlayerStats.game_id, 
            GamePlayerStats.player_id, 
            GamePlayerStats.team_id
        ).filter_by(game_id=game_id).all()

    # Dictionary to store team_id and their corresponding player_ids
    teams = {}
    for stats in player_stats:
        if stats.team_id not in teams:
            teams[stats.team_id] = []
        teams[stats.team_id].append(stats.player_id)

    return teams


def get_previous_game_id(player_id, current_game_id, session):
    # Get the start time of the current game
    current_game_begin_at = (
        session.query(Games.begin_at)
        .filter_by(id=current_game_id)
        .scalar()
    )

    # Check if the current game's start time was successfully retrieved
    if current_game_begin_at is None:
        return None

    # Query for the most recent game the player participated in before the current game
    previous_game = (
        session.query(GamePlayerStats)
        .join(Games, GamePlayerStats.game_id == Games.id)
        .filter(
            GamePlayerStats.player_id == player_id,
            GamePlayerStats.game_id != current_game_id,
            Games.begin_at < current_game_begin_at  # Ensure the game began before the current game
        )
        .order_by(desc(Games.begin_at))
        .first()
    )

    return previous_game.game_id if previous_game else None


def get_players_stats(player_ids, game_id, session):
    # Retrieve previous game ids for all players
    previous_game_ids = {
        player_id: get_previous_game_id(player_id, game_id, session) 
        for player_id in player_ids
    }
    
    # Filter out players with no previous game id
    previous_game_ids = {k: v for k, v in previous_game_ids.items() if v is not None}
    
    if not previous_game_ids:
        return {}
    
    # Construct complex OR condition for all (player_id, game_id) pairs
    conditions = or_(*[
        (CustomStatsMA.player_id == player_id) & (CustomStatsMA.game_id == game_id) 
        for player_id, game_id in previous_game_ids.items()
    ])
    
    # Query the database once to retrieve all relevant player statistics
    player_stats = session.query(CustomStatsMA).filter(conditions).all()
    
    # Organize results into a dictionary
    stats = {}
    for player in player_stats:
        if player.player_id not in stats:
            stats[player.player_id] = {}
        stats[player.player_id][player.ma] = player
        
    return stats


def bayes_shrink(value, N, stat, module, A=10):
    prior = getattr(module, stat+"_mean")

    if N == 0:
        value = 0

    return (A*prior + N*value) / (A+N)


def apply_parallel(df_grouped, func):
    results = []
    
    # Counter to keep track of completed rows
    completed_rows = 0
    
    def callback(future):
        nonlocal completed_rows
        result = future.result()
        results.append(result)
        completed_rows += len(result)
        if completed_rows == len(df_grouped):
            print(f"Processed 100.00%")
        elif completed_rows % 100 == 0:
            print(f"Processed {round(completed_rows / len(df_grouped) * 100, 2)}%")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(func, group) for name, group in df_grouped]
        for future in concurrent.futures.as_completed(futures):
            future.add_done_callback(callback)
    
    return pd.concat(results, ignore_index=True)


def add_stats_to_csv(df, write_filename="datasets/games_stats.csv", moments_module="feature_moments"):
    # Create a new DataFrame to store results
    results = df.copy()
    
    # Add columns for custom stats
    columns = [col.name for col in CustomStatsMA.__table__.columns if '_N' not in col.name and col.name not in ['id', 'game_id', 'player_id', 'num_rounds', 'ma']]

    new_columns = {}
    for window in WINDOWS:
        for stat in columns:
            new_columns[f'loser_team_{window}_{stat}'] = None
            new_columns[f'winner_team_{window}_{stat}'] = None

    # Convert the dictionary of new columns to a DataFrame
    new_columns_df = pd.DataFrame(new_columns, index=[0])

    # Concatenate all new columns to the original DataFrame at once
    results = pd.concat([results, new_columns_df], axis=1)

    #load bayes means
    bayes_module = importlib.import_module(moments_module)

    
    # Function to calculate stats
    def calculate_stats(row):
        session = Session()
        try:
            #game id
            game_id = int(row['id'].values[0])

            # Get player IDs for the teams
            teams = get_players_ids(game_id, session)

            # Get the previous game's player stats
            winner_team_stats = get_players_stats(teams[int(row['winner_team_id'].values[0])], game_id, session)
            loser_team_stats = get_players_stats(teams[int(row['loser_team_id'].values[0])], game_id, session)

            # Calculate and store the average stats for the winning and losing teams
            for window in WINDOWS:
                for stat in columns:
                    if winner_team_stats:
                        row[f'winner_team_{window}_{stat}'] = np.mean([bayes_shrink(getattr(player[window], stat), getattr(player[window], stat + "_N"), stat, bayes_module) for player in winner_team_stats.values()])
                    else:
                        row[f'winner_team_{window}_{stat}'] = np.nan

                    if loser_team_stats:
                        row[f'loser_team_{window}_{stat}'] = np.mean([bayes_shrink(getattr(player[window], stat), getattr(player[window], stat + "_N"), stat, bayes_module) for player in loser_team_stats.values()])
                    else:
                        row[f'loser_team_{window}_{stat}'] = np.nan
        except Exception as e:
            print("An error occurred:", str(e))
            print("Full traceback:")
            traceback.print_exc()

        session.close()

        # Set options to display all columns and rows
        '''pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        print(row)'''
            
        return row
    
    # Apply the function to each row of the DataFrame
    results = apply_parallel(results.groupby(results.index), calculate_stats)

    # Write the results to a new CSV file
    results.to_csv(write_filename, index=False)





if __name__ == "__main__":
    add_stats_to_csv(pd.read_csv("datasets/games_glicko.csv"))



   