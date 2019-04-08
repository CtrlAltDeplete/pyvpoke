from multiprocessing import Process, Manager
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
from time import time
from tinydb import TinyDB


def fill_table_for_pokemon(pokemon_indices, all_pokemon, return_list):
    for index in pokemon_indices:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_pokemon[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(index, len(all_pokemon)):
            enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[k]
            enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
            results = battle_all_shields(ally, enemy)
            return_list.append({'pokemon': [str(ally), str(enemy)], 'result': results})
    return return_list


def main(type_restrictions: tuple, cup_name: str):
    start_time = time()
    gm = GameMaster()

    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(type_restrictions))

    print("Creating Processes...")
    num_processes = 8
    indices_lists = []
    for i in range(num_processes):
        indices_lists.append([])
    for i in range(len(all_possibilities)):
        for j in range(num_processes):
            if i % num_processes == j:
                indices_lists[j].append(i)
    print("Starting Processes...")
    jobs = []
    manager = Manager()
    return_list = manager.list()
    for indices_list in indices_lists:
        p = Process(target=fill_table_for_pokemon, args=(indices_list, all_possibilities, return_list))
        jobs.append(p)
        p.start()

    for proc in jobs:
        proc.join()

    pokemon_results = {}
    for result in return_list:
        pokemon = result['pokemon']
        ally_result = result['result']
        enemy_result = ((x[1], x[0]) for x in ally_result)
        ally_name = pokemon[0].split(', ')[0]
        if ally_name not in pokemon_results:
            pokemon_results[ally_name] = {}
        if pokemon[0] not in pokemon_results[ally_name]:
            pokemon_results[ally_name][pokemon[0]] = []
        pokemon_results[ally_name][pokemon[0]].append({'enemy': pokemon[1], 'results': ally_result})
        if pokemon[0] == pokemon[1]:
            continue
        enemy_name = pokemon[1].split(', ')[0]
        if enemy_name not in pokemon_results:
            pokemon_results[enemy_name] = {}
        if pokemon[1] not in pokemon_results[enemy_name]:
            pokemon_results[enemy_name][pokemon[1]] = []
        pokemon_results[enemy_name][pokemon[1]].append({'enemy': pokemon[0], 'results': enemy_result})

    for pokemon in pokemon_results:
        db = TinyDB(f"{path}/data/databases/{cup_name}/{pokemon}.json")
        table = db.table('battle_results')
        table.insert_multiple(pokemon_results[pokemon])
        db.close()

    elapsed_time = time() - start_time
    print()
    print(elapsed_time)
    print("Done.")


if __name__ == '__main__':
    cups_and_restrictions = (
        ('boulder', ('rock', 'steel', 'ground', 'fighting')),
        ('twilight', ('poison', 'ghost', 'dark', 'fairy')),
        ('tempest', ('ground', 'ice', 'electric', 'flying')),
        ('kingdom', ('fire', 'steel', 'ice', 'dragon'))
    )
    for cup, restrictions in cups_and_restrictions:
        main(restrictions, cup)
