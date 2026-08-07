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
import RPi.GPIO as GPIO

SERVO_PIN = 23
BASE_PWM_DUTY = 7.5
PWM_STEP = 1.0
MIN_DUTY = 2.5
MAX_DUTY = 12.5

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

        # Target Positions and Yaw
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = 0.0
        self.target_yaw = 0.0
        
        # Current Positions and Yaw
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.current_yaw = 0.0
        self.has_position_lock = False

        # Servo Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        self.servo_pwm = GPIO.PWM(SERVO_PIN, 50) # 50Hz
        self.current_duty = BASE_PWM_DUTY
        self.servo_pwm.start(self.current_duty)

        # Timer running at 20Hz (0.05s) - PX4 prefers >= 20Hz for offboard mode
        self.timer = self.create_timer(0.05, self.timer_callback)

        # Keyboard Listener Setup
        self.old_terminal_settings = termios.tcgetattr(sys.stdin)
        self.keyboard_thread = threading.Thread(target=self.key_listener, daemon=True)
        self.keyboard_thread.start()

        self.get_logger().info("Node started\nPress SPACE to takeoff/land\nPress 'w' to increase servo duty cycle\nPress 's' to decrease servo duty cycle\nPress ENTER to kill\nPress CTRL+C to exit")

    def timer_callback(self):
        # Constantly publish OffboardControlMode and TrajectorySetpoint
        self.publish_offboard_control_mode()
        # Pass X, Y, Z, and Yaw to the publisher
        self.publish_trajectory_setpoint(self.target_x, self.target_y, self.target_z, self.target_yaw)
        
    def pos_callback(self, msg):
        # Update current X, Y, Z, and Yaw (heading) from the flight controller
        self.current_x = msg.x
        self.current_y = msg.y
        self.current_z = msg.z
        self.current_yaw = msg.heading
        self.has_position_lock = True

        # Check if we reached hover altitude
        if self.state == 'TAKING_OFF' and self.current_z <= -0.9:
            self.state = 'HOVERING'
            self.get_logger().info("Hovering stably at 1m. Ready for next command.")

        # Check if we reached the ground
        elif self.state == 'LANDING' and self.current_z >= -0.1:
            self.state = 'GROUND'
            self.get_logger().info("Landing stably. Disarming.")

    def key_listener(self):
        # Background thread to listen for keyboard inputs without blocking ROS timer
        try: 
            tty.setcbreak(sys.stdin.fileno())
            while rclpy.ok():
                # Wait 0.1s for a key press
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()

                    if key == ' ':
                        self.handle_spacebar()
                    elif key == 'w':
                        self.handle_w()
                    elif key == 's':
                        self.handle_s()
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
            if not self.has_position_lock:
                self.get_logger().warn("Cannot take off: No local position lock yet. Waiting for EKF...")
                return

            self.get_logger().info("SPACEBAR Pressed: Taking Off")
            
            # CRITICAL: Lock the target X, Y, and YAW to the CURRENT state so it goes straight up without rotating
            self.target_x = self.current_x
            self.target_y = self.current_y
            self.target_yaw = self.current_yaw
            self.target_z = -1.0
            self.state = 'TAKING_OFF'

            # Send commands to arm and switch to offboard mode
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0, 21196.0)
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

        elif self.state == 'HOVERING':
            self.get_logger().info("SPACEBAR Pressed: Landing")
            self.state = 'LANDING'
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 4.0, 6.0)

        else:
            self.get_logger().warn(f"Ignoring input. Drone is currently {self.state}...")

    def handle_w(self):
        self.current_duty += PWM_STEP
        if self.current_duty > MAX_DUTY:
            self.current_duty = MAX_DUTY
            self.get_logger().warn("Servo reached max pos")
        else:
            self.servo_pwm.ChangeDutyCycle(self.current_duty)
            self.get_logger().info("Servo duty cycle increased")
        
    def handle_s(self):
        self.current_duty -= PWM_STEP
        if self.current_duty < MIN_DUTY:
            self.current_duty = MIN_DUTY
            self.get_logger().warn("Servo reached min pos")
        else:
            self.servo_pwm.ChangeDutyCycle(self.current_duty)
            self.get_logger().info("Servo duty cycle decreased")
    
    def handle_enter(self):
        self.get_logger().error("KILL SWITCH ACTIVATED! DISARMING IMMEDIATELY")
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)
        
        # Reset targets to current position so it doesn't do anything crazy if re-armed
        self.target_x = self.current_x
        self.target_y = self.current_y
        self.target_z = self.current_z
        self.target_yaw = self.current_yaw
        self.state = 'GROUND'

    def restore_terminal(self):
        # Restores standard terminal behavior so console doesn't break on exit
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

    def publish_trajectory_setpoint(self, target_x, target_y, target_z, target_yaw):
        msg = TrajectorySetpoint()
        # Use the dynamically updated X and Y targets
        msg.position = [target_x, target_y, target_z]
        # Use the dynamically updated Yaw target
        msg.yaw = target_yaw
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher.publish(msg)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0, param3=0.0):
        msg = VehicleCommand()
        msg.command = command
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        msg.param3 = float(param3)
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.vehicle_command_publisher.publish(msg)

    def destroy_node(self):
        self.servo_pwm.stop()
        del self.servo_pwm
        GPIO.cleanup()
        super().destroy_node()

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
