# HWiNFO OLED System Monitor

Display your PC's system metrics on SteelSeries OLED screens using HWiNFO sensor data.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)

> **Compatible with Windows only** - requires HWiNFO64 and SteelSeries devices

## Quick Start

1. Enable "Shared Memory Support" in HWiNFO Settings → General/User Interface, then restart HWiNFO
2. Install Python dependencies: `pip install -r requirements.txt`
3. Run: `python hwinfo_oled_monitor.py`
4. Follow the interactive sensor selection wizard
5. Check your SteelSeries OLED display!

## Features

**Universal Compatibility** - Works with any PC build (CPU/GPU agnostic)  
**No CSV Logging** - Reads directly from HWiNFO shared memory  
**Interactive Setup** - Sensor selection wizard on first run  
**Cycling Display Modes** - 6 different layouts showing various metrics  
**Real-time Monitoring** - Updates every 3 seconds  
**GameSense Integration** - Uses SteelSeries GameSense SDK  
**Console Fallback** - Works without OLED display for testing  
**Auto-Save Config** - Remembers your sensor selections  

## Supported Devices

Any SteelSeries device with an OLED screen:
- SteelSeries GameDAC
- SteelSeries Arctis Pro Wireless
- Other SteelSeries OLED-equipped devices

## Display Modes

The monitor cycles through these modes every 3 seconds:

1. **System Overview** - CPU and GPU load percentages
2. **CPU Details** - CPU temperature and load
3. **GPU Details** - GPU temperature and load
4. **Memory Stats** - RAM usage and GPU memory
5. **Temperature Overview** - CPU and GPU temperatures
6. **Time & Info** - Current time and storage/motherboard temp

## Requirements

