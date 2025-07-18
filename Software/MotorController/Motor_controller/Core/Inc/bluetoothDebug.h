/*
 * bluetoothDebug.h
 *
 *  Created on: Jul 2, 2025
 *      Author: PANKAJA
 */

#ifndef INC_BLUETOOTHDEBUG_H_
#define INC_BLUETOOTHDEBUG_H_


#include "stm32f4xx_hal.h"

// Function prototypes
void UART_Init(UART_HandleTypeDef *huart);    // Initialize UART
void UART_Transmit(UART_HandleTypeDef *huart, char *data);  // Transmit string data
void UART_Transmit_Float(UART_HandleTypeDef *huart, const char *header, float number, uint8_t decimal_points);  // Transmit float with customizable header
void UART_Transmit_Int(UART_HandleTypeDef *huart, const char *header, int number);  // Transmit integer with customizable header

void UART_Transmit_IR(UART_HandleTypeDef *huart, uint16_t IRL, uint16_t IRR);
void UART_Transmit_TOF(UART_HandleTypeDef *huart, uint16_t TOF1, uint16_t TOF2, uint16_t TOF3, uint16_t TOF4);
void UART_Transmit_WheelW(UART_HandleTypeDef *huart, float W1, float W2, float W3, float W4);


#endif /* INC_BLUETOOTHDEBUG_H_ */
