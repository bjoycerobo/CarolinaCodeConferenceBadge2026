"""
Robojuice conference badge
==========================

Hold SW1 + SW2 + SW3 to open the badge menu.

Menu controls:
SW1  -- up
SW2  -- select
SW3  -- down

Game controls:
SW1  -- move right
SW2  -- quit; double-tap changes Pong computer mode
SW3  -- move left

In Flappy, SW1 or SW3 flaps and SW2 quits.

Hold all three switches inside any game to return to the menu.

The original sample launcher remains at samples/Launcher/code.py.
"""

# Keep the LCD dark while CircuitPython imports the display libraries.
import board
import digitalio

backlight = digitalio.DigitalInOut(board.IO5)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = False

import time
import math
import random
import gc
import busio
import displayio
import fourwire
import terminalio
import neopixel
import adafruit_imageload
import adafruit_st7735r
from adafruit_display_text import label


WIDTH = 128
HEIGHT = 160
MENU_HOLD_SECONDS = 0.35
DOUBLE_TAP_SECONDS = 0.4

HOME = 0
INFO = 1
QR = 2
CONFERENCE = 3
LINKEDIN = 4


# Hardware ---------------------------------------------------------
pixels = neopixel.NeoPixel(board.IO4, 5, brightness=0.08, auto_write=False)
pixels.fill((0, 0, 0))
pixels.show()


def button(pin):
    switch = digitalio.DigitalInOut(pin)
    switch.switch_to_input(pull=digitalio.Pull.UP)
    return switch


sw1 = button(board.IO1)
sw2 = button(board.IO2)
sw3 = button(board.IO43)

# Keep the optional font chip off the shared SPI bus.
font_cs = digitalio.DigitalInOut(board.IO9)
font_cs.direction = digitalio.Direction.OUTPUT
font_cs.value = True

displayio.release_displays()
spi = busio.SPI(clock=board.IO12, MOSI=board.IO11)
display_bus = fourwire.FourWire(
    spi, command=board.IO6, chip_select=board.IO10, reset=board.IO7,
    baudrate=8_000_000,
)
display = adafruit_st7735r.ST7735R(
    display_bus, width=WIDTH, height=HEIGHT, rotation=0, bgr=True,
    auto_refresh=False,
)


# Display helpers --------------------------------------------------
def background(color=0x000010):
    bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
    palette = displayio.Palette(1)
    palette[0] = color
    return displayio.TileGrid(bitmap, pixel_shader=palette)


