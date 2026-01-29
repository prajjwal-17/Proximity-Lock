import asyncio
import threading
import time
import ctypes
from datetime import datetime
from queue import Queue, Empty

from bleak import BleakScanner
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# ================= CONFIG =================
TARGET_ADDRESS = "D4:5B:51:9C:4B:A0"

RSSI_THRESHOLD = -90
RSSI_TIME = 5
NO_SIGNAL_TIME = 10

AUTO_ON_RSSI = -65
AUTO_ON_TIME = 3

POST_LOCK_COOLDOWN = 5
# =========================================

enabled = False
last_seen = time.time()
below_since = None
strong_since = None
cooldown_until = 0

loop = None
scanner = None

log_queue = Queue()

# ================= LOGGING =================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    log_queue.put(f"[{ts}] {msg}")

# ================= SYSTEM =================
def lock_windows():
    global below_since, cooldown_until, last_seen
    log("LOCK → Windows locked")
    ctypes.windll.user32.LockWorkStation()
    below_since = None
    # Reset last_seen to now to prevent immediate re-lock after unlock
    last_seen = time.time()
    cooldown_until = time.time() + POST_LOCK_COOLDOWN

# ================= BLE CALLBACK =================
def detection_callback(device, advertisement_data):
    global last_seen, below_since, strong_since, enabled

    if device.address.lower() != TARGET_ADDRESS.lower():
        return

    now = time.time()
    rssi = advertisement_data.rssi
    last_seen = now

    log(f"RSSI {rssi}")

    # -------- AUTO-ON --------
    if not enabled:
        if rssi >= AUTO_ON_RSSI:
            if strong_since is None:
                strong_since = now
                log("AUTO-ON → strong signal")
            elif now - strong_since >= AUTO_ON_TIME:
                enabled = True
                strong_since = None
                log("AUTO-ON → ENABLED")
        else:
            strong_since = None
        return

    # -------- LOCK LOGIC --------
    if rssi <= RSSI_THRESHOLD:
        if below_since is None:
            below_since = now
            log("LOCK → weak RSSI detected")
    else:
        below_since = None

# ================= BLE LOOP =================
async def ble_loop():
    global scanner
    scanner = BleakScanner(detection_callback)
    await scanner.start()
    log("BLE scanner running")

    while True:
        now = time.time()

        # Only check lock conditions if enabled
        if enabled:
            # Skip lock checks during cooldown
            if time.time() < cooldown_until:
                await asyncio.sleep(0.5)
                continue

            if below_since and (now - below_since >= RSSI_TIME):
                lock_windows()

            if now - last_seen >= NO_SIGNAL_TIME:
                log("LOCK → no signal timeout")
                lock_windows()

        await asyncio.sleep(0.5)

def start_ble_thread():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ble_loop())

# ================= GUI =================
class ProxLockApp:
    def __init__(self, root):
        self.root = root
        root.title("ProxLock")
        root.geometry("720x480")
        root.configure(bg="#0f1115")

        self.status_var = tk.StringVar(value="OFF")

        top = tk.Frame(root, bg="#0f1115")
        top.pack(fill=tk.X, pady=10)

        tk.Label(top, text="Status:", fg="#9da5b4", bg="#0f1115").pack(side=tk.LEFT, padx=5)
        tk.Label(
            top,
            textvariable=self.status_var,
            fg="#00ffcc",
            bg="#0f1115",
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(top, text="START", command=self.start,
                  bg="#1f6feb", fg="white", width=10).pack(side=tk.LEFT, padx=20)

        tk.Button(top, text="STOP", command=self.stop,
                  bg="#da3633", fg="white", width=10).pack(side=tk.LEFT)

        tk.Button(top, text="EXIT", command=self.exit,
                  bg="#30363d", fg="white").pack(side=tk.RIGHT, padx=10)

        self.log_box = ScrolledText(
            root,
            height=20,
            bg="#0b0e14",
            fg="#c9d1d9",
            insertbackground="white",
            font=("Consolas", 10)
        )
        self.log_box.pack(fill=tk.BOTH, padx=10, pady=10)

        self.poll_logs()

    def start(self):
        global enabled, below_since, strong_since, last_seen
        enabled = True
        below_since = None
        strong_since = None
        # Reset last_seen when manually starting to avoid immediate lock
        last_seen = time.time()
        self.status_var.set("ON")
        log("MANUAL → ON")

    def stop(self):
        global enabled, below_since, strong_since, cooldown_until, last_seen
        enabled = False
        below_since = None
        strong_since = None
        cooldown_until = 0
        # Reset last_seen to prevent stale timeout
        last_seen = time.time()
        self.status_var.set("OFF")
        log("MANUAL → OFF (timers reset)")

    def exit(self):
        log("App exiting")
        self.root.destroy()
        if loop:
            loop.stop()

    def poll_logs(self):
        try:
            while True:
                msg = log_queue.get_nowait()
                self.log_box.insert(tk.END, msg + "\n")
                self.log_box.see(tk.END)
        except Empty:
            pass
        self.root.after(200, self.poll_logs)

# ================= MAIN =================
def main():
    threading.Thread(target=start_ble_thread, daemon=True).start()
    root = tk.Tk()
    ProxLockApp(root)
    log("App started")
    root.mainloop()

if __name__ == "__main__":
    main()