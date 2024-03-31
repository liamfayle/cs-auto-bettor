from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
from odds_pipeline.pinnacle_api import PinnyAPI, get_line_info
from odds_pipeline.line_api import get_bo1_prob, compute_moneyline_prob
from odds_pipeline.async_input import KBHit
import time
from collect_data import collect_data
from datetime import datetime
from odds_pipeline.capital_manager import get_adjusted_bet_size, get_bet_dollars, store_bet_db, close_bet_db
from odds_pipeline.log import log, LEVEL_ERROR, LEVEL_WARNING


class AlgoBet():
    def run(self):
        #initializes and starts algobetter
        #init pinny api
        self.pinny_api = PinnyAPI()
        self.pinny_api.create_driver(headless=False)

        self.kb = KBHit()

        log("Program Starting.")

        #Bet loop
        while 1:
            if self.kb.kbhit():
                c = self.kb.getch()
                if ord(c) == 27: # ESC
                    break

            if not self.pinny_api.is_logged_in():
                while 1:
                    self.login()
                    if self.pinny_api.is_logged_in():
                        break
                    else:
                        log("Failed to login; trying again.", level=LEVEL_WARNING)
                        time.sleep(10)

            self.pinny_api.refresh() #Refresh page
            log("Getting line info.")
            self.line_dicts = get_line_info(self.pinny_api)

            #New bet loop
            log(f"Beginning loop through lines. {len(self.line_dicts)} Lines to process.")
            for line in self.line_dicts:
                away_bo1_prob, _ = get_bo1_prob(line)
                away, draw, home = self.compute_moneylines(away_bo1_prob, line['bo_type'])
                away, draw, home = self.benter_boost(away, draw, home, line)
                value_line_side, value_line = self.check_for_value(away, draw, home, line)

                if value_line_side is None:
                    continue

                bet_amount = round(get_bet_dollars(get_adjusted_bet_size(line['match_id'], value_line, line[value_line_side + "_line"], max_bet=0.0002)), 2)

                if bet_amount == 0:
                    continue

                log(f"Found value on line.\n\t\t\t\t\t\t\t{line}\n\t\t\t\t\t\t\tRecommended Amount=${bet_amount}, Team={line[value_line_side + '_team_name']}, MyLine={round(value_line, 3)}, BookLine={line[value_line_side + '_line']}")

                pinny_bet_side = "draw"
                if value_line_side != "draw":
                    if line['swapped']:
                        pinny_bet_side = self.get_opposite(value_line_side)
                    else:
                        pinny_bet_side = value_line_side
                    pinny_bet_team = line[pinny_bet_side + "_team_name"]
                pinny_bet_odds = line[pinny_bet_side + "_line"]

                self.pinny_api.clear_bet_slip()
                line_card = self.pinny_api.get_line(
                    line['away_team_name'] if not line['swapped'] else line['home_team_name'], 
                    line['home_team_name'] if not line['swapped'] else line['away_team_name'],
                    line['event_name']
                    )

                success_bet = self.pinny_api.bet_line(
                    line_card, 
                    pinny_bet_side,
                    pinny_bet_team,
                    pinny_bet_odds,
                    bet_amount
                )

                if success_bet > 0:
                    log(f'Bet line on team {line[value_line_side + "_team_name"]} with line_dict {line}')
                    store_bet_db(line['match_id'], value_line_side, line[value_line_side + "_team_name"], success_bet, value_line, line[value_line_side + "_line"])

            collect_data()
            
        self.pinny_api.kill_driver()

    def login(self):
        self.pinny_api.load_url()
        self.pinny_api.login()
        self.pinny_api.refresh()

    def compute_moneylines(self, away_bo1_prob, bo_type):
        moneylines = compute_moneyline_prob(away_bo1_prob, bo_type)

        if len(moneylines) == 2:
            return 1/float(moneylines[0]), None, 1/float(moneylines[1])
        
        return [1/float(x) for x in moneylines]

    def check_for_value(self, away, draw, home, line):
        away_ev = self.calc_ev(1/away if away is not None and away > 0 else None, line['away_line'])
        home_ev = self.calc_ev(1/home if home is not None and home > 0 else None, line['home_line'])
        draw_ev = self.calc_ev(1/draw if draw is not None and draw > 0 else None, line['draw_line'])
        ev_values = {"away": away_ev, "home": home_ev, "draw": draw_ev}
        largest_ev = max(ev_values, key=ev_values.get)
        if ev_values[largest_ev] > 0:
            if largest_ev == "away":
                return largest_ev, away
            if largest_ev == "home":
                return largest_ev, home
            if largest_ev == "draw":
                return largest_ev, draw
        return None, None

    def calc_ev(self, win_prob, market_odds):
        if win_prob is None or market_odds is None:
            return -1
        return (float(win_prob) * (float(market_odds)-1)) - (1-float(win_prob))

    def get_opposite(self, side):
        if side == "away":
            return "home"
        return "away"

    def benter_boost(self, away, draw, home, line, mf=0.70): #Market Fraction = mf
        away_new = float(line['away_line']) if line['away_line'] is not None else None
        home_new = float(line['home_line']) if line['home_line'] is not None else None
        draw_new = float(line['draw_line']) if line['draw_line'] is not None else None
        if away is not None and line['away_line'] is not None and line['hold'] is not None:
            away_new = (1-mf) * float(away) + mf * self.remove_hold(line['away_line'], line['hold'])
        if home is not None and line['home_line'] is not None and line['hold'] is not None:
            home_new = (1-mf) * float(home) + mf * self.remove_hold(line['home_line'], line['hold'])
        if draw is not None and line['draw_line'] is not None and line['hold'] is not None:
            draw_new = (1-mf) * float(draw) + mf * self.remove_hold(line['draw_line'], line['hold'])
        return away_new, draw_new, home_new

    def remove_hold(self, line, hold):
        line = float(line)
        hold = float(hold)
        p = 1 / line
        nv_p = p / (1+hold)
        return 1 / nv_p

if __name__ == "__main__":
    algo_bet = AlgoBet()
    algo_bet.run()
