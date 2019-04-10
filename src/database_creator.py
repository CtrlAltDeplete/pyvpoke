from multiprocessing import Process
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
from tinydb import TinyDB
import datetime
import os


def fill_table_for_pokemon(pokemon_indices, all_pokemon, cup, pokemon):
    to_write = []
    for index in pokemon_indices:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_pokemon[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(index, len(all_pokemon)):
            enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[k]
            enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
            results = battle_all_shields(ally, enemy)
            to_write.append({'pokemon': [str(ally), str(enemy)], 'result': results})
        for j in pokemon_indices:
            if j > index:
                enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[j]
                enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
                results = battle_all_shields(ally, enemy)
                to_write.append({'pokemon': [str(ally), str(enemy)], 'result': results})
    db = TinyDB(f"{path}/data/databases/{cup}/{pokemon}.info")
    table = db.table('battle_results')
    table.insert_multiple(to_write)
    db.close()


def build_first_half_of_database(cup, restrictions):
    gm = GameMaster()

    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(restrictions))
    all_pokemon = tuple([x for x in gm.iter_pokemon(restrictions)])

    print("Starting Processes...")
    num_processes = 8

    for i in range(0, len(all_pokemon), 8):
        jobs = []
        for j in range(min(num_processes, len(all_pokemon) - i)):
            pokemon = all_pokemon[i + j]
            pokemon_indices = []
            for k, x in enumerate(all_possibilities):
                if x[0] == pokemon:
                    pokemon_indices.append(k)
            jobs.append(Process(target=fill_table_for_pokemon, args=(pokemon_indices, all_possibilities, cup, pokemon)))
            jobs[j].start()

        for p in range(min(num_processes, len(all_pokemon) - i)):
            jobs[p].join()

        print(f"{datetime.datetime.now()}: {percent_calculator(len(all_pokemon), i + 8)}% finished.")

    print()
    print("Done.")


def build_second_half_of_database(cup):
    cup_directory = f"{path}/data/databases/{cup}"
    all_db_files = os.listdir(cup_directory)
    for i in range(len(all_db_files) - 1, -1, -1):
        pokemon_to_search_for = all_db_files[i].split(".")[0]
        db = TinyDB(f"{cup_directory}/{all_db_files[i]}")
        table = db.table('battle_results')
        docs = table.all()
        to_write = []
        for doc in docs:
            ally = doc['pokemon'][0]
            enemy = doc['pokemon'][1]
            if ally != enemy and ally.split(', ')[0] == enemy.split(', ')[0]:
                result = []
                for r in doc['result']:
                    result.append((r[1], r[0]))
                to_write.append({'pokemon': [enemy, ally], 'result': result})
        if to_write:
            table.insert_multiple(to_write)
        db.close()
        for j in range(0, i, 1):
            db = TinyDB(f"{cup_directory}/{all_db_files[j]}")
            table = db.table('battle_results')
            docs = table.all()
            to_write = []
            for doc in docs:
                if pokemon_to_search_for == doc['pokemon'][1].split(', ')[0]:
                    pokemon = [doc['pokemon'][1], doc['pokemon'][0]]
                    result = []
                    for r in doc['result']:
                        result.append((r[1], r[0]))
                    to_write.append({'pokemon': pokemon, 'result': result})
            db.close()
            if to_write:
                db = TinyDB(f'{cup_directory}/{all_db_files[i]}')
                table = db.table('battle_results')
                table.insert_multiple(to_write)
                db.close()
        print(f"{percent_calculator(len(all_db_files), len(all_db_files) - i)}% Finished.")


def percent_calculator(total_pokemon, current_index):
    current_finished = 0
    total = 0
    for i in range(total_pokemon):
        if i <= current_index:
            current_finished += (total_pokemon - i)
        total += (total_pokemon - i)
    return round(100 * current_finished / total, 1)


if __name__ == '__main__':
    cups_and_restrictions = (
        # ('boulder', ('rock', 'steel', 'ground', 'fighting')),
        ('twilight', ('poison', 'ghost', 'dark', 'fairy')),
        # ('tempest', ('ground', 'ice', 'electric', 'flying')),
        # ('kingdom', ('fire', 'steel', 'ice', 'dragon'))
    )
    # for i in range(3):
    #     cup, restrictions = cups_and_restrictions[i]
    #     build_first_half_of_database(cup, restrictions)
    for cup, restrictions in cups_and_restrictions:
        build_second_half_of_database(cup)
