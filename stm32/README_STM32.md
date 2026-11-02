# StartSense - STM32 NUCLEO-H753ZI Integration Guide

This guide describes how to configure, compile, and flash the embedded firmware in **STM32CubeIDE** for the **StartSense** project.

---

## 1. Hardware Pinout & Wiring Diagram

| Component | Component Pin | NUCLEO-H753ZI Header Pin | Function |
|---|---|---|---|
| **100 kΩ Potentiometer** | Pin 1 (Outer leg) | **3.3V** (CN8 Pin 7 or CN7 Pin 16) | VDD Power Supply |
| **100 kΩ Potentiometer** | Pin 2 (Center Wiper) | **PA3 / A0** (CN9 Pin 1) | ADC1 Input (Analog In) |
| **100 kΩ Potentiometer** | Pin 3 (Outer leg) | **GND** (CN8 Pin 9 or 11) | Ground Reference |
| **USB Cable** | Micro-USB / Type-C | ST-LINK USB Connector (CN1) | Power + VCP Serial |

*(Optional 100 Ω resistor can be placed in series with Pin 2 wiper to breadboard PA3 as current limiter).*

### On-board User LEDs (Pre-wired on NUCLEO-H753ZI):
- **LD1 (Green, PB0):** Illuminates when laptop recommendation `ACCEPT_START` is validated and active.
- **LD2 (Yellow, PE1):** Illuminates when `DERATE` or `RETRY_SAFE_PROFILE` is engaged.
- **LD3 (Red, PB14):** Illuminates when `STOP` or an embedded safety violation occurs (Overcurrent/Overheat).

---

## 2. STM32CubeIDE Project Setup Steps

1. **Launch STM32CubeIDE**:
   - Click `File -> New -> STM32 Project`.
   - In the Board Selector tab, search for: `NUCLEO-H753ZI`.
   - Name the project: `StartSense_Nucleo`.
   - Initialize all peripherals with default mode: `Yes`.

2. **Pinout & Configuration (`.ioc` file)**:
   - **ADC1**:
     - Expand `Analog -> ADC1`.
     - Check `IN15` (mapped to `PA3`).
     - Configuration -> Parameter Settings: Resolution = `16 Bits` (or 12 Bits), Data Alignment = `Right alignment`.
   - **USART3 (ST-LINK Virtual COM Port)**:
     - Expand `Connectivity -> USART3`.
     - Mode: `Asynchronous`.
     - Baud Rate: `115200 Bits/s`, Word Length: `8 Bits`, Parity: `None`, Stop Bits: `1`.
     - In **NVIC Settings**, enable `USART3 global interrupt`.
   - **GPIO**:
     - `PB0` (Green LED) -> Output Push-Pull.
     - `PE1` (Yellow LED) -> Output Push-Pull.
     - `PB14` (Red LED) -> Output Push-Pull.

3. **Replace `Core/Src/main.c`**:
   - Copy the contents from `StartSense/stm32/Core/Src/main.c` into your project's `Core/Src/main.c`.

4. **Build & Flash**:
   - Connect the NUCLEO board to your laptop with the USB cable.
   - Click the **Hammer** icon (Build) or press `Ctrl + B`.
   - Click the **Run** (Play) icon or `Run -> Run As -> STM32 Cortex-M C/C++ Application`.

---

## 3. Connecting to the StartSense Dashboard

1. Open the StartSense Streamlit dashboard on your laptop.
2. In the sidebar under **STM32 Hardware Link**:
   - Set Connection Mode to: **Hardware (USB Serial)**.
   - Select your ST-LINK Virtual COM Port (e.g. `COM3` or `COM4`).
   - Baud Rate: `115200`.
   - Click **Connect Hardware**.
3. Turn the potentiometer knob:
   - Watch the real-time **Physical Potentiometer ADC** gauge on Page 2 update live!
   - Run a startup test on Page 3 or inspect safety decisions on Page 5.
