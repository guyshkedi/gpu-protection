const int fan_control_pin = 13;
unsigned long start_time;
int max_wait_time = 3;
// the setup function runs once when you press reset or power the board
void setup() {
  pinMode(fan_control_pin,OUTPUT);
  analogWrite(fan_control_pin,0);
  Serial.begin(9600);
}

// the loop function runs over and over again forever
void loop() {
  start_time = millis();
  while (millis() - start_time < max_wait_time * 1000) {
    if(Serial.available() > 0) {
      start_time = millis();
      char data = Serial.read();
      Serial.println(data);
      if (data == '0') {
        Serial.println("Turning Fan OFF");
        analogWrite(fan_control_pin,0);
      } else {
        Serial.println("Turning Fan ON");
        analogWrite(fan_control_pin,255);
      }
    }
  }
  Serial.println("No response. turning ON.");
  digitalWrite(fan_control_pin,255);
}
