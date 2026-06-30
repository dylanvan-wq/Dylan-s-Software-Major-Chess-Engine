# main.py controls the main game loop, user input, screen updates and AI turns.

import pygame
import sys

from const import *
from game import Game


class Main:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Dylan Chess Engine')
        self.game = Game()

    def mainloop(self):
        screen = self.screen
        clock = pygame.time.Clock()

        while True:
            dt_ms = clock.tick(60)
            game = self.game

            game.update_clock(dt_ms)
            game.ai_move_if_needed()
            game.draw(screen)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Buttons remain the main control method for accessibility.
                    if game.handle_click(event.pos):
                        game.dragger.undrag_piece()
                        continue

                    # For the board, a normal click selects/moves pieces. A hold
                    # and drag from a piece draws a planning arrow instead.
                    if game.state == 'playing' and game.is_human_turn():
                        if game.begin_left_mouse_action(event.pos):
                            continue

                if event.type == pygame.MOUSEMOTION:
                    board_coords = game.screen_to_board(event.pos)
                    if game.state == 'playing' and board_coords is not None:
                        game.set_hover(*board_coords)
                    else:
                        game.hovered_sqr = None

                    if game.state == 'playing':
                        game.update_left_mouse_action(event.pos)
                        game.update_planning_arrow(event.pos)

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if game.state == 'playing' and game.is_human_turn():
                        if game.finish_left_mouse_action(event.pos):
                            continue

                # Right-click drag is kept as an optional shortcut, but the main
                # tested arrow workflow is left-click hold and drag.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and game.state == 'playing':
                    if game.start_planning_arrow(event.pos):
                        continue

                if event.type == pygame.MOUSEBUTTONUP and event.button == 3 and game.state == 'playing':
                    if game.finish_planning_arrow(event.pos):
                        continue


if __name__ == '__main__':
    main = Main()
    main.mainloop()
