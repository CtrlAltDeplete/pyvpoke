from src.gamemaster import path, banned, GameMaster
import sqlite3
from copy import deepcopy


def result_iter(cur, arraysize=1000):
    while True:
        results = cur.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def calculate_meta(cup: str):
    # Create a matrix of all battle results
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute('SELECT * FROM battle_sims')

    print("Assembling matrix...")

    matrix = {}
    for row in result_iter(cur):
        row_id, ally, enemy = row[:3]
        scores = row[3:]
        if ally not in matrix:
            matrix[ally] = {}
        matrix[ally][enemy] = (scores[0] + scores[4] + scores[8] + sum(scores)) / 2
    conn.close()

    to_remove = []
    for pokemon in matrix:
        if any([ban in pokemon for ban in banned]):
            to_remove.append(pokemon)
    for pokemon in to_remove:
        matrix.pop(pokemon, None)
        for pokemon_2 in matrix:
            matrix[pokemon_2].pop(pokemon, None)

    rankings = {}
    current_rank = 1

    print("Calculating rankings...")

    max_rank = len(matrix)
    while current_rank <= max_rank:
        matrix, to_remove = weight_matrix_with_removals(matrix)
        for pokemon in to_remove:
            rankings[pokemon] = {'absolute_rank': current_rank}
            matrix.pop(pokemon, None)
            for pokemon_2 in matrix:
                matrix[pokemon_2].pop(pokemon, None)
            current_rank += 1
        print(current_rank)

    results = {}
    all_pokemon = {}

    for pokemon in rankings:
        results[pokemon] = {}
        if len(pokemon.split(', ')) == 4:
            name, fast, charge_1, charge_2 = pokemon.split(', ')
            results[pokemon]['name'] = name
            results[pokemon]['fast'] = fast
            results[pokemon]['charge_1'] = charge_1
            results[pokemon]['charge_2'] = charge_2
        else:
            name, fast, charge_1 = pokemon.split(', ')
            results[pokemon]['name'] = name
            results[pokemon]['fast'] = fast
            results[pokemon]['charge_1'] = charge_1
            results[pokemon]['charge_2'] = None
        results[pokemon]['absolute_rank'] = rankings[pokemon]['absolute_rank']
        if name in all_pokemon:
            all_pokemon[name] = max(all_pokemon[name], rankings[pokemon]['absolute_rank'])
        else:
            all_pokemon[name] = rankings[pokemon]['absolute_rank']

    all_pokemon = [(all_pokemon[key], key) for key in all_pokemon]
    all_pokemon.sort(reverse=True)
    results = [(results[k]['name'], results[k]['fast'], results[k]['charge_1'], results[k]['charge_2'], results[k]['absolute_rank']) for k in rankings]
    min_score = min([x[4] for x in results])
    max_score = max([x[4] for x in results])

    print("Writing to database...")

    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    columns = (
        ' '.join(('id', 'INTEGER PRIMARY KEY AUTOINCREMENT')),
        ' '.join(('pokemon', 'TEXT')),
        ' '.join(('fast', 'TEXT')),
        ' '.join(('charge_1', 'TEXT')),
        ' '.join(('charge_2', 'TEXT')),
        ' '.join(('absolute_rank', 'REAL')),
        ' '.join(('relative_rank', 'REAL'))
    )
    command = f"CREATE TABLE rankings ({', '.join(columns)})"
    cur.execute(command)

    command = "INSERT INTO rankings(pokemon, fast, charge_1, charge_2, absolute_rank) VALUES (?,?,?,?,?)"
    cur.executemany(command, results)

    command = f"UPDATE rankings SET absolute_rank = round((absolute_rank - {min_score}) * 100 / ({max_score} - {min_score}), 1)"
    cur.execute(command)

    for i in range(1, len(all_pokemon) + 1):
        command = f"UPDATE rankings SET relative_rank = {i} WHERE id in (SELECT id FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC LIMIT 1)"
        cur.execute(command, (all_pokemon[i - 1][1],))

    conn.commit()
    conn.close()
    print("Done.\n")


def weight_matrix_with_removals(matrix: dict):
    victories = {}
    for ally in matrix:
        victories[ally] = []
        for enemy in matrix:
            if matrix[ally][enemy] > matrix[enemy][ally]:
                victories[ally].append(enemy)

    to_ignore = []
    victories = [(pokemon, set(v)) for pokemon, v in victories.items()]
    for pokemon, v in victories:
        if any(v.issubset(w[1]) and v != w[1] for w in victories):
            to_ignore.append(pokemon)

    if len(to_ignore) + 1 >= len(matrix.keys()):
        return matrix, list(matrix.keys())

    for ally in matrix:
        column = 0
        for enemy in matrix:
            if enemy not in to_ignore:
                column += matrix[enemy][ally]
        matrix[ally]['column'] = column

    total = 0
    for ally in matrix:
        row = 0
        for enemy in matrix:
            if matrix[ally]['column'] == 0:
                print(matrix)
                exit(69)
            row += matrix[ally][enemy] / matrix[ally]['column']
        matrix[ally]['row'] = row
        total += row

    scores = []
    for ally in matrix:
        scores.append(matrix[ally]['row'])

    to_remove = []
    scores.sort()

    for pokemon in matrix:
        if matrix[pokemon]['row'] in scores[:min(3, len(scores))]:
            to_remove.append(pokemon)

    return matrix, to_remove


