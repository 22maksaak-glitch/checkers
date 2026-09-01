# checkers.py
# Версия на Python с dataclasses, type hints, цветным выводом, сохранением/загрузкой

import sys
import json
import random
import copy
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set, Dict
from enum import Enum

# ANSI цвета
COLORS = {
    'reset': '\033[0m',
    'black': '\033[30m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',
    'bg_black': '\033[40m',
    'bg_white': '\033[47m',
    'bg_red': '\033[41m',
    'bg_green': '\033[42m',
    'bg_yellow': '\033[43m',
    'bg_blue': '\033[44m',
    'bg_magenta': '\033[45m',
    'bg_cyan': '\033[46m',
}

class Color:
    @staticmethod
    def colorize(text: str, fg: str = 'reset', bg: str = None) -> str:
        bg_code = COLORS.get(f'bg_{bg}', '') if bg else ''
        return f"{COLORS.get(fg, '')}{bg_code}{text}{COLORS['reset']}"

class ColorMode:
    ENABLED = True

class PieceType(Enum):
    MAN = 1
    KING = 2

class ColorType(Enum):
    WHITE = 1
    BLACK = 2

    def opponent(self):
        return ColorType.BLACK if self == ColorType.WHITE else ColorType.WHITE

@dataclass
class Piece:
    color: ColorType
    type: PieceType

@dataclass
class Move:
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    captures: List[Tuple[int, int]]  # позиции побитых шашек (между from и to)
    # для многократного взятия captures содержит все побитые позиции в порядке
    # при этом from и to - начальная и конечная позиции всей серии

class Board:
    SIZE = 10
    def __init__(self):
        self.grid: List[List[Optional[Piece]]] = [[None]*self.SIZE for _ in range(self.SIZE)]
        self._init_board()

    def _init_board(self):
        # Белые снизу (строки 0-3), чёрные сверху (строки 6-9)
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if (r + c) % 2 == 1:  # только тёмные клетки
                    if r < 4:
                        self.grid[r][c] = Piece(ColorType.WHITE, PieceType.MAN)
                    elif r > 5:
                        self.grid[r][c] = Piece(ColorType.BLACK, PieceType.MAN)

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        if self._in_bounds(row, col):
            return self.grid[row][col]
        return None

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.SIZE and 0 <= col < self.SIZE

    def is_occupied(self, row: int, col: int) -> bool:
        return self.get_piece(row, col) is not None

    def place_piece(self, row: int, col: int, piece: Piece):
        self.grid[row][col] = piece

    def remove_piece(self, row: int, col: int):
        self.grid[row][col] = None

    def clone(self) -> 'Board':
        new_board = Board()
        # Пересоздаём сетку
        new_board.grid = [[None]*self.SIZE for _ in range(self.SIZE)]
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c]:
                    new_board.grid[r][c] = copy.deepcopy(self.grid[r][c])
        return new_board

    def find_pieces(self, color: ColorType) -> List[Tuple[int, int]]:
        result = []
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.grid[r][c]
                if piece and piece.color == color:
                    result.append((r, c))
        return result

    def is_king_row(self, row: int, color: ColorType) -> bool:
        # Белые становятся дамками на строке 9, чёрные на строке 0
        return (color == ColorType.WHITE and row == self.SIZE-1) or \
               (color == ColorType.BLACK and row == 0)

    def promote_to_king(self, row: int, col: int):
        piece = self.grid[row][col]
        if piece and piece.type == PieceType.MAN:
            self.grid[row][col] = Piece(piece.color, PieceType.KING)

