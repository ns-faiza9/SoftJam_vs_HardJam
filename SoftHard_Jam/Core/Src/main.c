
/* USER CODE BEGIN Header */
/**
  * @file           : main.c
  * @brief          : StartSense - ADC and UART test
  */
/* USER CODE END Header */

#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

COM_InitTypeDef BspCOMInit;
ADC_HandleTypeDef hadc1;

/* USER CODE BEGIN PV */
uint32_t adc_value = 0;
char uart_buffer[64];
int uart_length = 0;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);

/* USER CODE BEGIN PFP */
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

static void StartSense_SendMessage(const char *message)
{
    HAL_UART_Transmit(
        &hcom_uart[COM1],
        (uint8_t *)message,
        (uint16_t)strlen(message),
        100
    );
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
    /* MPU Configuration */
    MPU_Config();

    /* MCU Configuration */
    HAL_Init();

    /* Configure the system clock */
    SystemClock_Config();

    /* Initialize configured peripherals */
    MX_GPIO_Init();
    MX_ADC1_Init();

    /* Initialize LEDs */
    BSP_LED_Init(LED_GREEN);
    BSP_LED_Init(LED_YELLOW);
    BSP_LED_Init(LED_RED);

    /* Initialize user button */
    BSP_PB_Init(BUTTON_USER, BUTTON_MODE_EXTI);

    /* Initialize Virtual COM Port */
    BspCOMInit.BaudRate = 115200;
    BspCOMInit.WordLength = COM_WORDLENGTH_8B;
    BspCOMInit.StopBits = COM_STOPBITS_1;
    BspCOMInit.Parity = COM_PARITY_NONE;
    BspCOMInit.HwFlowCtl = COM_HWCONTROL_NONE;

    if (BSP_COM_Init(COM1, &BspCOMInit) != BSP_ERROR_NONE)
    {
        Error_Handler();
    }

    /* USER CODE BEGIN 2 */

    HAL_Delay(500);

    StartSense_SendMessage(
        "\r\n===== StartSense Initialised =====\r\n"
    );

    StartSense_SendMessage(
        "ADC Input: PA3 / ADC1 Channel 15\r\n"
    );

    StartSense_SendMessage(
        "UART: 115200 baud\r\n"
    );

    StartSense_SendMessage(
        "Potentiometer monitoring started\r\n\r\n"
    );

    BSP_LED_On(LED_GREEN);

    /* USER CODE END 2 */

    /* Infinite loop */
    /* USER CODE BEGIN WHILE */
    while (1)
    {
        if (HAL_ADC_Start(&hadc1) == HAL_OK)
        {
            if (HAL_ADC_PollForConversion(&hadc1, 100) == HAL_OK)
            {
                adc_value = HAL_ADC_GetValue(&hadc1);

                uart_length = snprintf(
                    uart_buffer,
                    sizeof(uart_buffer),
                    "StartSense,ADC,%lu\r\n",
                    (unsigned long)adc_value
                );

                if (uart_length > 0 &&
                    uart_length < (int)sizeof(uart_buffer))
                {
                    if (HAL_UART_Transmit(
                        &hcom_uart[COM1],
                        (uint8_t *)uart_buffer,
                        (uint16_t)uart_length,
                        100
                    ) != HAL_OK)
                    {
                        BSP_LED_On(LED_RED);
                    }
                }
            }
            else
            {
                BSP_LED_On(LED_RED);
            }

            HAL_ADC_Stop(&hadc1);
        }
        else
        {
            BSP_LED_On(LED_RED);
        }

        HAL_Delay(250);

        /* USER CODE END WHILE */

        /* USER CODE BEGIN 3 */
    }
    /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Supply configuration update enable */
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

    /* Configure the main internal regulator output voltage */
    __HAL_PWR_VOLTAGESCALING_CONFIG(
        PWR_REGULATOR_VOLTAGE_SCALE2
    );

    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY))
    {
    }

    /* Configure PLL clock source */
    __HAL_RCC_PLL_PLLSOURCE_CONFIG(RCC_PLLSOURCE_HSI);

    /* Initialize RCC oscillators */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_DIV1;
    RCC_OscInitStruct.HSICalibrationValue =
        RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    /* Initialize CPU, AHB and APB clocks */
    RCC_ClkInitStruct.ClockType =
        RCC_CLOCKTYPE_HCLK |
        RCC_CLOCKTYPE_SYSCLK |
        RCC_CLOCKTYPE_PCLK1 |
        RCC_CLOCKTYPE_PCLK2 |
        RCC_CLOCKTYPE_D3PCLK1 |
        RCC_CLOCKTYPE_D1PCLK1;

    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
    RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV1;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV1;

    if (HAL_RCC_ClockConfig(
        &RCC_ClkInitStruct,
        FLASH_LATENCY_1
    ) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief ADC1 Initialization Function
  */
static void MX_ADC1_Init(void)
{
    ADC_MultiModeTypeDef multimode = {0};
    ADC_ChannelConfTypeDef sConfig = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV2;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge =
        ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ConversionDataManagement =
        ADC_CONVERSIONDATA_DR;
    hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    hadc1.Init.LeftBitShift = ADC_LEFTBITSHIFT_NONE;
    hadc1.Init.OversamplingMode = DISABLE;
    hadc1.Init.Oversampling.Ratio = 1;

    if (HAL_ADC_Init(&hadc1) != HAL_OK)
    {
        Error_Handler();
    }

    multimode.Mode = ADC_MODE_INDEPENDENT;

    if (HAL_ADCEx_MultiModeConfigChannel(
        &hadc1,
        &multimode
    ) != HAL_OK)
    {
        Error_Handler();
    }

    sConfig.Channel = ADC_CHANNEL_15;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_64CYCLES_5;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    sConfig.Offset = 0;
    sConfig.OffsetSignedSaturation = DISABLE;

    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief GPIO Initialization Function
  */
static void MX_GPIO_Init(void)
{
    /* GPIO Ports Clock Enable */
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
}

/* USER CODE BEGIN 4 */
/* USER CODE END 4 */

/**
  * @brief MPU Configuration
  */
void MPU_Config(void)
{
    MPU_Region_InitTypeDef MPU_InitStruct = {0};

    HAL_MPU_Disable();

    MPU_InitStruct.Enable = MPU_REGION_ENABLE;
    MPU_InitStruct.Number = MPU_REGION_NUMBER0;
    MPU_InitStruct.BaseAddress = 0x0;
    MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
    MPU_InitStruct.SubRegionDisable = 0x87;
    MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
    MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
    MPU_InitStruct.DisableExec =
        MPU_INSTRUCTION_ACCESS_DISABLE;
    MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
    MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
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

#ifdef USE_FULL_ASSERT

void assert_failed(uint8_t *file, uint32_t line)
{
    (void)file;
    (void)line;
}

#endif
