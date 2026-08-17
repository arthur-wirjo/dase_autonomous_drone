import serial
import struct
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

class low_pass_filter:
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self.filtered_value = None

    def update(self, raw_value):
        if self.filtered_value == None:
            self.filtered_value = raw_value
        else:
            self.filtered_value = (self.alpha * raw_value) + ((1.0 - self.alpha) * self.filtered_value)
        return self.filtered_value

def main():
    filters = {1: low_pass_filter(alpha=0.15), 
               2: low_pass_filter(alpha=0.15),
               3: low_pass_filter(alpha=0.15),
               4: low_pass_filter(alpha=0.15)}

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"listening to serial port {SERIAL_PORT}")

        buffer = bytearray()

        while True:
            if ser.in_waiting > 0:
                buffer += ser.read(ser.in_waiting)

                header_idx = buffer.find(b'CmdM:4')

                # full packet is 98 bytes long
                if header_idx != -1 and len(buffer) >= header_idx + 98:
                    packet = buffer[header_idx : header_idx + 98]
                    buffer = buffer[header_idx + 98 :]

                    # raw distances for anchor 0-7 are located at byte offset 17
                    # 8 anchors * 4 bytes per integer = 32 byte chunk
                    raw_ranges_bytes = packet[17:49]

                    try:
                        # unpack 32 byte chunk to 8 little-endian 32-bit integers
                        ranges_mm = struct.unpack('<8i', raw_ranges_bytes)
                        output_str = ""
                        for anchor_id in range(1, 5):
                            raw_m = ranges_mm[anchor_id] / 1000.0 # convert milimeter to meters
                            if raw_m > 0:
                                filtered_m = filters[anchor_id].update(raw_m)
                                output_str += f"A{anchor_id} [Raw: {raw_m:.2f}m | Filtered: {filtered_m:.2f}m]\n"
                        if output_str:
                            print(output_str + "\n")
                    except struct.error:
                        pass 

                # prevent buffer from overflowing if data corrupted
                if len(buffer) > 500:
                    buffer = buffer[-250:]

    except KeyboardInterrupt:
        print("\nbye :)")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    main()                