def centered(text, y, color=0xFFFFFF, scale=1):
    return centered_on(text, WIDTH // 2, y, color, scale)


def centered_on(text, x, y, color=0xFFFFFF, scale=1):
    item = label.Label(terminalio.FONT, text=text, color=color, scale=scale)
    item.anchor_point = (0.5, 0.5)
    item.anchored_position = (x, y)
    return item


def load_image(path):
    return adafruit_imageload.load(
        path, bitmap=displayio.Bitmap, palette=displayio.Palette,
    )


def image_tile(bitmap, palette, x, y):
    tile = displayio.TileGrid(bitmap, pixel_shader=palette)
    tile.x = x
    tile.y = y
    return tile


logo_bitmap, logo_palette = load_image("/img/RobojuiceLogo.bmp")
qr_bitmap, qr_palette = load_image("/img/RobojuiceQR.bmp")
linkedin_bitmap, linkedin_palette = load_image("/img/LinkedInQR.bmp")
ccc_bitmap, ccc_palette = load_image("/img/CarolinaCodeConference Logo.bmp")


def home_screen():
    group = displayio.Group()
    group.append(background())
    group.append(centered("CUSTOM SOFTWARE +", 16, 0x00FFFF))
    group.append(centered("PRACTICAL AI", 28, 0x00FFFF))
    group.append(image_tile(logo_bitmap, logo_palette, 6, 53))
    group.append(centered("GIVE YOUR TEAM", 104, 0xFFFFFF, 2))
    group.append(centered("BETTER SYSTEMS", 124, 0xFFFFFF, 2))
    group.append(centered("HOLD 1+2+3: MENU", 151, 0x808080))
    return group


def info_screen():
    group = displayio.Group()
    group.append(background())
    group.append(image_tile(logo_bitmap, logo_palette, 6, 12))
    group.append(centered("GIVE YOUR TEAM", 57, 0x00FFFF, 2))
    group.append(centered("BETTER SYSTEMS", 78, 0x00FFFF, 2))
    group.append(centered("BRANDON JOYCE", 108, 0xFFFFFF, 2))
    group.append(centered("SENIOR DEVELOPER", 125, 0xFFB000))
    group.append(centered("HOLD 1+2+3: MENU", 151, 0x808080))
    return group


def qr_screen():
    group = displayio.Group()
    group.append(background(0x000000))
    group.append(image_tile(qr_bitmap, qr_palette, 0, 8))
    group.append(centered("SCAN FOR ROBOJUICE.COM", 151, 0xFFFFFF))
    return group


def conference_screen():
    group = displayio.Group()
    group.append(background(0x000000))
    group.append(image_tile(ccc_bitmap, ccc_palette, 0, 0))
    group.append(centered("HOLD 1+2+3: MENU", 151, 0x808080))
    return group


def linkedin_screen():
    group = displayio.Group()
    group.append(background(0xFFFFFF))
    group.append(centered("CONNECT ON LINKEDIN", 10, 0x0A66C2))
    group.append(image_tile(linkedin_bitmap, linkedin_palette, 8, 22))
    group.append(centered("linkedin.com/in/", 143, 0x202020))
    group.append(centered("brandonwjoyce", 154, 0x202020))
    return group


screens = (
    home_screen(), info_screen(), qr_screen(), conference_screen(),
    linkedin_screen(),
)


MENU_ITEMS = (
    "CCC DEFAULT",
    "ROBOJUICE BADGE",
    "ROBOJUICE QR",
    "LINKEDIN QR",
    "PONG",
    "BREAKOUT",
    "FLAPPY",
    "BADGE BLASTER",
    "BYTE DROP",
)


def build_menu():
    group = displayio.Group()
    group.append(background(0x000010))
    group.append(centered("BADGE MENU", 10, 0x00FFFF, 2))
    labels = []
    for index, name in enumerate(MENU_ITEMS):
        item = centered(name, 26 + index * 13, 0x708090)
        group.append(item)
        labels.append(item)
    group.append(centered("1 UP   2 OK   3 DOWN", 151, 0x607080))
    return group, labels


menu_scene, menu_labels = build_menu()


# Interaction ------------------------------------------------------
def show_screen(index):
    display.root_group = screens[index]
    display.refresh()


def solid_tile(width, height, color, x=0, y=0):
    bitmap = displayio.Bitmap(width, height, 1)
    palette = displayio.Palette(1)
    palette[0] = color
    return displayio.TileGrid(
        bitmap, pixel_shader=palette, x=x, y=y,
    )


def wait_for_buttons_released():
    while not (sw1.value and sw2.value and sw3.value):
        time.sleep(0.02)


def all_buttons_pressed():
    return not sw1.value and not sw2.value and not sw3.value


def update_menu_hold(started_at):
    """Return the all-button hold start time, or -1 when it has matured."""
    if all_buttons_pressed():
        now = time.monotonic()
        if started_at is None:
            return now
        if now - started_at >= MENU_HOLD_SECONDS:
            return -1
        return started_at
    return None


def interruptible_wait(seconds):
    """Wait for a duration; return True if the menu chord is held."""
    deadline = time.monotonic() + seconds
    menu_hold_started = None
    while time.monotonic() < deadline:
        menu_hold_started = update_menu_hold(menu_hold_started)
        if menu_hold_started == -1:
            return True
        time.sleep(0.02)
    return False


def wait_for_game_buttons_released():
    """Wait out menu-selection input while still honoring the menu chord."""
    menu_hold_started = None
    while not (sw1.value and sw2.value and sw3.value):
        menu_hold_started = update_menu_hold(menu_hold_started)
        if menu_hold_started == -1:
            return True
        time.sleep(0.02)
    return False


def choose_menu_item(selected):
    display.rotation = 0
    display.root_group = menu_scene

    def highlight():
        for index, item in enumerate(menu_labels):
            item.color = 0xFFFF00 if index == selected else 0x708090
        display.refresh()

    wait_for_buttons_released()
    highlight()
    previous_values = (True, True, True)

    while True:
        values = (sw1.value, sw2.value, sw3.value)
        pressed1 = not values[0] and previous_values[0]
        pressed2 = not values[1] and previous_values[1]
        pressed3 = not values[2] and previous_values[2]
        previous_values = values

        if pressed1:
            selected = (selected - 1) % len(MENU_ITEMS)
            highlight()
            time.sleep(0.12)
        elif pressed3:
            selected = (selected + 1) % len(MENU_ITEMS)
            highlight()
            time.sleep(0.12)
        elif pressed2:
            wait_for_buttons_released()
            return selected
        time.sleep(0.02)


def play_pong():
    """Run one-player Pong until SW2 is pressed.

    The fixed-rate loop and automated-paddle pattern are adapted from
    FoamyGuy's MIT-licensed CircuitPython Badge Reverse Pong Game:
    https://github.com/FoamyGuy/CircuitPython-Badge-Reverse-Pong-Game
    """
    game_width = 160
    game_height = 128
    paddle_width = 32
    paddle_height = 4
    ball_size = 4
    player_y = game_height - 8
    computer_y = 4
    winning_score = 5
    frame_seconds = 1.0 / 30.0

    scene = displayio.Group()
    scene.append(solid_tile(game_width, game_height, 0x000010))

    # A simple dotted center line keeps the screen recognizably Pong-like.
    for x in range(2, game_width, 8):
        scene.append(solid_tile(4, 1, 0x304050, x=x, y=game_height // 2))

    player = solid_tile(paddle_width, paddle_height, 0x00D8FF)
    computer = solid_tile(paddle_width, paddle_height, 0xFFB000)
    ball = solid_tile(ball_size, ball_size, 0xFFFFFF)
    scene.append(player)
    scene.append(computer)
    scene.append(ball)

    mode_label = centered_on("CPU: FOLLOW", game_width // 2, 18, 0xFFB000)
    score = centered_on("CPU 0  YOU 0", game_width // 2, 54, 0xFFFFFF)
    message = centered_on("", game_width // 2, 74, 0xFFFFFF)
    hint = centered_on("S3<             >S1", game_width // 2, 88, 0x607080)
    mode_hint = centered_on("S2 TAP QUIT / 2X MODE", game_width // 2, 100, 0x607080)
    scene.append(mode_label)
    scene.append(score)
    scene.append(message)
    scene.append(hint)
    scene.append(mode_hint)

    display.rotation = 90
    display.root_group = scene
    pixels.fill((0, 0, 0))
    pixels.show()

    # Do not treat the menu selection press as game input.
    if wait_for_game_buttons_released():
        display.rotation = 0
        return

    player_x = (game_width - paddle_width) / 2
    computer_x = (game_width - paddle_width) / 2
    player_score = 0
    computer_score = 0
    serve_direction = 1

    def countdown(text="GET READY"):
        message.text = text
        display.refresh()
        if interruptible_wait(0.6):
            return True
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            if interruptible_wait(1.0):
                return True
        message.text = ""
        display.refresh()
        return False

    def reset_ball(direction):
        ball_x = (game_width - ball_size) / 2
        ball_y = (game_height - ball_size) / 2
        ball_vx = 72.0 * direction
        ball_vy = -48.0 if (player_score + computer_score) % 2 else 48.0
        return ball_x, ball_y, ball_vx, ball_vy

    if countdown():
        display.rotation = 0
        return
    ball_x, ball_y, ball_vx, ball_vy = reset_ball(serve_direction)
    last_frame = time.monotonic()
    computer_update = 0
    computer_follows_ball = True
    computer_going_left = True
    previous_sw2 = True
    pending_quit_at = None
    menu_hold_started = None

    while True:
        now = time.monotonic()
        if now - last_frame < frame_seconds:
            time.sleep(0.003)
            continue
        dt = now - last_frame
        if dt > 0.08:
            dt = 0.08
        last_frame = now

        menu_hold_started = update_menu_hold(menu_hold_started)
        if menu_hold_started == -1:
            display.rotation = 0
            return

        sw2_value = sw2.value
        sw2_pressed = (
            not all_buttons_pressed()
            and not sw2_value
            and previous_sw2
        )
        previous_sw2 = sw2_value

        # A single tap quits after the double-tap window. A second tap in
        # that window toggles between following the ball and the upstream
        # AutoPaddle-style steady back-and-forth movement.
        if pending_quit_at is not None and now > pending_quit_at:
            display.rotation = 0
            return
        if sw2_pressed:
            if pending_quit_at is not None:
                pending_quit_at = None
                computer_follows_ball = not computer_follows_ball
                if computer_follows_ball:
                    mode_label.text = "CPU: FOLLOW"
                else:
                    mode_label.text = "CPU: SWEEP"
            else:
                pending_quit_at = now + DOUBLE_TAP_SECONDS

        # Holding both movement buttons leaves the player's paddle still.
        if not sw1.value and sw3.value:
            player_x += 105.0 * dt
        elif not sw3.value and sw1.value:
            player_x -= 105.0 * dt
        if player_x < 0:
            player_x = 0
        elif player_x > game_width - paddle_width:
            player_x = game_width - paddle_width

        # Automated paddle adapted from the upstream AutoPaddle update pattern.
        if computer_follows_ball:
            # Updating less often and limiting speed keeps FOLLOW beatable.
            computer_update += 1
            if computer_update >= 3:
                target = ball_x + ball_size / 2
                center = computer_x + paddle_width / 2
                step = 3.0
                if target < center - 3:
                    computer_x -= step
                elif target > center + 3:
                    computer_x += step
                computer_update = 0
        else:
            # This mirrors the original AutoPaddle: move steadily until an
            # edge is reached, reverse direction, and repeat.
            if computer_going_left:
                computer_x -= 1
            else:
                computer_x += 1
            if computer_x <= 0:
                computer_going_left = False
            elif computer_x >= game_width - paddle_width:
                computer_going_left = True
        if computer_x < 0:
            computer_x = 0
        elif computer_x > game_width - paddle_width:
            computer_x = game_width - paddle_width

        ball_x += ball_vx * dt
        ball_y += ball_vy * dt

        if ball_x <= 0:
            ball_x = 0
            ball_vx = abs(ball_vx)
        elif ball_x >= game_width - ball_size:
            ball_x = game_width - ball_size
            ball_vx = -abs(ball_vx)

        if (
            ball_vy > 0
            and ball_y + ball_size >= player_y
            and ball_y <= player_y + paddle_height
            and ball_x + ball_size >= player_x
            and ball_x <= player_x + paddle_width
        ):
            ball_y = player_y - ball_size
            offset = (
                (ball_x + ball_size / 2)
                - (player_x + paddle_width / 2)
            ) / (paddle_width / 2)
            ball_vy = -abs(ball_vy) * 1.03
            ball_vx += offset * 28.0
        elif (
            ball_vy < 0
            and ball_y <= computer_y + paddle_height
            and ball_y + ball_size >= computer_y
            and ball_x + ball_size >= computer_x
            and ball_x <= computer_x + paddle_width
        ):
            ball_y = computer_y + paddle_height
            ball_vy = abs(ball_vy) * 1.03

        point_scored = False
        if ball_y < -ball_size:
            player_score += 1
            serve_direction = -1
            point_scored = True
        elif ball_y > game_height:
            computer_score += 1
            serve_direction = 1
            point_scored = True

        if point_scored:
            score.text = "CPU %d  YOU %d" % (computer_score, player_score)
            if player_score >= winning_score or computer_score >= winning_score:
                if player_score >= winning_score:
                    result = "YOU WIN!"
                    pixels.fill((0, 40, 12))
                else:
                    result = "COMPUTER WINS"
                    pixels.fill((40, 5, 0))
                pixels.show()
                if countdown(result):
                    display.rotation = 0
                    return
                pixels.fill((0, 0, 0))
                pixels.show()
                player_score = 0
                computer_score = 0
                score.text = "CPU 0  YOU 0"
            ball_x, ball_y, ball_vx, ball_vy = reset_ball(serve_direction)
            if interruptible_wait(0.5):
                display.rotation = 0
                return
            last_frame = time.monotonic()

        player.x = int(player_x)
        player.y = player_y
        computer.x = int(computer_x)
        computer.y = computer_y
        ball.x = int(ball_x)
        ball.y = int(ball_y)
        display.refresh()


def play_breakout():
    """Run Breakout until SW2 is pressed.

    Gameplay adapted from Adafruit's MIT-licensed CircuitPython Breakout:
    Copyright (c) 2025 Anne Barela for Adafruit Industries
    https://learn.adafruit.com/breakout-game-on-metro-rp2350-and-fruit-jam
    """
    game_width = 160
    game_height = 128
    paddle_width = 32
    paddle_height = 4
    paddle_y = 119
    ball_size = 4
    frame_seconds = 1.0 / 30.0
    starting_lives = 3

    scene = displayio.Group()
    scene.append(solid_tile(game_width, game_height, 0x000010))

    status = centered_on("LIVES 3   BRICKS 40", game_width // 2, 8, 0xFFFFFF)
    message = centered_on("", game_width // 2, 67, 0xFFFFFF)
    hint = centered_on("S3<     S2 QUIT     >S1", game_width // 2, 108, 0x607080)
    scene.append(status)
    scene.append(message)
    scene.append(hint)

    paddle = solid_tile(paddle_width, paddle_height, 0x00D8FF)
    ball = solid_tile(ball_size, ball_size, 0xFFFFFF)
    paddle.x = (game_width - paddle_width) // 2
    paddle.y = paddle_y
    ball.x = (game_width - ball_size) // 2
    ball.y = paddle_y - 18
    scene.append(paddle)
    scene.append(ball)

    brick_width = 13
    brick_height = 6
    brick_gap = 2
    brick_colors = (0xFF4050, 0xFF9A30, 0xFFE040, 0x40D878)
    brick_bitmap = displayio.Bitmap(brick_width, brick_height, 1)
    brick_palettes = []
    for color in brick_colors:
        palette = displayio.Palette(1)
        palette[0] = color
        brick_palettes.append(palette)

    bricks = []
    for row in range(4):
        for column in range(10):
            brick_x = 6 + column * (brick_width + brick_gap)
            brick_y = 20 + row * (brick_height + brick_gap)
            tile = displayio.TileGrid(
                brick_bitmap,
                pixel_shader=brick_palettes[row],
                x=brick_x,
                y=brick_y,
            )
            scene.append(tile)
            bricks.append([tile, brick_x, brick_y, True])

    display.rotation = 90
    display.root_group = scene
    pixels.fill((0, 0, 0))
    pixels.show()

    # Do not treat the menu selection press as game input.
    if wait_for_game_buttons_released():
        display.rotation = 0
        return

    def countdown(text="BREAKOUT"):
        message.text = text
        display.refresh()
        if interruptible_wait(0.6):
            return True
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            if interruptible_wait(1.0):
                return True
        message.text = ""
        return False

    def reset_bricks():
        for brick in bricks:
            brick[0].hidden = False
            brick[3] = True

    def reset_ball():
        return (
            (game_width - ball_size) / 2,
            paddle_y - 18.0,
            62.0,
            -68.0,
        )

    paddle_x = (game_width - paddle_width) / 2
    lives = starting_lives
    bricks_left = len(bricks)
    if countdown():
        display.rotation = 0
        return
    ball_x, ball_y, ball_vx, ball_vy = reset_ball()
    last_frame = time.monotonic()
    menu_hold_started = None

    while True:
        now = time.monotonic()
        if now - last_frame < frame_seconds:
            time.sleep(0.003)
            continue
        dt = now - last_frame
        if dt > 0.08:
            dt = 0.08
        last_frame = now

        menu_hold_started = update_menu_hold(menu_hold_started)
        if menu_hold_started == -1:
            display.rotation = 0
            return

        if not sw2.value and not all_buttons_pressed():
            display.rotation = 0
            return

        if not sw1.value and sw3.value:
            paddle_x += 105.0 * dt
        elif not sw3.value and sw1.value:
            paddle_x -= 105.0 * dt
        if paddle_x < 0:
            paddle_x = 0
        elif paddle_x > game_width - paddle_width:
            paddle_x = game_width - paddle_width

        previous_ball_x = ball_x
        ball_x += ball_vx * dt
        ball_y += ball_vy * dt

        if ball_x <= 0:
            ball_x = 0
            ball_vx = abs(ball_vx)
        elif ball_x >= game_width - ball_size:
            ball_x = game_width - ball_size
            ball_vx = -abs(ball_vx)
        if ball_y <= 15:
            ball_y = 15
            ball_vy = abs(ball_vy)

        if (
            ball_vy > 0
            and ball_y + ball_size >= paddle_y
            and ball_y <= paddle_y + paddle_height
            and ball_x + ball_size >= paddle_x
            and ball_x <= paddle_x + paddle_width
        ):
            ball_y = paddle_y - ball_size
            offset = (
                (ball_x + ball_size / 2)
                - (paddle_x + paddle_width / 2)
            ) / (paddle_width / 2)
            ball_vy = -abs(ball_vy)
            ball_vx += offset * 24.0
            if ball_vx > 105.0:
                ball_vx = 105.0
            elif ball_vx < -105.0:
                ball_vx = -105.0

        for brick in bricks:
            if not brick[3]:
                continue
            brick_x = brick[1]
            brick_y = brick[2]
            if (
                ball_x + ball_size >= brick_x
                and ball_x <= brick_x + brick_width
                and ball_y + ball_size >= brick_y
                and ball_y <= brick_y + brick_height
            ):
                brick[3] = False
                brick[0].hidden = True
                bricks_left -= 1
                status.text = "LIVES %d   BRICKS %d" % (lives, bricks_left)

                came_from_side = (
                    previous_ball_x + ball_size <= brick_x
                    or previous_ball_x >= brick_x + brick_width
                )
                if came_from_side:
                    ball_vx = -ball_vx
                else:
                    ball_vy = -ball_vy
                break

        if ball_y > game_height:
            lives -= 1
            if lives > 0:
                message.text = "BALL LOST"
                status.text = "LIVES %d   BRICKS %d" % (lives, bricks_left)
                display.refresh()
                if interruptible_wait(1.0):
                    display.rotation = 0
                    return
                message.text = ""
                ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                last_frame = time.monotonic()
            else:
                pixels.fill((40, 5, 0))
                pixels.show()
                if countdown("GAME OVER"):
                    display.rotation = 0
                    return
                pixels.fill((0, 0, 0))
                pixels.show()
                lives = starting_lives
                bricks_left = len(bricks)
                reset_bricks()
                status.text = "LIVES 3   BRICKS 40"
                ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                last_frame = time.monotonic()
        elif bricks_left == 0:
            pixels.fill((0, 40, 12))
            pixels.show()
            if countdown("YOU WIN!"):
                display.rotation = 0
                return
            pixels.fill((0, 0, 0))
            pixels.show()
            lives = starting_lives
            bricks_left = len(bricks)
            reset_bricks()
            status.text = "LIVES 3   BRICKS 40"
            ball_x, ball_y, ball_vx, ball_vy = reset_ball()
            last_frame = time.monotonic()

        paddle.x = int(paddle_x)
        paddle.y = paddle_y
        ball.x = int(ball_x)
        ball.y = int(ball_y)
        display.refresh()


# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# FlappyBird type game adapted from Adafruit's TrelliBird.
#
# Adafruit invests time and resources providing this open source code.
# Please support Adafruit and open source hardware by purchasing
# products from Adafruit!
#
# Written by Dave Astels for Adafruit Industries
# Copyright (c) 2018 Adafruit Industries
# Licensed under the MIT license.
#
# All text above must be included in any redistribution.
# https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/TrelliBird
def play_flappy():
    """Run a FlappyBird-style game until SW2 is pressed."""
    game_width = 160
    game_height = 128
    ceiling_y = 15
    ground_y = 117
    bird_x = 32
    bird_width = 7
    bird_height = 6
    pipe_width = 14
    pipe_gap = 42
    pipe_spacing = 90
    frame_seconds = 1.0 / 30.0

    scene = displayio.Group()
    scene.append(solid_tile(game_width, game_height, 0x082040))
    scene.append(solid_tile(game_width, 11, 0x183008, y=ground_y))

    score_label = centered_on("SCORE 0", game_width // 2, 8, 0xFFFFFF)
    message = centered_on("", game_width // 2, 64, 0xFFFFFF, 2)
    hint = centered_on("S1/S3 FLAP   S2 QUIT", game_width // 2, 123, 0xA0C080)
    scene.append(score_label)
    scene.append(message)
    scene.append(hint)

    bird = solid_tile(bird_width, bird_height, 0xFFE040, bird_x, 58)
    scene.append(bird)

    pipe_bitmap = displayio.Bitmap(pipe_width, game_height, 1)
    pipe_palette = displayio.Palette(1)
    pipe_palette[0] = 0x30C860
    pipes = []
    for index in range(2):
        top = displayio.TileGrid(pipe_bitmap, pixel_shader=pipe_palette)
        bottom = displayio.TileGrid(pipe_bitmap, pixel_shader=pipe_palette)
        scene.append(top)
        scene.append(bottom)
        pipes.append([top, bottom, game_width + index * pipe_spacing, 64, False])

    display.rotation = 90
    display.root_group = scene
    pixels.fill((0, 0, 0))
    pixels.show()
    if wait_for_game_buttons_released():
        display.rotation = 0
        return

    def position_pipe(pipe, x_position):
        gap_center = random.randint(42, 90)
        pipe[2] = x_position
        pipe[3] = gap_center
        pipe[4] = False
        gap_top = gap_center - pipe_gap // 2
        gap_bottom = gap_center + pipe_gap // 2
        pipe[0].x = int(x_position)
        pipe[0].y = gap_top - game_height
        pipe[1].x = int(x_position)
        pipe[1].y = gap_bottom

    def countdown(text):
        message.text = text
        display.refresh()
        if interruptible_wait(0.6):
            return True
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            if interruptible_wait(1.0):
                return True
        message.text = ""
        return False

    while True:
        bird_y = 56.0
        bird_velocity = 0.0
        score = 0
        score_label.text = "SCORE 0"
        position_pipe(pipes[0], game_width + 20)
        position_pipe(pipes[1], game_width + 20 + pipe_spacing)
        bird.y = int(bird_y)
        if countdown("FLAPPY"):
            display.rotation = 0
            return
        last_frame = time.monotonic()
        previous_values = (True, True, True)
        collided = False
        menu_hold_started = None

        while not collided:
            now = time.monotonic()
            if now - last_frame < frame_seconds:
                time.sleep(0.003)
                continue
            dt = now - last_frame
            if dt > 0.08:
                dt = 0.08
            last_frame = now

            values = (sw1.value, sw2.value, sw3.value)
            pressed1 = not values[0] and previous_values[0]
            pressed2 = not values[1] and previous_values[1]
            pressed3 = not values[2] and previous_values[2]
            previous_values = values

            menu_hold_started = update_menu_hold(menu_hold_started)
            if menu_hold_started == -1:
                display.rotation = 0
                return
            if all_buttons_pressed():
                display.refresh()
                continue

            if pressed2:
                display.rotation = 0
                return
            if pressed1 or pressed3:
                bird_velocity = -72.0

            bird_velocity += 150.0 * dt
            bird_y += bird_velocity * dt
            bird.y = int(bird_y)

            pipe_speed = 48.0 + min(score * 1.5, 24.0)
            rightmost = max(pipes[0][2], pipes[1][2])
            for pipe in pipes:
                pipe[2] -= pipe_speed * dt
                if pipe[2] + pipe_width < 0:
                    position_pipe(pipe, rightmost + pipe_spacing)
                    rightmost = pipe[2]
                else:
                    pipe[0].x = int(pipe[2])
                    pipe[1].x = int(pipe[2])

                if not pipe[4] and pipe[2] + pipe_width < bird_x:
                    pipe[4] = True
                    score += 1
                    score_label.text = "SCORE %d" % score

                overlaps_pipe = (
                    bird_x + bird_width >= pipe[2]
                    and bird_x <= pipe[2] + pipe_width
                )
                if overlaps_pipe:
                    gap_top = pipe[3] - pipe_gap // 2
                    gap_bottom = pipe[3] + pipe_gap // 2
                    if bird_y <= gap_top or bird_y + bird_height >= gap_bottom:
                        collided = True

            if bird_y <= ceiling_y or bird_y + bird_height >= ground_y:
                collided = True

            display.refresh()

        pixels.fill((40, 5, 0))
        pixels.show()
        message.text = "GAME OVER"
        display.refresh()
        if interruptible_wait(1.0):
            display.rotation = 0
            return
        pixels.fill((0, 0, 0))
        pixels.show()
        if countdown("SCORE %d" % score):
            display.rotation = 0
            return


# SPDX-FileCopyrightText: 2018 Radomir Dopieralski
# SPDX-License-Identifier: MIT
#
# Badge Blaster is an original displayio adaptation of the fixed-shooter
# structure demonstrated by Radomir Dopieralski's MIT-licensed Vacuum Invaders:
# https://github.com/python-ugame/vacuum-invaders
def play_badge_blaster():
    """Defend the badge from descending corrupted data packets."""
    game_width = 160
    game_height = 128
    ship_width = 20
    ship_height = 5
    ship_y = 108
    frame_seconds = 1.0 / 30.0

    scene = displayio.Group()
    scene.append(solid_tile(game_width, game_height, 0x000010))

    status = centered_on("SCORE 0   LIVES 3", game_width // 2, 8, 0xFFFFFF)
    message = centered_on("", game_width // 2, 65, 0xFFFFFF, 2)
    hint = centered_on("S3<  S2 FIRE/3X  >S1", game_width // 2, 122, 0x607080)
    scene.append(status)
    scene.append(message)
    scene.append(hint)

    ship = solid_tile(ship_width, ship_height, 0x00D8FF)
    ship_tip = solid_tile(4, 4, 0xFFFFFF)
    scene.append(ship)
    scene.append(ship_tip)

    bug_bitmap = displayio.Bitmap(8, 6, 2)
    bug_palette = displayio.Palette(2)
    bug_palette[0] = 0x000010
    bug_palette[1] = 0x70F0A0
    for bug_x, bug_y in (
        (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
        (0, 1), (4, 1), (6, 1), (7, 1),
        (0, 2), (2, 2), (4, 2), (6, 2),
        (0, 3), (3, 3), (4, 3), (7, 3),
        (0, 4), (4, 4), (6, 4),
        (0, 5), (1, 5), (2, 5), (3, 5),
        (4, 5), (5, 5), (6, 5), (7, 5),
    ):
        bug_bitmap[bug_x, bug_y] = 1

    enemies = []
    for row in range(2):
        for column in range(6):
            bug = displayio.TileGrid(bug_bitmap, pixel_shader=bug_palette)
            scene.append(bug)
            enemies.append([
                bug,
                13 + column * 24 + (row % 2) * 6,
                24 + row * 15,
                True,
            ])

    shot_bitmap = displayio.Bitmap(2, 6, 1)
    shot_palette = displayio.Palette(1)
    shot_palette[0] = 0xFFFFFF
    shots = []
    for _ in range(3):
        shot = displayio.TileGrid(shot_bitmap, pixel_shader=shot_palette)
        shot.hidden = True
        scene.append(shot)
        shots.append(shot)

    bolt_bitmap = displayio.Bitmap(2, 5, 1)
    bolt_palette = displayio.Palette(1)
    bolt_palette[0] = 0xFF7040
    bolts = []
    for _ in range(3):
        bolt = displayio.TileGrid(bolt_bitmap, pixel_shader=bolt_palette)
        bolt.hidden = True
        scene.append(bolt)
        bolts.append(bolt)

    display.rotation = 90
    display.root_group = scene
    pixels.fill((0, 0, 0))
    pixels.show()
    if wait_for_game_buttons_released():
        display.rotation = 0
        return

    def countdown(text):
        message.text = text
        display.refresh()
        if interruptible_wait(0.6):
            return True
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            if interruptible_wait(1.0):
                return True
        message.text = ""
        return False

    def hide_projectiles():
        for projectile in shots:
            projectile.hidden = True
        for projectile in bolts:
            projectile.hidden = True

    def reset_wave():
        for index, enemy in enumerate(enemies):
            row = index // 6
            column = index % 6
            enemy[1] = 13 + column * 24 + (row % 2) * 6
            enemy[2] = 24 + row * 15
            enemy[3] = True
            enemy[0].hidden = False
            enemy[0].x = enemy[1]
            enemy[0].y = enemy[2]

    ship_x = (game_width - ship_width) / 2
    score_value = 0
    lives = 3
    wave = 1
    group_x = 0.0
    group_y = 0.0
    enemy_direction = 1
    next_bolt_at = time.monotonic() + 1.2
    previous_values = (True, True, True)
    last_s2_tap = None
    s2_tap_count = 0
    menu_hold_started = None
    reset_wave()
    if countdown("BADGE BLASTER"):
        display.rotation = 0
        return
    last_frame = time.monotonic()

    while True:
        now = time.monotonic()
        if now - last_frame < frame_seconds:
            time.sleep(0.003)
            continue
        dt = now - last_frame
        if dt > 0.08:
            dt = 0.08
        last_frame = now

        values = (sw1.value, sw2.value, sw3.value)
        pressed2 = not values[1] and previous_values[1]
        previous_values = values

        menu_hold_started = update_menu_hold(menu_hold_started)
        if menu_hold_started == -1:
            display.rotation = 0
            return
        chord_down = all_buttons_pressed()

        if not chord_down:
            if not sw1.value and sw3.value:
                ship_x += 110.0 * dt
            elif not sw3.value and sw1.value:
                ship_x -= 110.0 * dt

            if pressed2:
                if last_s2_tap is not None and now - last_s2_tap <= 0.55:
                    s2_tap_count += 1
                else:
                    s2_tap_count = 1
                last_s2_tap = now
                if s2_tap_count >= 3:
                    display.rotation = 0
                    return
                for shot in shots:
                    if shot.hidden:
                        shot.x = int(ship_x + ship_width / 2 - 1)
                        shot.y = ship_y - 6
                        shot.hidden = False
                        break

        if ship_x < 0:
            ship_x = 0
        elif ship_x > game_width - ship_width:
            ship_x = game_width - ship_width
        ship.x = int(ship_x)
        ship.y = ship_y
        ship_tip.x = int(ship_x + ship_width / 2 - 2)
        ship_tip.y = ship_y - 4

        live_count = 0
        left_edge = game_width
        right_edge = 0
        for enemy in enemies:
            if not enemy[3]:
                continue
            live_count += 1
            enemy_left = enemy[1] + group_x
            enemy_right = enemy_left + 8
            if enemy_left < left_edge:
                left_edge = enemy_left
            if enemy_right > right_edge:
                right_edge = enemy_right
        if live_count:
            enemy_speed = 22.0 + wave * 3.0
            next_group_x = group_x + enemy_direction * enemy_speed * dt
            if (
                enemy_direction < 0 and left_edge + enemy_direction * enemy_speed * dt <= 2
            ) or (
                enemy_direction > 0 and right_edge + enemy_direction * enemy_speed * dt >= game_width - 2
            ):
                enemy_direction = -enemy_direction
                group_y += 7
            else:
                group_x = next_group_x

        reached_ship = False
        for enemy in enemies:
            if not enemy[3]:
                continue
            enemy[0].x = int(enemy[1] + group_x)
            enemy[0].y = int(enemy[2] + group_y)
            if enemy[0].y + 6 >= ship_y:
                reached_ship = True

        for shot in shots:
            if shot.hidden:
                continue
            shot.y -= max(1, int(145.0 * dt))
            if shot.y < 12:
                shot.hidden = True
                continue
            for enemy in enemies:
                if not enemy[3]:
                    continue
                enemy_x = enemy[1] + group_x
                enemy_y = enemy[2] + group_y
                if (
                    enemy[3]
                    and shot.x + 2 >= enemy_x
                    and shot.x <= enemy_x + 8
                    and shot.y + 6 >= enemy_y
                    and shot.y <= enemy_y + 6
                ):
                    enemy[3] = False
                    enemy[0].hidden = True
                    shot.hidden = True
                    live_count -= 1
                    score_value += 25
                    status.text = "SCORE %d   LIVES %d" % (score_value, lives)
                    break

        if now >= next_bolt_at and live_count:
            free_bolt = None
            for bolt in bolts:
                if bolt.hidden:
                    free_bolt = bolt
                    break
            if free_bolt is not None:
                target_number = random.randint(0, live_count - 1)
                source = None
                for enemy in enemies:
                    if not enemy[3]:
                        continue
                    if target_number == 0:
                        source = enemy
                        break
                    target_number -= 1
                if source is not None:
                    free_bolt.x = int(source[1] + group_x + 3)
                    free_bolt.y = int(source[2] + group_y + 6)
                    free_bolt.hidden = False
            next_bolt_at = now + max(0.45, 1.1 - wave * 0.08)

        player_hit = reached_ship
        for bolt in bolts:
            if bolt.hidden:
                continue
            bolt.y += max(1, int((70.0 + wave * 4.0) * dt))
            if bolt.y > game_height:
                bolt.hidden = True
            elif (
                bolt.x + 2 >= ship_x
                and bolt.x <= ship_x + ship_width
                and bolt.y + 5 >= ship_y - 4
                and bolt.y <= ship_y + ship_height
            ):
                bolt.hidden = True
                player_hit = True

        if player_hit:
            lives -= 1
            status.text = "SCORE %d   LIVES %d" % (score_value, lives)
            pixels.fill((40, 5, 0))
            pixels.show()
            message.text = "SHIP HIT"
            display.refresh()
            if interruptible_wait(0.8):
                display.rotation = 0
                return
            pixels.fill((0, 0, 0))
            pixels.show()
            hide_projectiles()
            group_x = 0.0
            group_y = 0.0
            reset_wave()
            if lives <= 0:
                if countdown("GAME OVER"):
                    display.rotation = 0
                    return
                lives = 3
                score_value = 0
                wave = 1
                status.text = "SCORE 0   LIVES 3"
            message.text = ""
            last_frame = time.monotonic()
        elif live_count == 0:
            wave += 1
            score_value += 100
            status.text = "SCORE %d   LIVES %d" % (score_value, lives)
            hide_projectiles()
            group_x = 0.0
            group_y = 0.0
            reset_wave()
            if countdown("WAVE %d" % wave):
                display.rotation = 0
                return
            last_frame = time.monotonic()

        display.refresh()


def play_byte_drop():
    """Run an original falling-polyomino puzzle with a compact bitmap board."""
    board_width = 9
    board_height = 14
    cell_scale = 7
    board_x = 49
    board_y = 15
    hold_seconds = 0.28
    triple_tap_seconds = 0.55

    # This intentionally differs from the familiar seven-piece set: it mixes
    # three-cell and five-cell packets on a 9 x 14 board.
    shapes = (
        ((0, 0), (1, 0), (0, 1)),
        ((0, 0), (1, 0), (2, 0)),
        ((0, 0), (1, 0), (0, 1), (1, 1), (0, 2)),
        ((0, 0), (0, 1), (1, 1), (1, 2), (2, 2)),
        ((0, 0), (1, 0), (2, 0), (1, 1), (1, 2)),
    )

    scene = displayio.Group()
    scene.append(solid_tile(160, 128, 0x000010))
    scene.append(solid_tile(
        board_width * cell_scale + 4,
        board_height * cell_scale + 4,
        0x305060,
        board_x - 2,
        board_y - 2,
    ))

    board_bitmap = displayio.Bitmap(board_width, board_height, 7)
    board_palette = displayio.Palette(7)
    board_palette[0] = 0x020812
    board_palette[1] = 0x00D8FF
    board_palette[2] = 0xFFB000
    board_palette[3] = 0x50E080
    board_palette[4] = 0xC070FF
    board_palette[5] = 0xFF5060
    board_palette[6] = 0x70A0FF
    board_tile = displayio.TileGrid(board_bitmap, pixel_shader=board_palette)
    board_group = displayio.Group(
        scale=cell_scale,
        x=board_x,
        y=board_y,
    )
    board_group.append(board_tile)
    scene.append(board_group)

    scene.append(centered_on("BYTE", 24, 34, 0x00D8FF, 2))
    scene.append(centered_on("DROP", 24, 52, 0xFFFFFF, 2))
    score_label = centered_on("SCORE", 137, 30, 0x708090)
    score_value_label = centered_on("0", 137, 45, 0xFFFFFF)
    lines_label = centered_on("ROWS 0", 137, 68, 0xFFB000)
    message = centered_on("", 80, 64, 0xFFFFFF, 2)
    hint = centered_on("S3<  S2 TURN/DROP  >S1", 80, 123, 0x607080)
    scene.append(score_label)
    scene.append(score_value_label)
    scene.append(lines_label)
    scene.append(message)
    scene.append(hint)

    display.rotation = 90
    display.root_group = scene
    pixels.fill((0, 0, 0))
    pixels.show()
    if wait_for_game_buttons_released():
        display.rotation = 0
        return

    board_state = bytearray(board_width * board_height)

    def normalize(cells):
        minimum_x = min(cell[0] for cell in cells)
        minimum_y = min(cell[1] for cell in cells)
        return tuple((cell[0] - minimum_x, cell[1] - minimum_y) for cell in cells)

    def rotated(cells):
        return normalize(tuple((-cell[1], cell[0]) for cell in cells))

    def blocked(cells, piece_x, piece_y):
        for cell_x, cell_y in cells:
            x = piece_x + cell_x
            y = piece_y + cell_y
            if x < 0 or x >= board_width or y >= board_height:
                return True
            if y >= 0 and board_state[y * board_width + x]:
                return True
        return False

    def render(cells, piece_x, piece_y, color):
        for y in range(board_height):
            for x in range(board_width):
                board_bitmap[x, y] = board_state[y * board_width + x]
        for cell_x, cell_y in cells:
            x = piece_x + cell_x
            y = piece_y + cell_y
            if 0 <= x < board_width and 0 <= y < board_height:
                board_bitmap[x, y] = color
        display.refresh()

    def clear_board():
        for index in range(len(board_state)):
            board_state[index] = 0

    def clear_full_rows():
        cleared = 0
        y = board_height - 1
        while y >= 0:
            full = True
            for x in range(board_width):
                if not board_state[y * board_width + x]:
                    full = False
                    break
            if full:
                cleared += 1
                for pull_y in range(y, 0, -1):
                    for x in range(board_width):
                        board_state[pull_y * board_width + x] = (
                            board_state[(pull_y - 1) * board_width + x]
                        )
                for x in range(board_width):
                    board_state[x] = 0
            else:
                y -= 1
        return cleared

    def new_piece():
        cells = shapes[random.randint(0, len(shapes) - 1)]
        widest = max(cell[0] for cell in cells) + 1
        return cells, (board_width - widest) // 2, 0, random.randint(1, 6)

    def countdown(text):
        message.text = text
        display.refresh()
        if interruptible_wait(0.6):
            return True
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            if interruptible_wait(1.0):
                return True
        message.text = ""
        return False

    while True:
        clear_board()
        score_value = 0
        rows_cleared = 0
        score_value_label.text = "0"
        lines_label.text = "ROWS 0"
        cells, piece_x, piece_y, piece_color = new_piece()
        render(cells, piece_x, piece_y, piece_color)
        if countdown("BYTE DROP"):
            display.rotation = 0
            return

        previous_values = (True, True, True)
        s2_pressed_at = None
        last_s2_tap = None
        s2_tap_count = 0
        menu_hold_started = None
        last_drop = time.monotonic()
        game_over = False

        while not game_over:
            now = time.monotonic()
            values = (sw1.value, sw2.value, sw3.value)
            pressed1 = not values[0] and previous_values[0]
            pressed2 = not values[1] and previous_values[1]
            pressed3 = not values[2] and previous_values[2]
            released2 = values[1] and not previous_values[1]
            previous_values = values

            menu_hold_started = update_menu_hold(menu_hold_started)
            if menu_hold_started == -1:
                display.rotation = 0
                return
            chord_down = all_buttons_pressed()
            changed = False

            if not chord_down:
                if pressed1 and not blocked(cells, piece_x + 1, piece_y):
                    piece_x += 1
                    changed = True
                elif pressed3 and not blocked(cells, piece_x - 1, piece_y):
                    piece_x -= 1
                    changed = True

                if pressed2:
                    s2_pressed_at = now
                if released2 and s2_pressed_at is not None:
                    held_for = now - s2_pressed_at
                    s2_pressed_at = None
                    if held_for < hold_seconds:
                        turned = rotated(cells)
                        if not blocked(turned, piece_x, piece_y):
                            cells = turned
                            changed = True
                        if last_s2_tap is not None and now - last_s2_tap <= triple_tap_seconds:
                            s2_tap_count += 1
                        else:
                            s2_tap_count = 1
                        last_s2_tap = now
                        if s2_tap_count >= 3:
                            display.rotation = 0
                            return

            fast_drop = (
                s2_pressed_at is not None
                and now - s2_pressed_at >= hold_seconds
                and not chord_down
            )
            drop_interval = 0.06 if fast_drop else max(0.18, 0.62 - rows_cleared * 0.025)
            if now - last_drop >= drop_interval:
                if not blocked(cells, piece_x, piece_y + 1):
                    piece_y += 1
                else:
                    for cell_x, cell_y in cells:
                        x = piece_x + cell_x
                        y = piece_y + cell_y
                        if y >= 0:
                            board_state[y * board_width + x] = piece_color
                    cleared = clear_full_rows()
                    if cleared:
                        rows_cleared += cleared
                        score_value += cleared * cleared * 120
                        score_value_label.text = str(score_value)
                        lines_label.text = "ROWS %d" % rows_cleared
                    else:
                        score_value += 5
                        score_value_label.text = str(score_value)
                    cells, piece_x, piece_y, piece_color = new_piece()
                    if blocked(cells, piece_x, piece_y):
                        game_over = True
                last_drop = now
                changed = True

            if changed:
                render(cells, piece_x, piece_y, piece_color)
            time.sleep(0.015)

        pixels.fill((40, 5, 0))
        pixels.show()
        message.text = "GAME OVER"
        display.refresh()
        if interruptible_wait(1.0):
            display.rotation = 0
            return
        pixels.fill((0, 0, 0))
        pixels.show()
        if countdown("SCORE %d" % score_value):
            display.rotation = 0
            return


def open_menu(selected):
    while True:
        selected = choose_menu_item(selected)

        if selected == 0:
            show_screen(CONFERENCE)
            return selected, CONFERENCE
        if selected == 1:
            show_screen(INFO)
            return selected, INFO
        if selected == 2:
            show_screen(QR)
            return selected, QR
        if selected == 3:
            show_screen(LINKEDIN)
            return selected, LINKEDIN

        if selected == 4:
            play_pong()
        elif selected == 5:
            play_breakout()
        elif selected == 6:
            play_flappy()
        elif selected == 7:
            play_badge_blaster()
        elif selected == 8:
            play_byte_drop()

        # Game scenes are local to their play functions. Return to a known
        # root group before collecting them so repeated games do not fragment
        # the ESP32-S3's heap.
        display.rotation = 0
        display.root_group = menu_scene
        gc.collect()


current_screen = CONFERENCE
menu_selection = 0
show_screen(current_screen)
backlight.value = True

menu_hold_started = None
last_time = time.monotonic()

while True:
    now = time.monotonic()
    dt = now - last_time
    last_time = now

    all_pressed = not sw1.value and not sw2.value and not sw3.value
    if all_pressed:
        if menu_hold_started is None:
            menu_hold_started = now
        elif now - menu_hold_started >= MENU_HOLD_SECONDS:
            menu_selection, current_screen = open_menu(menu_selection)
            wait_for_buttons_released()
            menu_hold_started = None
            last_time = time.monotonic()
        time.sleep(0.02)
        continue

    menu_hold_started = None

    # Gentle blue/cyan breathing makes the Robojuice badge noticeable.
    # QR and conference screens remain dark for reliable scanning and calm.
    if current_screen == INFO:
        brightness = 0.12 + 0.28 * (0.5 + 0.5 * math.sin(now * 1.7))
        pixels[0] = (0, int(100 * brightness), int(150 * brightness))
        pixels[1] = (0, int(140 * brightness), int(210 * brightness))
        pixels[2] = (0, int(180 * brightness), int(255 * brightness))
        pixels[3] = (0, int(140 * brightness), int(210 * brightness))
        pixels[4] = (0, int(100 * brightness), int(150 * brightness))
        pixels.show()
    elif dt > 0:
        pixels.fill((0, 0, 0))
        pixels.show()

    time.sleep(0.02)
