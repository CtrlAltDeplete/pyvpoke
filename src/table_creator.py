from src.gamemaster import path, GameMaster
from src.meta_calculator import ordered_top_pokemon, ordered_movesets_for_pokemon


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
        percentile = round(100 - pokemon['absolute_rank'], 0)
        moves = ordered_movesets_for_pokemon(cup, name)
        moves_html = []
        for moveset in moves:
            moves_html.append(fill_move_template(name, moveset, cup))
        moves_html = "\n".join(moves_html)
        list_items.append(listing_template.format(name, name, rank, name, percentile, percentile, name, moves_html))
    list_items = "\n".join(list_items).replace("♂", " (Male)").replace("♀", " (Female)")
    with open(save_name, 'w') as f:
        f.write(list_items)


def fill_move_template(pokemon_name: str, move_info: tuple, cup: str):
    absolute_rank, fast_name, charge_1_name, charge_2_name = move_info
    fast_type = gm.get_move(fast_name)['type']
    charge_1_type = gm.get_move(charge_1_name)['type']
    charge_2_type = gm.get_move(charge_2_name)['type']
    card_address = f"{cup}+{pokemon_name}+{fast_type}+{charge_1_name}+{charge_2_name}"
    return move_template.format(round(100 - absolute_rank, 0), fast_type, fast_name, charge_1_type, charge_1_name,
                                charge_2_type, charge_2_name, card_address)


if __name__ == '__main__':
    for cup in ['twilight', 'tempest', 'kingdom']:
        create_ranking_table(cup, f'{path}/web/{cup}.html')
        print(f"Finished {cup} cup.")
