#Hardware Wiring & Configuration Guide

## ESP32-CAM Pinout Reference

```
                    ┌─────────────────────────────────┐
                    │     ESP32-CAM Development       │
                    │         Module                  │
                    │                                 │
        GND   ──────┤ GND                         GND ├────── GND
        3.3V  ──────┤ 3V3                         5V  ├────── 5V (Servo Power)
        TX    ──────┤ U0T                         GND ├────── GND
        RX    ──────┤ U0R                         IO2 ├────── (Reserved for Flash)
        IO4   ──────┤ IO4 (Status LED)            IO15├────── (Reserved)
        IO12  ──────┤ IO12 (Servo PWM)           IO13├────── (Camera CLK)
        IO13  ──────┤ IO13                        IO14├────── (Camera D2)
        IO14  ──────┤ IO14                        IO27├────── (Camera HREF)
        IO27  ──────┤ IO27                        IO26├────── (Camera SDA)
        IO25  ──────┤ IO25 (Sync)                 IO25├────── (Sync)
        IO32  ──────┤ IO32 (PWDN)                 IO34├────── (Analog only)
        IO35  ──────┤ IO35                        IO39├────── (Analog only)
        IO36  ──────┤ IO36                        IO19├────── (Camera D5)
        IO23  ──────┤ IO23 (HREF)                 IO18├────── (Camera Y3)
        IO19  ──────┤ IO19                        IO5 ├────── (Camera XCK)
        IO18  ──────┤ IO18                        IO17├────── (Reserved)
        IO05  ──────┤ IO5                         IO16├────── (Reserved)
        IO17  ──────┤ IO17 (Reserved)             IO0 ├────── (Camera Y2)
        IO16  ──────┤ IO16 (Reserved)             IO22├────── (Camera PCLK)
        IO0   ──────┤ IO0 (Camera Y2)             IO21├────── (Camera SDA)
        IO22  ──────┤ IO22                        GND ├────── GND
        IO21  ──────┤ IO21                        GND ├────── GND
                    └─────────────────────────────────┘
```

## Servo Motor Wiring

### Standard 180° Servo (SG90, MG996R)

```
Pin Color Mapping:
- RED    : Power (5V)
- BROWN  : Ground (GND)
- YELLOW : Signal (PWM)

```
|    Component     |  Wire Color  |  GPIO Pin  |  Notes          |
|------------------|--------------|-----------|-----------------|
| Servo VCC        | RED          | 5V Power  | External supply |
| Servo GND        | BROWN        | GND       | Common ground   |
| Servo Signal     | YELLOW       | IO12      | PWM control     |


### Wiring Diagram

```
                                    SERVO MOTOR
                                   ┌─────────────┐
                                   │ SG90/MG996R │
                                   │             │
                 ┌──────────────────┤ Signal      │
                 │                  │ (Yellow)    │
       ESP32-CAM │                  │ GND (Brown) ├──┐
        GPIO 12  │                  │ 5V (Red)    │  │
                 │                  └─────────────┘  │
                 │                       │            │
                 └───────────┬────────────┼────────────┤
                            PWM          GND          5V

                      External 5V Power Supply
                      ├─────────────────────┤
                      │   Servo Power       │
                      │   (3A minimum)      │
                      │ Red: +5V            │ ┌─ To Servo Red
                      │ Black: GND          │ └─ To Servo Brown
                      │                     │
                      └─────────────────────┘
                             │
                      ┌──────┴──────┐
                      │     GND     │
                      │  (Return to │
                      │   ESP32)    │
                      └─────────────┘
```

## Status LED Wiring

```
        ESP32-CAM                Current Limiting Resistor
          GPIO 4                        220Ω
            ├─────────────────────/\/\/────────┐
            │                                  │
            │                              ┌───┴────┐
            │                              │    LED  │
            │                              │ (+) Red │
            │                              │ (-) Blk │
            └──────────────────────────────┤    GND  │
                                           └─────────┘

                                    OR without resistor:
          GPIO 4 ────────┐
                         │
                    ┌────┴─────┐
                    │   LED     │ (High-efficiency LED)
                    │ (+ Red)   │
                    │ (- Black) │
                    └────┬─────┘
                         │
                        GND
```

## Complete System Wiring Schematic

```
                    ┌─────────────────────────────────────────┐
                    │       SMART PARKING GATE CONTROL        │
                    │              ESP32-CAM                  │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                ┌───┴────────┐   ┌────┴──────┐   ┌─────┴──────┐
                │ Servo Motor │   │Status LED │   │  Camera    │
                │ (GPIO 12)   │   │(GPIO 4)   │   │(Built-in)  │
                │             │   │           │   │            │
                │ Signal      │   │ Current   │   │ JST Socket │
                │ GND         │   │ Limiting  │   │            │
                │ 5V          │   │ Resistor  │   │            │
                └──┬──┬──┬────┘   └───┬──┬────┘   └────────────┘
                   │  │  │           │  │
                   │  │  └─────GND───┘  │
                   │  │                 │
                   │  │        ┌────────┘
                   │  │        │
           ┌───────┘  │        │
           │          │   ┌────┴──────┐
           │          │   │ USB Power │
           │          │   │ (3.3V)    │
           │    ┌─────┴───┴──┬────────┤
           │    │  Micro USB │        │
           │    └────────────┴────────┘
           │                    │
           │                GND Return
           │
      5V External
      Power Supply
      (Servo Power)
           │
           └─────────┬───────────────┘
                    GND
              (Common Ground)
```

## Pin Configuration Summary

### Required for Gate Control

