"""
Robojuice conference badge
==========================

SW1  -- Robojuice home
SW2  -- Robojuice / Brandon Joyce information
SW3  -- QR code for https://robojuice.com/

Hidden shortcuts:
SW1 + SW3       -- LinkedIn QR code
Hold SW2 + SW3  -- one-player Pong

Pong controls:
SW1  -- move right
SW2  -- quit; double-tap changes computer mode
SW3  -- move left

Hold all three switches for 1.25 seconds to return to the Carolina
Code Conference default screen.

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
HOLD_TO_RESET_SECONDS = 1.25
GAME_HOLD_SECONDS = 0.6
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
    group.append(centered("1 HOME  2 INFO  3 QR", 151, 0x808080))
    return group


def info_screen():
    group = displayio.Group()
    group.append(background())
    group.append(image_tile(logo_bitmap, logo_palette, 6, 12))
    group.append(centered("GIVE YOUR TEAM", 57, 0x00FFFF, 2))
    group.append(centered("BETTER SYSTEMS", 78, 0x00FFFF, 2))
    group.append(centered("BRANDON JOYCE", 108, 0xFFFFFF, 2))
    group.append(centered("SENIOR DEVELOPER", 125, 0xFFB000))
    group.append(centered("1 HOME  2 INFO  3 QR", 151, 0x808080))
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
    group.append(centered("HOLD 1 + 2 + 3 TO RESET", 151, 0x808080))
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

    # Do not treat the SW2 + SW3 entry chord as game input.
    while not (sw1.value and sw2.value and sw3.value):
        time.sleep(0.02)

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


current_screen = HOME
show_screen(current_screen)
backlight.value = True

previous = (True, True, True)
reset_started = None
game_hold_started = None
last_time = time.monotonic()

while True:
    now = time.monotonic()
    dt = now - last_time
    last_time = now

    values = (sw1.value, sw2.value, sw3.value)
    all_pressed = not values[0] and not values[1] and not values[2]
    game_pressed = values[0] and not values[1] and not values[2]
    linkedin_pressed = not values[0] and values[1] and not values[2]

    # A deliberate hold prevents an accidental reset while someone
    # changes screens. The conference screen is static and quiet.
    if all_pressed:
        if reset_started is None:
            reset_started = now
        elif now - reset_started >= HOLD_TO_RESET_SECONDS:
            if current_screen != CONFERENCE:
                current_screen = CONFERENCE
                show_screen(current_screen)
            pixels.fill((0, 0, 0))
            pixels.show()
        previous = values
        time.sleep(0.02)
        continue

    reset_started = None

    if game_pressed:
        if game_hold_started is None:
            game_hold_started = now
        elif now - game_hold_started >= GAME_HOLD_SECONDS:
            play_pong()
            current_screen = INFO
            show_screen(current_screen)
            previous = (sw1.value, sw2.value, sw3.value)
            last_time = time.monotonic()
            game_hold_started = None
        else:
            previous = values
        time.sleep(0.02)
        continue

    game_hold_started = None
    pressed1 = not values[0] and previous[0]
    pressed2 = not values[1] and previous[1]
    pressed3 = not values[2] and previous[2]
    previous = values

    if linkedin_pressed:
        current_screen = LINKEDIN
        show_screen(current_screen)
        while not (sw1.value and sw3.value):
            time.sleep(0.02)
        previous = (sw1.value, sw2.value, sw3.value)
    elif pressed2:
        current_screen = INFO
        show_screen(current_screen)
    elif pressed1:
        current_screen = HOME
        show_screen(current_screen)
    elif pressed3:
        current_screen = QR
        show_screen(current_screen)

    # Gentle blue/cyan breathing makes the home and information
    # screens noticeable without distracting from the text. QR and
    # conference screens remain dark for reliable scanning and calm.
    if current_screen == HOME or current_screen == INFO:
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
