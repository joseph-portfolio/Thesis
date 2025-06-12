#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

const char* ssid = "YourHotspotSSID";
const char* password = "YourHotspotPassword";

const char* pi_ip = "192.168.43.100";  // ping raspberrypi.local, once connected to same network
const int pi_port = 5000;

WebServer server(80);

// ESP32 pins
const int in1 = 14; // motor A: clockwise IN1 
const int in2 = 27; // motor A: counterclockwise IN2
const int in3 = 26; // motor B: clockwise IN3
const int in4 = 25; // motor B: counterclockwise IN4
const int pm1 = 4; // pump 1: collection to main
const int pm2 = 16; // pump 2: distilled water
const int pm3 = 17; // pump 3: disposal  -- changed from GPIO 7 (unsafe) to GPIO 17
const int vlv = 13; // valve
const int uv = 33; // UV LED
const int wht = 32; // White LED

void setup() {
  Serial.begin(115200);

  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);
  pinMode(pm1, OUTPUT);
  pinMode(pm2, OUTPUT);
  pinMode(pm3, OUTPUT);
  pinMode(vlv, OUTPUT);
  pinMode(uv, OUTPUT);
  pinMode(wht, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000); Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP Address: "); Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/forward", []() { drive(1); triggerPi(); server.send(200, "text/plain", "Forward"); });
  server.on("/backward", []() { drive(2); triggerPi(); server.send(200, "text/plain", "Backward"); });
  server.on("/left", []() { drive(3); triggerPi(); server.send(200, "text/plain", "Left"); });
  server.on("/right", []() { drive(4); triggerPi(); server.send(200, "text/plain", "Right"); });
  server.on("/stop", []() { drive(0); server.send(200, "text/plain", "Stop"); });
  server.on("/cnc", []() { cnc(); server.send(200, "text/plain", "Collect and Capture"); });

  server.begin();
}

void loop() {
  server.handleClient();
}

void drive(int cmd) {
  switch (cmd) {
    case 0:
      digitalWrite(in1, LOW); digitalWrite(in2, LOW);
      digitalWrite(in3, LOW); digitalWrite(in4, LOW);
      break;
    case 1:
      digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
      digitalWrite(in3, HIGH); digitalWrite(in4, LOW);
      break;
    case 2:
      digitalWrite(in1, LOW); digitalWrite(in2, HIGH);
      digitalWrite(in3, LOW); digitalWrite(in4, HIGH);
      break;
    case 3:
      digitalWrite(in1, LOW); digitalWrite(in2, HIGH);
      digitalWrite(in3, HIGH); digitalWrite(in4, LOW);
      break;
    case 4:
      digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
      digitalWrite(in3, LOW); digitalWrite(in4, HIGH);
      break;
  }
}

void triggerPi() {
  // Sends an HTTP POST request to the Raspberry Pi to trigger image capture
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(pi_ip) + ":" + String(pi_port) + "/capture";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST("");  // Empty body
    Serial.print("Triggered Pi, response code: ");
    Serial.println(httpCode);
    http.end();
  } else {
    Serial.println("WiFi not connected. Cannot trigger Pi.");
  }
}

void cnc() {
  digitalWrite(pm1, HIGH); delay(3000); // Step 1: Activate Pump 1 for 3 seconds
	digitalWrite(pm1, LOW); // Step 2: Stop Pump 1
	digitalWrite(vlv, HIGH); delay(3000); // Step 3: Open Valve 1 for 3 seconds
	digitalWrite(vlv, LOW); // Step 4: Close Valve 1
	digitalWrite(uv, HIGH); // Step 5: UV LED On
	triggerPi(); // To call capture image from rpi
	delay(1000); // Placeholder delay for upload
	digitalWrite(uv, LOW); // Step 6: UV LED Off
	digitalWrite(wht, HIGH); // Step 7: White LED On
	triggerPi(); // To call capture image from rpi
	delay(1000); // Placeholder delay for upload
	digitalWrite(wht, LOW); // Step 8: White LED Off
	digitalWrite(vlv, HIGH); digitalWrite(pm2, HIGH);
	delay(3000); // Step 9: Open Valve 1 with Distilled Water from Pump 2 for 3 seconds
	digitalWrite(vlv, LOW); delay(3000); // Step 8: Close Valve 2 for 3 seconds
	digitalWrite(pm2, LOW); // Step 9: Stop Pump 2
	digitalWrite(pm3, HIGH); delay(3000); // Step 10: Open Pump for 3 seconds
	digitalWrite(pm3, LOW); // Step 11: Close Valve 3, finished
}

void handleRoot() {
  server.send(200, "text/html", R"rawliteral(
    <!DOCTYPE html>
    <html>
    <head>
      <title>ESP32 WSV Control</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        button {
          width: 150px; height: 50px; font-size: 16px; margin: 5px;
        }
      </style>
    </head>
    <body style="text-align:center;">
      <h2>RC Boat Control</h2>
      <button onclick="sendCmd('forward')">Forward</button><br>
      <button onclick="sendCmd('left')">Left</button>
      <button onclick="sendCmd('stop')">Stop</button>
      <button onclick="sendCmd('right')">Right</button><br>
      <button onclick="sendCmd('backward')">Backward</button><br>
      <button id="cncBtn" onclick="runCNC()">Collect and Capture</button><br>

      <script>
        function sendCmd(cmd) {
          fetch("/" + cmd)
            .then(response => response.text())
            .then(text => alert("Response: " + text))
            .catch(err => alert("Error: " + err));
        }

        function runCNC() {
          let btn = document.getElementById('cncBtn');
          btn.disabled = true;
          btn.innerText = "Running...";
          fetch("/cnc")
            .then(response => response.text())
            .then(text => {
              alert(text);
              btn.disabled = false;
              btn.innerText = "Collect and Capture";
            })
            .catch(err => {
              alert("Error: " + err);
              btn.disabled = false;
              btn.innerText = "Collect and Capture";
            });
        }
      </script>
    </body>
    </html>
  )rawliteral");
}
