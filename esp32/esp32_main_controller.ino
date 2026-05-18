#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

// ================= WIFI =================
const char* WIFI_SSID = "Gopi"; // Give Your Wifi Name
const char* WIFI_PASSWORD = "12345678"; // Give your Wifi Password

// ================= SERVER =================
const char* SERVER_IP = " 10.66.110.251"; // Give your server here (type for server in command prompt "ipconfig", there you will find "IPv4" address that is your server )
const char* SERVER_PORT = "5000";
const char* API_KEY = "ESP32_SECRET_KEY";

// ================= SERVO =================
#define SERVO_PIN 22
#define SERVO_OPEN 90
#define SERVO_CLOSED 0
#define GATE_OPEN_TIME 5000

Servo gateServo;

// ================= SLOT PINS =================
#define SLOT1_PIN 4
#define SLOT2_PIN 16
#define SLOT3_PIN 17
#define SLOT4_PIN 18
#define SLOT5_PIN 19
#define SLOT6_PIN 21

// ================= TIMERS =================
unsigned long lastSlotUpdate = 0;
unsigned long lastGateCheck = 0;

const unsigned long SLOT_INTERVAL = 10000;
const unsigned long GATE_CHECK_INTERVAL = 2000;

// ================= SERVO CONTROL FLAGS =================
volatile bool gateCommand = false;
volatile bool gateBusy = false;

// ================= WIFI =================
void connectWiFi()
{
  Serial.println("Connecting WiFi");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// ================= SERVO INIT =================
void initServo()
{
  gateServo.setPeriodHertz(50);
  gateServo.attach(SERVO_PIN, 500, 2400);

  gateServo.write(SERVO_CLOSED);

  Serial.println("Servo Initialized");
}

// ================= SERVO TASK =================
void servoTask(void *pvParameters)
{
  while(true)
  {
    if(gateCommand && !gateBusy)
    {
      gateBusy = true;

      Serial.println("Opening Gate");

      gateServo.write(SERVO_OPEN);

      vTaskDelay(GATE_OPEN_TIME / portTICK_PERIOD_MS);

      Serial.println("Closing Gate");

      gateServo.write(SERVO_CLOSED);

      gateBusy = false;
      gateCommand = false;

      Serial.println("Gate Cycle Complete");
    }

    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
}

// ================= CHECK SERVER FOR GATE COMMAND =================
void checkGateCommand()
{
  if (WiFi.status() != WL_CONNECTED || gateBusy) return;

  HTTPClient http;

  String url = "http://" + String(SERVER_IP) + ":" + SERVER_PORT + "/api/gate_control";

  http.begin(url);
  http.addHeader("X-API-Key", API_KEY);

  int httpCode = http.GET();

  if (httpCode == 200)
  {
    String payload = http.getString();

    StaticJsonDocument<128> doc;
    deserializeJson(doc, payload);

    const char* command = doc["command"];

    if (command && strcmp(command, "OPEN") == 0)
    {
      Serial.println("Gate OPEN command received");

      gateCommand = true;
    }
  }

  http.end();
}

// ================= SEND SLOT STATUS =================
void sendSlotStatus()
{
  if (WiFi.status() != WL_CONNECTED) return;

  StaticJsonDocument<256> doc;

  doc["slot1"] = digitalRead(SLOT1_PIN) == LOW ? "occupied" : "available";
  doc["slot2"] = digitalRead(SLOT2_PIN) == LOW ? "occupied" : "available";
  doc["slot3"] = digitalRead(SLOT3_PIN) == LOW ? "occupied" : "available";
  doc["slot4"] = digitalRead(SLOT4_PIN) == LOW ? "occupied" : "available";
  doc["slot5"] = digitalRead(SLOT5_PIN) == LOW ? "occupied" : "available";
  doc["slot6"] = digitalRead(SLOT6_PIN) == LOW ? "occupied" : "available";

  String payload;
  serializeJson(doc, payload);

  HTTPClient http;

  String url = "http://" + String(SERVER_IP) + ":" + SERVER_PORT + "/update_slots";

  http.begin(url);

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  int httpCode = http.POST(payload);

  Serial.print("Slot update response: ");
  Serial.println(httpCode);

  http.end();
}

// ================= SETUP =================
void setup()
{
  Serial.begin(115200);

  pinMode(SLOT1_PIN, INPUT_PULLUP);
  pinMode(SLOT2_PIN, INPUT_PULLUP);
  pinMode(SLOT3_PIN, INPUT_PULLUP);
  pinMode(SLOT4_PIN, INPUT_PULLUP);
  pinMode(SLOT5_PIN, INPUT_PULLUP);
  pinMode(SLOT6_PIN, INPUT_PULLUP);

  connectWiFi();

  initServo();

  // Create Servo Task
  xTaskCreatePinnedToCore(
    servoTask,
    "ServoTask",
    2048,
    NULL,
    1,
    NULL,
    1
  );

  Serial.println("System Ready");
}

// ================= LOOP =================
void loop()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    connectWiFi();
  }

  // Check server for gate command
  if (millis() - lastGateCheck > GATE_CHECK_INTERVAL)
  {
    lastGateCheck = millis();
    checkGateCommand();
  }

  // Send slot updates
  if (millis() - lastSlotUpdate > SLOT_INTERVAL)
  {
    lastSlotUpdate = millis();
    sendSlotStatus();
  }
}