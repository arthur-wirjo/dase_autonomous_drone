import serial

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

try:
    # timeout=1 ensures it doesn't block forever if no data arrives
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Sniffing raw data on {SERIAL_PORT} at {BAUD_RATE} baud...")
    print("Waiting for data...\n")
    
    while True:
        if ser.in_waiting > 0:
            raw_data = ser.read(ser.in_waiting)
            # Print the raw bytes exactly as they arrive
            print(raw_data)
            
except KeyboardInterrupt:
    print("\nbye :)")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
