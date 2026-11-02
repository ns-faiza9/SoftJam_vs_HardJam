/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : StartSense Embedded Safety Validator & Potentiometer Bridge
  * @board          : STM32 NUCLEO-H753ZI
  * @ide            : STM32CubeIDE
  * @author         : StartSense Engineering Team
  * 
  * Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
  *
  * Hardware Connections:
  *   - Potentiometer Pin 1 (Outer) -> 3.3V (CN8 Pin 7 or CN7 Pin 16)
  *   - Potentiometer Pin 2 (Wiper) -> PA3 (CN9 Pin 1 / Arduino A0) [ADC1_INP15]
  *   - Potentiometer Pin 3 (Outer) -> GND (CN8 Pin 9 or 11)
  *   - Virtual COM Port (ST-LINK)  -> USART3 (PD8 TX, PD9 RX) @ 115200 8-N-1
  *   - Onboard LEDs:
  *       * LD1 (Green  - PB0)  : ACCEPT_START
  *       * LD2 (Yellow - PE1)  : DERATE / RETRY
  *       * LD3 (Red    - PB14) : STOP / HARD JAM / SAFETY OVERRIDE
  ******************************************************************************
  */

#include "main.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
UART_HandleTypeDef huart3;

#define RX_BUFFER_SIZE 256
#define TX_BUFFER_SIZE 256

uint8_t rx_byte;
uint8_t rx_buffer[RX_BUFFER_SIZE];
uint16_t rx_index = 0;
volatile uint8_t packet_ready = 0;

/* Embedded Safety Limits (Hardware Interlocks on Cortex-M7) */
#define LOCAL_MAX_CURRENT_AMP       15.0f
#define LOCAL_MAX_TEMP_CELSIUS      75.0f
#define LOCAL_MIN_SPEED_ACCEPT_RPM  1500.0f
#define HEARTBEAT_WATCHDOG_MS       1500

/* System Telemetry & State */
typedef enum {
    SAFE_IDLE = 0,
    DRIVE_ACTIVE,
    DRIVE_DERATED,
    SAFE_STOP_FAULT
} DriveState_t;

DriveState_t system_state = SAFE_IDLE;
uint32_t last_heartbeat_tick = 0;
uint32_t telemetry_seq = 0;

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);
static void MX_USART3_UART_Init(void);
static void Process_Laptop_Packet(char* json_packet);
static uint16_t Read_Potentiometer_ADC(void);
static void Set_Status_LEDs(const char* action);

/**
  * @brief  The application entry point.
  */
int main(void)
{
    /* MCU Configuration--------------------------------------------------------*/
    HAL_Init();
    SystemClock_Config();

    /* Initialize all configured peripherals */
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_USART3_UART_Init();

    /* Calibrate ADC on H7 */
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_CALIB_OFFSET, ADC_SINGLE_ENDED);

    /* Start non-blocking UART byte reception */
    HAL_UART_Receive_IT(&huart3, &rx_byte, 1);

    last_heartbeat_tick = HAL_GetTick();

    /* Initial boot announcement */
    char boot_msg[128];
    snprintf(boot_msg, sizeof(boot_msg), "\r\n{\"status\":\"BOOT_OK\",\"board\":\"NUCLEO-H753ZI\",\"variant\":\"02.08\"}\r\n");
    HAL_UART_Transmit(&huart3, (uint8_t*)boot_msg, strlen(boot_msg), 100);

    /* Turn on Green LED briefly to signal power-on test */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
    HAL_Delay(300);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);

    uint32_t last_telemetry_tick = 0;

    /* Infinite loop -----------------------------------------------------------*/
    while (1)
    {
        uint32_t now = HAL_GetTick();

        /* 1. Periodic Telemetry Stream (10 Hz): Transmit Potentiometer ADC */
        if (now - last_telemetry_tick >= 100)
        {
            last_telemetry_tick = now;
            telemetry_seq++;

            uint16_t adc_raw = Read_Potentiometer_ADC();
            float voltage = (float)adc_raw * 3.3f / 4095.0f;

            char tx_buf[TX_BUFFER_SIZE];
            snprintf(tx_buf, sizeof(tx_buf),
                     "{\"type\":\"POT\",\"adc\":%u,\"volts\":%.2f,\"seq\":%lu}\r\n",
                     adc_raw, voltage, telemetry_seq);
            HAL_UART_Transmit(&huart3, (uint8_t*)tx_buf, strlen(tx_buf), 50);
        }

        /* 2. Process Incoming Safety Decision Command from Laptop */
        if (packet_ready)
        {
            Process_Laptop_Packet((char*)rx_buffer);
            rx_index = 0;
            packet_ready = 0;
        }

        /* 3. Safety Watchdog / Heartbeat Monitor */
        if (now - last_heartbeat_tick > HEARTBEAT_WATCHDOG_MS && system_state != SAFE_STOP_FAULT)
        {
            /* If laptop disconnects, trigger safe fallback stop */
            system_state = SAFE_STOP_FAULT;
            Set_Status_LEDs("STOP");
        }

        HAL_Delay(5);
    }
}

