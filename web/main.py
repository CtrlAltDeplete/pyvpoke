import sys
sys.path.extend(['C:\\Users\\gavyn\\Documents\\Python\\pyvpoke', 'C:/Users/gavyn/Documents/Python/pyvpoke'])

from flask import Flask, render_template
from src.gamemaster import path


app = Flask(__name__)


@app.route('/<cup>')
def hello_world(cup):
    with open(f"{path}/web/static/{cup}.html") as f:
        table = f.read()
    return render_template('ranking_template.html', table=table)
