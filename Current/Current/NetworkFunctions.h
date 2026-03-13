#include "MotorFunctions.h"

#define MAX_JPG_SIZE 32000
uint8_t jpegData[MAX_JPG_SIZE];

void handleMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;

  if (info->opcode == WS_TEXT && info->final && info->index == 0) {
    data[len] = 0;
    String message = (char*)data;
    Serial.println("Text: " + message);

    if (message == "forward")  ledON();
    else if (message == "reverse") ledOFF();
    else if (message == "stop") inactive();
    else if (message == "takePhoto") ws.textAll("Photo Taken");
  }

  else if (info->opcode == WS_BINARY || info->opcode == WS_CONTINUATION) {
    if (info->index + len <= MAX_JPG_SIZE) {
      memcpy(jpegData + info->index, data, len);
    }

    if (info->final && (info->index + len == info->len)) {
      Serial.printf("Full JPEG ready (%u bytes). Sending to web client...\n", info->len);

      ws.binaryAll(jpegData, info->len);
    }
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
      Serial.printf("Error");
      break;
    default:
      break;
  }
}
