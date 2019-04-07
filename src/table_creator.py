from src.gamemaster import path, GameMaster
from src.meta_calculator import (
    ordered_top_pokemon, ordered_movesets_for_pokemon,
)
from src.pokemon import Pokemon
from multiprocessing import Process
from tinydb import TinyDB, Query
from json import dump


gm = GameMaster()


def create_ranking_table(cup: str):
    list_items = []
    for pokemon in ordered_top_pokemon(cup):
        name = pokemon['name']
        rank = pokemon['relative_rank']
        percentile = round(100 - pokemon['absolute_rank'], 1)
        moves = ordered_movesets_for_pokemon(cup, name)
        moves_html = []
        for moveset in moves:
            html = fill_move_template(name, moveset, cup)
            if html:
                moves_html.append(html)
        if not moves_html:
            continue
        if percentile >= 100 - 4.26:
            color = 'green'
        elif percentile >= 100 - 4.26 - 4.26 ** 2:
            color = 'yellow'
        else:
            color = 'red'
        p = Pokemon(name, pokemon['fast'], pokemon['charge_1'], pokemon['charge_2'])
        level = p.level
        atkIV, defIV, staIV = p.ivs['atk'], p.ivs['def'], p.ivs['hp']
        if percentile >= 95:
            works_well_with, works_well_against, works_poorly_against = combos_with_and_against(cup, str(p))
        else:
            works_well_with = None
            works_well_against = None
            works_poorly_against = None
        list_item = {
            'name': name,
            'relative_rank': rank,
            'color': color,
            'absolute_rank': percentile,
            'level': level,
            'atk': atkIV,
            'def': defIV,
            'sta': staIV,
            'movesets': moves_html,
            'works_well_with': works_well_with,
            'works_well_against': works_well_against,
            'works_poorly_against': works_poorly_against
        }
        list_items.append(list_item)
    with open(f"{path}/web/{cup}.data", 'w') as f:
        dump(list_items, f)


def combos_with_and_against(cup, pokemon):
    meta = ordered_top_pokemon(cup, 95)
    works_well_with = []
    works_well_against = []
    works_poorly_against = []
    matrix = {pokemon: {}}
    db = TinyDB(f"{path}/data/databases/{cup}.json")
    table = db.table('battle_results')
    query = Query()
    for mon in meta:
        mon_string = ", ".join([mon['name'], mon['fast'], mon['charge_1'], mon['charge_2']])
        if mon_string != pokemon:
            result = table.search(query.pokemon.all([pokemon, mon_string]))[0]
        else:
            result = table.search(query.pokemon == [pokemon, mon_string])[0]
        if result['pokemon'] == [pokemon, mon_string]:
            r = sum([x[0] for x in result['result']])
        elif result['pokemon'] == [mon_string, pokemon]:
            r = sum([x[1] for x in result['result']])
        matrix[pokemon][mon['name']] = r
        if mon_string != pokemon:
            works_well_against.append((r, mon['name']))
            works_poorly_against.append((r, mon['name']))
        matrix[mon['name']] = {}
        query_2 = Query()
        for mon2 in meta:
            mon_2_string = ", ".join([mon2['name'], mon2['fast'], mon2['charge_1'], mon2['charge_2']])
            result = table.search(query_2.pokemon.all([mon_string, mon_2_string]))[0]
            if result['pokemon'] == [mon_string, mon_2_string]:
                r = sum([x[0] for x in result['result']])
            elif result['pokemon'] == [mon_2_string, mon_string]:
                r = sum([x[1] for x in result['result']])
            matrix[mon['name']][mon2['name']] = r
    db.close()
    for mon in meta:
        points = 1
        for mon2 in meta:
            points *= max(matrix[pokemon][mon2['name']], matrix[mon['name']][mon2['name']])
        if mon['name'] not in pokemon:
            works_well_with.append((points, mon['name']))

    works_well_with.sort(reverse=True)
    works_well_against.sort(reverse=True)
    works_poorly_against.sort(reverse=False)
    works_well_with = [x[1] for x in works_well_with[:6]]
    works_well_against = [x[1] for x in works_well_against[:6]]
    works_poorly_against = [x[1] for x in works_poorly_against[:6]]
    return works_well_with, works_well_against, works_poorly_against


def fill_move_template(pokemon_name: str, move_info: tuple, cup: str):
    absolute_rank, fast_name, charge_1_name, charge_2_name = move_info
    fast_type = gm.get_move(fast_name)['type']
    charge_1_type = gm.get_move(charge_1_name)['type']
    charge_2_type = gm.get_move(charge_2_name)['type']
    card_address = f"{cup}+{pokemon_name}+{fast_name}+{charge_1_name}+{charge_2_name}"
    return {
        'absolute_rank': round(100 - absolute_rank, 1),
        'fast_type': fast_type,
        'fast_name': fast_name,
        'charge_1_type': charge_1_type,
        'charge_1_name': charge_1_name,
        'charge_2_type': charge_2_type,
        'charge_2_name': charge_2_name,
        'string': card_address
    }


def main():
    # jobs = []
    # cup = ['kingdom', 'boulder', 'tempest']
    cup = ['boulder', 'twilight', 'tempest', 'kingdom']
    # for i in range(3):
    #     jobs.append(Process(target=create_ranking_table, args=(cup[i],)))
    #     jobs[i].start()
    # for i in range(3):
    #     jobs[i].join()
    #     print(f"Finished {cup[i]} cup.")
    create_ranking_table('kingdom')


if __name__ == '__main__':
    main()
