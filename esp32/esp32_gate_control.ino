#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include <driver/rtc_io.h>
#include <ESP32Servo.h>

// ==================== CONFIGURATION ====================

// WiFi Credentials
const char* WIFI_SSID = "Vishu";
const char* WIFI_PASSWORD = "12345678";

// Server Configuration
const char* SERVER_URL = "http://10.79.56.251:5000"; // Change to your Flask server IP
const char* API_ENDPOINT = "/api/verify_plate";
const char* API_KEY = "ESP32_SECRET_KEY"; // Must match app.config['ESP_API_KEY']

// Servo Configuration
const int SERVO_PIN = 32; // GPIO 32 (Warning: Conflict with Camera PWDN)
Servo gateServo;
const int SERVO_CLOSED = 0;     // Closed position
const int SERVO_OPEN = 90;      // Open position
const int GATE_OPEN_TIME = 5000; // 5 seconds

// Camera Configuration
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Status LED
const int STATUS_LED = 4; // GPIO 4 - Indicate authorization status

// ==================== FUNCTION DECLARATIONS ====================

void initWiFi();
void initCamera();
void initServo();
void captureAndVerify();
void openGate();
void closeGate();
void handleAuthorized();
void handleDenied();
void blinkLED(int color, int count); // 1=green, 2=red

// ==================== SETUP ====================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("========================================");
    Serial.println("   Smart Parking Gate - ESP32-CAM");
    Serial.println("========================================");
    
    // Initialize components
    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, LOW);
    
    initWiFi();
    initCamera();
    initServo();
    
    closeGate(); // Start with gate closed
    
    Serial.println("\n✅ System initialized successfully!");
    Serial.println("Starting gate verification loop...\n");
}

// ==================== LOOP ====================

void loop() {
    // Check if WiFi is still connected
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("⚠️ WiFi disconnected. Reconnecting...");
        initWiFi();
        delay(5000);
        return;
    }
    
    // Capture image and verify
    captureAndVerify();
    
    // Wait before next capture (prevents excessive requests)
    delay(2000);
}

// ==================== INITIALIZATION ====================

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

void initCamera() {
    Serial.println("📷 Initializing ESP32-CAM...");
    
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 10; // 0-63, lower = higher quality
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;
    
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("❌ Camera init failed with error 0x%x\n", err);
        return;
    }
    
    Serial.println("✅ Camera initialized!");
}

void initServo() {
    Serial.println("🔧 Initializing servo motor...");
    gateServo.setPeriodHertz(50);
    gateServo.attach(SERVO_PIN, 1000, 2000); // Pin, min pulse, max pulse
    gateServo.write(SERVO_CLOSED);
    delay(500);
    Serial.println("✅ Servo initialized!");
}

// ==================== GATE CONTROL ====================

void openGate() {
    Serial.println("🔓 Opening gate...");
    gateServo.write(SERVO_OPEN);
    blinkLED(1, 3); // 3 green blinks
    delay(GATE_OPEN_TIME);
    closeGate();
}

void closeGate() {
    Serial.println("🔒 Closing gate...");
    gateServo.write(SERVO_CLOSED);
    delay(500);
}

void blinkLED(int color, int count) {
    // color: 1=green (authorized), 2=red (denied)
    // Simple implementation: blink once for now
    for (int i = 0; i < count; i++) {
        digitalWrite(STATUS_LED, HIGH);
        delay(100);
        digitalWrite(STATUS_LED, LOW);
        delay(100);
    }
}

// ==================== PLATE VERIFICATION ====================

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

// ==================== RESPONSE HANDLERS ====================

void handleAuthorized() {
    Serial.println("\n🎉 AUTHORIZING ACCESS...");
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━");
    blinkLED(1, 3);
    openGate();
    Serial.println("Gate cycle complete.\n");
}

void handleDenied() {
    Serial.println("\n🚫 ACCESS DENIED");
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━");
    blinkLED(2, 1);
    closeGate();
    Serial.println();
}

// ==================== UTILITY FUNCTIONS ====================

/*
 * OPTIONAL: Advanced features you can add:
 * 
 * 1. MOTION DETECTION:
 *    - Use an IR motion sensor on pin X to trigger capture only when vehicle detected
 *    - Reduces unnecessary network traffic
 * 
 * 2. LOGGING:
 *    - Store responses (authorized/denied) in SPIFFS flash memory
 *    - Periodically upload logs to server
 * 
 * 3. FALLBACK MODE:
 *    - If server unreachable, use preset authorized time window
 *    - Or open gate based on manual button press
 * 
 * 4. STATISTICS:
 *    - Track successful/failed authorizations
 *    - Display on local web interface (192.168.x.x web server)
 */
