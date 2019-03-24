from tinydb import TinyDB
from src.battle import battle_all_shields
from src.gamemaster import path, GameMaster
from src.pokemon import Pokemon
import time


db = TinyDB(f"{path}/data/databases/kingdom.json")
table = db.table('battle_results')
gm = GameMaster()

all_possibilities = tuple((pokemon, fast, charge_1, charge_2) for pokemon, fast, charge_1, charge_2 in gm.iter_pokemon_move_set_combos(['fire', 'ice', 'dragon', 'steel']))
print("All Possibilities generated...")
total = len(all_possibilities) * (len(all_possibilities) - 1) / 2
current = 0
previous_percent = 0
start_time = time.time()
for i in range(len(all_possibilities)):
    ally_name, ally_fast, ally_charge_1, ally_charge_2 = all_possibilities[i]
    ally = Pokemon(ally_name, ally_fast, ally_charge_1, ally_charge_2)
    for j in range(i + 1, len(all_possibilities)):
        enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2 = all_possibilities[j]
        enemy = Pokemon(enemy_name, enemy_fast, enemy_charge_1, enemy_charge_2)
        results = battle_all_shields(ally, enemy)
        table.insert({'ally': str(ally), 'enemy': str(enemy), 'result': results[0]})
        table.insert({'ally': str(enemy), 'enemy': str(ally), 'result': results[1]})
        current += 1
        new_percent = round(100 * current / total, 1)
        if new_percent - previous_percent >= 0.5:
            time_remaining = time.localtime(time.time() + (time.time() - start_time) * total / current)
            print(f"{new_percent}% complete.")
            print(f"ETA: {time_remaining.tm_mon}/{time_remaining.tm_mday}/{time_remaining.tm_year}\t{time_remaining.tm_hour}:{time_remaining.tm_min}")
            print()
            previous_percent = new_percent
