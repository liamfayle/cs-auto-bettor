from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from sqlalchemy import create_engine, Column, Integer, String, Float, BigInteger, ForeignKey, Date, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from scraper.constants import DATABASE_URL


Base = declarative_base()

#BO3 API TABLES HERE

class Events(Base):
    __tablename__ = 'events'
    
    #Columns
    id = Column(BigInteger, primary_key=True)
    slug = Column(String)
    name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    prize = Column(Float)
    event_type = Column(String)
    tier = Column(String)
    tier_rank = Column(Integer)
    status = Column(String)
    country_id = Column(BigInteger, ForeignKey('countries.id'))  # Assuming there's a 'countries' table
    region_id = Column(BigInteger, ForeignKey('regions.id'))  # Assuming there's a 'regions' table
    city = Column(String)  
    number_matches = Column(Integer)
    matches_parsed = Column(Boolean)

    # Relationships
    prizes = relationship("Prizes", backref="events")
    matches = relationship("Matches", backref="events")

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            slug=data.get('slug'),
            name=data.get('name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            prize=data.get('prize'),
            event_type=data.get('event_type'),
            tier=data.get('tier'),
            tier_rank=data.get('tier_rank'),
            status=data.get('status'),
            country_id=data.get('country_id'),
            region_id=data.get('region_id'),
            city=data.get('city'),
            number_matches=data.get('number_matches'),
            matches_parsed=data.get('matches_parsed')
        )

class Prizes(Base):
    __tablename__ = 'prizes'

    #Columns
    id = Column(BigInteger, primary_key=True)
    money = Column(Float)
    place = Column(String)
    team_id = Column(BigInteger, ForeignKey('teams.id'))  
    event_id = Column(BigInteger, ForeignKey('events.id'))  

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            money=data.get('money'),
            place=data.get('place'),
            team_id=data.get('team_id'),
            event_id=data.get('event_id')
        )

class Regions(Base):
    __tablename__ = 'regions'

    #Columns
    id = Column(BigInteger, primary_key=True)
    slug = Column(String)
    name = Column(String)
    
    # Relationships
    countries = relationship("Countries", backref="regions")

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            slug=data.get('slug'),
            name=data.get('name')
        )

class Countries(Base):
    __tablename__ = 'countries'

    id = Column(BigInteger, primary_key=True)
    code = Column(String)
    name = Column(String)
    region_id = Column(BigInteger, ForeignKey('regions.id'))  # Linking to the 'regions' table

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            code=data.get('code'),
            name=data.get('name'),
            region_id=data.get('region_id')
        )

class Teams(Base):
    __tablename__ = 'teams'

    #Columns
    id = Column(BigInteger, primary_key=True)
    slug = Column(String)
    name = Column(String)
    
    # Relationships
    players = relationship("Players", backref="teams")

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            slug=data.get('slug'),
            name=data.get('name')
        )

class Matches(Base):
    __tablename__ = 'matches'
    
    #Columns
    id = Column(BigInteger, primary_key=True)
    slug = Column(String)
    away_team_id = Column(BigInteger, ForeignKey('teams.id'))
    home_team_id = Column(BigInteger, ForeignKey('teams.id'))
    winner_team_id = Column(BigInteger, ForeignKey('teams.id'))
    loser_team_id = Column(BigInteger, ForeignKey('teams.id'))
    event_id = Column(BigInteger, ForeignKey('events.id'))
    away_score = Column(Integer)
    home_score = Column(Integer)
    bo_type = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    tier = Column(String)
    tier_rank = Column(Integer)
    game_version = Column(Integer)
    
    #Relationships
    games = relationship("Games", backref="matches") 
    

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            slug=data.get('slug'),
            away_team_id=data.get('away_team_id'),
            home_team_id=data.get('home_team_id'),
            winner_team_id=data.get('winner_team_id'),
            loser_team_id=data.get('loser_team_id'),
            event_id=data.get('event_id'),
            away_score=data.get('away_score'),
            home_score=data.get('home_score'),
            bo_type=data.get('bo_type'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            tier=data.get('tier'),
            tier_rank=data.get('tier_rank'),
            game_version=data.get('game_version')
        )

class Games(Base):
    __tablename__ = 'games'

    id = Column(BigInteger, primary_key=True)
    match_id = Column(BigInteger, ForeignKey('matches.id'))
    begin_at = Column(DateTime)
    map_name = Column(String)
    duration = Column(BigInteger)  # Assuming duration is in seconds, so storing as an Integer
    winner_team_score = Column(Integer)
    loser_team_score = Column(Integer)
    status = Column(String)
    number = Column(Integer)
    rounds_count = Column(Integer)
    winner_team_id = Column(BigInteger, ForeignKey('teams.id'))
    loser_team_id = Column(BigInteger, ForeignKey('teams.id'))
    
    # Relationships
    rounds = relationship("Rounds", backref="games")
    player_stats = relationship("GamePlayerStats", backref="games")

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            match_id=data.get('match_id'),
            begin_at=data.get('begin_at'),
            map_name=data.get('map_name'),
            duration=data.get('duration'),
            winner_team_score=data.get('winner_team_score'),
            loser_team_score=data.get('loser_team_score'),
            status=data.get('status'),
            number=data.get('number'),
            rounds_count=data.get('rounds_count'),
            winner_team_id=data.get('winner_team_id'),
            loser_team_id=data.get('loser_team_id')
        )

class Rounds(Base):
    __tablename__ = 'rounds'

    id = Column(BigInteger, primary_key=True)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    round_number = Column(Integer)
    round_duration = Column(BigInteger)
    end_reason = Column(String)
    winner_team_side = Column(String)
    winner_team_score = Column(Integer)
    winner_team_name = Column(String)
    loser_team_side = Column(String)
    loser_team_score = Column(Integer)
    loser_team_name = Column(String)
    loser_team_id = Column(BigInteger, ForeignKey('teams.id'))
    winner_team_id = Column(BigInteger, ForeignKey('teams.id')) 

    # Relationships
    team_stats = relationship('RoundTeamStats', backref="rounds")
    player_stats = relationship("RoundPlayerStats", backref="rounds")

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            game_id=data.get('game_id'),
            round_number=data.get('round_number'),
            round_duration=data.get('round_duration'),
            end_reason=data.get('end_reason'),
            winner_team_side=data.get('winner_team_side'),
            winner_team_score=data.get('winner_team_score'),
            winner_team_name=data.get('winner_team_name'),
            loser_team_side=data.get('loser_team_side'),
            loser_team_score=data.get('loser_team_score'),
            loser_team_name=data.get('loser_team_name'),
            winner_team_id=data.get('winner_team_id'),
            loser_team_id=data.get('loser_team_id')
        )

