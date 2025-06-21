#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// ─── Wi-Fi credentials ───
const char* ssid     = "hello";
const char* password = "hatdog123";

// ─── Raspberry Pi server details ───
const char* pi_ip = "192.168.170.183";
const int   pi_port = 5000;

// ─── Motor and actuator pins ───
const int in1 = 14, in2 = 27, in3 = 26, in4 = 25;
const int pm1 = 4,  pm2 = 16, pm3 = 17;
const int vlv = 13, uv = 33,  wht = 32;

WebServer server(80);

// ─── Function declarations ───
void handleRoot();
void drive(int cmd);
void triggerPi();
void cnc();
void led(int l);
void pnv(int p);

// ─── Setup ───
void setup() {
  Serial.begin(115200);
  pinMode(in1, OUTPUT); pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT); pinMode(in4, OUTPUT);
  pinMode(pm1, OUTPUT); pinMode(pm2, OUTPUT); pinMode(pm3, OUTPUT);
  pinMode(vlv, OUTPUT); pinMode(uv, OUTPUT); pinMode(wht, OUTPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: " + WiFi.localIP().toString());

  server.on("/", handleRoot);
  server.on("/backward",  []() { drive(1); server.send(200, "text/plain", "Backward"); });
  server.on("/forward",   []() { drive(2); server.send(200, "text/plain", "Forward"); });
  server.on("/left",      []() { drive(3); server.send(200, "text/plain", "Left"); });
  server.on("/right",     []() { drive(4); server.send(200, "text/plain", "Right"); });
  server.on("/stop",      []() { drive(0); server.send(200, "text/plain", "Stop"); });
  server.on("/cnc",       []() { cnc(); server.send(200, "text/plain", "Collect and Capture done"); });
  server.on("/uvled",     []() { led(0); server.send(200, "text/plain", "UV LED"); });
  server.on("/whtled",    []() { led(1); server.send(200, "text/plain", "White LED"); });
  server.on("/noled",     []() { led(2); server.send(200, "text/plain", "Turn Off LED"); });
  server.on("/pm1",       []() { pnv(0); server.send(200, "text/plain", "Pump 1 Activate"); });
  server.on("/pm2",       []() { pnv(1); server.send(200, "text/plain", "Pump 2 Activate"); });
  server.on("/pm3",       []() { pnv(2); server.send(200, "text/plain", "Pump 3 Activate"); });
  server.on("/vlv",       []() { pnv(3); server.send(200, "text/plain", "Valve Activate"); });
  server.on("/capture",   []() { triggerPi(); server.send(200, "text/plain", "Capture Image"); });

  server.begin();
}

void loop() {
  server.handleClient();
}

// ─── Motor drive logic ───
void drive(int cmd) {
  switch (cmd) {
    case 0: digitalWrite(in1, LOW); digitalWrite(in2, LOW); digitalWrite(in3, LOW); digitalWrite(in4, LOW); break;
    case 1: digitalWrite(in1, HIGH); digitalWrite(in2, LOW); digitalWrite(in3, HIGH); digitalWrite(in4, LOW); break;
    case 2: digitalWrite(in1, LOW); digitalWrite(in2, HIGH); digitalWrite(in3, LOW); digitalWrite(in4, HIGH); break;
    case 3: digitalWrite(in1, LOW); digitalWrite(in2, HIGH); digitalWrite(in3, HIGH); digitalWrite(in4, LOW); break;
    case 4: digitalWrite(in1, HIGH); digitalWrite(in2, LOW); digitalWrite(in3, LOW); digitalWrite(in4, HIGH); break;
  }
}

// ─── Notify Raspberry Pi ───
void triggerPi() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(pi_ip) + ":" + String(pi_port) + "/capture";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.POST("");
    http.end();
  }
}

// ─── Collection and capture sequence ───
void cnc() {
  digitalWrite(pm1, HIGH); delay(1500);
  digitalWrite(pm1, LOW);
  digitalWrite(vlv, HIGH); delay(1500);
  digitalWrite(vlv, LOW);
  digitalWrite(uv, HIGH); triggerPi(); delay(15000);
  digitalWrite(uv, LOW);
  digitalWrite(wht, HIGH); triggerPi(); delay(15000);
  digitalWrite(wht, LOW);
  digitalWrite(vlv, HIGH); digitalWrite(pm2, HIGH); delay(1500);
  digitalWrite(vlv, LOW); delay(1500);
  digitalWrite(pm2, LOW);
  digitalWrite(pm3, HIGH); delay(1500);
  digitalWrite(pm3, LOW);
}

void led(int l) {
  switch (l) {
    case 0: digitalWrite(uv, HIGH); break;
    case 1: digitalWrite(wht, HIGH); break;
    case 2: digitalWrite(uv, LOW); digitalWrite(wht, LOW); break;
  }
}

void pnv(int p) {
  switch (p) {
    case 0: digitalWrite(pm1, HIGH); delay(1500); digitalWrite(pm1, LOW); break;
    case 1: digitalWrite(pm2, HIGH); delay(1500); digitalWrite(pm2, LOW); break;
    case 2: digitalWrite(pm3, HIGH); delay(1500); digitalWrite(pm3, LOW); break;
    case 3: digitalWrite(vlv, HIGH); delay(1500); digitalWrite(vlv, LOW); break;
  }
}

// ─── Root HTML ───
void handleRoot() {
  server.send(200, "text/html", R"rawliteral(
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ESP32 Control</title>
    <style>
      button { width: 150px; height: 50px; font-size: 16px; margin: 5px; }
    </style></head><body style="text-align:center">
      <h2>WSV Control Panel</h2>
      <button onclick="sendCmd('forward')">Forward</button><br>
      <button onclick="sendCmd('left')">Left</button>
      <button onclick="sendCmd('stop')">Stop</button>
      <button onclick="sendCmd('right')">Right</button><br>
      <button onclick="sendCmd('backward')">Backward</button><br>
      <button onclick="sendCmd('uvled')">UV LED</button>
      <button onclick="sendCmd('noled')">Turn Off LED</button>
      <button onclick="sendCmd('whtled')">White LED</button><br>
      <button onclick="sendCmd('pm1')">Pump 1</button>
      <button onclick="sendCmd('pm2')">Pump 2</button>
      <button onclick="sendCmd('pm3')">Pump 3</button>
      <button onclick="sendCmd('vlv')">Valve</button><br>
      <button id="cncBtn" onclick="runCNC()">Collect and Capture</button><br>
      <button onclick="sendCmd('capture')">Capture Image</button><br>

      <script>
        function sendCmd(c) {
          fetch('/' + c).then(r => r.text()).then(alert).catch(alert);
        }
        function runCNC() {
          const b = document.getElementById('cncBtn');
          b.disabled = true; b.innerText = 'Running...';
          fetch('/cnc').then(r => r.text()).then(t => {
            alert(t);
            b.disabled = false; b.innerText = 'Collect and Capture';
          }).catch(e => {
            alert(e);
            b.disabled = false; b.innerText = 'Collect and Capture';
          });
        }
      </script>
    </body></html>
  )rawliteral");
}
