from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
from datetime import datetime
from sqlalchemy import desc
from odds_pipeline.log import log, LEVEL_ERROR, LEVEL_WARNING

MAX_BET = 0.03


def get_kelly_bet(my_odds, book_odds, frac=0.3):
    p = 1 / float(my_odds)
    q = 1 - p
    b = float(book_odds) - 1
    return (p - q / b) * frac


def get_scaled_bet_size(kelly_bet, max_bet, book_odds, scale_function):
    kelly_bet = float(kelly_bet)
    max_bet - float(max_bet)
    book_odds = float(book_odds)
    return min(kelly_bet, max_bet * scale_function(book_odds))


def inverse_sqrt_scale(odds):
    odds = float(odds)
    return 1 / odds**0.5


def store_bet_db(match_id, team_side, team_name, bet_amount, my_odds, book_odds):
    bet_amount = float(bet_amount)
    my_odds = float(my_odds)
    book_odds = float(book_odds)
    session = Session()
    # Query to check if the Position exists
    position = session.query(Position).filter(Position.match_id == match_id).first()
    
    if position is None: #create pos
        position = Position(
            match_id=match_id, team_side=team_side, team_name=team_name, total_dollars=bet_amount,
            sw_my_odds=my_odds, sw_book_odds=book_odds, status="open"
        )
        session.add(position)
        session.flush()
    else:
        # Update existing position
        total_bets = position.total_dollars + bet_amount
        position.sw_my_odds = (position.sw_my_odds * position.total_dollars + my_odds * bet_amount) / total_bets
        position.sw_book_odds = (position.sw_book_odds * position.total_dollars + book_odds * bet_amount) / total_bets
        position.total_dollars = total_bets

    bet = Bet(
        match_id=match_id, team_side=team_side, team_name=team_name, position_id=position.id,
        dollars=bet_amount, my_odds=my_odds, book_odds=book_odds, date_placed=datetime.now()
    )
    session.add(bet)

    session.commit()
    session.close()


def close_bet_db(match_id, status):
    session = Session()

    # Query the Position
    position = session.query(Position).filter(Position.match_id == match_id).first()
    if not position:
        # Handle the case where no position is found
        log(f"No position found for match_id: {match_id}", LEVEL_ERROR)
        session.close()
        return

    # Query the most recent PinnacleMoneylines for the match_id
    pinnacle_line = session.query(PinnacleMoneylines).filter(
        PinnacleMoneylines.match_id == match_id
    ).order_by(desc(PinnacleMoneylines.date)).first()

    if not pinnacle_line:
        # Handle the case where no PinnacleMoneylines record is found
        log(f"No PinnacleMoneylines record found for match_id: {match_id}", LEVEL_ERROR)
        session.close()
        return

    # Determine the closing line based on team_side
    if position.team_side.lower() == 'home':
        closing_line = pinnacle_line.home_line
    elif position.team_side.lower() == 'away':
        closing_line = pinnacle_line.away_line
    elif position.team_side.lower() == 'draw':
        closing_line = pinnacle_line.draw_line
    else:
        log("Invalid team_side in position", LEVEL_ERROR)
        session.close()
        return

    # Calculate CLV and other metrics
    position.closing_line = closing_line
    position.clv = position.sw_my_odds - closing_line
    position.clv_percentage = (position.sw_my_odds / closing_line) - 1

    # Calculate NV CLV Percentage
    prob_closing = 1 / closing_line
    nv_prob = prob_closing / (1 + pinnacle_line.hold)
    nv_closing_line = 1 / nv_prob
    position.nv_clv_percentage = (position.sw_my_odds / nv_closing_line) - 1

    # Update the status and other calculations as necessary
    if status.lower() == "won":
        position.return_dollar = (position.sw_book_odds - 1) * position.total_dollars
        position.return_percentage = position.return_dollar / position.total_dollars
    elif status.lower() == "lost":
        position.return_dollar = -1 * position.total_dollars
        position.return_percentage = -1
    elif status.lower() == "push":
        position.return_dollar = 0
        position.return_percentage = 0
    else:
        log("Invalid status for closing bet", LEVEL_ERROR)
        session.close()
        return

    position.status = status

    # Commit the changes
    session.commit()
    session.close()


def get_adjusted_bet_size(match_id, my_odds, book_odds, max_bet=MAX_BET):
    my_odds = float(my_odds)
    book_odds = float(book_odds)
    session = Session()
    position = session.query(Position).filter(Position.match_id == match_id).first()
    bankroll = session.query(Bankroll).order_by(desc(Bankroll.date)).first()
    session.close()

    if position is None:
        # If no position exists, the entire scaled bet size is available
        kelly_bet = get_kelly_bet(my_odds, book_odds)
        scaled_bet_size = get_scaled_bet_size(kelly_bet, max_bet, book_odds, inverse_sqrt_scale)
        return scaled_bet_size

    # Calculate the current bet size and the maximum possible bet size
    current_bet_size = position.total_dollars / bankroll.total_balance #in %
    kelly_bet = get_kelly_bet(my_odds, book_odds)
    max_possible_bet_size = get_scaled_bet_size(kelly_bet, max_bet, book_odds, inverse_sqrt_scale)

    # Determine how much more can be bet
    additional_bet_size = max_possible_bet_size - current_bet_size
    return additional_bet_size if additional_bet_size > 0 else 0


def get_bet_dollars(bet_size):
    bet_size = float(bet_size)
    session = Session()
    bankroll = session.query(Bankroll).order_by(desc(Bankroll.date)).first()
    session.close()
    return bankroll.total_balance * bet_size


def bank_to_pinny(amount):
    session = Session()
    old_bankroll = session.query(Bankroll).order_by(desc(Bankroll.date)).first()
    new_bankroll = Bankroll(
        date=datetime.now(), total_balance=old_bankroll.total_balance, 
        pinny_balance=old_bankroll.pinny_balance+amount,
        bank_balance=old_bankroll.bank_balance-amount
    )
    session.add(new_bankroll)
    session.commit()
    session.close


def pinny_to_bank(amount):
    amount = float(amount)
    session = Session()
    old_bankroll = session.query(Bankroll).order_by(desc(Bankroll.date)).first()
    new_bankroll = Bankroll(
        date=datetime.now(), total_balance=old_bankroll.total_balance, 
        pinny_balance=old_bankroll.pinny_balance-amount,
        bank_balance=old_bankroll.bank_balance+amount
    )
    session.add(new_bankroll)
    session.commit()
    session.close


def bet_return_balance(amount): #dollar bet return positive or neg
    amount = float(amount)
    session = Session()
    old_bankroll = session.query(Bankroll).order_by(desc(Bankroll.date)).first()
    new_bankroll = Bankroll(
        date=datetime.now(), total_balance=old_bankroll.total_balance+amount, 
        pinny_balance=old_bankroll.pinny_balance+amount,
        bank_balance=old_bankroll.bank_balance
    )
    session.add(new_bankroll)
    session.commit()
    session.close


def set_bankroll_hard(total, pinny, bank):
    session = Session()
    new_bankroll = Bankroll(
        date=datetime.now(), total_balance=total, 
        pinny_balance=pinny,
        bank_balance=bank
    )
    session.add(new_bankroll)
    session.commit()
    session.close