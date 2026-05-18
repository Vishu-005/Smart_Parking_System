# Smart Parking Gate Control - Data Flow & Sequence Diagrams

## System Architecture Diagram

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                    SMART PARKING GATE CONTROL SYSTEM                          ║
╚════════════════════════════════════════════════════════════════════════════════╝

                      ┌──────────────────────────────────────────┐
                      │        PHYSICAL LAYER                    │
                      │                                          │
                      │  ┌──────────────┐    ┌─────────────┐   │
                      │  │  ESP32-CAM   │◄──►│  OV2640     │   │
                      │  │              │    │  Camera     │   │
                      │  │  ┌─────────┐ │    └─────────────┘   │
                      │  │  │ Servo   │ │                      │
                      │  │  │ GPIO 12 │ │    ┌─────────────┐   │
                      │  │  └─────────┘ │    │  Status LED │   │
                      │  │  ┌─────────┐ │    │  GPIO 4     │   │
                      │  │  │ WiFi    │ │    └─────────────┘   │
                      │  │  │ Module  │ │                      │
                      │  └──────────────┘                       │
                      │         │                               │
                      │         │ HTTP + TLS (optional)         │
                      │         ▼                               │
                      └──────────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
    ┌─────────────────────────┐   ┌─────────────────────────┐
    │   FLASK SERVER          │   │  Network               │
    │   (Your PC / Laptop)    │   │  ┌─────────────────┐   │
    │                         │   │  │  WiFi Router    │   │
    │  ┌─────────────────┐   │   │  │  2.4 GHz        │   │
    │  │  /api/verify_   │   │   │  └─────────────────┘   │
    │  │  plate          │   │   └─────────────────────────┘
    │  │  ┌───────────┐  │   │
    │  │  │ OpenCV   │  │   │
    │  │  │ Tesseract│  │   │
    │  │  │ OCR      │  │   │
    │  │  └───────────┘  │   │
    │  └─────────────────┘   │
    │                         │
    │  ┌─────────────────┐   │
    │  │  SQLAlchemy    │   │
    │  │  Database      │   │
    │  │  Query Engine  │   │
    │  └────────┬────────┘   │
    └───────────┼─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  POSTGRESQL DATABASE    │
    │                         │
    │  ┌─────────────────┐   │
    │  │  Bookings Table │   │
    │  │                 │   │
    │  │ ID | vehicle_   │   │
    │  │    | number     │   │
    │  │    | start_time │   │
    │  │    | end_time   │   │
    │  │    | status     │   │
    │  │    | slot_id    │   │
    │  └─────────────────┘   │
    │                         │
    │  ┌─────────────────┐   │
    │  │  Slots Table    │   │
    │  │  (Location data)│   │
    │  └─────────────────┘   │
    │                         │
    └─────────────────────────┘
