from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
import numpy as np
from sqlalchemy import and_, not_
from multiprocessing import Pool
from typing import Tuple, List
from tqdm import tqdm


def safe_value(value: any) -> any:
    '''
    Return a safe value to avoid None.

    :param value: Any value that may be None.
    
    :return: If the input value is None, returns 0; otherwise, returns the input value.
    '''
    return 0 if value is None else value


def format_stats_player_game(args: Tuple[int, int]) -> None:
    '''
    Format and store player game statistics in the database.

    :param args: A tuple containing two integers - (game_id, player_id).
    
    :return: None.
    '''
    session = Session()

    game_id, player_id = args
    rounds_player = session.query(RoundPlayerStats).filter(
        RoundPlayerStats.player_id == player_id,
        RoundPlayerStats.game_id == game_id
    ).all()

    rounds_team = []
    if len(rounds_player) > 0:
        rounds_team = session.query(RoundTeamStats).filter(
            RoundTeamStats.game_id == rounds_player[0].game_id,
        ).all()
    
    # Initialize accumulators
    total_kills = 0
    total_team_damage = 0
    total_deaths = 0
    total_assists = 0
    total_first_kills = 0
    total_first_deaths = 0
    total_headshots = 0
    total_kast = 0
    total_wins = 0
    total_2k = 0
    total_3k = 0
    total_4k = 0
    total_5k = 0
    total_clutch = 0
    total_clutch_attempt = 0
    total_1v1 = 0
    total_1v2 = 0
    total_1v3 = 0
    total_1v4 = 0
    total_1v5 = 0
    total_trade_kills = 0
    total_traded_deaths = 0
    total_ei = 0
    total_mis = 0
    total_damage = 0
    total_rounds = len(rounds_player)
    total_shots = 0
    total_hits = 0
    total_money_spent = 0
    total_money_saved = 0
    total_flash_assists = 0
    total_utility_damage = 0
    total_enemy_clutches = 0
    total_enemy_clutch_attempts = 0
    total_bomb_plants = 0
    total_bomb_plant_attempts = 0
    total_bomb_defuse = 0
    total_bomb_defuse_attempts = 0
    total_damage_against = 0

    T_kills = 0
    T_team_damage = 0
    T_deaths = 0
    T_assists = 0
    T_first_kills = 0
    T_first_deaths = 0
    T_headshots = 0
    T_kast = 0
    T_wins = 0
    T_2k = 0
    T_3k = 0
    T_4k = 0
    T_5k = 0
    T_clutch = 0
    T_clutch_attempt = 0
    T_1v1 = 0
    T_1v2 = 0
    T_1v3 = 0
    T_1v4 = 0
    T_1v5 = 0
    T_trade_kills = 0
    T_traded_deaths = 0
    T_ei = 0
    T_mis = 0
    T_damage = 0
    T_rounds = 0
    T_shots = 0
    T_hits = 0
    T_money_spent = 0
    T_money_saved = 0
    T_flash_assists = 0
    T_utility_damage = 0
    T_enemy_clutches = 0
    T_enemy_clutch_attempts = 0
    T_damage_agaisnt = 0

    CT_kills = 0
    CT_team_damage = 0
    CT_deaths = 0
    CT_assists = 0
    CT_first_kills = 0
    CT_first_deaths = 0
    CT_headshots = 0
    CT_kast = 0
    CT_wins = 0
    CT_2k = 0
    CT_3k = 0
    CT_4k = 0
    CT_5k = 0
    CT_clutch = 0
    CT_clutch_attempt = 0
    CT_1v1 = 0
    CT_1v2 = 0
    CT_1v3 = 0
    CT_1v4 = 0
    CT_1v5 = 0
    CT_trade_kills = 0
    CT_traded_deaths = 0
    CT_ei = 0
    CT_mis = 0
    CT_damage = 0
    CT_rounds = 0
    CT_shots = 0
    CT_hits = 0
    CT_money_spent = 0
    CT_money_saved = 0
    CT_flash_assists = 0
    CT_utility_damage = 0
    CT_enemy_clutches = 0
    CT_enemy_clutch_attempts = 0
    CT_damage_agaisnt = 0

    
    
    for round, team in zip(rounds_player, rounds_team):
        total_kills += safe_value(round.kills)
        total_team_damage += safe_value(team.damage)
        total_deaths += safe_value(round.death)
        total_assists += safe_value(round.assists)
        total_damage += safe_value(round.damage)
        total_first_kills += safe_value(round.first_kills)
        total_first_deaths += safe_value(round.first_death)
        total_headshots += safe_value(round.headshots)
        total_kast += safe_value(round.kast_score)
        total_wins += safe_value(round.win)
        total_2k += safe_value(round.multikills_2k)
        total_3k += safe_value(round.multikills_3k)
        total_4k += safe_value(round.multikills_4k)
        total_5k += safe_value(round.multikills_5k)
        total_clutch += safe_value(round.clutches)
        total_clutch_attempt += safe_value(round.clutch_attempts)
        total_1v1 += safe_value(round.clutches_1v1)
        total_1v2 += safe_value(round.clutches_1v2)
        total_1v3 += safe_value(round.clutches_1v3)
        total_1v4 += safe_value(round.clutches_1v4)
        total_1v5 += safe_value(round.clutches_1v5)
        total_trade_kills += safe_value(round.trade_kills)
        total_traded_deaths += safe_value(round.traded_death)
        total_ei += safe_value((team.enemy_equipment_value / team.equipment_value) * round.damage if team.enemy_equipment_value is not None and team.equipment_value is not None and team.equipment_value > 0 else round.damage)
        total_mis += safe_value(round.kills + round.kills**(np.sqrt(round.kills/5)) - 1 if round.kills is not None and round.kills >= 0 else 0)
        total_shots += safe_value(round.shots)
        total_hits += safe_value(round.hits)
        total_money_spent += safe_value(round.money_spent)
        total_money_saved += safe_value(round.money_save)
        total_flash_assists += safe_value(round.flash_assists)
        total_utility_damage += safe_value(round.grenades_damage)
        total_enemy_clutches += safe_value(round.clutches_vs)
        total_enemy_clutch_attempts += safe_value(round.clutch_attempts_vs)
        total_bomb_plants += safe_value(round.bomb_plants)
        total_bomb_plant_attempts += safe_value(round.bomb_plant_attempts)
        total_bomb_defuse += safe_value(round.bomb_defuses)
        total_bomb_defuse_attempts += safe_value(round.bomb_defuse_attempts)
        total_damage_against += safe_value(round.got_damage)

        if round.team_side == "T":
            T_kills += safe_value(round.kills)
            T_team_damage += safe_value(team.damage)
            T_deaths += safe_value(round.death)
            T_assists += safe_value(round.assists)
            T_damage += safe_value(round.damage)
            T_first_kills += safe_value(round.first_kills)
            T_first_deaths += safe_value(round.first_death)
            T_headshots += safe_value(round.headshots)
            T_kast += safe_value(round.kast_score)
            T_wins += safe_value(round.win)
            T_2k += safe_value(round.multikills_2k)
            T_3k += safe_value(round.multikills_3k)
            T_4k += safe_value(round.multikills_4k)
            T_5k += safe_value(round.multikills_5k)
            T_clutch += safe_value(round.clutches)
            T_clutch_attempt += safe_value(round.clutch_attempts)
            T_1v1 += safe_value(round.clutches_1v1)
            T_1v2 += safe_value(round.clutches_1v2)
            T_1v3 += safe_value(round.clutches_1v3)
            T_1v4 += safe_value(round.clutches_1v4)
            T_1v5 += safe_value(round.clutches_1v5)
            T_trade_kills += safe_value(round.trade_kills)
            T_traded_deaths += safe_value(round.traded_death)
            T_ei += safe_value((team.enemy_equipment_value / team.equipment_value) * round.damage if team.enemy_equipment_value is not None and team.equipment_value is not None and team.equipment_value > 0 else round.damage)
            T_mis += safe_value(round.kills + round.kills**(np.sqrt(round.kills/5)) - 1 if round.kills is not None and round.kills >= 0 else 0)
            T_shots += safe_value(round.shots)
            T_hits += safe_value(round.hits)
            T_money_spent += safe_value(round.money_spent)
            T_money_saved += safe_value(round.money_save)
            T_flash_assists += safe_value(round.flash_assists)
            T_utility_damage += safe_value(round.grenades_damage)
            T_enemy_clutches += safe_value(round.clutches_vs)
            T_enemy_clutch_attempts += safe_value(round.clutch_attempts_vs)
            T_rounds += 1
            T_damage_agaisnt += safe_value(round.got_damage)

        if round.team_side == "CT":
            CT_kills += safe_value(round.kills)
            CT_team_damage += safe_value(team.damage)
            CT_deaths += safe_value(round.death)
            CT_assists += safe_value(round.assists)
            CT_damage += safe_value(round.damage)
            CT_first_kills += safe_value(round.first_kills)
            CT_first_deaths += safe_value(round.first_death)
            CT_headshots += safe_value(round.headshots)
            CT_kast += safe_value(round.kast_score)
            CT_wins += safe_value(round.win)
            CT_2k += safe_value(round.multikills_2k)
            CT_3k += safe_value(round.multikills_3k)
            CT_4k += safe_value(round.multikills_4k)
            CT_5k += safe_value(round.multikills_5k)
            CT_clutch += safe_value(round.clutches)
            CT_clutch_attempt += safe_value(round.clutch_attempts)
            CT_1v1 += safe_value(round.clutches_1v1)
            CT_1v2 += safe_value(round.clutches_1v2)
            CT_1v3 += safe_value(round.clutches_1v3)
            CT_1v4 += safe_value(round.clutches_1v4)
            CT_1v5 += safe_value(round.clutches_1v5)
            CT_trade_kills += safe_value(round.trade_kills)
            CT_traded_deaths += safe_value(round.traded_death)
            CT_ei += safe_value((team.enemy_equipment_value / team.equipment_value) * round.damage if team.enemy_equipment_value is not None and team.equipment_value is not None and team.equipment_value > 0 else round.damage)
            CT_mis += safe_value(round.kills + round.kills**(np.sqrt(round.kills/5)) - 1 if round.kills is not None and round.kills >= 0 else 0)
            CT_shots += safe_value(round.shots)
            CT_hits += safe_value(round.hits)
            CT_money_spent += safe_value(round.money_spent)
            CT_money_saved += safe_value(round.money_save)
            CT_flash_assists += safe_value(round.flash_assists)
            CT_utility_damage += safe_value(round.grenades_damage)
            CT_enemy_clutches += safe_value(round.clutches_vs)
            CT_enemy_clutch_attempts += safe_value(round.clutch_attempts_vs)
            CT_rounds += 1
            CT_damage_agaisnt += safe_value(round.got_damage)
        
    
    # Compute statistics for CustomPlayerStatsGame
    #General STATS
    kpr = total_kills / total_rounds if total_rounds > 0 else None
    tdp = total_damage / total_team_damage if total_team_damage > 0 else None
    kdr = total_kills / total_deaths if total_deaths > 0 else None
    spr = (total_rounds - total_deaths) / total_rounds if total_rounds > 0 else None
    dpr = total_deaths / total_rounds if total_rounds > 0 else None
    adr = total_damage / total_rounds if total_rounds > 0 else None
    apr = total_assists / total_rounds if total_rounds > 0 else None
    fkr = total_first_kills / total_rounds if total_rounds > 0 else None
    fdr = total_first_deaths / total_rounds if total_rounds > 0 else None
    odpr = (total_first_deaths + total_first_kills) / total_rounds if total_rounds > 0 else None
    odwr = total_first_kills / (total_first_kills + total_first_deaths) if (total_first_deaths + total_first_kills) > 0 else None
    hsp = (total_headshots / total_kills) if total_kills > 0 else None
    kast = total_kast / total_rounds if total_rounds > 0 else None
    rwpr = total_wins / total_rounds if total_rounds > 0 else None
    kpr2 = total_2k / total_rounds if total_rounds > 0 else None
    kpr3 = total_3k / total_rounds if total_rounds > 0 else None
    kpr4 = total_4k / total_rounds if total_rounds > 0 else None
    kpr5 = total_5k / total_rounds if total_rounds > 0 else None
    cr = total_clutch / total_clutch_attempt if total_clutch_attempt > 0 else None
    wcr = (total_1v1 + 2.25*total_1v2 + 3.375*total_1v3 + 5.0625*total_1v4 + 7.59375*total_1v5)  / total_clutch_attempt if total_clutch_attempt > 0 else None
    tkpr = total_trade_kills / total_rounds if total_rounds > 0 else None
    tkr = total_trade_kills / total_kills if total_kills > 0 else None
    nkr = (total_kills - total_trade_kills) / total_kills if total_kills > 0 else None
    tddr = total_traded_deaths / total_deaths if total_deaths > 0 else None
    ei = total_ei / total_rounds if total_rounds > 0 else None
    mis = total_mis / total_rounds if total_rounds > 0 else None
    ac = total_hits / total_shots if total_shots > 0 else None
    cpd = total_money_spent / total_damage if total_damage > 0 else None
    evspr = total_money_saved / total_rounds if total_rounds > 0 else None
    evsos = total_money_saved / total_money_spent if total_money_spent > 0 else None
    bpk = total_shots / total_kills if total_kills > 0 and total_shots > 0 else None
    fapr = total_flash_assists / total_rounds if total_rounds > 0 else None
    udpr = total_utility_damage / total_rounds if total_rounds > 0 else None
    udpi = total_utility_damage / total_money_spent if total_money_spent > 0 else None
    cv = total_enemy_clutches / total_enemy_clutch_attempts if total_enemy_clutch_attempts > 0 else None
    dtpr = total_damage_against / total_rounds if total_rounds > 0 else None
    bppa = total_bomb_plants / total_bomb_plant_attempts if total_bomb_plant_attempts > 0 else None
    bdpa = total_bomb_defuse / total_bomb_defuse_attempts if total_bomb_defuse_attempts > 0 else None

    # T STATS
    kpr_T = T_kills / T_rounds if T_rounds > 0 else None
    tdp_T = T_damage / T_team_damage if T_team_damage > 0 else None
    kdr_T = T_kills / T_deaths if T_deaths > 0 else None
    spr_T = (T_rounds - T_deaths) / T_rounds if T_rounds > 0 else None
    dpr_T = T_deaths / T_rounds if T_rounds > 0 else None
    adr_T = T_damage / T_rounds if T_rounds > 0 else None
    apr_T = T_assists / T_rounds if T_rounds > 0 else None
    fkr_T = T_first_kills / T_rounds if T_rounds > 0 else None
    fdr_T = T_first_deaths / T_rounds if T_rounds > 0 else None
    odpr_T = (T_first_deaths + T_first_kills) / T_rounds if T_rounds > 0 else None
    odwr_T = T_first_kills / (T_first_kills + T_first_deaths) if (T_first_deaths + T_first_kills) > 0 else None
    hsp_T = (T_headshots / T_kills) if T_kills > 0 else None
    kast_T = T_kast / T_rounds if T_rounds > 0 else None
    rwpr_T = T_wins / T_rounds if T_rounds > 0 else None
    kpr2_T = T_2k / T_rounds if T_rounds > 0 else None
    kpr3_T = T_3k / T_rounds if T_rounds > 0 else None
    kpr4_T = T_4k / T_rounds if T_rounds > 0 else None
    kpr5_T = T_5k / T_rounds if T_rounds > 0 else None
    cr_T = T_clutch / T_clutch_attempt if T_clutch_attempt > 0 else None
    wcr_T = (T_1v1 + 2.25*T_1v2 + 3.375*T_1v3 + 5.0625*T_1v4 + 7.59375*T_1v5) / T_clutch_attempt if T_clutch_attempt > 0 else None
    tkpr_T = T_trade_kills / T_rounds if T_rounds > 0 else None
    tkr_T = T_trade_kills / T_kills if T_kills > 0 else None
    nkr_T = (T_kills - T_trade_kills) / T_kills if T_kills > 0 else None
    tddr_T = T_traded_deaths / T_deaths if T_deaths > 0 else None
    ei_T = T_ei / T_rounds if T_rounds > 0 else None
    mis_T = T_mis / T_rounds if T_rounds > 0 else None
    ac_T = T_hits / T_shots if T_shots > 0 else None
    cpd_T = T_money_spent / T_damage if T_damage > 0 else None
    evspr_T = T_money_saved / T_rounds if T_rounds > 0 else None
    evsos_T = T_money_saved / T_money_spent if T_money_spent > 0 else None
    bpk_T = T_shots / T_kills if T_kills > 0 and T_shots > 0 else None
    fapr_T = T_flash_assists / T_rounds if T_rounds > 0 else None
    udpr_T = T_utility_damage / T_rounds if T_rounds > 0 else None
    udpi_T = T_utility_damage / T_money_spent if T_money_spent > 0 else None
    cv_T = T_enemy_clutches / T_enemy_clutch_attempts if T_enemy_clutch_attempts > 0 else None
    dtpr_T = T_damage_agaisnt / T_rounds if T_rounds > 0 else None
    
    # CT STATS
    kpr_CT = CT_kills / CT_rounds if CT_rounds > 0 else None
    tdp_CT = CT_damage / CT_team_damage if CT_team_damage > 0 else None
    kdr_CT = CT_kills / CT_deaths if CT_deaths > 0 else None
    spr_CT = (CT_rounds - CT_deaths) / CT_rounds if CT_rounds > 0 else None
    dpr_CT = CT_deaths / CT_rounds if CT_rounds > 0 else None
    adr_CT = CT_damage / CT_rounds if CT_rounds > 0 else None
    apr_CT = CT_assists / CT_rounds if CT_rounds > 0 else None
    fkr_CT = CT_first_kills / CT_rounds if CT_rounds > 0 else None
    fdr_CT = CT_first_deaths / CT_rounds if CT_rounds > 0 else None
    odpr_CT = (CT_first_deaths + CT_first_kills) / CT_rounds if CT_rounds > 0 else None
    odwr_CT = CT_first_kills / (CT_first_kills + CT_first_deaths) if (CT_first_deaths + CT_first_kills) > 0 else None
    hsp_CT = (CT_headshots / CT_kills) if CT_kills > 0 else None
    kast_CT = CT_kast / CT_rounds if CT_rounds > 0 else None
    rwpr_CT = CT_wins / CT_rounds if CT_rounds > 0 else None
    kpr2_CT = CT_2k / CT_rounds if CT_rounds > 0 else None
    kpr3_CT = CT_3k / CT_rounds if CT_rounds > 0 else None
    kpr4_CT = CT_4k / CT_rounds if CT_rounds > 0 else None
    kpr5_CT = CT_5k / CT_rounds if CT_rounds > 0 else None
    cr_CT = CT_clutch / CT_clutch_attempt if CT_clutch_attempt > 0 else None
    wcr_CT = (CT_1v1 + 2.25*CT_1v2 + 3.375*CT_1v3 + 5.0625*CT_1v4 + 7.59375*CT_1v5) / CT_clutch_attempt if CT_clutch_attempt > 0 else None #uses 1.5**num kills
    tkpr_CT = CT_trade_kills / CT_rounds if CT_rounds > 0 else None
    tkr_CT = CT_trade_kills / CT_kills if CT_kills > 0 else None
    nkr_CT = (CT_kills - CT_trade_kills) / CT_kills if CT_kills > 0 else None
    tddr_CT = CT_traded_deaths / CT_deaths if CT_deaths > 0 else None
    ei_CT = CT_ei / CT_rounds if CT_rounds > 0 else None
    mis_CT = CT_mis / CT_rounds if CT_rounds > 0 else None
    ac_CT = CT_hits / CT_shots if CT_shots > 0 else None
    cpd_CT = CT_money_spent / CT_damage if CT_damage > 0 else None
    evspr_CT = CT_money_saved / CT_rounds if CT_rounds > 0 else None
    evsos_CT = CT_money_saved / CT_money_spent if CT_money_spent > 0 else None
    bpk_CT = CT_shots / CT_kills if CT_kills > 0 and CT_shots > 0 else None
    fapr_CT = CT_flash_assists / CT_rounds if CT_rounds > 0 else None
    udpr_CT = CT_utility_damage / CT_rounds if CT_rounds > 0 else None
    udpi_CT = CT_utility_damage / CT_money_spent if CT_money_spent > 0 else None
    cv_CT = CT_enemy_clutches / CT_enemy_clutch_attempts if CT_enemy_clutch_attempts > 0 else None
    dtpr_CT = CT_damage_agaisnt / CT_rounds if CT_rounds > 0 else None
    
    new_stats = CustomPlayerStatsGame(
        game_id=game_id, player_id=player_id, num_rounds=total_rounds,
        kpr=kpr, tdp=tdp, kdr=kdr, spr=spr, dpr=dpr, adr=adr, apr=apr, fkr=fkr,
        fdr=fdr, odpr=odpr, odwr=odwr, hsp=hsp, kast=kast, rwpr=rwpr, kpr2=kpr2,
        kpr3=kpr3, kpr4=kpr4, kpr5=kpr5, cr=cr, wcr=wcr, tkpr=tkpr, tkr=tkr,
        nkr=nkr, tddr=tddr, ei=ei, mis=mis, ac=ac, cpd=cpd, evspr=evspr, evsos=evsos,
        bpk=bpk, fapr=fapr, udpr=udpr, udpi=udpi, cv=cv, dtpr=dtpr, bppa=bppa,
        bdpa=bdpa, kpr_T=kpr_T, tdp_T=tdp_T, kdr_T=kdr_T, spr_T=spr_T, dpr_T=dpr_T,
        adr_T=adr_T, apr_T=apr_T, fkr_T=fkr_T, fdr_T=fdr_T, odpr_T=odpr_T, odwr_T=odwr_T,
        hsp_T=hsp_T, kast_T=kast_T, rwpr_T=rwpr_T, kpr2_T=kpr2_T, kpr3_T=kpr3_T,
        kpr4_T=kpr4_T, kpr5_T=kpr5_T, cr_T=cr_T, wcr_T=wcr_T, tkpr_T=tkpr_T,
        tkr_T=tkr_T, nkr_T=nkr_T, tddr_T=tddr_T, ei_T=ei_T, mis_T=mis_T, ac_T=ac_T,
        cpd_T=cpd_T, evspr_T=evspr_T, evsos_T=evsos_T, bpk_T=bpk_T, fapr_T=fapr_T,
        udpr_T=udpr_T, udpi_T=udpi_T, cv_T=cv_T, dtpr_T=dtpr_T, kpr_CT=kpr_CT,
        tdp_CT=tdp_CT, kdr_CT=kdr_CT, spr_CT=spr_CT, dpr_CT=dpr_CT, adr_CT=adr_CT,
        apr_CT=apr_CT, fkr_CT=fkr_CT, fdr_CT=fdr_CT, odpr_CT=odpr_CT, odwr_CT=odwr_CT,
        hsp_CT=hsp_CT, kast_CT=kast_CT, rwpr_CT=rwpr_CT, kpr2_CT=kpr2_CT, kpr3_CT=kpr3_CT,
        kpr4_CT=kpr4_CT, kpr5_CT=kpr5_CT, cr_CT=cr_CT, wcr_CT=wcr_CT, tkpr_CT=tkpr_CT,
        tkr_CT=tkr_CT, nkr_CT=nkr_CT, tddr_CT=tddr_CT, ei_CT=ei_CT, mis_CT=mis_CT,
        ac_CT=ac_CT, cpd_CT=cpd_CT, evspr_CT=evspr_CT, evsos_CT=evsos_CT, bpk_CT=bpk_CT,
        fapr_CT=fapr_CT, udpr_CT=udpr_CT, udpi_CT=udpi_CT, cv_CT=cv_CT, dtpr_CT=dtpr_CT
    )

    session.add(new_stats)
    session.commit()
    session.close()


