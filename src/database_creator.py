from multiprocessing import Process, Manager
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
from time import time
from tinydb import TinyDB
from json import load, dump


def fill_table_for_pokemon(pokemon_indices, all_pokemon, return_list):
    previous_percent = 0
    total = sum([x * (x - 1) / 2 for x in pokemon_indices])
    current = 0

    for index in pokemon_indices:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_pokemon[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(index, len(all_pokemon)):
            enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[k]
            enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
            results = battle_all_shields(ally, enemy)
            if str(ally) == "Hitmonchan, Counter, Ice Punch, Power-Up Punch" and str(enemy) == "Medicham, Counter, Psychic, Power-Up Punch":
                for r in results:
                    print(r)
            return_list.append({'pokemon': [str(ally), str(enemy)], 'result': results})
            current += 1
            if round(100 * current / total) > 1 + previous_percent:
                previous_percent = round(100 * len(return_list) / total)
                print(f"Thread {pokemon_indices[0]}: {previous_percent}% complete.")
    return return_list


def add_pokemon_move(cup_name: str, type_restrictions: tuple, pokemon: str, move_name: str):
    gm = GameMaster()
    all_possibilites = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(type_restrictions))

    indices_list = []
    for i in range(len(all_possibilites)):
        if pokemon in all_possibilites[i] and move_name in all_possibilites[i]:
            indices_list.append(i)
    to_write = []
    for index in indices_list:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_possibilites[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(len(all_possibilites)):
            if k not in indices_list[:indices_list.index(index)]:
                enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_possibilites[k]
                enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
                results = battle_all_shields(ally, enemy)
                to_write.append({'pokemon': [str(ally), str(enemy)], 'result': results})
    db = TinyDB(f"{path}/data/databases/{cup_name}.json")
    table = db.table('battle_results')
    table.insert_multiple(to_write)
    db.close()
    print(f"Finished {pokemon} with {move_name}.")


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

    db = TinyDB(f"{path}/data/databases/{cup_name}.json")
    table = db.table('battle_results')

    table.insert_multiple(return_list)

    elapsed_time = time() - start_time
    print()
    print(len(table))
    print(elapsed_time)
    print("Done.")
    db.close()


if __name__ == '__main__':
    cups_and_restrictions = (
        ('boulder', ('rock', 'steel', 'ground', 'fighting')),
        # ('twilight', ('poison', 'ghost', 'dark', 'fairy')),
        # ('tempest', ('ground', 'ice', 'electric', 'flying')),
        # ('kingdom', ('fire', 'steel', 'ice', 'dragon'))
    )
    for cup, restrictions in cups_and_restrictions:
        main(restrictions, cup)
