# Smart Parking Gate Control - Pre-Deployment Checklist

## 🚀 Before Going Live

This checklist ensures all components are properly configured and tested before deploying to production.

---

## 📦 Code & Dependencies

- [ ] **Python Dependencies Installed**
  ```bash
  pip install -r requirements.txt
  # Should include: flask, flask-sqlalchemy, opencv-python, pytesseract, numpy
  ```

- [ ] **pytesseract System Installation**
  ```bash
  # Windows: Download tesseract-ocr installer
  # https://github.com/UB-Mannheim/tesseract/wiki
  # Or: choco install tesseract
  
  # macOS: brew install tesseract
  
  # Linux: sudo apt-get install tesseract-ocr
  ```

- [ ] **Flask Backend Functional**
  ```bash
  python app.py
  # Should start without errors
  # Should show: "Running on http://127.0.0.1:5000"
  ```

- [ ] **Database Connected**
  - [ ] PostgreSQL service running
  - [ ] Database `parking_db` exists
  - [ ] Connection string correct in `app.py`
  ```python
  # Should be able to:
  flask shell
  >>> from app import db
  >>> db.engine.execute("SELECT 1")
  ```

- [ ] **All HTML Templates Present**
  - [ ] templates/index.html
  - [ ] templates/book.html
  - [ ] templates/admin.html
  - [ ] templates/login.html
  - [ ] templates/register.html

---

## 🔌 Hardware Assembly

### Servo Motor
- [ ] Connected to GPIO 12 (signal)
- [ ] Connected to GND (ground)
- [ ] Connected to 5V external power supply (NOT USB)
- [ ] Servo moves to 0° when powered on
- [ ] Servo responds to angle commands

### Status LED
- [ ] Connected to GPIO 4
- [ ] 220Ω resistor in series
- [ ] LED polarity correct (longer leg toward GPIO)
- [ ] LED blinks when powered

### Camera
- [ ] OV2640 JST connector fully inserted
- [ ] Camera lens clean
- [ ] Camera captures images without errors

### Power Supply
- [ ] 5V/2A supply for servo (separate from USB)
- [ ] USB power for ESP32 (3.3V/1A minimum)
- [ ] Common ground between ESP32 and servo power
- [ ] No voltage drops on power lines

---

## ⚙️ ESP32 Configuration

### Arduino IDE
- [ ] Arduino IDE installed (latest version)
- [ ] ESP32 board package installed
- [ ] ArduinoJson library installed
- [ ] ESP32Servo library installed

### Code Configuration
Edit `esp32/esp32_gate_control.ino`:

- [ ] WiFi SSID set to your network name
  ```cpp
  const char* WIFI_SSID = "your_network";
  ```

- [ ] WiFi password set correctly
  ```cpp
  const char* WIFI_PASSWORD = "your_password";
  ```

- [ ] Flask server IP address set (e.g., `192.168.1.100`)
  ```cpp
  const char* SERVER_URL = "http://192.168.1.100:5000";
  ```

- [ ] API key matches Flask config
  ```cpp
  const char* API_KEY = "ESP32_SECRET_KEY";
  ```

- [ ] GPIO pin assignments verified
  ```cpp
  const int SERVO_PIN = 12;      // GPIO 12
  const int STATUS_LED = 4;      // GPIO 4
  ```

### Upload Settings
- [ ] Board: ESP32 Dev Module
- [ ] CPU Freq: 160 MHz
- [ ] Flash: 4MB (QIO)
- [ ] Partition Scheme: Default (4MB with spiffs)
- [ ] Port: Correct COM port selected

### Upload & Verify
- [ ] Sketch uploaded without errors
- [ ] Serial monitor opens (115200 baud)
- [ ] Shows boot messages
- [ ] Shows "✅ WiFi connected!"
- [ ] Shows Flask server connection message

---

## 📱 Flask Endpoint Verification

### Test with curl
```bash
# Create test image first (or use existing license plate photo)
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  -H "Content-Type: image/jpeg" \
  --data-binary @test_plate.jpg

# Should return JSON response (even if DENIED)
# ✅ Response code: 200
# ✅ Contains "status" field
```

### Test Responses
- [ ] Valid image returns 200 status
  ```json
  {"status": "AUTHORIZED" or "DENIED", "vehicle_number": "...", ...}
  ```

- [ ] Invalid API key returns 401
  ```json
  {"status": "DENIED", "error": "Invalid API key"}
  ```

- [ ] No image returns 400
  ```json
  {"status": "DENIED", "error": "No image data provided"}
  ```

