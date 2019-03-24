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
    charizard = Pokemon("Charizard", "Fire Spin", "Blast Burn", "Dragon Claw")
    lapras = Pokemon("Lapras", "Water Gun", "Hydro Pump", "Surf")
    print(battle_all_shields(charizard, lapras))
