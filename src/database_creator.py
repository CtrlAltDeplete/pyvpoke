from multiprocessing import Process
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
import sqlite3
import datetime


def fill_table_for_pokemon(pokemon, all_pokemon, cup):
    ally_name, ally_fast, ally_charge_1, ally_charge_2 = pokemon
    ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
    to_write = []
    for enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 in all_pokemon:
        enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
        results = battle_all_shields(ally, enemy)
        to_write.append([str(ally), str(enemy)] + list(x[0] for x in results))

    command = "INSERT INTO battle_sims(ally, enemy, zeroVzero, zeroVone, zeroVtwo, oneVzero, oneVone, oneVtwo, twoVzero, twoVone, twoVtwo) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    cur.executemany(command, to_write)
    conn.commit()
    conn.close()


def build_database(cup, restrictions):
    gm = GameMaster()
    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(restrictions))
    # all_possibilities = []
    # for pokemon in ['Blastoise', 'Charizard', 'Venusaur']:
    #     all_possibilities.extend([x for x in gm.all_movesets_for_pokemon(pokemon)])

    print("Starting Processes...")
    num_processes = 7
    columns = (
        ' '.join(('id', 'INTEGER PRIMARY KEY AUTOINCREMENT')),
        ' '.join(('ally', 'TEXT')),
        ' '.join(('enemy', 'TEXT')),
        ' '.join(('zeroVzero', 'INTEGER')),
        ' '.join(('zeroVone', 'INTEGER')),
        ' '.join(('zeroVtwo', 'INTEGER')),
        ' '.join(('oneVzero', 'INTEGER')),
        ' '.join(('oneVone', 'INTEGER')),
        ' '.join(('oneVtwo', 'INTEGER')),
        ' '.join(('twoVzero', 'INTEGER')),
        ' '.join(('twoVone', 'INTEGER')),
        ' '.join(('twoVtwo', 'INTEGER')),
    )
    command = f"CREATE TABLE battle_sims ({', '.join(columns)})"

    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    cur.execute(command)
    conn.commit()
    conn.close()

    for i in range(0, len(all_possibilities), num_processes):
        jobs = []
        for j in range(min(num_processes, len(all_possibilities) - i)):
            pokemon = all_possibilities[i + j]
            jobs.append(Process(target=fill_table_for_pokemon, args=(pokemon, all_possibilities, cup)))
            jobs[j].start()

        for p in range(min(num_processes, len(all_possibilities) - i)):
            jobs[p].join()

        print(f"{datetime.datetime.now()}: {percent_calculator(len(all_possibilities), i + num_processes)}% finished.")

    print()
    print("Done.")


def percent_calculator(total_pokemon, current_index):
    return round(100 * current_index / total_pokemon, 1)


if __name__ == '__main__':
    # cups_and_restrictions = (
        # ('boulder', ('rock', 'steel', 'ground', 'fighting')),
    #     ('twilight', ('poison', 'ghost', 'dark', 'fairy')),
    #     ('tempest', ('ground', 'ice', 'electric', 'flying')),
    #     ('kingdom', ('fire', 'steel', 'ice', 'dragon'))
    # )
    # for i in range(4):
    #     cup, restrictions = cups_and_restrictions[i]
    #     build_database(cup, restrictions)
    build_database('nightmare', ('psychic', 'fighting', 'dark'))
