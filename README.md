<img width="300" alt="dase_drone_v1 1" src="https://github.com/user-attachments/assets/c6e43249-29da-4e86-8fb7-ba1c89823b0b" />
<img width="300" alt="dase_drone_v1 0" src="https://github.com/user-attachments/assets/e5657703-d757-4975-93ea-a4471c0c0638" />

## DASE Autonomous Drone

This repository contains the setup, configuration, and execution documentation for an autonomous quadcopter powered by a Pixhawk 6C Mini (PX4), a Raspberry Pi 5 flight computer (ROS 2 via Micro-XRCE-DDS), and an MTF-01P Optical Flow/Lidar sensor + Ultra-Wideband (UWB) modules for GPS-denied indoor navigation.

## Hardware Architecture

*   **Flight Controller:** Pixhawk 6C Mini (Holybro)
*   **ESC:** Tekko32 AM32 4-in-1 ESC (Holybro)
*   **Flight Computer:** Raspberry Pi 5 (Ubuntu 24.04)
*   **Camera:** Raspberry Pi Camera Module 3
*   **Power Distribution:**
    *   **PDB 1:** PM06 (Powers the flight controller and ESC)
    *   **PDB 2:** Generic 5V/5A BEC (Powers the Raspberry Pi 5)
*   **Sensors:** MicroAir MTF-01P (Optical Flow + Distance Sensor)
*   **Receiver:** RadioMaster ER6 ELRS Receiver
*   **Radio Controller:** RadioMaster Pocket (ELRS)
*   **Propulsion:** Generic 5-inch FPV drone motors and propellers
*   **Battery:** Generic 4S Li-Po Battery
*   **Accessories:** USB to TTL Serial Adapter
*   **UWB Modules:** AI-Thinker BU03 Kit (x5)
*   **Servo:** MG90 (For moving the camera) 

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
3.  **Camera & Streaming Prerequisites:**
    *   Install FFmpeg on both the Host PC and the Raspberry Pi: 
        ```bash
        sudo apt update
        sudo apt install ffmpeg
        ```
    *   If starting with a fresh Raspberry Pi, you must configure the OS to recognize the camera (especially Camera Module v3 on Ubuntu 24.04). Follow this guide: [How I set up the Raspberry Pi Camera v3 on a Raspberry Pi 5 running Ubuntu 24.04](https://medium.com/@arnav04verma/how-i-set-up-the-raspberry-pi-camera-v3-on-a-raspberry-pi-5-running-ubuntu-24-04-7563d1c61a3b)

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
*   Open the MicoAssistant Web Tool at https://micoair.com/assistant/ .
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

### Extra notes
*   IMPORTANT: Please ensure the ground has texture and is NOT smooth, or else the optical sensor will not be able to detect x-y movement from the ground texture
*   Turn on the radio controller and put it in ELRS mode before turning the drone for easier binding.
*   It is suggested to setup a Tailscale VPN network to SSH into the Raspberry Pi since the university Wi-Fi firewall blocks direct SSH. 

---

## UWB Global Localization Setup

Optical flow and Z-axis Lidar sensors are excellent for *relative* localization, but they drift over time. To achieve true *global* localization indoors, this project uses Ultra-Wideband (UWB) modules. 

In the context of GPS-denied locations such as factories or warehouses, UWB is an appealing option because:
*   It does not require direct line of sight.
*   The sensor is very lightweight and less computationally heavy compared to Lidar SLAM.
*   It is relatively inexpensive.

**Hardware Used:** 5x AI-Thinker BU03 UWB development boards (1 configured as a Tag, 4 configured as Anchors). The system uses the Two-Way Ranging (TWR) algorithm to calculate the distance between the Tag and each Anchor.

### 1. Prerequisites
*   Get a serial monitor software to communicate with the UWB modules (e.g., **PuTTY** for Windows or **CuteCom** for Linux).
*   Ensure the baud rate is configured to `115200` and the line terminator is set to `CR/LF`.
*   Connect the module to your computer using the **TTL USB-C port** (not the standard USB port) for AT command configuration.
*   **Important:** Before sending any configuration commands, always send `AT` to verify the connection (it should return `OK`). After changing configurations, you **must** send `AT+SAVE` or the module will revert upon restart.
*   *Reference Links:* [Official UWB Documentation](https://docs.ai-thinker.com/en/uwb_1/index.html) | [Full AT Command List](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/_media_old/BU03_BU04_AT_command_en_v1.0.6.pdf)

### 2. Configure Each UWB Module
By default, the modules should be in TWR mode. If not, set it using `AT+SETUWBMODE=0`.

The template command for configuring the UWB modules is `AT+SETCFG=X1,X2,X3,X4`:
*   `X1`: ID (0-10)
*   `X2`: Role (0 = Tag, 1 = Anchor)
*   `X3`: Channel (0 = Channel 9, 1 = Channel 5)
*   `X4`: Group (0-255)

Additionally, we must reset the linear fitting parameters to `y = 1x + 0` before calibration using `AT+SETDEV=X1,X2,X3,X4,X5,a,b,X8,X9`.

Configure your 5 modules one by one using the TTL port:

**Module 1 (The Tag):**
```text
AT+SETCFG=0,0,1,1
AT+SAVE
```

**Module 2 (Anchor 1):**
```text
AT+SETCFG=1,1,1,1
AT+SETDEV=10,16336,1.0,0.018,0.642,1,0,0,0
AT+SAVE
```

**Module 3 (Anchor 2):**
```text
AT+SETCFG=2,1,1,1
AT+SETDEV=10,16336,1.0,0.018,0.642,1,0,0,0
AT+SAVE
```

**Module 4 (Anchor 3):**
```text
AT+SETCFG=3,1,1,1
AT+SETDEV=10,16336,1.0,0.018,0.642,1,0,0,0
AT+SAVE
```

**Module 5 (Anchor 4):**
```text
AT+SETCFG=4,1,1,1
AT+SETDEV=10,16336,1.0,0.018,0.642,1,0,0,0
AT+SAVE
```

### 3. Calibrating Anchors (Linear Fitting)
*   Download the Excel calibration sheet: [English Version](https://cdn.shopify.com/s/files/1/0621/0050/4774/files/BU03_data_calibration.xlsx?v=1756780996) | [Chinese Version](https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/_media_old/d_%E6%95%B0%E6%8D%AE%E6%A0%87%E5%AE%9A%E6%A8%A1%E6%9D%BF.xlsx)
*   Connect the Raspberry Pi to the **Tag** module through its **(USB) USB-C port** (not the TTL port).
*   Ensure the Raspberry Pi detects the Tag module at `/dev/ttyACM0` by running `ls /dev/tty*` in the terminal.

 **Note for Ubuntu/Pi Users:** If you cannot see `/dev/ttyACM0`, it is likely conflicting with a background service called `brltty` (a braille display driver). Fix this by running `sudo apt remove brltty`, then replug the USB cable.

*   Power on all the Anchors. They should display their sensed distance from the Tag on their screens.
*   In the Excel sheet, plot the *actual physical distance* between the Tag and an Anchor against the *sensed distance* in 20cm intervals (up to the max distance of your flight area).

**Note:** If the Anchor's screen values fluctuate too much, run the `dase_autonomous_drone/uwb/tag_testing.py` script on the Pi to view stabilized distances using an Exponential Moving Average (EMA) filter. You can tune the `alpha` variable in the script for more/less smoothing.

*   After logging the data, the Excel sheet will generate a linear equation: `y = ax + b`.
*   Plug the Tag back into the TTL port and reconfigure each Anchor with its new `a` and `b` parameters:
    ```text
    AT+SETDEV=10,16336,1.0,0.018,0.642,a,b,0,0
    AT+SAVE
    ```

### 4. Running UWB Global Localization in ROS 2
Before running the node, you must configure the physical locations of your Anchors in the flight space.
1.  Open `dase_autonomous_drone/autonomous_hover/uwb_localization_node.py`.
2.  In the `UWBLocalizationNode` initialization, edit the `self.ANCHORS_ENU` dictionary to match the exact `(X, Y, Z)` coordinates of your Anchors in meters (using the ENU coordinate frame: X=Right, Y=Forward, Z=Up):
    ```python
    self.ANCHORS_ENU = {
        1: np.array([-1.5, -1.5, 0]), 
        2: np.array([1.5, -1.5, 0]), 
        3: np.array([-1.5, 1.5, 1.94]), 
        4: np.array([1.5, 1.435, 1.84])
    }
    ```
3.  Rebuild your ROS 2 workspace:
    ```bash
    cd ~/ros2_ws
    colcon build --packages-select autonomous_hover
    source install/setup.bash
    ```
4.  Run the localization node:
    ```bash
    ros2 run autonomous_hover uwb_localization
    ```
    *(Alternatively, you can execute the bash script located at `dase_autonomous_drone/bash_scripts/run_uwb_localization.sh`)*

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
| `SYS_HAS_GPS` | **0 (Disabled)** | Tells the system no GPS is attached. |
| `SYS_HAS_MAG` | **0 (Disabled)** | Tells the system no Compass is attached (prevents pre-flight failures underground). |
| `EKF2_GPS_CTRL` | **0 (Disabled)** | Disables GPS fusion for indoor flight. |
| `EKF2_MAG_TYPE` | **5 (None)** | Forces the EKF2 to ignore magnetic fields and rely entirely on the gyro for heading. |
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
---

## Live Video Streaming (Raspberry Pi Camera)

To monitor the drone's perspective during flight, you can stream video from the Raspberry Pi Camera to your Host PC using `FFmpeg`. The repository includes bash scripts for two different streaming modes depending on your network conditions.

**IMPORTANT NOTE:** The scripts use hardcoded IP addresses (e.g., Tailscale VPN IPs). Before running them, open the scripts and replace the IP addresses with your actual Host PC and Drone IP addresses.

### Mode 1: Fast Camera (Low Latency UDP)
Best for real-time FPV viewing. It uses the `libx264` codec with ultrafast presets over UDP.

1.  **On the Drone (Sender):**
    Edit `run_fast_camera.sh` to include your **Host PC's IP address**, then run:
    ```bash
    ./dase_autonomous_drone/bash_scripts/run_fast_camera.sh
    ```
    *(Under the hood, this runs: `rpicam-vid -t 0 --codec yuv420 --width 1280 --height 720 --framerate 30 -o - | ffmpeg -f rawvideo -pix_fmt yuv420p -s 1280x720 -r 30 -i - -c:v libx264 -preset ultrafast -tune zerolatency -f mpegts udp://<HOST_IP>:8888`)*

2.  **On the Host PC (Receiver):**
    ```bash
    ./dase_autonomous_drone/bash_scripts/recieve_fast_camera.sh
    ```
    *(Under the hood, this runs: `ffplay -fflags nobuffer -flags low_delay -framedrop udp://0.0.0.0:8888`)*

### Mode 2: Smooth Camera (High Quality TCP)
Best for stable, high-quality recording or viewing where a slight delay is acceptable. It uses MJPEG over TCP.

1.  **On the Drone (Sender):**
    ```bash
    ./dase_autonomous_drone/bash_scripts/run_smooth_camera.sh
    ```
    *(Under the hood, this runs: `rpicam-vid -t 0 --codec mjpeg --width 1280 --height 720 --framerate 30 --listen -o tcp://0.0.0.0:8888`)*

2.  **On the Host PC (Receiver):**
    Edit `recieve_smooth_camera.sh` to include your **Drone's IP address**, then run:
    ```bash
    ./dase_autonomous_drone/bash_scripts/recieve_smooth_camera.sh
    ```
    *(Under the hood, this runs: `ffplay -f mjpeg -fflags nobuffer -flags low_delay -framedrop tcp://<DRONE_IP>:8888`)*
    
### Notes for next students continuing the project:
*   Although the drone can hover and maintain position relatively well for some time
*   It's yaw still drifts overtime since UWB modules cannot detect yaw, optical flow sensor drifts, and IMU drifts
*   Resulting in the drones yaw to drift overtime and hover more unstably
*   The DASE department has some ORADAR MS200p 2D lidar sensors
*   They are relatively light and can be used to correct for yaw drift and have more stable x and y axis localization
*   The next goal of this project is to have the drone be able to stably hover indefinietly and correct any sort of drift in GPS-denied situation
