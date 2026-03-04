//
//Define outputs here
#define leftFWD   16
#define leftREV   17
#define rightFWD  18
#define rightREV  19
#define LED_BUILTIN 2
//

void forward(){
  digitalWrite(leftFWD, HIGH);
  digitalWrite(leftREV, LOW);
  digitalWrite(rightFWD, HIGH);
  digitalWrite(rightREV, LOW);

  return;
}

void reverse(){
  digitalWrite(leftFWD, LOW);
  digitalWrite(leftREV, HIGH);
  digitalWrite(rightFWD, LOW);
  digitalWrite(rightREV, HIGH);

  return;
}

void inactive(){
  digitalWrite(leftFWD, LOW);
  digitalWrite(leftREV, LOW);
  digitalWrite(rightFWD, LOW);
  digitalWrite(rightREV, LOW);

  return;
}

void ledON(){
  digitalWrite(LED_BUILTIN, LOW);
}

void ledOFF(){
  digitalWrite(LED_BUILTIN, HIGH);
}