```python
# Servo Configuration (app.py)
const int SERVO_PIN = 12              # GPIO 12 - PWM output
const int SERVO_CLOSED = 0            # 0 degrees = closed
const int SERVO_OPEN = 90             # 90 degrees = open
const int GATE_OPEN_TIME = 5000       # 5 seconds

# Status LED Configuration
const int STATUS_LED = 4              # GPIO 4 - Digital output

# WiFi & Power
GND   - Common ground with Python server
3.3V  - ESP32 power
5V    - Servo motor power (external supply)
```

### Camera Pins (Already Configured)

```
Pin     | Function          | GPIO
--------|-------------------|-----
XCLK    | Clock             | 0
SIOD    | I2C SDA           | 26
SIOC    | I2C SCL           | 27
Y9      | Data              | 35
Y8      | Data              | 34
Y7      | Data              | 39
Y6      | Data              | 36
Y5      | Data              | 21
Y4      | Data              | 19
Y3      | Data              | 18
Y2      | Data              | 5
VSYNC   | Vertical Sync     | 25
HREF    | Horizontal Ref    | 23
PCLK    | Pixel Clock       | 22
PWDN    | Power Down        | 32
RESET   | Reset             | -1 (not used)
```

## Power Supply Requirements

### Servo Motor
```
Standard SG90:
- Operating Voltage: 4.8-6V
- Operating Current: 100-200mA
- Peak Current: 300mA (at startup)

MG996R (Stronger):
- Operating Voltage: 4.8-7.2V
- Operating Current: 500mA-1A
- Peak Current: 1.5A-2A

RECOMMENDATION:
- Use separate 5V/2A power supply for servo
- Connect common ground to ESP32
- Do NOT power servo from ESP32 USB power
```

### ESP32-CAM
```
- Operating Voltage: 3.3V
- Operating Current: 80-160mA
- Peak Current: 300mA (during WiFi transmission)
- USB Power (via Micro-USB): 500mA maximum

RECOMMENDATION:
- Use quality USB power adapter (5V/1A minimum)
- For production: Use step-down converter from 5V supply
```

## Assembly Checklist

- [ ] ESP32-CAM mounted on breadboard/frame
- [ ] Servo motor connected to GPIO 12 (signal), GND, and 5V (external)
- [ ] Status LED connected to GPIO 4 through 220Ω resistor
- [ ] Common ground between ESP32 and servo power supply
- [ ] USB power cable connected to ESP32
- [ ] 5V power supply connected to servo (separate from USB)
- [ ] All solder joints checked for cold/dry connections
- [ ] No duplicate pin assignments
- [ ] WiFi antenna properly positioned (ESP32-CAM has built-in antenna)

## Servo Calibration

### Test Sweep
```cpp
void testServoSweep() {
    for (int angle = 0; angle <= 180; angle++) {
        gateServo.write(angle);
        Serial.printf("Angle: %d\n", angle);
        delay(50);
    }
    delay(1000);
    for (int angle = 180; angle >= 0; angle--) {
        gateServo.write(angle);
        delay(50);
    }
}

// In setup() or loop():
// testServoSweep();  // Verify full range motion
```

### Adjust Open/Close Angles

If your servo doesn't reach full 90° or has mechanical limits:

```cpp
// Adjust these values:
const int SERVO_CLOSED = 0;     // Try: 5-10 if servo vibrates at 0
const int SERVO_OPEN = 85;      // Try: 80-90 depending on mechanical limit
```

## Troubleshooting Connections

| Problem | Debugging Steps |
|---------|-----------------|
| Servo doesn't move | 1. Check GPIO 12 connection; 2. Verify 5V power at servo; 3. Test with sweep code; 4. Check servo power supply amperage |
| Servo moves but jitters | 1. Improve power supply quality; 2. Add 100µF capacitor across servo power; 3. Check for loose connections |
| LED doesn't light | 1. Check GPIO 4 connection; 2. Verify current limiting resistor; 3. Check LED polarity (longer leg = +) |
| ESP32 won't upload | 1. Check Micro-USB cable quality; 2. Select correct COM port; 3. Hold BOOT button while uploading; 4. Check driver installation |
| WiFi connection fails | 1. Verify SSID/password in code; 2. Check 2.4GHz network (not 5GHz); 3. Move closer to router; 4. Check antenna position |
| Camera not initializing | 1. Check JST camera connector; 2. Verify all camera pin assignments; 3. In Arduino: Tools → Camera Model → AI Thinker; 4. Check for corrupted flash |

## Recommended Components (BOM)

```
Item                                QTY   Est. Cost
─────────────────────────────────────────────────
ESP32-CAM Development Board          1     $10-15
Servo Motor (SG90 or MG996R)         1     $5-15
5V/2A Power Supply (external)        1     $3-8
Micro-USB Data Cable                 1     $2-3
Jumper Wires (Male-to-Male)         20     $2-3
Breadboard (400-point)               1     $2-3
220Ω Resistor (for LED)             1     $0.10
100µF Capacitor (servo stabilization)1     $0.50
LED (5mm Red)                        1     $0.50
Servo Extension Cable (optional)     1     $3-5
                                          ────────
                        TOTAL COST: ~$30-50
```

## Production Considerations

For production deployment:

1. **Weatherproof Housing**
   - Use IP65-rated enclosure for ESP32
   - Keep camera lens clear
   - Protect power connections

2. **Redundancy**
   - Backup manual override button
   - Battery backup for servo power
   - Fallback to open gate on power loss

3. **Reliability**
   - Use industrial-grade servo (MG996R)
   - Add capacitors for power stability
   - Implement watchdog timer
   - Log all access events

4. **Security**
   - Encrypt WiFi traffic (HTTPS)
   - Update API key regularly
   - Monitor for failed access attempts
   - Physical tamper detection

---

**Hardware installation complete!** 
Proceed to configure WiFi and Flask server settings.
