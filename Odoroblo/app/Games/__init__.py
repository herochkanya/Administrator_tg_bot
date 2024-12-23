import sqlite3
import json

from .xo.xo import XO
from .config import database_path

version = 1.0

xo_field = {
    '1': 'ㅤ', '2': 'ㅤ', '3': 'ㅤ',
    '4': 'ㅤ', '5': 'ㅤ', '6': 'ㅤ',
    '7': 'ㅤ', '8': 'ㅤ', '9': 'ㅤ',
}

with sqlite3.connect(database_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        f'''
        CREATE TABLE IF NOT EXISTS xo_games (
            game_id STRING PRIMARY KEY,
            x_user_id STRING DEFAULT "None",
            o_user_id STRING DEFAULT "None",
            field STRING DEFAULT '{json.dumps(xo_field)}',
            who_walk DEFAULT "x",
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()