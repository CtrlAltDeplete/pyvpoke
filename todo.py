from src.gamemaster import path
import os
from tinydb import TinyDB, Query


cup = ('boulder', 'kingdom', 'tempest', 'twilight')
for c in cup:
    cup_directory = f"{path}/data/databases/{c}"
    all_db_files = os.listdir(cup_directory)
    for db_name in all_db_files:
        query = Query()
        db = TinyDB(f"{path}/data/databases/{c}/{db_name}")
        table = db.table('battle_results')
        docs = table.all()
        to_remove = {}
        for doc in docs:
            if tuple(doc['pokemon']) not in to_remove and len(table.search(query.pokemon == doc['pokemon'])) > 1:
                to_remove[tuple(doc['pokemon'])] = doc.doc_id
        table.remove(doc_ids=[x[1] for x in to_remove.items()])
        db.close()
    print(f"{c} finished.")
