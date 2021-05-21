const int fanControlPin = 11;
unsigned long start_time;
int max_wait_time = 3;
char data_recieved = '9';
int power = 255;
// the setup function runs once when you press reset or power the board
void setup() {
  pinMode(fanControlPin,OUTPUT);
  Serial.begin(9600);
  analogWrite(fanControlPin,255);
}

// the loop function runs over and over again forever
void loop() {
  start_time = millis();
  while (millis() - start_time < max_wait_time * 1000) {
    if(Serial.available() > 0) {
      start_time = millis();
      data_recieved = Serial.read();
      //Serial.print(data);
      //Serial.print("Got Data: ");
      //Serial.println(data_recieved);
      power = data_recieved - '0';
      //Serial.print("conversion to int: ");
      //Serial.println(power);
      power = (power + 1) * 10;
      //Serial.print("Calculated Power in %: ");
      //Serial.println(power);
      power = int(float(power) * (255.0/100));
      Serial.print("Calculated Power in 0-255: ");
      Serial.println(power);
      analogWrite(fanControlPin,power);
    }
  }
  //Serial.println("No response. turning ON.");
  digitalWrite(fanControlPin,255);
}
