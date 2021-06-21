const int fanControlPin = 11;
unsigned long start_time, current_time;
unsigned long println_start_time;
int max_wait_time = 3;
String data_recieved = "000";
int power = 255;
int multiplier = 100;
int temp_power;
// the setup function runs once when you press reset or power the board
void setup() {
  pinMode(fanControlPin,OUTPUT);
  Serial.begin(9600);
  Serial.setTimeout(1000);
  analogWrite(fanControlPin,255);
}

// the loop function runs over and over again forever
void loop() {
  start_time = millis();
  println_start_time = start_time;
  current_time = start_time;
  while (current_time - start_time < max_wait_time * 1000) {
    if (current_time - println_start_time > 1 * 1000) {
      println_start_time = current_time;
      Serial.println(power);
    }
    if(Serial.available() > 0) {
      start_time = millis();
      multiplier = 100;
      power = 0;
      
      data_recieved = Serial.readStringUntil('-');
      //Serial.print(data);
      //Serial.print("Got Data: ");
      //Serial.println(data_recieved);
      //temp_power = data_recieved - '0';
      //temp_power = power * multiplier;
      //power = power + temp_power;
      //multiplier = multiplier / 10;
      power = data_recieved.toInt();
      //Serial.print("Calculated Power: ");
      //Serial.println(power);
      
      Serial.println(power);
      analogWrite(fanControlPin,power);
    }
    current_time = millis();
  }
  power = 255;
  //Serial.println("No response. turning ON.");
  digitalWrite(fanControlPin,power);
}
