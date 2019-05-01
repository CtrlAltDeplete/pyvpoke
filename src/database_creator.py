from multiprocessing import Process
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster, banned
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
    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(restrictions) if pokemon not in banned)
    # all_possibilities = []
    # for pokemon in ['Blastoise', 'Charizard', 'Venusaur']:
    #     all_possibilities.extend([x for x in gm.all_movesets_for_pokemon(pokemon)])

    print("Starting Processes...")
    num_processes = 8
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

    start_time = datetime.datetime.now()
    for i in range(0, len(all_possibilities), num_processes):
        jobs = []
        for j in range(min(num_processes, len(all_possibilities) - i)):
            pokemon = all_possibilities[i + j]
            jobs.append(Process(target=fill_table_for_pokemon, args=(pokemon, all_possibilities, cup)))
            jobs[j].start()

        for p in range(min(num_processes, len(all_possibilities) - i)):
            jobs[p].join()

        print(percent_calculator(len(all_possibilities), i + num_processes, start_time))

    print()
    print("Done.")


def repair_database(cup, restrictions):
    gm = GameMaster()
    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(restrictions) if pokemon not in banned)
    # all_possibilities = []
    # for pokemon in ['Blastoise', 'Charizard', 'Venusaur']:
    #     all_possibilities.extend([x for x in gm.all_movesets_for_pokemon(pokemon)])

    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()

    repair_dict = {}
    for i, ally in enumerate(all_possibilities):
        ally_str = ', '.join(ally) if ally[3] else ', '.join(ally[:-1])
        command = "SELECT id FROM battle_sims WHERE ally = ?"
        cur.execute(command, (ally_str,))
        rows = cur.fetchall()
        if len(rows) == len(all_possibilities):
            print(f"{round(100 * i / len(all_possibilities), 2)}%")
            continue
        elif not rows:
            index = 0
        else:
            index = len(rows)
        repair_dict[ally] = [x for x in all_possibilities[index:]]
        print(f"{round(100 * i / len(all_possibilities), 2)}%")

    conn.close()

    print("Starting Processes...")
    num_processes = 8

    start_time = datetime.datetime.now()
    keys = [x for x in repair_dict.keys()]
    for i in range(0, len(keys), num_processes):
        jobs = []
        for j in range(min(num_processes, len(keys) - i)):
            pokemon = keys[i + j]
            jobs.append(Process(target=fill_table_for_pokemon, args=(pokemon, repair_dict[pokemon], cup)))
            jobs[j].start()

        for p in range(min(num_processes, len(keys) - i)):
            jobs[p].join()

        print(percent_calculator(len(keys), i + num_processes, start_time))

    print()
    print("Done.")


def percent_calculator(total_pokemon, current_index, start_time):
    now = datetime.datetime.now()
    percent = round(100 * current_index / total_pokemon, 1)
    finish_time = start_time + (total_pokemon / current_index) * (now - start_time)
    return f"{percent}%\t\t{finish_time.strftime('%Y-%m-%d %H:%M:%S')}"


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
    gm = GameMaster()
    cup, restrictions = ('regionals', ('rock', 'steel', 'ground', 'poison', 'ghost', 'fairy', 'ice', 'electric', 'flying', 'fire', 'dragon', 'psychic', 'fighting', 'dark'))

    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in
                              gm.iter_pokemon_move_set_combos(restrictions) if pokemon not in banned)
    pokemon_to_add = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.all_movesets_for_pokemon('Sableye'))
    pokemon_to_add = pokemon_to_add + tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.all_movesets_for_pokemon('Medicham'))

    conn = sqlite3.connect(f"{path}/data/databases/regionals.db")
    cur = conn.cursor()
    for i, ally in enumerate(pokemon_to_add):
        command = "SELECT * FROM battle_sims WHERE ally = ?"
        ally_str = ', '.join(ally if ally[-1] else ally[:-1])
        cur.execute(command, (ally_str,))
        rows = cur.fetchall()
        to_write = []
        for row in rows:
            if 'Medicham' not in row[2] and 'Sableye' not in row[2]:
                new_row = [row[2], row[1]]
                for score in row[3:]:
                    new_row.append(1000 - score)
                to_write.append(new_row)
        command = "INSERT INTO battle_sims(ally, enemy, zeroVzero, zeroVone, zeroVtwo, oneVzero, oneVone, oneVtwo, twoVzero, twoVone, twoVtwo) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        cur.executemany(command, to_write)
        print(f"{round(100 * i / len(pokemon_to_add), 1)}%")
    conn.commit()
    conn.close()

    print()
    print("Done.")
