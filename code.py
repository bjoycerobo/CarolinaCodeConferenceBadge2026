"""
Robojuice conference badge
==========================

SW1  -- Robojuice home
SW2  -- Robojuice / Brandon Joyce information
SW3  -- QR code for https://robojuice.com/

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

HOME = 0
INFO = 1
QR = 2
CONFERENCE = 3


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
    item = label.Label(terminalio.FONT, text=text, color=color, scale=scale)
    item.anchor_point = (0.5, 0.5)
    item.anchored_position = (WIDTH // 2, y)
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
ccc_bitmap, ccc_palette = load_image("/img/CarolinaCodeConference.bmp")


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


screens = (home_screen(), info_screen(), qr_screen(), conference_screen())


# Interaction ------------------------------------------------------
def show_screen(index):
    display.root_group = screens[index]
    display.refresh()


current_screen = HOME
show_screen(current_screen)
backlight.value = True

previous = (True, True, True)
reset_started = None
last_time = time.monotonic()

while True:
    now = time.monotonic()
    dt = now - last_time
    last_time = now

    values = (sw1.value, sw2.value, sw3.value)
    all_pressed = not values[0] and not values[1] and not values[2]

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
    pressed1 = not values[0] and previous[0]
    pressed2 = not values[1] and previous[1]
    pressed3 = not values[2] and previous[2]
    previous = values

    if pressed1:
        current_screen = HOME
        show_screen(current_screen)
    elif pressed2:
        current_screen = INFO
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
