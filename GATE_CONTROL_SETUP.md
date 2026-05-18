# Smart Parking Gate Control - Implementation Guide

## Overview

This document provides complete setup instructions for the automatic gate control system using ESP32-CAM and a servo motor.

## Components

### Hardware Required
- **ESP32-CAM**: Microcontroller with built-in camera
- **Servo Motor**: Standard 180° servo (e.g., MG996R, SG90)
- **Power Supply**: 5V for servo, 3.3V for ESP32
- **Status LED**: Optional status indicator
- **Jumper Wires & Breadboard**
- **Flask Server** (your laptop/desktop running the parking system)
- **WiFi Network**: For device connectivity

### Software Requirements
```
Python Packages (Flask side):
- opencv-python (cv2)
- pytesseract
- flask
- flask-sqlalchemy
- ArduinoJson (ESP32 library)
- Arduino IDE with ESP32 board support
```

---

## Part 1: Flask Backend Setup

### Step 1: Install Dependencies

Add these packages to your `requirements.txt`:
```
opencv-python
pytesseract
numpy
pillow
```

Install them:
```bash
pip install -r requirements.txt
```

### Step 2: Update App Configuration

In `app.py`, ensure these configurations are set:

```python
# API Key for ESP32 authentication
app.config['ESP_API_KEY'] = os.environ.get('ESP_API_KEY', 'ESP32_SECRET_KEY')

# Upload folder for temporary image storage
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
```

### Step 3: Database Schema

Your `Booking` model already has the required fields:
- `vehicle_number`: License plate (e.g., "KA01AB1234")
- `start_time`: Booking start (DateTime)
- `end_time`: Booking end (DateTime)
- `status`: "active" or "cancelled"

The `/api/verify_plate` endpoint will query this with:
```sql
SELECT * FROM booking 
WHERE LOWER(vehicle_number) = LOWER(plate_text)
AND status = 'active'
AND start_time >= TODAY
AND start_time <= NOW
AND end_time > NOW
```

---

## Part 2: API Endpoints

### POST /api/verify_plate

Endpoint for ESP32-CAM to verify vehicle access.

**Request:**
```
POST /api/verify_plate HTTP/1.1
Host: your-flask-server:5000
Content-Type: image/jpeg
X-API-Key: ESP32_SECRET_KEY

[binary image data]
```

Or with Form Data:
```
POST /api/verify_plate HTTP/1.1
Host: your-flask-server:5000
X-API-Key: ESP32_SECRET_KEY
Content-Type: multipart/form-data

Form field: file = image.jpg
```

**Response (Authorized):**
```json
{
  "status": "AUTHORIZED",
  "vehicle_number": "KA01AB1234",
  "ocr_confidence": 87.5,
  "booking_details": {
    "booking_id": 42,
    "slot_number": 5,
    "start_time": "2026-03-01T10:00:00",
    "end_time": "2026-03-01T18:00:00",
    "vehicle_number": "KA01AB1234"
  }
}
```

**Response (Denied):**
```json
{
  "status": "DENIED",
  "vehicle_number": "KA01AB1234",
  "error": "No active booking found",
  "ocr_confidence": 85.3
}
```

**Response (OCR Failure):**
```json
{
  "status": "DENIED",
  "error": "Could not extract valid plate number",
  "confidence": null
}
```

---

## Part 3: Plate Extraction & Cleaning

### Plate Text Cleaning

The `clean_plate_text()` function performs:
1. **Remove special characters**: Strips spaces, dashes, special symbols
2. **Alphanumeric only**: Keeps only A-Z, 0-9
3. **Uppercase conversion**: Standardizes format

Examples:
```
Input: "KA-01-AB-1234" → Output: "KA01AB1234"
Input: "ka 01 ab 1234" → Output: "KA01AB1234"
Input: "KA.01.AB.1234" → Output: "KA01AB1234"
```

### Database Query Logic

```python
def verify_booking_for_plate(plate_number):
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())
    
    booking = Booking.query.filter(
        Booking.vehicle_number.ilike(plate_number),  # Case-insensitive
        Booking.status == "active",
        Booking.start_time >= today_start,            # Booking today
        Booking.start_time <= now,                    # Has started
        Booking.end_time > now                        # Not ended yet
    ).first()
    
    return booking is not None
```

---

## Part 4: ESP32-CAM Arduino Code