```

## Request-Response Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│             VEHICLE ARRIVAL TO GATE AUTHORIZATION FLOW                  │
└─────────────────────────────────────────────────────────────────────────┘

    TIME    │ ESP32-CAM               │ Flask Server         │ PostgreSQL
            │                         │                      │
    T+0s    │ [Motion Detected]       │                      │
            │ Capture Image           │                      │
            │ ◄─ JPEG (150-300 KB)    │                      │
            │                         │                      │
    T+1-2s  │ Encode JPEG             │                      │
            │ Prepare HTTP POST       │                      │
            │                         │                      │
    T+2-3s  │ Connect WiFi            │                      │
            │ Open TCP Socket         │                      │
            │ Transmit Image ──────────► Receive HTTP POST   │
            │    [200 KB] ►►►          │                      │
            │                         │ Save temp image      │
            │                         │ (instance/uploads/)  │
            │                         │                      │
    T+3-5s  │                         │ Import plate_        │
            │                         │ processor.py         │
            │                         │ Call process_image() │
            │                         │ ├─ Enhance image     │
            │                         │ ├─ Find plate region │
            │                         │ ├─ Pytesseract OCR   │
            │                         │ └─ Returns text      │
            │                         │ ("KA201AB1234")      │
            │                         │                      │
    T+5-6s  │                         │ Call clean_plate_    │
            │                         │ text()               │
            │                         │ ("KA01AB1234")       │
            │                         │                      │
    T+6-7s  │                         │ Call verify_booking_ │
            │                         │ for_plate()          │
            │                         │ ├─ Get current time  │
            │                         │ ├─ Build query       │
            │                         │ ├─ Filter:           │
            │                         │ │ ├─vehicle match    │
            │                         │ │ ├─status='active'  │
            │                         │ │ ├─today only       │
            │                         │ │ └─time in range    │
            │                         │ └─ Execute query ────► SELECT * FROM
            │                         │                       booking WHERE
            │                         │                       vehicle_number
            │                         │                       ='KA01AB1234'
            │                         │                       AND ...
            │                         │ ◄────────────────── [Row Found]
            │                         │                      │
    T+7-8s  │                         │ Parse booking        │
            │                         │ Build JSON response: │
            │                         │ {                    │
            │                         │   status:"AUTH"      │
            │                         │   vehicle:"KA01AB..."│
            │                         │   booking_details... │
            │                         │ }                    │
            │                         │                      │
    T+8s    │ ◄──────────────────────── HTTP 200 OK         │
            │ Receive JSON response   │ (JSON payload)       │
            │                         │                      │
    T+8.1s  │ Parse JSON              │                      │
            │ Check status            │                      │
            │ IF "AUTHORIZED":        │                      │
            │                         │                      │
    T+8.5s  │ Call openGate()         │                      │
            │ Set servo = 90°         │                      │
            │ [Servo rotates]         │                      │
            │ LED blinks 3x green     │                      │
            │                         │                      │
    T+8.5s  │ [GATE OPENS]            │                      │
    to      │ ║                       │                      │
    T+13.5s │ ║ Wait 5 seconds        │                      │
            │ ║                       │                      │
    T+13.5s │ Set servo = 0°          │                      │
            │ [Servo rotates back]    │                      │
            │                         │                      │
    T+14s   │ [GATE CLOSES]           │                      │
            │ ║                       │                      │
            │                         │                      │
            │                         │                      │
            │ IF "DENIED":            │                      │
            │ LED blinks 1x red       │                      │
            │ Keep servo = 0°         │                      │
            │ [GATE REMAINS CLOSED]   │                      │

TOTAL TIME: ~8 seconds (capture to response)
         OR ~14 seconds (full gate cycle if authorized)
```

## Database Query Sequence

