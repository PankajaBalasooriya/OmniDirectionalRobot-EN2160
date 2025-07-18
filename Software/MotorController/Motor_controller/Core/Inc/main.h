/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */
ADC_HandleTypeDef* Get_HADC1_Ptr(void);

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define M4_INA_Pin GPIO_PIN_2
#define M4_INA_GPIO_Port GPIOC
#define M4_INB_Pin GPIO_PIN_3
#define M4_INB_GPIO_Port GPIOC
#define M4_EncoderCH1_Pin GPIO_PIN_0
#define M4_EncoderCH1_GPIO_Port GPIOA
#define M4_EncoderCH2_Pin GPIO_PIN_1
#define M4_EncoderCH2_GPIO_Port GPIOA
#define M1_CS_Pin GPIO_PIN_4
#define M1_CS_GPIO_Port GPIOA
#define M2_CS_Pin GPIO_PIN_5
#define M2_CS_GPIO_Port GPIOA
#define M3_CS_Pin GPIO_PIN_6
#define M3_CS_GPIO_Port GPIOA
#define M4_CS_Pin GPIO_PIN_7
#define M4_CS_GPIO_Port GPIOA
#define TX_EN_Pin GPIO_PIN_4
#define TX_EN_GPIO_Port GPIOC
#define LED_RX_Pin GPIO_PIN_1
#define LED_RX_GPIO_Port GPIOB
#define LED_TX_Pin GPIO_PIN_2
#define LED_TX_GPIO_Port GPIOB
#define M2_EncoderCH1_Pin GPIO_PIN_6
#define M2_EncoderCH1_GPIO_Port GPIOC
#define M2_EncoderCH2_Pin GPIO_PIN_7
#define M2_EncoderCH2_GPIO_Port GPIOC
#define M2_INA_Pin GPIO_PIN_8
#define M2_INA_GPIO_Port GPIOC
#define M2_INB_Pin GPIO_PIN_9
#define M2_INB_GPIO_Port GPIOC
#define M1_PWM_Pin GPIO_PIN_8
#define M1_PWM_GPIO_Port GPIOA
#define M2_PWM_Pin GPIO_PIN_9
#define M2_PWM_GPIO_Port GPIOA
#define M3_PWM_Pin GPIO_PIN_10
#define M3_PWM_GPIO_Port GPIOA
#define M4_PWM_Pin GPIO_PIN_11
#define M4_PWM_GPIO_Port GPIOA
#define Status_LED_Pin GPIO_PIN_12
#define Status_LED_GPIO_Port GPIOA
#define TMS_Pin GPIO_PIN_13
#define TMS_GPIO_Port GPIOA
#define TCK_Pin GPIO_PIN_14
#define TCK_GPIO_Port GPIOA
#define M1_EncoderCH1_Pin GPIO_PIN_15
#define M1_EncoderCH1_GPIO_Port GPIOA
#define M1_INA_Pin GPIO_PIN_10
#define M1_INA_GPIO_Port GPIOC
#define M1_INB_Pin GPIO_PIN_11
#define M1_INB_GPIO_Port GPIOC
#define M1_EncoderCH2_Pin GPIO_PIN_3
#define M1_EncoderCH2_GPIO_Port GPIOB
#define M3_INA_Pin GPIO_PIN_4
#define M3_INA_GPIO_Port GPIOB
#define M3_INB_Pin GPIO_PIN_5
#define M3_INB_GPIO_Port GPIOB
#define M3_EncoderCH1_Pin GPIO_PIN_6
#define M3_EncoderCH1_GPIO_Port GPIOB
#define M3_EncoderCH2_Pin GPIO_PIN_7
#define M3_EncoderCH2_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
