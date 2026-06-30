from const import *
from square import Square
from piece import *
from move import Move
import copy


class Board:
    """Stores the chess board and calculates legal chess moves.

    The original project already handled piece movement. This version extends it
    with safer move generation helpers that can be used by the AI, game-over
    detection and post-game review.
    """

    def __init__(self):
        self.squares = [[0, 0, 0, 0, 0, 0, 0, 0] for _ in range(COLS)]
        self.last_move = None
        self._create()
        self._add_pieces('white')
        self._add_pieces('black')

    def move(self, piece, move, testing=False):
        """Move a piece on the board.

        The testing flag is kept for compatibility with the original project.
        Audio is now handled by Game so the board can be tested without pygame.
        """
        initial = move.initial
        final = move.final

        en_passant_empty = self.squares[final.row][final.col].isempty()
        is_en_passant = (
            isinstance(piece, Pawn)
            and final.col != initial.col
            and en_passant_empty
        )

        # Move the selected piece.
        self.squares[initial.row][initial.col].piece = None
        self.squares[final.row][final.col].piece = piece

        # En passant removes the pawn beside the starting square.
        if is_en_passant:
            captured_col = final.col
            self.squares[initial.row][captured_col].piece = None

        # Castling moves the rook after the king has moved two files.
        if isinstance(piece, King) and self.castling(initial, final):
            if final.col == 6:
                rook_initial_col = 7
                rook_final_col = 5
            else:
                rook_initial_col = 0
                rook_final_col = 3

            rook = self.squares[initial.row][rook_initial_col].piece
            self.squares[initial.row][rook_initial_col].piece = None
            self.squares[initial.row][rook_final_col].piece = rook
            if rook:
                rook.moved = True
                rook.clear_moves()

        if isinstance(piece, Pawn):
            self.check_promotion(piece, final)

        piece.moved = True
        piece.clear_moves()
        self.last_move = Move(
            Square(initial.row, initial.col),
            Square(final.row, final.col)
        )

    def valid_move(self, piece, move):
        return move in piece.moves

    def check_promotion(self, piece, final):
        if final.row == 0 or final.row == 7:
            self.squares[final.row][final.col].piece = Queen(piece.color)

    def castling(self, initial, final):
        return abs(initial.col - final.col) == 2

    def set_true_en_passant(self, piece):
        """Only a pawn that moved two squares can be captured en passant."""
        for row in range(ROWS):
            for col in range(COLS):
                board_piece = self.squares[row][col].piece
                if isinstance(board_piece, Pawn):
                    board_piece.en_passant = False

        if not isinstance(piece, Pawn) or self.last_move is None:
            return

        if abs(self.last_move.initial.row - self.last_move.final.row) == 2:
            piece.en_passant = True

    def in_check(self, piece, move):
        """Return True if this move leaves the moving side's king in check."""
        temp_board = copy.deepcopy(self)
        initial = move.initial
        final = move.final
        temp_piece = temp_board.squares[initial.row][initial.col].piece

        if temp_piece is None:
            return True

        temp_move = Move(Square(initial.row, initial.col), Square(final.row, final.col))
        temp_board.move(temp_piece, temp_move, testing=True)
        return temp_board.is_in_check(piece.color)

    def calc_moves(self, piece, row, col, bool=True):
        """Calculate valid moves for one piece on one square."""
        piece.clear_moves()

        def add_if_legal(move):
            if bool:
                if not self.in_check(piece, move):
                    piece.add_move(move)
            else:
                piece.add_move(move)

        def pawn_moves():
            steps = 1 if piece.moved else 2
            start = row + piece.dir
            end = row + (piece.dir * (1 + steps))

            # Forward movement.
            for possible_move_row in range(start, end, piece.dir):
                if not Square.in_range(possible_move_row):
                    break
                if self.squares[possible_move_row][col].isempty():
                    move = Move(Square(row, col), Square(possible_move_row, col))
                    add_if_legal(move)
                else:
                    break

            # Captures.
            possible_move_row = row + piece.dir
            for possible_move_col in (col - 1, col + 1):
                if Square.in_range(possible_move_row, possible_move_col):
                    target_piece = self.squares[possible_move_row][possible_move_col].piece
                    if self.squares[possible_move_row][possible_move_col].has_enemy_piece(piece.color):
                        move = Move(
                            Square(row, col),
                            Square(possible_move_row, possible_move_col, target_piece)
                        )
                        add_if_legal(move)

            # En passant.
            en_passant_row = 3 if piece.color == 'white' else 4
            final_row = 2 if piece.color == 'white' else 5
            if row == en_passant_row:
                for side_col in (col - 1, col + 1):
                    if Square.in_range(side_col):
                        side_piece = self.squares[row][side_col].piece
                        if isinstance(side_piece, Pawn) and side_piece.color != piece.color:
                            if side_piece.en_passant:
                                move = Move(
                                    Square(row, col),
                                    Square(final_row, side_col, side_piece)
                                )
                                add_if_legal(move)

        def knight_moves():
            possible_moves = [
                (row - 2, col + 1), (row - 1, col + 2),
                (row + 1, col + 2), (row + 2, col + 1),
                (row + 2, col - 1), (row + 1, col - 2),
                (row - 1, col - 2), (row - 2, col - 1),
            ]

            for possible_move_row, possible_move_col in possible_moves:
                if Square.in_range(possible_move_row, possible_move_col):
                    target_piece = self.squares[possible_move_row][possible_move_col].piece
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        move = Move(
                            Square(row, col),
                            Square(possible_move_row, possible_move_col, target_piece)
                        )
                        add_if_legal(move)

        def straightline_moves(increments):
            for row_incr, col_incr in increments:
                possible_move_row = row + row_incr
                possible_move_col = col + col_incr

                while Square.in_range(possible_move_row, possible_move_col):
                    target_square = self.squares[possible_move_row][possible_move_col]
                    target_piece = target_square.piece
                    move = Move(
                        Square(row, col),
                        Square(possible_move_row, possible_move_col, target_piece)
                    )

                    if target_square.isempty():
                        add_if_legal(move)
                    elif target_square.has_enemy_piece(piece.color):
                        add_if_legal(move)
                        break
                    else:
                        break

                    possible_move_row += row_incr
                    possible_move_col += col_incr

        def king_moves():
            adjacent_squares = [
                (row - 1, col), (row - 1, col + 1),
                (row, col + 1), (row + 1, col + 1),
                (row + 1, col), (row + 1, col - 1),
                (row, col - 1), (row - 1, col - 1),
            ]

            for possible_move_row, possible_move_col in adjacent_squares:
                if Square.in_range(possible_move_row, possible_move_col):
                    target_piece = self.squares[possible_move_row][possible_move_col].piece
                    if self.squares[possible_move_row][possible_move_col].isempty_or_enemy(piece.color):
                        move = Move(
                            Square(row, col),
                            Square(possible_move_row, possible_move_col, target_piece)
                        )
                        add_if_legal(move)

            # Castling. The king may not be in check, pass through check or land in check.
            if piece.moved or self.is_in_check(piece.color):
                return

            # Queen-side castling.
            left_rook = self.squares[row][0].piece
            if isinstance(left_rook, Rook) and not left_rook.moved:
                if all(self.squares[row][c].isempty() for c in (1, 2, 3)):
                    through = Move(Square(row, col), Square(row, 3))
                    final = Move(Square(row, col), Square(row, 2))
                    if not self.in_check(piece, through) and not self.in_check(piece, final):
                        piece.left_rook = left_rook
                        piece.add_move(final)

            # King-side castling.
            right_rook = self.squares[row][7].piece
            if isinstance(right_rook, Rook) and not right_rook.moved:
                if all(self.squares[row][c].isempty() for c in (5, 6)):
                    through = Move(Square(row, col), Square(row, 5))
                    final = Move(Square(row, col), Square(row, 6))
                    if not self.in_check(piece, through) and not self.in_check(piece, final):
                        piece.right_rook = right_rook
                        piece.add_move(final)

        if isinstance(piece, Pawn):
            pawn_moves()
        elif isinstance(piece, Knight):
            knight_moves()
        elif isinstance(piece, Bishop):
            straightline_moves([(-1, 1), (-1, -1), (1, 1), (1, -1)])
        elif isinstance(piece, Rook):
            straightline_moves([(-1, 0), (0, 1), (1, 0), (0, -1)])
        elif isinstance(piece, Queen):
            straightline_moves([
                (-1, 1), (-1, -1), (1, 1), (1, -1),
                (-1, 0), (0, 1), (1, 0), (0, -1)
            ])
        elif isinstance(piece, King):
            king_moves()

    def all_legal_moves(self, color):
        """Return all legal moves for a colour as (piece, move) pairs."""
        legal_moves = []
        for row in range(ROWS):
            for col in range(COLS):
                square = self.squares[row][col]
                if square.has_piece() and square.piece.color == color:
                    piece = square.piece
                    self.calc_moves(piece, row, col, bool=True)
                    for move in piece.moves:
                        legal_moves.append((piece, move))
        return legal_moves

    def has_legal_moves(self, color):
        return len(self.all_legal_moves(color)) > 0

    def is_checkmate(self, color):
        return self.is_in_check(color) and not self.has_legal_moves(color)

    def is_stalemate(self, color):
        return not self.is_in_check(color) and not self.has_legal_moves(color)

    def is_insufficient_material(self):
        pieces = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece:
                    pieces.append(piece)

        non_kings = [p for p in pieces if not isinstance(p, King)]
        if not non_kings:
            return True
        if len(non_kings) == 1 and isinstance(non_kings[0], (Bishop, Knight)):
            return True
        return False

    def find_king(self, color):
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if isinstance(piece, King) and piece.color == color:
                    return row, col
        return None

    def is_in_check(self, color):
        king_position = self.find_king(color)
        if king_position is None:
            return True

        king_row, king_col = king_position
        enemy_color = 'black' if color == 'white' else 'white'

        for row in range(ROWS):
            for col in range(COLS):
                piece = self.squares[row][col].piece
                if piece and piece.color == enemy_color:
                    if self.attacks_square(piece, row, col, king_row, king_col):
                        return True
        return False

    def attacks_square(self, piece, row, col, target_row, target_col):
        if isinstance(piece, Pawn):
            return target_row == row + piece.dir and target_col in (col - 1, col + 1)

        if isinstance(piece, Knight):
            return (target_row - row, target_col - col) in [
                (-2, 1), (-1, 2), (1, 2), (2, 1),
                (2, -1), (1, -2), (-1, -2), (-2, -1)
            ]

        if isinstance(piece, King):
            return max(abs(target_row - row), abs(target_col - col)) == 1

        directions = []
        if isinstance(piece, Bishop):
            directions = [(-1, 1), (-1, -1), (1, 1), (1, -1)]
        elif isinstance(piece, Rook):
            directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        elif isinstance(piece, Queen):
            directions = [
                (-1, 1), (-1, -1), (1, 1), (1, -1),
                (-1, 0), (0, 1), (1, 0), (0, -1)
            ]

        for row_step, col_step in directions:
            check_row = row + row_step
            check_col = col + col_step
            while Square.in_range(check_row, check_col):
                if check_row == target_row and check_col == target_col:
                    return True
                if self.squares[check_row][check_col].has_piece():
                    break
                check_row += row_step
                check_col += col_step
        return False

    def _create(self):
        for row in range(ROWS):
            for col in range(COLS):
                self.squares[row][col] = Square(row, col)

    def _add_pieces(self, color):
        row_pawn, row_other = (6, 7) if color == 'white' else (1, 0)

        for col in range(COLS):
            self.squares[row_pawn][col] = Square(row_pawn, col, Pawn(color))

        self.squares[row_other][1] = Square(row_other, 1, Knight(color))
        self.squares[row_other][6] = Square(row_other, 6, Knight(color))

        self.squares[row_other][2] = Square(row_other, 2, Bishop(color))
        self.squares[row_other][5] = Square(row_other, 5, Bishop(color))

        self.squares[row_other][0] = Square(row_other, 0, Rook(color))
        self.squares[row_other][7] = Square(row_other, 7, Rook(color))

        self.squares[row_other][3] = Square(row_other, 3, Queen(color))
        self.squares[row_other][4] = Square(row_other, 4, King(color))
