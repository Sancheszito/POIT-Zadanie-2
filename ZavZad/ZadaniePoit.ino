const int irSensorPin = 2;
const int trigPin = 8;
const int echoPin = 9;

bool measuring = false;
bool prevIrState = HIGH;

void setup() {
  Serial.begin(9600);
  pinMode(irSensorPin, INPUT);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void loop() {
  int irState = digitalRead(irSensorPin);

  // Detekcia prechodu z HIGH -> LOW (mávnutie)
  if (prevIrState == HIGH && irState == LOW) {
    measuring = !measuring; // prepneme stav
    if (measuring) {
      Serial.println("START");
    } else {
      Serial.println("STOP");
    }
    delay(500); // debounce (zabráni viacerým prepnutiam pri jednom mávnutí)
  }

  prevIrState = irState;

  if (measuring) {
    long duration;
    float distance;

    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    duration = pulseIn(echoPin, HIGH);
    distance = duration * 0.034 / 2;

    Serial.println(distance);
    delay(500); // meranie každých 0.5 sekundy
  }

  delay(50); // bežné čítanie IR senzora
}
