/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  * @board          : STM32 NUCLEO-H753ZI
  ******************************************************************************
  */

#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32h7xx_hal.h"

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* Private defines -----------------------------------------------------------*/
#define USER_LED_GREEN_PIN    GPIO_PIN_0
#define USER_LED_GREEN_PORT   GPIOB
#define USER_LED_YELLOW_PIN   GPIO_PIN_1
#define USER_LED_YELLOW_PORT  GPIOE
#define USER_LED_RED_PIN      GPIO_PIN_14
#define USER_LED_RED_PORT     GPIOB

#define POT_ADC_PIN           GPIO_PIN_3
#define POT_ADC_PORT          GPIOA

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
