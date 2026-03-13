#include "esp_camera.h"
#include <WiFi.h>
#include <WebSocketsClient_Generic.h>

//Server Data
const char* websocket_server = "192.168.4.1";
const uint16_t websocket_port = 80;
const char* websocket_path   = "/ws";
//Constants
WebSocketsClient ws;
unsigned long lastCapture = 0;
const unsigned long INTERVAL_MS = 3000;
bool connected = false;
//Camera info
#define CAMERA_MODEL_AI_THINKER
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
//

void takePhoto(){
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  Serial.printf("Sending JPEG → %u bytes\n", fb->len);
  ws.sendBIN(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void webSocketEvent(WStype_t type, uint8_t * data, size_t len) {
  String message = (char*)data;
  
  switch(type){
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected!");
      connected = false;
      break;
    case WStype_CONNECTED:
      Serial.printf("[WS] Connected to URL: %s\n", data);
      connected = true;
      break;
    case WStype_TEXT:
      Serial.printf("[WS] Text received: %s\n", data);
      if (message == "takePhoto") takePhoto();
      break;
    case WStype_BIN:
      Serial.printf("[WS] Binary received (%u bytes)\n", len);
      break;
    default:
      break;
  }
}

void setup() {
  Serial.begin(115200);

  camera_config_t config;
  config.ledc_channel    = LEDC_CHANNEL_0;
  config.ledc_timer      = LEDC_TIMER_0;
  config.pin_d0          = Y2_GPIO_NUM;
  config.pin_d1          = Y3_GPIO_NUM;
  config.pin_d2          = Y4_GPIO_NUM;
  config.pin_d3          = Y5_GPIO_NUM;
  config.pin_d4          = Y6_GPIO_NUM;
  config.pin_d5          = Y7_GPIO_NUM;
  config.pin_d6          = Y8_GPIO_NUM;
  config.pin_d7          = Y9_GPIO_NUM;
  config.pin_xclk        = XCLK_GPIO_NUM;
  config.pin_pclk        = PCLK_GPIO_NUM;
  config.pin_vsync       = VSYNC_GPIO_NUM;
  config.pin_href        = HREF_GPIO_NUM;
  config.pin_sscb_sda    = SIOD_GPIO_NUM;
  config.pin_sscb_scl    = SIOC_GPIO_NUM;
  config.pin_pwdn        = PWDN_GPIO_NUM;
  config.pin_reset       = RESET_GPIO_NUM;
  config.xclk_freq_hz    = 20000000;
  config.pixel_format    = PIXFORMAT_JPEG;

  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 25;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed!");
    while(1) delay(1000);
  }

  sensor_t * s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_SVGA);

  Serial.println("Camera ready");

  // WiFi
  WiFi.begin("The A Team");
  Serial.print("Connecting WiFi ");
  while (WiFi.status() != WL_CONNECTED) {
    delay(450);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected: " + WiFi.localIP().toString());

  // WebSocket
  ws.begin(websocket_server, websocket_port, websocket_path);
  ws.onEvent(webSocketEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
}