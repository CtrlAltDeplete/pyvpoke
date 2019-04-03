from src.gamemaster import path, GameMaster
from src.meta_calculator import ordered_top_pokemon, ordered_movesets_for_pokemon
from multiprocessing import Process
from json import dump


with open(f"{path}/data/move_template.html") as f:
    move_template = f.read()
with open(f"{path}/data/list_item_template.html") as f:
    listing_template = f.read()
gm = GameMaster()


def create_ranking_table(cup: str):
    list_items = []
    for pokemon in ordered_top_pokemon(cup):
        name = pokemon['name'].replace("♂", " (Male)").replace("♀", " (Female)")
        rank = pokemon['relative_rank']
        percentile = round(100 - pokemon['absolute_rank'], 1)
        moves = ordered_movesets_for_pokemon(cup, name)
        moves_html = []
        for moveset in moves:
            moves_html.append(fill_move_template(name, moveset, cup))
        if percentile >= 100 - 4.26:
            color = 'green'
        elif percentile >= 100 - 4.26 - 4.26 ** 2:
            color = 'yellow'
        else:
            color = 'red'
        list_items.append([name, name, rank, name, name, color, percentile, percentile, name, moves_html])
    with open(f"{path}/web/{cup}.rankings", 'w') as f:
        dump(list_items, f)


def fill_move_template(pokemon_name: str, move_info: tuple, cup: str):
    absolute_rank, fast_name, charge_1_name, charge_2_name = move_info
    fast_type = gm.get_move(fast_name)['type']
    charge_1_type = gm.get_move(charge_1_name)['type']
    charge_2_type = gm.get_move(charge_2_name)['type']
    card_address = f"{cup}+{pokemon_name}+{fast_name}+{charge_1_name}+{charge_2_name}"
    return [round(100 - absolute_rank, 1), fast_type, fast_name, charge_1_type, charge_1_name, charge_2_type,
            charge_2_name, card_address, fast_type, fast_name, charge_1_type, charge_1_name, charge_2_type,
            charge_2_name, round(100 - absolute_rank, 1), card_address]


def main():
    jobs = []
    cup = ['boulder', 'twilight', 'tempest', 'kingdom']
    for i in range(4):
        jobs.append(Process(target=create_ranking_table, args=(cup[i],)))
        jobs[i].start()
    for i in range(4):
        jobs[i].join()
        print(f"Finished {cup[i]} cup.")


if __name__ == '__main__':
    main()
