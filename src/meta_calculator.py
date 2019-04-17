from src.gamemaster import path, banned, GameMaster
import sqlite3
from copy import deepcopy


def calculate_meta(cup: str):
    # Create a matrix of all battle results
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    cur.execute('SELECT * FROM battle_sims')
    rows = cur.fetchall()
    conn.close()

    matrix = {}
    for row in rows:
        row_id, ally, enemy = row[:3]
        scores = row[3:]
        if ally not in matrix:
            matrix[ally] = {}
        matrix[ally][enemy] = (scores[0] + scores[4] + scores[8] + sum(scores)) / 2

    to_remove = []
    for pokemon in matrix:
        if any([ban in pokemon for ban in banned]):
            to_remove.append(pokemon)
    for pokemon in to_remove:
        matrix.pop(pokemon, None)
        for pokemon_2 in matrix:
            matrix[pokemon_2].pop(pokemon, None)

    rankings = {}
    current_rank = len(matrix)

    print("Matrix filled, analyzing data...")

    while current_rank > 0:
        matrix, to_remove = weight_matrix_with_removals(matrix)
        for pokemon in to_remove:
            rankings[pokemon] = {'absolute_rank': current_rank}
            matrix.pop(pokemon, None)
            for pokemon_2 in matrix:
                matrix[pokemon_2].pop(pokemon, None)
        current_rank -= len(to_remove)

    print("Data analyzed, writing to database...")

    r = 1
    for i in range(len(rankings) + 1):
        for pokemon in rankings:
            if rankings[pokemon]['absolute_rank'] == i and 'relative_rank' not in rankings[pokemon]:
                rankings[pokemon]['relative_rank'] = r
                r += 1
                for pokemon_2 in rankings:
                    if pokemon.split(', ')[0] == pokemon_2.split(', ')[0] and not pokemon_2 == pokemon:
                        rankings[pokemon_2]['relative_rank'] = 0

    for pokemon in rankings:
        rankings[pokemon]['absolute_rank'] = round(100 * rankings[pokemon]['absolute_rank'] / len(rankings), 1)
        if len(pokemon.split(', ')) == 4:
            name, fast, charge_1, charge_2 = pokemon.split(', ')
            rankings[pokemon]['name'] = name
            rankings[pokemon]['fast'] = fast
            rankings[pokemon]['charge_1'] = charge_1
            rankings[pokemon]['charge_2'] = charge_2
        else:
            name, fast, charge_1 = pokemon.split(', ')
            rankings[pokemon]['name'] = name
            rankings[pokemon]['fast'] = fast
            rankings[pokemon]['charge_1'] = charge_1
            rankings[pokemon]['charge_2'] = None

    rankings = [(rankings[k]['name'], rankings[k]['fast'], rankings[k]['charge_1'], rankings[k]['charge_2'], rankings[k]['absolute_rank'], rankings[k]['relative_rank']) for k in rankings]

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

    command = "INSERT INTO rankings(pokemon, fast, charge_1, charge_2, absolute_rank, relative_rank) VALUES (?,?,?,?,?,?)"
    cur.executemany(command, rankings)
    conn.commit()
    conn.close()


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
        matrix[ally]['row'] = round(matrix[ally]['row'] * 100 / total, 4)
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
    command = f"SELECT pokemon FROM rankings WHERE relative_rank > 0 and absolute_rank <= 100 - {percentile_limit} ORDER BY relative_rank"
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
    command = f"SELECT fast, charge_1, charge_2, absolute_rank FROM rankings WHERE pokemon = {pokemon} ORDER BY relative_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return rows


def calculate_mean_and_sd(cup: str):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = "SELECT absolute_rank FROM rankings"
    cur.execute(command)
    scores = [x[0] for x in cur.fetchall()]
    conn.close()
    mean = sum(scores) / len(scores)
    sd = (sum([(x - mean) ** 2 for x in scores]) / len(scores)) ** 0.5
    return mean, sd / 2


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank), 1)


if __name__ == '__main__':
    mean, sd = calculate_mean_and_sd('kingdom')
    for pokemon in ordered_top_pokemon('kingdom', mean + 3 * sd):
        print(pokemon)
