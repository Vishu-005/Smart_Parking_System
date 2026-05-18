# Smart Parking Gate Control System - Complete Implementation

## 📍 START HERE

This is your guide to implementing automatic gate control for the Smart Parking System using ESP32-CAM and servo motor.

### Quick Navigation

**New to this project?** Start with:
1. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Overview & quick start (5 min read)
2. [HARDWARE_WIRING.md](HARDWARE_WIRING.md) - Hardware assembly guide (15 min read)
3. [GATE_CONTROL_SETUP.md](GATE_CONTROL_SETUP.md) - Complete setup instructions (30 min read)

**Need code details?**
- [GATE_CONTROL_CODE_REFERENCE.md](GATE_CONTROL_CODE_REFERENCE.md) - All code snippets
- [esp32_gate_control.ino](esp32/esp32_gate_control.ino) - Complete Arduino firmware

**Understanding the system?**
- [DATA_FLOW_DIAGRAMS.md](DATA_FLOW_DIAGRAMS.md) - Visual architecture & sequences
- [app.py](app.py) - Updated Flask backend (search for `/api/verify_plate`)

---

## 📦 What's Included

### Code Files
```
smart_parking_system/
├── app.py                           ✅ UPDATED with /api/verify_plate endpoint
├── plate_processor.py              (Existing - no changes needed)
├── esp32/
│   └── esp32_gate_control.ino      ✅ NEW - Complete ESP32-CAM firmware
└── requirements.txt                (Add: opencv-python, pytesseract)
```

### Documentation Files
```
smart_parking_system/
├── IMPLEMENTATION_SUMMARY.md       ✅ NEW - Overview, quick start, checklist
├── GATE_CONTROL_SETUP.md          ✅ NEW - Complete setup guide
├── GATE_CONTROL_CODE_REFERENCE.md ✅ NEW - Code snippets & examples
├── HARDWARE_WIRING.md             ✅ NEW - Wiring diagrams & pinouts
├── DATA_FLOW_DIAGRAMS.md          ✅ NEW - Architecture diagrams
└── GATE_CONTROL_INDEX.md          📄 This file
```

---

## 🚀 5-Minute Quick Start

### Prerequisites
- [ ] Python Flask server running
- [ ] PostgreSQL with parking_db
- [ ] ESP32-CAM development board
- [ ] Servo motor (SG90 or MG996R)
- [ ] Arduino IDE installed

### Step 1: Update Requirements
```bash
pip install opencv-python pytesseract numpy pillow
```

### Step 2: Configure ESP32 Code
Edit `esp32/esp32_gate_control.ino`:
```cpp
const char* WIFI_SSID = "your_wifi";
const char* WIFI_PASSWORD = "your_password";
const char* SERVER_URL = "http://192.168.1.100:5000";
```

### Step 3: Upload to ESP32
- Arduino IDE → Select ESP32 Dev Module
- Upload sketch
- Check Serial Monitor (115200 baud)
- Should see: "✅ WiFi connected!"

### Step 4: Test Authorization
```bash
# Create test booking
python
>>> from app import app, Booking, db
>>> from datetime import datetime, timedelta
>>> with app.app_context():
...     booking = Booking(
...         user_id=1, slot_id=1,
...         start_time=datetime.now(),
...         end_time=datetime.now() + timedelta(hours=8),
...         vehicle_number="KA01AB1234",
...         status="active"
...     )
...     db.session.add(booking)
...     db.session.commit()

# Test API
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  --data-binary @test_plate.jpg
```

Expected response:
```json
{"status": "AUTHORIZED", "vehicle_number": "KA01AB1234", ...}
```

---

## 📊 System Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────┐
│   ESP32-CAM     │────────►│  Flask Server    │────────►│ PostgreSQL   │
│  + Camera       │  HTTP   │  + OpenCV + OCR  │  Query  │  (Bookings)  │
│  + Servo Motor  │ POST    │                  │         │              │
│  + Status LED   │         │ /api/verify_     │         │              │
│                 │◄────────│  plate           │◄────────│              │
│                 │ Json    │                  │         │              │
└─────────────────┘         └──────────────────┘         └──────────────┘
        │                           │
        │ Capture License Plate    │ Extract plate number
        │ Send to Flask            │ Query database
        │ Receive AUTHORIZED/DENIED│ Return status
        │                          │
        ▼                          │
    ┌─────────────┐               │
    │ Open Gate   │◄──────────────┘
    │ 5 sec hold  │
    │ Close Gate  │
    └─────────────┘