class Players(Base):
    __tablename__ = 'players'

    id = Column(BigInteger, primary_key=True)
    slug = Column(String)
    nickname = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    team_id = Column(BigInteger, ForeignKey('teams.id'))  # Assuming there's a 'teams' table
    country_id = Column(BigInteger, ForeignKey('countries.id'))  # Assuming there's a 'countries' table

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            slug=data.get('slug'),
            nickname=data.get('nickname'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            team_id=data.get('team_id'),
            country_id=data.get('country_id'),
        )

class GamePlayerStats(Base):
    __tablename__ = 'game_player_stats'

    id = Column(BigInteger, primary_key=True)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    player_id = Column(BigInteger, ForeignKey('players.id'))
    team_name = Column(String)
    team_id = Column(BigInteger, ForeignKey('teams.id'))
    win = Column(Integer)
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    headshots = Column(Integer)
    first_kills = Column(Integer)
    first_death = Column(Integer)
    trade_kills = Column(Integer)
    traded_death = Column(Integer)
    kast = Column(Float)
    player_rating = Column(Float)
    two_k = Column(Integer)  # Using two_k as the name because 2k is not a valid variable name
    three_k = Column(Integer)
    four_k = Column(Integer)
    five_k = Column(Integer)
    adr = Column(Float)
    hits = Column(Integer)
    shots = Column(Integer)
    got_damage = Column(Float)
    damage = Column(Float)
    utility_value = Column(Float)
    money_spent = Column(Integer)
    money_save = Column(Integer)
    clutches = Column(Integer)

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            game_id=data.get('game_id'),
            player_id=data.get('player_id'),
            team_name=data.get('team_name'),
            team_id=data.get('team_id'),
            win=data.get('win'),
            kills=data.get('kills'),
            deaths=data.get('deaths'),
            assists=data.get('assists'),
            headshots=data.get('headshots'),
            first_kills=data.get('first_kills'),
            first_death=data.get('first_death'),
            trade_kills=data.get('trade_kills'),
            traded_death=data.get('traded_death'),
            kast=data.get('kast'),
            player_rating=data.get('player_rating'),
            two_k=data.get('two_k'),
            three_k=data.get('three_k'),
            four_k=data.get('four_k'),
            five_k=data.get('five_k'),
            adr=data.get('adr'),
            hits=data.get('hits'),
            shots=data.get('shots'),
            got_damage=data.get('got_damage'),
            damage=data.get('damage'),
            utility_value=data.get('utility_value'),
            money_spent=data.get('money_spent'),
            money_save=data.get('money_save'),
            clutches=data.get('clutches')
        )

class RoundTeamStats(Base):
    __tablename__ = 'round_team_stats'

    id = Column(BigInteger, primary_key=True)
    team_side = Column(String)
    round_number = Column(Integer)
    win = Column(Boolean)
    equipment_value = Column(Float)
    win_streak = Column(Integer)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    game_round_id = Column(BigInteger, ForeignKey('rounds.id'))
    team_name = Column(String)
    team_id = Column(BigInteger, ForeignKey('teams.id'))
    damage = Column(Float)
    kast_scores_sum = Column(Integer)
    players_count = Column(Integer)
    kills = Column(Integer)
    death = Column(Integer)
    assists = Column(Integer)
    headshots = Column(Integer)
    first_kills = Column(Integer)
    first_death = Column(Integer)
    trade_kills = Column(Integer)
    traded_death = Column(Integer)
    lose_streak = Column(Integer)
    got_damage = Column(Float)
    clutches = Column(Integer)
    utility_value = Column(Integer)
    flash_assists = Column(Integer)
    hits = Column(Integer)
    shots = Column(Integer)
    grenades_damage = Column(Float)
    money_spent = Column(Float)
    money_save = Column(Float)
    bomb_plant_attempts = Column(Integer)
    bomb_plants = Column(Integer)
    bomb_plant_fakes = Column(Integer)
    bomb_plant_deaths = Column(Integer)
    bomb_defuse_attempts = Column(Integer)
    bomb_defuses = Column(Integer)
    bomb_defuse_fakes = Column(Integer)
    bomb_defuse_deaths = Column(Integer)
    smoke_covered_enemies = Column(Integer)
    got_grenades_damage = Column(Float)
    cumulative_wins = Column(Integer)
    cumulative_kills = Column(Integer)
    cumulative_deaths = Column(Integer)
    cumulative_damage = Column(Float)
    cumulative_assists = Column(Integer)
    enemy_equipment_value = Column(Float)
    enemy_team_name = Column(String)
    enemy_team_id = Column(BigInteger, ForeignKey('teams.id'))
    clutch_attempts = Column(Integer)
    clutch_attempts_vs = Column(Integer)
    clutches_vs = Column(Integer)
    pistol_round = Column(Boolean)

    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get('id'),
            team_side=data.get('team_side'),
            round_number=data.get('round_number'),
            win=data.get('win'),
            equipment_value=data.get('equipment_value'),
            win_streak=data.get('win_streak'),
            game_id=data.get('game_id'),
            game_round_id=data.get('game_round_id'),
            team_name=data.get('team_name'),
            team_id=data.get('team_id'),
            damage=data.get('damage'),
            kast_scores_sum=data.get('kast_scores_sum'),
            players_count=data.get('players_count'),
            kills=data.get('kills'),
            death=data.get('death'),
            assists=data.get('assists'),
            headshots=data.get('headshots'),
            first_kills=data.get('first_kills'),
            first_death=data.get('first_death'),
            trade_kills=data.get('trade_kills'),
            traded_death=data.get('traded_death'),
            lose_streak=data.get('lose_streak'),
            got_damage=data.get('got_damage'),
            clutches=data.get('clutches'),
            utility_value=data.get('utility_value'),
            flash_assists=data.get('flash_assists'),
            hits=data.get('hits'),
            shots=data.get('shots'),
            grenades_damage=data.get('grenades_damage'),
            money_spent=data.get('money_spent'),
            money_save=data.get('money_save'),
            bomb_plant_attempts=data.get('bomb_plant_attempts'),
            bomb_plants=data.get('bomb_plants'),
            bomb_plant_fakes=data.get('bomb_plant_fakes'),
            bomb_plant_deaths=data.get('bomb_plant_deaths'),
            bomb_defuse_attempts=data.get('bomb_defuse_attempts'),
            bomb_defuses=data.get('bomb_defuses'),
            bomb_defuse_fakes=data.get('bomb_defuse_fakes'),
            bomb_defuse_deaths=data.get('bomb_defuse_deaths'),
            smoke_covered_enemies=data.get('smoke_covered_enemies'),
            got_grenades_damage=data.get('got_grenades_damage'),
            cumulative_wins=data.get('cumulative_wins'),
            cumulative_kills=data.get('cumulative_kills'),
            cumulative_deaths=data.get('cumulative_deaths'),
            cumulative_damage=data.get('cumulative_damage'),
            cumulative_assists=data.get('cumulative_assists'),
            enemy_equipment_value=data.get('enemy_equipment_value'),
            enemy_team_name=data.get('enemy_team_name'),
            enemy_team_id=data.get('enemy_team_id'),
            clutch_attempts=data.get('clutch_attempts'),
            clutch_attempts_vs=data.get('clutch_attempts_vs'),
            clutches_vs=data.get('clutches_vs'),
            pistol_round=data.get('pistol_round')
        )

