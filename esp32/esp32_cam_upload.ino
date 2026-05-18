#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ================= WIFI =================
const char* ssid = "Gopi"; // Give your Wifi Name
const char* password = "12345678"; // Give your Wifi Paasword

// ================= SERVER =================
const char* serverUrl = "http://192.168.41.251:5000/api/upload_plate"; // Give your server here (type for server in command prompt "ipconfig", there you will find "IPv4" address that is your server )
const char* apiKey = "ESP32_SECRET_KEY";

// ================= CAMERA PINS (AI THINKER) =================
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


// ================= WIFI CONNECT =================
void connectWiFi() {

  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}


// ================= CAMERA INIT =================
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

  if(psramFound()) {

    Serial.println("PSRAM Found");

    // Better resolution for number plate OCR
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 2;

  } else {

    Serial.println("No PSRAM");

    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();

  // ===== FIX IMAGE ORIENTATION =====
  s->set_vflip(s, 1);     // flip vertically
  s->set_hmirror(s, 0);   // mirror horizontally

  // ===== CAMERA SETTINGS =====
  s->set_brightness(s, 0);
  s->set_contrast(s, 0);
  s->set_saturation(s, 0);
  s->set_gain_ctrl(s, 1);
  s->set_exposure_ctrl(s, 1);

  // discard first bad frame
  camera_fb_t * fb = esp_camera_fb_get();
  if (fb) esp_camera_fb_return(fb);

  Serial.println("Camera Ready");
}


// ================= SETUP =================
void setup() {

  Serial.begin(115200);
  delay(1000);

  connectWiFi();
  initCamera();
}


// ================= LOOP =================
void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }

  Serial.println("Capturing image...");

  camera_fb_t * fb = esp_camera_fb_get();

  if (!fb || fb->len < 100) {
    Serial.println("Camera capture failed");
    if (fb) esp_camera_fb_return(fb);
    delay(2000);
    return;
  }

  Serial.printf("Image captured: %d bytes\n", fb->len);

  HTTPClient http;

  http.begin(serverUrl);
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-API-Key", apiKey);

  int httpResponseCode = http.POST(fb->buf, fb->len);

  Serial.print("HTTP Response code: ");
  Serial.println(httpResponseCode);

  if (httpResponseCode > 0) {

    String response = http.getString();

    Serial.println("Server Response:");
    Serial.println(response);

  } else {

    Serial.println("POST failed");
  }

  http.end();

  esp_camera_fb_return(fb);

  Serial.println("Waiting 10 seconds...\n");

  delay(10000);
}