- [ ] OCR failure returns 400
  ```json
  {"status": "DENIED", "error": "Could not extract valid plate number"}
  ```

---

## 🗄️ Database Configuration

### Booking Table
- [ ] `vehicle_number` column exists (VARCHAR(20))
- [ ] `start_time` column exists (DATETIME)
- [ ] `end_time` column exists (DATETIME)
- [ ] `status` column exists (VARCHAR(20), default='active')
- [ ] Check constraints on status values

### Test Data
- [ ] At least one active booking created
- [ ] Booking has valid vehicle_number
- [ ] Booking time range includes current time
- [ ] Status is 'active'

```python
# Test query:
from app import app, Booking
from datetime import datetime

with app.app_context():
    booking = Booking.query.filter_by(status='active').first()
    if booking:
        print(f"✅ Found booking: {booking.vehicle_number}")
    else:
        print("⚠️ No active bookings found")
```

---

## 🔒 Security Configuration

### API Key
- [ ] Generate secure random API key (32+ characters)
  ```python
  import secrets
  api_key = secrets.token_hex(16)  # 32 chars
  print(api_key)
  ```

- [ ] Store in environment variable
  ```bash
  export ESP_API_KEY="your_secure_key_here"
  ```

- [ ] Never commit to git
- [ ] Match in both Flask and ESP32 code

### Credentials
- [ ] WiFi password not visible in code
- [ ] Database connection string has secure password
- [ ] PostgreSQL user has minimal required permissions
- [ ] Flask SECRET_KEY is unique (not default)

### Network
- [ ] Using WPA2/WPA3 WiFi encryption
- [ ] WiFi router password strong
- [ ] Consider HTTPS for production (requires SSL certificate)

---

## ✅ End-to-End Testing

### Test 1: Happy Path (Authorized)
```
1. Create booking: vehicle_number="KA01AB1234", today 10:00-18:00
2. Capture license plate image
3. Send to /api/verify_plate
4. Verify response: {"status": "AUTHORIZED"}
5. Observe: Servo moves to 90°
6. Wait 5 seconds
7. Servo returns to 0°
8. Gate closes
```

- [ ] Booking created successfully
- [ ] Image captured clearly
- [ ] Flask returns AUTHORIZED
- [ ] Servo opens gate
- [ ] Gate holds for 5 seconds
- [ ] Gate closes automatically

### Test 2: Denied - No Booking
```
1. Create image of license plate: KA99ZZ9999 (doesn't exist in DB)
2. Send to /api/verify_plate
3. Verify response: {"status": "DENIED", "error": "No active booking found"}
4. Observe: Servo stays at 0° (gate closed)
```

- [ ] Correct DENIED status
- [ ] Appropriate error message
- [ ] Servo stays closed

### Test 3: Denied - Expired Booking
```
1. Create booking with end_time in the past
2. Current time is after end_time
3. Capture matching license plate
4. Send to /api/verify_plate
5. Verify response: {"status": "DENIED"}
```

- [ ] Expired booking correctly rejected
- [ ] Servo stays closed

### Test 4: Denied - Not Yet Started
```
1. Create booking with start_time in the future
2. Current time is before start_time
3. Capture matching license plate
4. Send to /api/verify_plate
5. Verify response: {"status": "DENIED"}
```

- [ ] Future booking correctly rejected
- [ ] Servo stays closed

### Test 5: OCR Accuracy
```
1. Test with various license plate images
2. Expected plates: KA01AB1234, MH02CD5678, AP03EF9999
3. Verify extraction accuracy
```

- [ ] OCR extracts correct plate (±1 character acceptable)
- [ ] Cleaning function removes special chars
- [ ] Case conversion works correctly

---

## 📊 Performance Validation

### Timing
- [ ] Image capture: < 2 seconds
- [ ] Image transmission: < 3 seconds  
- [ ] OCR processing: < 5 seconds
- [ ] Database query: < 100ms
- [ ] Total response: < 12 seconds
- [ ] Servo cycle: 5-7 seconds

### Load Testing
- [ ] Send 5 images in rapid succession - no crashes
- [ ] Check memory usage on ESP32 - no overflow
- [ ] Monitor Flask logs - no database connection issues

---

## 🐛 Error Scenarios

Test each error condition:

