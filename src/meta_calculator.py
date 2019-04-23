from src.gamemaster import path, banned, GameMaster
import sqlite3


def result_iter(cur, arraysize=1000):
    while True:
        results = cur.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def calculate_meta(cup: str):
    # Create a matrix of all battle results
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute('SELECT * FROM battle_sims')

    print("Assembling matrix...")

    matrix = {}
    for row in result_iter(cur):
        row_id, ally, enemy = row[:3]
        scores = row[3:]
        if ally not in matrix:
            matrix[ally] = {}
        matrix[ally][enemy] = (scores[0] + scores[4] + scores[8] + sum(scores)) / 2
    conn.close()

    to_remove = []
    for pokemon in matrix:
        if any([ban in pokemon for ban in banned]):
            to_remove.append(pokemon)
    for pokemon in to_remove:
        matrix.pop(pokemon, None)
        for pokemon_2 in matrix:
            matrix[pokemon_2].pop(pokemon, None)

    rankings = {}
    current_rank = 1

    print("Calculating rankings...")

    max_rank = len(matrix)
    while current_rank <= max_rank:
        matrix, to_remove = weight_matrix_with_removals(matrix)
        for pokemon in to_remove:
            rankings[pokemon] = {'absolute_rank': current_rank}
            matrix.pop(pokemon, None)
            for pokemon_2 in matrix:
                matrix[pokemon_2].pop(pokemon, None)
            current_rank += 1
        print(current_rank)

    results = {}
    all_pokemon = {}

    for pokemon in rankings:
        results[pokemon] = {}
        if len(pokemon.split(', ')) == 4:
            name, fast, charge_1, charge_2 = pokemon.split(', ')
            results[pokemon]['name'] = name
            results[pokemon]['fast'] = fast
            results[pokemon]['charge_1'] = charge_1
            results[pokemon]['charge_2'] = charge_2
        else:
            name, fast, charge_1 = pokemon.split(', ')
            results[pokemon]['name'] = name
            results[pokemon]['fast'] = fast
            results[pokemon]['charge_1'] = charge_1
            results[pokemon]['charge_2'] = None
        results[pokemon]['absolute_rank'] = rankings[pokemon]['absolute_rank']
        if name in all_pokemon:
            all_pokemon[name] = max(all_pokemon[name], rankings[pokemon]['absolute_rank'])
        else:
            all_pokemon[name] = rankings[pokemon]['absolute_rank']

    all_pokemon = [(all_pokemon[key], key) for key in all_pokemon]
    all_pokemon.sort(reverse=True)
    results = [(results[k]['name'], results[k]['fast'], results[k]['charge_1'], results[k]['charge_2'], results[k]['absolute_rank']) for k in rankings]
    min_score = min([x[4] for x in results])
    max_score = max([x[4] for x in results])

    print("Writing to database...")

    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    columns = (
        ' '.join(('id', 'INTEGER PRIMARY KEY AUTOINCREMENT')),
        ' '.join(('pokemon', 'TEXT')),
        ' '.join(('fast', 'TEXT')),
        ' '.join(('charge_1', 'TEXT')),
        ' '.join(('charge_2', 'TEXT')),
        ' '.join(('absolute_rank', 'REAL')),
        ' '.join(('relative_rank', 'REAL'))
    )

    command = f"CREATE TABLE rankings ({', '.join(columns)})"
    cur.execute(command)

    command = "INSERT INTO rankings(pokemon, fast, charge_1, charge_2, absolute_rank) VALUES (?,?,?,?,?)"
    cur.executemany(command, results)

    command = f"UPDATE rankings SET absolute_rank = round((absolute_rank - {min_score}) * 100 / ({max_score} - {min_score}), 1)"
    cur.execute(command)

    for i in range(1, len(all_pokemon) + 1):
        command = f"UPDATE rankings SET relative_rank = {i} WHERE id in (SELECT id FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC LIMIT 1)"
        cur.execute(command, (all_pokemon[i - 1][1],))

    conn.commit()
    conn.close()
    print("Done.\n")


def weight_matrix_with_removals(matrix: dict):
    victories = {}
    for ally in matrix:
        victories[ally] = []
        for enemy in matrix:
            if matrix[ally][enemy] > matrix[enemy][ally]:
                victories[ally].append(enemy)

    to_ignore = []
    victories = [(pokemon, set(v)) for pokemon, v in victories.items()]
    for pokemon, v in victories:
        if any(v.issubset(w[1]) and v != w[1] for w in victories):
            to_ignore.append(pokemon)

    if len(to_ignore) + 1 >= len(matrix.keys()):
        return matrix, list(matrix.keys())

    for ally in matrix:
        column = 0
        for enemy in matrix:
            if enemy not in to_ignore:
                column += matrix[enemy][ally]
        matrix[ally]['column'] = column

    total = 0
    for ally in matrix:
        row = 0
        for enemy in matrix:
            if matrix[ally]['column'] == 0:
                print(matrix)
                exit(69)
            row += matrix[ally][enemy] / matrix[ally]['column']
        matrix[ally]['row'] = row
        total += row

    scores = []
    for ally in matrix:
        scores.append(matrix[ally]['row'])

    to_remove = []
    scores.sort()

    for pokemon in matrix:
        if matrix[pokemon]['row'] in scores[:min(3, len(scores))]:
            to_remove.append(pokemon)

    return matrix, to_remove


def ordered_top_pokemon(cup: str, percentile_limit: int = 100):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT pokemon FROM rankings WHERE relative_rank > 0 and absolute_rank >= 100 - {percentile_limit} ORDER BY relative_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return [x[0] for x in rows]


def all_pokemon_movesets(cup: str, percentile_limit: int = 100):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT pokemon FROM rankings WHERE absolute_rank >= 100 - {percentile_limit} ORDER BY absolute_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return [x[0] for x in rows]


def ordered_movesets_for_pokemon(cup: str, pokemon: str):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT fast, charge_1, charge_2, absolute_rank FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC"
    cur.execute(command, (pokemon,))
    rows = cur.fetchall()
    conn.close()
    return rows


def calculate_mean_and_sd(cup: str):
    ordered_pokemon = ordered_top_pokemon(cup)
    scores = []
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    for pokemon in ordered_pokemon:
        command = f"SELECT absolute_rank FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC"
        cur.execute(command, (pokemon,))
        row = cur.fetchone()
        scores.append(row[0])
    conn.close()
    mean = sum(scores) / len(scores)
    sd = (sum([(x - mean) ** 2 for x in scores]) / len(scores)) ** 0.5
    return mean, sd / 2


def scale_ranking(rank, min_rank, max_rank):
    return round((rank - min_rank) * 100 / (max_rank - min_rank), 1)


if __name__ == '__main__':
    calculate_meta('nightmare')