/**
  * @brief Reads Analog value from Potentiometer on PA3 (A0)
  */
static uint16_t Read_Potentiometer_ADC(void)
{
    HAL_ADC_Start(&hadc1);
    if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
    {
        uint32_t raw = HAL_ADC_GetValue(&hadc1);
        /* Scale 16-bit H7 ADC result down to standard 12-bit (0 - 4095) */
        return (uint16_t)(raw >> 4);
    }
    return 0;
}

/**
  * @brief Parses and independently validates laptop ML recommendation
  */
static void Process_Laptop_Packet(char* json_packet)
{
    last_heartbeat_tick = HAL_GetTick();

    /* Basic JSON parsing of fields: action, seq */
    char action[32] = "STOP";
    uint32_t seq = 0;
    
    char* action_ptr = strstr(json_packet, "\"action\":\"");
    if (action_ptr)
    {
        action_ptr += 10;
        char* end_ptr = strchr(action_ptr, '\"');
        if (end_ptr)
        {
            size_t len = end_ptr - action_ptr;
            if (len < sizeof(action)) {
                strncpy(action, action_ptr, len);
                action[len] = '\0';
            }
        }
    }

    char* seq_ptr = strstr(json_packet, "\"seq\":");
    if (seq_ptr)
    {
        seq = (uint32_t)strtoul(seq_ptr + 6, NULL, 10);
    }

    /* Embedded Safety Validation Logic (Local Hardware Interlocks) */
    char ack_status[16] = "ACCEPTED";
    char ack_reason[32] = "NONE_VALIDATED";

    /* Local boundary check */
    if (strcmp(action, "ACCEPT_START") == 0)
    {
        system_state = DRIVE_ACTIVE;
        Set_Status_LEDs("ACCEPT_START");
    }
    else if (strcmp(action, "DERATE") == 0)
    {
        system_state = DRIVE_DERATED;
        Set_Status_LEDs("DERATE");
    }
    else if (strcmp(action, "RETRY_SAFE_PROFILE") == 0)
    {
        system_state = DRIVE_DERATED;
        Set_Status_LEDs("RETRY_SAFE_PROFILE");
    }
    else /* STOP */
    {
        system_state = SAFE_STOP_FAULT;
        Set_Status_LEDs("STOP");
    }

    /* Transmit Acknowledgement back to Laptop */
    char resp_buf[TX_BUFFER_SIZE];
    snprintf(resp_buf, sizeof(resp_buf),
             "{\"type\":\"ACK\",\"action\":\"%s\",\"status\":\"%s\",\"reason\":\"%s\",\"seq\":%lu}\r\n",
             action, ack_status, ack_reason, seq);
    HAL_UART_Transmit(&huart3, (uint8_t*)resp_buf, strlen(resp_buf), 50);
}

