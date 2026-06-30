import copy
import random

from square import Square
from move import Move
from piece import Pawn, King, Queen, Rook, Bishop, Knight


class ChessAI:
    """Internal chess bot controller with three school-project difficulty levels.

    v6.2 uses an internal engine only, because this is easier to run on school
    devices and simpler to document. The ELO labels are approximate gameplay
    targets, not official ratings.

    Easy   -> approx. 200-400: mostly random legal play with occasional captures.
    Medium -> approx. 600-800: basic tactics, checks and material awareness.
    Hard   -> approx. 1000-1200: shallow minimax with alpha-beta pruning and
              stronger blunder avoidance, while remaining beatable.
    """

    PIECE_VALUES = {
        'pawn': 1.0,
        'knight': 3.0,
        'bishop': 3.05,
        'rook': 5.0,
        'queen': 9.0,
        'king': 0.0,
    }

    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty

    def select_move(self, board, color):
        legal_moves = board.all_legal_moves(color)
        if not legal_moves:
            return None

        # All bots recognise a one-move checkmate sometimes, but easier bots are
        # intentionally less consistent so their behaviour feels like the target
        # rating range rather than perfect engine play.
        mate_move = self._mate_in_one(board, color, legal_moves)
        if mate_move is not None:
            if self.difficulty == 'hard' or random.random() < (0.45 if self.difficulty == 'medium' else 0.15):
                return mate_move

        if self.difficulty == 'easy':
            return self._easy_move(board, color, legal_moves)
        if self.difficulty == 'hard':
            return self._hard_move(board, color, legal_moves)
        return self._medium_move(board, color, legal_moves)

    # ------------------------------------------------------------------
    # Difficulty behaviour

    def _easy_move(self, board, color, legal_moves):
        """Approx. 200-400: careless, active and inconsistent.

        Easy should not be risk-averse. It still takes pieces and tries attacks,
        but it often fails to notice that the attacking move hangs something or
        creates a weakness. To avoid games ending instantly, it avoids the worst
        queen/rook blunders most of the time.
        """
        captures = self._capture_moves(board, legal_moves)
        checks = self._checking_moves(board, color, legal_moves)
        active = self._active_easy_moves(board, color, legal_moves)
        safeish = self._not_completely_losing_moves(board, color, legal_moves)

        roll = random.random()
        if captures and roll < 0.38:
            # Prefer captures, but not always the best capture.
            return self._weighted_random_capture(board, captures)
        if checks and roll < 0.56:
            return random.choice(checks)
        if active and roll < 0.78:
            return random.choice(active)
        if safeish and roll < 0.90:
            return random.choice(safeish)
        return random.choice(legal_moves)

    def _medium_move(self, board, color, legal_moves):
        """Approx. 600-800: sees obvious captures and checks, but misses tactics."""
        # Deliberate inconsistency prevents Medium from becoming too strong.
        if random.random() < 0.16:
            return random.choice(legal_moves)

        scored = []
        for piece, move in legal_moves:
            score = self._move_score(board, color, piece, move, tactical_only=True)
            score += random.uniform(-0.65, 0.65)
            scored.append((score, piece, move))
        scored.sort(key=lambda item: item[0], reverse=True)

        # Medium usually chooses from the top few candidate moves.
        top_n = min(5, len(scored))
        if top_n > 1 and random.random() < 0.32:
            _score, piece, move = random.choice(scored[:top_n])
        else:
            _score, piece, move = scored[0]
        return piece, move

    def _hard_move(self, board, color, legal_moves):
        """Approx. 1000-1200: shallow search with controlled human mistakes."""
        # If under check, reduce randomness and focus on survival.
        in_check = board.is_in_check(color)
        candidates = self._ordered_moves(board, color, legal_moves)[:20]

        # A small human-like imperfection rate remains so Hard is not unbeatable.
        if not in_check and random.random() < 0.07:
            safe_candidates = self._safe_candidate_moves(board, color, candidates)
            return random.choice(safe_candidates[:6] or candidates[:6] or legal_moves)

        return self._best_minimax_move(board, color, candidates, depth=2, noise=0.06)

    # ------------------------------------------------------------------
    # Move scoring and search

    def _mate_in_one(self, board, color, legal_moves):
        opponent = self._opponent(color)
        for piece, move in self._ordered_moves(board, color, legal_moves):
            new_board = self._board_after_move(board, piece, move)
            if new_board.is_checkmate(opponent):
                return piece, move
        return None

    def _checking_moves(self, board, color, legal_moves):
        opponent = self._opponent(color)
        checks = []
        for piece, move in legal_moves:
            new_board = self._board_after_move(board, piece, move)
            if new_board.is_in_check(opponent):
                checks.append((piece, move))
        return checks

    def _capture_moves(self, board, legal_moves):
        captures = []
        for piece, move in legal_moves:
            if self._captured_value(board, piece, move) > 0:
                captures.append((piece, move))
        return captures

    def _weighted_random_capture(self, board, captures):
        scored = []
        for piece, move in captures:
            value = self._captured_value(board, piece, move)
            # Easy likes material, but noise means it can choose a low-value or
            # tactically careless capture instead of the objectively best one.
            score = max(0.15, value + random.uniform(-1.2, 1.0))
            scored.append((score, piece, move))
        total = sum(score for score, _piece, _move in scored)
        pick = random.uniform(0, total)
        running = 0
        for score, piece, move in scored:
            running += score
            if running >= pick:
                return piece, move
        _score, piece, move = scored[-1]
        return piece, move

    def _active_easy_moves(self, board, color, legal_moves):
        opponent = self._opponent(color)
        active = []
        for piece, move in legal_moves:
            score = 0
            # Centre/development and attacking moves make Easy look like it is
            # trying to play chess, even if it misses the reply.
            score += self._centre_bonus(move.final.row, move.final.col)
            score += self._development_bonus(piece, move)
            new_board = self._board_after_move(board, piece, move)
            for row in range(8):
                for col in range(8):
                    target = new_board.squares[row][col].piece
                    if target and target.color == opponent:
                        moved_piece = new_board.squares[move.final.row][move.final.col].piece
                        if moved_piece and new_board.attacks_square(moved_piece, move.final.row, move.final.col, row, col):
                            score += 0.45
                            break
            # Do not regularly choose a move that hangs a queen or rook for free.
            penalty = self._safety_penalty_after_move(board, color, piece, move)
            if penalty <= max(5.5, self.PIECE_VALUES.get(piece.name, 1) * 1.15) and score > 0.18:
                active.append((piece, move))
        return active or legal_moves

    def _not_completely_losing_moves(self, board, color, legal_moves):
        filtered = []
        for piece, move in legal_moves:
            penalty = self._safety_penalty_after_move(board, color, piece, move)
            piece_value = self.PIECE_VALUES.get(piece.name, 1.0)
            # Easy can hang pawns/minor pieces, but usually avoids immediately
            # donating a queen or rook unless randomness selects from all moves.
            if penalty < max(3.8, piece_value * 1.05):
                filtered.append((piece, move))
        return filtered

    def _best_capture_move(self, board, color, legal_moves):
        scored = []
        for piece, move in legal_moves:
            captured = self._captured_value(board, piece, move)
            if captured > 0:
                scored.append((captured + random.uniform(-0.15, 0.15), piece, move))
        if not scored:
            return random.choice(legal_moves)
        scored.sort(key=lambda item: item[0], reverse=True)
        _score, piece, move = scored[0]
        return piece, move

    def _best_minimax_move(self, board, color, candidates, depth=2, noise=0.0):
        opponent = self._opponent(color)
        scored_moves = []
        for piece, move in candidates:
            new_board = self._board_after_move(board, piece, move)
            if new_board.is_checkmate(opponent):
                score = 100000
            else:
                score = self._minimax(new_board, depth - 1, opponent, color, float('-inf'), float('inf'))
            score += self._move_score(board, color, piece, move) * 0.18
            if noise:
                score += random.uniform(-noise, noise)
            scored_moves.append((score, piece, move))

        scored_moves.sort(key=lambda item: item[0], reverse=True)
        _score, piece, move = scored_moves[0]
        return piece, move

    def _minimax(self, board, depth, color_to_move, ai_color, alpha, beta):
        opponent = self._opponent(color_to_move)
        if board.is_checkmate(ai_color):
            return -100000
        if board.is_checkmate(self._opponent(ai_color)):
            return 100000
        if board.is_stalemate(color_to_move) or board.is_insufficient_material():
            return 0
        if depth == 0:
            return self._evaluate_for_color(board, ai_color)

        legal_moves = board.all_legal_moves(color_to_move)
        if not legal_moves:
            return self._evaluate_for_color(board, ai_color)

        ordered = self._ordered_moves(board, color_to_move, legal_moves)[:18]
        maximizing = color_to_move == ai_color

        if maximizing:
            best = float('-inf')
            for piece, move in ordered:
                new_board = self._board_after_move(board, piece, move)
                value = self._minimax(new_board, depth - 1, opponent, ai_color, alpha, beta)
                best = max(best, value)
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return best

        best = float('inf')
        for piece, move in ordered:
            new_board = self._board_after_move(board, piece, move)
            value = self._minimax(new_board, depth - 1, opponent, ai_color, alpha, beta)
            best = min(best, value)
            beta = min(beta, value)
            if beta <= alpha:
                break
        return best

    def _ordered_moves(self, board, color, legal_moves):
        ordered = []
        for piece, move in legal_moves:
            score = self._move_score(board, color, piece, move)
            ordered.append((score, piece, move))
        ordered.sort(key=lambda item: item[0], reverse=True)
        return [(piece, move) for _score, piece, move in ordered]

    def _safe_candidate_moves(self, board, color, moves):
        safe = []
        for piece, move in moves:
            if self._safety_penalty_after_move(board, color, piece, move) < max(2.0, abs(piece.value) * 0.55):
                safe.append((piece, move))
        return safe

    def _move_score(self, board, color, piece, move, tactical_only=False):
        opponent = self._opponent(color)
        new_board = self._board_after_move(board, piece, move)

        captured = self._captured_value(board, piece, move)
        score = captured * 3.0

        if new_board.is_checkmate(opponent):
            score += 100000
        elif new_board.is_in_check(opponent):
            score += 1.3

        # Avoid obvious hanging pieces, especially queens and rooks. This is the
        # main adjustment that makes Medium/Hard closer to their target ELO.
        safety_penalty = self._safety_penalty_after_move(board, color, piece, move)
        score -= safety_penalty

        if not tactical_only:
            score += self._evaluate_for_color(new_board, color) * 0.16
            score += self._mobility_bonus(new_board, color) * 0.035

        # Opening/development heuristics.
        score += self._development_bonus(piece, move)
        score += self._centre_bonus(move.final.row, move.final.col)

        # Discourage moving the king too early unless castling or escaping check.
        if isinstance(piece, King) and abs(move.final.col - move.initial.col) != 2:
            score -= 0.45

        return score

    def _evaluate_for_color(self, board, color):
        score = 0.0
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if not piece:
                    continue
                value = self.PIECE_VALUES.get(piece.name, 0.0)
                positional = self._piece_square_bonus(piece, row, col)
                if piece.color == color:
                    score += value + positional
                else:
                    score -= value + positional
        return score

    def _mobility_bonus(self, board, color):
        opponent = self._opponent(color)
        try:
            return len(board.all_legal_moves(color)) - len(board.all_legal_moves(opponent))
        except Exception:
            return 0

    def _piece_square_bonus(self, piece, row, col):
        centre = self._centre_bonus(row, col) * 0.30
        bonus = centre

        if isinstance(piece, Pawn):
            progress = (6 - row) if piece.color == 'white' else (row - 1)
            bonus += max(0, progress) * 0.035
        elif isinstance(piece, (Knight, Bishop)):
            home_row = 7 if piece.color == 'white' else 0
            if row != home_row:
                bonus += 0.12
        elif isinstance(piece, Rook):
            if col in (3, 4):
                bonus += 0.06
        elif isinstance(piece, King):
            home_row = 7 if piece.color == 'white' else 0
            if row != home_row:
                bonus -= 0.18

        return bonus

    def _development_bonus(self, piece, move):
        bonus = 0.0
        if isinstance(piece, (Knight, Bishop)):
            home_row = 7 if piece.color == 'white' else 0
            if move.initial.row == home_row:
                bonus += 0.35
        if isinstance(piece, Pawn):
            # Reward central pawn play in the opening.
            if move.final.col in (3, 4):
                bonus += 0.20
        if isinstance(piece, King) and abs(move.final.col - move.initial.col) == 2:
            bonus += 0.9
        return bonus

    def _centre_bonus(self, row, col):
        centre_distance = abs(3.5 - row) + abs(3.5 - col)
        return max(0.0, 3.5 - centre_distance) * 0.12

    # ------------------------------------------------------------------
    # Safety / attack helpers

    def _safety_penalty_after_move(self, board, color, piece, move):
        new_board = self._board_after_move(board, piece, move)
        moved_piece = new_board.squares[move.final.row][move.final.col].piece
        if not moved_piece or isinstance(moved_piece, King):
            return 0.0

        opponent = self._opponent(color)
        attackers = self._attackers(new_board, opponent, move.final.row, move.final.col)
        if not attackers:
            return 0.0

        defenders = self._attackers(new_board, color, move.final.row, move.final.col)
        moved_value = self.PIECE_VALUES.get(moved_piece.name, abs(moved_piece.value))
        min_attacker = min(self.PIECE_VALUES.get(p.name, abs(p.value)) for p in attackers)
        min_defender = min((self.PIECE_VALUES.get(p.name, abs(p.value)) for p in defenders), default=99.0)

        # A hanging piece is heavily punished. A defended piece is only punished
        # if the opponent attacks it with a cheaper piece.
        if not defenders:
            return moved_value * 0.95
        if min_attacker < moved_value and min_defender > min_attacker:
            return (moved_value - min_attacker) * 0.65
        return moved_value * 0.12

    def _attackers(self, board, color, target_row, target_col):
        attackers = []
        for row in range(8):
            for col in range(8):
                piece = board.squares[row][col].piece
                if piece and piece.color == color:
                    if board.attacks_square(piece, row, col, target_row, target_col):
                        attackers.append(piece)
        return attackers

    def _captured_value(self, board, piece, move):
        target = board.squares[move.final.row][move.final.col].piece
        if target:
            return self.PIECE_VALUES.get(target.name, abs(target.value))

        # En passant capture.
        if isinstance(piece, Pawn) and move.final.col != move.initial.col:
            side_piece = board.squares[move.initial.row][move.final.col].piece
            if isinstance(side_piece, Pawn) and side_piece.color != piece.color:
                return self.PIECE_VALUES['pawn']
        return 0.0

    def _board_after_move(self, board, piece, move):
        board_copy = copy.deepcopy(board)
        copied_piece = board_copy.squares[move.initial.row][move.initial.col].piece
        copied_move = Move(
            Square(move.initial.row, move.initial.col),
            Square(move.final.row, move.final.col)
        )
        board_copy.move(copied_piece, copied_move, testing=True)
        board_copy.set_true_en_passant(copied_piece)
        return board_copy

    def _opponent(self, color):
        return 'black' if color == 'white' else 'white'