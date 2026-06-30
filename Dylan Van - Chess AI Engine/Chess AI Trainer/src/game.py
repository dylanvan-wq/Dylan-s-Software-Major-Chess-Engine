import copy
import math
import os
import random
import threading
import pygame

from const import *
from board import Board
from dragger import Dragger
from config import Config
from square import Square
from move import Move
from piece import Pawn, King
from ai import ChessAI
import ai
print("AI FILE:", ai.__file__)


class Game:
    """Controls menu flow, game state, timers, AI and post-game review."""

    def __init__(self):
        self.hovered_sqr = None
        self.board = Board()
        self.dragger = Dragger()
        self.config = Config()

        # Menu selections. The game starts on the home menu instead of immediately
        # entering a match, which improves usability and client handover quality.
        self.state = 'menu'  # menu, playing or review
        self.menu_mode = 'ai'  # ai or pvp
        self.menu_color = 'white'  # white, black or random
        self.menu_time_seconds = 600  # 10 minutes by default, None means endless
        self.menu_difficulty = 'medium'

        # Active match settings.
        self.next_player = 'white'
        self.play_against_ai = True
        self.player_color = 'white'
        self.player_perspective = 'white'
        self.ai_color = 'black'
        self.ai_difficulty = 'medium'
        self.ai = ChessAI(self.ai_difficulty)
        self.time_control_seconds = 600
        self.white_time = 600.0
        self.black_time = 600.0

        self.status_message = 'Choose a mode to begin'
        self.countdown_until_ms = None
        self.result_message = ''
        self.game_over_title = ''
        self.game_over_reason = ''
        self.show_result_popup = False
        self.move_history = []
        self.board_snapshots = [copy.deepcopy(self.board)]
        self.review_index = 0
        self.position_counts = {}

        # Click-to-move controls. A piece is selected first, then the user
        # clicks a legal target square to complete the move.
        self.selected_piece = None
        self.selected_square = None

        # AI timing. Bot thinking is non-blocking, so the bot clock continues
        # running while it waits before moving. The actual bot calculation also
        # runs in a background thread so the pygame window does not freeze.
        self.ai_move_due_ms = None
        self.ai_worker_thread = None
        self.ai_worker_token = None
        self.ai_worker_result = None
        self.ai_worker_error = None

        # Small corner notifications for invalid actions such as illegal moves.
        self.toast_message = ''
        self.toast_until_ms = 0

        # v6.3 settings menu. Core match actions are hidden behind a small
        # cogwheel so the live side panel stays clean and readable.
        self.show_settings_menu = False

        # Planning arrows are a fair visual aid, similar to chess.com arrows.
        # They do not reveal best moves or allow undoing moves.
        self.planning_arrows = []
        self.arrow_start = None
        self.arrow_preview = None

        # Left-click drag arrows. A simple click still selects/moves pieces,
        # but holding and dragging from a piece creates a planning arrow.
        self.left_mouse_start_pos = None
        self.left_mouse_start_square = None
        self.left_dragging_arrow = False

        self.buttons = []
        self.sidebar_font = pygame.font.SysFont('arial', 18)
        self.small_font = pygame.font.SysFont('arial', 15)
        self.title_font = pygame.font.SysFont('arial', 28, bold=True)
        self.menu_title_font = pygame.font.SysFont('arial', 44, bold=True)
        self.status_font = pygame.font.SysFont('arial', 20, bold=True)
        self.popup_title_font = pygame.font.SysFont('arial', 40, bold=True)
        self.popup_reason_font = pygame.font.SysFont('arial', 20, bold=True)
        self.button_font = pygame.font.SysFont('arial', 16, bold=True)
        self.hud_font = pygame.font.SysFont('arial', 18, bold=True)
        self.hud_time_font = pygame.font.SysFont('arial', 20, bold=True)
        self.countdown_font = pygame.font.SysFont('arial', 72, bold=True)

        # Cache piece images once instead of reloading PNG files every frame.
        # This reduces frame drops on Mac during gameplay and review.
        self.image_cache = {}

    # ------------------------------------------------------------------
    # Main drawing methods

    def draw(self, surface):
        self.buttons = []
        if self.state == 'menu':
            self.show_menu(surface)
            return

        display_board = self.get_display_board()
        surface.fill(self._ui_palette()['page'])
        self.show_player_bars(surface)
        self.show_bg(surface)
        self.show_last_move(surface, display_board)
        if self.state == 'playing':
            self.show_check_indicator(surface, display_board)
            self.show_moves(surface)
        self.show_pieces(surface, display_board)
        if self.state == 'playing':
            self.show_planning_arrows(surface)
            self.show_hover(surface)
        if self.dragger.dragging and self.state == 'playing':
            self.dragger.update_blit(surface)
        self.show_sidebar(surface)
        if self.state == 'playing' and self.show_settings_menu:
            self.show_settings_menu_modal(surface)
        self.show_toast(surface)
        self.show_countdown_overlay(surface)

        # A clear result pop-up appears as soon as a match ends. This makes the
        # win/loss/draw condition obvious before the user enters review mode.
        if self.state == 'review' and self.show_result_popup:
            self.show_result_modal(surface)

    def show_menu(self, surface):
        surface.fill((18, 22, 30))

        # Decorative board preview using actual project assets. This avoids
        # unsupported Unicode chess symbols appearing as strange square boxes.
        board_x, board_y, size = 50, 145, 440
        sq = size // 8
        for row in range(8):
            for col in range(8):
                colour = (238, 218, 181) if (row + col) % 2 == 0 else (118, 82, 55)
                pygame.draw.rect(surface, colour, (board_x + col * sq, board_y + row * sq, sq, sq))
        pygame.draw.rect(surface, (255, 215, 120), (board_x, board_y, size, size), 4)
        self._draw_menu_starting_pieces(surface, board_x, board_y, sq)

        self._draw_text(surface, 'Chess Engine', 560, 55, self.menu_title_font, (255, 255, 255))
        subtitle_lines = [
            'Select your match settings before starting.'
        ]
        subtitle_y = 112
        for line in subtitle_lines:
            subtitle_y = self._draw_text(surface, line, 562, subtitle_y, self.sidebar_font, (210, 215, 225)) + 2

        x = 560
        y = 165
        y = self._draw_text(surface, '1. Game Mode', x, y, self.status_font, (255, 220, 120)) + 12
        self._draw_button(surface, 'mode_pvp', 'Player vs Player', (x, y, 200, 44), selected=self.menu_mode == 'pvp')
        self._draw_button(surface, 'mode_ai', 'Player vs Bot', (x + 220, y, 200, 44), selected=self.menu_mode == 'ai')

        y += 76
        y = self._draw_text(surface, '2. Play As', x, y, self.status_font, (255, 220, 120)) + 12
        self._draw_button(surface, 'color_white', 'White', (x, y, 128, 42), selected=self.menu_color == 'white')
        self._draw_button(surface, 'color_black', 'Black', (x + 145, y, 128, 42), selected=self.menu_color == 'black')
        self._draw_button(surface, 'color_random', 'Randomise', (x + 290, y, 146, 42), selected=self.menu_color == 'random')

        y += 74
        y = self._draw_text(surface, '3. Time Control', x, y, self.status_font, (255, 220, 120)) + 12
        self._draw_button(surface, 'time_600', '10 min Rapid', (x, y, 134, 42), selected=self.menu_time_seconds == 600)
        self._draw_button(surface, 'time_180', '3 min Blitz', (x + 150, y, 134, 42), selected=self.menu_time_seconds == 180)
        self._draw_button(surface, 'time_60', '1 min Bullet', (x + 300, y, 134, 42), selected=self.menu_time_seconds == 60)
        y += 50
        self._draw_button(surface, 'time_endless', 'Endless', (x, y, 134, 42), selected=self.menu_time_seconds is None)

        y += 74
        y = self._draw_text(surface, '4. Bot Difficulty', x, y, self.status_font, (255, 220, 120)) + 12
        disabled = self.menu_mode != 'ai'
        self._draw_button(surface, 'diff_easy', 'Easy\n200-400', (x, y, 134, 42), selected=self.menu_difficulty == 'easy', disabled=disabled)
        self._draw_button(surface, 'diff_medium', 'Medium\n600-800', (x + 150, y, 134, 42), selected=self.menu_difficulty == 'medium', disabled=disabled)
        self._draw_button(surface, 'diff_hard', 'Hard\n1000-1200', (x + 300, y, 134, 42), selected=self.menu_difficulty == 'hard', disabled=disabled)

        y += 82
        self._draw_button(surface, 'start_game', 'START MATCH', (x, y, 436, 56), selected=True, accent=True)

        y += 80
        for line in self.wrap_text(self._menu_summary(), 52):
            y = self._draw_text(surface, line, x, y, self.small_font, (195, 205, 220)) + 2

    def _draw_menu_starting_pieces(self, surface, board_x, board_y, sq):
        back_rank = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        for col, name in enumerate(back_rank):
            self._draw_menu_piece(surface, 'black', name, board_x, board_y, sq, 0, col)
            self._draw_menu_piece(surface, 'white', name, board_x, board_y, sq, 7, col)
        for col in range(8):
            self._draw_menu_piece(surface, 'black', 'pawn', board_x, board_y, sq, 1, col)
            self._draw_menu_piece(surface, 'white', 'pawn', board_x, board_y, sq, 6, col)

    def _draw_menu_piece(self, surface, color, name, board_x, board_y, sq, row, col):
        image_size = int(sq * 0.86)
        image = self._get_piece_image(color, name, image_size)
        center = (board_x + col * sq + sq // 2, board_y + row * sq + sq // 2)
        if image:
            surface.blit(image, image.get_rect(center=center))
        else:
            label = name[0].upper() if name != 'knight' else 'N'
            txt_color = (20, 20, 20) if color == 'black' else (245, 245, 245)
            rendered = self.button_font.render(label, True, txt_color)
            surface.blit(rendered, rendered.get_rect(center=center))

    def _get_piece_image(self, color, name, size):
        key = (color, name, size)
        if key in self.image_cache:
            return self.image_cache[key]

        image_path = os.path.join('assets', 'images', 'imgs-80px', f'{color}_{name}.png')
        try:
            image = pygame.image.load(image_path).convert_alpha()
            if image.get_width() != size or image.get_height() != size:
                image = pygame.transform.smoothscale(image, (size, size))
            self.image_cache[key] = image
            return image
        except pygame.error:
            self.image_cache[key] = None
            return None

    def show_bg(self, surface):
        theme = self.config.theme

        for board_row in range(ROWS):
            for board_col in range(COLS):
                screen_row, screen_col = self.board_to_screen(board_row, board_col)
                color = theme.bg.light if (board_row + board_col) % 2 == 0 else theme.bg.dark
                rect = (BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)

                if screen_col == 0:
                    label_color = theme.bg.dark if (board_row + board_col) % 2 == 0 else theme.bg.light
                    label = self.config.font.render(str(ROWS - board_row), True, label_color)
                    surface.blit(label, (BOARD_OFFSET_X + 5, BOARD_OFFSET_Y + 5 + screen_row * SQSIZE))

                if screen_row == 7:
                    label_color = theme.bg.dark if (board_row + board_col) % 2 == 0 else theme.bg.light
                    label = self.config.font.render(Square.get_alphacol(board_col), True, label_color)
                    surface.blit(label, (BOARD_OFFSET_X + screen_col * SQSIZE + SQSIZE - 20, BOARD_OFFSET_Y + BOARD_SIZE - 20))

    def show_pieces(self, surface, board=None):
        board = board or self.board
        for row in range(ROWS):
            for col in range(COLS):
                if board.squares[row][col].has_piece():
                    piece = board.squares[row][col].piece
                    if piece is not self.dragger.piece:
                        img = self._get_piece_image(piece.color, piece.name, 80)
                        if img is None:
                            continue
                        screen_row, screen_col = self.board_to_screen(row, col)
                        img_center = BOARD_OFFSET_X + screen_col * SQSIZE + SQSIZE // 2, BOARD_OFFSET_Y + screen_row * SQSIZE + SQSIZE // 2
                        piece.texture_rect = img.get_rect(center=img_center)
                        surface.blit(img, piece.texture_rect)

    def show_moves(self, surface):
        theme = self.config.theme
        piece = self.dragger.piece if self.dragger.dragging else self.selected_piece
        if not piece:
            return

        if self.selected_square:
            screen_row, screen_col = self.board_to_screen(self.selected_square[0], self.selected_square[1])
            selected_rect = (BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, (255, 220, 120), selected_rect, width=5)

        for move in piece.moves:
            screen_row, screen_col = self.board_to_screen(move.final.row, move.final.col)
            color = theme.moves.light if (move.final.row + move.final.col) % 2 == 0 else theme.moves.dark
            rect = (BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, color, rect)
            # A smaller centre dot makes legal destinations clear for click-to-move users.
            center = (BOARD_OFFSET_X + screen_col * SQSIZE + SQSIZE // 2, BOARD_OFFSET_Y + screen_row * SQSIZE + SQSIZE // 2)
            pygame.draw.circle(surface, (70, 85, 95), center, 12)

    def show_check_indicator(self, surface, board=None):
        board = board or self.board
        if not board.is_in_check(self.next_player):
            return

        king_pos = board.find_king(self.next_player)
        if king_pos is None:
            return

        screen_row, screen_col = self.board_to_screen(*king_pos)
        rect = pygame.Rect(BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
        overlay = pygame.Surface((SQSIZE, SQSIZE), pygame.SRCALPHA)
        overlay.fill((230, 50, 50, 95))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, (255, 60, 60), rect, width=6)

    def show_toast(self, surface):
        if not self.toast_message or pygame.time.get_ticks() > self.toast_until_ms:
            return

        text = self.small_font.render(self.toast_message, True, (255, 245, 245))
        padding_x, padding_y = 16, 10
        rect = pygame.Rect(18, HEIGHT - 58, text.get_width() + padding_x * 2, text.get_height() + padding_y * 2)
        pygame.draw.rect(surface, (115, 45, 45), rect, border_radius=8)
        pygame.draw.rect(surface, (255, 120, 120), rect, width=2, border_radius=8)
        surface.blit(text, (rect.x + padding_x, rect.y + padding_y))

    def show_last_move(self, surface, board=None):
        board = board or self.board
        theme = self.config.theme
        if board.last_move:
            for pos in (board.last_move.initial, board.last_move.final):
                screen_row, screen_col = self.board_to_screen(pos.row, pos.col)
                color = theme.trace.light if (pos.row + pos.col) % 2 == 0 else theme.trace.dark
                rect = (BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
                pygame.draw.rect(surface, color, rect)

    def show_hover(self, surface):
        if self.hovered_sqr:
            screen_row, screen_col = self.board_to_screen(self.hovered_sqr.row, self.hovered_sqr.col)
            rect = (BOARD_OFFSET_X + screen_col * SQSIZE, BOARD_OFFSET_Y + screen_row * SQSIZE, SQSIZE, SQSIZE)
            pygame.draw.rect(surface, (180, 180, 180), rect, width=3)

    def show_planning_arrows(self, surface):
        for start, end in self.planning_arrows:
            self._draw_arrow(surface, start, end, preview=False)
        if self.arrow_start and self.arrow_preview:
            self._draw_arrow(surface, self.arrow_start, self.arrow_preview, preview=True)

    def _draw_arrow(self, surface, start, end, preview=False):
        if start == end:
            return

        start_x, start_y = self.square_center(*start)
        end_x, end_y = self.square_center(*end)
        dx = end_x - start_x
        dy = end_y - start_y
        distance = max(1, math.hypot(dx, dy))
        unit_x = dx / distance
        unit_y = dy / distance

        # Shorten the line slightly so the arrow head sits cleanly on the target square.
        line_end = (end_x - unit_x * 18, end_y - unit_y * 18)
        alpha = 110 if preview else 175
        colour = (245, 190, 70, alpha)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(overlay, colour, (start_x, start_y), line_end, 12)

        angle = math.atan2(dy, dx)
        head_len = 32
        head_width = 22
        left = (
            end_x - head_len * math.cos(angle) + head_width * math.sin(angle),
            end_y - head_len * math.sin(angle) - head_width * math.cos(angle),
        )
        right = (
            end_x - head_len * math.cos(angle) - head_width * math.sin(angle),
            end_y - head_len * math.sin(angle) + head_width * math.cos(angle),
        )
        pygame.draw.polygon(overlay, colour, [(end_x, end_y), left, right])
        surface.blit(overlay, (0, 0))

    def square_center(self, row, col):
        screen_row, screen_col = self.board_to_screen(row, col)
        return (BOARD_OFFSET_X + screen_col * SQSIZE + SQSIZE // 2, BOARD_OFFSET_Y + screen_row * SQSIZE + SQSIZE // 2)

    def start_planning_arrow(self, pos):
        board_coords = self.screen_to_board(pos)
        if board_coords is None:
            return False
        row, col = board_coords
        if not self.board.squares[row][col].has_piece():
            return False
        self.arrow_start = board_coords
        self.arrow_preview = board_coords
        return True

    def update_planning_arrow(self, pos):
        if self.arrow_start is None:
            return
        board_coords = self.screen_to_board(pos)
        if board_coords is not None:
            self.arrow_preview = board_coords

    def finish_planning_arrow(self, pos):
        if self.arrow_start is None:
            return False
        start = self.arrow_start
        end = self.screen_to_board(pos)
        self.arrow_start = None
        self.arrow_preview = None

        if end is None or start == end:
            return True

        arrow = (start, end)
        if arrow in self.planning_arrows:
            self.planning_arrows.remove(arrow)
        else:
            self.planning_arrows.append(arrow)
            self.planning_arrows = self.planning_arrows[-12:]
        return True

    def begin_left_mouse_action(self, pos):
        board_coords = self.screen_to_board(pos)
        if board_coords is None:
            return False
        self.left_mouse_start_pos = pos
        self.left_mouse_start_square = board_coords
        self.left_dragging_arrow = False
        return True

    def update_left_mouse_action(self, pos):
        if self.left_mouse_start_square is None or self.left_mouse_start_pos is None:
            return

        start_x, start_y = self.left_mouse_start_pos
        current_x, current_y = pos
        drag_distance = math.hypot(current_x - start_x, current_y - start_y)

        if not self.left_dragging_arrow and drag_distance >= 12:
            start_row, start_col = self.left_mouse_start_square
            if not self.board.squares[start_row][start_col].has_piece():
                self.left_mouse_start_pos = None
                self.left_mouse_start_square = None
                return
            self.left_dragging_arrow = True
            self.arrow_start = self.left_mouse_start_square
            self.arrow_preview = self.left_mouse_start_square

        if self.left_dragging_arrow:
            board_coords = self.screen_to_board(pos)
            if board_coords is not None:
                self.arrow_preview = board_coords

    def finish_left_mouse_action(self, pos):
        if self.left_mouse_start_square is None:
            return False

        was_arrow_drag = self.left_dragging_arrow
        self.left_mouse_start_pos = None
        self.left_mouse_start_square = None
        self.left_dragging_arrow = False

        if was_arrow_drag:
            return self.finish_planning_arrow(pos)

        # A normal click clears visual planning arrows, then continues with the
        # click-to-select/click-to-move chess control. Dragging does not clear
        # existing arrows, which allows users to plan multiple lines.
        if self.screen_to_board(pos) is not None and self.planning_arrows:
            self.clear_planning_arrows()
        return self.handle_board_click(pos)

    def clear_planning_arrows(self):
        self.planning_arrows = []
        self.arrow_start = None
        self.arrow_preview = None

    def _ui_palette(self):
        """Return UI colours that stay consistent with the current board theme."""
        theme = self.config.theme
        accent = theme.trace.dark if isinstance(theme.trace.dark, tuple) else (222, 176, 62)
        board_dark = theme.bg.dark if isinstance(theme.bg.dark, tuple) else (55, 65, 80)
        panel = self._mix((18, 22, 30), board_dark, 0.24)
        page = self._mix((14, 18, 25), board_dark, 0.18)
        button = self._mix((42, 50, 64), board_dark, 0.25)
        return {
            'page': page,
            'panel': panel,
            'button': button,
            'button_border': self._mix((90, 100, 118), accent, 0.35),
            'accent': accent,
            'text': (245, 248, 255),
            'muted': (195, 205, 220),
        }

    def _mix(self, a, b, amount):
        return tuple(max(0, min(255, int(a[i] * (1 - amount) + b[i] * amount))) for i in range(3))

    def show_player_bars(self, surface):
        if self.state not in ('playing', 'review'):
            return
        palette = self._ui_palette()
        top_color = 'black' if self.player_perspective == 'white' else 'white'
        bottom_color = 'white' if self.player_perspective == 'white' else 'black'
        self._draw_player_bar(surface, top_color, top=True, palette=palette)
        self._draw_player_bar(surface, bottom_color, top=False, palette=palette)

    def _draw_player_bar(self, surface, color, top, palette):
        y = 0 if top else BOARD_OFFSET_Y + BOARD_SIZE
        rect = pygame.Rect(0, y, BOARD_SIZE, HUD_HEIGHT)
        pygame.draw.rect(surface, palette['panel'], rect)
        border_y = y + HUD_HEIGHT - 2 if top else y
        pygame.draw.rect(surface, palette['accent'], (0, border_y, BOARD_SIZE, 2))

        tag = self.player_tag(color)
        turn_marker = '  • to move' if self.state == 'playing' and self.next_player == color and not self.countdown_active() else ''
        label = f'{tag}{turn_marker}'
        label_img = self.hud_font.render(label, True, palette['text'])
        surface.blit(label_img, (18, y + (HUD_HEIGHT - label_img.get_height()) // 2))

        # Chess.com-style clock box on the right of the board area.
        time_text = self.player_time_text(color)
        time_img = self.hud_time_font.render(time_text, True, (20, 22, 28))
        box_w = max(128, time_img.get_width() + 34)
        box = pygame.Rect(BOARD_SIZE - box_w - 16, y + 7, box_w, HUD_HEIGHT - 14)
        box_bg = (238, 238, 238) if color == 'white' else (54, 58, 66)
        text_color = (20, 22, 28) if color == 'white' else (245, 248, 255)
        if self.state == 'playing' and self.next_player == color and not self.countdown_active():
            box_bg = palette['accent']
            text_color = (20, 22, 28)
        pygame.draw.rect(surface, box_bg, box, border_radius=8)
        pygame.draw.rect(surface, palette['button_border'], box, width=2, border_radius=8)
        time_img = self.hud_time_font.render(time_text, True, text_color)
        surface.blit(time_img, time_img.get_rect(center=box.center))

    def player_tag(self, color):
        color_name = color.title()
        if self.play_against_ai:
            if color == self.ai_color:
                return f'{self.ai_difficulty.title()} Bot ({color_name})'
            return f'Player 1 ({color_name})'
        if color == 'white':
            return 'Player 1 (White)'
        return 'Player 2 (Black)'

    def player_time_text(self, color):
        if color == 'white':
            return self.format_time(self.white_time)
        return self.format_time(self.black_time)

    def countdown_active(self):
        return self.countdown_until_ms is not None and pygame.time.get_ticks() < self.countdown_until_ms

    def show_countdown_overlay(self, surface):
        if self.state != 'playing' or not self.countdown_active():
            return
        remaining_ms = max(0, self.countdown_until_ms - pygame.time.get_ticks())
        number = max(1, math.ceil(remaining_ms / 1000))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 85))
        surface.blit(overlay, (0, 0))

        text = self.countdown_font.render(str(number), True, (255, 220, 120))
        centre = (BOARD_OFFSET_X + BOARD_SIZE // 2, BOARD_OFFSET_Y + BOARD_SIZE // 2 - 20)
        surface.blit(text, text.get_rect(center=centre))
        sub = self.status_font.render('Get ready', True, (245, 248, 255))
        surface.blit(sub, sub.get_rect(center=(centre[0], centre[1] + 70)))

    def show_sidebar(self, surface):
        panel_x = BOARD_SIZE
        palette = self._ui_palette()
        pygame.draw.rect(surface, palette['panel'], (panel_x, 0, SIDEBAR_WIDTH, HEIGHT))
        pygame.draw.line(surface, palette['button_border'], (panel_x, 0), (panel_x, HEIGHT), 2)

        y = 24
        y = self._draw_text(surface, 'Chess Engine', panel_x + 18, y, self.title_font, palette['text']) + 10
        y = self._draw_wrapped_text(
            surface,
            self.status_message,
            panel_x + 18,
            y,
            self.status_font,
            (250, 220, 120),
            SIDEBAR_WIDTH - 36,
            line_gap=4,
        ) + 14

        if self.state == 'playing':
            self._draw_play_sidebar(surface, panel_x, y)
            self._draw_settings_cog(surface, panel_x)
        elif self.state == 'review':
            self._draw_review_sidebar(surface, panel_x, y)

    def _draw_play_sidebar(self, surface, panel_x, y):
        palette = self._ui_palette()
        mode = 'Human vs AI' if self.play_against_ai else 'Human vs Human'
        y = self._draw_text(surface, 'Match Settings', panel_x + 18, y, self.status_font, palette['text']) + 10
        lines = [
            f'Mode: {mode}',
            f'Time: {self.time_control_name()}',
            f'View: {self.player_perspective.title()}',
        ]
        if self.play_against_ai:
            lines.append(f'Opponent: {self.ai_difficulty.title()} Bot')
        else:
            lines.append('Opponent: Player 2')
        for line in lines:
            y = self._draw_wrapped_text(surface, line, panel_x + 18, y, self.sidebar_font, palette['muted'], SIDEBAR_WIDTH - 36, line_gap=4) + 3

        y += 20
        y = self._draw_text(surface, 'Controls', panel_x + 18, y, self.status_font, palette['text']) + 12
        control_lines = [
            'Click a piece, then click a legal square to move.',
            'Hold and drag from a piece to draw a planning arrow.',
            'Click the board once to clear arrows.',
            'Use the cogwheel for match options.'
        ]
        for line in control_lines:
            y = self._draw_wrapped_text(surface, line, panel_x + 18, y, self.sidebar_font, palette['muted'], SIDEBAR_WIDTH - 36, line_gap=4) + 6

        # Change Theme remains on the live panel because it is a display option,
        # while match actions are moved into the settings menu.
        y = max(y + 12, HEIGHT - 150)
        self._draw_button(surface, 'theme', 'Change Theme', (panel_x + 18, y, 224, 40))

    def _draw_settings_cog(self, surface, panel_x):
        palette = self._ui_palette()
        rect = pygame.Rect(panel_x + SIDEBAR_WIDTH - 68, HEIGHT - 68, 50, 50)

        # Round app-style settings button.
        pygame.draw.circle(surface, palette['button'], rect.center, 25)
        pygame.draw.circle(surface, palette['button_border'], rect.center, 25, width=2)

        # Draw a proper gear/cog icon instead of a sun-like symbol. The teeth
        # are created as a filled polygon with an inner circular cut-out, similar
        # to settings icons used in common apps and websites.
        cx, cy = rect.center
        teeth = 8
        points = []
        root_radius = 13
        outer_radius = 20
        tooth_half_width = math.radians(8)
        for i in range(teeth):
            centre = (math.tau / teeth) * i - math.pi / 2
            gap_angle = centre - (math.tau / teeth) / 2
            points.append((cx + math.cos(gap_angle) * root_radius, cy + math.sin(gap_angle) * root_radius))
            points.append((cx + math.cos(centre - tooth_half_width) * outer_radius, cy + math.sin(centre - tooth_half_width) * outer_radius))
            points.append((cx + math.cos(centre + tooth_half_width) * outer_radius, cy + math.sin(centre + tooth_half_width) * outer_radius))
            next_gap = centre + (math.tau / teeth) / 2
            points.append((cx + math.cos(next_gap) * root_radius, cy + math.sin(next_gap) * root_radius))
        pygame.draw.polygon(surface, palette['text'], points)

        # Inner hole and subtle ring make it clearly read as a cogwheel.
        pygame.draw.circle(surface, palette['button'], rect.center, 8)
        pygame.draw.circle(surface, palette['text'], rect.center, 8, width=2)
        self.buttons.append({'id': 'settings_toggle', 'rect': rect, 'disabled': False})

    def show_settings_menu_modal(self, surface):
        palette = self._ui_palette()
        modal_w = SIDEBAR_WIDTH - 28
        modal_h = 260
        modal_x = BOARD_SIZE + 14
        modal_y = HEIGHT - modal_h - 82
        rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        shadow = pygame.Surface((modal_w + 12, modal_h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 95), shadow.get_rect(), border_radius=16)
        surface.blit(shadow, (modal_x + 5, modal_y + 7))

        pygame.draw.rect(surface, palette['panel'], rect, border_radius=14)
        pygame.draw.rect(surface, palette['button_border'], rect, width=2, border_radius=14)

        y = modal_y + 18
        y = self._draw_text(surface, 'Settings', modal_x + 18, y, self.status_font, palette['text']) + 14
        self._draw_button(surface, 'resign', 'Resign', (modal_x + 18, y, modal_w - 36, 38))
        y += 50
        self._draw_button(surface, 'restart_same', 'Restart Match', (modal_x + 18, y, modal_w - 36, 38))
        y += 50
        self._draw_button(surface, 'home_menu', 'Return to Home Menu', (modal_x + 18, y, modal_w - 36, 38))
        y += 50
        self._draw_button(surface, 'settings_close', 'Close', (modal_x + 18, y, modal_w - 36, 38))

    def _draw_review_sidebar(self, surface, panel_x, y):
        y = self._draw_text(surface, 'POST-GAME REVIEW', panel_x + 18, y, self.status_font, (120, 220, 255)) + 10
        for line in self.wrap_text(self.result_message, 28):
            y = self._draw_text(surface, line, panel_x + 18, y, self.sidebar_font, (230, 230, 230)) + 4

        y += 8
        y = self._draw_text(surface, f'Position: {self.review_index} / {len(self.board_snapshots) - 1}', panel_x + 18, y, self.sidebar_font, (250, 220, 120)) + 14

        self._draw_button(surface, 'review_start', 'Start', (panel_x + 18, y, 102, 34))
        self._draw_button(surface, 'review_end', 'Final', (panel_x + 140, y, 102, 34))
        y += 44
        self._draw_button(surface, 'review_prev', 'Previous', (panel_x + 18, y, 102, 34))
        self._draw_button(surface, 'review_next', 'Next', (panel_x + 140, y, 102, 34))

        y += 54
        y = self._draw_text(surface, 'Move History', panel_x + 18, y, self.status_font, (255, 255, 255)) + 10

        if not self.move_history:
            y = self._draw_text(surface, 'No moves recorded.', panel_x + 18, y, self.small_font, (205, 210, 220)) + 8
        else:
            current_move = max(1, self.review_index)
            start = max(0, current_move - 11)
            end = min(len(self.move_history), start + 15)
            for i in range(start, end):
                move_number = i + 1
                notation = self.move_history[i]['notation']
                player = 'W' if self.move_history[i]['color'] == 'white' else 'B'
                text = f'{move_number:>2}. {player}  {notation}'
                if move_number == self.review_index:
                    pygame.draw.rect(surface, (64, 78, 96), (panel_x + 12, y - 3, SIDEBAR_WIDTH - 24, 22), border_radius=4)
                    color = (255, 255, 255)
                else:
                    color = (205, 210, 220)
                y = self._draw_text(surface, text, panel_x + 18, y, self.small_font, color) + 5

        y = max(y + 10, HEIGHT - 120)
        self._draw_button(surface, 'restart_same', 'Play Again', (panel_x + 18, y, 224, 38))
        y += 48
        self._draw_button(surface, 'home_menu', 'Return to Home Menu', (panel_x + 18, y, 224, 38))

    def show_result_modal(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        surface.blit(overlay, (0, 0))

        modal_w, modal_h = 660, 330
        modal_x = (WIDTH - modal_w) // 2
        modal_y = (HEIGHT - modal_h) // 2
        rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(surface, (28, 34, 45), rect, border_radius=18)
        pygame.draw.rect(surface, (255, 220, 120), rect, width=3, border_radius=18)

        y = modal_y + 34
        title_color = (255, 220, 120) if self.game_over_title != 'DRAW' else (120, 220, 255)
        rendered = self.popup_title_font.render(self.game_over_title, True, title_color)
        surface.blit(rendered, rendered.get_rect(center=(modal_x + modal_w // 2, y + 28)))
        y += 82

        for line in self.wrap_text(self.game_over_reason, 48):
            rendered = self.popup_reason_font.render(line, True, (240, 245, 255))
            surface.blit(rendered, rendered.get_rect(center=(modal_x + modal_w // 2, y)))
            y += 30

        y += 18
        for line in self.wrap_text('Post-game review is now unlocked. Use it to replay the match and inspect the move history.', 62):
            rendered = self.sidebar_font.render(line, True, (195, 205, 220))
            surface.blit(rendered, rendered.get_rect(center=(modal_x + modal_w // 2, y)))
            y += 24

        button_y = modal_y + modal_h - 72
        self._draw_button(surface, 'dismiss_result', 'Review Game', (modal_x + 52, button_y, 170, 44), selected=True)
        self._draw_button(surface, 'restart_same', 'Play Again', (modal_x + 245, button_y, 170, 44))
        self._draw_button(surface, 'home_menu', 'Return to\nHome Menu', (modal_x + 438, button_y, 170, 44))

    # ------------------------------------------------------------------
    # Button and UI helpers

    def _draw_text(self, surface, text, x, y, font, color):
        rendered = font.render(text, True, color)
        surface.blit(rendered, (x, y))
        return y + rendered.get_height()

    def _draw_wrapped_text(self, surface, text, x, y, font, color, max_width, line_gap=3):
        words = text.split()
        line = ''
        for word in words:
            test_line = f'{line} {word}'.strip()
            if font.size(test_line)[0] <= max_width:
                line = test_line
            else:
                if line:
                    y = self._draw_text(surface, line, x, y, font, color) + line_gap
                line = word
        if line:
            y = self._draw_text(surface, line, x, y, font, color) + line_gap
        return y

    def _draw_button(self, surface, button_id, text, rect_tuple, selected=False, disabled=False, accent=False):
        rect = pygame.Rect(rect_tuple)
        palette = self._ui_palette()
        if disabled:
            bg, border, txt = (68, 72, 80), (90, 94, 104), (150, 155, 165)
        elif accent:
            bg, border, txt = palette['accent'], self._mix((255, 255, 255), palette['accent'], 0.35), (22, 24, 30)
        elif selected:
            bg, border, txt = self._mix((55, 80, 130), palette['accent'], 0.35), palette['accent'], (255, 255, 255)
        else:
            bg, border, txt = palette['button'], palette['button_border'], (230, 235, 245)

        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=8)

        lines = str(text).split('\n')
        rendered_lines = [self.button_font.render(line, True, txt) for line in lines]
        total_height = sum(img.get_height() for img in rendered_lines) + max(0, len(rendered_lines) - 1) * 1
        y = rect.centery - total_height // 2
        for img in rendered_lines:
            surface.blit(img, img.get_rect(centerx=rect.centerx, y=y))
            y += img.get_height() + 1

        self.buttons.append({'id': button_id, 'rect': rect, 'disabled': disabled})

    def handle_click(self, pos):
        if self.show_settings_menu and self.state == 'playing':
            settings_ids = {'settings_toggle', 'settings_close', 'resign', 'restart_same', 'home_menu'}
            for button in reversed(self.buttons):
                if button['id'] in settings_ids and button['rect'].collidepoint(pos) and not button['disabled']:
                    self._activate_button(button['id'])
                    return True
            self.show_settings_menu = False
            return True

        for button in reversed(self.buttons):
            if button['rect'].collidepoint(pos) and not button['disabled']:
                self._activate_button(button['id'])
                return True
        return False

    def _activate_button(self, button_id):
        if button_id == 'mode_pvp':
            self.menu_mode = 'pvp'
        elif button_id == 'mode_ai':
            self.menu_mode = 'ai'
        elif button_id == 'color_white':
            self.menu_color = 'white'
        elif button_id == 'color_black':
            self.menu_color = 'black'
        elif button_id == 'color_random':
            self.menu_color = 'random'
        elif button_id == 'time_600':
            self.menu_time_seconds = 600
        elif button_id == 'time_180':
            self.menu_time_seconds = 180
        elif button_id == 'time_60':
            self.menu_time_seconds = 60
        elif button_id == 'time_endless':
            self.menu_time_seconds = None
        elif button_id == 'diff_easy':
            self.menu_difficulty = 'easy'
        elif button_id == 'diff_medium':
            self.menu_difficulty = 'medium'
        elif button_id == 'diff_hard':
            self.menu_difficulty = 'hard'
        elif button_id == 'start_game':
            self.start_game()
        elif button_id == 'restart_same':
            self.show_settings_menu = False
            self.start_game()
        elif button_id == 'home_menu':
            self.show_settings_menu = False
            self.return_to_menu()
        elif button_id == 'theme':
            self.change_theme()
        elif button_id == 'resign':
            self.show_settings_menu = False
            self.resign_current_player()
        elif button_id == 'settings_toggle':
            self.show_settings_menu = not self.show_settings_menu
        elif button_id == 'settings_close':
            self.show_settings_menu = False
        elif button_id == 'dismiss_result':
            self.show_result_popup = False
        elif button_id == 'review_previous' or button_id == 'review_prev':
            self.review_previous()
        elif button_id == 'review_next':
            self.review_next()
        elif button_id == 'review_start':
            self.review_start()
        elif button_id == 'review_end':
            self.review_end()

    def wrap_text(self, text, max_chars):
        words = text.split()
        lines = []
        current = ''
        for word in words:
            if len(current) + len(word) + 1 > max_chars:
                if current:
                    lines.append(current)
                current = word
            else:
                current = f'{current} {word}'.strip()
        if current:
            lines.append(current)
        return lines

    def _menu_summary(self):
        mode = 'Player vs Bot' if self.menu_mode == 'ai' else 'Player vs Player'
        colour = self.menu_color.title()
        time_name = self.time_control_name(self.menu_time_seconds)
        if self.menu_mode == 'ai':
            return f'Selected: {mode} | {colour} | {time_name} | {self.menu_difficulty.title()} bot'
        return f'Selected: {mode} | {colour} perspective | {time_name}'

    # ------------------------------------------------------------------
    # Coordinate helpers for board orientation

    def board_to_screen(self, row, col):
        if self.player_perspective == 'black':
            return 7 - row, 7 - col
        return row, col

    def screen_to_board(self, pos):
        x, y = pos
        board_x = x - BOARD_OFFSET_X
        board_y = y - BOARD_OFFSET_Y
        if board_x < 0 or board_y < 0 or board_x >= BOARD_SIZE or board_y >= BOARD_SIZE:
            return None
        screen_row = board_y // SQSIZE
        screen_col = board_x // SQSIZE
        if self.player_perspective == 'black':
            return 7 - screen_row, 7 - screen_col
        return screen_row, screen_col

    # ------------------------------------------------------------------
    # Match lifecycle and timer methods

    def reset_ai_worker(self):
        """Invalidate any pending bot move without blocking the UI thread."""
        self.ai_move_due_ms = None
        self.ai_worker_thread = None
        self.ai_worker_token = None
        self.ai_worker_result = None
        self.ai_worker_error = None

    def begin_ai_worker(self):
        """Start calculating the bot move in the background.

        v5.2 delayed the bot with a timer, but the move calculation still ran
        inside the main pygame loop. On macOS this made the cursor show the
        loading spinner and froze the clocks. This worker keeps rendering and
        timing responsive while the AI searches.
        """
        token = (len(self.move_history), self.next_player, self.position_key())
        self.ai_worker_token = token
        self.ai_worker_result = None
        self.ai_worker_error = None

        board_copy = copy.deepcopy(self.board)
        bot_color = self.ai_color
        difficulty = self.ai_difficulty

        def worker():
            try:
                ai = ChessAI(difficulty)
                legal_moves = board_copy.all_legal_moves(bot_color)
                choice = random.choice(legal_moves) if legal_moves else None
                if choice is None:
                    result = None
                else:
                    _piece, move = choice
                    result = (
                        move.initial.row,
                        move.initial.col,
                        move.final.row,
                        move.final.col,
                    )
                self.ai_worker_result = (token, result)
            except Exception as exc:
                self.ai_worker_error = (token, str(exc))

        self.ai_worker_thread = threading.Thread(target=worker, daemon=True)
        self.ai_worker_thread.start()

    def start_game(self):
        chosen_color = self.menu_color
        if chosen_color == 'random':
            chosen_color = random.choice(['white', 'black'])

        self.state = 'playing'
        self.board = Board()
        self.dragger = Dragger()
        self.hovered_sqr = None
        self.next_player = 'white'
        self.result_message = ''
        self.game_over_title = ''
        self.game_over_reason = ''
        self.show_result_popup = False
        self.move_history = []
        self.board_snapshots = [copy.deepcopy(self.board)]
        self.review_index = 0
        self.selected_piece = None
        self.selected_square = None
        self.show_settings_menu = False
        self.reset_ai_worker()
        self.toast_message = ''
        self.toast_until_ms = 0

        self.time_control_seconds = self.menu_time_seconds
        if self.menu_time_seconds is None:
            self.white_time = None
            self.black_time = None
        else:
            self.white_time = float(self.menu_time_seconds)
            self.black_time = float(self.menu_time_seconds)
        self.play_against_ai = self.menu_mode == 'ai'
        self.player_color = chosen_color
        self.player_perspective = chosen_color
        if self.menu_difficulty not in ('easy', 'medium', 'hard'):
            self.menu_difficulty = 'medium'
        self.ai_difficulty = self.menu_difficulty
        self.ai = ChessAI(self.ai_difficulty)
        self.position_counts = {self.position_key(): 1}
        self.clear_planning_arrows()
        self.countdown_until_ms = pygame.time.get_ticks() + 5000

        if self.play_against_ai:
            self.ai_color = 'black' if self.player_color == 'white' else 'white'
            self.status_message = 'White to move'
        else:
            self.ai_color = None
            self.status_message = 'White to move'

    def return_to_menu(self):
        self.dragger.undrag_piece()
        self.state = 'menu'
        self.show_result_popup = False
        self.clear_planning_arrows()
        self.selected_piece = None
        self.selected_square = None
        self.reset_ai_worker()
        self.show_settings_menu = False
        self.countdown_until_ms = None
        self.status_message = 'Choose a mode to begin'
        self.countdown_until_ms = None

    def update_clock(self, dt_ms):
        if self.state != 'playing':
            return

        if self.countdown_until_ms is not None:
            if pygame.time.get_ticks() < self.countdown_until_ms:
                self.status_message = 'Match starting soon'
                return
            self.countdown_until_ms = None
            self.update_game_status()

        if self.time_control_seconds is None:
            return

        # Both the human and bot clocks run after the five-second countdown.
        decrement = dt_ms / 1000.0
        if self.next_player == 'white':
            self.white_time = max(0.0, self.white_time - decrement)
            if self.white_time <= 0:
                self.finish_by_timeout('white')
        else:
            self.black_time = max(0.0, self.black_time - decrement)
            if self.black_time <= 0:
                self.finish_by_timeout('black')

    def finish_by_timeout(self, losing_color):
        winner = 'black' if losing_color == 'white' else 'white'
        reason = f'{losing_color.title()} ran out of time. {winner.title()} wins on time.'
        self.finish_game(winner=winner, condition='time', reason=reason)

    def resign_current_player(self):
        if self.state != 'playing':
            return
        losing_color = self.next_player
        winner = 'black' if losing_color == 'white' else 'white'
        reason = f'{losing_color.title()} resigned. {winner.title()} wins by resignation.'
        self.finish_game(winner=winner, condition='resignation', reason=reason)

    def finish_game(self, winner=None, condition='game over', reason=''):
        self.state = 'review'
        self.show_result_popup = True
        self.clear_planning_arrows()
        self.dragger.undrag_piece()
        self.selected_piece = None
        self.selected_square = None
        self.reset_ai_worker()
        self.show_settings_menu = False
        self.countdown_until_ms = None
        self.review_index = len(self.board_snapshots) - 1

        if winner is None:
            self.game_over_title = 'DRAW'
            self.result_message = reason or f'Draw by {condition}.'
            self.status_message = f'Draw: {condition}'
        else:
            self.game_over_title = self.outcome_title(winner)
            self.result_message = reason or f'{winner.title()} wins by {condition}.'
            self.status_message = f'{winner.title()} wins by {condition}'

        self.game_over_reason = reason or self.result_message

    def outcome_title(self, winner):
        if self.play_against_ai:
            if winner == self.player_color:
                return 'YOU WIN'
            if winner == self.ai_color:
                return 'YOU LOSE'
        return f'{winner.upper()} WINS'

    def time_control_name(self, seconds='active'):
        if seconds == 'active':
            seconds = self.time_control_seconds
        if seconds is None:
            return 'Endless'
        if seconds == 600:
            return '10 min Rapid'
        if seconds == 180:
            return '3 min Blitz'
        if seconds == 60:
            return '1 min Bullet'
        return f'{seconds // 60} min'

    def format_time(self, seconds):
        if seconds is None:
            return 'No limit'
        # Display as minutes:seconds:hundredths. This gives the user
        # visible millisecond-style feedback during blitz and bullet games.
        total_hundredths = max(0, int(seconds * 100))
        minutes = total_hundredths // 6000
        secs = (total_hundredths % 6000) // 100
        hundredths = total_hundredths % 100
        return f'{minutes:02d}:{secs:02d}:{hundredths:02d}'

    # ------------------------------------------------------------------
    # Game-state methods

    def make_move(self, piece, move, made_by_ai=False):
        captured = self.is_capture(piece, move)
        notation = self.create_notation(piece, move, captured)
        moving_color = piece.color

        self.board.move(piece, move, testing=True)
        self.board.set_true_en_passant(piece)

        opponent = 'black' if moving_color == 'white' else 'white'
        if self.board.is_checkmate(opponent):
            notation += '#'
        elif self.board.is_in_check(opponent):
            notation += '+'

        self.play_sound(captured)
        self.move_history.append({
            'notation': notation,
            'color': moving_color,
            'ai': made_by_ai,
        })

        self.next_turn()
        self.board_snapshots.append(copy.deepcopy(self.board))
        self.review_index = len(self.board_snapshots) - 1

        key = self.position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        self.clear_planning_arrows()
        self.selected_piece = None
        self.selected_square = None
        self.reset_ai_worker()
        self.update_game_status()

    def update_game_status(self):
        if self.position_counts.get(self.position_key(), 0) >= 3:
            self.finish_game(winner=None, condition='threefold repetition', reason='Draw by threefold repetition. The same position occurred three times.')
            return

        if self.board.is_insufficient_material():
            self.finish_game(winner=None, condition='insufficient material', reason='Draw by insufficient material. Neither side has enough material to force checkmate.')
            return

        if self.board.is_checkmate(self.next_player):
            winner = 'black' if self.next_player == 'white' else 'white'
            reason = f'{winner.title()} wins by checkmate. {self.next_player.title()} has no legal move to escape check.'
            self.finish_game(winner=winner, condition='checkmate', reason=reason)
            return

        if self.board.is_stalemate(self.next_player):
            self.finish_game(winner=None, condition='stalemate', reason=f'Draw by stalemate. {self.next_player.title()} is not in check but has no legal moves.')
            return

        if self.board.is_in_check(self.next_player):
            self.status_message = f'{self.next_player.title()} is in check'
        else:
            self.status_message = f'{self.next_player.title()} to move'

    def handle_board_click(self, pos):
        board_coords = self.screen_to_board(pos)
        if board_coords is None:
            return False

        row, col = board_coords
        if not Square.in_range(row, col):
            return False

        clicked_square = self.board.squares[row][col]

        # First click or changing selection: select one of the current player's pieces.
        if clicked_square.has_piece() and clicked_square.piece.color == self.next_player:
            self.selected_piece = clicked_square.piece
            self.selected_square = (row, col)
            self.board.calc_moves(self.selected_piece, row, col, bool=True)
            return True

        # Second click: try to move the selected piece to the clicked square.
        if self.selected_piece and self.selected_square:
            initial = Square(self.selected_square[0], self.selected_square[1])
            final = Square(row, col)
            move = Move(initial, final)
            if self.board.valid_move(self.selected_piece, move):
                self.make_move(self.selected_piece, move, made_by_ai=False)
            else:
                self.notify('Illegal move')
            return True

        return False

    def notify(self, message, duration_ms=1700):
        self.toast_message = message
        self.toast_until_ms = pygame.time.get_ticks() + duration_ms

    def ai_move_if_needed(self):
        if self.state != 'playing':
            self.reset_ai_worker()
            return
        if self.countdown_active():
            return
        if not self.play_against_ai or self.next_player != self.ai_color:
            self.reset_ai_worker()
            return

        now = pygame.time.get_ticks()
        current_token = (len(self.move_history), self.next_player, self.position_key())

        if self.ai_move_due_ms is None:
            delay_seconds = self.ai_thinking_delay_seconds()
            self.ai_move_due_ms = now + int(delay_seconds * 1000)
            self.status_message = f'{self.ai_color.title()} bot is thinking...'
            self.begin_ai_worker()
            return

        if self.ai_worker_token != current_token:
            # The position changed while a stale worker was still finishing.
            self.reset_ai_worker()
            return

        if now < self.ai_move_due_ms:
            return

        if self.ai_worker_error and self.ai_worker_error[0] == current_token:
            print("BOT ERROR:", self.ai_worker_error[1])
            self.notify(f'Bot error: {self.ai_worker_error[1]}')
            self.reset_ai_worker()
            self.update_game_status()
            return

        if self.ai_worker_thread and self.ai_worker_thread.is_alive():
            # Harder AI may still be searching. Keep the app responsive and let
            # the bot's clock continue to run until the move is ready.
            self.status_message = f'{self.ai_color.title()} bot is calculating...'
            return

        if not self.ai_worker_result or self.ai_worker_result[0] != current_token:
            self.reset_ai_worker()
            return

        _token, result = self.ai_worker_result
        if result is None:
            self.reset_ai_worker()
            self.update_game_status()
            return

        initial_row, initial_col, final_row, final_col = result
        piece = self.board.squares[initial_row][initial_col].piece
        move = Move(Square(initial_row, initial_col), Square(final_row, final_col))

        if piece is None or piece.color != self.ai_color or not self.board.valid_move(piece, move):
            # Defensive fallback in case a worker result ever becomes invalid.
            legal_moves = self.board.all_legal_moves(self.ai_color)
            if not legal_moves:
                self.reset_ai_worker()
                self.update_game_status()
                return
            piece, move = random.choice(legal_moves)

        self.reset_ai_worker()
        self.make_move(piece, move, made_by_ai=True)

    def ai_thinking_delay_seconds(self):
        if self.ai_difficulty == 'easy':
            return random.uniform(4.0, 5.0)
        if self.ai_difficulty == 'medium':
            return random.uniform(3.0, 4.0)
        if self.ai_difficulty == 'hard':
            return random.uniform(2.0, 3.0)
        return random.uniform(3.0, 4.0)

    def is_human_turn(self):
        if self.countdown_active():
            return False
        return not (self.play_against_ai and self.next_player == self.ai_color)

    def next_turn(self):
        self.next_player = 'white' if self.next_player == 'black' else 'black'

    def set_hover(self, row, col):
        if Square.in_range(row, col):
            self.hovered_sqr = self.board.squares[row][col]
        else:
            self.hovered_sqr = None

    def change_theme(self):
        self.config.change_theme()

    def review_previous(self):
        if self.state == 'review':
            self.show_result_popup = False
            self.review_index = max(0, self.review_index - 1)

    def review_next(self):
        if self.state == 'review':
            self.show_result_popup = False
            self.review_index = min(len(self.board_snapshots) - 1, self.review_index + 1)

    def review_start(self):
        if self.state == 'review':
            self.show_result_popup = False
            self.review_index = 0

    def review_end(self):
        if self.state == 'review':
            self.show_result_popup = False
            self.review_index = len(self.board_snapshots) - 1

    def get_display_board(self):
        if self.state == 'review':
            return self.board_snapshots[self.review_index]
        return self.board

    def is_capture(self, piece, move):
        if self.board.squares[move.final.row][move.final.col].has_piece():
            return True
        return isinstance(piece, Pawn) and move.initial.col != move.final.col

    def create_notation(self, piece, move, captured=False):
        if isinstance(piece, King) and abs(move.initial.col - move.final.col) == 2:
            return 'O-O' if move.final.col == 6 else 'O-O-O'

        piece_letters = {
            'pawn': '',
            'knight': 'N',
            'bishop': 'B',
            'rook': 'R',
            'queen': 'Q',
            'king': 'K',
        }
        start_file = Square.get_alphacol(move.initial.col)
        target = self.square_name(move.final.row, move.final.col)
        letter = piece_letters.get(piece.name, '')

        if piece.name == 'pawn':
            if captured:
                return f'{start_file}x{target}'
            return target
        if captured:
            return f'{letter}x{target}'
        return f'{letter}{target}'

    def square_name(self, row, col):
        return f'{Square.get_alphacol(col)}{8 - row}'

    def position_key(self):
        pieces = []
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board.squares[row][col].piece
                if piece is None:
                    pieces.append('--')
                else:
                    moved_flag = '1' if piece.moved else '0'
                    pieces.append(f'{piece.color[0]}{piece.name[0]}{moved_flag}')
        return '|'.join(pieces) + f'|turn:{self.next_player}'

    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()
