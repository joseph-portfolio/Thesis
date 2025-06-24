"""
GPS Location Reader for Neo6M module
Reads NMEA data from serial port and extracts latitude/longitude
"""

import serial
import time
import re
import sys

def parse_gprmc(nmea_sentence):
    """
    Parse GPRMC (Recommended Minimum) sentence
    Format: $GPRMC,time,status,lat,lat_dir,lon,lon_dir,speed,course,date,mag_var,mag_var_dir,checksum
    """
    parts = nmea_sentence.split(',')
    
    if len(parts) < 12 or parts[2] != 'A':  # 'A' means valid fix
        return None
    
    try:
        # Parse latitude (DDMM.MMMM format)
        lat_raw = float(parts[3])
        lat_deg = int(lat_raw / 100)
        lat_min = lat_raw - (lat_deg * 100)
        latitude = lat_deg + (lat_min / 60)
        if parts[4] == 'S':
            latitude = -latitude
        
        # Parse longitude (DDDMM.MMMM format)
        lon_raw = float(parts[5])
        lon_deg = int(lon_raw / 100)
        lon_min = lon_raw - (lon_deg * 100)
        longitude = lon_deg + (lon_min / 60)
        if parts[6] == 'W':
            longitude = -longitude
        
        return latitude, longitude
    except (ValueError, IndexError):
        return None

def parse_gpgga(nmea_sentence):
    """
    Parse GPGGA (Global Positioning System Fix Data) sentence
    Format: $GPGGA,time,lat,lat_dir,lon,lon_dir,quality,satellites,hdop,altitude,alt_unit,geoid_height,geoid_unit,dgps_time,dgps_id,checksum
    """
    parts = nmea_sentence.split(',')
    
    if len(parts) < 15 or parts[6] == '0':  # Quality 0 means no fix
        return None
    
    try:
        # Parse latitude (DDMM.MMMM format)
        lat_raw = float(parts[2])
        lat_deg = int(lat_raw / 100)
        lat_min = lat_raw - (lat_deg * 100)
        latitude = lat_deg + (lat_min / 60)
        if parts[3] == 'S':
            latitude = -latitude
        
        # Parse longitude (DDDMM.MMMM format)
        lon_raw = float(parts[4])
        lon_deg = int(lon_raw / 100)
        lon_min = lon_raw - (lon_deg * 100)
        longitude = lon_deg + (lon_min / 60)
        if parts[5] == 'W':
            longitude = -longitude
        
        return latitude, longitude
    except (ValueError, IndexError):
        return None

def get_location(port='/dev/serial0', baudrate=9600, timeout_seconds=60):
    """
    Get GPS location from Neo6M module
    
    Args:
        port: Serial port device (default: /dev/serial0)
        baudrate: Baud rate (default: 9600)
        timeout_seconds: Maximum time to wait for a GPS fix (default: 60 seconds)
    
    Returns:
        tuple: (latitude, longitude) when GPS fix is obtained, or None if no fix is obtained
    """
    ser = None
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        print(f"Reading GPS data from {port}...")
        print("Waiting for GPS fix... (this may take a few minutes)")
        print("Press Ctrl+C to stop")
        
        start_time = time.time()
        
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                print(f"Timeout reached ({timeout_seconds} seconds). No GPS fix obtained.")
                break
            try:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line.startswith('$GPRMC'):
                    result = parse_gprmc(line)
                    if result:
                        return result
                elif line.startswith('$GPGGA'):
                    result = parse_gpgga(line)
                    if result:
                        return result
                # Show some activity
                if line.startswith('$'):
                    print(f"Received: {line[:20]}...")
            except UnicodeDecodeError:
                continue
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        return None
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return None
    finally:
        if ser:
            ser.close()
    return None

def main():
    print("Neo6M GPS Location Reader")
    print("=" * 30)
    
    # Get location
    location = get_location()
    
    if location:
        latitude, longitude = location
        print(f"\n✓ GPS Fix Acquired!")
        print(f"Latitude:  {latitude:.6f}")
        print(f"Longitude: {longitude:.6f}")
        print(f"\nGoogle Maps link:")
        print(f"https://www.google.com/maps?q={latitude},{longitude}")
        return latitude, longitude
    else:
        print("\n✗ Interrupted by user")
        return None

if __name__ == "__main__":
    main()