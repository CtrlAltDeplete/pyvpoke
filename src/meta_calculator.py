from src.gamemaster import path, banned
from tinydb import TinyDB, Query
from math import inf


def calculate_meta(cup: str):
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    sim_table = db.table('battle_results')
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
            rankings[pokemon] = {"absolute_rank": current_rank}
            matrix.pop(pokemon, None)
            for pokemon2 in matrix:
                matrix[pokemon2].pop(pokemon, None)
        current_rank -= len(to_remove)

    print("Data analyzed, writing to database...")

    r = 1
    for i in range(len(rankings)):
        for pokemon in rankings:
            if rankings[pokemon]['absolute_rank'] == i and 'relative_rank' not in rankings[pokemon]:
                rankings[pokemon]['relative_rank'] = r
                r += 1
                for pokemon2 in rankings:
                    if pokemon.split(', ')[0] in pokemon2 and not pokemon2 == pokemon:
                        rankings[pokemon2]['relative_rank'] = 0

    for pokemon in rankings:
        rankings[pokemon]['absolute_rank'] *= 100 / (len(rankings) - 1)
        rankings[pokemon]['absolute_rank'] = round(rankings[pokemon]['absolute_rank'], 1)
        name, fast, charge_1, charge_2 = pokemon.split(', ')
        rankings[pokemon]['name'] = name
        rankings[pokemon]['fast'] = fast
        rankings[pokemon]['charge_1'] = charge_1
        rankings[pokemon]['charge_2'] = charge_2

    rankings = [rankings[k] for k in rankings]

    meta_table.insert_multiple(rankings)
    db.close()


# def fill_card_info(cup: str, pokemon: str, fast: str, charge_1: str, charge_2: str):
#     ordered_pokemon = ordered_top_pokemon(cup)
#     db = TinyDB(f"{path}/data/databases/{cup}.json")
#     sim_table = db.table('battle_results')
#     win_against = []
#     lose_against = []
#     i = 0
#     query = Query()
#     while len(win_against) < 18 and len(lose_against) < 18:
#         ally = ', '.join([pokemon, fast, charge_1, charge_2])
#         enemy = ', '.join([ordered_pokemon[i]['name'], ordered_pokemon[i]['fast'], ordered_pokemon[i]['charge_1'], ordered_pokemon[i]['charge_2']])
#         battle = sim_table.search(query.pokemon == [ally, enemy])
#         if battle:
#             win = battle[0]['result'][0] > battle[0]['result'][1]
#         else:
#             battle = sim_table.search(query.pokemon == [enemy, ally])
#             win = battle[0]['result'][0] < battle[0]['result'][1]
#         if win and len(win_against) < 18:
#             win_against.append(ordered_pokemon[i]['name'])
#         elif not win and len(lose_against) < 18:
#             lose_against.append(ordered_pokemon[i]['name'])
#     db.close()
#     return {'name': pokemon, 'fast': fast, 'charge_1': charge_1, 'charge_2': charge_2, 'win': win_against, 'lose': lose_against}


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


def ordered_top_pokemon(cup: str):
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('meta')
    data = table.search(query.relative_rank != 0)
    db.close()
    data.sort(key=lambda k: k['relative_rank'])
    return data


def ordered_movesets_for_pokemon(cup: str, pokemon: str):
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('meta')
    data = table.search(query.name == pokemon)
    data = [(d['absolute_rank'], d['fast'], d['charge_1'], d['charge_2']) for d in data]
    data.sort(key=lambda k: k[0])
    return data


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank))


if __name__ == '__main__':
    calculate_meta('boulder')
