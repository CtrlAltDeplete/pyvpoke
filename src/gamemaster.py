from json import dump, load


# path = 'C:/Users/gavyn/Documents/Python/pyvpoke'
path = 'C:/Users/gavyn/PycharmProjects/pyvpoke'
NORMAL = 'normal'
FIGHTING = 'fighting'
FLYING = 'flying'
POISON = 'poison'
GROUND = 'ground'
ROCK = 'rock'
BUG = 'bug'
GHOST = 'ghost'
STEEL = 'steel'
FIRE = 'fire'
WATER = 'water'
GRASS = 'grass'
ELECTRIC = 'electric'
PSYCHIC = 'psychic'
ICE = 'ice'
DRAGON = 'dragon'
DARK = 'dark'
FAIRY = 'fairy'
banned = ('Mewtwo', 'Giratina (Altered Forme)', 'Groudon', 'Kygore', 'Rayquaza', 'Garchomp', 'Latios', 'Latias',
          'Palkia', 'Dialga', 'Heatran', 'Giratina (Origin Forme)', 'Gastrodon', 'Shaymin (Sky Forme)',
          'Shaymin (Lan Forme)', 'Rotom', 'Gallade', 'Gabite')
ignored = ('Mew', 'Jirachi', 'Magnezone', 'Probopass')
type_to_color = {
    NORMAL: "A8A77A",
    FIGHTING: "C22E28",
    FLYING: "A98FF3",
    POISON: "A33EA1",
    GROUND: "E2BF65",
    ROCK: "B6A136",
    BUG: "A6B91A",
    GHOST: "735797",
    STEEL: "B7B7CE",
    FIRE: "EE8130",
    WATER: "6390F0",
    GRASS: "7AC74C",
    ELECTRIC: "F7D02C",
    PSYCHIC: "F95587",
    ICE: "96D9D6",
    DRAGON: "6F35FC",
    DARK: "705746",
    FAIRY: "D685AD"
}


class GameMaster:
    def __init__(self):
        self.cpms = {}
        with open(f'{path}/data/cp_mult.csv') as f:
            data = f.read().split()[1:]
        for line in data:
            datum = line.split(',')
            level = float(datum[0])
            mult = float(datum[1])
            self.cpms[level] = mult

        with open(f'{path}/data/pokemon.json') as json_file:
            self.pokemon_data = load(json_file)

        with open(f'{path}/data/fast_moves.json') as json_file:
            self.fast_moves_data = load(json_file)

        with open(f'{path}/data/charge_moves.json') as json_file:
            self.charge_moves_data = load(json_file)

        self.types = [NORMAL, FIRE, FIGHTING, WATER, FLYING, GRASS, POISON, ELECTRIC, GROUND, PSYCHIC, ROCK, ICE, BUG,
                      DRAGON, GHOST, DARK, STEEL, FAIRY]

        self.pokemon = [pokemon for pokemon in self.pokemon_data]
        self.pokemon.sort()

    def get_move(self, name):
        for move in self.fast_moves_data:
            if move == name:
                return self.fast_moves_data[move]
        for move in self.charge_moves_data:
            if move == name:
                return self.charge_moves_data[move]

    def get_pokemon(self, name):
        for pokemon in self.pokemon_data:
            if pokemon == name:
                return self.pokemon_data[pokemon]

    def get_cpm(self, level):
        return self.cpms[level]

    def iter_pokemon(self, type_restriction=None):
        if type_restriction is None:
            type_restriction = self.types
        for pokemon in self.pokemon:
            pokemon_data = self.get_pokemon(pokemon)
            if any([t in type_restriction for t in pokemon_data['types']]):
                yield pokemon

    def iter_pokemon_move_set_combos(self, type_restriction=None):
        for pokemon in self.iter_pokemon(type_restriction):
            pokemon_data = self.get_pokemon(pokemon)
            for fast_move in pokemon_data['fast']:
                for i in range(len(pokemon_data['charge'])):
                    charge_1 = pokemon_data['charge'][i]
                    yield pokemon, fast_move, charge_1, None
                    for j in range(i + 1, len(pokemon_data['charge'])):
                        charge_2 = pokemon_data['charge'][j]
                        yield pokemon, fast_move, charge_1, charge_2
