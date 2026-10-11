#include "storm_data.h"

const int GREEN_PIN = 25, YELLOW_PIN = 26, RED_PIN = 27, BUZZER_PIN = 14;

const float THREAT_KM = 16.0;
const float K = 12.0;
const int RED_HOLD_MIN = 10;
const int SIM_MINUTES = 150;
const int MS_PER_SIM_MINUTE = 500;  

enum State { ST_GREEN, ST_YELLOW, ST_RED };
const char* STATE_NAMES[] = {"GREEN", "YELLOW", "RED"};

static double wt[N_STRIKES], wd[N_STRIKES];
static double kt[N_STRIKES], kd[N_STRIKES];

bool linfit(const double* x, const double* y, int n, double &slope, double &icpt) {
  double sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (int i = 0; i < n; i++) {
    sx += x[i]; sy += y[i]; sxx += x[i] * x[i]; sxy += x[i] * y[i];
  }
  double den = n * sxx - sx * sx;
  if (fabs(den) < 1e-9) return false;
  slope = (n * sxy - sx * sy) / den;
  icpt = (sy - slope * sx) / n;
  return true;
}

double estimateEta(double now) {
  int n = 0;
  for (int i = 0; i < N_STRIKES; i++) {
    if (STRIKE_T[i] <= now && STRIKE_T[i] > now - 20) {
      wt[n] = STRIKE_T[i]; wd[n] = STRIKE_D[i]; n++;
    }
  }
  if (n < 6) return -1;

  double slope, icpt;
  if (!linfit(wt, wd, n, slope, icpt)) return -1;

  double sum = 0, sumsq = 0;
  for (int i = 0; i < n; i++) {
    double r = wd[i] - (slope * wt[i] + icpt);
    sum += r; sumsq += r * r;
  }
  double mean = sum / n;
  double sd = sqrt(sumsq / n - mean * mean);
  int m = 0;
  for (int i = 0; i < n; i++) {
    double r = wd[i] - (slope * wt[i] + icpt);
    if (fabs(r) < 2 * sd) { kt[m] = wt[i]; kd[m] = wd[i]; m++; }
  }
  if (m >= 4) linfit(kt, kd, m, slope, icpt);

  if (slope > -0.05) return -1; 
  double current = slope * now + icpt;
  if (current <= 10) return 0;
  return (current - 10) / (-slope);
}


bool isReceding(double now) {
  double sumR = 0, sumE = 0;
  int nR = 0, nE = 0;
  for (int i = 0; i < N_STRIKES; i++) {
    double t = STRIKE_T[i];
    if (t > now) break;
    if (t > now - 10) { sumR += STRIKE_D[i]; nR++; }
    else if (t > now - 20) { sumE += STRIKE_D[i]; nE++; }
  }
  return nR >= 3 && nE >= 3 && (sumR / nR) > (sumE / nE) + 2;
}

double waitAdaptive(const double* closeT, int nClose) {
  if (nClose < 4) return 30.0;
  int m = nClose < 10 ? nClose : 10;
  double meanGap = (closeT[nClose - 1] - closeT[nClose - m]) / (m - 1);
  double w = K * meanGap;
  if (w < 5) w = 5;
  if (w > 30) w = 30;
  return w;
}

State alertState(double now) {
  int nSeen = 0, nRecentClose = 0;
  bool anyRecent30 = false;
  for (int i = 0; i < N_STRIKES; i++) {
    double t = STRIKE_T[i], d = STRIKE_D[i];
    if (t > now) break;
    nSeen++;
    if (t > now - 5 && d <= 10) nRecentClose++;
    if (t > now - 10 && d <= 30) anyRecent30 = true;
  }
  if (nSeen == 0) return ST_GREEN;

  if (nRecentClose >= 2) return ST_RED;

  double eta = estimateEta(now);
  if (eta >= 0 && eta <= 10 && !isReceding(now)) return ST_RED;

  int nClose = 0;
  for (int i = 0; i < N_STRIKES; i++) {
    if (STRIKE_T[i] > now) break;
    if (STRIKE_D[i] <= THREAT_KM) { wt[nClose] = STRIKE_T[i]; nClose++; }
  }

  if (nClose > 0) {
    if (now < wt[nClose - 1] + waitAdaptive(wt, nClose)) return ST_YELLOW;
  } else {
    if (anyRecent30) return ST_YELLOW;
  }
  return ST_GREEN;
}

void showState(State s) {
  digitalWrite(GREEN_PIN, s == ST_GREEN);
  digitalWrite(YELLOW_PIN, s == ST_YELLOW);
  digitalWrite(RED_PIN, s == ST_RED);
  digitalWrite(BUZZER_PIN, s == ST_RED);
}
int minuteNow = 0;
int prevState = -1;
int redStart = 0;

void setup() {
  Serial.begin(115200);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  Serial.println("Lightning warning box: replaying storm");
}

void loop() {
  State s = alertState(minuteNow);

  if (prevState == ST_RED && s != ST_RED && minuteNow - redStart < RED_HOLD_MIN) {
    s = ST_RED;
  }
  if (s == ST_RED && prevState != ST_RED) redStart = minuteNow;

  if ((int)s != prevState) {
    Serial.print("minute ");
    Serial.print(minuteNow);
    Serial.print(": ");
    Serial.println(STATE_NAMES[s]);
    showState(s);
  }
  prevState = s;

  minuteNow++;
  if (minuteNow >= SIM_MINUTES) {
    Serial.println("--- replay finished, restarting ---");
    delay(3000);
    minuteNow = 0;
    prevState = -1;
  }
  delay(MS_PER_SIM_MINUTE);
}