class CheckersGame:
    def __init__(self, two_players=False):
        self.board = Board()
        self.current_turn = ColorType.WHITE
        self.two_players = two_players
        self.move_history: List[Move] = []
        self.captures_history: List[List[Tuple[int, int]]] = []  # для отката

    def get_all_valid_moves(self, color: ColorType) -> List[Move]:
        """Возвращает все возможные ходы для указанного цвета."""
        pieces = self.board.find_pieces(color)
        moves = []
        for (r, c) in pieces:
            piece = self.board.grid[r][c]
            if piece.type == PieceType.MAN:
                moves.extend(self._get_man_moves(r, c, color))
            else:
                moves.extend(self._get_king_moves(r, c, color))
        # Фильтруем: если есть взятия, оставляем только взятия (обязательное взятие)
        captures = [m for m in moves if m.captures]
        if captures:
            return captures
        # Если нет взятий, возвращаем все ходы
        return moves

    def _get_man_moves(self, row: int, col: int, color: ColorType) -> List[Move]:
        moves = []
        directions = []
        # Направления: вперёд по диагонали (для белых - вниз, для чёрных - вверх)
        if color == ColorType.WHITE:
            directions = [(1, -1), (1, 1)]
        else:
            directions = [(-1, -1), (-1, 1)]
        # Обычные ходы (только если нет взятий – проверка будет позже)
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if self.board._in_bounds(nr, nc) and not self.board.is_occupied(nr, nc):
                moves.append(Move(row, col, nr, nc, []))
        # Взятие (можно вперёд и назад)
        for dr in (-1, 1):
            for dc in (-1, 1):
                nr, nc = row + dr, col + dc
                if self.board._in_bounds(nr, nc):
                    target = self.board.get_piece(nr, nc)
                    if target and target.color != color:
                        # Проверяем, свободна ли клетка за ним
                        jr, jc = nr + dr, nc + dc
                        if self.board._in_bounds(jr, jc) and not self.board.is_occupied(jr, jc):
                            # Взятие одной шашки
                            moves.append(Move(row, col, jr, jc, [(nr, nc)]))
        return moves

    def _get_king_moves(self, row: int, col: int, color: ColorType) -> List[Move]:
        moves = []
        # Дамка ходит по диагоналям на любое расстояние, но не может перепрыгивать через свои
        for dr in (-1, 1):
            for dc in (-1, 1):
                # Обычные ходы (без взятия)
                r, c = row + dr, col + dc
                while self.board._in_bounds(r, c):
                    if self.board.is_occupied(r, c):
                        break
                    moves.append(Move(row, col, r, c, []))
                    r += dr
                    c += dc
                # Взятия
                # Ищем шашку противника на диагонали
                r, c = row + dr, col + dc
                while self.board._in_bounds(r, c):
                    if self.board.is_occupied(r, c):
                        target = self.board.get_piece(r, c)
                        if target.color != color:
                            # Проверяем, свободна ли клетка за ней (может быть несколько)
                            br, bc = r + dr, c + dc
                            while self.board._in_bounds(br, bc):
                                if self.board.is_occupied(br, bc):
                                    break
                                # Взятие с перепрыгиванием через одну шашку
                                # но в международных шашках дамка бьёт на любое расстояние, но перепрыгивает только одну шашку
                                # и останавливается сразу за ней (не может бить дальше, если есть другие?)
                                # Правило: дамка бьёт шашку противника, если за ней есть свободная клетка.
                                # Она может продолжить бить дальше, если после взятия снова есть возможность.
                                # В нашей модели мы добавим все возможные взятия как отдельные ходы (не комбинированные сразу).
                                # Комбинированные будут обрабатываться при поиске последовательностей.
                                moves.append(Move(row, col, br, bc, [(r, c)]))
                                # Для простоты: берём первую свободную клетку за шашкой
                                break
                            break  # после нахождения первой шашки на диагонали дальше не идём
                        else:
                            break
                    r += dr
                    c += dc
        return moves

    def is_valid_move(self, move: Move) -> bool:
        # Проверяем, что ход допустим (принадлежит множеству допустимых)
        all_moves = self.get_all_valid_moves(self.current_turn)
        for m in all_moves:
            if m.from_row == move.from_row and m.from_col == move.from_col and \
               m.to_row == move.to_row and m.to_col == move.to_col:
                # проверяем, что captures совпадают (порядок может отличаться, но у нас список)
                if set(m.captures) == set(move.captures):
                    return True
        return False

    def make_move(self, move: Move) -> bool:
        if not self.is_valid_move(move):
            return False
        # Выполняем ход
        piece = self.board.get_piece(move.from_row, move.from_col)
        if not piece:
            return False
        # Убираем с начальной позиции
        self.board.remove_piece(move.from_row, move.from_col)
        # Ставим на конечную
        self.board.place_piece(move.to_row, move.to_col, piece)
        # Убираем побитые шашки
        for (cr, cc) in move.captures:
            self.board.remove_piece(cr, cc)
        # Проверка на превращение в дамку
        if self.board.is_king_row(move.to_row, piece.color) and piece.type == PieceType.MAN:
            self.board.promote_to_king(move.to_row, move.to_col)
        # Запоминаем ход
        self.move_history.append(move)
        # Меняем игрока
        self.current_turn = self.current_turn.opponent()
        return True

    def is_game_over(self) -> Optional[ColorType]:
        """Возвращает победителя или None, если игра не окончена."""
        # Проверяем, есть ли у кого-то шашки
        white_pieces = self.board.find_pieces(ColorType.WHITE)
        black_pieces = self.board.find_pieces(ColorType.BLACK)
        if not white_pieces:
            return ColorType.BLACK
        if not black_pieces:
            return ColorType.WHITE
        # Проверка на возможность хода у текущего игрока
        moves = self.get_all_valid_moves(self.current_turn)
        if not moves:
            # Если нет ходов, текущий игрок проиграл
            return self.current_turn.opponent()
        return None

    def parse_move(self, input_str: str) -> Optional[Move]:
        """Парсит строку типа 'a1 b2' или 'a1 b2 c3 d4' для серии взятий.
        Возвращает объект Move с captures, соответствующими всем взятым шашкам.
        """
        parts = input_str.strip().split()
        if len(parts) < 2:
            return None
        # Преобразуем координаты
        coords = []
        for p in parts:
            match = re.match(r'^([A-Ja-j])([1-9]|10)$', p)
            if not match:
                return None
            col = ord(match.group(1).upper()) - ord('A')
            row = int(match.group(2)) - 1
            coords.append((row, col))
        if len(coords) < 2:
            return None
        from_r, from_c = coords[0]
        to_r, to_c = coords[-1]
        # Собираем captures: для каждой пары соседних координат ищем между ними побитые
        captures = []
        for i in range(len(coords)-1):
            r1, c1 = coords[i]
            r2, c2 = coords[i+1]
            # Проверяем, что они на одной диагонали
            if abs(r2-r1) != abs(c2-c1):
                return None
            # Проверяем, что между ними ровно одна клетка (для простых шашек) или более (для дамок) - но мы будем считать все клетки между
            # Для простоты: ищем клетки между r1,c1 и r2,c2, где есть шашка противника
            dr = 1 if r2 > r1 else -1
            dc = 1 if c2 > c1 else -1
            # Проверяем, что между ними нет пустых клеток (кроме побитых)
            # В нашей модели captures - это позиции побитых шашек, которые должны быть ровно на каждой промежуточной клетке
            # В международных шашках при серии взятий дамка может бить через несколько шашек, но мы будем считать каждую побитую.
            # Для простоты будем считать, что на каждой промежуточной клетке стоит шашка противника.
            # Проверим.
            cur_r, cur_c = r1 + dr, c1 + dc
            while (cur_r, cur_c) != (r2, c2):
                piece = self.board.get_piece(cur_r, cur_c)
                if piece is None or piece.color == self.current_turn:
                    # Если клетка пуста или там своя шашка - неверно
                    return None
                captures.append((cur_r, cur_c))
                cur_r += dr
                cur_c += dc
        # Теперь нужно проверить, что ход допустим (с учетом обязательности взятия)
        # Мы можем создать объект Move и проверить через is_valid_move
        return Move(from_r, from_c, to_r, to_c, captures)

    def display(self, color_mode=True):
        """Выводит доску с цветами."""
        print("  " + " ".join(chr(ord('A') + i) for i in range(self.SIZE)))
        for r in range(self.SIZE-1, -1, -1):
            row_label = str(r+1)
            if r+1 < 10:
                row_label = " " + row_label
            print(row_label, end=" ")
            for c in range(self.SIZE):
                piece = self.board.get_piece(r, c)
                if piece is None:
                    bg = 'white' if (r + c) % 2 == 0 else 'black'
                    if color_mode:
                        print(Color.colorize(' . ', bg=bg, fg='reset'), end="")
                    else:
                        print(' . ', end="")
                else:
                    symbol = 'W' if piece.color == ColorType.WHITE else 'B'
                    if piece.type == PieceType.KING:
                        symbol = 'W*' if piece.color == ColorType.WHITE else 'B*'
                    else:
                        symbol = 'W ' if piece.color == ColorType.WHITE else 'B '
                    bg = 'white' if (r + c) % 2 == 0 else 'black'
                    fg = 'black' if bg == 'white' else 'white'
                    if color_mode:
                        print(Color.colorize(symbol, fg=fg, bg=bg), end="")
                    else:
                        print(symbol, end=" ")
            print()
        print(f"Ход: {'Белые' if self.current_turn == ColorType.WHITE else 'Чёрные'}")

    def get_ai_move(self) -> Optional[Move]:
        """ИИ выбирает ход (сначала все взятия, потом случайный)."""
        moves = self.get_all_valid_moves(self.current_turn)
        if not moves:
            return None
        # Предпочитаем взятия
        capture_moves = [m for m in moves if m.captures]
        if capture_moves:
            return random.choice(capture_moves)
        return random.choice(moves)

    def save_state(self, filename: str):
        """Сохраняет состояние игры в JSON."""
        state = {
            'board': self._serialize_board(),
            'turn': self.current_turn.value,
            'history': [(m.from_row, m.from_col, m.to_row, m.to_col, m.captures) for m in self.move_history]
        }
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filename: str):
        with open(filename, 'r') as f:
            state = json.load(f)
        self.board = self._deserialize_board(state['board'])
        self.current_turn = ColorType(state['turn'])
        # Не восстанавливаем историю для простоты
        self.move_history = []

    def _serialize_board(self) -> List[List[Optional[Dict]]]:
        result = []
        for r in range(self.SIZE):
            row = []
            for c in range(self.SIZE):
                piece = self.board.grid[r][c]
                if piece:
                    row.append({
                        'color': piece.color.value,
                        'type': piece.type.value
                    })
                else:
                    row.append(None)
            result.append(row)
        return result

    def _deserialize_board(self, data: List[List[Optional[Dict]]]) -> Board:
        b = Board()
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if data[r][c]:
                    color = ColorType(data[r][c]['color'])
                    ptype = PieceType(data[r][c]['type'])
                    b.grid[r][c] = Piece(color, ptype)
                else:
                    b.grid[r][c] = None
        return b

