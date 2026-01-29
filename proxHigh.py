import asyncio
import threading
import time
import ctypes
from datetime import datetime
from queue import Queue, Empty

from bleak import BleakScanner
import tkinter as tk
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

# ================= CONFIG =================
TARGET_ADDRESS = "BLuetooth Address"

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
    log("⚠ LOCK → Windows locked")
    ctypes.windll.user32.LockWorkStation()
    below_since = None
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

    log(f"📡 RSSI {rssi}")

    if not enabled:
        if rssi >= AUTO_ON_RSSI:
            if strong_since is None:
                strong_since = now
                log("🔄 AUTO-ON → strong signal")
            elif now - strong_since >= AUTO_ON_TIME:
                enabled = True
                strong_since = None
                log("✅ AUTO-ON → ENABLED")
        else:
            strong_since = None
        return

    if rssi <= RSSI_THRESHOLD:
        if below_since is None:
            below_since = now
            log("⚠ LOCK → weak RSSI detected")
    else:
        below_since = None

# ================= BLE LOOP =================
async def ble_loop():
    global scanner
    scanner = BleakScanner(detection_callback)
    await scanner.start()
    log("🚀 BLE scanner running")

    while True:
        now = time.time()

        if enabled:
            if time.time() < cooldown_until:
                await asyncio.sleep(0.5)
                continue

            if below_since and (now - below_since >= RSSI_TIME):
                lock_windows()

            if now - last_seen >= NO_SIGNAL_TIME:
                log("⚠ LOCK → no signal timeout")
                lock_windows()

        await asyncio.sleep(0.5)

def start_ble_thread():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ble_loop())

# ================= CUSTOM WIDGETS =================
class GlowButton(tk.Canvas):
    def __init__(self, parent, text, command, color, width=140, height=45):
        super().__init__(parent, width=width, height=height, bg="#0a0e14", highlightthickness=0)
        self.command = command
        self.text = text
        self.color = color
        self.hover = False
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
        self.draw()
        
    def draw(self):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        
        if self.hover:
            # Glowing border
            self.create_rectangle(2, 2, w-2, h-2, outline=self.color, width=3)
            self.create_rectangle(0, 0, w, h, outline=self.color, width=1)
            # Bright background
            self.create_rectangle(4, 4, w-4, h-4, fill=self.color, outline="")
            self.create_text(w//2, h//2, text=self.text, fill="#0a0e14", 
                           font=("Orbitron", 11, "bold"))
        else:
            # Normal border
            self.create_rectangle(1, 1, w-1, h-1, outline=self.color, width=2)
            # Subtle inner glow
            self.create_rectangle(3, 3, w-3, h-3, outline=self.color, width=1)
            self.create_text(w//2, h//2, text=self.text, fill=self.color,
                           font=("Orbitron", 10, "bold"))
    
    def on_enter(self, e):
        self.hover = True
        self.draw()
        
    def on_leave(self, e):
        self.hover = False
        self.draw()
        
    def on_click(self, e):
        if self.command:
            self.command()

class StatusIndicator(tk.Canvas):
    def __init__(self, parent, width=20, height=20):
        super().__init__(parent, width=width, height=height, bg="#0a0e14", highlightthickness=0)
        self.active = False
        self.animation_step = 0
        self.draw()
        self.animate()
        
    def set_active(self, active):
        self.active = active
        self.draw()
        
    def draw(self):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        cx, cy = w//2, h//2
        
        if self.active:
            # Pulsing active indicator
            size = 6 + int(2 * abs((self.animation_step % 60) - 30) / 30)
            color = "#00ff88"
            # Outer glow
            self.create_oval(cx-8, cy-8, cx+8, cy+8, outline=color, width=1)
            # Inner core
            self.create_oval(cx-size, cy-size, cx+size, cy+size, fill=color, outline="")
        else:
            # Inactive indicator
            self.create_oval(cx-5, cy-5, cx+5, cy+5, outline="#334155", width=2)
            
    def animate(self):
        if self.active:
            self.animation_step += 1
            self.draw()
        self.after(50, self.animate)

