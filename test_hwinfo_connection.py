"""
Quick test script to verify HWiNFO connection and basic functionality
"""

import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    try:
        import requests
        print("  ✓ requests")
    except ImportError:
        print("  ✗ requests - install with: pip install requests")
        return False
    
    try:
        import psutil
        print("  ✓ psutil")
    except ImportError:
        print("  ✗ psutil - install with: pip install psutil")
        return False
    
    try:
        from pywhinfo import HWiNFO
        print("  ✓ pywhinfo (local module)")
    except ImportError:
        print("  ✗ pywhinfo.py not found in current directory")
        return False
    
    print()
    return True

def test_hwinfo_connection():
    """Test connection to HWiNFO shared memory"""
    print("Testing HWiNFO connection...")
    try:
        from pywhinfo import HWiNFO
        
        hwinfo = HWiNFO()
        print(f"  ✓ Connected to HWiNFO (Version: {hwinfo.version})")
        
        sensors = list(hwinfo.iter_sensors())
        print(f"  ✓ Found {len(sensors)} sensors")
        
        if sensors:
            print(f"\n  Sample sensors:")
            for sensor in sensors[:5]:
                print(f"    - {sensor.label}: {sensor.value} {sensor.unit}")
        
        hwinfo.close()
        print()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        print()
        print("  Make sure:")
        print("    1. HWiNFO64 is running")
        print("    2. 'Shared Memory Support' is enabled (Settings → General)")
        print("    3. HWiNFO was restarted after enabling shared memory")
        print()
        return False

def test_psutil():
    """Test psutil functionality"""
    print("Testing psutil...")
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        print(f"  ✓ CPU Usage: {cpu_percent}%")
        print(f"  ✓ RAM Usage: {memory.percent}%")
        print()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print()
        return False

def main():
    print("=" * 70)
    print("HWiNFO OLED Monitor - Connectivity Test")
    print("=" * 70)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    
    results.append(("HWiNFO Connection", test_hwinfo_connection()))
    
    results.append(("System Info (psutil)", test_psutil()))
    
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {test_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✓ All tests passed! You're ready to run hwinfo_oled_monitor.py")
    else:
        print("✗ Some tests failed. Please fix the issues above before running the monitor.")
    
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