### Hardware Wiring

```
ESP32-CAM to Servo Motor:
GPIO 12    → Servo Signal (PWM)
GND        → Servo GND
5V (via external power supply) → Servo VCC

ESP32-CAM to Status LED:
GPIO 4     → LED (with 220Ω resistor to GND)
GND        → LED -

ESP32-CAM to WiFi/Power:
3.3V       → Power supply
GND        → Common GND
```

### Installation Steps

1. **Arduino IDE Setup**
   - Install ESP32 board package:
     - File → Preferences → Additional Board URLs
     - Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
     - Tools → Board Manager → Search "ESP32" → Install

2. **Install Required Libraries**
   - Sketch → Include Library → Manage Libraries
   - Search and install:
     - `ArduinoJson` (by Benoit Blanchon)
     - `ESP32Servo` (by John K. Bennett)

3. **Configure Your Credentials**
   
   Edit `esp32_gate_control.ino`:
   ```cpp
   const char* WIFI_SSID = "your_wifi_name";
   const char* WIFI_PASSWORD = "your_wifi_password";
   const char* SERVER_URL = "http://192.168.1.100:5000";  // Your Flask server IP
   const char* API_KEY = "ESP32_SECRET_KEY";  // Must match your Flask config
   ```

4. **Board Settings**
   - Board: ESP32 Dev Module
   - CPU Freq: 160 MHz
   - Flash: 4MB (QIO)
   - Partition Scheme: Default (4MB with spiffs)

5. **Upload**
   - Connect ESP32-CAM via USB
   - Select COM port
   - Click Upload

### Servo Motion Sequence

```cpp
void openGate() {
    gateServo.write(90);      // Open position
    delay(5000);               // Hold for 5 seconds
    gateServo.write(0);        // Close position
}
```

- **0°**: Gate closed (motor off)
- **90°**: Gate open (full rotation)
- **Hold time**: 5 seconds to allow vehicle to pass

---

## Part 5: Testing & Troubleshooting

### Test 1: Flask Endpoint

```bash
# Create a test image
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  --data-binary @test_image.jpg

# Check response
# Should return: {"status": "DENIED", "error": "Could not extract valid plate number"}
```

### Test 2: Database Query

```python
from app import app, Booking
from datetime import datetime

with app.app_context():
    now = datetime.now()
    bookings = Booking.query.filter(
        Booking.status == "active",
        Booking.start_time <= now,
        Booking.end_time > now
    ).all()
    
    for b in bookings:
        print(f"Active: {b.vehicle_number} - {b.start_time} to {b.end_time}")
```

### Test 3: ESP32 Serial Monitor

```
Connect ESP32, open Serial Monitor (115200 baud)
Expected output:
========================================
   Smart Parking Gate - ESP32-CAM
========================================
📡 Connecting to WiFi...
✅ WiFi connected!
IP Address: 192.168.x.x
📷 Initializing ESP32-CAM...
✅ Camera initialized!
🔧 Initializing servo motor...
✅ Servo initialized!

Starting gate verification loop...
📸 Capturing image...
🌐 Sending to: http://192.168.1.100:5000/api/verify_plate
📡 HTTP Response Code: 200
📋 Response: {"status": "AUTHORIZED", "vehicle_number": "KA01AB1234"...}
✅ ACCESS GRANTED!
🔓 Opening gate...
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "WiFi connection failed" | Check SSID/password, ensure 2.4GHz network |
| "HTTP Error: Connection refused" | Check Flask server IP, ensure server is running |
| "OCR returns empty string" | Low camera quality, adjust JPEG quality setting |
| "Servo doesn't move" | Check power supply, verify GPIO pin connections |
| "API key unauthorized" | Ensure X-API-Key header matches Flask config |

---

## Part 6: Booking Model Updates

Ensure your Booking table has these fields:

```python
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'))
    start_time = db.Column(db.DateTime)        # ← Required
    end_time = db.Column(db.DateTime)          # ← Required
    status = db.Column(db.String(20), default="active")  # ← Required
    vehicle_number = db.Column(db.String(20), nullable=True)  # ← Required