class RoundPlayerStats(Base):
    __tablename__ = 'round_player_stats'

    id = Column(BigInteger, primary_key=True)
    round_number = Column(Integer)
    win = Column(Boolean)
    kills = Column(Integer)
    death = Column(Integer)
    assists = Column(Integer)
    headshots = Column(Integer)
    first_kills = Column(Integer)
    first_death = Column(Integer)
    trade_kills = Column(Integer)
    traded_death = Column(Integer)  
    kast_score = Column(Integer)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    game_round_id = Column(BigInteger, ForeignKey('rounds.id'))
    player_id = Column(BigInteger, ForeignKey('players.id'))
    team_name = Column(String)
    team_id = Column(BigInteger, ForeignKey('teams.id'))
    enemy_team_name = Column(String)
    damage = Column(Float)
    hits = Column(Integer)
    shots = Column(Integer)
    cumulative_damage = Column(Float)
    got_damage = Column(Float)
    utility_value = Column(Integer)
    money_spent = Column(Float)
    money_save = Column(Float)
    team_side = Column(String)
    cumulative_kills = Column(Integer)
    cumulative_death = Column(Integer)
    cumulative_assists = Column(Integer)
    cumulative_kast_score = Column(Integer)
    cumulative_kast = Column(Integer)
    clutches = Column(Integer)
    pistol_round = Column(Boolean)
    movement_distance = Column(Float)
    avg_team_distance = Column(Float)
    bomb_plant_attempts = Column(Integer)
    bomb_plants = Column(Integer)
    bomb_plant_fakes = Column(Integer)
    bomb_plant_deaths = Column(Integer)
    bomb_defuse_attempts = Column(Integer)
    bomb_defuses = Column(Integer)
    bomb_defuse_fakes = Column(Integer)
    bomb_defuse_deaths = Column(Integer)
    smoke_covered_enemies = Column(Integer)
    grenades_damage = Column(Float)
    flash_assists = Column(Integer)
    got_grenades_damage = Column(Float)
    avg_enemy_equipment_value = Column(Float)
    cumulative_wins = Column(Integer)
    wall_bang_kills = Column(Integer)
    no_scope_kills = Column(Integer)
    flash_assisted_kills = Column(Integer)
    blinded_kills = Column(Integer)
    clutch_attempts = Column(Integer)
    clutch_attempts_vs = Column(Integer)
    clutches_vs = Column(Integer)

    # Additional columns for multikills and clutch stats
    multikills_2k = Column(Integer)
    multikills_3k = Column(Integer)
    multikills_4k = Column(Integer)
    multikills_5k = Column(Integer)
    clutches_1v1 = Column(Integer)
    clutches_1v2 = Column(Integer)
    clutches_1v3 = Column(Integer)
    clutches_1v4 = Column(Integer)
    clutches_1v5 = Column(Integer)


    @classmethod
    def add_instance(cls, data):
        return cls(
            id=data.get("id"),
            round_number=data.get("round_number"),
            win=data.get("win"),
            kills=data.get("kills"),
            death=data.get("death"),
            assists=data.get("assists"),
            headshots=data.get("headshots"),
            first_kills=data.get("first_kills"),
            first_death=data.get("first_death"),
            trade_kills=data.get("trade_kills"),
            traded_death=data.get("traded_death"),
            kast_score=data.get("kast_score"),
            game_id=data.get("game_id"),
            game_round_id=data.get("game_round_id"),
            player_id=data.get("player_id"),
            team_name=data.get("team_name"),
            team_id=data.get("team_id"),
            enemy_team_name=data.get("enemy_team_name"),
            damage=data.get("damage"),
            hits=data.get("hits"),
            shots=data.get("shots"),
            cumulative_damage=data.get("cumulative_damage"),
            got_damage=data.get("got_damage"),
            utility_value=data.get("utility_value"),
            money_spent=data.get("money_spent"),
            money_save=data.get("money_save"),
            team_side=data.get("team_side"),
            cumulative_kills=data.get("cumulative_kills"),
            cumulative_death=data.get("cumulative_death"),
            cumulative_assists=data.get("cumulative_assists"),
            cumulative_kast_score=data.get("cumulative_kast_score"),
            cumulative_kast=data.get("cumulative_kast"),
            clutches=data.get("clutches"),
            pistol_round=data.get("pistol_round"),
            movement_distance=data.get("movement_distance"),
            avg_team_distance=data.get("avg_team_distance"),
            bomb_plant_attempts=data.get("bomb_plant_attempts"),
            bomb_plants=data.get("bomb_plants"),
            bomb_plant_fakes=data.get("bomb_plant_fakes"),
            bomb_plant_deaths=data.get("bomb_plant_deaths"),
            bomb_defuse_attempts=data.get("bomb_defuse_attempts"),
            bomb_defuses=data.get("bomb_defuses"),
            bomb_defuse_fakes=data.get("bomb_defuse_fakes"),
            bomb_defuse_deaths=data.get("bomb_defuse_deaths"),
            smoke_covered_enemies=data.get("smoke_covered_enemies"),
            grenades_damage=data.get("grenades_damage"),
            flash_assists=data.get("flash_assists"),
            got_grenades_damage=data.get("got_grenades_damage"),
            avg_enemy_equipment_value=data.get("avg_enemy_equipment_value"),
            cumulative_wins=data.get("cumulative_wins"),
            wall_bang_kills=data.get("wall_bang_kills"),
            no_scope_kills=data.get("no_scope_kills"),
            flash_assisted_kills=data.get("flash_assisted_kills"),
            blinded_kills=data.get("blinded_kills"),
            clutch_attempts=data.get("clutch_attempts"),
            clutch_attempts_vs=data.get("clutch_attempts_vs"),
            clutches_vs=data.get("clutches_vs"),
            multikills_2k=data.get("multikills_2k"),
            multikills_3k=data.get("multikills_3k"),
            multikills_4k=data.get("multikills_4k"),
            multikills_5k=data.get("multikills_5k"),
            clutches_1v1=data.get("clutches_1v1"),
            clutches_1v2=data.get("clutches_1v2"),
            clutches_1v3=data.get("clutches_1v3"),
            clutches_1v4=data.get("clutches_1v4"),
            clutches_1v5=data.get("clutches_1v5"),
        )