def format_all_stats(args: List[Tuple[int, int]], num_processes: int) -> None:
    '''
    Format and store player game statistics in the database for multiple games and players.

    :param args: A list of tuples, each containing two integers - (game_id, player_id).
    :param num_processes: An integer specifying the number of processes to use for parallel processing.
    
    :return: None.
    '''
    with Pool(processes=num_processes) as pool:
        pool.map(format_stats_player_game, [(game_id, player_id) for game_id, player_id in args])


def get_new_player_stats(window: int = 10, num_processes: int = 8) -> None:
    '''
    Retrieve and format new player game statistics and store them in the database.

    :param window: An integer specifying the number of instances to process in each iteration.
    :param num_processes: An integer specifying the number of processes to use for parallel processing.
    
    :return: None.
    '''
    session = Session()

    games_players = (
        session.query(
            GamePlayerStats.game_id,
            GamePlayerStats.player_id
        )
        .filter(
            not_(
                session.query(CustomPlayerStatsGame)
                .filter(
                    and_(
                        CustomPlayerStatsGame.game_id == GamePlayerStats.game_id,
                        CustomPlayerStatsGame.player_id == GamePlayerStats.player_id
                    )
                )
                .exists()
            )
        )
        .filter(GamePlayerStats.game_id != None)
        .distinct()
        .all()
    )

    session.close()

    to_process = len(games_players)

    print(f"Need to process {to_process} instances.")
    for i in tqdm(range(0, to_process, window), desc="Processing"):
        if (i+window) < to_process:
            format_all_stats(games_players[i:i+window], num_processes)
        else:
            format_all_stats(games_players[i:to_process], num_processes)
    

if __name__ == "__main__":
    init_db()

    '''session = Session()
    CustomPlayerStatsGame.__table__.drop(session.bind) #remove
    session.close()''' #CODE FOR DELETING TABLE OF STATS

    get_new_player_stats() 