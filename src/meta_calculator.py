from src.gamemaster import path, banned, ignored, GameMaster
from tinydb import TinyDB, Query
from multiprocessing import Process
from copy import deepcopy
import os


def calculate_meta(cup_directory: str):
    matrix = {}
    for db_file in os.listdir(cup_directory):
        db = TinyDB(os.path.join(cup_directory, db_file))
        sim_table = db.table('battle_results')
        for doc in sim_table.all():
            ally, enemy = doc['pokemon']
            results = doc['result']
            if ally not in matrix:
                matrix[ally] = {}
            matrix[ally][enemy] = sum(r[0] for r in results) / len(results)
        db.close()

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

    db = TinyDB(f"{cup_directory}/meta.rankings")
    table = db.table('meta')
    table.insert_multiple(rankings)
    db.close()


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
        elif pokemon.split(', ')[0] in ignored:
            to_ignore.append(pokemon)

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
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}/meta.rankings")
    table = db.table('meta')
    data = table.search(query.relative_rank != 0)
    db.close()
    data = [x for x in data if 100 - x['absolute_rank'] >= percentile_limit]
    data.sort(key=lambda k: k['relative_rank'])
    return data


def all_pokemon_movesets(cup: str):
    db = TinyDB(f"{path}/data/databases/{cup}/meta.rankings")
    table = db.table('meta')
    data = table.all()
    db.close()
    data.sort(key=lambda k: k['absolute_rank'])
    return data


def ordered_movesets_for_pokemon(cup: str, pokemon: str):
    query = Query()
    db = TinyDB(f"{path}/data/databases/{cup}/meta.rankings")
    table = db.table('meta')
    data = table.search(query.name == pokemon)
    data = [(d['absolute_rank'], d['fast'], d['charge_1'], d['charge_2']) for d in data]
    data.sort(key=lambda k: k[0])
    return data


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank), 1)


def main():
    yeet = ('boulder', ('rock', 'fighting', 'steel', 'ground'), 'twilight', ('fairy', 'poison', 'dark', 'ghost'), 'tempest', ('flying', 'electric', 'ice', 'ground'), 'kingdom', ('steel', 'ice', 'fire', 'dragon'))
    # jobs = []
    # for i in range(4):
    #     jobs.append(Process(target=calculate_meta, args=(yeet[i * 2],)))
    #     jobs[i].start()
    # for i in range(4):
    #     jobs[i].join()
    #     print(f"Meta for {yeet[i * 2]} finished.")
    jobs = []
    for i in range(4):
        jobs.append(Process(target=fill_all_card_info, args=(yeet[i * 2], yeet[i * 2 + 1])))
        jobs[i].start()
    for i in range(4):
        jobs[i].join()
        print(f"Card DB for {yeet[i * 2]} finished.")


if __name__ == '__main__':
    main()
