# StartSense Serial Communication Protocol Specification
**Document Version:** 1.0.0  
**Transport:** UART / USB Virtual COM Port (115200 8-N-1)  
**Encoding:** ASCII UTF-8 JSON Lines (terminated by `\r\n`)

---

## 1. STM32 -> Laptop Telemetry (Periodic @ 10 Hz)

The STM32 periodically broadcasts the digitized 12-bit potentiometer value:

```json
{"type":"POT","adc":2048,"volts":1.65,"seq":120}
```

| Key | Type | Description |
|---|---|---|
| `type` | string | `"POT"` identifier |
| `adc` | integer | Raw 12-bit ADC value (`0` to `4095`) |
| `volts` | float | Calculated voltage in Volts (`0.00` to `3.30` V) |
| `seq` | integer | Incremental packet sequence counter |

---

## 2. Laptop -> STM32 Safety Decision Command

When the ML intelligence pipeline analyzes a motor startup episode, it sends an operational recommendation:

```json
{"cmd":"REC","action":"ACCEPT_START","conf":0.96,"seq":1002}
```

| Key | Type | Allowed Values | Description |
|---|---|---|---|
| `cmd` | string | `"REC"` | Operational Recommendation command |
| `action` | string | `"ACCEPT_START"`, `"RETRY_SAFE_PROFILE"`, `"DERATE"`, `"STOP"` | Machine learning recommendation |
| `conf` | float | `0.00` - `1.00` | Model confidence probability |
| `seq` | integer | integer | Command sequence number |

---

## 3. STM32 -> Laptop Validation Acknowledgement

The embedded Cortex-M7 core on the STM32 validates the laptop recommendation against its hard local safety limits before responding:

```json
{"type":"ACK","action":"ACCEPT_START","status":"ACCEPTED","reason":"NONE_VALIDATED","seq":1002}
```

Or if rejected by local firmware limits:

```json
{"type":"ACK","action":"ACCEPT_START","status":"REJECTED","reason":"ERR_OVERCURRENT_HARDWARE","seq":1002}
```

| Key | Type | Allowed Values | Description |
|---|---|---|---|
| `type` | string | `"ACK"` | Acknowledgement identifier |
| `action` | string | string | Echoed recommended action |
| `status` | string | `"ACCEPTED"`, `"REJECTED"` | Embedded firmware validation verdict |
| `reason` | string | `"NONE_VALIDATED"`, `"ERR_OVERCURRENT_HARDWARE"`, `"ERR_OVERTEMP_HARDWARE"`, `"ERR_SPEED_NOT_REACHED"`, `"ERR_LINK_OFFLINE"` | Safety diagnostic reason code |
| `seq` | integer | integer | Sequence number matching command |
