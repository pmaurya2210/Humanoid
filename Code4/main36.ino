#include <WiFi.h>
#include <esp_now.h>
#include <Wire.h>
#include <ESP32Servo.h>

/* ================= FACE ESP ================= */
#define FACE_SLAVE_ADDR 8

/* ================= MOTOR PINS ================= */
#define LEFT_PWM   12
#define LEFT_DIR   13
#define RIGHT_PWM  14
#define RIGHT_DIR  27

// SPEED SETTINGS
int moveSpeed = 120;   // forward/backward
int turnSpeed = 210;   // left/right

/* ================= SERVO SETUP ================= */
Servo servo[7];

int servoPins[7] =
{
  26,  // 0 Left Elbow 1
  33,  // 1 Left Elbow 2
  23,  // 2 Left Wrist
  25,  // 3 Right Elbow 1
  32,  // 4 Right Elbow 2
  17,  // 5 Right Wrist
  4    // 6 Neck
};

/* ================= INITIAL ANGLES ================= */
int initLeftElbow1   = 0;
int initLeftElbow2   = 100;
int initLeftWrist    = 150;
int initRightElbow1  = 0;
int initRightElbow2  = 85;
int initRightWrist   = 100;
int initNeck         = 90;

/* ================= CURRENT POSITIONS ================= */
int leftElbow1Pos  = initLeftElbow1;
int leftElbow2Pos  = initLeftElbow2;
int leftWristPos   = initLeftWrist;

int rightElbow1Pos = initRightElbow1;
int rightElbow2Pos = initRightElbow2;
int rightWristPos  = initRightWrist;

int neckPos        = initNeck;

/* ================= DATA STRUCT ================= */
typedef struct
{
  int cmd;
} Packet;

Packet incoming;

/* ================= COMMAND MEMORY ================= */
int currentCommand = 0;

/* ================= SMOOTH SETTINGS ================= */
int servoStepDelay = 5;
int servoStepSize  = 2;

/* ================= MOTOR SMOOTH SETTINGS ================= */
int motorCurrentPWM = 0;
int motorRampStep = 8;     // bigger = faster acceleration/deceleration
int motorRampDelay = 10;   // ms between motor updates

enum MotorMode
{
  MOTOR_STOP,
  MOTOR_FORWARD,
  MOTOR_BACKWARD,
  MOTOR_LEFT,
  MOTOR_RIGHT
};

MotorMode targetMotorMode = MOTOR_STOP;
MotorMode appliedMotorMode = MOTOR_STOP;

bool currentLeftDir = LOW;
bool currentRightDir = LOW;

unsigned long lastMotorUpdate = 0;

/* ================= HELPER ================= */
void sendToFace(uint8_t cmd)
{
  Wire.beginTransmission(FACE_SLAVE_ADDR);
  Wire.write(cmd);
  Wire.endTransmission();
}

void writeAllServos()
{
  servo[0].write(leftElbow1Pos);
  servo[1].write(leftElbow2Pos);
  servo[2].write(leftWristPos);
  servo[3].write(rightElbow1Pos);
  servo[4].write(rightElbow2Pos);
  servo[5].write(rightWristPos);
  servo[6].write(neckPos);
}

void smoothMoveOne(int servoIndex, int &currentPos, int targetPos)
{
  if (targetPos > 180) targetPos = 180;
  if (targetPos < 0)   targetPos = 0;

  while (currentPos != targetPos)
  {
    if (currentPos < targetPos) currentPos += servoStepSize;
    else currentPos -= servoStepSize;

    if (currentPos > targetPos && currentPos - servoStepSize < targetPos) currentPos = targetPos;
    if (currentPos < targetPos && currentPos + servoStepSize > targetPos) currentPos = targetPos;

    servo[servoIndex].write(currentPos);
    delay(servoStepDelay);
  }
}

