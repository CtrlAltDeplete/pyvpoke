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
    num_processes = 10
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
        ('twilight', ('poison', 'ghost', 'dark', 'fairy')),
        ('tempest', ('ground', 'ice', 'electric', 'flying')),
        ('kingdom', ('fire', 'steel', 'ice', 'dragon'))
    )
    moves_to_add = (
        # ('Alakazam', 'Dazzling Gleam', 'charge'),
        # ('Alakazam', 'Psychic', 'charge'),
        # ('Ampharos', 'Dragon Pulse', 'charge'),
        # ('Arcanine', 'Bite', 'fast'),
        # ('Arcanine', 'Bulldoze', 'charge'),
        # ('Arcanine', 'Flamethrower', 'charge'),
        # ('Articuno', 'Hurricane', 'charge'),
        # ('Beedrill', 'Bug Bite', 'fast'),
        # ('Blastoise', 'Hydro Cannon', 'charge'),
        # ('Blaziken', 'Stone Edge', 'charge'),
        # ('Breloom', 'Grass Knot', 'charge'),
        # ('Butterfree', 'Bug Bite', 'fast'),
        # ('Chansey', 'Psybeam', 'charge'),
        # ('Charizard', 'Ember', 'fast'),
        # ('Charizard', 'Wing Attack', 'fast'),
        # ('Charizard', 'Flamethrower', 'charge'),
        # ('Charizard', 'Blast Burn', 'charge'),
        # ('Charmeleon', 'Scratch', 'fast'),
        # ('Clefable', 'Pound', 'fast'),
        # ('Cleffa', 'Psychic', 'charge'),
        # ('Cleffa', 'Body Slam', 'charge'),
        # ('Cloyster', 'Blizzard', 'charge'),
        # ('Cloyster', 'Icy Wind', 'charge'),
        # ('Delibird', 'Ice Shard', 'fast'),
        # ('Delibird', 'Quick Attack', 'fast'),
        # ('Dewgong', 'Ice Shard', 'fast'),
        # ('Dewgong', 'Aqua Jet', 'charge'),
        # ('Dewgong', 'Icy Wind', 'charge'),
        # ('Diglett', 'Mud Shot', 'fast'),
        # ('Dodrio', 'Air Cutter', 'charge'),
        # ('Doduo', 'Swift', 'charge'),
        # ('Dragonite', 'Dragon Breath', 'fast'),
        # ('Dragonite', 'Dragon Claw', 'charge'),
        # ('Dragonite', 'Dragon Pulse', 'charge'),
        # ('Lapras', 'Ice Shard', 'fast'),
        # ('Lapras', 'Dragon Pulse', 'charge'),
        # ('Lapras', 'Ice Beam', 'charge'),
        # ('Tyranitar', 'Smack Down', 'fast'),
        # ('Feraligatr', 'Hydro Cannon', 'charge'),
        # ('Typhlosion', 'Blast Burn', 'charge'),
        # ('Venusaur', 'Frenzy Plant', 'charge'),
        ('Dragonite', 'Draco Meteor', 'charge'),
        ('Dugtrio', 'Mud Shot', 'fast'),
        ('Eevee', 'Body Slam', 'charge'),
        ('Eevee', 'Last Resort', 'charge'),
        ('Ekans', 'Gunk Shot', 'charge'),
        ('Electrode', 'Tackle', 'fast'),
        ('Elekid', 'Thunderbolt', 'charge'),
        ('Espeon', 'Last Resort', 'charge'),
        ('Exeggutor', 'Confusion', 'fast'),
        ('Exeggutor', 'Zen Headbutt', 'fast'),
        ('Farfetch\'d', 'Cut', 'fast'),
        ('Fearow', 'Twister', 'charge'),
        ('Flareon', 'Heat Wave', 'charge'),
        ('Flareon', 'Last Resort', 'charge'),
        ('Gastly', 'Sucker Punch', 'fast'),
        ('Gastly', 'Ominous Wind', 'charge'),
        ('Gengar', 'Shadow Claw', 'fast'),
        ('Gengar', 'Lick', 'fast'),
        ('Gengar', 'Sludge Wave', 'charge'),
        ('Gengar', 'Dark Pulse', 'charge'),
        ('Gengar', 'Psychic', 'charge'),
        ('Golbat', 'Ominous Wind', 'charge'),
        ('Golem', 'Mud Shot', 'fast'),
        ('Golem', 'Ancient Power', 'charge'),
        ('Graveler', 'Mud Shot', 'fast'),
        ('Graveler', 'Rock Slide', 'charge'),
        ('Grimer', 'Acid', 'fast'),
        ('Gyarados', 'Dragon Breath', 'fast'),
        ('Gyarados', 'Dragon Tail', 'fast'),
        ('Gyarados', 'Dragon Pulse', 'charge'),
        ('Gyarados', 'Twister', 'charge'),
        ('Haunter', 'Lick', 'fast'),
        ('Haunter', 'Shadow Ball', 'charge'),
        ('Hitmonchan', 'Rock Smash', 'fast'),
        ('Hitmonchan', 'Brick Break', 'charge'),
        ('Hitmonlee', 'Stomp', 'charge'),
        ('Hitmonlee', 'Brick Break', 'charge'),
        ('Hypno', 'Psyshock', 'charge'),
        ('Hypno', 'Shadow Ball', 'charge'),
        ('Igglybuff', 'Body Slam', 'charge'),
        ('Jigglypuff', 'Play Rough', 'charge'),
        ('Jigglypuff', 'Body Slam', 'charge'),
        ('Jolteon', 'Last Resort', 'charge'),
        ('Jynx', 'Pound', 'fast'),
        ('Jynx', 'Ice Punch', 'charge'),
        ('Kabutops', 'Fury Cutter', 'fast'),
        ('Kangaskhan', 'Brick Break', 'charge'),
        ('Kangaskhan', 'Stomp', 'charge'),
        ('Kingdra', 'Water Gun', 'fast'),
        ('Kingler', 'Mud Shot', 'fast'),
        ('Koffing', 'Acid', 'fast'),
        ('Loudred', 'Crunch', 'charge'),
        ('Machamp', 'Karate Chop', 'fast'),
        ('Machamp', 'Cross Chop', 'charge'),
        ('Machamp', 'Stone Edge', 'charge'),
        ('Machamp', 'Submission', 'charge'),
        ('Machoke', 'Cross Chop', 'charge'),
        ('Machop', 'Low Kick', 'fast'),
        ('Magby', 'Flamethrower', 'charge'),
        ('Magneton', 'Thunder Shock', 'fast'),
        ('Magneton', 'Discharge', 'charge'),
        ('Mamoswine', 'Ancient Power', 'charge'),
        ('Meganium', 'Frenzy Plant', 'charge'),
        ('Meowth', 'Body Slam', 'charge'),
        ('Metagross', 'Meteor Mash', 'charge'),
        ('Mewtwo', 'Shadow Ball', 'charge'),
        ('Mewtwo', 'Hyper Beam', 'charge'),
        ('Moltres', 'Ember', 'fast'),
        ('Moltres', 'Sky Attack', 'charge'),
        ('Muk', 'Acid', 'fast'),
        ('Muk', 'Lick', 'fast'),
        ('Nidoking', 'Fury Cutter', 'fast'),
        ('Ninetales', 'Ember', 'fast'),
        ('Ninetales', 'Fire Blast', 'charge'),
        ('Ninetales', 'Flamethrower', 'charge'),
        ('Omanyte', 'Rock Tomb', 'charge'),
        ('Omanyte', 'Brine', 'charge'),
        ('Omastar', 'Rock Throw', 'fast'),
        ('Omastar', 'Rock Slide', 'charge'),
        ('Onix', 'Iron Head', 'charge'),
        ('Onix', 'Rock Slide', 'charge'),
        ('Parasect', 'Bug Bite', 'fast'),
        ('Persian', 'Night Slash', 'charge'),
        ('Pichu', 'Quick Attack', 'fast'),
        ('Pidgeot', 'Wing Attack', 'fast'),
        ('Pidgeot', 'Air Cutter', 'charge'),
        ('Pikachu', 'Present', 'fast'),
        ('Pikachu', 'Surf', 'charge'),
        ('Pikachu', 'Thunder', 'charge'),
        ('Pinsir', 'Fury Cutter', 'fast'),
        ('Pinsir', 'Submission', 'charge'),
        ('Politoed', 'Earthquake', 'charge'),
        ('Poliwhirl', 'Scald', 'charge'),
        ('Poliwrath', 'Mud Shot', 'fast'),
        ('Poliwrath', 'Submission', 'charge'),
        ('Ponyta', 'Fire Blast', 'charge'),
        ('Porygon', 'Quick Attack', 'fast'),
        ('Porygon', 'Tackle', 'fast'),
        ('Porygon', 'Zen Headbutt', 'fast'),
        ('Porygon', 'Discharge', 'charge'),
        ('Porygon', 'Psybeam', 'charge'),
        ('Porygon', 'Signal Beam', 'charge'),
        ('Primeape', 'Karate Chop', 'fast'),
        ('Primeape', 'Cross Chop', 'charge'),
        ('Raichu', 'Thunder Shock', 'fast'),
        ('Raichu', 'Thunder', 'charge'),
        ('Rapidash', 'Ember', 'fast'),
        ('Rhydon', 'Megahorn', 'charge'),
        ('Sandshrew', 'Rock Tomb', 'charge'),
        ('Sceptile', 'Frenzy Plant', 'charge'),
        ('Scyther', 'Steel Wing', 'fast'),
        ('Scyther', 'Bug Buzz', 'charge'),
        ('Seadra', 'Blizzard', 'charge'),
        ('Seaking', 'Poison Jab', 'fast'),
        ('Seaking', 'Icy Wind', 'charge'),
        ('Seaking', 'Drill Run', 'charge'),
        ('Seel', 'Water Gun', 'fast'),
        ('Seel', 'Aqua Jet', 'charge'),
        ('Shadinja', 'Bite', 'fast'),
        ('Shedinja', 'Struggle Bug', 'fast'),
        ('Smoochum', 'Frost Breath', 'fast'),
        ('Snorlax', 'Body Slam', 'charge'),
        ('Spearow', 'Twister', 'charge'),
        ('Starmie', 'Quick Attack', 'fast'),
        ('Starmie', 'Tackle', 'fast'),
        ('Starmie', 'Psybeam', 'charge'),
        ('Staryu', 'Quick Attack', 'fast'),
        ('Suicune', 'Hidden Power', 'fast'),
        ('Tangela', 'Power Whip', 'charge'),
        ('Togepi', 'Zen Headbutt', 'fast'),
        ('Togetic', 'Steel Wing', 'fast'),
        ('Togetic', 'Zen Headbutt', 'fast'),
        ('Umbreon', 'Last Resort', 'charge'),
        ('Vaporeon', 'Last Resort', 'charge'),
        ('Venomoth', 'Bug Bite', 'fast'),
        ('Venomoth', 'Poison Fang', 'charge'),
        ('Voltorb', 'Signal Beam', 'charge'),
        ('Weepinbell', 'Razor Leaf', 'fast'),
        ('Zapdos', 'Thunder Shock', 'fast'),
        ('Zapdos', 'Discharge', 'charge'),
        ('Zubat', 'Sludge Bomb', 'charge')
    )

    gm = GameMaster()

    for pokemon, move_name, move_type in moves_to_add:
        pokemon_data = gm.get_pokemon(pokemon)
        if move_name in pokemon_data[move_type]:
            print(f"{pokemon} already has {move_name}.")
            continue
        else:
            with open(f"{path}/data/pokemon.json", 'r') as f:
                data = load(f)
            data[pokemon][move_type].append(move_name)
            with open(f"{path}/data/pokemon.json", 'w') as f:
                dump(data, f)
            del gm
            gm = GameMaster()
        move_data = gm.get_move(move_name)
        for cup, restrictions in cups_and_restrictions:
            if any([x in restrictions for x in pokemon_data['types']]):
                print(f"Adding {pokemon} with {move_name} to {cup}.")
                add_pokemon_move(cup, restrictions, pokemon, move_name)
        print()
