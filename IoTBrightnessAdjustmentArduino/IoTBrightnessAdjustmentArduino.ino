// https://playground.arduino.cc/code/timer
#include <Timer.h>

#define LDR_Pin 0
#define Sound_Analog_Pin A1
#define Rotary_CLK_Pin 6
#define Rotary_DT_Pin 7
#define Dummy_Digital_Pin 13
#define Rotary_Button_Pin 2

#define counterResetTimeout 700
bool blockTimeout = false;
bool mode_auto = true;

// read LDR value every 10 seconds
#define LDR_readInterval 1000
int LDR_level;

// How long the clap sound detection should be suspended (2 seconds)
#define Sound_blockDelay 2000
#define Sound_analogThreshold 75
short Sound_counter = 0;

#define Rotary_buttonDebounceTime 500
volatile boolean Rotary_stateChanged = false;
unsigned long Rotary_newButtonPressedTime;
unsigned long Rotary_lastButtonPressedTime;
int Rotary_lastValue;
int Rotary_value;

#define clapTriggerDelay 2
bool blockClap = false;
unsigned long lastClapTime = 0;

Timer ldr_t;
Timer light_t;
Timer clap_t;

int timer_id;

void readLDR() {
  LDR_level = analogRead(LDR_Pin);
  Serial.print("ldr_level " + String(LDR_level));
  Serial.println();
}

void setup() {
  pinMode(Rotary_Button_Pin, INPUT_PULLUP);
  pinMode(Dummy_Digital_Pin, OUTPUT);
  pinMode(Rotary_CLK_Pin, INPUT);
  pinMode(Rotary_DT_Pin, INPUT);
  attachInterrupt(digitalPinToInterrupt(Rotary_Button_Pin), Rotary_interruptHandler, RISING);
  Serial.begin(9600);
  Rotary_lastValue = digitalRead(Rotary_CLK_Pin);
  timer_id = ldr_t.every(LDR_readInterval, readLDR, NULL);
}

void Rotary_interruptHandler() {
  Rotary_stateChanged = true;
}

void resetCounterAfterTimeout() {
  if (blockTimeout) {
    blockTimeout = false;
    return;
  }
  Sound_counter = 0;
}

void unblockClap() {
  blockClap = false;
}

void loop() {
  if (Rotary_stateChanged){
    Rotary_stateChanged = false;
    Rotary_newButtonPressedTime = millis();
    if ((Rotary_newButtonPressedTime - Rotary_lastButtonPressedTime) >= Rotary_buttonDebounceTime) {
      if (mode_auto){
        mode_auto = false;
        Serial.println("mode_manual");
        ldr_t.stop(timer_id);
      }
      else {
        mode_auto = true;
        Serial.println("mode_auto");
        timer_id = ldr_t.every(LDR_readInterval, readLDR, NULL);
      }
      Rotary_lastButtonPressedTime = Rotary_newButtonPressedTime;
    }
  }
  if (mode_auto) {
    ldr_t.update();
  }
  else {
    light_t.update();
    clap_t.update();
    int Sound_analogValue = analogRead(Sound_Analog_Pin);
    if (!blockClap && (millis() - lastClapTime) > clapTriggerDelay) {
      if (Sound_analogValue >= Sound_analogThreshold) {
        digitalWrite(Dummy_Digital_Pin, HIGH);
        if (Sound_counter == 0 || Sound_counter == 2) {
          blockTimeout = true;
          Sound_counter++;
          light_t.after(counterResetTimeout, resetCounterAfterTimeout, NULL);
          lastClapTime = millis();
        }
      } else {
        digitalWrite(Dummy_Digital_Pin, LOW);
        if (Sound_counter == 1 || Sound_counter == 3) {
          blockTimeout = true;
          Sound_counter++;
          light_t.after(counterResetTimeout, resetCounterAfterTimeout, NULL);
          lastClapTime = millis();
        }
        if (Sound_counter == 4) {
          Sound_counter = 0;
          blockTimeout = false;
          Serial.println("light_toggle");
          blockClap = true;
          clap_t.after(Sound_blockDelay, unblockClap, NULL);
        }
      }
    }
  }
  
  Rotary_value = digitalRead(Rotary_CLK_Pin);
  if (Rotary_value != Rotary_lastValue) {
    if (digitalRead(Rotary_DT_Pin) != Rotary_value) {
      Serial.println("rotary CCW");
    } else {
      Serial.println("rotary CW");
    }
  }
  Rotary_lastValue = Rotary_value;
}
