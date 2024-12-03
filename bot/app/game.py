from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from config import X, O

# Клас для станів гри
class TicTacToeGame(StatesGroup):
    waiting_for_choice = State()  # Очікування вибору
    playing = State()  # Гра в процесі

# Клас гри (додайте ваш функціонал TicTacToe сюди)
class TicTacToe:
    def __init__(self):
        self.board = [" "] * 9
        self.current_player = None

    def create_board_buttons(self):
        markup = InlineKeyboardMarkup(row_width=3)
        for i, cell in enumerate(self.board):
            markup.insert(InlineKeyboardButton(text=cell or str(i + 1), callback_data=f"cell_{i}"))
        return markup

    def make_move(self, cell_index):
        if self.board[cell_index] == " ":
            self.board[cell_index] = self.current_player
            self.current_player = X if self.current_player == O else O
            return True
        return False

    def is_winner(self):
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Горизонталі
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Вертикалі
            [0, 4, 8], [2, 4, 6]  # Діагоналі
        ]
        for line in winning_combinations:
            if self.board[line[0]] == self.board[line[1]] == self.board[line[2]] != " ":
                return self.board[line[0]]
        return None

    def is_board_full(self):
        return all(cell != " " for cell in self.board)