- [ ] **No WiFi**: ESP32 retries and shows "⚠️ WiFi disconnected"
- [ ] **Server unreachable**: ESP32 shows HTTP error, gate stays closed
- [ ] **Corrupted image**: Flask returns 400, gate stays closed
- [ ] **OCR fails**: Flask returns 400, gate stays closed
- [ ] **Database error**: Flask returns error JSON, gate stays closed
- [ ] **Invalid API key**: Flask returns 401, gate stays closed
- [ ] **Servo power loss**: Gate stays in last position
- [ ] **LED power loss**: Gate still operates (LED independent)

---

## 📋 Production Deployment

### Before Live
- [ ] All tests in this checklist passed
- [ ] Documentation reviewed and understood
- [ ] Hardware physically secured
- [ ] Environmental factors considered (weatherproofing)
- [ ] Backup systems in place (manual override)
- [ ] Monitoring system ready (logs, alerts)

### Initial Deployment
- [ ] Deploy ESP32 firmware
- [ ] Verify first 5 vehicle authorizations
- [ ] Monitor logs for errors
- [ ] Check servo mechanical operation
- [ ] Plan 24/7 monitoring

### Post-Deployment
- [ ] Monitor ESP32 serial logs for errors
- [ ] Check Flask server logs daily
- [ ] Review unauthorized access attempts
- [ ] Verify database backups working
- [ ] Test manual gate override monthly

---

## 📞 Troubleshooting Quick Reference

| Problem | Check | Fix |
|---------|-------|-----|
| ESP32 won't WiFi | SSID/password | Re-enter credentials |
| API returns 401 | API key match | Update both configs |
| API returns 400 | Image format | Use JPEG, ensure valid |
| No database match | vehicle_number | Ensure booking created |
| Servo doesn't move | GPIO 12, power | Verify connections |
| OCR returns empty | Image quality | Improve lighting |

---

## ✨ Sign-Off

**System Tested By**: ________________

**Date**: ________________

**Status**: 
- [ ] Ready for Production
- [ ] Ready for Testing
- [ ] Minor Issues (Document below)
- [ ] Major Issues (Do not deploy)

**Notes**:
```
_________________________________
_________________________________
_________________________________
```

---

## 🎓 Final Verification

Run this final test script before going live:

```python
# test_deployment.py
from app import app, Booking, db, clean_plate_text, verify_booking_for_plate
from datetime import datetime, timedelta
import json

print("=" * 50)
print("  SMART PARKING GATE - DEPLOYMENT TEST")
print("=" * 50)

with app.app_context():
    # Test 1: Database connection
    print("\n[1] Testing database connection...")
    try:
        booking_count = Booking.query.count()
        print(f"    ✅ Database connected. Total bookings: {booking_count}")
    except Exception as e:
        print(f"    ❌ Database error: {e}")
        exit(1)
    
    # Test 2: Clean plate text
    print("\n[2] Testing plate cleaning function...")
    test_plates = [
        ("KA-01 AB-1234", "KA01AB1234"),
        ("ka01ab1234", "KA01AB1234"),
        ("KA.01.AB.1234", "KA01AB1234"),
    ]
    for dirty, expected in test_plates:
        result = clean_plate_text(dirty)
        status = "✅" if result == expected else "❌"
        print(f"    {status} {dirty} → {result} (expected {expected})")
    
    # Test 3: Booking verification
    print("\n[3] Testing booking verification...")
    active_booking = Booking.query.filter_by(status='active').first()
    if active_booking:
        plate = active_booking.vehicle_number
        is_auth, details = verify_booking_for_plate(plate)
        status = "✅" if is_auth else "❌"
        print(f"    {status} Plate {plate}: {'AUTHORIZED' if is_auth else 'DENIED'}")
        if details:
            for k, v in details.items():
                print(f"       - {k}: {v}")
    else:
        print("    ⚠️  No active bookings found. Create test booking first.")
    
    # Test 4: Flask endpoint availability
    print("\n[4] Testing Flask endpoint...")
    with app.test_client() as client:
        response = client.post('/api/verify_plate', 
                              data=b'test',
                              headers={'X-API-Key': app.config['ESP_API_KEY'],
                                      'Content-Type': 'image/jpeg'})
        print(f"    ✅ Endpoint accessible (Status: {response.status_code})")
    
    print("\n" + "=" * 50)
    print("  ✅ DEPLOYMENT TEST COMPLETE")
    print("=" * 50)
```

Run it:
```bash
python test_deployment.py
```

---

**All checks passed? You're ready for production!** 🎉

Refer to [GATE_CONTROL_INDEX.md](GATE_CONTROL_INDEX.md) for documentation index.