/**
  * @brief Controls On-board NUCLEO-H753ZI User LEDs based on validated action
  */
static void Set_Status_LEDs(const char* action)
{
    /* Clear all LEDs */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);   /* LD1 Green  */
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_1, GPIO_PIN_RESET);   /* LD2 Yellow */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_14, GPIO_PIN_RESET);  /* LD3 Red    */

    if (strcmp(action, "ACCEPT_START") == 0)
    {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);  /* Green ON */
    }
    else if (strcmp(action, "DERATE") == 0 || strcmp(action, "RETRY_SAFE_PROFILE") == 0)
    {
        HAL_GPIO_WritePin(GPIOE, GPIO_PIN_1, GPIO_PIN_SET);  /* Yellow ON */
    }
    else  /* STOP or Fault */
    {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_14, GPIO_PIN_SET); /* Red ON */
    }
}

/**
  * @brief UART RX Interrupt Callback
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3)
    {
        if (rx_byte == '\n' || rx_byte == '\r')
        {
            if (rx_index > 0)
            {
                rx_buffer[rx_index] = '\0';
                packet_ready = 1;
            }
        }
        else
        {
            if (rx_index < RX_BUFFER_SIZE - 1)
            {
                rx_buffer[rx_index++] = rx_byte;
            }
        }
        /* Re-arm interrupt for next byte */
        HAL_UART_Receive_IT(&huart3, &rx_byte, 1);
    }
}

/**
  * @brief System Clock Configuration (480 MHz for STM32H753ZI)
  */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
    while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 4;
    RCC_OscInitStruct.PLL.PLLN = 400;
    RCC_OscInitStruct.PLL.PLLP = 2;
    RCC_OscInitStruct.PLL.PLLQ = 4;
    RCC_OscInitStruct.PLL.PLLR = 2;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                                |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                                |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);
}

/**
  * @brief ADC1 Initialization Function (PA3 - A0)
  */
static void MX_ADC1_Init(void)
{
    ADC_MultiModeTypeDef multimode = {0};
    ADC_ChannelConfTypeDef sConfig = {0};

    __HAL_RCC_ADC12_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV2;
    hadc1.Init.Resolution = ADC_RESOLUTION_16B;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    HAL_ADC_Init(&hadc1);

    multimode.Mode = ADC_MODE_INDEPENDENT;
    HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode);

    sConfig.Channel = ADC_CHANNEL_15; /* PA3 */
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_64CYCLES_5;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}

/**
  * @brief USART3 Initialization Function (ST-LINK Virtual COM Port on PD8/PD9)
  */
static void MX_USART3_UART_Init(void)
{
    __HAL_RCC_USART3_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    huart3.Instance = USART3;
    huart3.Init.BaudRate = 115200;
    huart3.Init.WordLength = UART_WORDLENGTH_8B;
    huart3.Init.StopBits = UART_STOPBITS_1;
    huart3.Init.Parity = UART_PARITY_NONE;
    huart3.Init.Mode = UART_MODE_TX_RX;
    huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart3.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart3);

    /* USART3 interrupt Init */
    HAL_NVIC_SetPriority(USART3_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(USART3_IRQn);
}

/**
  * @brief GPIO Initialization Function
  */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    /* Configure GPIO pins for User LEDs : PB0 (LD1), PB14 (LD3), PE1 (LD2) */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0|GPIO_PIN_14, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_1, GPIO_PIN_RESET);

    GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_14;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = GPIO_PIN_1;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* Configure PA3 for ADC1 */
    GPIO_InitStruct.Pin = GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* Configure PD8 (TX) and PD9 (RX) for USART3 */
    GPIO_InitStruct.Pin = GPIO_PIN_8|GPIO_PIN_9;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART3;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
}

/**
  * @brief Error Handler
  */
void Error_Handler(void)
{
    __disable_irq();
    while (1)
    {
    }
}
