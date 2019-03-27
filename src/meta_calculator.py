from src.gamemaster import path, banned
from tinydb import TinyDB, Query
from math import inf


def calculate_meta(cup: str, purge: bool = False):
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    sim_table = db.table('battle_results')
    if purge:
        db.purge_table('meta')
    meta_table = db.table('meta')
    matrix = {}
    query = Query()

    print("Querying data...")

    for record in sim_table.search(query.result.exists()):
        ally, enemy = record['pokemon']
        results = record['result']
        if ally not in matrix:
            matrix[ally] = {}
        if enemy not in matrix:
            matrix[enemy] = {}
        matrix[ally][enemy] = results[0]
        matrix[enemy][ally] = results[1]

    print("Matrix filled, analyzing data...")
    matrix = weight_matrix(matrix)

    results = [(value, key) for key, value in matrix.items()]
    results.sort(reverse=True)
    db_results = []
    for result in results:
        db_results.append({'name': result[1], 'score': result[0]})
    print("Writing data to database...")
    meta_table.insert_multiple(db_results)
    db.close()


def calculate_in_depth_meta(cup: str):
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    sim_table = db.table('battle_results')
    meta_table = db.table('in_depth_meta')
    matrix = {}
    query = Query()

    print("Querying data...")

    for record in sim_table.search(query.result.exists()):
        ally, enemy = record['pokemon']
        results = record['result']
        if ally not in matrix:
            matrix[ally] = {}
        if enemy not in matrix:
            matrix[enemy] = {}
        matrix[ally][enemy] = results[0]
        matrix[enemy][ally] = results[1]

    to_remove = []
    for pokemon in matrix:
        if any([ban in pokemon for ban in banned]):
            to_remove.append(pokemon)
    to_remove = set(to_remove)
    for pokemon in to_remove:
        matrix.pop(pokemon, None)
        for pokemon2 in matrix:
            matrix[pokemon2].pop(pokemon, None)

    rankings = {}
    current_rank = len(matrix)

    print("Matrix filled, analyzing data...")

    while current_rank > 0:
        matrix, to_remove = weight_matrix_with_removals(matrix)
        for pokemon in to_remove:
            rankings[pokemon] = current_rank
            matrix.pop(pokemon, None)
            for pokemon2 in matrix:
                matrix[pokemon2].pop(pokemon, None)
        current_rank -= len(to_remove)

    print("Data analyzed, writing to database...")

    filtered_rankings = {}
    for pokemon in rankings:
        pokemon_name, fast_move, charge_move_1, charge_move_2 = pokemon.split(', ')
        rank = rankings[pokemon]
        if pokemon_name not in filtered_rankings:
            filtered_rankings[pokemon_name] = {'name': pokemon_name, 'rank': inf, 'movesets': []}
        filtered_rankings[pokemon_name]['rank'] = min(filtered_rankings[pokemon_name]['rank'], rank)
        filtered_rankings[pokemon_name]['movesets'].append([rank, fast_move, charge_move_1, charge_move_2])

    to_write = []
    for pokemon in filtered_rankings:
        movesets = filtered_rankings[pokemon]['movesets']
        movesets.sort()
        for i in range(len(movesets)):
            movesets[i][0] = i + 1
        filtered_rankings[pokemon]['movesets'] = movesets
        to_write.append(filtered_rankings[pokemon])

    meta_table.insert_multiple(to_write)
    db.close()


def weight_matrix(matrix: dict):
    for ally in matrix:
        column = 0
        for enemy in matrix:
            column += matrix[enemy][ally]
        matrix[ally]['column'] = column

    total = 0
    for ally in matrix:
        row = 0
        for enemy in matrix:
            row += matrix[ally][enemy] / matrix[ally]['column']
        matrix[ally]['row'] = row
        total += row
    for ally in matrix:
        matrix[ally] = round(matrix[ally]['row'] * 100 / total, 4)
    return matrix


def weight_matrix_with_removals(matrix: dict):
    for ally in matrix:
        column = 0
        for enemy in matrix:
            column += matrix[enemy][ally]
        matrix[ally]['column'] = column

    total = 0
    for ally in matrix:
        row = 0
        for enemy in matrix:
            row += matrix[ally][enemy] / matrix[ally]['column']
        matrix[ally]['row'] = row
        total += row
    for ally in matrix:
        matrix[ally]['row'] = round(matrix[ally]['row'] * 100 / total, 4)

    min_score = inf
    to_remove = []

    for pokemon in matrix:
        min_score = min(min_score, matrix[pokemon]['row'])

    for pokemon in matrix:
        if matrix[pokemon]['row'] == min_score:
            to_remove.append(pokemon)

    return matrix, to_remove


def top_pokemon(banned: tuple, cup: str, pokemon_num: int = None):
    data = []
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('meta')
    for record in table.search(query.name.exists()):
        data.append((record['score'], record['name']))
    db.close()
    data.sort(reverse=True)
    to_return = []
    i = 0
    j = 0
    used = []
    min_rank = inf
    max_rank = 0
    if pokemon_num is None:
        pokemon_num = len(data)
    while j < pokemon_num:
        name, fast_attack, charge_1, charge_2 = data[j][1].split(', ')
        if name in banned or name in used:
            j += 1
            continue
        to_return.append([data[j][0], name, fast_attack, charge_1, charge_2])
        min_rank = min(min_rank, data[j][0])
        max_rank = max(max_rank, data[j][0])
        used.append(name)
        j += 1
        i += 1
    for record in to_return:
        record[0] = scale_ranking(record[0], min_rank, max_rank)
    return to_return[:pokemon_num]


def top_pokemon_in_depth(cup: str, pokemon_num: int = None):
    data = []
    query = Query()
    db = TinyDB(F"{path}/data/databases/{cup}.json")
    table = db.table('in_depth_meta')
    for record in table.search(query.name.exists()):
        data.append((record['rank'], record['name'], record['movesets'][0][1], record['movesets'][0][2], record['movesets'][0][3]))
    data.sort()
    if pokemon_num is None:
        pokemon_num = len(data)
    return data[:pokemon_num]


def rank_of_pokemon(name: str, cup: str):
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('meta2')
    data = []
    query = Query()
    for record in table.search(query.name.exists()):
        data.append((record['score'], record['name']))
    db.close()
    data.sort(reverse=True)
    i = 1
    for datum in data:
        if name in datum[1]:
            return datum, i
        i += 1


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank))


if __name__ == '__main__':
    cup = 'kingdom'
    calculate_in_depth_meta(cup)
    # top_mons = top_pokemon_in_depth(cup)
    # for mon in top_mons:
    #     print(f"{mon[0]}: {', '.join(mon[1:])}")
    # with open(f'{path}/data/{cup}_rankings.csv', 'w') as f:
    #     f.write('\n'.join([','.join([str(y) for y in x]) for x in top_mons]))
