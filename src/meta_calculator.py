from src.gamemaster import path, banned, GameMaster
from tinydb import TinyDB, Query
from math import inf
from multiprocessing import Process
from copy import deepcopy


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
                    if pokemon.split(', ')[0] == pokemon2.split(', ')[0] and not pokemon2 == pokemon:
                        rankings[pokemon2]['relative_rank'] = 0

    for pokemon in rankings:
        rankings[pokemon]['absolute_rank'] *= 100 / float(len(rankings))
        name, fast, charge_1, charge_2 = pokemon.split(', ')
        rankings[pokemon]['name'] = name
        rankings[pokemon]['fast'] = fast
        rankings[pokemon]['charge_1'] = charge_1
        rankings[pokemon]['charge_2'] = charge_2

    rankings = [rankings[k] for k in rankings]

    meta_table.insert_multiple(rankings)
    db.close()


def fill_all_card_info(cup: str, cup_types: tuple):
    gm = GameMaster()
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    sim_table = db.table('battle_results')
    meta_table = db.table('meta')
    print("Querying meta information...")
    query = Query()
    ordered_pokemon = meta_table.search(query.relative_rank != 0)
    ordered_pokemon.sort(key=lambda k: k['relative_rank'])
    print("Generating card info...")
    to_write = [
        fill_card_info(ordered_pokemon, cup_types, document['name'], document['fast'], document['charge_1'], document['charge_2'], sim_table, gm) for document in all_pokemon_movesets(cup)
    ]
    db.close()
    print("Writing to database...")
    db = TinyDB(f"{path}/web/{cup}-card-data.json")
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
                win = battle['result'][0] > battle['result'][1]
                break
            elif battle['pokemon'] == [enemy, ally]:
                win = battle['result'][0] < battle['result'][1]
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
    scores = []
    for ally in matrix:
        matrix[ally]['row'] = round(matrix[ally]['row'] * 100 / total, 4)
        scores.append(matrix[ally]['row'])

    to_remove = []
    scores.sort()

    for pokemon in matrix:
        if matrix[pokemon]['row'] in scores[:min(2, len(scores))]:
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


def all_pokemon_movesets(cup: str):
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('meta')
    data = table.search(query.absolute_rank.exists())
    db.close()
    data.sort(key=lambda k: k['absolute_rank'])
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
    return round((rank - min_rank) * 100 / (max_rank - min_rank), 1)


def main():
    yeet = ('boulder', ('rock', 'fighting', 'steel', 'ground'), 'twilight', ('fairy', 'poison', 'dark', 'ghost'), 'tempest', ('flying', 'electric', 'ice', 'ground'), 'kingdom', ('steel', 'ice', 'fire', 'dragon'))
    jobs = []
    for i in range(4):
        jobs.append(Process(target=calculate_meta, args=(yeet[i * 2],)))
        jobs[i].start()
    for i in range(4):
        jobs[i].join()
        print(f"Meta for {yeet[i * 2]} finished.")
    jobs = []
    for i in range(4):
        jobs.append(Process(target=fill_all_card_info, args=(yeet[i * 2], yeet[2 * i + 1])))
        jobs[i].start()
    for i in range(4):
        jobs[i].join()
        print(f"Card DB for {yeet[i * 2]} finished.")


if __name__ == '__main__':
    main()