```

---

## 🔄 Booking Authorization Flow

```
User Books Parking
    ↓
Booking stored: vehicle_number="KA01AB1234", start=10:00, end=18:00
    ↓
Vehicle arrives at gate at 2:30 PM
    ↓
ESP32-CAM captures license plate image
    ↓
Send image to Flask: POST /api/verify_plate
    ↓
Flask processes with OpenCV + pytesseract:
  - Extract text: "KA-01 AB-1234"
  - Clean to: "KA01AB1234"
    ↓
Database query:
  SELECT * FROM booking
  WHERE vehicle_number='KA01AB1234'
  AND status='active'
  AND start_time <= NOW
  AND end_time > NOW
    ↓
Match found! (Booking active from 10:00 to 18:00)
    ↓
Return: {"status": "AUTHORIZED"}
    ↓
ESP32 receives response
    ↓
Servo motor:
  - Rotate to 90° (OPEN)
  - Wait 5 seconds
  - Rotate to 0° (CLOSE)
    ↓
Vehicle passes through
```

---

## 📝 Key Components

### 1. Flask Endpoint: `/api/verify_plate`

**Purpose**: Accept image from ESP32-CAM, extract license plate, verify booking

**Input**: JPEG image (multipart/form-data or raw bytes)

**Output**:
```json
{
  "status": "AUTHORIZED" or "DENIED",
  "vehicle_number": "extracted plate",
  "ocr_confidence": 87.3,
  "booking_details": {...}  // if authorized
}
```

**Error Cases**:
- Invalid API key → 401
- No image data → 400
- OCR fails → 400
- No matching booking → DENIED status with error

### 2. Helper Functions

#### `clean_plate_text(text)`
- Input: "KA-01 AB-1234"
- Output: "KA01AB1234"
- Logic: Remove spaces/special chars, uppercase

#### `verify_booking_for_plate(plate_number)`
- Queries database for active booking
- Checks: vehicle_number match, status='active', datetime range
- Returns: (bool, booking_details)

### 3. ESP32-CAM Firmware

**Key Features**:
- WiFi connectivity
- Camera capture (640x480 JPEG)
- HTTP POST to Flask endpoint
- JSON response parsing
- Servo motor control
- Status LED feedback

**Servo Motion**:
- AUTHORIZED: 90° for 5 seconds, then back to 0°
- DENIED: Stay at 0° (gate closed)

### 4. Database Query Logic

```python
booking = Booking.query.filter(
    Booking.vehicle_number.ilike(plate_number),  # Case-insensitive
    Booking.status == "active",                  # Not cancelled
    Booking.start_time >= today_start,           # Started today
    Booking.start_time <= now,                   # Has started
    Booking.end_time > now                       # Not expired yet
).first()
```

---

## 🔧 Configuration

### Flask (app.py)
```python
app.config['ESP_API_KEY'] = os.environ.get('ESP_API_KEY', 'ESP32_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.config['PROCESSED_FOLDER'] = os.path.join('static', 'processed')
```

### ESP32 (Arduino)
```cpp
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* SERVER_URL = "http://192.168.1.100:5000";
const char* API_KEY = "ESP32_SECRET_KEY";
const int SERVO_PIN = 12;           // GPIO pin
const int SERVO_OPEN = 90;          // Degrees
const int SERVO_CLOSED = 0;         // Degrees
const int GATE_OPEN_TIME = 5000;    // Milliseconds
```

---

## 🧪 Testing

### Unit Tests
```bash
# Test OCR cleaning
python -c "from app import clean_plate_text; print(clean_plate_text('KA-01 AB-1234'))"
# Output: KA01AB1234 ✓

# Test database query
python -c "
from app import app, Booking
from datetime import datetime
with app.app_context():
    booking = Booking.query.filter(Booking.status=='active').first()
    print(booking.vehicle_number if booking else 'None')
"
```

### Integration Tests
```bash
# Test Flask endpoint
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  -H "Content-Type: image/jpeg" \
  --data-binary @plate.jpg
```

### Hardware Tests
```cpp
// In Arduino setup():
Serial.begin(115200);
testServoSweep();  // Should see full 0-180° rotation
```

---

## 📊 Performance Metrics

| Metric | Expected Time |
|--------|---|
| Image capture to transmission | 1-2 sec |
| Image transmission | 1-3 sec |
| OCR processing | 2-5 sec |
| Database query | <100 ms |
| **Total response time** | **5-12 sec** |
| Servo open + hold + close | 5-7 sec |

---

## 🔒 Security Features

- ✅ API key authentication (X-API-Key header)
- ✅ Case-insensitive database matching (prevents case-sensitivity bypass)
- ✅ Time-based authorization (prevents stale booking abuse)
- ✅ Status-based filtering (prevents cancelled booking reuse)
- ✅ SQLAlchemy ORM (prevents SQL injection)
- ✅ Temporary image cleanup (no permanent plate storage)

---

## 🐛 Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| `ESP32 won't connect to WiFi` | Check 2.4GHz network, verify credentials |
| `HTTP 401 Unauthorized` | X-API-Key header doesn't match Flask config |
| `No active booking found` | Create booking with matching vehicle_number |
| `OCR returns empty` | Improve lighting, angle camera perpendicular |
| `Servo doesn't move` | Verify GPIO 12 connection, check 5V power |
| `pytesseract not found` | `pip install pytesseract` + install tesseract-ocr |
| `Database error` | Ensure PostgreSQL running, check connection string |

For detailed troubleshooting, see [GATE_CONTROL_SETUP.md](GATE_CONTROL_SETUP.md#troubleshooting-checklist)

---

## 📚 Documentation Map

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Overview, quick start, checklist | 10 min |
| [HARDWARE_WIRING.md](HARDWARE_WIRING.md) | Hardware assembly, pinout diagrams, BOM | 15 min |
| [GATE_CONTROL_SETUP.md](GATE_CONTROL_SETUP.md) | Complete setup guide, API docs, examples | 30 min |
| [GATE_CONTROL_CODE_REFERENCE.md](GATE_CONTROL_CODE_REFERENCE.md) | Code snippets, database queries | 20 min |
| [DATA_FLOW_DIAGRAMS.md](DATA_FLOW_DIAGRAMS.md) | Architecture, sequence diagrams, flows | 15 min |
| [esp32_gate_control.ino](esp32/esp32_gate_control.ino) | Arduino firmware source code | 20 min |

---

## 🎯 Implementation Checklist

- [ ] Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- [ ] Verify Flask has opencv-python & pytesseract installed
- [ ] Assemble hardware per [HARDWARE_WIRING.md](HARDWARE_WIRING.md)
- [ ] Configure WiFi credentials in Arduino sketch
- [ ] Set Flask server IP in Arduino code
- [ ] Upload firmware to ESP32
- [ ] Verify "✅ WiFi connected!" on serial monitor
- [ ] Create test booking in database
- [ ] Test `/api/verify_plate` endpoint
- [ ] Verify servo opens/closes on response
- [ ] Test with actual license plate image

---

## 🎓 Learning Resources

- **OpenCV Documentation**: https://docs.opencv.org/
- **pytesseract**: https://github.com/madmaze/pytesseract
- **ArduinoJson**: https://arduinojson.org/
- **ESP32 Documentation**: https://docs.espressif.com/
- **Flask SQLAlchemy**: https://flask-sqlalchemy.palletsprojects.com/

---

## 📞 Support & Contact

For issues or questions:
1. Check [GATE_CONTROL_SETUP.md](GATE_CONTROL_SETUP.md#troubleshooting-checklist) troubleshooting section
2. Review [DATA_FLOW_DIAGRAMS.md](DATA_FLOW_DIAGRAMS.md) for system architecture
3. Check Serial Monitor output on ESP32 for detailed error messages
4. Review Flask terminal for OCR and database query logs

---

## 🎉 You're Ready!

Everything is implemented and documented. Start with the Quick Start above and refer to the documentation as needed.

**Next step**: Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for detailed setup instructions.

---

*Last Updated: March 1, 2026*
*Version: 1.0 - Complete Implementation*
