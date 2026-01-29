import asyncio
import threading
import time
import ctypes
from bleak import BleakScanner

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

TARGET_ADDRESS = "D4:5B:51:9C:4B:A0"

RSSI_THRESHOLD = -90
RSSI_TIME = 5
NO_SIGNAL_TIME = 10

enabled = False
last_seen = time.time()
below_since = None
scanner = None
loop = None

def lock_windows():
    ctypes.windll.user32.LockWorkStation()

def detection_callback(device, advertisement_data):
    global last_seen, below_since
    if not enabled:
        return

    if device.address.lower() != TARGET_ADDRESS.lower():
        return

    now = time.time()
    rssi = advertisement_data.rssi
    last_seen = now

    if rssi <= RSSI_THRESHOLD:
        if below_since is None:
            below_since = now
    else:
        below_since = None

async def ble_loop():
    global scanner
    scanner = BleakScanner(detection_callback)
    await scanner.start()

    while True:
        if not enabled:
            await asyncio.sleep(1)
            continue

        now = time.time()

        if below_since and (now - below_since >= RSSI_TIME):
            lock_windows()
            break

        if now - last_seen >= NO_SIGNAL_TIME:
            lock_windows()
            break

        await asyncio.sleep(0.5)

def start_ble_thread():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ble_loop())

def toggle(icon, _):
    global enabled, last_seen, below_since
    enabled = not enabled
    last_seen = time.time()
    below_since = None
    icon.title = "ProxLock ON" if enabled else "ProxLock OFF"

def exit_app(icon, _):
    icon.stop()
    if loop:
        loop.stop()

def create_image():
    img = Image.new("RGB", (64, 64), color="black")
    d = ImageDraw.Draw(img)
    d.rectangle((16, 16, 48, 48), fill="white")
    return img

def main():
    icon = pystray.Icon(
        "ProxLock",
        create_image(),
        "ProxLock OFF",
        menu=pystray.Menu(
            item("Toggle ON/OFF", toggle),
            item("Exit", exit_app)
        )
    )

    t = threading.Thread(target=start_ble_thread, daemon=True)
    t.start()

    icon.run()

if __name__ == "__main__":
    main()

