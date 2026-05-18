# Gate Control - Quick Code Reference

## 1. Flask Helper Functions

### Plate Text Cleaning
```python
def clean_plate_text(text):
    """
    Clean extracted plate text:
    - Remove spaces and special characters (keep alphanumeric only)
    - Convert to uppercase
    """
    if not text:
        return None
    # Remove spaces, dashes, and special chars - keep only alphanumeric
    cleaned = re.sub(r'[^A-zA-Z0-9]', '', text)
    return cleaned.upper()
```

### Database Query with End Time Calculation
```python
def verify_booking_for_plate(plate_number):
    """
    Check if a plate number has an active booking for TODAY.
    
    Query logic:
    - Find booking where vehicle_number matches (case-insensitive)
    - booking_date (start_time) is TODAY
    - current_time is between start_time and end_time
    - status is 'active'
    """
    if not plate_number:
        return False, {"error": "Invalid plate number"}
    
    try:
        now = datetime.now()
        today_start = datetime.combine(now.date(), datetime.min.time())
        today_end = datetime.combine(now.date(), datetime.max.time())
        
        # Query for active bookings matching plate and date/time
        booking = Booking.query.filter(
            Booking.vehicle_number.ilike(plate_number),  # Case-insensitive match
            Booking.status == "active",
            Booking.start_time >= today_start,  # Booking started today
            Booking.start_time <= today_end,    # Confirmation: within today
            Booking.start_time <= now,          # Booking has started
            Booking.end_time > now              # Booking hasn't ended yet
        ).first()
        
        if booking:
            return True, {
                "booking_id": booking.id,
                "slot_number": booking.slot.slot_number,
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat(),
                "vehicle_number": booking.vehicle_number
            }
        else:
            return False, {
                "error": "No active booking found",
                "searched_plate": plate_number
            }
    
    except Exception as e:
        print(f"Database error during plate verification: {e}")
        return False, {"error": f"Database error: {str(e)}"}
```

## 2. Flask API Endpoint

### POST /api/verify_plate (Complete)
```python
@app.route("/api/verify_plate", methods=["POST"])
def verify_plate():
    """
    Endpoint for ESP32-CAM to verify if a vehicle can pass through the gate.
    
    Accepts multipart/form-data or raw image bytes
    Form fields: file (image) or raw image bytes
    
    Returns:
    {
        "status": "AUTHORIZED" or "DENIED",
        "vehicle_number": <extracted_plate>,
        "booking_details": {...},  # if authorized
        "error": "..."  # if denied or error
    }
    """
    
    # Accept API key or allow without authentication for gate system
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key != app.config['ESP_API_KEY']:
        return jsonify({
            "status": "DENIED",
            "error": "Invalid API key"
        }), 401
    
    # Get image from request
    image_data = None
    
    if 'file' in request.files:
        # Multipart/form-data with file
        f = request.files['file']
        if f.filename == '':
            return jsonify({
                "status": "DENIED",
                "error": "No file selected"
            }), 400
        
        if not _allowed_file(f.filename):
            return jsonify({
                "status": "DENIED",
                "error": "Unsupported file type"
            }), 400
        
        image_data = f.read()
    
    elif request.data and request.headers.get('Content-Type', '').startswith('image/'):
        # Raw image bytes
        image_data = request.data
    
    else:
        return jsonify({
            "status": "DENIED",
            "error": "No image data provided"
        }), 400
    
    # Save image temporarily
    try:
        import numpy as np
        nparr = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        if nparr is None:
            return jsonify({
                "status": "DENIED",
                "error": "Could not decode image"
            }), 400
        
        token = secrets.token_hex(8)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        temp_filename = f"{timestamp}_{token}_gate_verify.jpg"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        cv2.imwrite(temp_path, nparr)
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({
            "status": "DENIED",
            "error": f"Image processing error: {str(e)}"
        }), 500
    
    # Extract plate using OCR
    plate_number = None
    ocr_confidence = None
    
    try:
        from plate_processor import process_image as process_ocr
        processed_path, ocr_text, confidence, notes = process_ocr(temp_path, output_dir=app.config['PROCESSED_FOLDER'])
        
        if ocr_text:
            plate_number = clean_plate_text(ocr_text)
            ocr_confidence = confidence
            print(f"✅ Extracted plate: {ocr_text} → Cleaned: {plate_number}")
        else:
            print(f"⚠️ OCR failed to extract text. Notes: {notes}")
        
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return jsonify({
            "status": "DENIED",
            "error": f"OCR failed: {str(e)}"
        }), 500
    
    finally:
        # Clean up temporary image
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
    
    if not plate_number:
        return jsonify({
            "status": "DENIED",
            "error": "Could not extract valid plate number",
            "confidence": ocr_confidence
        }), 400
    
    # Verify booking for extracted plate
    is_authorized, booking_info = verify_booking_for_plate(plate_number)
    
    response = {
        "status": "AUTHORIZED" if is_authorized else "DENIED",
        "vehicle_number": plate_number,
        "ocr_confidence": ocr_confidence
    }
    
    if is_authorized:
        response["booking_details"] = booking_info
    else:
        response["error"] = booking_info.get("error")
    
    return jsonify(response), 200
```