# ================= GUI =================
class ProxLockApp:
    def __init__(self, root):
        self.root = root
        root.title("PROXLOCK // PROXIMITY SECURITY SYSTEM")
        root.geometry("900x600")
        root.configure(bg="#0a0e14")
        
        # Try to use custom font, fallback to available fonts
        try:
            self.title_font = tkfont.Font(family="Orbitron", size=18, weight="bold")
        except:
            self.title_font = tkfont.Font(family="Arial", size=18, weight="bold")
            
        try:
            self.mono_font = tkfont.Font(family="Consolas", size=10)
        except:
            self.mono_font = tkfont.Font(family="Courier", size=10)

        # ===== HEADER =====
        header = tk.Frame(root, bg="#0a0e14", height=80)
        header.pack(fill=tk.X, pady=(20, 10))
        header.pack_propagate(False)
        
        # Title with cyberpunk styling
        title_container = tk.Frame(header, bg="#0a0e14")
        title_container.pack(expand=True)
        
        tk.Label(title_container, text="⬢ PROXLOCK", 
                fg="#00ff88", bg="#0a0e14", 
                font=self.title_font).pack()
        
        tk.Label(title_container, text="PROXIMITY SECURITY SYSTEM v2.1", 
                fg="#64748b", bg="#0a0e14",
                font=("Arial", 9)).pack()
        
        # Separator line
        sep1 = tk.Canvas(root, height=2, bg="#0a0e14", highlightthickness=0)
        sep1.pack(fill=tk.X, padx=40)
        sep1.create_line(0, 1, 900, 1, fill="#1e293b", width=2)
        
        # ===== STATUS PANEL =====
        status_frame = tk.Frame(root, bg="#0a0e14")
        status_frame.pack(pady=20)
        
        # Status indicator and text
        indicator_frame = tk.Frame(status_frame, bg="#0a0e14")
        indicator_frame.pack()
        
        self.status_indicator = StatusIndicator(indicator_frame)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 15))
        
        status_text_frame = tk.Frame(indicator_frame, bg="#0a0e14")
        status_text_frame.pack(side=tk.LEFT)
        
        tk.Label(status_text_frame, text="SYSTEM STATUS", 
                fg="#64748b", bg="#0a0e14",
                font=("Arial", 9)).pack(anchor="w")
        
        self.status_var = tk.StringVar(value="OFFLINE")
        self.status_label = tk.Label(status_text_frame, textvariable=self.status_var,
                                     fg="#ff4757", bg="#0a0e14",
                                     font=("Orbitron", 16, "bold"))
        self.status_label.pack(anchor="w")
        
        # ===== CONTROL PANEL =====
        controls = tk.Frame(root, bg="#0a0e14")
        controls.pack(pady=20)
        
        self.start_btn = GlowButton(controls, "▶ START", self.start, "#00ff88")
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = GlowButton(controls, "■ STOP", self.stop, "#ff4757")
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        self.exit_btn = GlowButton(controls, "✕ EXIT", self.exit, "#64748b", width=120)
        self.exit_btn.pack(side=tk.LEFT, padx=10)
        
        # Separator line
        sep2 = tk.Canvas(root, height=2, bg="#0a0e14", highlightthickness=0)
        sep2.pack(fill=tk.X, padx=40, pady=(20, 10))
        sep2.create_line(0, 1, 900, 1, fill="#1e293b", width=2)
        
        # ===== LOG PANEL =====
        log_label_frame = tk.Frame(root, bg="#0a0e14")
        log_label_frame.pack(fill=tk.X, padx=40)
        
        tk.Label(log_label_frame, text="⚡ SYSTEM LOG", 
                fg="#64748b", bg="#0a0e14",
                font=("Arial", 9, "bold")).pack(anchor="w")
        
        # Log container with border
        log_container = tk.Frame(root, bg="#1e293b", padx=2, pady=2)
        log_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=(5, 20))
        
        self.log_box = ScrolledText(
            log_container,
            bg="#0f1419",
            fg="#00ff88",
            insertbackground="#00ff88",
            font=self.mono_font,
            selectbackground="#1e3a5f",
            selectforeground="#00ff88",
            borderwidth=0,
            highlightthickness=0
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)
        
        # Add tags for colored log entries
        self.log_box.tag_config("timestamp", foreground="#64748b")
        self.log_box.tag_config("error", foreground="#ff4757")
        self.log_box.tag_config("success", foreground="#00ff88")
        self.log_box.tag_config("warning", foreground="#ffa502")
        self.log_box.tag_config("info", foreground="#48dbfb")
        
        self.poll_logs()

    def start(self):
        global enabled, below_since, strong_since, last_seen
        enabled = True
        below_since = None
        strong_since = None
        last_seen = time.time()
        self.status_var.set("ACTIVE")
        self.status_label.configure(fg="#00ff88")
        self.status_indicator.set_active(True)
        log("✅ MANUAL → ON")

    def stop(self):
        global enabled, below_since, strong_since, cooldown_until, last_seen
        enabled = False
        below_since = None
        strong_since = None
        cooldown_until = 0
        last_seen = time.time()
        self.status_var.set("OFFLINE")
        self.status_label.configure(fg="#ff4757")
        self.status_indicator.set_active(False)
        log("⏸ MANUAL → OFF (timers reset)")

    def exit(self):
        log("🔌 App exiting")
        self.root.destroy()
        if loop:
            loop.stop()

    def poll_logs(self):
        try:
            while True:
                msg = log_queue.get_nowait()
                
                # Parse and colorize log entry
                if "][" in msg:
                    parts = msg.split("]", 1)
                    timestamp = parts[0] + "]"
                    content = parts[1] if len(parts) > 1 else ""
                    
                    self.log_box.insert(tk.END, timestamp, "timestamp")
                    
                    # Color code based on content
                    if "⚠" in content or "LOCK" in content:
                        self.log_box.insert(tk.END, content + "\n", "warning")
                    elif "✅" in content or "ENABLED" in content:
                        self.log_box.insert(tk.END, content + "\n", "success")
                    elif "📡" in content or "RSSI" in content:
                        self.log_box.insert(tk.END, content + "\n", "info")
                    elif "🚀" in content:
                        self.log_box.insert(tk.END, content + "\n", "success")
                    else:
                        self.log_box.insert(tk.END, content + "\n")
                else:
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
    log("🚀 App started")
    root.mainloop()

if __name__ == "__main__":
    main()