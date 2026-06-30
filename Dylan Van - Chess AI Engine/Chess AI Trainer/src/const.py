# Screen dimensions
# ==========================
# Screen Dimensions
# ==========================

BOARD_SIZE = 680

HUD_HEIGHT = 40          # Used for BOTH top and bottom bars
SIDEBAR_WIDTH = 420

BOARD_OFFSET_X = 20
BOARD_OFFSET_Y = HUD_HEIGHT

WIDTH = BOARD_SIZE + SIDEBAR_WIDTH + BOARD_OFFSET_X
HEIGHT = BOARD_SIZE + (HUD_HEIGHT * 2)

# ==========================
# Board
# ==========================

ROWS = 8
COLS = 8

SQSIZE = BOARD_SIZE // COLS

# ==========================
# Colours
# ==========================

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

LIGHT = (238, 238, 210)
DARK = (118, 150, 86)

BG = (28, 35, 30)
SIDEBAR = (38, 48, 38)

YELLOW = (245, 245, 80)
GREEN = (170, 200, 40)
