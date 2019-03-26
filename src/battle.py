from src.pokemon import Pokemon


def battle(ally: Pokemon, enemy: Pokemon, shields: int):
    ally.starting_shields = shields
    enemy.starting_shields = shields

    ally.reset()
    enemy.reset()

    turns = 0

    # Main Battle Loop
    while ally.is_alive() and enemy.is_alive():
        ally.reduce_cooldown()
        enemy.reduce_cooldown()

        turns += 1
        if ally.can_act():
            if not ally.use_charge_move(enemy):
                ally.use_move(ally.fast_move, enemy)

        if enemy.can_act():
            if not enemy.use_charge_move(ally):
                enemy.use_move(enemy.fast_move, ally)

    # There are 2 points for using enemy shields and 3 for using enemy health.
    ally_rating = 2 if enemy.starting_shields == 0 else 2 * enemy.get_shields() / enemy.starting_shields
    enemy_rating = 2 if ally.starting_shields == 0 else 2 * ally.get_shields() / ally.starting_shields
    ally_rating += 5 * (enemy.starting_health - enemy.get_health()) / enemy.starting_health
    enemy_rating += 5 * (ally.starting_health - ally.get_health()) / ally.starting_health

    total_rating = ally_rating + enemy_rating

    return int(round(1000 * ally_rating / total_rating, 0)), int(round(1000 * enemy_rating / total_rating, 0))


def battle_all_shields(ally: Pokemon, enemy: Pokemon):
    results = [0, 0]
    for i in range(3):
        new_result = battle(ally, enemy, i)
        results[0] += new_result[0]
        results[1] += new_result[1]
    return int(round(results[0] / 3, 0)), int(round(results[1] / 3, 0))


if __name__ == '__main__':
    # all_pokemon = (
    #     Pokemon('Lapras', 'Water Gun', 'Surf', 'Dragon Pulse'),
    #     Pokemon('Lucario', 'Counter', 'Power-Up Punch', 'Shadow Ball'),
    #     Pokemon('Bastiodon', 'Smack Down', 'Stone Edge', 'Flamethrower'),
    #     Pokemon('Sealeo', 'Water Gun', 'Body Slam', 'Water Pulse'),
    #     Pokemon('Flygon', 'Mud Shot', 'Dragon Claw', 'Stone Edge'),
    #     Pokemon('Walrein', 'Waterfall', 'Water Pulse', 'Earthquake'),
    #     Pokemon('Steelix', 'Dragon Tail', 'Earthquake', 'Crunch'),
    #     Pokemon('Alolan Marowak', 'Hex', 'Shadow Ball', 'Bone Club'),
    #     Pokemon('Blaziken', 'Counter', 'Stone Edge', 'Brave Bird'),
    #     Pokemon('Melmetal', 'Thunder Shock', 'Rock Slide', 'Flash Cannon')
    # )
    # for ally in all_pokemon:
    #     results = []
    #     for enemy in all_pokemon:
    #         results.append(battle_all_shields(ally, enemy)[0])
    #     print('\t'.join(str(result) for result in results))
    lapras = Pokemon('Lapras', 'Water Gun', 'Hydro Pump', 'Surf')
    lucario = Pokemon('Lucario', 'Counter', 'Power-Up Punch', 'Close Combat')
    print(battle(lucario, lapras, 2))