#CUSTOM PLAYER STATS & GLICKO

class CustomPlayerStatsGame(Base):
    __tablename__ = 'custom_player_stats_game'

    id = Column(BigInteger, primary_key=True)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    player_id = Column(BigInteger, ForeignKey('players.id'))
    num_rounds = Column(Integer)


    '''
    EXTENSIONS

    >Momentum Factor
    >Map Factors / Pooling
    >Historical Performance Stat (ie track how players did vs other players)
    '''

    # General stats
    kpr = Column(Float, comment="Kill per round")
    tdp = Column(Float, comment="% Share of team damage")
    kdr = Column(Float, comment="Kill Death Ratio")
    spr = Column(Float, comment="Survival per round")
    dpr = Column(Float, comment="Death per round")
    adr = Column(Float, comment="Average Damage per round")
    apr = Column(Float, comment="Assist per round")
    fkr = Column(Float, comment="First kills per round")
    fdr = Column(Float, comment="First deaths per round")
    odpr = Column(Float, comment="Opening Duel per round")
    odwr = Column(Float, comment="Opening Duel Win Rate")
    hsp = Column(Float, comment="Headshot Percentage")
    kast = Column(Float, comment="Average KAST per round")
    rwpr = Column(Float, comment="Conversion [round win] per round")
    kpr2 = Column(Float, comment="Average double kills per round")
    kpr3 = Column(Float, comment="Average triple kills per round")
    kpr4 = Column(Float, comment="Average quad kills per round")
    kpr5 = Column(Float, comment="Average penta kills per round")
    cr = Column(Float, comment="Clutch Rate")
    wcr = Column(Float, comment="Weighted Clutch Rate")
    tkpr = Column(Float, comment="Trade kills per round")
    tkr = Column(Float, comment="Trade kills rate")
    nkr = Column(Float, comment="normal kills rate")
    tddr = Column(Float, comment="Traded death per death")
    ei = Column(Float, comment="Economic Efficiency")
    mis = Column(Float, comment="Multikill index score")
    ac = Column(Float, comment="Accuracy")
    cpd = Column(Float, comment="Cost Per damage")
    evspr = Column(Float, comment="Equipment Value Saved per Round")
    evsos = Column(Float, comment="Equipment Value Saved over spent")
    bpk = Column(Float, comment="Bullets per Kill")
    fapr = Column(Float, comment="Flash Assists per Round")
    udpr = Column(Float, comment="Utility Damage per Round")
    udpi = Column(Float, comment="Utility Damage per Investment")
    cv = Column(Float, comment="clutches given up")
    dtpr = Column(Float, comment="Damage Taken per Round") #BELOW are game stats only
    bppa = Column(Float, comment="Bomb Plants per Attempt")
    bdpa = Column(Float, comment="Bomb Defuse per Attempt")
    '''act = Column(Float, comment="Average Cohesion Time")
    hthr = Column(Float, comment="heasd to head rounds (A + rounds_won / A + rounds_lost)")
    time_since_last_match = Column(Float, comment="Time Since Last Match")
    maps_played_last_30d = Column(Integer, comment="Matches Played in Last 30 Days")''' #Not sure how to implement this (will come back if need to refine model)

    # T-side stats
    kpr_T = Column(Float, comment="Kill per round (T side)")
    kdr_T = Column(Float, comment="Kill Death Ratio (T side)")
    tdp_T = Column(Float, comment="% Share of team damage")
    spr_T = Column(Float, comment="Survival per round (T side)")
    dpr_T = Column(Float, comment="Death per round (T side)")
    adr_T = Column(Float, comment="Average Damage per round (T side)")
    apr_T = Column(Float, comment="Assist per round (T side)")
    fkr_T = Column(Float, comment="First kills per round (T side)")
    fdr_T = Column(Float, comment="First deaths per round (T side)")
    odpr_T = Column(Float, comment="Opening Duel per rate (T side)")
    odwr_T = Column(Float, comment="Opening Duel Win Rate (T side)")
    hsp_T = Column(Float, comment="Headshot Percentage (T side)")
    kast_T = Column(Float, comment="Average KAST per round (T side)")
    rwpr_T = Column(Float, comment="Conversion [round win] per round (T side)")
    kpr2_T = Column(Float, comment="Average double kills per round (T side)")
    kpr3_T = Column(Float, comment="Average triple kills per round (T side)")
    kpr4_T = Column(Float, comment="Average quad kills per round (T side)")
    kpr5_T = Column(Float, comment="Average penta kills per round (T side)")
    cr_T = Column(Float, comment="Clutch rate (per attempt) (T side)")
    wcr_T = Column(Float, comment="Weighted Clutch Rate")
    tkpr_T = Column(Float, comment="Trade kills per round (T side)")
    tkr_T = Column(Float, comment="Trade kills rate (T side)")
    nkr_T = Column(Float, comment="Normal kills rate (T side)")
    tddr_T = Column(Float, comment="Traded death per death (T side)")
    ei_T = Column(Float, comment="Economic Efficiency (T side)")
    mis_T = Column(Float, comment="Multiplier for multikills (T side)")
    ac_T = Column(Float, comment="Accuracy (T side)")
    cpd_T = Column(Float, comment="Cost Per damage (T side)")
    evspr_T = Column(Float, comment="Equipment Value Saved per Round (T side)")
    evsos_T = Column(Float, comment="Equipment Value Saved over spent")
    bpk_T = Column(Float, comment="Bullets per Kill (T side)")
    fapr_T = Column(Float, comment="Flash Assists per Round (T side)")
    udpr_T = Column(Float, comment="Utility Damage per Round (T side)")
    udpi_T = Column(Float, comment="Utility Damage per Investment (T side)")
    cv_T = Column(Float, comment="Lost Clutches per Attempt (T side)")
    dtpr_T = Column(Float, comment="Damage Taken per Round (T side)")

    # CT-side stats
    kpr_CT = Column(Float, comment="Kill per round (CT side)")
    kdr_CT = Column(Float, comment="Kill Death Ratio (CT side)")
    spr_CT = Column(Float, comment="Survival per round (CT side)")
    tdp_CT = Column(Float, comment="% Share of team damage")
    dpr_CT = Column(Float, comment="Death per round (CT side)")
    adr_CT = Column(Float, comment="Average Damage per round (CT side)")
    apr_CT = Column(Float, comment="Assist per round (CT side)")
    fkr_CT = Column(Float, comment="First kills per round (CT side)")
    fdr_CT = Column(Float, comment="First deaths per round (CT side)")
    odpr_CT = Column(Float, comment="Opening Duel per round (CT side)")
    odwr_CT = Column(Float, comment="Opening Duel Win Rate (CT side)")
    hsp_CT = Column(Float, comment="Headshot Percentage (CT side)")
    kast_CT = Column(Float, comment="Average KAST per round (CT side)")
    rwpr_CT = Column(Float, comment="Conversion [round win] per round (CT side)")
    kpr2_CT = Column(Float, comment="Average double kills per round (CT side)")
    kpr3_CT = Column(Float, comment="Average triple kills per round (CT side)")
    kpr4_CT = Column(Float, comment="Average quad kills per round (CT side)")
    kpr5_CT = Column(Float, comment="Average penta kills per round (CT side)")
    cr_CT = Column(Float, comment="Clutch rate (per attempt) (CT side)")
    wcr_CT = Column(Float, comment="Weighted Clutch Rate")
    tkpr_CT = Column(Float, comment="Trade kills per round (CT side)")
    tkr_CT = Column(Float, comment="Trade kills rate (CT side)")
    nkr_CT = Column(Float, comment="Normal kills rate (CT side)")
    tddr_CT = Column(Float, comment="Traded death per death (CT side)")
    ei_CT = Column(Float, comment="Economic Efficiency (CT side)")
    mis_CT = Column(Float, comment="Multiplier for multikills (CT side)")
    ac_CT = Column(Float, comment="Accuracy  (CT side)")
    cpd_CT = Column(Float, comment="Cost Per damage (CT side)")
    evspr_CT = Column(Float, comment="Equipment Value Saved per Round (CT side)")
    evsos_CT = Column(Float, comment="Equipment Value Saved over spent")
    bpk_CT = Column(Float, comment="Bullets per Kill (CT side)")
    fapr_CT = Column(Float, comment="Flash Assists per Round (CT side)")
    udpr_CT = Column(Float, comment="Utility Damage per Round (CT side)")
    udpi_CT = Column(Float, comment="Utility Damage per Investment (CT side)")
    cv_CT = Column(Float, comment="Lost Clutches per Attempt (CT side)")
    dtpr_CT = Column(Float, comment="Damage Taken per Round (CT side)")