```

When creating bookings from your web interface, ensure vehicle_number is captured and stored.

---

## Part 7: Example Workflow

### User Books Parking

1. User registers vehicle: "KA01AB1234"
2. User books slot 5 for today from 10:00 AM to 6:00 PM
3. Booking stored in DB:
   ```
   {vehicle_number: "KA01AB1234", start_time: 2026-03-01 10:00, end_time: 2026-03-01 18:00, status: "active"}
   ```

### Vehicle Arrives at Gate

1. ESP32-CAM captures image of license plate
2. Sends HTTP POST with image to `/api/verify_plate`
3. Flask processes image:
   - OCR extracts: "KA-01-AB-1234"
   - Cleaned to: "KA01AB1234"
   - Queries database
4. Match found! Current time is 2:30 PM (within 10:00-18:00)
5. Returns: `{"status": "AUTHORIZED"}`
6. ESP32 rotates servo 90° → Gate opens
7. 5-second wait
8. Servo rotates back → Gate closes

### Vehicle Denied

If current time is 8:00 PM (beyond 18:00):
1. OCR extracts plate
2. Query finds booking but booking.end_time (18:00) < now (20:00)
3. No match in active condition
4. Returns: `{"status": "DENIED", "error": "No active booking found"}`
5. Servo stays at 0° → Gate remains closed

---

## Part 8: Security Considerations

1. **API Key**
   ```python
   # In .env file (never commit)
   export ESP_API_KEY="your-random-secret-key-32-chars"
   
   # Load in app.py
   app.config['ESP_API_KEY'] = os.environ.get('ESP_API_KEY')
   ```

2. **HTTPS (Production)**
   - Use HTTPS endpoint instead of HTTP
   - Deploy Flask with proper SSL certificates

3. **Rate Limiting**
   - Add rate limiting to `/api/verify_plate` to prevent abuse:
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=lambda: request.remote_addr)
   
   @app.route("/api/verify_plate", methods=["POST"])
   @limiter.limit("10 per minute")
   def verify_plate():
       ...
   ```

4. **Request Validation**
   - Verify Content-Type and Content-Length
   - Validate image data before processing

---

## Part 9: Advanced Features

### Motion Detection Trigger
```cpp
const int MOTION_SENSOR = 33;

void loop() {
    if (digitalRead(MOTION_SENSOR) == HIGH) {
        captureAndVerify();
        delay(5000);  // Cooldown
    }
}
```

### Local Web Interface
```cpp
// Add a web server to ESP32 for statistics, logs, configuration
#include <WebServer.h>
WebServer server(80);

void setup() {
    server.on("/", handleRoot);
    server.begin();
}

void loop() {
    server.handleClient();
}
```

### Offline Fallback
```cpp
// If server unreachable, check local time window
bool checkLocalTimeWindow() {
    // Open gate between 6 AM - 10 PM based on RTC
    return hour >= 6 && hour < 22;
}
```

### Logging to SPIFFS
```cpp
#include <SPIFFS.h>
void logAccess(String vehicle, String status) {
    File f = SPIFFS.open("/log.txt", "a");
    f.println(vehicle + " - " + status + " - " + getTime());
    f.close();
}
```

---

## Troubleshooting Checklist

- [ ] Flask server running on correct IP and port
- [ ] X-API-Key header matches in both Flask and ESP32
- [ ] Database has active bookings with matching vehicle numbers
- [ ] Camera captures clear images of license plates
- [ ] Servo power supply is adequate (5V minimum 1A)
- [ ] WiFi 2.4GHz network (not 5GHz)
- [ ] ESP32 Serial Monitor shows "✅ WiFi connected!"
- [ ] Booking start_time/end_time are DateTime, not just dates

---

## File Structure

```
smart_parking_system/
├── app.py                    # Updated with /api/verify_plate
├── plate_processor.py       # Existing OCR logic (unchanged)
├── requirements.txt         # Updated with cv2, pytesseract
├── esp32/
│   ├── esp32_gate_control.ino    # Main gate control sketch
│   ├── esp32_cam_upload.ino      # Existing upload sketch
│   └── esp32_slot.ino            # Existing slot update sketch
├── instance/uploads/        # Temporary image storage
└── static/processed/        # Processed plate images
```

---

## Support & Next Steps

1. **Test with single booking** before adding multiple vehicles
2. **Monitor logs** in Flask terminal for errors
3. **Use a motion sensor** to reduce unnecessary network traffic
4. **Implement backup power** for servo in case of outages
5. **Add access logs** to track all gate events for debugging

---

Last Updated: March 1, 2026
Version: 1.0
