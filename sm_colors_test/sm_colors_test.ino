void setup() {
  for (int pin = 2; pin < 12; pin++) {
    pinMode(pin, OUTPUT);
  }
  Serial.begin(9600);
}

byte byte_buffer[12];
void loop() {
  while (Serial.available() >= 12) {
    Serial.readBytes(byte_buffer, 12);
    for (int i = 0; i < 12; i++) {
      if (byte_buffer[i] == 0) digitalWrite(i, LOW);
      if (byte_buffer[i] == 1) digitalWrite(i, HIGH);
    }
  }
}

