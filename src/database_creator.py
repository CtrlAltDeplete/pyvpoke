from multiprocessing import Process, Manager
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
from tinydb import TinyDB


def fill_table_for_pokemon(pokemon_indices, all_pokemon, return_dict, key):
    global table
    return_dict[key] = []
    for index in pokemon_indices:
        ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_pokemon[index]
        ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
        for k in range(index + 1, len(all_pokemon)):
            enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_pokemon[k]
            enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
            results = battle_all_shields(ally, enemy)
            return_dict[key].extend([{'ally': str(ally), 'enemy': str(enemy), 'result': results[0]},
                                     {'ally': str(enemy), 'enemy': str(ally), 'result': results[1]}])
    return_dict[key] = tuple(return_dict[key])


def main():
    gm = GameMaster()

    all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(['fire', 'ice', 'dragon', 'steel']))
    print("Creating Processes...")
    num_processes = 20
    indices_lists = []
    for i in range(num_processes):
        indices_lists.append([])
    for i in range(len(all_possibilities)):
        for j in range(num_processes):
            if i // num_processes == j:
                indices_lists[j].append(i)
    print("Processes Created, Joining Processes...")
    jobs = []
    manager = Manager()
    return_dict = manager.dict()
    i = 0
    for indices_list in indices_lists:
        p = Process(target=fill_table_for_pokemon, args=(indices_list, all_possibilities, return_dict, i))
        jobs.append(p)
        p.start()
        i += 1
    finished_processes = 0
    print(f"0.0% complete.")
    for proc in jobs:
        proc.join()
        finished_processes += 1
        print(f"{round(100 * finished_processes / num_processes, 1)}% complete.")

    db = TinyDB(f"{path}/data/databases/kingdom.json")
    table = db.table('battle_results')
    for key in return_dict:
        table.insert_multiple(return_dict[key])


if __name__ == '__main__':
    main()