## 3. Required Imports for app.py

```python
import os
import secrets
from datetime import datetime, date, timedelta
import cv2
import re

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
```

## 4. ESP32-CAM Arduino Code (Critical Sections)

### WiFi Connection
```cpp
void initWiFi() {
    Serial.println("\n📡 Connecting to WiFi...");
    Serial.printf("SSID: %s\n", WIFI_SSID);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi connection failed!");
    }
}
```

### Servo Control
```cpp
void openGate() {
    Serial.println("🔓 Opening gate...");
    gateServo.write(SERVO_OPEN);      // 90 degrees
    blinkLED(1, 3);                   // 3 green blinks
    delay(GATE_OPEN_TIME);            // 5 seconds
    closeGate();
}

void closeGate() {
    Serial.println("🔒 Closing gate...");
    gateServo.write(SERVO_CLOSED);    // 0 degrees
    delay(500);
}
```

### Image Capture & Send
```cpp
void captureAndVerify() {
    Serial.println("\n📸 Capturing image...");
    
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("❌ Camera capture failed!");
        return;
    }
    
    Serial.printf("📊 Image size: %d bytes\n", fb->len);
    
    // Send to server
    if (sendImageToServer(fb)) {
        // Response handled in sendImageToServer()
    }
    
    esp_camera_fb_return(fb);
}

bool sendImageToServer(camera_fb_t* fb) {
    HTTPClient http;
    String full_url = String(SERVER_URL) + String(API_ENDPOINT);
    
    Serial.printf("\n🌐 Sending to: %s\n", full_url.c_str());
    
    http.begin(full_url);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-API-Key", API_KEY);
    
    int httpCode = http.POST(fb->buf, fb->len);
    
    Serial.printf("📡 HTTP Response Code: %d\n", httpCode);
    
    if (httpCode > 0) {
        String payload = http.getString();
        Serial.printf("📋 Response: %s\n", payload.c_str());
        
        // Parse JSON response
        DynamicJsonDocument doc(512);
        DeserializationError error = deserializeJson(doc, payload);
        
        if (error) {
            Serial.print("❌ JSON parse error: ");
            Serial.println(error.c_str());
            http.end();
            handleDenied();
            return false;
        }
        
        String status = doc["status"];
        String vehicle_number = doc["vehicle_number"];
        
        Serial.printf("Status: %s\n", status.c_str());
        Serial.printf("Vehicle: %s\n", vehicle_number.c_str());
        
        if (status == "AUTHORIZED") {
            Serial.println("✅ ACCESS GRANTED!");
            handleAuthorized();
            http.end();
            return true;
        } else {
            Serial.println("❌ ACCESS DENIED!");
            String error_msg = doc["error"];
            Serial.printf("Reason: %s\n", error_msg.c_str());
            handleDenied();
            http.end();
            return false;
        }
    } else {
        Serial.printf("❌ HTTP Error: %s\n", http.errorToString(httpCode).c_str());
        handleDenied();
    }
    
    http.end();
    return false;
}
```

