"""
HWiNFO System Monitor for SteelSeries GameDAC OLED Display
Displays system metrics from HWiNFO on SteelSeries OLED screens

This script reads hardware monitoring data from HWiNFO's shared memory and displays
it on SteelSeries devices with OLED screens (GameDAC, Arctis Pro Wireless, Apex Pro etc.)

Features:
- Reads directly from HWiNFO shared memory
- Automatically discovers GameSense server
- Multiple display modes cycling every 3 seconds
- Works with any PC build (CPU/GPU agnostic)
- Fallback to console-only mode if GameSense unavailable
- Interactive sensor selector on first run

Requirements:
- HWiNFO64 with "Shared Memory Support" enabled
- SteelSeries Engine or SteelSeries GG running
- Python packages: requests, psutil
- pywhinfo.py (included in this repository)

Setup:
1. Open HWiNFO64 Settings → General/User Interface
2. Enable "Shared Memory Support"
3. Restart HWiNFO (important!)
4. Run this script and select your sensors interactively

License: MIT
"""

import requests
import time
import os
import psutil
import json
from datetime import datetime
from collections import deque

try:
    from pywhinfo import HWiNFO
except ImportError:
    print("ERROR: pywhinfo module not found!")
    print("Make sure pywhinfo.py is in the same directory as this script.")
    print()
    input("Press Enter to exit...")
    exit(1)


# ============================================================================
# CONFIGURATION - Will be saved/loaded automatically
# ============================================================================

CONFIG_FILE = "hwinfo_monitor_config.json"

SENSOR_IDS = {
    'cpu_temp': None,
    'cpu_load': None,
    'gpu_temp': None,
    'gpu_load': None,
    'gpu_memory': None,
    'ram_temp': None,
    'ram_usage': None,
    'mb_temp': None,
    'nvme_temp': None,
}

UPDATE_INTERVAL = 3

NUM_DISPLAY_MODES = 6

gpu_load_history = deque(maxlen=5)
cpu_load_history = deque(maxlen=5)
hwinfo = None

def load_config():
    """Load saved sensor configuration"""
    global SENSOR_IDS
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                SENSOR_IDS.update(loaded)
                print(f"✓ Loaded configuration from {CONFIG_FILE}")
                return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config: {e}")
    return False

