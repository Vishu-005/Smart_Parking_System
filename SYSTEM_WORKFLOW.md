# Smart Parking System - Workflow Explanation

This document describes the interaction between the different components of the Smart Parking System.

## Architecture Components

1.  **ESP32-CAM**: Responsible for image acquisition and license plate transmission.
2.  **Flask Backend**: The central logic hub for OCR, booking verification, and automation.
3.  **ESP32 Main Controller**: Handles physical hardware like the gate servo and parking slot sensors.

## Operation Flow

### 1. Vehicle Entry & Verification
1.  **ESP32-CAM** detects a vehicle (or captures periodically) and takes a JPEG image.
2.  **ESP32-CAM** sends the image via `POST` to the Flask endpoint `/api/verify_plate`.
3.  **Flask Backend**:
    *   Receives the image.
    *   Uses `EasyOCR` or `Pytesseract` to extract the license plate text.
    *   Cleans the text and queries the `parking_db` for an active booking.
4.  **If Authorized**:
    *   Flask sends an HTTP `GET` request to `http://<ESP32_MAIN_IP>/open_gate`.
    *   The request includes the `X-API-Key` header for security.
5.  **ESP32 Main Controller**:
    *   Verifies the API key.
    *   Rotates the Servo (GPIO 23) to 90°.
    *   Waits for 5 seconds.
    *   Rotates the Servo back to 0°.

### 2. Slot Monitoring
1.  **ESP32 Main Controller** continuously monitors 5 IR sensors (GPIOs 12, 16, 17, 14, 15).
2.  Every 10 seconds, it compiles the occupancy status into a JSON payload.
3.  **ESP32 Main Controller** sends a `POST` request to `http://<BACKEND_IP>/update_slots`.
4.  **Flask Backend** updates the `Slot` table in the database, allowing the web dashboard to show real-time availability.

### 3. Automated Vehicle Exit
1.  **Flask Backend** runs a background scheduler (APScheduler) every 30 seconds.
2.  The scheduler identifies bookings that have passed their `end_time`.
3.  For each expired booking, Flask sends an HTTP `GET` request to `http://<ESP32_MAIN_IP>/exit_gate`.
4.  **ESP32 Main Controller** performs the same gate toggle logic to let the vehicle out.

---

## API Summary

| Endpoint | Method | Source | Destination | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/verify_plate` | POST | ESP32-CAM | Flask | Uploads image for OCR/Auth |
| `http://<ESP32_IP>/open_gate` | GET | Flask | ESP32 Main | Commands gate to open for ENTRY |
| `http://<ESP32_IP>/exit_gate` | GET | Flask | ESP32 Main | Commands gate to open for EXIT |
| `/update_slots` | POST | ESP32 Main | Flask | Updates real-time slot status |