### Software
- **HWiNFO64** (free) - [Download here](https://www.hwinfo.com/download/)
- **SteelSeries Engine** or **SteelSeries GG** - [Download here](https://steelseries.com/gg)
- **Python 3.7+** - [Download here](https://www.python.org/downloads/)

### Python Packages
```bash
pip install requests psutil
```

> **Note:** The `pywhinfo` module is included in this repository as `pywhinfo.py` - no separate installation needed!

## Setup Instructions

### 0. Clone or Download this Repository

```bash
git clone https://github.com/SergioDanielFernandesCruz/projeto_final.git # needs updated URL
cd projeto_final/hwinfo_oled-specs                                       # needs updated path
```

Or download the ZIP file from GitHub and extract it.

### 1. Enable HWiNFO Shared Memory

1. Download and install [HWiNFO64](https://www.hwinfo.com/download/)
2. Launch HWiNFO and go to **Settings** (⚙️ icon)
3. Navigate to **Safety** tab
4. Enable **"Shared Memory Support"**
5. Click **OK**
6. **Restart HWiNFO64** (important - restart the app!)
7. Keep HWiNFO running in the background after restarting it

### 2. Install Python Dependencies

Open a command prompt or PowerShell and run:

```bash
pip install -r requirements.txt
```

The `pywhinfo` library is included as `pywhinfo.py` in this repository.

**Test your setup:**
```bash
python test_hwinfo_connection.py
```

This will verify that HWiNFO is accessible and all dependencies are installed correctly.

### 3. Run the Monitor

1. Make sure **HWiNFO64** is running with shared memory enabled
2. Make sure **SteelSeries Engine/GG** is running
3. Run the script:
   ```bash
   python hwinfo_oled_monitor.py
   ```

4. **First Run:** Interactive sensor selection wizard will appear
   - The script will show you all available sensors from your system
   - Select the sensors you want to monitor (CPU temp, GPU load, etc.)
   - Selections are saved to `hwinfo_monitor_config.json`

5. Check your SteelSeries OLED display!

## Interactive Sensor Selection

On first run, you'll see something like this:

```
======================================================================
SENSOR SELECTION WIZARD
======================================================================

Let's configure your sensors!
For each metric, you'll see available sensors from your system.
Type the number to select, or press Enter to skip.

1  CPU Temperature
--------------------------------------------------
  [1] CPU Package: 45.0 °C
  [2] CPU (Tctl/Tdie): 44.5 °C
  [3] Core Temperature: 43.0 °C

Select CPU temp sensor (1-3, or Enter to skip): 1
✓ Selected: CPU Package

2  CPU Load/Usage
--------------------------------------------------
  [1] Total CPU Usage: 25.3 %
  [2] CPU Utilization: 25.3 %

Select CPU load sensor (1-2, or Enter to skip): 1
✓ Selected: Total CPU Usage

... (continues for GPU, memory, etc.)
```

The script will remember your selected options in `hwinfo_monitor_config.json`.

## Troubleshooting

### "Could not connect to HWiNFO shared memory"
- Make sure HWiNFO64 is running
- Enable "Shared Memory Support" in HWiNFO Settings → Safety
- **Restart HWiNFO** after enabling (very important!)
- Make sure you're running HWiNFO64 (not 32-bit version)

### "GameSense server not found"
- Make sure SteelSeries Engine or GG is running
- Check that your SteelSeries device is connected
- The script will still work in console-only mode

### "No sensors found" or wrong sensors selected
- Delete `hwinfo_monitor_config.json` to run setup wizard again
- Make sure HWiNFO is actively reading sensors (check HWiNFO window)
- Some sensors may not be available on all hardware

### "pywhinfo" module not found
- The `pywhinfo.py` file should be in the same directory as `hwinfo_oled_monitor.py`
- Make sure both files are in the same folder
- If you downloaded only one file, download the complete repository

### Display showing "0" values
- Check that you selected the correct sensors in the setup wizard
- Open HWiNFO sensor window to verify sensor values are updating
- Delete config file and run setup wizard again

## Customization

### Change Update Interval
Edit line 69 in the the hwinfo_oled_monitor.py file:
```python
UPDATE_INTERVAL = 3  # Change to desired seconds
```

### Change Number of Display Modes
Edit line 72 in the script:
```python
NUM_DISPLAY_MODES = 6  # Change to show fewer/more modes
```

### Reconfigure Sensors
Simply delete `hwinfo_monitor_config.json` and run the script again.

### Add Custom Display Modes
Edit the `get_display_data()` function to add your own layouts!

## How It Works

This script uses HWiNFO's **shared memory** feature to read sensor data in real-time:

1. **HWiNFO** writes sensor data to Windows shared memory
2. **pywhinfo.py** module reads from that shared memory
3. Script processes and formats the data
4. Data is sent to **SteelSeries GameSense SDK**
5. GameSense displays it on your OLED screen

### Why Shared Memory vs CSV?
- **Faster** - No file I/O overhead
- **More reliable** - Real-time data access
- **Cleaner** - No log files cluttering your drive
- **Less disk wear** - No constant writing to SSD/HDD

## Running on Startup (Windows)

### Method 1: Startup Folder

1. Create a batch file `start_hwinfo_monitor.bat`:
   ```batch
   @echo off
   cd /d "C:\path\to\script\directory"
   python hwinfo_oled_monitor.py
   ```

2. Press `Win + R`, type `shell:startup`, press Enter
3. Create a shortcut to your batch file in the Startup folder

### Method 2: Task Scheduler (Recommended)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "At log on"
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\hwinfo_oled_monitor.py`
   - Start in: `C:\path\to\script\directory`
5. Add a 30-second delay to let HWiNFO/SteelSeries start first

## FAQ

**Q: Do I need to enable CSV logging in HWiNFO?**  
A: No! This script reads directly from shared memory. CSV logging is not required.

**Q: Can I use this with LibreHardwareMonitor or other tools?**  
A: No, this specifically requires HWiNFO's shared memory format.

**Q: Will this work on a laptop?**  
A: Yes! As long as you have HWiNFO and a SteelSeries OLED device.

**Q: Can I monitor more than one GPU?**  
A: Yes! Select additional sensors during the setup wizard.

**Q: Does this slow down my system?**  
A: No, it has minimal CPU/memory impact (< 0.1% CPU usage).

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

Ideas for contributions:
- Additional display modes
- Support for more sensor types
- Multi-device support
- ...

## License

MIT License - feel free to use and modify for your needs.

## Acknowledgments

- [HWiNFO](https://www.hwinfo.com/) team for the excellent monitoring software
- [namazso](https://gist.github.com/namazso/0c37be5a53863954c8c8279f66cfb1cc) for reverse-engineering the HWiNFO shared memory format
- SteelSeries for the GameSense SDK
- Community testers

## Support

For issues or questions, please open an issue on the GitHub repository.

---

**Made with love for the PC Gaming Community**

## Project Structure

```
hwinfo_oled-specs/
├── hwinfo_oled_monitor.py       # Main monitoring script
├── pywhinfo.py                  # HWiNFO shared memory interface
├── test_hwinfo_connection.py   # Test script to verify setup
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── LICENSE                      # MIT License
├── .gitignore                   # Git ignore rules
└── hwinfo_monitor_config.json  # Your sensor config (auto-generated, not in repo)
```

Note: The `hwinfo_monitor_config.json` file is auto-generated on first run and excluded from the repository via `.gitignore` to avoid committing personal sensor IDs. To reconfigure sensors, delete this file and run the script again.
