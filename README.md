# ProxLock

Bluetooth proximity-based Windows screen locker with a cyberpunk-inspired UI. Automatically locks your PC when your BLE device moves out of range.

## Features

- Automatic workstation locking based on BLE signal strength
- Real-time RSSI monitoring with configurable thresholds
- Auto-enable when strong signal detected
- Post-lock cooldown to prevent immediate re-locking
- Modern cyberpunk-themed interface with animations
- Color-coded event logging

## Requirements

- Windows 10 (1809+) or Windows 11
- Bluetooth 4.0+ with BLE support
- Python 3.8+ (for building from source)

## Quick Start

### Using Pre-built Executable

1. Download the latest release
2. Run `ProxLock.exe`
3. Configure your BLE device address (see Configuration)

### Running from Source

```bash
git clone https://github.com/yourusername/proxlock.git
cd proxlock
pip install -r requirements.txt
python proxlock_hightech.py
```

## Configuration

### Find Your BLE Device

```python
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        print(f"{d.name or 'Unknown'}: {d.address} (RSSI: {d.rssi})")

asyncio.run(scan())
```

### Configure ProxLock

Edit `proxlock_hightech.py`:

```python
TARGET_ADDRESS = ""  # Your device's bluetooth address

RSSI_THRESHOLD = -90      # Lock when signal drops below this (dBm)
RSSI_TIME = 5             # Stay below threshold for this long (seconds)
NO_SIGNAL_TIME = 10       # Lock after no signal for this long (seconds)

AUTO_ON_RSSI = -65        # Auto-enable when signal above this
AUTO_ON_TIME = 3          # Auto-enable after this duration
POST_LOCK_COOLDOWN = 5    # Wait this long after locking
```

## Building Executable

### Windows (Simple)

```batch
build_simple.bat
```

The executable will be in the `dist` folder.

### Manual Build

```bash
pip install bleak pyinstaller
pyinstaller --onefile --windowed --name "ProxLock" proxlock_hightech.py
```

## Usage

**START** - Enable proximity monitoring  
**STOP** - Disable monitoring and reset timers  
**EXIT** - Close application

### Status Indicators

- Pulsing green dot = Active monitoring
- Gray dot = Inactive
- Color-coded logs: Green (success), Blue (RSSI), Yellow (warnings)

## Configuration Guide

### RSSI Threshold Tuning

| Sensitivity | RSSI Value | Use Case |
|------------|------------|----------|
| High (locks easily) | -70 to -80 | Small room, close proximity |
| Medium | -85 to -95 | Office desk, standard use |
| Low (locks rarely) | -100 to -110 | Large room, distant device |

### Timing Parameters

- **RSSI_TIME**: 3-5 seconds for quick response, 8-10 for relaxed
- **NO_SIGNAL_TIME**: 8-12 seconds recommended
- **POST_LOCK_COOLDOWN**: 5-10 seconds to avoid re-lock loop

## Troubleshooting

**Won't lock PC**
- Run as Administrator

**Device not detected**
- Verify MAC address with scanner script
- Check Bluetooth is enabled
- Ensure device is powered on

**Locks immediately after unlock**
- Fixed in v2.1 - update to latest version

**Manual STOP doesn't work**
- Fixed in v2.1 - update to latest version

**Build fails**
```bash
pip install --upgrade pip setuptools wheel
pip install bleak==0.21.1 pyinstaller==6.3.0
```

## Technical Details

### Architecture

- BLE thread runs async event loop for scanning
- GUI thread handles tkinter interface
- Queue-based logging between threads
- Uses Windows API `LockWorkStation()` for locking

### Performance

- Memory: ~50-80 MB
- CPU: <1% idle, <3% scanning
- Polling: 500ms main loop, 200ms GUI updates

## Security Notes

- Proximity locking is supplementary security
- Not resistant to BLE spoofing
- Use with strong passwords/biometrics
- Not recommended for high-security environments alone

## File Structure

```
ProxLock/
├── proxlock_hightech.py    # Main application
├── requirements.txt         # Dependencies
├── build_simple.bat        # Build script
├── ProxLock.spec           # PyInstaller config
└── README.md               # This file
```

## Version History

**v2.1** - Fixed re-lock bug and manual stop issue  
**v2.0** - New cyberpunk UI with animations  
**v1.0** - Initial release

## Contributing

Issues and pull requests welcome. Please include:
- Clear description of changes
- Test results on Windows 10/11
- Updated documentation if needed

## License

MIT License - see LICENSE file for details

## Disclaimer

Provided "as is" without warranty. Use at your own risk. Not liable for security breaches or damages.