class CustomStatsMA(Base):
    __tablename__ = 'custom_stats_ma'

    id = Column(BigInteger, primary_key=True)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    player_id = Column(BigInteger, ForeignKey('players.id'))
    num_rounds = Column(Integer)

    #IDENTIFERS
    ma = Column(String, comment="How long is MA")

    # General stats
    kpr = Column(Float, comment="Kill per round")
    tdp = Column(Float, comment="% Share of team damage")
    kdr = Column(Float, comment="Kill Death Ratio")
    spr = Column(Float, comment="Survival per round")
    dpr = Column(Float, comment="Death per round")
    adr = Column(Float, comment="Average Damage per round")
    apr = Column(Float, comment="Assist per round")
    fkr = Column(Float, comment="First kills per round")
    fdr = Column(Float, comment="First deaths per round")
    odpr = Column(Float, comment="Opening Duel per round")
    odwr = Column(Float, comment="Opening Duel Win Rate")
    hsp = Column(Float, comment="Headshot Percentage")
    kast = Column(Float, comment="Average KAST per round")
    rwpr = Column(Float, comment="Conversion [round win] per round")
    kpr2 = Column(Float, comment="Average double kills per round")
    kpr3 = Column(Float, comment="Average triple kills per round")
    kpr4 = Column(Float, comment="Average quad kills per round")
    kpr5 = Column(Float, comment="Average penta kills per round")
    cr = Column(Float, comment="Clutch Rate")
    wcr = Column(Float, comment="Weighted Clutch Rate")
    tkpr = Column(Float, comment="Trade kills per round")
    tkr = Column(Float, comment="Trade kills rate")
    nkr = Column(Float, comment="normal kills rate")
    tddr = Column(Float, comment="Traded death per death")
    ei = Column(Float, comment="Economic Efficiency")
    mis = Column(Float, comment="Multikill index score")
    ac = Column(Float, comment="Accuracy")
    cpd = Column(Float, comment="Cost Per damage")
    evspr = Column(Float, comment="Equipment Value Saved per Round")
    evsos = Column(Float, comment="Equipment Value Saved over spent")
    bpk = Column(Float, comment="Bullets per Kill")
    fapr = Column(Float, comment="Flash Assists per Round")
    udpr = Column(Float, comment="Utility Damage per Round")
    udpi = Column(Float, comment="Utility Damage per Investment")
    cv = Column(Float, comment="clutches given up")
    dtpr = Column(Float, comment="Damage Taken per Round") #BELOW are game stats only
    bppa = Column(Float, comment="Bomb Plants per Attempt")
    bdpa = Column(Float, comment="Bomb Defuse per Attempt")

    # T-side stats
    kpr_T = Column(Float, comment="Kill per round (T side)")
    kdr_T = Column(Float, comment="Kill Death Ratio (T side)")
    tdp_T = Column(Float, comment="% Share of team damage")
    spr_T = Column(Float, comment="Survival per round (T side)")
    dpr_T = Column(Float, comment="Death per round (T side)")
    adr_T = Column(Float, comment="Average Damage per round (T side)")
    apr_T = Column(Float, comment="Assist per round (T side)")
    fkr_T = Column(Float, comment="First kills per round (T side)")
    fdr_T = Column(Float, comment="First deaths per round (T side)")
    odpr_T = Column(Float, comment="Opening Duel per rate (T side)")
    odwr_T = Column(Float, comment="Opening Duel Win Rate (T side)")
    hsp_T = Column(Float, comment="Headshot Percentage (T side)")
    kast_T = Column(Float, comment="Average KAST per round (T side)")
    rwpr_T = Column(Float, comment="Conversion [round win] per round (T side)")
    kpr2_T = Column(Float, comment="Average double kills per round (T side)")
    kpr3_T = Column(Float, comment="Average triple kills per round (T side)")
    kpr4_T = Column(Float, comment="Average quad kills per round (T side)")
    kpr5_T = Column(Float, comment="Average penta kills per round (T side)")
    cr_T = Column(Float, comment="Clutch rate (per attempt) (T side)")
    wcr_T = Column(Float, comment="Weighted Clutch Rate")
    tkpr_T = Column(Float, comment="Trade kills per round (T side)")
    tkr_T = Column(Float, comment="Trade kills rate (T side)")
    nkr_T = Column(Float, comment="Normal kills rate (T side)")
    tddr_T = Column(Float, comment="Traded death per death (T side)")
    ei_T = Column(Float, comment="Economic Efficiency (T side)")
    mis_T = Column(Float, comment="Multiplier for multikills (T side)")
    ac_T = Column(Float, comment="Accuracy (T side)")
    cpd_T = Column(Float, comment="Cost Per damage (T side)")
    evspr_T = Column(Float, comment="Equipment Value Saved per Round (T side)")
    evsos_T = Column(Float, comment="Equipment Value Saved over spent")
    bpk_T = Column(Float, comment="Bullets per Kill (T side)")
    fapr_T = Column(Float, comment="Flash Assists per Round (T side)")
    udpr_T = Column(Float, comment="Utility Damage per Round (T side)")
    udpi_T = Column(Float, comment="Utility Damage per Investment (T side)")
    cv_T = Column(Float, comment="Lost Clutches per Attempt (T side)")
    dtpr_T = Column(Float, comment="Damage Taken per Round (T side)")

    # CT-side stats
    kpr_CT = Column(Float, comment="Kill per round (CT side)")
    kdr_CT = Column(Float, comment="Kill Death Ratio (CT side)")
    spr_CT = Column(Float, comment="Survival per round (CT side)")
    tdp_CT = Column(Float, comment="% Share of team damage")
    dpr_CT = Column(Float, comment="Death per round (CT side)")
    adr_CT = Column(Float, comment="Average Damage per round (CT side)")
    apr_CT = Column(Float, comment="Assist per round (CT side)")
    fkr_CT = Column(Float, comment="First kills per round (CT side)")
    fdr_CT = Column(Float, comment="First deaths per round (CT side)")
    odpr_CT = Column(Float, comment="Opening Duel per round (CT side)")
    odwr_CT = Column(Float, comment="Opening Duel Win Rate (CT side)")
    hsp_CT = Column(Float, comment="Headshot Percentage (CT side)")
    kast_CT = Column(Float, comment="Average KAST per round (CT side)")
    rwpr_CT = Column(Float, comment="Conversion [round win] per round (CT side)")
    kpr2_CT = Column(Float, comment="Average double kills per round (CT side)")
    kpr3_CT = Column(Float, comment="Average triple kills per round (CT side)")
    kpr4_CT = Column(Float, comment="Average quad kills per round (CT side)")
    kpr5_CT = Column(Float, comment="Average penta kills per round (CT side)")
    cr_CT = Column(Float, comment="Clutch rate (per attempt) (CT side)")
    wcr_CT = Column(Float, comment="Weighted Clutch Rate")
    tkpr_CT = Column(Float, comment="Trade kills per round (CT side)")
    tkr_CT = Column(Float, comment="Trade kills rate (CT side)")
    nkr_CT = Column(Float, comment="Normal kills rate (CT side)")
    tddr_CT = Column(Float, comment="Traded death per death (CT side)")
    ei_CT = Column(Float, comment="Economic Efficiency (CT side)")
    mis_CT = Column(Float, comment="Multiplier for multikills (CT side)")
    ac_CT = Column(Float, comment="Accuracy  (CT side)")
    cpd_CT = Column(Float, comment="Cost Per damage (CT side)")
    evspr_CT = Column(Float, comment="Equipment Value Saved per Round (CT side)")
    evsos_CT = Column(Float, comment="Equipment Value Saved over spent")
    bpk_CT = Column(Float, comment="Bullets per Kill (CT side)")
    fapr_CT = Column(Float, comment="Flash Assists per Round (CT side)")
    udpr_CT = Column(Float, comment="Utility Damage per Round (CT side)")
    udpi_CT = Column(Float, comment="Utility Damage per Investment (CT side)")
    cv_CT = Column(Float, comment="Lost Clutches per Attempt (CT side)")
    dtpr_CT = Column(Float, comment="Damage Taken per Round (CT side)")

    # General stats
    kpr_N = Column(Integer, comment="Kill per round (includes amount of non NaN values in period)")
    tdp_N = Column(Integer, comment="% Share of team damage (includes amount of non NaN values in period)")
    kdr_N = Column(Integer, comment="Kill Death Ratio (includes amount of non NaN values in period)")
    spr_N = Column(Integer, comment="Survival per round (includes amount of non NaN values in period)")
    dpr_N = Column(Integer, comment="Death per round (includes amount of non NaN values in period)")
    adr_N = Column(Integer, comment="Average Damage per round (includes amount of non NaN values in period)")
    apr_N = Column(Integer, comment="Assist per round (includes amount of non NaN values in period)")
    fkr_N = Column(Integer, comment="First kills per round (includes amount of non NaN values in period)")
    fdr_N = Column(Integer, comment="First deaths per round (includes amount of non NaN values in period)")
    odpr_N = Column(Integer, comment="Opening Duel per round (includes amount of non NaN values in period)")
    odwr_N = Column(Integer, comment="Opening Duel Win Rate (includes amount of non NaN values in period)")
    hsp_N = Column(Integer, comment="Headshot Percentage (includes amount of non NaN values in period)")
    kast_N = Column(Integer, comment="Average KAST per round (includes amount of non NaN values in period)")
    rwpr_N = Column(Integer, comment="Conversion [round win] per round (includes amount of non NaN values in period)")
    kpr2_N = Column(Integer, comment="Average double kills per round (includes amount of non NaN values in period)")
    kpr3_N = Column(Integer, comment="Average triple kills per round (includes amount of non NaN values in period)")
    kpr4_N = Column(Integer, comment="Average quad kills per round (includes amount of non NaN values in period)")
    kpr5_N = Column(Integer, comment="Average penta kills per round (includes amount of non NaN values in period)")
    cr_N = Column(Integer, comment="Clutch Rate (includes amount of non NaN values in period)")
    wcr_N = Column(Integer, comment="Weighted Clutch Rate (includes amount of non NaN values in period)")
    tkpr_N = Column(Integer, comment="Trade kills per round (includes amount of non NaN values in period)")
    tkr_N = Column(Integer, comment="Trade kills rate (includes amount of non NaN values in period)")
    nkr_N = Column(Integer, comment="normal kills rate (includes amount of non NaN values in period)")
    tddr_N = Column(Integer, comment="Traded death per death (includes amount of non NaN values in period)")
    ei_N = Column(Integer, comment="Economic Efficiency (includes amount of non NaN values in period)")
    mis_N = Column(Integer, comment="Multikill index score (includes amount of non NaN values in period)")
    ac_N = Column(Integer, comment="Accuracy (includes amount of non NaN values in period)")
    cpd_N = Column(Integer, comment="Cost Per damage (includes amount of non NaN values in period)")
    evspr_N = Column(Integer, comment="Equipment Value Saved per Round (includes amount of non NaN values in period)")
    evsos_N = Column(Integer, comment="Equipment Value Saved over spent (includes amount of non NaN values in period)")
    bpk_N = Column(Integer, comment="Bullets per Kill (includes amount of non NaN values in period)")
    fapr_N = Column(Integer, comment="Flash Assists per Round (includes amount of non NaN values in period)")
    udpr_N = Column(Integer, comment="Utility Damage per Round (includes amount of non NaN values in period)")
    udpi_N = Column(Integer, comment="Utility Damage per Investment (includes amount of non NaN values in period)")
    cv_N = Column(Integer, comment="clutches given up (includes amount of non NaN values in period)")
    dtpr_N = Column(Integer, comment="Damage Taken per Round (includes amount of non NaN values in period)")
    bppa_N = Column(Integer, comment="Bomb Plants per Attempt (includes amount of non NaN values in period)")
    bdpa_N = Column(Integer, comment="Bomb Defuse per Attempt (includes amount of non NaN values in period)")

    # T-side stats
    kpr_T_N = Column(Integer, comment="Kill per round (T side) (includes amount of non NaN values in period)")
    kdr_T_N = Column(Integer, comment="Kill Death Ratio (T side) (includes amount of non NaN values in period)")
    tdp_T_N = Column(Integer, comment="% Share of team damage (T side) (includes amount of non NaN values in period)")
    spr_T_N = Column(Integer, comment="Survival per round (T side) (includes amount of non NaN values in period)")
    dpr_T_N = Column(Integer, comment="Death per round (T side) (includes amount of non NaN values in period)")
    adr_T_N = Column(Integer, comment="Average Damage per round (T side) (includes amount of non NaN values in period)")
    apr_T_N = Column(Integer, comment="Assist per round (T side) (includes amount of non NaN values in period)")
    fkr_T_N = Column(Integer, comment="First kills per round (T side) (includes amount of non NaN values in period)")
    fdr_T_N = Column(Integer, comment="First deaths per round (T side) (includes amount of non NaN values in period)")
    odpr_T_N = Column(Integer, comment="Opening Duel per rate (T side) (includes amount of non NaN values in period)")
    odwr_T_N = Column(Integer, comment="Opening Duel Win Rate (T side) (includes amount of non NaN values in period)")
    hsp_T_N = Column(Integer, comment="Headshot Percentage (T side) (includes amount of non NaN values in period)")
    kast_T_N = Column(Integer, comment="Average KAST per round (T side) (includes amount of non NaN values in period)")
    rwpr_T_N = Column(Integer, comment="Conversion [round win] per round (T side) (includes amount of non NaN values in period)")
    kpr2_T_N = Column(Integer, comment="Average double kills per round (T side) (includes amount of non NaN values in period)")
    kpr3_T_N = Column(Integer, comment="Average triple kills per round (T side) (includes amount of non NaN values in period)")
    kpr4_T_N = Column(Integer, comment="Average quad kills per round (T side) (includes amount of non NaN values in period)")
    kpr5_T_N = Column(Integer, comment="Average penta kills per round (T side) (includes amount of non NaN values in period)")
    cr_T_N = Column(Integer, comment="Clutch rate (per attempt) (T side) (includes amount of non NaN values in period)")
    wcr_T_N = Column(Integer, comment="Weighted Clutch Rate (T side) (includes amount of non NaN values in period)")
    tkpr_T_N = Column(Integer, comment="Trade kills per round (T side) (includes amount of non NaN values in period)")
    tkr_T_N = Column(Integer, comment="Trade kills rate (T side) (includes amount of non NaN values in period)")
    nkr_T_N = Column(Integer, comment="normal kills rate (T side) (includes amount of non NaN values in period)")
    tddr_T_N = Column(Integer, comment="Traded death per death (T side) (includes amount of non NaN values in period)")
    ei_T_N = Column(Integer, comment="Economic Efficiency (T side) (includes amount of non NaN values in period)")
    mis_T_N = Column(Integer, comment="Multikill index score (T side) (includes amount of non NaN values in period)")
    ac_T_N = Column(Integer, comment="Accuracy (T side) (includes amount of non NaN values in period)")
    cpd_T_N = Column(Integer, comment="Cost Per damage (T side) (includes amount of non NaN values in period)")
    evspr_T_N = Column(Integer, comment="Equipment Value Saved per Round (T side) (includes amount of non NaN values in period)")
    evsos_T_N = Column(Integer, comment="Equipment Value Saved over spent (T side) (includes amount of non NaN values in period)")
    bpk_T_N = Column(Integer, comment="Bullets per Kill (T side) (includes amount of non NaN values in period)")
    fapr_T_N = Column(Integer, comment="Flash Assists per Round (T side) (includes amount of non NaN values in period)")
    udpr_T_N = Column(Integer, comment="Utility Damage per Round (T side) (includes amount of non NaN values in period)")
    udpi_T_N = Column(Integer, comment="Utility Damage per Investment (T side) (includes amount of non NaN values in period)")
    cv_T_N = Column(Integer, comment="clutches given up (T side) (includes amount of non NaN values in period)")
    dtpr_T_N = Column(Integer, comment="Damage Taken per Round (T side) (includes amount of non NaN values in period)")

    # CT-side stats
    kpr_CT_N = Column(Integer, comment="Kill per round (CT side) (includes amount of non NaN values in period)")
    kdr_CT_N = Column(Integer, comment="Kill Death Ratio (CT side) (includes amount of non NaN values in period)")
    tdp_CT_N = Column(Integer, comment="% Share of team damage (CT side) (includes amount of non NaN values in period)")
    spr_CT_N = Column(Integer, comment="Survival per round (CT side) (includes amount of non NaN values in period)")
    dpr_CT_N = Column(Integer, comment="Death per round (CT side) (includes amount of non NaN values in period)")
    adr_CT_N = Column(Integer, comment="Average Damage per round (CT side) (includes amount of non NaN values in period)")
    apr_CT_N = Column(Integer, comment="Assist per round (CT side) (includes amount of non NaN values in period)")
    fkr_CT_N = Column(Integer, comment="First kills per round (CT side) (includes amount of non NaN values in period)")
    fdr_CT_N = Column(Integer, comment="First deaths per round (CT side) (includes amount of non NaN values in period)")
    odpr_CT_N = Column(Integer, comment="Opening Duel per rate (CT side) (includes amount of non NaN values in period)")
    odwr_CT_N = Column(Integer, comment="Opening Duel Win Rate (CT side) (includes amount of non NaN values in period)")
    hsp_CT_N = Column(Integer, comment="Headshot Percentage (CT side) (includes amount of non NaN values in period)")
    kast_CT_N = Column(Integer, comment="Average KAST per round (CT side) (includes amount of non NaN values in period)")
    rwpr_CT_N = Column(Integer, comment="Conversion [round win] per round (CT side) (includes amount of non NaN values in period)")
    kpr2_CT_N = Column(Integer, comment="Average double kills per round (CT side) (includes amount of non NaN values in period)")
    kpr3_CT_N = Column(Integer, comment="Average triple kills per round (CT side) (includes amount of non NaN values in period)")
    kpr4_CT_N = Column(Integer, comment="Average quad kills per round (CT side) (includes amount of non NaN values in period)")
    kpr5_CT_N = Column(Integer, comment="Average penta kills per round (CT side) (includes amount of non NaN values in period)")
    cr_CT_N = Column(Integer, comment="Clutch rate (per attempt) (CT side) (includes amount of non NaN values in period)")
    wcr_CT_N = Column(Integer, comment="Weighted Clutch Rate (CT side) (includes amount of non NaN values in period)")
    tkpr_CT_N = Column(Integer, comment="Trade kills per round (CT side) (includes amount of non NaN values in period)")
    tkr_CT_N = Column(Integer, comment="Trade kills rate (CT side) (includes amount of non NaN values in period)")
    nkr_CT_N = Column(Integer, comment="normal kills rate (CT side) (includes amount of non NaN values in period)")
    tddr_CT_N = Column(Integer, comment="Traded death per death (CT side) (includes amount of non NaN values in period)")
    ei_CT_N = Column(Integer, comment="Economic Efficiency (CT side) (includes amount of non NaN values in period)")
    mis_CT_N = Column(Integer, comment="Multikill index score (CT side) (includes amount of non NaN values in period)")
    ac_CT_N = Column(Integer, comment="Accuracy (CT side) (includes amount of non NaN values in period)")
    cpd_CT_N = Column(Integer, comment="Cost Per damage (CT side) (includes amount of non NaN values in period)")
    evspr_CT_N = Column(Integer, comment="Equipment Value Saved per Round (CT side) (includes amount of non NaN values in period)")
    evsos_CT_N = Column(Integer, comment="Equipment Value Saved over spent (CT side) (includes amount of non NaN values in period)")
    bpk_CT_N = Column(Integer, comment="Bullets per Kill (CT side) (includes amount of non NaN values in period)")
    fapr_CT_N = Column(Integer, comment="Flash Assists per Round (CT side) (includes amount of non NaN values in period)")
    udpr_CT_N = Column(Integer, comment="Utility Damage per Round (CT side) (includes amount of non NaN values in period)")
    udpi_CT_N = Column(Integer, comment="Utility Damage per Investment (CT side) (includes amount of non NaN values in period)")
    cv_CT_N = Column(Integer, comment="clutches given up (CT side) (includes amount of non NaN values in period)")
    dtpr_CT_N = Column(Integer, comment="Damage Taken per Round (CT side) (includes amount of non NaN values in period)")

