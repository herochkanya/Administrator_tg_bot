import sqlite3
import json

from ..config import database_path

class XO:

    def __init__(
            self,
            game_id: int,
            x_symbol: str = '❌',
            o_symbol: str = '⭕'
        ):
        self.game_id = game_id
        self.symbols = {'x': x_symbol, 'o': o_symbol}
        self._new_game()
        self.x_user_id = self._get_x_user_id()
        self.o_user_id = self._get_o_user_id()
        self.users = {'x': self.x_user_id, 'o': self.o_user_id}

    def x_user_id_is(self, id):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xo_games SET x_user_id=? WHERE game_id=?", (id, self.game_id))
            conn.commit()
        self.x_user_id = id

    def o_user_id_is(self, id):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xo_games SET o_user_id=? WHERE game_id=?", (id, self.game_id))
            conn.commit()
        self.o_user_id = id

    def _get_x_user_id(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT x_user_id FROM xo_games WHERE game_id=?", (self.game_id,))
            return cursor.fetchone()[0]

    def _get_o_user_id(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT o_user_id FROM xo_games WHERE game_id=?", (self.game_id,))
            return cursor.fetchone()[0]

    def _new_game(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT game_id FROM xo_games WHERE game_id=?", (self.game_id,))
            existing_id = cursor.fetchone()
        
            if existing_id is None:
                cursor.execute("INSERT INTO xo_games (game_id) VALUES (?)", (self.game_id,))
                conn.commit()
    
    def field(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT field FROM xo_games WHERE game_id=?", (self.game_id,))
            field = cursor.fetchone()[0]
        return json.loads(field)
    
    def _update_field(self, field: dict):
        field = json.dumps(field)
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xo_games SET field=? WHERE game_id=?", (field, self.game_id))
            conn.commit()

    def who_walk(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT who_walk FROM xo_games WHERE game_id=?", (self.game_id,))
            walk_is = cursor.fetchone()[0]
        return walk_is
    
    def _who_walk_update(self):
        lst = ['x', 'o']
        lst.remove(self.who_walk())
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xo_games SET who_walk=? WHERE game_id=?", (lst[0], self.game_id))
            conn.commit()

    def does_win(self):
        field = self.field()
        results = [
            field['1'] + field['2'] + field['3'],
            field['4'] + field['5'] + field['6'],
            field['7'] + field['8'] + field['9'],
            field['1'] + field['4'] + field['7'],
            field['2'] + field['5'] + field['8'],
            field['3'] + field['6'] + field['9'],
            field['1'] + field['5'] + field['9'],
            field['3'] + field['5'] + field['7'],
        ]
        if self.symbols['x']*3 in results or self.symbols['o']*3 in results:
            return True
        
    def draw(self):
        field = self.field()
        if list(field.values()).count(self.symbols['x']) + list(field.values()).count(self.symbols['o']) == 9:
            return True
        
        return False
    
    def make_move(self, number_of_field):
        field = self.field()
        walk_is = self.who_walk()
        
        if field[number_of_field] != 'ㅤ':
            return False
        
        field[number_of_field] = self.symbols[walk_is]
        self._update_field(field)
        self._who_walk_update()
        return True
    
    def del_game(self):
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM xo_games WHERE game_id=?", (self.game_id,))
            conn.commit()



        