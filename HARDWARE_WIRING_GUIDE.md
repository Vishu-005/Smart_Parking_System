# Hardware Wiring Guide - Smart Parking Controller

This guide outlines the pin connections for the ESP32 Dev Module (Main Controller).

## ESP32 Dev Module Pinout

### 1. Servo Motor (Gate)
| Component Pin | ESP32 GPIO | Description |
| :--- | :--- | :--- |
| **PWM (Signal)** | **GPIO 23** | Control signal for the servo |
| VCC | 5V / VIN | Ensure stable 5V current |
| GND | GND | Common ground |

### 2. Parking Slot Sensors (IR)
| Slot Number | ESP32 GPIO | Logic |
| :--- | :--- | :--- |
| **SLOT 1** | **GPIO 12** | LOW = Occupied, HIGH = Available |
| **SLOT 2** | **GPIO 16** | LOW = Occupied, HIGH = Available |
| **SLOT 3** | **GPIO 17** | LOW = Occupied, HIGH = Available |
| **SLOT 4** | **GPIO 14** | LOW = Occupied, HIGH = Available |
| **SLOT 5** | **GPIO 15** | LOW = Occupied, HIGH = Available |

---

## Technical Specifications

### Servo Settings
- **Safe Range**: 0° (Closed) to 90° (Open).
- **Delay**: The gate remains open for **5 seconds** before automatically closing.

### IR Sensors
- **Model**: Standard IR Obstacle Avoidance Sensor.
- **Wiring**:
    *   VCC -> ESP32 3.3V or 5V (depending on sensor model).
    *   GND -> ESP32 GND.
    *   OUT -> Assigned GPIO (see table above).
- **Calibration**: Use the on-board potentiometer to adjust detection distance (~5-10cm).

### Network Connectivity
- **WiFi**: ESP32 connects to `devil` / `123456789`.
- **Server**: Communicates with Backend at `10.187.23.53:5000`.

---

## Setup Instructions
1.  Upload the `esp32_main_controller.ino` firmware using Arduino IDE.
2.  Open the Serial Monitor (115200 baud) to verify the IP address.
3.  Ensure the Flask backend is running on the computer at the specified IP.
4.  Test the gate by visiting `http://<ESP32_IP>/open_gate` in your browser.
