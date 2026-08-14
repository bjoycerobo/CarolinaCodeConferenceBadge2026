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
)


def build_menu():
    group = displayio.Group()
    group.append(background(0x000010))
    group.append(centered("BADGE MENU", 10, 0x00FFFF, 2))
    labels = []
    for index, name in enumerate(MENU_ITEMS):
        item = centered(name, 35 + index * 15, 0x708090)
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
    wait_for_buttons_released()

    player_x = (game_width - paddle_width) / 2
    computer_x = (game_width - paddle_width) / 2
    player_score = 0
    computer_score = 0
    serve_direction = 1

    def countdown(text="GET READY"):
        message.text = text
        display.refresh()
        time.sleep(0.6)
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            time.sleep(1.0)
        message.text = ""
        display.refresh()

    def reset_ball(direction):
        ball_x = (game_width - ball_size) / 2
        ball_y = (game_height - ball_size) / 2
        ball_vx = 72.0 * direction
        ball_vy = -48.0 if (player_score + computer_score) % 2 else 48.0
        return ball_x, ball_y, ball_vx, ball_vy

    countdown()
    ball_x, ball_y, ball_vx, ball_vy = reset_ball(serve_direction)
    last_frame = time.monotonic()
    computer_update = 0
    computer_follows_ball = True
    computer_going_left = True
    previous_sw2 = True
    pending_quit_at = None

    while True:
        now = time.monotonic()
        if now - last_frame < frame_seconds:
            time.sleep(0.003)
            continue
        dt = now - last_frame
        if dt > 0.08:
            dt = 0.08
        last_frame = now

        sw2_value = sw2.value
        sw2_pressed = not sw2_value and previous_sw2
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
                countdown(result)
                pixels.fill((0, 0, 0))
                pixels.show()
                player_score = 0
                computer_score = 0
                score.text = "CPU 0  YOU 0"
            ball_x, ball_y, ball_vx, ball_vy = reset_ball(serve_direction)
            time.sleep(0.5)
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
    wait_for_buttons_released()

    def countdown(text="BREAKOUT"):
        message.text = text
        display.refresh()
        time.sleep(0.6)
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            time.sleep(1.0)
        message.text = ""

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
    countdown()
    ball_x, ball_y, ball_vx, ball_vy = reset_ball()
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

        if not sw2.value:
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
                time.sleep(1.0)
                message.text = ""
                ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                last_frame = time.monotonic()
            else:
                pixels.fill((40, 5, 0))
                pixels.show()
                countdown("GAME OVER")
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
            countdown("YOU WIN!")
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
    wait_for_buttons_released()

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
        time.sleep(0.6)
        for number in (3, 2, 1):
            message.text = str(number)
            display.refresh()
            time.sleep(1.0)
        message.text = ""

    while True:
        bird_y = 56.0
        bird_velocity = 0.0
        score = 0
        score_label.text = "SCORE 0"
        position_pipe(pipes[0], game_width + 20)
        position_pipe(pipes[1], game_width + 20 + pipe_spacing)
        bird.y = int(bird_y)
        countdown("FLAPPY")
        last_frame = time.monotonic()
        previous_values = (True, True, True)
        collided = False

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
        time.sleep(1.0)
        pixels.fill((0, 0, 0))
        pixels.show()
        countdown("SCORE %d" % score)


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
