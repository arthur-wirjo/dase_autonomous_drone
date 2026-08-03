<img width="300" alt="dase_drone_v1 1" src="https://github.com/user-attachments/assets/c6e43249-29da-4e86-8fb7-ba1c89823b0b" />
<img width="300" alt="dase_drone_v1 0" src="https://github.com/user-attachments/assets/e5657703-d757-4975-93ea-a4471c0c0638" />

## DASE Autonomous Drone

This repository contains the setup, configuration, and execution documentation for an autonomous quadcopter powered by a Pixhawk 6C Mini (PX4), a Raspberry Pi 5 companion computer (ROS 2 via Micro-XRCE-DDS), and an MTF-01P Optical Flow/Lidar sensor for GPS-denied indoor navigation.

## Hardware Architecture

*   **Flight Controller:** Pixhawk 6C Mini (Holybro)
*   **ESC:** Tekko32 AM32 4-in-1 ESC (Holybro)
*   **Flight Computer:** Raspberry Pi 5 (Ubuntu 24.04)
*   **Power Distribution:**
    *   **PDB 1:** PM06 (Powers the flight controller and ESC)
    *   **PDB 2:** Generic 5V/5A BEC (Powers the Raspberry Pi 5)
*   **Sensors:** MicroAir MTF-01P (Optical Flow + Distance Sensor)
*   **Receiver:** RadioMaster ER6 ELRS Receiver
*   **Radio Controller:** RadioMaster Pocket (ELRS)
*   **Propulsion:** Generic 5-inch FPV drone motors and propellers
*   **Battery:** Generic 4S Li-Po Battery
*   **Accessories:** USB to TTL Serial Adapter

---

## Wiring & Assembly

1.  **Power Routing:**
    *   Split the main battery lead into PDB 1 and PDB 2.
    *   Connect PDB 1 to the flight controller (Power port) and the ESC.
    *   Connect PDB 2 to the Raspberry Pi 5 (via GPIO 5V/GND or USB-C).
2.  **Motor & ESC Connections:**
    *   Solder all four motors to the 4-in-1 ESC.
    *   Connect the ESC signal cable to the **I/O PWM outputs (M1, M2, M3, M4)** on the Pixhawk.
3.  **Sensor & Receiver Connections:**
    *   **MTF-01P:** Connect to the `TELEM 1` port of the flight controller.
    *   **ER6 Receiver:** Connect to the `GPS 2` port of the flight controller.
4.  **Companion Computer (Raspberry Pi 5):**
    *   Connect to the flight controller's `TELEM 2` port:
        *   Pi GPIO 14 (TX) ➔ FC `TELEM 2` RX
        *   Pi GPIO 15 (RX) ➔ FC `TELEM 2` TX
        *   Pi GND ➔ FC `TELEM 2` GND
5.  **Frame:** Assemble the frame, mount all components securely, and attach the motors. **Leave propellers off until final flight testing.**

---

## Software Prerequisites (Host PC & Pi)

1.  **Host PC Setup:**
    *   Install QGroundControl (QGC).
    *   Install the PX4-Autopilot toolchain (Required for SITL simulation, generating PX4 ROS 2 messages, and building custom firmware).
    *   Install the Micro-XRCE-DDS-Agent.
2.  **ROS 2 Workspace Setup (Host PC & Raspberry Pi):**
    ```bash
    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://github.com/PX4/px4_msgs.git
    git clone https://github.com/arthur-wirjo/dase_autonomous_drone.git
    cd ~/ros2_ws
    colcon build
    source install/setup.bash
    ```

---

## Running the Simulation (SITL)

To test your ROS 2 nodes safely in a Gazebo simulated environment:

1.  Open QGroundControl.
2.  Start the Micro-XRCE-DDS Agent for UDP:
    ```bash
    MicroXRCEAgent udp4 -p 8888
    ```
3.  In your `PX4-Autopilot` directory, launch the Gazebo simulation:
    ```bash
    make px4_sitl gz_x500
    ```
4.  Run the ROS 2 control node:
    ```bash
    ros2 run autonomous_hover hover_node
    ```

---

## Hardware Configuration (Real-World Setup)

