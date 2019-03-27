from src.gamemaster import path, GameMaster, banned
from tinydb import TinyDB, Query
from math import inf


def calculate_meta():
    db = TinyDB(f"{path}/data/databases/kingdom.json")
    sim_table = db.table('battle_results')
    db.purge_table('meta2')
    meta_table = db.table('meta2')
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
        diff = max(abs(results[1] - results[0]), 1) ** 2
        matrix[ally][enemy] = results[0] * diff if results[0] > results[1] else results[0] / diff
        matrix[enemy][ally] = results[1] * diff if results[1] > results[0] else results[1] / diff

    print("Matrix filled, analyzing data...")

    for ally in matrix:
        column = 0
        for enemy in matrix:
            column += matrix[enemy][ally]
        matrix[ally]['column'] = column

    total = 0
    for ally in matrix:
        row = 0
        for enemy in matrix:
            matrix[ally][enemy] /= matrix[ally]['column']
            row += matrix[ally][enemy]
        matrix[ally]['row'] = row
        total += row
    for ally in matrix:
        matrix[ally] = round(matrix[ally]['row'] * 100 / total, 4)
    results = [(value, key) for key, value in matrix.items()]
    results.sort(reverse=True)
    db_results = []
    for result in results:
        db_results.append({'name': result[1], 'score': result[0]})
    print("Writing data to database...")
    meta_table.insert_multiple(db_results)
    db.close()


def top_pokemon(banned: tuple, pokemon_num: int = None):
    data = []
    query = Query()
    db = TinyDB(f"{path}/data/databases/kingdom.json")
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


def rank_of_pokemon(name):
    db = TinyDB(f"{path}/data/databases/kingdom.json")
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
    calculate_meta()
    top_mons = top_pokemon(banned)
    for mon in top_mons:
        print(f"{mon[0]}: {', '.join(mon[1:])}")
    with open(f'{path}/data/kingdom_rankings_2.csv', 'w') as f:
        f.write('\n'.join([','.join([str(y) for y in x]) for x in top_mons]))