class PlayerGlicko(Base):
    __tablename__ = 'player_glicko'

    id = Column(BigInteger, primary_key=True)
    game_id = Column(BigInteger, ForeignKey('games.id'))
    player_id = Column(BigInteger, ForeignKey('players.id'))
    begin_at = Column(DateTime)
    
    rating_pre = Column(Float)
    deviation_pre = Column(Float)
    vol_pre = Column(Float)

    rating_post = Column(Float)
    deviation_post = Column(Float)
    vol_post = Column(Float)


#ODDS TABLES

class PinnacleMoneylines(Base):
    __tablename__ = 'pinnacle_moneylines'

    id = Column(BigInteger, primary_key=True)
    home_team = Column(String)
    home_team_id = Column(BigInteger)
    away_team = Column(String)
    away_team_id = Column(BigInteger)
    match_id = Column(BigInteger)
    date = Column(DateTime)
    
    away_line = Column(Float)
    home_line = Column(Float)
    draw_line = Column(Float)

    hold = Column(Float)

    bo_type = Column(Integer)
    tier = Column(String)

    swapped = Column(Boolean) #indicates whether pinnacle had the away/ home teams listed backwards


class MyMoneylines(Base):
    __tablename__ = 'my_moneylines'

    id = Column(BigInteger, primary_key=True)
    home_team = Column(String)
    home_team_id = Column(BigInteger)
    away_team = Column(String)
    away_team_id = Column(BigInteger)
    match_id = Column(BigInteger)
    date = Column(DateTime)

    #Incase line is posted ahead of time and needs to be updated
    home_last_match_id = Column(BigInteger)
    away_last_match_id = Column(BigInteger)

    away_line = Column(Float)
    home_line = Column(Float)

    bo_type = Column(Integer)
    tier = Column(String)