void smoothMoveAll(
  int t0, int t1, int t2,
  int t3, int t4, int t5,
  int t6 = -1
)
{
  bool moving = true;

  while (moving)
  {
    moving = false;

    if (leftElbow1Pos != t0)
    {
      moving = true;
      if (leftElbow1Pos < t0) leftElbow1Pos += servoStepSize;
      else leftElbow1Pos -= servoStepSize;
      if (abs(leftElbow1Pos - t0) < servoStepSize) leftElbow1Pos = t0;
      servo[0].write(leftElbow1Pos);
    }

    if (leftElbow2Pos != t1)
    {
      moving = true;
      if (leftElbow2Pos < t1) leftElbow2Pos += servoStepSize;
      else leftElbow2Pos -= servoStepSize;
      if (abs(leftElbow2Pos - t1) < servoStepSize) leftElbow2Pos = t1;
      servo[1].write(leftElbow2Pos);
    }

    if (leftWristPos != t2)
    {
      moving = true;
      if (leftWristPos < t2) leftWristPos += servoStepSize;
      else leftWristPos -= servoStepSize;
      if (abs(leftWristPos - t2) < servoStepSize) leftWristPos = t2;
      servo[2].write(leftWristPos);
    }

    if (rightElbow1Pos != t3)
    {
      moving = true;
      if (rightElbow1Pos < t3) rightElbow1Pos += servoStepSize;
      else rightElbow1Pos -= servoStepSize;
      if (abs(rightElbow1Pos - t3) < servoStepSize) rightElbow1Pos = t3;
      servo[3].write(rightElbow1Pos);
    }

    if (rightElbow2Pos != t4)
    {
      moving = true;
      if (rightElbow2Pos < t4) rightElbow2Pos += servoStepSize;
      else rightElbow2Pos -= servoStepSize;
      if (abs(rightElbow2Pos - t4) < servoStepSize) rightElbow2Pos = t4;
      servo[4].write(rightElbow2Pos);
    }

    if (rightWristPos != t5)
    {
      moving = true;
      if (rightWristPos < t5) rightWristPos += servoStepSize;
      else rightWristPos -= servoStepSize;
      if (abs(rightWristPos - t5) < servoStepSize) rightWristPos = t5;
      servo[5].write(rightWristPos);
    }

    if (t6 >= 0 && neckPos != t6)
    {
      moving = true;
      if (neckPos < t6) neckPos += servoStepSize;
      else neckPos -= servoStepSize;
      if (abs(neckPos - t6) < servoStepSize) neckPos = t6;
      servo[6].write(neckPos);
    }

    delay(servoStepDelay);
  }
}

/* ================= NAMASTE ================= */
void namaste()
{
  smoothMoveAll(
    60, 50, 180,
    65, 125,80,
    neckPos
  );
}

/* ================= HAND REST ================= */
void handsRest()
{
  smoothMoveAll(
    initLeftElbow1, initLeftElbow2, initLeftWrist,
    initRightElbow1, initRightElbow2, initRightWrist,
    neckPos
  );
}

/* ================= LEFT ELBOW ================= */
void leftHandUp()
{
  if(leftElbow1Pos < 180)
  {
    leftElbow1Pos++;
    servo[0].write(leftElbow1Pos);
  }
}

void leftHandDown()
{
  if(leftElbow1Pos > 0)
  {
    leftElbow1Pos--;
    servo[0].write(leftElbow1Pos);
  }
}

/* ================= RIGHT ELBOW ================= */
void rightHandUp()
{
  if(rightElbow1Pos < 180)
  {
    rightElbow1Pos++;
    servo[3].write(rightElbow1Pos);
  }
}

void rightHandDown()
{
  if(rightElbow1Pos > 0)
  {
    rightElbow1Pos--;
    servo[3].write(rightElbow1Pos);
  }
}

/* ================= LEFT WRIST ================= */
void leftWristLeft()
{
  if(leftWristPos > 150)
  {
    leftWristPos--;
    servo[2].write(leftWristPos);
  }
}

void leftWristRight()
{
  if(leftWristPos < 180)
  {
    leftWristPos++;
    servo[2].write(leftWristPos);
  }
}

/* ================= RIGHT WRIST ================= */
void rightWristLeft()
{
  if(rightWristPos > 110)
  {
    rightWristPos--;
    servo[5].write(rightWristPos);
  }
}

void rightWristRight()
{
  if(rightWristPos < 80)
  {
    rightWristPos++;
    servo[5].write(rightWristPos);
  }
}

/* ================= NECK ================= */
void neckLeft()
{
  smoothMoveOne(6, neckPos, 40);
}

void neckRight()
{
  smoothMoveOne(6, neckPos, 150);
}

void neckCenter()
{
  smoothMoveOne(6, neckPos, initNeck);
}

/* ================= MOTOR SMOOTH ================= */
void applyMotorOutput(bool leftDir, bool rightDir, int pwmValue)
{
  digitalWrite(LEFT_DIR, leftDir);
  digitalWrite(RIGHT_DIR, rightDir);
  ledcWrite(LEFT_PWM, pwmValue);
  ledcWrite(RIGHT_PWM, pwmValue);
}

void setMotorTarget(MotorMode mode)
{
  targetMotorMode = mode;
}

