from src.web_preparer import create_card_table, create_ranking_table


cups = [
    # 'test',
    ('boulder', ('rock', 'fighting', 'ground', 'steel')),
    ('twilight', ('poison', 'fairy', 'dark', 'ghost')),
    ('tempest', ('flying', 'ice', 'electric', 'ground')),
    ('kingdom', ('dragon', 'fire', 'ice', 'steel')),
    ('nightmare', ('fighting', 'psychic', 'dark'))
]
for cup, type_restrictions in cups:
    create_ranking_table(cup)
    create_card_table(cup, type_restrictions)