### 1. Custom Firmware (ELRS via GPS 2)
By default, PX4 expects GPS data on the GPS 2 port. To use it for the ELRS receiver:
*   In the `PX4-Autopilot` workspace, modify the default PX4 firmware configuration.
*   **Enable** `crsf_rc` and **disable** `rc_input`.
*   Build and flash this custom firmware to the Pixhawk via QGC.

### 2. MTF-01P Sensor Setup
*   Connect the MTF-01P to your computer using the USB to TTL adapter.
*   Open the MicoAssistant Web Tool.
*   Connect to the sensor, navigate to the parameters section, and change the protocol from `Mavlink_APM` to `Mavlink_PX4`.

### 3. Motor Configuration & Reversal
*   In QGC's **Actuators** section, select the **Quadrotor X** geometry.
*   Assign Motors 1-4 to the MAIN outputs. Set the protocol to **PWM 400Hz**.
    *   *Note: If you wish to use DShot300 or DShot600 in the future, you must move the ESC signal wires from the I/O pins to the FMU/AUX pins on the Pixhawk.*
*   **CRITICAL:** Ensure propellers are removed. Use the Actuator Testing sliders to check motor spin directions.
    *   Motors 1 & 2 must spin **Counter-Clockwise (CCW)**.
    *   Motors 3 & 4 must spin **Clockwise (CW)**.
*   If a motor spins the wrong way, physically desolder any two of the three wires connecting that motor to the ESC and swap them.

### 4. Radio & Sensors
*   Calibrate your radio controller in QGC.
*   Configure your flight mode switch to include **Position**, **Manual**, and **Position Slow**. *(Safety Tip: Always have Manual mode easily accessible to quickly regain control or disarm in an emergency).*
*   Calibrate the compass, gyroscope, and accelerometer in QGC. Ensure the flight controller's forward arrow aligns with the physical front of the drone.

---

## QGC Parameter Reference

Ensure the following parameters are set in QGroundControl. Reboot the flight controller after applying.

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `RC_CRSF_PRT_CFG` | **GPS 2** | Routes CRSF RC protocol to the GPS 2 port. |
| `MAV_0_CONFIG` | **TELEM 1** | Assigns MAVLink instance 0 to TELEM 1 (MTF-01P). |
| `MAV_0_MODE` | **0 (Normal)** | Standard MAVLink communication. |
| `SER_TEL1_BAUD` | **115200** | Matches the MTF-01P baud rate. |
| `MAV_PROTO_VER` | **1** | Forces MAVLink v1. *Note: QGC may show a warning expecting v2; this is normal and can be safely ignored.* |
| `EKF2_GPS_CTRL` | **0 (Disabled)** | Disables GPS fusion for indoor flight. |
| `SYS_HAS_GPS` | **0 (Disabled)** | Tells the system no GPS is attached. |
| `EKF2_HGT_REF` | **Range sensor** | Uses the Lidar for altitude estimation. |
| `EKF2_OF_CTRL` | **Enabled** | Fuses Optical Flow data for horizontal velocity. |
| `EKF2_RNG_CTRL` | **Enabled** | Fuses Rangefinder data. |
| `EKF2_MIN_RNG` | **0.1** | Minimum valid Lidar distance (meters). |
| `UXRCE_DDS_CFG` | **TELEM 2** | Routes ROS 2 DDS traffic to the Pi. |

*Verification:* Open the MAVLink Inspector in QGC and verify that `DISTANCE_SENSOR [0]` and `OPTICAL_FLOW_RAD [0]` are actively publishing data.

---

## Running the Drone (IRL)

1.  Turn on the radio controller and ensure the ELRS link is active.
2.  Power on the drone (plug in the Li-Po battery).
3.  SSH into the Raspberry Pi.
4.  Start the XRCE-DDS Agent over the serial connection:
    ```bash
    MicroXRCEAgent serial --dev /dev/ttyAMA0 -b 921600
    ```
5.  Open a second SSH terminal on the Pi.
6.  Source your ROS 2 workspace:
    ```bash
    source ~/ros2_ws/install/setup.bash
    ```
7.  Run the autonomous flight node:
    ```bash
    ros2 run autonomous_hover hover_node
    ```
