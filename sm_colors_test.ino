const int byte_map[10] = {
  11, 10, 9, 8, // Lane 1, 2, 3, 4
  7, 3, 5, 6, 4, // 4, 8, 16, 12, 24
  2 // Gray
};

void setup() {
  for (int pin = 2; pin <= 11; pin++) {
    pinMode(pin, OUTPUT);
  }
  Serial.begin(9600);
}

byte byte_buffer[10];
void loop() {
  while (Serial.available() >= 10) {
    Serial.readBytes(byte_buffer, 10);
    for (int i = 0; i < 10; i++) {
      if (byte_buffer[i] == 0) digitalWrite(byte_map[i], LOW);
      if (byte_buffer[i] == 1) digitalWrite(byte_map[i], HIGH);
    }
  }
}

