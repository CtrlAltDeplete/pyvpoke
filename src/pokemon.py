import math
from src.gamemaster import GameMaster


gm = GameMaster()


class Pokemon:
    class Move:
        def __init__(self, name, user_types):
            self.name = name
            move_data = gm.get_move(name)
            self.power = move_data['power']
            self.energy = move_data['energy']
            self.type = move_data['type']
            if self.type in user_types:
                self.power *= 1.2
            if 'turns' in move_data:
                self.cooldown = move_data['turns']
            else:
                self.cooldown = 0
                self.energy *= -1
            self.applied_buff = (0, 0)
            if self.name == 'Power-Up Punch':
                self.applied_buff = (0.25, 0)

        def apply_buff(self, user):
            if user.buff_count < 4 and self.applied_buff != (0, 0):
                user.buffs[0] += self.applied_buff[0]
                user.buffs[1] += self.applied_buff[1]
                user.buff_count += 1

        def get_damage(self, user, enemy):
            return math.floor(self.power * enemy.get_effectiveness(self.type) * 0.5 * 1.3 * user.get_attack() / enemy.get_defense()) + 1

        def is_fast(self):
            return self.energy > 0

        def is_charge(self):
            return self.energy < 0

        def is_available(self, energy):
            if self.is_fast():
                return True
            else:
                return energy >= -self.energy

        def __str__(self):
            return self.name

    def __init__(self, name, fast_move_name, charge_move_1_name, charge_move_2_name=None):
        self.name = name
        pokemon_data = gm.get_pokemon(name)
        self.types = pokemon_data['types']
        self.base_stats = pokemon_data['base stats']
        self.ivs = {'atk': 0, 'def': 0, 'hp': 0}
        self.stats = {'atk': 0, 'def': 0, 'hp': 0}
        self.cp = 0
        self.hp = 0
        self.starting_health = 0
        self.starting_energy = 0
        self.starting_shields = 0
        self.level = 40
        self.fast_move = self.Move(fast_move_name, self.types)
        self.charge_move_pool = [self.Move(charge_move_1_name, self.types)]
        if charge_move_2_name:
            self.charge_move_pool.append(self.Move(charge_move_2_name, self.types))
        self.best_charge_move = self.charge_move_pool[0]
        self.single_weak = pokemon_data['weaknesses']['1.60']
        self.double_weak = pokemon_data['weaknesses']['2.56']
        self.single_resist = pokemon_data['resistances']['0.625']
        self.double_resist = pokemon_data['resistances']['0.391']
        self.energy = 0
        self.cooldown = 0
        self.shields = 0
        self.buff_count = 0
        self.buffs = [1, 1]
        self.initialize()

    def calculate_CP(self, cpm, atkIV, defIV, hpIV):
        return math.floor(((self.base_stats['atk'] + atkIV) * math.pow(self.base_stats['def'] + defIV, 0.5) * math.pow(self.base_stats['hp'] + hpIV, 0.5) * math.pow(cpm, 2)) / 10)

    def initialize(self):
        options = []
        for level in range(80, 1, -1):
            cpm = gm.get_cpm(level / 2)
            min_level_cp = self.calculate_CP(cpm, 0, 0, 0)
            max_level_cp = self.calculate_CP(cpm, 15, 15, 15)
            if max_level_cp < 1500 or 1500 < min_level_cp:
                continue
            for hpIV in range(15, -1, -1):
                for defIV in range(hpIV, -1, -1):
                    for atkIV in range(15, -1, -1):
                        cp = self.calculate_CP(cpm, atkIV, defIV, hpIV)
                        if cp <= 1500:
                            atk_stat = cpm * (self.base_stats['atk'] + atkIV)
                            def_stat = cpm * (self.base_stats['def'] + defIV)
                            hp_stat = math.floor(cpm * (self.base_stats['hp'] + hpIV))
                            overall = hp_stat * atk_stat * def_stat / 1000
                            options.append((overall, level / 2, atkIV, defIV, hpIV))
        if options:
            option = max(options)
            self.level = option[1]
            self.ivs['atk'] = option[2]
            self.ivs['def'] = option[3]
            self.ivs['hp'] = option[4]
        else:
            self.level = 40
            self.ivs['atk'] = 15
            self.ivs['def'] = 15
            self.ivs['hp'] = 15
        cpm = gm.get_cpm(self.level)
        self.stats['atk'] = cpm * (self.base_stats['atk'] + self.ivs['atk'])
        self.stats['def'] = cpm * (self.base_stats['def'] + self.ivs['def'])
        self.stats['hp'] = math.floor(cpm * (self.base_stats['hp'] + self.ivs['hp']))
        self.hp = self.stats['hp']
        self.starting_health = self.hp
        self.cp = self.calculate_CP(cpm, self.ivs['atk'], self.ivs['def'], self.ivs['hp'])

    def reset(self):
        # Sets the health, energy, and shields to their starting values.
        self.hp = self.starting_health
        self.energy = self.starting_energy
        self.shields = self.starting_shields
        self.cooldown = 0
        self.buff_count = 0
        self.buffs = [1, 1]

    def get_effectiveness(self, move_type):
        if move_type in self.single_weak:
            return 1.6
        elif move_type in self.double_weak:
            return 2.56
        elif move_type in self.single_resist:
            return 0.625
        elif move_type in self.double_resist:
            return 0.391
        return 1.0

    def is_alive(self):
        # Return whether or not the pokemon's current HP is above 0.
        return self.hp > 0

    def get_health(self):
        return self.hp

    def reduce_cooldown(self):
        # Subtract one from cooldown.
        self.cooldown -= 1 if self.cooldown > 0 else 0

    def get_shields(self):
        # Returns the current shield count.
        return self.shields

    def can_act(self):
        # Return true if the cooldown is 0.
        return self.cooldown == 0

    def get_cooldown(self):
        return self.cooldown

    def get_fast_cooldown(self):
        return self.fast_move.cooldown

    def use_charge_move(self, enemy):
        self.best_charge_move = self.charge_move_pool[0]
        if len(self.charge_move_pool) > 1 and self.charge_move_pool[1].get_damage(self, enemy) > self.charge_move_pool[0].get_damage(self, enemy):
            self.best_charge_move = self.charge_move_pool[1]

        use_charge_move = False
        charge_move_used = False
        if self.best_charge_move.is_available(self.energy):
            use_charge_move = True
            if (enemy.cooldown == 0 or enemy.cooldown == enemy.fast_move.cooldown) and enemy.fast_move.cooldown > self.fast_move.cooldown:
                use_charge_move = False
            elif enemy.cooldown > self.fast_move.cooldown:
                use_charge_move = False

            if enemy.get_health() <= self.fast_move.get_damage(self, enemy):
                use_charge_move = False

            if enemy.get_shields() > 0:
                if enemy.get_health() <= self.fast_move.get_damage(self, enemy) * enemy.fast_move.cooldown / self.fast_move.cooldown:
                    use_charge_move = False
                for charge_move in self.charge_move_pool:
                    if charge_move.is_available(self.energy) and charge_move.energy < self.best_charge_move.energy:
                        use_charge_move = False

            if use_charge_move:
                self.use_move(self.best_charge_move, enemy)
                charge_move_used = True

        for move in self.charge_move_pool:
            if move.is_available(self.energy) and not charge_move_used:
                if move.get_damage(self, enemy) >= enemy.get_health() and enemy.get_health() >= self.fast_move.get_damage(self, enemy) and enemy.get_shields() == 0 and not charge_move_used:
                    self.use_move(move, enemy)
                    charge_move_used = True
                if enemy.get_shields() > 0 and not charge_move_used:
                    if enemy.get_health() > self.fast_move.get_damage(self, enemy) and enemy.get_health() > self.fast_move.get_damage(self, enemy) * enemy.fast_move.cooldown / self.fast_move.cooldown:
                        self.use_move(move, enemy)
                        charge_move_used = True

                near_death = False
                if enemy.cooldown == 0:
                    if self.get_health() <= enemy.fast_move.get_damage(enemy, self):
                        near_death = True
                    if self.shields == 0:
                        for enemy_move in enemy.charge_move_pool:
                            if enemy_move.is_available(enemy.energy) and self.get_health() <= enemy_move.get_damage(enemy, self):
                                near_death = True
                if self.hp <= 0:
                    near_death = True

                if 0 < enemy.cooldown < self.fast_move.cooldown or (enemy.cooldown == 0 and enemy.fast_move.cooldown < self.fast_move.cooldown):
                    available_time = self.fast_move.cooldown - enemy.cooldown
                    future_actions = math.ceil(available_time / enemy.fast_move.cooldown)
                    future_fast_damage = future_actions * enemy.fast_move.get_damage(enemy, self)

                    if self.get_health() <= future_fast_damage:
                        near_death = True

                    if self.get_shields() == 0:
                        future_effective_energy = enemy.energy + (enemy.fast_move.energy * (future_actions - 1))
                        future_effective_hp = self.get_health() - ((future_actions - 1) * enemy.fast_move.get_damage(enemy, self))
                        for enemy_move in enemy.charge_move_pool:
                            if enemy_move.is_available(future_effective_energy) and future_effective_hp <= enemy_move.get_damage(enemy, self):
                                near_death = True

                if enemy.get_shields() > 0 and enemy.get_health() <= self.fast_move.get_damage(self, enemy):
                    near_death = False

                if self.energy >= -self.best_charge_move.energy and move.get_damage(self, enemy) < self.best_charge_move.get_damage(self, enemy):
                    near_death = False

                if near_death and not charge_move_used:
                    self.use_move(move, enemy)
                    charge_move_used = True
        return charge_move_used

    def use_move(self, move, enemy):
        # Use the given move on the given enemy
        damage = move.get_damage(self, enemy)
        self.energy += move.energy
        if self.energy < 0:
            raise Exception("Used a charge move with insufficient energy.")
        if move.is_charge():
            if enemy.get_shields() > 0:
                damage = 1
                enemy.shields -= 1
        else:
            self.cooldown += move.cooldown
            self.energy = min(100, self.energy)

        enemy.hp = max(0, enemy.hp - damage)
        move.apply_buff(self)

    def get_attack(self):
        return self.stats['atk'] * self.buffs[0]

    def get_defense(self):
        return self.stats['def'] * self.buffs[1]

    def __str__(self):
        return f"{self.name}, {self.fast_move}, {', '.join((str(move) for move in self.charge_move_pool))}"


if __name__ == '__main__':
    bulbasaur = Pokemon('Bulbasaur', 'Vine Whip', 'Power Whip', 'Solar Beam')
