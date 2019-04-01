from src.gamemaster import path, GameMaster
from src.meta_calculator import ordered_top_pokemon, ordered_movesets_for_pokemon
from multiprocessing import Process


with open(f"{path}/data/move_template.html") as f:
    move_template = f.read()
with open(f"{path}/data/list_item_template.html") as f:
    listing_template = f.read()
gm = GameMaster()


def create_ranking_table(cup: str, save_name: str):
    list_items = []
    for pokemon in ordered_top_pokemon(cup):
        name = pokemon['name']
        rank = pokemon['relative_rank']
        percentile = round(100 - pokemon['absolute_rank'], 1)
        moves = ordered_movesets_for_pokemon(cup, name)
        moves_html = []
        for moveset in moves:
            moves_html.append(fill_move_template(name, moveset, cup))
        moves_html = "\n".join(moves_html)
        if percentile >= 100 - 4.26:
            color = 'green'
        elif percentile >= 100 - 4.26 - 4.26 ** 2:
            color = 'yellow'
        else:
            color = 'red'
        list_items.append(listing_template.format(name, name, rank, name, name, color, percentile, percentile, name, moves_html))
    list_items = "\n".join(list_items).replace("♂", " (Male)").replace("♀", " (Female)")
    with open(save_name, 'w') as f:
        f.write(list_items)


def fill_move_template(pokemon_name: str, move_info: tuple, cup: str):
    absolute_rank, fast_name, charge_1_name, charge_2_name = move_info
    fast_type = gm.get_move(fast_name)['type']
    charge_1_type = gm.get_move(charge_1_name)['type']
    charge_2_type = gm.get_move(charge_2_name)['type']
    card_address = f"{cup}+{pokemon_name}+{fast_name}+{charge_1_name}+{charge_2_name}"
    return move_template.format(round(100 - absolute_rank, 1), fast_type, fast_name, charge_1_type, charge_1_name,
                                charge_2_type, charge_2_name, card_address, fast_type, fast_name, charge_1_type,
                                charge_1_name, charge_2_type, charge_2_name, round(100 - absolute_rank, 1), card_address
                                )


if __name__ == '__main__':
    jobs = []
    cup = ['boulder', 'twilight', 'tempest', 'kingdom']
    for i in range(4):
        jobs.append(Process(target=create_ranking_table, args=(cup[i], f'{path}/web/{cup[i]}.html')))
        jobs[i].start()
    for i in range(4):
        jobs[i].join()
        print(f"Finished {cup[i]} cup.")