def fill_all_card_info(cup: str, cup_types: tuple):
    gm = GameMaster()
    db = TinyDB(f"{path}/data/databases/{cup}/meta.rankings")
    # sim_table = db.table('battle_results')
    meta_table = db.table('meta')
    print("Querying meta information...")
    query = Query()
    ordered_pokemon = meta_table.search(query.relative_rank != 0)
    db.close()
    ordered_pokemon.sort(key=lambda k: k['relative_rank'])
    print("Generating card info...")
    to_write = []
    for doc in all_pokemon_movesets(cup):
        db = TinyDB(f"{path}/data/databases/{cup}/{doc['name']}.json")
        sim_table = db.table('battle_results')
        to_write.append(fill_card_info(ordered_pokemon, cup_types, doc['name'], doc['fast'], doc['charge_1'], doc['charge_2'], sim_table, gm))
        db.close()
    print("Writing to database...")
    db = TinyDB(f"{path}/web/{cup}.carddata")
    db.insert_multiple(to_write)
    db.close()


def fill_card_info(ordered_pokemon, cup_types: tuple, pokemon: str, fast: str, charge_1: str, charge_2: str, sim_table, gm):
    # name, background, fast_data, charge_1_data, charge_2_data, winning_matchups, losing_matchups
    win_against = []
    lose_against = []
    i = 0
    ally = ', '.join([pokemon, fast, charge_1, charge_2])
    query = Query()
    battles = sim_table.search(query.pokemon.any([ally]))
    while (len(win_against) < 18 or len(lose_against) < 18) and i < len(ordered_pokemon):
        enemy = ', '.join([ordered_pokemon[i]['name'], ordered_pokemon[i]['fast'], ordered_pokemon[i]['charge_1'], ordered_pokemon[i]['charge_2']])
        for battle in battles:
            if battle['pokemon'] == [ally, enemy]:
                win = sum([b[0] for b in battle['result']]) > sum([b[1] for b in battle['result']])
                break
            elif battle['pokemon'] == [enemy, ally]:
                win = sum([b[0] for b in battle['result']]) < sum([b[1] for b in battle['result']])
                break
        if win and len(win_against) < 18:
            win_against.append(ordered_pokemon[i]['name'])
        elif not win and len(lose_against) < 18:
            lose_against.append(ordered_pokemon[i]['name'])
        i += 1
    pokemon_types = deepcopy(gm.get_pokemon(pokemon)['types'])
    background = pokemon_types[0] if pokemon_types[0] in cup_types else pokemon_types[1]
    fast_data = deepcopy(gm.get_move(fast))
    if fast_data['type'] in pokemon_types:
        fast_data['power'] *= 1.2
    charge_1_data = deepcopy(gm.get_move(charge_1))
    if charge_1_data['type'] in pokemon_types:
        charge_1_data['power'] *= 1.2
    charge_2_data = deepcopy(gm.get_move(charge_2))
    if charge_2_data['type'] in pokemon_types:
        charge_2_data['power'] *= 1.2
    return {'name': pokemon,
            'background': background,
            'fast_data': fast_data,
            'fast_name': fast,
            'charge_1_data': charge_1_data,
            'charge_1_name': charge_1,
            'charge_2_data': charge_2_data,
            'charge_2_name': charge_2,
            'winning_matchups': win_against,
            'losing_matchups': lose_against}


def ordered_top_pokemon(cup: str, percentile_limit: int = 0):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT pokemon FROM rankings WHERE relative_rank > 0 and absolute_rank >= 100 - {percentile_limit} ORDER BY relative_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return [x[0] for x in rows]


def all_pokemon_movesets(cup: str, percentile_limit: int = 0):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT pokemon FROM rankings WHERE absolute_rank <= 100 - {percentile_limit} ORDER BY absolute_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return [x[0] for x in rows]


def ordered_movesets_for_pokemon(cup: str, pokemon: str):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT fast, charge_1, charge_2, absolute_rank FROM rankings WHERE pokemon = ? ORDER BY relative_rank"
    cur.execute(command, (pokemon,))
    rows = cur.fetchall()
    conn.close()
    return rows


def calculate_mean_and_sd(cup: str):
    ordered_pokemon = ordered_top_pokemon(cup)
    scores = []
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    for pokemon in ordered_pokemon:
        command = f"SELECT absolute_rank FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC"
        cur.execute(command, (pokemon,))
        row = cur.fetchone()
        scores.append(row[0])
    conn.close()
    mean = sum(scores) / len(scores)
    sd = (sum([(x - mean) ** 2 for x in scores]) / len(scores)) ** 0.5
    return mean, sd / 2


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank), 1)


if __name__ == '__main__':
    calculate_meta('nightmare')
