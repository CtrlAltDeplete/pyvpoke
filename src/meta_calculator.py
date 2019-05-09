from src.gamemaster import path, banned
from multiprocessing import Process, Manager
import sqlite3
import numpy as np


def result_iter(cur, arraysize=1000):
    while True:
        results = cur.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def calculate_meta(cup: str, page_rank_matrix=None):
    # Create a matrix of all battle results
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute('SELECT * FROM battle_sims')

    print("Assembling matrix...")

    score_matrix = {}
    for row in result_iter(cur):
        row_id, ally, enemy = row[:3]
        scores = row[3:]
        if ally not in score_matrix:
            score_matrix[ally] = {}
        score_matrix[ally][enemy] = sum(scores) / len(scores)
    conn.close()

    print("Calculating Page Ranks...")

    keys = list(x for x in score_matrix.keys() if not any([y in x for y in banned]))
    if page_rank_matrix is None:
        manager = Manager()
        num_processes = 8
        page_rank_matrix = manager.dict()
        for i in range(0, len(keys), num_processes):
            jobs = []
            for j in range(min(num_processes, len(keys) - i)):
                moveset = keys[i + j]
                page_rank_matrix[moveset] = []
                jobs.append(Process(target=add_moveset_to_meta_matrix, args=(score_matrix, page_rank_matrix, moveset, keys)))
                jobs[j].start()
            for p in range(min(num_processes, len(keys) - i)):
                jobs[p].join()
            print(f"{round(100 * (i + num_processes) / len(keys), 1)}%")
        page_rank_matrix = [page_rank_matrix[x] for x in keys]
        for col in range(len(keys)):
            column_sum = 0
            for row in range(len(keys)):
                column_sum += page_rank_matrix[row][col]
            for row in range(len(keys)):
                try:
                    page_rank_matrix[row][col] = 0 if column_sum == 0 else page_rank_matrix[row][col] / float(column_sum)
                except ZeroDivisionError:
                    print("Zero Division Error", keys[col])
                    exit(69)

        page_rank_matrix = np.array(page_rank_matrix)
        with open(f"{path}/data/{cup}_matrix.json", 'w') as f:
            page_rank_matrix.tofile(f)
    else:
        page_rank_matrix.shape = (len(keys), len(keys))

    print("Scoring Pokemon...")

    control_vector = [1.0 / len(keys) for i in range(len(keys))]
    old_order = [(control_vector[i], keys[i]) for i in range(len(keys))]
    old_order.sort(reverse=False)
    old_order = [x[1] for x in old_order]

    i = 0
    constant_rank_count = 0
    while True:
        i += 1
        control_vector = page_rank_matrix.dot(control_vector)
        new_order = [(control_vector[j], keys[j]) for j in range(len(keys))]
        new_order.sort(reverse=True)
        new_order = [x[1] for x in new_order]
        differences = 0
        for j in range(len(new_order)):
            if old_order[j] != new_order[j]:
                differences += 1
        old_order = new_order
        if differences == 0:
            constant_rank_count += 1
            if constant_rank_count == 3:
                break
        else:
            constant_rank_count = 0

    rankings = [(control_vector[i], keys[i]) for i in range(len(keys))]
    rankings.sort(reverse=False)
    rankings = [(100 * float(i) / float(len(rankings)), key[1]) for i, key in enumerate(rankings)]

    results = {}
    all_pokemon = {}

    i = 0
    for score, pokemon in rankings:
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
        results[pokemon]['absolute_rank'] = score
        if name in all_pokemon:
            all_pokemon[name] = max(all_pokemon[name], results[pokemon]['absolute_rank'])
        else:
            all_pokemon[name] = results[pokemon]['absolute_rank']
        i += 1

    all_pokemon = [(all_pokemon[key], key) for key in all_pokemon]
    all_pokemon.sort(reverse=True)
    results = [(results[k]['name'], results[k]['fast'], results[k]['charge_1'], results[k]['charge_2'], results[k]['absolute_rank']) for k in results]

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

    for i in range(1, len(all_pokemon) + 1):
        command = f"UPDATE rankings SET relative_rank = {i} WHERE id in (SELECT id FROM rankings WHERE pokemon = ? ORDER BY absolute_rank DESC LIMIT 1)"
        cur.execute(command, (all_pokemon[i - 1][1],))

    conn.commit()
    conn.close()
    print("Done.\n")


def add_moveset_to_meta_matrix(score_matrix, pr_matrix, moveset, keys):
    score_list = []
    for ally in keys:
        score = 0
        for enemy in keys:
            score += max(score_matrix[moveset][enemy], score_matrix[ally][enemy])
        score_list.append(score)
    pr_matrix[moveset] = score_list


def bellcurve_of_data(rankings):
    s = np.random.normal(50.0, 50.0 / 3.2, len(rankings))
    s.sort()
    return [(round(max(0.0, min(s[i], 100.0)), 1), rank[1]) for i, rank in enumerate(rankings)]


def ordered_top_pokemon(cup: str, percentile_limit: int = 100):
    conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
    cur = conn.cursor()
    command = f"SELECT pokemon, absolute_rank FROM rankings WHERE relative_rank > 0 and absolute_rank >= 100 - {percentile_limit} ORDER BY relative_rank"
    cur.execute(command)
    rows = cur.fetchall()
    conn.close()
    return rows


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


def multiply_matrices(a, v):
    new_matrix = {}
    for key in v:
        value = 0
        for col in v:
            value += a[key][col] * v[col]
        new_matrix[key] = value
    return new_matrix


def scale_ranking(rank, min_rank, max_rank):
    return round(100 - (rank - min_rank) * 100 / (max_rank - min_rank), 2)


if __name__ == '__main__':
    for cup in [
        'nightmare',
        'kingdom',
        'tempest',
        'twilight',
        'boulder',
        'regionals'
    ]:
        try:
            conn = sqlite3.connect(f"{path}/data/databases/{cup}.db")
            cur = conn.cursor()
            cur.execute("DROP TABLE rankings")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass

        # with open(f"{path}/data/{cup}_matrix.json", 'r') as f:
        #     matrix = np.core.multiarray.fromfile(f)
        # calculate_meta(cup, matrix)
        calculate_meta(cup)

        # for mon, score in ordered_top_pokemon(cup):
        #     print(mon)
        #     for moveset in ordered_movesets_for_pokemon(cup, mon):
        #         print('\t' + str(moveset))
        #     print()