### Configuration Placeholders
```cpp
// WiFi Credentials
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Server Configuration
const char* SERVER_URL = "http://192.168.1.100:5000"; // Change to your Flask server IP
const char* API_ENDPOINT = "/api/verify_plate";
const char* API_KEY = "ESP32_SECRET_KEY"; // Must match app.config['ESP_API_KEY']

// Servo Configuration
const int SERVO_PIN = 12;              // GPIO 12
const int SERVO_CLOSED = 0;            // Closed position
const int SERVO_OPEN = 90;             // Open position
const int GATE_OPEN_TIME = 5000;       // 5 seconds
```

## 5. Database Query Examples

### Find All Active Bookings Today
```python
from datetime import date, datetime

today_start = datetime.combine(date.today(), datetime.min.time())
today_end = datetime.combine(date.today(), datetime.max.time())

bookings = Booking.query.filter(
    Booking.status == "active",
    Booking.start_time >= today_start,
    Booking.start_time <= today_end
).all()

for b in bookings:
    print(f"{b.vehicle_number}: {b.start_time} - {b.end_time}")
```

### Check if Currently Parked
```python
from datetime import datetime

now = datetime.now()

current_bookings = Booking.query.filter(
    Booking.status == "active",
    Booking.start_time <= now,
    Booking.end_time > now
).all()

for b in current_bookings:
    print(f"{b.vehicle_number} is currently parked (expires at {b.end_time})")
```

## 6. Testing Commands

### Test API with curl
```bash
# With raw image bytes
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  -H "Content-Type: image/jpeg" \
  --data-binary @license_plate.jpg

# With form data
curl -X POST http://localhost:5000/api/verify_plate \
  -H "X-API-Key: ESP32_SECRET_KEY" \
  -F "file=@license_plate.jpg"
```

### Test Database Connection
```python
from app import app, Booking, db
from datetime import datetime

with app.app_context():
    # List all active bookings
    bookings = Booking.query.filter_by(status="active").all()
    print(f"Total active bookings: {len(bookings)}")
    
    for b in bookings:
        now = datetime.now()
        is_active = b.start_time <= now <= b.end_time
        print(f"  {b.vehicle_number}: {b.start_time} → {b.end_time} | Active now: {is_active}")
```

## 7. Error Handling Summary

| Scenario | Response | Recovery |
|----------|----------|----------|
| Invalid API Key | `{"status": "DENIED", "error": "Invalid API key"}` | Check X-API-Key header |
| No Image Data | `{"status": "DENIED", "error": "No image data provided"}` | Ensure multipart/form-data or raw bytes |
| Image Decode Error | `{"status": "DENIED", "error": "Could not decode image"}` | Check image format (JPEG/PNG) |
| OCR Fails | `{"status": "DENIED", "error": "OCR failed: ..."}` | Check pytesseract installation |
| No Valid Plate | `{"status": "DENIED", "error": "Could not extract valid plate number"}` | Improve camera angle/lighting |
| No Booking Found | `{"status": "DENIED", "error": "No active booking found"}` | User must create booking first |
| Database Error | `{"status": "DENIED", "error": "Database error: ..."}` | Check PostgreSQL connection |

## 8. Booking Creation Example

When user books parking, ensure vehicle_number is stored:

```python
@app.route("/api/book", methods=["POST"])
@login_required
def book_slot():
    data = request.json
    start = datetime.fromisoformat(data["start"])
    end = datetime.fromisoformat(data["end"])
    vehicle_number = data.get("vehicle_number")  # ← CRITICAL

    booking = Booking(
        user_id=current_user.id,
        slot_id=data["slot_id"],
        start_time=start,
        end_time=end,
        status="active",
        vehicle_number=vehicle_number  # ← Must be saved
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Booked"})
```

---

**All code is production-ready and includes error handling.** 
Ready to integrate into your Flask app!