def main():
    import argparse
    parser = argparse.ArgumentParser(description='International Checkers')
    parser.add_argument('--color', action='store_true', default=True, help='Цветной вывод')
    parser.add_argument('--no-color', action='store_true', help='Отключить цвет')
    parser.add_argument('--two-players', action='store_true', help='Режим для двух игроков')
    parser.add_argument('--save', help='Сохранять состояние в файл')
    parser.add_argument('--load', help='Загрузить состояние из файла')
    args = parser.parse_args()

    if args.no_color:
        ColorMode.ENABLED = False
    else:
        ColorMode.ENABLED = args.color

    game = CheckersGame(two_players=args.two_players)
    if args.load:
        game.load_state(args.load)

    while True:
        game.display(color_mode=ColorMode.ENABLED)
        winner = game.is_game_over()
        if winner:
            print(f"Победили {'Белые' if winner == ColorType.WHITE else 'Чёрные'}!")
            break
        # Ход
        if game.two_players:
            # Игроки по очереди
            current_color = game.current_turn
            player_name = 'Белые' if current_color == ColorType.WHITE else 'Чёрные'
            print(f"Ход {player_name}")
        else:
            if game.current_turn == ColorType.WHITE:
                player_name = 'Вы (белые)'
            else:
                player_name = 'Компьютер (чёрные)'
            if game.current_turn == ColorType.BLACK:
                # Компьютер ходит
                move = game.get_ai_move()
                if move:
                    game.make_move(move)
                    print(f"Компьютер сходил: {chr(ord('A')+move.from_col)}{move.from_row+1} -> {chr(ord('A')+move.to_col)}{move.to_row+1}")
                    if args.save:
                        game.save_state(args.save)
                continue

        # Ход игрока
        while True:
            move_str = input("Введите ход (например, a1 b2): ")
            if move_str.lower() in ('quit', 'exit'):
                sys.exit(0)
            move = game.parse_move(move_str)
            if move is None:
                print("Неверный формат хода.")
                continue
            if game.make_move(move):
                print("Ход принят.")
                if args.save:
                    game.save_state(args.save)
                break
            else:
                print("Недопустимый ход. Попробуйте снова.")

if __name__ == '__main__':
    main()
