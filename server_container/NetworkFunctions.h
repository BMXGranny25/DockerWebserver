#include "MotorFunctions.h"

void handleMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;

  if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
    data[len] = 0;
    String message = (char*)data;

    Serial.println("Received: " + message);

    // Example motor control
    if (message == "forward") {
      ledON();
    }
    else if (message == "reverse"){
      ledOFF();
    }
    else if (message == "stop") {
      inactive();
    }
    // Send response back to browser
    Serial.println("Command received: " + message);
  }
}

void onEvent(AsyncWebSocket *server, AsyncWebSocketClient *client, AwsEventType type, void *arg, uint8_t *data, size_t len) {//Taken off the github
  
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("Client connected\n");
      client->printf("Hello pilot");
      break;
    case WS_EVT_DISCONNECT:
      Serial.printf("Client disconnected\n");
      break;
    case WS_EVT_DATA:
      handleMessage(arg, data, len);
      break;
    case WS_EVT_ERROR:
      Serial.printf("WebSocket error");
      break;
    default:
      break;
  }
  
}
