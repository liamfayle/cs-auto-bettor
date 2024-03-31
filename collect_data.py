import subprocess
from pathlib import Path
from odds_pipeline.log import log, LEVEL_ERROR, LEVEL_WARNING

def collect_data():
    current_directory = Path(__file__).parent
    current_directory_str = str(current_directory).replace('\\', '/')

    log("Scraping BO3.gg Data")
    subprocess.run(['python', current_directory_str + '/scraper/scrape_bo3.py']) #scrape new match data from completed and ongoing events.
    log("Data up to date.")

    log("Formatting Players Stats")
    subprocess.run(['python', current_directory_str + '/bo3_stats/format_stats.py']) #format stats into features and store in db
    log("Player Stats updated.")

    log("Updating Player Glicko")
    subprocess.run(['python', current_directory_str + '/bo3_stats/glicko.py']) #update glicko ratings
    log("Glicko ratings updated.")


if __name__ == "__main__":
    collect_data()


