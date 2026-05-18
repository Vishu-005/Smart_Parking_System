#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include <ESP32Servo.h>
#include <WebServer.h>

// ================= WIFI =================
const char* ssid = "ESP8266";
const char* password = "123456789";

// ================= SERVER =================
const char* serverUrl = "http://10.38.243.251:5000/update_slots";
const char* gateVerifyUrl = "http://10.38.243.251:5000/api/verify_plate";
const char* API_KEY = "ESP32_SECRET_KEY";

// ================= CAMERA PINS (AI Thinker) =================
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

// ================= SERVO =================
const int SERVO_PIN = 13;
const int SERVO_CLOSED = 0;
const int SERVO_OPEN = 90;
const int GATE_OPEN_TIME = 5000;

Servo gateServo;

// ================= SLOT PINS =================
const int SLOT1_PIN = 12;
const int SLOT2_PIN = 16;
const int SLOT3_PIN = 17;
const int SLOT4_PIN = 14;
const int SLOT5_PIN = 15;
//const int SLOT6_PIN = 21;

const int STATUS_LED = 33;

WebServer server(80);

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(SLOT1_PIN, INPUT);
  pinMode(SLOT2_PIN, INPUT);
  pinMode(SLOT3_PIN, INPUT);
  pinMode(SLOT4_PIN, INPUT);
  pinMode(SLOT5_PIN, INPUT);
  pinMode(SLOT6_PIN, INPUT);

  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  connectWiFi();
  initCamera();
  initServo();

  server.on("/open_exit_gate", HTTP_POST, handleOpenExitGate);
  server.begin();

  Serial.println("✅ System Ready");
}

// ================= LOOP =================
void loop() {
  server.handleClient();

  static unsigned long lastSlotUpdate = 0;
  static unsigned long lastGateCapture = 0;

  unsigned long now = millis();

  if (now - lastSlotUpdate >= 10000) {
    lastSlotUpdate = now;
    sendSlotStatus();
  }

  // Increased interval to prevent memory stress
  if (now - lastGateCapture >= 15000) {
    lastGateCapture = now;
    captureAndVerify();
  }
}

// ================= WIFI =================
void connectWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi Failed");
  }
}

// ================= CAMERA =================
void initCamera() {
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

  if (psramFound()) {
    Serial.println("PSRAM Found");
    config.frame_size = FRAMESIZE_QVGA;   // stable
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    Serial.println("No PSRAM");
    config.frame_size = FRAMESIZE_QQVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  config.grab_mode = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera Init Failed");
    return;
  }

  Serial.println("Camera Ready");
}

// ================= SERVO =================
void initServo() {
  gateServo.setPeriodHertz(50);
  gateServo.attach(SERVO_PIN, 1000, 2000);
  gateServo.write(SERVO_CLOSED);
}

void openGate() {
  Serial.println("Opening Gate");
  gateServo.write(SERVO_OPEN);
  delay(GATE_OPEN_TIME);
  gateServo.write(SERVO_CLOSED);
}

// ================= CAPTURE =================
void captureAndVerify() {

  if (WiFi.status() != WL_CONNECTED) return;

  Serial.println("Capturing Image...");

  camera_fb_t* fb = esp_camera_fb_get();

  if (!fb || fb->len == 0) {
    Serial.println("Capture Failed");
    if (fb) esp_camera_fb_return(fb);
    return;
  }

  HTTPClient http;
  http.begin(gateVerifyUrl);
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-API-Key", API_KEY);

  int httpCode = http.POST(fb->buf, fb->len);

  if (httpCode > 0) {
    String response = http.getString();

    DynamicJsonDocument doc(512);
    if (deserializeJson(doc, response) == DeserializationError::Ok) {
      String status = doc["status"];

      if (status == "AUTHORIZED") {
        Serial.println("ACCESS GRANTED");
        openGate();
      } else {
        Serial.println("ACCESS DENIED");
      }
    }
  }

  http.end();
  esp_camera_fb_return(fb);
}

// ================= SLOT UPDATE =================
void sendSlotStatus() {
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  String payload = "{";
  payload += "\"slot1\":\"" + String(digitalRead(SLOT1_PIN)==LOW?"occupied":"available") + "\",";
  payload += "\"slot2\":\"" + String(digitalRead(SLOT2_PIN)==LOW?"occupied":"available") + "\",";
  payload += "\"slot3\":\"" + String(digitalRead(SLOT3_PIN)==LOW?"occupied":"available") + "\",";
  payload += "\"slot4\":\"" + String(digitalRead(SLOT4_PIN)==LOW?"occupied":"available") + "\",";
  payload += "\"slot5\":\"" + String(digitalRead(SLOT5_PIN)==LOW?"occupied":"available") + "\",";
  payload += "\"slot6\":\"" + String(digitalRead(SLOT6_PIN)==LOW?"occupied":"available") + "\"}";
  
  http.POST(payload);
  http.end();
}

// ================= EXIT GATE =================
void handleOpenExitGate() {

  if (!server.hasHeader("X-API-Key") || 
      server.header("X-API-Key") != API_KEY) {
    server.send(401, "text/plain", "Unauthorized");
    return;
  }

  openGate();
  server.send(200, "text/plain", "Gate Opened");
}