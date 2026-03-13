#include <WiFi.h>
#include <LittleFS.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ESP32Servo.h>

//Set IP data
IPAddress local_IP(192, 168, 4, 1);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

//Open in port 80, I believe this is the default port for a web server
//Therefore all we need to do to connect to the server is http://ip/whatever
AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

#include "NetworkFunctions.h"

Servo myservo;
#define trigPin 32
#define echoPin 33
#define servoPin 27
#define SOUND_VELOCITY 0.034
long duration;
float distanceCm;
int pos = 0; 

void setup() {
  Serial.begin(115200);

  //Wifi setup
  WiFi.softAPConfig(local_IP, gateway, subnet);
  WiFi.softAP("The A Team");
  Serial.print("\nSoft-AP IP address = ");
  Serial.println(WiFi.softAPIP());

  //Load files
  if (!LittleFS.begin()) {
    Serial.println("Failed to mount LittleFS");
    return;
  }
  Serial.println("LittleFS mounted successfully");

  ws.onEvent(onEvent);
  server.addHandler(&ws);
  
  //Sends the html file on root directory request, the html file is set up so it will request the css and js files
  server.on("/", HTTP_ANY, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/index.html", "text/html");
  }); 
  server.on("/style.css", HTTP_ANY, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/style.css", "text/css");
  });
  server.on("/script.js", HTTP_ANY, [](AsyncWebServerRequest *request){
    request->send(LittleFS, "/script.js", "application/javascript");
  });

  server.begin();
  Serial.println("WebSocket server started");
     
  //
  //Setup pins here
  myservo.attach(servoPin, 700, 2200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  //
}
unsigned long lastSend = 0;

void moveAndCheck(int angle){
  myservo.write(angle);
  delay(30); 
  
  // Clears the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH, 30000);
  
  // Calculate the distance
  distanceCm = duration * SOUND_VELOCITY/2;
  distanceCm = trunc(distanceCm*10)/10;

  delay(25);

  //ws.textAll(String(distanceCm) + "," + String(angle));
}

void loop() {
  ws.cleanupClients(); //Not really needed but the Github recommends it

  for (pos = 0; pos <= 180; pos += 1) { 
    moveAndCheck(pos);
  }

  for (pos = 180; pos >= 0; pos -= 1) { 
    moveAndCheck(pos);
  }
}