```
┌──────────────────────────────────────────────────────────────────┐
│  DATABASE QUERY FOR BOOKING VERIFICATION                        │
└──────────────────────────────────────────────────────────────────┘

EXTRACTED PLATE: "KA01AB1234"
CURRENT TIME: 2026-03-01 14:30:00

QUERY LOGIC:
┌──────────────────────────────────────────────────────────┐
│ SELECT * FROM booking                                    │
│ WHERE LOWER(vehicle_number) = LOWER('KA01AB1234')       │
│   AND status = 'active'                                 │
│   AND DATE(start_time) = '2026-03-01'      ← TODAY      │
│   AND start_time <= '2026-03-01 14:30:00'  ← STARTED    │
│   AND end_time > '2026-03-01 14:30:00'     ← NOT ENDED  │
│ LIMIT 1                                                 │
└──────────────────────────────────────────────────────────┘

EXAMPLE DATA IN DATABASE:
┌─────┬──────────────┬─────────────┬─────────────┬────────┐
│ ID  │ vehicle_     │ start_time  │ end_time    │ status │
│     │ number       │             │             │        │
├─────┼──────────────┼─────────────┼─────────────┼────────┤
│ 40  │ KA01AB1234   │ 2026-03-01  │ 2026-03-01  │ active │
│     │              │ 10:00:00    │ 18:00:00    │        │
├─────┼──────────────┼─────────────┼─────────────┼────────┤
│ 41  │ KA02XY5678   │ 2026-03-01  │ 2026-03-01  │ active │
│     │              │ 14:00:00    │ 16:00:00    │        │
├─────┼──────────────┼─────────────┼─────────────┼────────┤
│ 42  │ KA01AB1234   │ 2026-03-02  │ 2026-03-02  │ active │
│     │              │ 09:00:00    │ 17:00:00    │        │
└─────┴──────────────┴─────────────┴─────────────┴────────┘

MATCHING CRITERIA EVALUATION:

FOR BOOKING ID 40 (KA01AB1234):
✓ LOWER(vehicle_number) = LOWER('KA01AB1234')
  └─ 'ka01ab1234' = 'ka01ab1234' ✓ MATCH

✓ status = 'active'
  └─ 'active' = 'active' ✓ MATCH

✓ DATE(start_time) = '2026-03-01'
  └─ DATE(2026-03-01 10:00:00) = '2026-03-01' ✓ MATCH

✓ start_time <= '2026-03-01 14:30:00'
  └─ 2026-03-01 10:00:00 ≤ 2026-03-01 14:30:00 ✓ MATCH

✓ end_time > '2026-03-01 14:30:00'
  └─ 2026-03-01 18:00:00 > 2026-03-01 14:30:00 ✓ MATCH

RESULT: ✅ FOUND - BOOKING ID 40
→ STATUS: AUTHORIZED

FOR BOOKING ID 41 (KA02XY5678):
✗ LOWER(vehicle_number) = LOWER('KA01AB1234')
  └─ 'ka02xy5678' ≠ 'ka01ab1234' ✗ NO MATCH
→ SKIPPED

FOR BOOKING ID 42 (KA01AB1234, but tomorrow):
✓ LOWER(vehicle_number) = LOWER('KA01AB1234')
  └─ 'ka01ab1234' = 'ka01ab1234' ✓ MATCH

✓ status = 'active'
  └─ 'active' = 'active' ✓ MATCH

✗ DATE(start_time) = '2026-03-01'
  └─ DATE(2026-03-02 09:00:00) = '2026-03-02' ✗ NO MATCH
  └─ EXPECTED: 2026-03-01, GOT: 2026-03-02
→ SKIPPED

FINAL RESULT: AUTHORIZED
└─ Booking 40 matches all criteria
└─ Vehicle can proceed
└─ Gate opens
```

## OCR Process Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  LICENSE PLATE EXTRACTION & CLEANING                            │
└──────────────────────────────────────────────────────────────────┘

STEP 1: CAPTURE RAW IMAGE
┌──────────────────────────┐
│  ESP32-CAM JPEG Image    │
│  (640x480 @ 10 quality)  │
│  ~200-300 KB             │
└──────────────────────────┘

STEP 2: TRANSMIT TO FLASK
        │
        ▼ HTTP POST with X-API-Key header
        └──► Flask /api/verify_plate endpoint

STEP 3: SAVE TEMPORARILY
┌──────────────────────────┐
│ instance/uploads/        │
│ 20260301142530_abc...jpg │
│ (deleted after processing)
└──────────────────────────┘

STEP 4: OPENCV ENHANCEMENT
        ├─ Convert BGR → Grayscale
        │  RGB pixels → Single intensity value
        │
        ├─ Bilateral Filter
        │  Denoise while preserving edges
        │  [9, 75, 75] parameters
        │
        ├─ CLAHE (Contrast Limited Adaptive
        │  Histogram Equalization)
        │  Local contrast enhancement
        │  Tile size: 8x8
        │
        └─ Sharpen with Kernel
           ┌────────┐
           │ 0 -1 0 │
           │-1  5 -1│
           │ 0 -1 0 │
           └────────┘

STEP 5: PLATE REGION DETECTION
        ├─ Gaussian Blur (5x5)
        ├─ Canny Edge Detection
        ├─ Find Contours
        ├─ Filter by:
        │  ├─ Shape: Quadrilateral (4-sided)
        │  ├─ Aspect Ratio: 2 to 8 (plate-like)
        │  └─ Area: 500 to 50% of image
        └─ Select largest candidate