def save_config():
    """Save sensor configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(SENSOR_IDS, f, indent=2)
        print(f"✓ Configuration saved to {CONFIG_FILE}")
        return True
    except IOError as e:
        print(f"Warning: Could not save config: {e}")
        return False

def find_sensor_by_keywords(hwinfo_instance, keywords, sensor_type=None):
    """
    Find sensor by matching keywords in label
    
    Args:
        hwinfo_instance: HWiNFO instance
        keywords: List of keywords to search for
        sensor_type: Optional sensor type to filter (e.g., 'SENSOR_TYPE_TEMP')
    
    Returns:
        List of matching sensors with their IDs and labels (no duplicates)
    """
    matches = []
    seen_ids = set() 
    
    for sensor in hwinfo_instance.iter_sensors():
        if sensor.id in seen_ids:
            continue
            
        label = sensor.label.lower()
        
        if any(kw.lower() in label for kw in keywords):
            if sensor_type is None or sensor.sensor_type == sensor_type:
                matches.append({
                    'id': sensor.id,
                    'label': sensor.label,
                    'unit': sensor.unit,
                    'value': sensor.value
                })
                seen_ids.add(sensor.id)
    
    return matches

def parse_selection(choice, max_options):
    """
    Parse user selection supporting ranges (1-5), comma-separated (1,3,5), or single values
    Returns list of selected indices (0-based)
    """
    if not choice or not choice.strip():
        return []
    
    selected_indices = []
    parts = choice.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = part.split('-')
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip()) - 1
                if 0 <= start_idx < max_options and 0 <= end_idx < max_options:
                    selected_indices.extend(range(start_idx, end_idx + 1))
            except (ValueError, IndexError):
                pass
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < max_options:
                    selected_indices.append(idx)
            except ValueError:
                pass
    
    return list(set(selected_indices))

def format_sensor_value(value):
    """Format sensor value to max 1 decimal place, or integer if whole number"""
    if isinstance(value, (int, float)):
        if value == int(value):
            return str(int(value))
        else:
            return f"{value:.1f}"
    return str(value)

def interactive_sensor_selection(hwinfo_instance):
    """Interactive sensor selection wizard"""
    global SENSOR_IDS
    
    print("\n" + "=" * 70)
    print("SENSOR SELECTION WIZARD")
    print("=" * 70)
    print("\nLet's configure your sensors!")
    print("For each metric, you'll see available sensors from your system.")
    print("Selection options:")
    print("  - Single number: 5")
    print("  - Multiple: 1,3,5,9")
    print("  - Range: 1-10")
    print("  - Press Enter to skip\n")
    
    # CPU Temperature
    print("\n[1] CPU Temperature")
    print("-" * 50)
    cpu_temp_sensors = find_sensor_by_keywords(hwinfo_instance, 
        ['cpu', 'package', 'tctl', 'tdie', 'processor'])
    
    cpu_temp_sensors = [s for s in cpu_temp_sensors 
                        if 'C' in s['unit'] or '°' in s['unit'] or 'temp' in s['label'].lower()]
    
    if cpu_temp_sensors:
        for i, s in enumerate(cpu_temp_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect CPU temp sensor(s) (1-{min(len(cpu_temp_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(cpu_temp_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['cpu_temp'] = cpu_temp_sensors[selected_indices[0]]['id']
            print(f"[OK] Selected: {cpu_temp_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {cpu_temp_sensors[idx]['label']}")
    else:
        print("  No CPU temperature sensors found")
    
    # CPU Load
    print("\n[2] CPU Load/Usage")
    print("-" * 50)
    cpu_load_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['cpu', 'total', 'usage', 'utilization', 'load', 'core'])
    
    cpu_load_sensors = [s for s in cpu_load_sensors 
                        if '%' in s['unit']
                        and 'memory' not in s['label'].lower()
                        and 'c6' not in s['label'].lower()
                        and 'c-state' not in s['label'].lower()
                        and 'page file' not in s['label'].lower()
                        and 'file usage' not in s['label'].lower()]
    
    cpu_load_sensors.sort(key=lambda s: (
        'total' not in s['label'].lower(),
        'core' in s['label'].lower(),
        s['label']
    ))
    
    if cpu_load_sensors:
        for i, s in enumerate(cpu_load_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect CPU load sensor(s) (1-{min(len(cpu_load_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(cpu_load_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['cpu_load'] = cpu_load_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {cpu_load_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {cpu_load_sensors[idx]['label']}")
    else:
        print("  No CPU load sensors found")
    
    # GPU Temperature
    print("\n[3] GPU Temperature")
    print("-" * 50)
    gpu_temp_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['gpu', 'graphics', 'video', 'vga'])
    
    if gpu_temp_sensors:
        for i, s in enumerate(gpu_temp_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect GPU temp sensor(s) (1-{min(len(gpu_temp_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(gpu_temp_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['gpu_temp'] = gpu_temp_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {gpu_temp_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {gpu_temp_sensors[idx]['label']}")
    else:
        print("  No GPU temperature sensors found")
    
    # GPU Load
    print("\n[4] GPU Load/Usage")
    print("-" * 50)
    gpu_load_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['gpu utilization', 'gpu d3d usage', 'gpu core load', 'gpu load', 'gpu activity'])
    
    gpu_load_sensors = [s for s in gpu_load_sensors if 'memory' not in s['label'].lower()]
    
    if gpu_load_sensors:
        for i, s in enumerate(gpu_load_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect GPU load sensor(s) (1-{min(len(gpu_load_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(gpu_load_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['gpu_load'] = gpu_load_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {gpu_load_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {gpu_load_sensors[idx]['label']}")
    else:
        print("  No GPU load sensors found")
    
    # GPU Memory
    print("\n[5] GPU Memory Usage (Optional)")
    print("-" * 50)
    gpu_mem_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['gpu memory', 'vram', 'dedicated'])
    
    gpu_mem_sensors = [s for s in gpu_mem_sensors 
                       if '%' in s['unit'] 
                       and 'thermal' not in s['label'].lower()
                       and 'limit' not in s['label'].lower()]
    
    if gpu_mem_sensors:
        for i, s in enumerate(gpu_mem_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect GPU memory sensor(s) (1-{min(len(gpu_mem_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(gpu_mem_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['gpu_memory'] = gpu_mem_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {gpu_mem_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {gpu_mem_sensors[idx]['label']}")
    
    # RAM Temperature
    print("\n[6] RAM Temperature (Optional)")
    print("-" * 50)
    ram_temp_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['dimm', 'dram', 'memory temperature'])
    
    ram_temp_sensors = [s for s in ram_temp_sensors 
                        if ('C' in s['unit'] or '°' in s['unit'])
                        and 'gpu' not in s['label'].lower()
                        and 'graphics' not in s['label'].lower()
                        and 'video' not in s['label'].lower()]
    
    if ram_temp_sensors:
        for i, s in enumerate(ram_temp_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect RAM temp sensor(s) (1-{min(len(ram_temp_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(ram_temp_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['ram_temp'] = ram_temp_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {ram_temp_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {ram_temp_sensors[idx]['label']}")
    else:
        print("  No RAM temperature sensors found")
    
    # RAM Usage
    print("\n[7] RAM Usage (Optional)")
    print("-" * 50)
    ram_usage_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['physical memory', 'virtual memory', 'memory committed', 'memory available'])
    
    ram_usage_sensors = [s for s in ram_usage_sensors 
                         if ('MB' in s['unit'] or 'GB' in s['unit'] or '%' in s['unit'])
                         and 'gpu' not in s['label'].lower()
                         and 'graphics' not in s['label'].lower()
                         and 'video' not in s['label'].lower()]
    
    if ram_usage_sensors:
        for i, s in enumerate(ram_usage_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect RAM usage sensor(s) (1-{min(len(ram_usage_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(ram_usage_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['ram_usage'] = ram_usage_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {ram_usage_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {ram_usage_sensors[idx]['label']}")
    else:
        print("  No RAM usage sensors found")
    
    # Motherboard Temperature
    print("\n[8] Motherboard Temperature (Optional)")
    print("-" * 50)
    mb_temp_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['motherboard', 'mainboard', 'chipset', 'vrm'])
    
    mb_temp_sensors = [s for s in mb_temp_sensors 
                       if 'C' in s['unit'] or '°' in s['unit'] or 'temp' in s['label'].lower()]
    
    if mb_temp_sensors:
        for i, s in enumerate(mb_temp_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect MB temp sensor(s) (1-{min(len(mb_temp_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(mb_temp_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['mb_temp'] = mb_temp_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {mb_temp_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {mb_temp_sensors[idx]['label']}")
    else:
        print("  No motherboard temperature sensors found")
    
    # NVMe/SSD Temperature
    print("\n[9] Storage Temperature (Optional)")
    print("-" * 50)
    nvme_temp_sensors = find_sensor_by_keywords(hwinfo_instance,
        ['nvme', 'ssd', 'drive', 'disk'])
    
    nvme_temp_sensors = [s for s in nvme_temp_sensors 
                         if 'C' in s['unit'] or '°' in s['unit'] or 'temp' in s['label'].lower()]
    
    if nvme_temp_sensors:
        for i, s in enumerate(nvme_temp_sensors[:10]):
            print(f"  [{i+1}] {s['label']}: {format_sensor_value(s['value'])} {s['unit']}")
        
        choice = input(f"\nSelect storage temp sensor(s) (1-{min(len(nvme_temp_sensors), 10)}, or Enter to skip): ")
        selected_indices = parse_selection(choice, min(len(nvme_temp_sensors), 10))
        
        if selected_indices:
            SENSOR_IDS['nvme_temp'] = nvme_temp_sensors[selected_indices[0]]['id']
            print(f"✓[OK] Selected: {nvme_temp_sensors[selected_indices[0]]['label']}")
            
            if len(selected_indices) > 1:
                print(f"  Additional sensors selected: {len(selected_indices) - 1}")
                for idx in selected_indices[1:]:
                    print(f"    - {nvme_temp_sensors[idx]['label']}")
    else:
        print("  No storage temperature sensors found")
    
    print("\n[OK] Sensor selection complete!")
    print("\nYou can reconfigure sensors by deleting:", CONFIG_FILE)
    
    save_config()

def get_sensor_value(sensor_id):
    """Get current value from a sensor by ID"""
    global hwinfo
    
    if sensor_id is None or hwinfo is None:
        return 0
    
    try:
        sensor = hwinfo.get_sensor_by_id(sensor_id)
        if sensor:
            return int(float(sensor.value))
    except (ValueError, AttributeError):
        pass
    
    return 0

def discover_gamesense_server():
    """Discover GameSense server address from SteelSeries Engine or GG"""
    try:
        possible_paths = [
            os.path.expandvars(r"%PROGRAMDATA%\SteelSeries\SteelSeries Engine 3\coreProps.json"),
            os.path.expandvars(r"%PROGRAMDATA%\SteelSeries\GG\coreProps.json"),
            os.path.expanduser(r"~\AppData\Roaming\SteelSeries\SteelSeries Engine 3\coreProps.json"),
            "coreProps.json"
        ]
        
        test_addresses = []
        
        for props_path in possible_paths:
            if os.path.exists(props_path):
                print(f"Found coreProps.json at: {props_path}")
                with open(props_path, 'r', encoding='utf-8') as f:
                    core_props = json.load(f)
                
                if 'address' in core_props:
                    address = core_props['address']
                    app_type = "SteelSeries Engine 3" if "Engine 3" in props_path else "SteelSeries GG"
                    test_addresses.append((f"http://{address}", app_type))
                
                if 'encryptedAddress' in core_props:
                    address = core_props['encryptedAddress']
                    app_type = "SteelSeries Engine 3 (encrypted)" if "Engine 3" in props_path else "SteelSeries GG (encrypted)"
                    test_addresses.append((f"http://{address}", app_type))
                
                if 'ggEncryptedAddress' in core_props:
                    address = core_props['ggEncryptedAddress']
                    test_addresses.append((f"http://{address}", "SteelSeries GG (encrypted)"))
        
        common_ports = [
            ("http://127.0.0.1:50647", "Common Engine 3 Port"),
            ("http://127.0.0.1:51765", "Common Engine App Port"),
            ("http://127.0.0.1:3001", "Engine App Localhost")
        ]
        test_addresses.extend(common_ports)
        
        for server_url, app_type in test_addresses:
            try:
                print(f"Testing GameSense at {server_url} ({app_type})...")
                response = requests.get(f"{server_url}/game_metadata", timeout=2)
                if response.status_code in [200, 405]:
                    print(f"SUCCESS: GameSense server discovered at {server_url} ({app_type})")
                    return server_url
            except requests.exceptions.RequestException as e:
                print(f"  Connection failed: {e}")
                continue
        
        print("ERROR: No responding GameSense server found")
        return None
        
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: Error discovering GameSense server: {e}")
        return None


def get_hwinfo_sensor_data():
    """Get latest sensor data from HWiNFO shared memory"""
    global hwinfo
    
    if hwinfo is None:
        return None
    
    try:
        cpu_temp = get_sensor_value(SENSOR_IDS['cpu_temp'])
        
        cpu_load_raw = get_sensor_value(SENSOR_IDS['cpu_load'])
        if cpu_load_raw > 0:
            cpu_load_history.append(cpu_load_raw)
            if len(cpu_load_history) >= 3:
                weights = [1, 2, 3, 4, 5]
                recent_values = list(cpu_load_history)[-5:]
                weighted_sum = sum(val * weights[i] for i, val in enumerate(recent_values))
                weight_total = sum(weights[:len(recent_values)])
                cpu_load = weighted_sum // weight_total
            else:
                cpu_load = cpu_load_raw
        else:
            cpu_load = 0
        
        gpu_temp = get_sensor_value(SENSOR_IDS['gpu_temp'])
        
        gpu_load_raw = get_sensor_value(SENSOR_IDS['gpu_load'])
        if gpu_load_raw > 0:
            if gpu_load_history:
                last_avg = sum(gpu_load_history) // len(gpu_load_history)
                if gpu_load_raw < last_avg - 3:
                    gpu_load_history.clear()
            
            gpu_load_history.append(gpu_load_raw)
            if len(gpu_load_history) >= 3:
                weights = [1, 2, 3, 4, 5]
                recent_values = list(gpu_load_history)[-5:]
                weighted_sum = sum(val * weights[i] for i, val in enumerate(recent_values))
                weight_total = sum(weights[:len(recent_values)])
                gpu_load = weighted_sum // weight_total
            else:
                gpu_load = gpu_load_raw
        else:
            gpu_load = 0
        
        gpu_memory = get_sensor_value(SENSOR_IDS['gpu_memory'])
        
        ram_usage = get_sensor_value(SENSOR_IDS['ram_usage'])
        if ram_usage == 0:
            ram_load = int(psutil.virtual_memory().percent)
        else:
            ram_load = int(psutil.virtual_memory().percent)
        
        ram_temp = get_sensor_value(SENSOR_IDS['ram_temp'])
        mb_temp = get_sensor_value(SENSOR_IDS['mb_temp'])
        nvme_temp = get_sensor_value(SENSOR_IDS['nvme_temp'])
        
        return {
            'cpu_temp': cpu_temp,
            'cpu_load': cpu_load,
            'gpu_temp': gpu_temp,
            'gpu_load': gpu_load,
            'gpu_memory': gpu_memory,
            'ram_load': ram_load,
            'ram_usage': ram_usage,
            'ram_temp': ram_temp,
            'mb_temp': mb_temp,
            'nvme_temp': nvme_temp
        }
        
    except Exception as e:
        print(f"Error reading HWiNFO data: {e}")
        return None


def get_display_data(sensor_data, update_count):
    """Generate display data for current mode"""
    current_time = datetime.now().strftime("%H:%M:%S")
    
    if not sensor_data:
        return {
            "line1": f"HWiNFO Monitor #{update_count}",
            "line2": f"No Data - {current_time}"
        }
    
    cpu_temp = sensor_data.get('cpu_temp', 0)
    cpu_load = sensor_data.get('cpu_load', 0)
    gpu_temp = sensor_data.get('gpu_temp', 0)
    gpu_load = sensor_data.get('gpu_load', 0)
    gpu_memory = sensor_data.get('gpu_memory', 0)
    ram_load = sensor_data.get('ram_load', 0)
    ram_usage = sensor_data.get('ram_usage', 0)
    ram_temp = sensor_data.get('ram_temp', 0)
    mb_temp = sensor_data.get('mb_temp', 0)
    nvme_temp = sensor_data.get('nvme_temp', 0)
    
    display_mode = update_count % NUM_DISPLAY_MODES
    
    if display_mode == 0:
        return {
            "line1": f"CPU: {cpu_load}%",
            "line2": f"GPU: {gpu_load}%"
        }
    
    elif display_mode == 1:
        return {
            "line1": f"CPU: {cpu_temp}°C",
            "line2": f"Load: {cpu_load}%"
        }
    
    elif display_mode == 2:
        if gpu_temp > 0 or gpu_load > 0:
            return {
                "line1": f"GPU: {gpu_temp}°C",
                "line2": f"Load: {gpu_load}%"
            }
        else:
            return {
                "line1": "GPU: No Data",
                "line2": "Check HWiNFO sensors"
            }
    
    elif display_mode == 3:
        if ram_temp > 0:
            return {
                "line1": f"RAM: {ram_load}%",
                "line2": f"Temp: {ram_temp}°C"
            }
        elif gpu_memory > 0:
            return {
                "line1": f"RAM: {ram_load}%",
                "line2": f"GPU Mem: {gpu_memory}%"
            }
        elif ram_usage > 0:
            # Format RAM usage (convert MB to GB if needed)
            if ram_usage >= 1024:
                ram_gb = ram_usage / 1024
                return {
                    "line1": f"RAM: {ram_load}%",
                    "line2": f"Used: {ram_gb:.1f} GB"
                }
            else:
                return {
                    "line1": f"RAM: {ram_load}%",
                    "line2": f"Used: {int(ram_usage)} MB"
                }
        else:
            return {
                "line1": f"RAM: {ram_load}%",
                "line2": "Memory Load"
            }
    
    elif display_mode == 4:
        temps = []
        if cpu_temp > 0:
            temps.append(f"CPU:{cpu_temp}°")
        if gpu_temp > 0:
            temps.append(f"GPU:{gpu_temp}°")
        
        if len(temps) >= 2:
            return {
                "line1": temps[0],
                "line2": temps[1]
            }
        elif len(temps) == 1:
            return {
                "line1": temps[0],
                "line2": f"RAM: {ram_load}%"
            }
        else:
            return {
                "line1": "No Temp Data",
                "line2": f"RAM: {ram_load}%"
            }
    
    else:
        day_of_week = datetime.now().strftime("%a")
        
        if nvme_temp > 0:
            extra_info = f"SSD: {nvme_temp}°C"
        elif mb_temp > 0:
            extra_info = f"MB: {mb_temp}°C"
        else:
            extra_info = f"RAM: {ram_load}%"
        
        return {
            "line1": f"{day_of_week} {current_time}",
            "line2": extra_info
        }

def register_game_and_handlers(gamesense_url, game_name):
    """Register the game and OLED display handlers"""
    try:
        bind_payload = {
            "game": game_name,
            "event": "SYSTEM_STATS",
            "min_value": 0,
            "max_value": 100,
            "icon_id": 15,
            "value_optional": True,
            "handlers": [
                {
                    "device-type": "screened",
                    "zone": "one", 
                    "mode": "screen",
                    "datas": [
                        {
                            "lines": [
                                {
                                    "has-text": True,
                                    "context-frame-key": "line1"
                                },
                                {
                                    "has-text": True, 
                                    "context-frame-key": "line2"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(f"{gamesense_url}/bind_game_event", json=bind_payload, timeout=5)
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Handler registration failed: {e}")
        return False

def send_display_update(gamesense_url, game_name, line1, line2, update_count):
    """Send update to GameSense OLED display"""
    payload = {
        "game": game_name,
        "event": "SYSTEM_STATS",
        "data": {
            "value": update_count,
            "frame": {
                "line1": line1,
                "line2": line2
            }
        }
    }
    
    try:
        response = requests.post(f"{gamesense_url}/game_event", json=payload, timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def main():
    """Main monitoring loop"""
    global hwinfo
    
    print("=" * 70)
    print("HWiNFO OLED SYSTEM MONITOR")
    print("SteelSeries GameSense Integration")
    print("=" * 70)
    print()
    
    print("Connecting to HWiNFO shared memory...")
    try:
        hwinfo = HWiNFO()
        print(f"✓ Connected to HWiNFO (Version: {hwinfo.version})")
        print(f"  Found {len(list(hwinfo.iter_sensors()))} sensors")
    except Exception as e:
        print(f"ERROR: Could not connect to HWiNFO shared memory: {e}")
        print()
        print("Setup Instructions:")
        print("1. Open HWiNFO64 Settings → General")
        print("2. Enable 'Shared Memory Support'")
        print("3. Restart HWiNFO64 (important!)")
        print("4. Make sure HWiNFO64 is running in the background")
        print()
        input("Press Enter to exit...")
        return
    
    print()
    
    config_exists = os.path.exists(CONFIG_FILE)
    
    if config_exists:
        print(f"Found existing configuration: {CONFIG_FILE}")
        print()
        choice = input("Use existing configuration? (Y/n): ").strip().lower()
        
        if choice in ['n', 'no']:
            print(f"Deleting {CONFIG_FILE}...")
            try:
                os.remove(CONFIG_FILE)
                config_exists = False
                print("[OK] Configuration deleted. Starting fresh setup...")
            except OSError as e:
                print(f"Warning: Could not delete config file: {e}")
        else:
            print("[OK] Using existing configuration...")
            config_exists = load_config()
    else:
        config_exists = False
    
    if not config_exists or all(v is None for v in SENSOR_IDS.values()):
        print("\nNo configuration found. Running sensor selection wizard...")
        interactive_sensor_selection(hwinfo)
    else:
        print("\nTo reconfigure, restart and choose 'n' when prompted.")
        print(f"Or manually delete: {CONFIG_FILE}")
    
    print()
    
    print("Discovering GameSense server...")
    gamesense_url = discover_gamesense_server()
    
    if not gamesense_url:
        print("WARNING: GameSense server not found. Running in console-only mode.")
        print("   To enable OLED display:")
        print("   1. Make sure SteelSeries Engine is running")
        print("   2. Connect your SteelSeries OLED device")
        print("   3. Restart this script")
        print()
        console_only_mode = True
    else:
        console_only_mode = False
    
    game_name = "HWINFO-SYSTEM-MONITOR"
    
    if not console_only_mode:
        print("Registering GameSense handlers...")
        if not register_game_and_handlers(gamesense_url, game_name):
            print("ERROR: Failed to register GameSense handlers!")
            print("   Switching to console-only mode")
            console_only_mode = True
        else:
            print("SUCCESS: GameSense handlers registered successfully!")
    
    print()
    print(f"{NUM_DISPLAY_MODES} Display Modes (cycling every {UPDATE_INTERVAL}s):")
    print("   0: System Overview (CPU/GPU Load %)")
    print("   1: CPU Details (Temp + Load)")
    print("   2: GPU Details (Temp + Load)")
    print("   3: Memory Stats (RAM + GPU Memory)")
    print("   4: Temperature Overview")
    print("   5: Time + Extra Info (Storage/MB temp)")
    print()
    
    if console_only_mode:
        print("Console Mode: Data displayed here only")
    else:
        print("GameDAC Mode: Data sent to OLED display")
    
    print(f"Updates every {UPDATE_INTERVAL} seconds with cycling layouts")
    print("Press Ctrl+C to stop")
    print()
    
    update_count = 0
    last_data = None
    
    try:
        while True:
            update_count += 1
            
            sensor_data = get_hwinfo_sensor_data()
            
            display_data = get_display_data(sensor_data, update_count)
            line1 = display_data["line1"]
            line2 = display_data["line2"]
            
            if not console_only_mode:
                success = send_display_update(gamesense_url, game_name, line1, line2, update_count)
            else:
                success = True
            
            current_data = (line1, line2)
            changed = current_data != last_data
            last_data = current_data
            
            mode_names = ["SysOverview", "CPU Detail", "GPU Detail", "Memory", "Temps", "Time/Info"]
            mode_name = mode_names[update_count % NUM_DISPLAY_MODES]
            
            if success:
                status = "NEW" if changed else "UPD"
                display_prefix = "[OLED]" if not console_only_mode else "[CONSOLE]"
                print(f"Update {update_count:3d}: {status} [{mode_name:>11}] {display_prefix} {line1}")
                print(f"             {'':>15} {'':>5} {line2}")
            else:
                print(f"Update {update_count:3d}: FAIL [{mode_name:>11}] | {line1}")
                if update_count % 10 == 0:
                    print("             Attempting handler re-registration...")
                    if not register_game_and_handlers(gamesense_url, game_name):
                        print("             WARNING: Switching to console-only mode")
                        console_only_mode = True
            
            if not console_only_mode and update_count % 10 == 0:
                try:
                    heartbeat_payload = {"game": game_name}
                    requests.post(f"{gamesense_url}/game_heartbeat", 
                                 json=heartbeat_payload, timeout=1)
                except requests.exceptions.RequestException:
                    pass
            
            print()
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        print(f"Final update count: {update_count}")
        
        if not console_only_mode:
            try:
                cleanup_payload = {"game": game_name}
                requests.post(f"{gamesense_url}/remove_game", json=cleanup_payload, timeout=2)
                print("GameSense registration cleaned up")
            except requests.exceptions.RequestException:
                pass

if __name__ == "__main__":
    main()
