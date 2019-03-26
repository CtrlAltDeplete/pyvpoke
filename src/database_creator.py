from multiprocessing import Process, Manager
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
from time import time
from tinydb import TinyDB, Query


def fill_table_for_pokemon(pokemon_indices, all_pokemon, return_list):
    for index in pokemon_indices:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_pokemon[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(index, len(all_pokemon)):
            enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[k]
            enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
            results = battle_all_shields(ally, enemy)
            if index != k:
                return_list.extend([{'ally': str(ally), 'enemy': str(enemy), 'result': 1000 + results[0] - results[1]},
                                    {'ally': str(enemy), 'enemy': str(ally), 'result': 1000 + results[1] - results[0]}])
            else:
                return_list.append({'ally': str(ally), 'enemy': str(enemy), 'result': 1000 + results[0] - results[1]})


def main():
    start_time = time()
    gm = GameMaster()

    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(['electric', 'ice', 'flying', 'ground']))
    print("Creating Processes...")
    num_processes = 16
    indices_lists = []
    for i in range(num_processes):
        indices_lists.append([])
    for i in range(len(all_possibilities)):
        for j in range(num_processes):
            if i % num_processes == j:
                indices_lists[j].append(i)
    print("Processes Created, Joining Processes...")
    jobs = []
    manager = Manager()
    return_list = manager.list()
    for indices_list in indices_lists:
        p = Process(target=fill_table_for_pokemon, args=(indices_list, all_possibilities, return_list))
        jobs.append(p)
        p.start()

    for i in range(num_processes - 1, -1, -1):
        print(i)
        jobs[i].join()
        print(f"{round(100 * (num_processes - i) / num_processes)}% Finished.")

    db = TinyDB(f"{path}/data/databases/kingdom.json")
    table = db.table('battle_result')

    table.insert_multiple(return_list)

    elapsed_time = time() - start_time
    print(elapsed_time)
    db.close()


def repair_database():
    db = TinyDB(f"{path}/data/databases/kingdom.json")
    table = db.table('battle_result')
    query = Query()

    print(len(table))
    ids_to_remove = []
    matchups_to_resimulate = []

    for record in table.search(query.ally.exists()):
        if ('Lucario' in record['ally'] and 'Power-Up Punch' in record['ally']) or ('Lucario' in record['enemy'] and 'Power-Up Punch' in record['enemy']):
            ids_to_remove.append(record.doc_id)
            matchups_to_resimulate.append((record['ally'], record['enemy']))

    table.remove(doc_ids=ids_to_remove)
    print(len(table))
    results_to_insert = []

    for ally_string, enemy_string in matchups_to_resimulate:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = ally_string.split(', ')
        enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = enemy_string.split(', ')
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
        result = battle_all_shields(ally, enemy)
        results_to_insert.append({'ally': str(ally), 'enemy': str(enemy), 'result': result})

    table.insert_multiple(results_to_insert)
    print(len(table))

    db.close()


if __name__ == '__main__':
    # main()
    repair_database()