STEP 6: OCR PREPROCESSING
        ├─ Convert to Grayscale
        ├─ Resize 2x (interpolation)
        ├─ Bilateral Filter
        ├─ Binary Thresholding (Otsu)
        │  White text on black background
        └─ Save processed image

STEP 7: PYTESSERACT OCR
        ├─ tesseract config: PSM 7
        │  └─ Treat as single text line
        ├─ Whitelist: A-Z 0-9 and dash
        │  └─ Ignore special characters
        └─ Extract confidence scores

        RESULT:
        Raw OCR Output: "KA-01 AB-1234"
        Confidence: 87.3%

STEP 8: TEXT CLEANING
        Raw:       "KA-01 AB-1234"
        Step 1:    Remove spaces/dashes/special chars
                   Regex: [^A-Za-z0-9]
        Result:    "KA01AB1234"
        Step 2:    Convert to uppercase
        Result:    "KA01AB1234"
        
        Final Output: "KA01AB1234"

STEP 9: DATABASE LOOKUP
        Query using cleaned plate: "KA01AB1234"
        ├─ AUTHORIZED ✓
        └─ DENIED ✗

STEP 10: RETURN RESPONSE
        {
          "status": "AUTHORIZED",
          "vehicle_number": "KA01AB1234",
          "ocr_confidence": 87.3,
          "booking_details": {...}
        }
```

## Decision Tree

```
┌──────────────┐
│ IMAGE SENT   │
└──────┬───────┘
       │
       ▼
   ┌─────────────┐        ┌─────────┐
   │ Decode JPEG │───NO──►│ DENIED  │
   │ successfully?│       │(Invalid)│
   └──────┬──────┘        └─────────┘
          │ YES
          ▼
   ┌─────────────┐        ┌─────────┐
   │ Save temp   │───FAIL─►│ DENIED  │
   │ image       │        │(I/O)    │
   └──────┬──────┘        └─────────┘
          │ YES
          ▼
   ┌─────────────┐        ┌─────────┐
   │ Process via │───FAIL─►│ DENIED  │
   │ pytesseract?│        │(OCR)    │
   └──────┬──────┘        └─────────┘
          │ YES
          ▼
   ┌──────────────┐       ┌─────────┐
   │ Extract text │──EMPTY►│ DENIED  │
   │ successfully?│       │(No Plate)
   └──────┬───────┘       └─────────┘
          │ GOT TEXT
          ▼
   ┌──────────────┐
   │  Clean text  │
   │  (uppercase, │
   │  alphanumeric)
   └──────┬───────┘
          │
          ▼
   ┌──────────────────┐   ┌─────────┐
   │ Query database   │───NONE─────►│ DENIED  │
   │ matching plate?  │   FOUND     │(No Bookg)
   └──────┬───────────┘             └─────────┘
          │ FOUND
          ▼
   ┌──────────────────┐   ┌─────────┐
   │ Status = 'active'│───NO──────►│ DENIED  │
   │ ?                │           │(Cancelled)
   └──────┬───────────┘           └─────────┘
          │ YES
          ▼
   ┌──────────────────┐   ┌─────────┐
   │ Booking date     │───NO──────►│ DENIED  │
   │ = TODAY ?        │           │(Wrong Dt)
   └──────┬───────────┘           └─────────┘
          │ YES
          ▼
   ┌──────────────────┐   ┌─────────┐
   │ NOW >=           │───NO──────►│ DENIED  │
   │ start_time ?     │           │(Not Strt)
   └──────┬───────────┘           └─────────┘
          │ YES
          ▼
   ┌──────────────────┐   ┌─────────┐
   │ NOW <            │───NO──────►│ DENIED  │
   │ end_time ?       │           │(Expired)
   └──────┬───────────┘           └─────────┘
          │ YES
          ▼
          ┌──────────────────────────┐
          │   ✅ AUTHORIZED          │
          │   Open Gate!             │
          │   Return booking details │
          └──────────────────────────┘
```

---

These diagrams provide visual reference for understanding the complete data flow and decision logic of the smart parking gate control system.