void updateMotorsSmooth()
{
  if (millis() - lastMotorUpdate < motorRampDelay) return;
  lastMotorUpdate = millis();

  bool desiredLeftDir = currentLeftDir;
  bool desiredRightDir = currentRightDir;
  int targetPWM = 0;

  switch (targetMotorMode)
  {
    case MOTOR_FORWARD:
      // FORWARD = ACTUAL BACKWARD
      desiredLeftDir = LOW;
      desiredRightDir = LOW;
      targetPWM = moveSpeed;
      break;

    case MOTOR_BACKWARD:
      // BACKWARD = ACTUAL FORWARD
      desiredLeftDir = HIGH;
      desiredRightDir = HIGH;
      targetPWM = moveSpeed;
      break;

    case MOTOR_LEFT:
      // LEFT = ACTUAL RIGHT
      desiredLeftDir = HIGH;
      desiredRightDir = LOW;
      targetPWM = turnSpeed;
      break;

    case MOTOR_RIGHT:
      // RIGHT = ACTUAL LEFT
      desiredLeftDir = LOW;
      desiredRightDir = HIGH;
      targetPWM = turnSpeed;
      break;

    default:
      targetPWM = 0;
      break;
  }

  bool directionChangeNeeded =
    (targetMotorMode != MOTOR_STOP) &&
    ((desiredLeftDir != currentLeftDir) || (desiredRightDir != currentRightDir));

  // First ramp down to 0 before changing direction
  if (directionChangeNeeded && motorCurrentPWM > 0)
  {
    motorCurrentPWM -= motorRampStep;
    if (motorCurrentPWM < 0) motorCurrentPWM = 0;
    applyMotorOutput(currentLeftDir, currentRightDir, motorCurrentPWM);
    return;
  }

  // Apply new direction once fully stopped
  if (targetMotorMode != MOTOR_STOP)
  {
    currentLeftDir = desiredLeftDir;
    currentRightDir = desiredRightDir;
  }

  // Ramp toward target PWM
  if (motorCurrentPWM < targetPWM)
  {
    motorCurrentPWM += motorRampStep;
    if (motorCurrentPWM > targetPWM) motorCurrentPWM = targetPWM;
  }
  else if (motorCurrentPWM > targetPWM)
  {
    motorCurrentPWM -= motorRampStep;
    if (motorCurrentPWM < targetPWM) motorCurrentPWM = targetPWM;
  }

  applyMotorOutput(currentLeftDir, currentRightDir, motorCurrentPWM);
}

/* ================= ESP NOW RECEIVE ================= */
void onReceive(const esp_now_recv_info *info, const uint8_t *data, int len)
{
  memcpy(&incoming, data, sizeof(incoming));
  currentCommand = incoming.cmd;

  if (incoming.cmd == 12)
  {
    Serial.println("12");
  }

  sendToFace((uint8_t)incoming.cmd);
}

/* ================= SETUP ================= */
void setup()
{
  Serial.begin(115200);
  Wire.begin(21,22);

  for(int i=0;i<7;i++)
  {
    servo[i].attach(servoPins[i]);
  }

  writeAllServos();

  pinMode(LEFT_DIR, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);

  ledcAttach(LEFT_PWM,1000,8);
  ledcAttach(RIGHT_PWM,1000,8);

  applyMotorOutput(LOW, LOW, 0);

  WiFi.mode(WIFI_STA);

  if(esp_now_init()!=ESP_OK)
  {
    Serial.println("ESP NOW INIT FAILED");
    return;
  }

  esp_now_register_recv_cb(onReceive);
}

/* ================= LOOP ================= */
void loop()
{
  if (Serial.available())
  {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg == "12")
    {
      currentCommand = 0;
      namaste();
    }
    else if (msg == "13")
    {
      currentCommand = 0;
      handsRest();
    }
    else if (msg.startsWith("RECOGNISED:"))
    {
      String name = msg.substring(11);
      Serial.println("ACK:RECOGNISED:" + name);
    }
  }

  switch(currentCommand)
  {
    case 12: namaste(); currentCommand=0; break;
    case 13: handsRest(); currentCommand=0; break;

    case 14: leftHandUp(); break;
    case 15: leftHandDown(); break;

    case 18: rightHandUp(); break;
    case 19: rightHandDown(); break;

    case 16: leftWristLeft(); break;
    case 17: leftWristRight(); break;

    case 20: rightWristLeft(); break;
    case 21: rightWristRight(); break;

    case 5: neckLeft(); currentCommand=0; break;
    case 6: neckRight(); currentCommand=0; break;
    case 7: neckCenter(); currentCommand=0; break;

    case 8: setMotorTarget(MOTOR_FORWARD); break;
    case 9: setMotorTarget(MOTOR_BACKWARD); break;
    case 10: setMotorTarget(MOTOR_LEFT); break;
    case 11: setMotorTarget(MOTOR_RIGHT); break;

    default:
      setMotorTarget(MOTOR_STOP);
      break;
  }

  updateMotorsSmooth();
  delay(10);
}