# LIVE BETTING TABLES

class Bet(Base):
    __tablename__ = "bet"

    id = Column(BigInteger, primary_key=True)
    match_id = Column(BigInteger)
    team_side = Column(String) #home, away, draw
    team_name = Column(String)
    position_id = Column(BigInteger, ForeignKey('position.id'))
    dollars = Column(Float)
    my_odds = Column(Float)
    book_odds = Column(Float)
    date_placed = Column(DateTime)

class Position(Base):
    __tablename__ = "position"

    id = Column(BigInteger, primary_key=True)
    match_id = Column(BigInteger)
    team_side = Column(String) #home, away, draw
    team_name = Column(String)
    total_dollars = Column(Float)
    sw_my_odds = Column(Float) #sw = stake weighted
    sw_book_odds = Column(Float)
    status = Column(String) # open, won, lost
    return_dollar = Column(Float)
    return_percentage = Column(Float)
    closing_line = Column(Float)
    clv = Column(Float) #sw_my_odds - closing_line
    clv_percentage = Column(Float) #(taken line / closing line) - 1
    nv_clv_percentage = Column(Float) # (taken line / nv closing line) - 1   ###where nv closing line prob_closing = 1 / closing line ;;; nv_prob = prob_closing / (1 + hold) ;;; nv_closing_line = 1 / nv_prob


class Bankroll(Base):
    __tablename__ = "bankroll"

    id = Column(BigInteger, primary_key=True)
    date = Column(DateTime)
    total_balance = Column(Float)
    pinny_balance = Column(Float)
    bank_balance = Column(Float)
    adjustment = Column(Float) #Used if some adjustment was made that isnt a part of betting history. (ie upon reviewing i was 200 short this would be -200, and any graphs would have to sub 200 from all precending entries)

engine = create_engine(DATABASE_URL, pool_size=100, max_overflow=200)
Session = sessionmaker(bind=engine)

def init_db():
    '''
    init_db creates the database instance and lets to use the other functions
    '''
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()

