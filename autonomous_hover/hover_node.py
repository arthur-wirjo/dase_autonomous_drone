#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition

import sys
import select
import termios
import tty
import threading

class HoverNode(Node):
    def __init__(self):
        super().__init__(node_name='hover_node')
        
        # Publishers
        self.offboard_control_mode_publisher = self.create_publisher(
                OffboardControlMode, '/fmu/in/offboard_control_mode', 10)
        self.trajectory_setpoint_publisher = self.create_publisher(
                TrajectorySetpoint, '/fmu/in/trajectory_setpoint', 10)
        self.vehicle_command_publisher = self.create_publisher(
                VehicleCommand, '/fmu/in/vehicle_command', 10)

        # Subscribers
        self.local_pos_sub = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1', self.pos_callback, qos_profile_sensor_data)
        
        # State Machine Variables
        self.state = 'GROUND' # GROUND, TAKING_OFF, HOVERING, LANDING
        self.target_z = 0.0
        self.current_z = 0.0

        # Timer running at 10Hz 
        self.timer = self.create_timer(0.1, self.timer_callback)

        # Keyboard Listener Setup
        self.old_terminal_settings = termios.tcgetattr(sys.stdin)
        self.keyboard_thread = threading.Thread(target=self.key_listener, daemon=True)
        self.keyboard_thread.start()

        self.get_logger().info("Node started. Press SPACE to takeoff/land, Press ENTER to kill, Press CTRL+C to exit.")

    def timer_callback(self):
        # Constantly publish OffboardControlMode and TrajectorySetpoint
        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint(self.target_z)
        
    def pos_callback(self, msg):
        self.current_z = msg.z

        # Check if we reached hover altitude
        if self.state == 'TAKING_OFF' and self.current_z <= -1.8:
            self.state = 'HOVERING'
            self.get_logger().info("Hovering stably at 2m. Ready for next command.")

        # Check if we reached the ground
        elif self.state == 'LANDING' and self.current_z >= -0.2:
            self.state = 'GROUND'
            self.get_logger().info("Landing stably. Disarming.")
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)

    def key_listener(self):
        # Background thread to listen for keyboard inputs without blocking ROS timer
        try: 
            tty.setcbreak(sys.stdin.fileno())
            while rclpy.ok():
                # Wait 0.1s for a key press
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)

                    if key == ' ':
                        self.handle_spacebar()
                    elif key in ['\r', '\n']:
                        self.handle_enter()
                    elif key == '\x03': # CTRL+C
                        self.get_logger().info("CTRL+C detected. Shutting down.")
                        rclpy.shutdown()
                        break
        finally:
            self.restore_terminal()

    def handle_spacebar(self):
        if self.state == 'GROUND':
            self.get_logger().info("SPACEBAR Pressed: Taking Off")
            self.target_z = -2.0
            self.state = 'TAKING_OFF'

            # Send commands to arm and switch to offboard mode
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

        elif self.state == 'HOVERING':
            self.get_logger().info("SPACEBAR Pressed: Landing")
            self.target_z = 0.0
            self.state = 'LANDING'

        else:
            self.get_logger().warn(f"Ignoring input. Drone is currently {self.state}...")

    def handle_enter(self):
        self.get_logger().error("KILL SWITCH ACTIVATED! DISARMING IMMEDIATELY")
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)
        self.target_z = 0.0
        self.state = 'GROUND'

    def restore_terminal(self):
        # Restores standard terminal behavior so consolde doesn't break on exit
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_terminal_settings)

    # PX4 Message Publishers
    def publish_offboard_control_mode(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate =  False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_control_mode_publisher.publish(msg)

    def publish_trajectory_setpoint(self, target_z):
        msg = TrajectorySetpoint()
        msg.position = [0.0, 0.0, target_z]
        msg.yaw = 0.0
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher.publish(msg)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.command = command
        msg.param1 = param1
        msg.param2 = param2
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.vehicle_command_publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = HoverNode()
    try:    
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.restore_terminal()
        node.destroy_node()
        if rclpy.ok():    
            rclpy.shutdown()

if __name__ == '__main__':
    main()
