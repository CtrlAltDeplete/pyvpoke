from src.gamemaster import path, GameMaster, type_to_color
from src.meta_calculator import top_pokemon_in_depth


def create_ranking_table(cup: str, cup_types: list, save_name: str):
    tr_template = '<tr style="background-color: #{}">\n<td>{}</td> <td>{}</td> <td>{}</td> <td>{}</td> <td>{}</td>\n</tr>'
    formatted_trs = []
    gm = GameMaster()
    i = 1
    for ranking in top_pokemon_in_depth(cup):
        types = gm.get_pokemon(ranking[1])['types']
        color = types[0] if types[0] in cup_types else types[1]
        color = type_to_color[color]
        formatted_trs.append(tr_template.format(color, i, ranking[1], ranking[2], ranking[3], ranking[4]))
        i += 1
    with open(save_name, 'w') as f:
        f.write('\n'.join(formatted_trs))


if __name__ == '__main__':
    create_ranking_table('kingdom', ['fire', 'ice', 'steel', 'dragon'], f'{path}/web/static/kingdom.html')
