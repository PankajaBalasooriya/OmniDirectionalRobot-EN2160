/*
 * motors.h
 *
 *  Created on: Apr 25, 2025
 *      Author: PANKAJA
 */

#ifndef INC_MOTORS_H_
#define INC_MOTORS_H_

#define GPIOB_BSRR          (*(volatile uint32_t *)(GPIOB_BASE + 0x18))

#define INA_PIN             0  // PB0
#define INB_PIN             1  // PB1

#define NUM_SAMPLES 128

#define PWM_MAX 1 //  do not exceed 1
#define MAX_TIMER_COUNTS 7199

float limitPWM(float pwm);
void setMotorPWM(float pwm);
void resetMotors();

uint16_t analogRead();
uint16_t getCurrentMilliamps();

#endif /* INC_MOTORS_H_ */
