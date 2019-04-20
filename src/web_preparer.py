from src.gamemaster import path, GameMaster
from src.meta_calculator import (
    ordered_top_pokemon, calculate_mean_and_sd, ordered_movesets_for_pokemon
)
from src.pokemon import Pokemon
from multiprocessing import Process
import sqlite3


gm = GameMaster()


def create_ranking_table(cup: str):
    conn = sqlite3.connect(f"{path}/web/{cup}.db")
    cur = conn.cursor()
    command = f"CREATE TABLE rankings (pokemon TEXT, relative_rank INTEGER, absolute_rank REAL, color TEXT, level REAL, atk INTEGER, def INTEGER, sta INTEGER, best_matchups TEXT, worst_matchups TEXT, optimal_team TEXT)"
    cur.execute(command)
    command = f"CREATE TABLE all_pokemon (name TEXT, absolute_rank REAL, fast TEXT, fast_type TEXT, charge_1 TEXT, charge_1_type TEXT, charge_2 TEXT, charge_2_type TEXT, string TEXT)"
    cur.execute(command)
    conn.commit()
    conn.close()

    mean, sd = calculate_mean_and_sd(cup)
    all_pokemon = ordered_top_pokemon(cup)
    num_processes = 8
    for i in range(0, len(all_pokemon), num_processes):
        jobs = []
        for j in range(min(num_processes, len(all_pokemon) - i)):
            pokemon = all_pokemon[i + j]
            jobs.append(Process(target=add_pokemon_to_ranking_table, args=(pokemon, cup, mean, sd, i+1)))
            jobs[j].start()

        for p in range(min(num_processes, len(all_pokemon) - i)):
            jobs[p].join()

        print(f"{round(100 * (i + min(num_processes, len(all_pokemon) - i)) / len(all_pokemon), 1)}%")


def add_pokemon_to_ranking_table(pokemon, cup, mean, sd, i):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT fast, charge_1, charge_2, absolute_rank FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC"
    cur.execute(command, (pokemon,))
    rows = cur.fetchall()
    p = Pokemon(pokemon, rows[0][0], rows[0][1], rows[0][2])
    best_matchups, worst_matchups, optimal_team = combos(cup, str(p), cur)
    data = {
        'name': pokemon,
        'relative_rank': i,
        'color': calculate_color(mean, sd, rows[0][3]),
        'absolute_rank': rows[0][3],
        'level': p.level,
        'atk': p.ivs['atk'],
        'def': p.ivs['def'],
        'sta': p.ivs['hp'],
        'optimal_team': ', '.join(optimal_team),
        'best_matchups': ', '.join(best_matchups),
        'worst_matchups': ', '.join(worst_matchups),
        'movesets': [{
                         'fast_type': gm.get_move(row[0])['type'],
                         'fast': row[0],
                         'charge_1_type': gm.get_move(row[1])['type'],
                         'charge_1': row[1],
                         'charge_2_type': gm.get_move(row[2])['type'],
                         'charge_2': row[2],
                         'absolute_rank': row[3],
                         'string': f"{cup}+{pokemon}+{row[0]}+{row[1]}+{row[2]}"
                     } if row[2] else {
                         'fast_type': gm.get_move(row[0])['type'],
                         'fast': row[0],
                         'charge_1_type': gm.get_move(row[1])['type'],
                         'charge_1': row[1],
                         'charge_2_type': None,
                         'charge_2': None,
                         'absolute_rank': row[3],
                         'string': f"{cup}+{pokemon}+{row[0]}+{row[1]}"
                     } for row in rows]
    }
    conn.close()
    conn = sqlite3.connect(f"{path}/web/{cup}.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO rankings VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
        data['name'], data['relative_rank'], data['absolute_rank'], data['color'], data['level'], data['atk'],
        data['def'], data['sta'], data['best_matchups'], data['worst_matchups'], data['optimal_team']
    ))
    command = "INSERT INTO all_pokemon VALUES(?,?,?,?,?,?,?,?,?)"
    bindings = [(
        data['name'], moveset['absolute_rank'], moveset['fast'], moveset['fast_type'], moveset['charge_1'],
        moveset['charge_1_type'], moveset['charge_2'], moveset['charge_2_type'], moveset['string']
    ) for moveset in data['movesets']]
    cur.executemany(command, bindings)
    conn.commit()
    conn.close()


def calculate_color(mean, sd, rank):
    if rank >= mean + 2 * sd:
        return "00FF00"
    elif rank >= mean + sd:
        return "66FF00"
    elif rank >= mean:
        return "CCFF00"
    elif rank >= mean - sd:
        return "FFCC00"
    elif rank >= mean - 2 * sd:
        return "FF6600"
    return "FF0000"


def combos(cup, pokemon, cur):
    meta = ordered_top_pokemon(cup, 90)
    meta_matrix = {}
    for mon in meta:
        fast, charge_1, charge_2, absolute_rank = ordered_movesets_for_pokemon(cup, mon)[0]
        if charge_2:
            data = ', '.join([mon, fast, charge_1, charge_2])
        else:
            data = ', '.join([mon, fast, charge_1])
        meta_matrix[data] = {}
    if pokemon not in meta_matrix:
        meta_matrix[pokemon] = {}
    command = "SELECT * FROM battle_sims WHERE ally = ? AND enemy = ?"
    for moveset in meta_matrix:
        for moveset_2 in meta_matrix:
            cur.execute(command, (moveset, moveset_2))
            meta_matrix[moveset][moveset_2] = sum(cur.fetchone()[3:])

    best_matchups = [(meta_matrix[pokemon][key], key.split(', ')[0]) for key in meta_matrix[pokemon] if key != pokemon]
    best_matchups.sort(reverse=True)
    best_matchups = [x[1] for x in best_matchups[:3]]

    worst_matchups = [(meta_matrix[pokemon][key], key.split(', ')[0]) for key in meta_matrix[pokemon] if key != pokemon]
    worst_matchups.sort()
    worst_matchups = [x[1] for x in worst_matchups[:3]]

    team_scores = []
    for ally_1 in meta_matrix:
        for ally_2 in meta_matrix:
            if ally_1 == ally_2 or pokemon in [ally_1, ally_2]:
                continue
            score = 1
            for enemy in meta_matrix:
                score *= max([meta_matrix[pokemon][enemy], meta_matrix[ally_1][enemy], meta_matrix[ally_2][enemy]])
            team_scores.append((score, (pokemon.split(', ')[0], ally_1.split(', ')[0], ally_2.split(', ')[0])))
    team_scores.sort(reverse=True)
    team_scores = [x for x in team_scores[0][1]]

    return best_matchups, worst_matchups, team_scores


def main():
    cups = [
        # 'test',
        # 'boulder',
        # 'twilight',
        # 'tempest',
        # 'kingdom',
        'nightmare'
    ]
    for cup in cups:
        create_ranking_table(cup)
        print(f"Finished {cup}.\n")


if __name__ == '__main__':
    main()
