import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleOdometry
import serial
import struct
import numpy as np
from scipy.optimize import minimize
import threading
import math

class EMAFilter:
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self.filtered_value = None

    def update(self, raw_value):
        if self.filtered_value is None:
            self.filtered_value = raw_value
        else:
            self.filtered_value = (raw_value * self.alpha) + (self.filtered_value * (1 - self.alpha))
        return self.filtered_value

class UWBLocalizationNode(Node):
    def __init__(self):
        super().__init__('uwb_localization_node')

        self.serial_port = '/dev/ttyACM0'
        self.baud_rate = 115200

        # Anchor coordinate in ENU: X = right, Y = forward, Z = up
        self.ANCHORS_ENU = {
            1: np.array([-1.5, -1.5, 0]), # bottom left
            2: np.array([1.5, -1.5, 0]), # bottom right
            3: np.array([-1.5, 1.5, 1.94]), # top left
            4: np.array([1.5, 1.435, 1.84]) # top right
        } 

        self.filters = {
            1: EMAFilter(alpha=0.15),
            2: EMAFilter(alpha=0.15),
            3: EMAFilter(alpha=0.15),
            4: EMAFilter(alpha=0.15)
        }

        self.latest_distances = {
            1: None,
            2: None,
            3: None,
            4: None
        }

        self.last_known_pos = np.array([0.0, 0.0, 0.1])

        self.odom_pub = self.create_publisher(VehicleOdometry, '/fmu/in/vehicle_visual_odometry', 10)

        self.serial_thread = threading.Thread(target=self.read_serial_data)
        self.serial_thread.daemon = True
        self.serial_thread.start()

    def calculate_position(self):
        if any(d is None for d in self.latest_distances.values()):
            self.get_logger().error("some anchors are not connected")
            return None

        def error_function(target_pos):
            error = 0
            for anchor_id, anchor_coords in self.ANCHORS_ENU.items():
                calc_distance = np.linalg.norm(target_pos - anchor_coords)
                error += (calc_distance - self.latest_distances[anchor_id])**2
            return error

        bounds = ((None, None), (None, None), (0.0, None))

        # run optimizer
        result = minimize(
            error_function,
            self.last_known_pos,
            method='L-BFGS-B',
            bounds=bounds
        )

        if result.success:
            self.last_known_pos = result.x
            return result.x
        return None

    def publish_to_px4(self, pos_enu):
        msg = VehicleOdometry()

        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        msg.timestamp_sample = msg.timestamp

        # NED frame
        msg.pose_frame = 1

        # convert ENU to NED coordinates
        msg.position = [
            float(pos_enu[1]), # X_NED = Y_ENU
            float(pos_enu[0]), # Y_NED = X_ENU
            float(-pos_enu[2]), # Z_NED = -Z_ENU
        ]

        # no orientation so set quaternions to NaN so EKF ignore them
        msg.q = [float('nan'), float('nan'), float('nan'), float('nan')]

        msg.velocity_frame = 0
        msg.velocity = [float('nan'), float('nan'), float('nan')]
        msg.angular_velocity = [float('nan'), float('nan'), float('nan')]

        # can adjust position variance later where lower = trust data more
        msg.position_variance = [0.1, 0.1, 100.0]
        msg.orientation_variance = [float('nan'), float('nan'), float('nan')]
        msg.velocity_variance = [float('nan'), float('nan'), float('nan')]

        self.odom_pub.publish(msg)
        self.get_logger().info(f"Published NED: X:{msg.position[0]:.2f}, Y:{msg.position[1]:.2f}, Z:{msg.position[2]:.2f}")

    def read_serial_data(self):
        try:
            ser = serial.Serial(self.serial_port, self.baud_rate, timeout=0.1)
            buffer = bytearray()

            while rclpy.ok():
                if ser.in_waiting > 0:
                    buffer += ser.read(ser.in_waiting)
                    header_idx = buffer.find(b'CmdM:4')

                    if header_idx != -1 and len(buffer) >= header_idx + 98:
                        packet = buffer[header_idx : header_idx + 98]
                        buffer = buffer[header_idx + 98 :]
                        raw_ranges_bytes = packet[17:49]

                        try:
                            ranges_mm = struct.unpack('<8i', raw_ranges_bytes)

                            for anchor_id in self.ANCHORS_ENU.keys():
                                raw_m = ranges_mm[anchor_id] / 1000.0
                                if raw_m > 0:
                                    self.latest_distances[anchor_id] = self.filters[anchor_id].update(raw_m)

                            # Calculate 3D position
                            pos_enu = self.calculate_position()

                            if pos_enu is not None:
                                self.publish_to_px4(pos_enu)

                        except struct.error:
                            pass

                    if len(buffer) > 500:
                        buffer = buffer[-250 :]

        except Exception as e:
            self.get_logger().error(f"Serial Error: {e}")
        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()

def main(args=None):
    rclpy.init(args=args)
    node = UWBLocalizationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
