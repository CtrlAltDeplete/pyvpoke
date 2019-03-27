from src.gamemaster import path, GameMaster
from src.meta_calculator import top_pokemon_in_depth


def create_ranking_table(cup: str, cup_types: list, save_name: str):
    tr_template = '<li style="border-bottom: 0px; padding: 2px 16px;"><div class="w3-row-padding w3-round-xlarge pokemon-ranking {}"><div class="w3-col s1">#{}</div><div class="w3-col s10">{}</div><div class="w3-col s1">{}</div></div></li>'
    formatted_trs = []
    gm = GameMaster()
    i = 1
    cup_pokemon = top_pokemon_in_depth(cup)
    max_rank = max([x[0] for x in cup_pokemon])
    for ranking in top_pokemon_in_depth(cup):
        types = gm.get_pokemon(ranking[1])['types']
        color = types[0] if types[0] in cup_types else types[1]
        formatted_trs.append(tr_template.format(color, i, ranking[1], round(100 - 100 * (ranking[0] - 1) / max_rank, 1)))
        i += 1
    with open(save_name, 'w') as f:
        f.write('\n'.join(formatted_trs))


if __name__ == '__main__':
    create_ranking_table('tempest', ['flying', 'ice', 'electric', 'ground'], f'{path}/tempest.html')
