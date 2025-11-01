"""
pywhinfo - Python wrapper for HWiNFO Shared Memory
Based on reverse-engineered HWiNFO shared memory format
Source: https://gist.github.com/namazso/0c37be5a53863954c8c8279f66cfb1cc
"""

import ctypes
import ctypes.wintypes
from enum import IntEnum
from typing import Iterator, Optional

# Constants from HWiNFO
HWINFO_SHARED_MEM_PATH = "Global\\HWiNFO_SENS_SM2"
HWINFO_SHARED_MEM_MUTEX = "Global\\HWiNFO_SM2_MUTEX"
HWINFO_HEADER_MAGIC = 0x53695748 


class SensorType(IntEnum):
    SENSOR_TYPE_NONE = 0
    SENSOR_TYPE_TEMP = 1
    SENSOR_TYPE_VOLT = 2
    SENSOR_TYPE_FAN = 3
    SENSOR_TYPE_CURRENT = 4
    SENSOR_TYPE_POWER = 5
    SENSOR_TYPE_CLOCK = 6
    SENSOR_TYPE_USAGE = 7
    SENSOR_TYPE_OTHER = 8


class HWiNFOHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('magic', ctypes.c_uint32),             
        ('version', ctypes.c_uint32),         
        ('version2', ctypes.c_uint32),          
        ('last_update', ctypes.c_int64),       
        ('sensor_section_offset', ctypes.c_uint32),   
        ('sensor_element_size', ctypes.c_uint32),     
        ('sensor_element_count', ctypes.c_uint32),    
        ('entry_section_offset', ctypes.c_uint32),    
        ('entry_element_size', ctypes.c_uint32),     
        ('entry_element_count', ctypes.c_uint32),     
    ]


class HWiNFOSensor(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('id', ctypes.c_uint32),                
        ('instance', ctypes.c_uint32),          
        ('name_original', ctypes.c_char * 128),  
        ('name_user', ctypes.c_char * 128),      
    ]


class HWiNFOEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('type', ctypes.c_uint32),              
        ('sensor_index', ctypes.c_uint32),      
        ('id', ctypes.c_uint32),                 
        ('name_original', ctypes.c_char * 128), 
        ('name_user', ctypes.c_char * 128),      
        ('unit', ctypes.c_char * 16),           
        ('value', ctypes.c_double),              
        ('value_min', ctypes.c_double),          
        ('value_max', ctypes.c_double),          
        ('value_avg', ctypes.c_double),         
    ]


class Sensor:
    
    def __init__(self, entry: HWiNFOEntry):
        self.sensor_type = entry.type
        self.sensor_index = entry.sensor_index
        self.id = entry.id
        self.label_original = entry.name_original.decode('utf-8', errors='ignore').strip('\x00')
        self.label_user = entry.name_user.decode('utf-8', errors='ignore').strip('\x00')
        self.unit = entry.unit.decode('utf-8', errors='ignore').strip('\x00')
        self.value = entry.value
        self.value_min = entry.value_min
        self.value_max = entry.value_max
        self.value_avg = entry.value_avg
    
    @property
    def label(self) -> str:
        return self.label_user if self.label_user else self.label_original
    
    def __repr__(self):
        return f"<Sensor #{self.id}: {self.label} = {self.value} {self.unit}>"


class HWiNFO:
    
    def __init__(self):
        self.mmap = None
        self.header = None
        self._connect()
    
    def _connect(self):
        self._handle = None
        self._ptr = None
        self.header = None
        
        try:
            kernel32 = ctypes.windll.kernel32
            
            kernel32.OpenFileMappingW.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.LPCWSTR]
            kernel32.OpenFileMappingW.restype = ctypes.wintypes.HANDLE
            
            kernel32.MapViewOfFile.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.c_size_t]
            kernel32.MapViewOfFile.restype = ctypes.c_void_p
            
            handle = kernel32.OpenFileMappingW(
                0x0004, 
                False,
                HWINFO_SHARED_MEM_PATH
            )
            
            if not handle or handle == -1:
                error_code = ctypes.get_last_error()
                raise RuntimeError(
                    f"Cannot open HWiNFO shared memory (Error code: {error_code}). "
                    "Make sure HWiNFO is running with 'Shared Memory Support' enabled."
                )
            
            ptr = kernel32.MapViewOfFile(
                handle,
                0x0004,  
                0,
                0,
                0
            )
            
            if not ptr:
                error_code = ctypes.get_last_error()
                kernel32.CloseHandle(handle)
                raise RuntimeError(f"Cannot map HWiNFO shared memory view (Error code: {error_code})")
            
            self._handle = handle
            self._ptr = ptr
            
            self.header = HWiNFOHeader.from_address(ptr)
            
            if self.header.magic != HWINFO_HEADER_MAGIC:
                raise RuntimeError(
                    f"Invalid HWiNFO header magic: 0x{self.header.magic:08X} "
                    f"(expected 0x{HWINFO_HEADER_MAGIC:08X})"
                )
            
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to connect to HWiNFO: {e}") from e
    
    @property
    def version(self) -> str:
        if self.header:
            return f"{self.header.version}.{self.header.version2}"
        return "Unknown"
    
    def iter_sensors(self) -> Iterator[Sensor]:
        if not self.header:
            return
        
        entry_base = self._ptr + self.header.entry_section_offset
        
        for i in range(self.header.entry_element_count):
            entry_addr = entry_base + (i * self.header.entry_element_size)
            entry = HWiNFOEntry.from_address(entry_addr)
            
            if entry.type == SensorType.SENSOR_TYPE_NONE:
                continue
            
            yield Sensor(entry)
    
    def get_sensor_by_id(self, sensor_id: int) -> Optional[Sensor]:
        if sensor_id is None:
            return None
        
        for sensor in self.iter_sensors():
            if sensor.id == sensor_id:
                return sensor
        
        return None
    
    def close(self):
        if hasattr(self, '_ptr') and self._ptr:
            ctypes.windll.kernel32.UnmapViewOfFile(ctypes.c_void_p(self._ptr))
            self._ptr = None
        
        if hasattr(self, '_handle') and self._handle:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None
    
    def __del__(self):
        self.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    print("Testing HWiNFO shared memory connection...")
    print()
    
    try:
        hwinfo = HWiNFO()
        print(f"✓ Connected to HWiNFO (Version: {hwinfo.version})")
        print()
        
        sensors = list(hwinfo.iter_sensors())
        print(f"Found {len(sensors)} sensors:")
        print()
        
        by_type = {}
        for sensor in sensors:
            type_name = SensorType(sensor.sensor_type).name
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(sensor)
        
        for type_name, type_sensors in sorted(by_type.items()):
            print(f"\n{type_name}:")
            print("-" * 70)
            for sensor in type_sensors[:10]:  # Show max 10 per type
                print(f"  ID {sensor.id:5d}: {sensor.label:40s} = {sensor.value:8.2f} {sensor.unit}")
        
        hwinfo.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        print("Make sure:")
        print("1. HWiNFO64 is running")
        print("2. 'Shared Memory Support' is enabled in HWiNFO Settings → General/User Interface")
        print("3. HWiNFO was restarted after enabling shared memory")