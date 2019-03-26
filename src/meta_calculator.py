from src.gamemaster import path, GameMaster
from tinydb import TinyDB, Query


def calculate_meta(db: TinyDB, table_name: str):
    sim_table = db.table(table_name)
    meta_table = db.table('meta')
    matrix = {}
    query = Query()
    gm = GameMaster()

    for ally in gm.iter_pokemon_move_set_combos(['ice', 'flying', 'electric', 'ground']):
        ally_string = ', '.join(ally)
        matrix[ally_string] = {'column': 0}
        # for record in sim_table.search(query.ally == ally_string):
        #     matrix[ally_string][record['enemy']] = record['result']

    print("Querying data...")

    for record in sim_table.search(query.ally.exists()):
        matrix[record['ally']][record['enemy']] = record['result']

    print("Matrix filled, analyzing data...")

    for ally in matrix:
        for enemy in matrix:
            matrix[ally]['column'] += matrix[enemy][ally]
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
    return results


def top_pokemon(table, banned, pokemon_num):
    data = []
    query = Query()
    for record in table.search(query.name.exists()):
        data.append((record['score'], record['name']))
    data.sort(reverse=True)
    to_return = []
    i = 0
    j = 0
    used = []
    while i < 20:
        name = data[j][1].split(', ')[0]
        if name in banned or name in used:
            j += 1
            continue
        to_return.append(data[j])
        used.append(name)
        j += 1
        i += 1
    return to_return[:pokemon_num]


def rank_of_pokemon(name):
    db = TinyDB(f"{path}/data/databases/kingdom.json")
    table = db.table('meta')
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


if __name__ == '__main__':
    db = TinyDB(f"{path}/data/databases/kingdom.json")
    db.purge_table('meta')
    table = db.table('meta')
    calculate_meta(db, 'battle_result')
    db.close()
    # print(rank_of_pokemon('Combusken'))
