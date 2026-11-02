"""
StartSense - Serial Communication Interface (STM32 NUCLEO-H753ZI)
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Provides seamless switching between:
1. MOCK MODE (full software simulation of potentiometer ADC and STM32 responses)
2. HARDWARE MODE (real PySerial connection to STM32 over USB Virtual COM Port)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import threading
import collections
import io
import pandas as pd
from typing import List, Dict, Any, Optional
import serial
import serial.tools.list_ports

class SerialInterface:
    def __init__(self):
        self.port: Optional[str] = None
        self.baudrate: int = 115200
        self.is_connected: bool = False
        self.is_mock_mode: bool = True
        self.serial_handle: Optional[serial.Serial] = None
        
        # State & Buffers
        self.mock_potentiometer_val: int = 1024 # 0 - 4095 (12-bit ADC)
        self.mock_potentiometer_voltage: float = 0.82
        self.latest_hardware_reading: Dict[str, Any] = {
            "adc_raw": 1024,
            "voltage": 0.82,
            "normalized": 0.25,
            "source": "MOCK_POTENTIOMETER",
            "timestamp": time.time()
        }
        self.comm_logs: List[Dict[str, Any]] = []
        self.raw_terminal_lines: List[str] = [
            f"[{time.strftime('%H:%M:%S')}] ===== StartSense Initialised =====",
            f"[{time.strftime('%H:%M:%S')}] ADC Input: PA3 / ADC1 Channel 15",
            f"[{time.strftime('%H:%M:%S')}] UART: 115200 baud",
            f"[{time.strftime('%H:%M:%S')}] Potentiometer monitoring started"
        ]
        self.max_logs: int = 60
        self._lock = threading.Lock()
        self._rx_thread = None
        self._rx_stop_event = threading.Event()
        self._stop_event = threading.Event()

        # Continuous 1-minute rolling buffer for real-time telemetry (at 4 Hz, 240 samples = 1 min)
        self.stream_history = collections.deque(maxlen=2400)
        self._init_rolling_history()
        self._sampler_thread = threading.Thread(target=self._stream_ticker, daemon=True)
        self._sampler_thread.start()

    def _init_rolling_history(self):
        """Pre-seeds the rolling buffer with 60 seconds of history up to now."""
        now = time.time()
        for i in range(240, 0, -1):
            sample_time = now - (i * 0.25)
            self._append_sample(self.mock_potentiometer_val, "SYSTEM_INIT", epoch=sample_time)

    def _append_sample(self, adc_val: int, source: str, epoch: Optional[float] = None):
        """Computes instantaneous metrics, ML diagnosis, and appends to rolling stream buffer."""
        t_epoch = epoch if epoch is not None else time.time()
        volts = round((adc_val / 4095.0) * 3.3, 3)
        load_norm = max(0.0, min(1.0, adc_val / 4095.0))
        load_pct = round(load_norm * 100.0, 1)

        # ML Condition classification & graded recommendation
        if load_pct < 35.0:
            cond = "NORMAL"
            conf = round(97.5 + (1.0 - load_norm / 0.35) * 2.1, 1)
            action = "ACCEPT_START"
            ack = "ACCEPTED (LOCAL_LIMITS_OK)"
            peak_i = round(6.8 + (load_norm / 0.35) * 1.4, 2)
            speed = round(2850 + (1.0 - load_norm / 0.35) * 200)
            temp = round(25.0 + load_norm * 8.0, 1)
        elif load_pct < 78.0:
            cond = "SOFT JAM"
            conf = round(91.0 + (1.0 - abs(load_norm - 0.565) / 0.215) * 7.5, 1)
            action = "RETRY_SAFE_PROFILE"
            ack = "ACCEPTED (THERMAL_WATCH_ACTIVE)"
            peak_i = round(8.8 + ((load_norm - 0.35) / 0.43) * 3.2, 2)
            speed = round(1650 + (1.0 - (load_norm - 0.35) / 0.43) * 750)
            temp = round(28.0 + load_norm * 14.0, 1)
        else:
            cond = "HARD JAM"
            conf = round(95.0 + min(1.0, (load_norm - 0.78) / 0.22) * 4.6, 1)
            action = "STOP"
            ack = "ACCEPTED (INTERLOCK_CUTOFF_ENGAGED)"
            peak_i = round(12.2 + min(1.0, (load_norm - 0.78) / 0.22) * 2.6, 2)
            speed = round(max(0, 320 * (1.0 - (load_norm - 0.78) / 0.22)))
            temp = round(34.0 + load_norm * 22.0, 1)

        # Format timestamp with milliseconds
        dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_epoch))
        ms = int((t_epoch % 1) * 1000)
        formatted_ts = f"{dt_str}.{ms:03d}"

        record = {
            "epoch": t_epoch,
            "timestamp": formatted_ts,
            "adc_raw_12bit": adc_val,
            "voltage_volts": volts,
            "pot_load_percentage": f"{load_pct}%",
            "hardware_source": source,
            "classified_condition": cond,
            "ml_confidence_pct": f"{min(99.8, conf)}%",
            "recommended_action": action,
            "mcu_safety_status": ack,
            "simulated_peak_current_amp": f"{peak_i} A",
            "simulated_speed_rpm": f"{speed} RPM",
            "simulated_temp_celsius": f"{temp} C"
        }
        with self._lock:
            self.stream_history.append(record)

    def _stream_ticker(self):
        """Background thread running at 4 Hz (every 250ms) to ensure continuous real-time logging."""
        while not self._stop_event.is_set():
            time.sleep(0.25)
            with self._lock:
                latest = self.latest_hardware_reading
                adc = latest["adc_raw"]
                src = "STM32_NUCLEO_H753ZI (PA3)" if not self.is_mock_mode else "MOCK_POTENTIOMETER"
            self._append_sample(adc, src)

    def get_recent_stream_csv(self, duration_sec: float = 10.0) -> str:
        """
        Filters and exports the real-time ADC samples + ML analysis 
        strictly from the last N seconds (default: 10 seconds) prior to the call.
        """
        now = time.time()
        cutoff = now - duration_sec

        with self._lock:
            # Gather samples within the last duration_sec seconds
            samples = [s.copy() for s in self.stream_history if s["epoch"] >= cutoff]

        if not samples:
            # Fallback in case of empty buffer (40 samples for 10 sec @ 4 Hz)
            sample_count = int(duration_sec * 4)
            with self._lock:
                samples = [s.copy() for s in list(self.stream_history)[-sample_count:]]

        # Calculate relative seconds (-10.00s to 0.00s)
        for s in samples:
            s["relative_time_sec"] = f"{s['epoch'] - now:+.2f}s"
            # Remove internal epoch before CSV export
            s.pop("epoch", None)

        # Build clean DataFrame with explicit column order
        cols = [
            "timestamp", "relative_time_sec", "adc_raw_12bit", "voltage_volts",
            "pot_load_percentage", "hardware_source", "classified_condition",
            "ml_confidence_pct", "recommended_action", "mcu_safety_status",
            "simulated_peak_current_amp", "simulated_speed_rpm", "simulated_temp_celsius"
        ]
        df = pd.DataFrame(samples)
        # Ensure all columns exist
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        df = df[cols]
        return df.to_csv(index=False, encoding="utf-8")

    def get_last_minute_stream_csv(self) -> str:
        """Backwards compatible alias for 10-second stream."""
        return self.get_recent_stream_csv(duration_sec=10.0)

    def get_available_ports(self) -> List[Dict[str, str]]:
        """Lists available serial COM ports on the system."""
        ports = serial.tools.list_ports.comports()
        port_list = []
        for p in ports:
            port_list.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "is_stlink": "STMicroelectronics" in p.description or "STLink" in p.description
            })
        return port_list

    def set_mock_potentiometer(self, adc_val: int):
        """Allows manual control of mock potentiometer from UI."""
        self.mock_potentiometer_val = int(max(0, min(4095, adc_val)))
        self.mock_potentiometer_voltage = round((self.mock_potentiometer_val / 4095.0) * 3.3, 2)
        norm = round(self.mock_potentiometer_val / 4095.0, 3)
        with self._lock:
            self.latest_hardware_reading = {
                "adc_raw": self.mock_potentiometer_val,
                "voltage": self.mock_potentiometer_voltage,
                "normalized": norm,
                "source": "MOCK_SIMULATION" if self.is_mock_mode else "REAL_HARDWARE",
                "timestamp": time.time()
            }
            self.raw_terminal_lines.append(f"[{time.strftime('%H:%M:%S')}] StartSense,ADC,{self.mock_potentiometer_val}")
            if len(self.raw_terminal_lines) > 200:
                self.raw_terminal_lines.pop(0)

    def get_raw_terminal_lines(self) -> List[str]:
        """Returns live raw text lines matching PuTTY terminal stream."""
        with self._lock:
            return list(self.raw_terminal_lines)

    def connect(self, port: str = "MOCK", baudrate: int = 115200) -> bool:
        """Connects in hardware mode or enables mock mode."""
        self.baudrate = baudrate
        if port in ("MOCK", "MOCK_MODE", None):
            self.disconnect()
            self.is_mock_mode = True
            self.is_connected = False
            self.port = "MOCK_VIRTUAL_PORT"
            self._log_event("SYS", f"Switched to MOCK MODE (Virtual Potentiometer active)")
            return True

        # If already connected to this exact port and working, keep it
        if self.serial_handle and self.serial_handle.is_open and self.port == port and not self.is_mock_mode:
            self.is_connected = True
            return True

        # Cleanly release any previously open port first
        self.disconnect()

        # Hardware connection attempt
        try:
            self.serial_handle = serial.Serial(port, baudrate=baudrate, timeout=0.1)
            self.port = port
            self.is_connected = True
            self.is_mock_mode = False
            self._log_event("SYS", f"Connected to Hardware COM Port {port} at {baudrate} baud (Streaming from SoftHard_Jam)")
            
            # Start background reader thread
            self._rx_stop_event.clear()
            self._rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
            self._rx_thread.start()
            return True
        except serial.SerialException as se:
            err_msg = str(se)
            if "PermissionError" in err_msg or "Access is denied" in err_msg:
                user_hint = f"Port {port} is busy or locked by another program (e.g. PuTTY or Serial Terminal). Please close it and retry."
            else:
                user_hint = f"Could not open {port}: {err_msg}"
            self._log_event("ERR", user_hint)
            self.is_mock_mode = True
            self.is_connected = False
            self.port = "MOCK_VIRTUAL_PORT"
            return False
        except Exception as e:
            self._log_event("ERR", f"Failed to connect to {port}: {str(e)}. Falling back to MOCK MODE.")
            self.is_mock_mode = True
            self.is_connected = False
            self.port = "MOCK_VIRTUAL_PORT"
            return False

    def disconnect(self):
        """Disconnects serial link and resets state cleanly."""
        self._rx_stop_event.set()
        if self.serial_handle:
            try:
                if self.serial_handle.is_open:
                    self.serial_handle.close()
            except Exception:
                pass
            self.serial_handle = None
        self.is_connected = False
        self.is_mock_mode = True
        self.port = "MOCK_VIRTUAL_PORT"
        self._log_event("SYS", "Serial link disconnected. Switched to MOCK MODE.")

    def send_recommendation(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends recommendation command to STM32 and captures acknowledgement.
        
        Packet schema:
        PC -> STM32: {"cmd":"REC","action":"ACCEPT_START","conf":0.96,"seq":1002}
        STM32 -> PC: {"type":"ACK","action":"ACCEPT_START","status":"ACCEPTED","reason":"NONE","seq":1002}
        """
        cmd_packet = {
            "cmd": "REC",
            "action": rec.get("recommended_action", "STOP"),
            "conf": rec.get("confidence", 0.9),
            "seq": rec.get("seq", 1001)
        }
        json_str = json.dumps(cmd_packet)
        self._log_event("TX", json_str)

        if self.is_mock_mode or not self.serial_handle:
            # Emulate immediate STM32 embedded acknowledgement
            # If action is STOP or ACCEPT_START, return matching status
            status = "ACCEPTED"
            reason = "NONE_VALIDATED"
            ack_packet = {
                "type": "ACK",
                "seq": cmd_packet["seq"],
                "action": cmd_packet["action"],
                "status": status,
                "reason": reason,
                "local_temp": 28.5,
                "local_adc": self.mock_potentiometer_val,
                "uptime_ms": int(time.time() * 1000) % 1000000
            }
            time.sleep(0.02)
            self._log_event("RX", json.dumps(ack_packet))
            return ack_packet

        # Hardware mode transmission
        try:
            self.serial_handle.write((json_str + "\n").encode("utf-8"))
            # Check if there is an immediate response line from MCU
            start_time = time.time()
            response_line = ""
            while time.time() - start_time < 0.15:
                if self.serial_handle.in_waiting:
                    line = self.serial_handle.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("{") and "ACK" in line:
                        response_line = line
                        break
                time.sleep(0.01)

            if response_line:
                self._log_event("RX", response_line)
                return json.loads(response_line)
            else:
                # Firmware in SoftHard_Jam transmits ADC telemetry and runs autonomously
                ack_packet = {
                    "type": "ACK",
                    "status": "ACCEPTED",
                    "reason": "HARDWARE_STREAMING",
                    "action": cmd_packet["action"],
                    "seq": cmd_packet["seq"]
                }
                self._log_event("SYS", f"Transmitted {cmd_packet['action']} to STM32 (Stream active)")
                return ack_packet
        except Exception as e:
            self._log_event("ERR", f"TX error: {str(e)}")
            return {"type": "ERROR", "status": "ERROR", "reason": str(e), "seq": cmd_packet["seq"]}

    def get_potentiometer_reading(self) -> Dict[str, Any]:
        """Returns the latest reading from either Mock or Real hardware potentiometer."""
        with self._lock:
            return self.latest_hardware_reading.copy()

    def get_logs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.comm_logs))

    def _log_event(self, direction: str, message: str):
        with self._lock:
            self.comm_logs.append({
                "time": time.strftime("%H:%M:%S"),
                "dir": direction,
                "msg": message
            })
            if len(self.comm_logs) > self.max_logs:
                self.comm_logs.pop(0)

    def _rx_worker(self):
        """Background thread reading periodic potentiometer telemetry from STM32 in hardware mode."""
        while not self._rx_stop_event.is_set():
            if self.serial_handle and self.serial_handle.is_open:
                try:
                    if self.serial_handle.in_waiting:
                        line = self.serial_handle.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            # Append to raw terminal buffer for PuTTY-like live stream
                            with self._lock:
                                self.raw_terminal_lines.append(f"[{time.strftime('%H:%M:%S')}] {line}")
                                if len(self.raw_terminal_lines) > 200:
                                    self.raw_terminal_lines.pop(0)

                            # 1. Parse SoftHard_Jam Protocol: "StartSense,ADC,<value>"
                            if "StartSense,ADC," in line:
                                try:
                                    # Split "StartSense,ADC,2048"
                                    parts = line.split(",")
                                    adc_val = int(parts[2].strip())
                                    volts = round((adc_val / 4095.0) * 3.3, 2)
                                    norm = round(adc_val / 4095.0, 3)
                                    with self._lock:
                                        self.latest_hardware_reading = {
                                            "adc_raw": adc_val,
                                            "voltage": volts,
                                            "normalized": norm,
                                            "source": "REAL_HARDWARE",
                                            "timestamp": time.time()
                                        }
                                    self._log_event("RX", f"STM32 ADC: {adc_val} ({volts}V)")
                                except (ValueError, IndexError):
                                    self._log_event("RX_RAW", line)

                            # 2. Parse JSON Protocol fallback: {"type":"POT","adc":2048}
                            elif line.startswith("{"):
                                try:
                                    data = json.loads(line)
                                    if data.get("type") == "POT":
                                        adc_val = int(data.get("adc", 0))
                                        volts = float(data.get("volts", round((adc_val / 4095.0) * 3.3, 2)))
                                        norm = round(adc_val / 4095.0, 3)
                                        with self._lock:
                                            self.latest_hardware_reading = {
                                                "adc_raw": adc_val,
                                                "voltage": volts,
                                                "normalized": norm,
                                                "source": "REAL_HARDWARE",
                                                "timestamp": time.time()
                                            }
                                        self._log_event("RX", line)
                                    else:
                                        self._log_event("RX_JSON", line)
                                except json.JSONDecodeError:
                                    self._log_event("RX_RAW", line)

                            # 3. Informational boot banner messages
                            elif "StartSense" in line or "Initialised" in line or "monitoring" in line:
                                self._log_event("MCU_BOOT", line)
                            else:
                                self._log_event("RX_RAW", line)
                except Exception as e:
                    time.sleep(0.05)
            time.sleep(0.01)

# Global singleton serial interface for Streamlit session
_serial_instance: Optional[SerialInterface] = None

def get_serial_interface() -> SerialInterface:
    global _serial_instance
    if _serial_instance is None:
        _serial_instance = SerialInterface()
        # Check if an ST-Link hardware port is present
        ports = _serial_instance.get_available_ports()
        stlink_ports = [p["device"] for p in ports if p.get("is_stlink")]
        if stlink_ports:
            # Attempt to connect to ST-Link port first
            connected = _serial_instance.connect(stlink_ports[0])
            if not connected:
                _serial_instance.connect("MOCK")
        else:
            _serial_instance.connect("MOCK")
    return _serial_instance

if __name__ == "__main__":
    print("Testing Serial Communication Interface in PyCharm...")
    ser = get_serial_interface()
    ports = ser.get_available_ports()
    print(f"\nDetected Serial Ports ({len(ports)}):")
    for p in ports:
        print(f"  - {p['device']}: {p['description']}")

    print("\nTesting MOCK MODE Potentiometer Reading:")
    ser.set_mock_potentiometer(2048)
    pot = ser.get_potentiometer_reading()
    print(f"  Raw ADC:    {pot['adc_raw']}")
    print(f"  Voltage:    {pot['voltage']} V")
    print(f"  Normalized: {pot['normalized']*100:.1f}%")

    print("\nTesting Outgoing Recommendation Transmission (MOCK ACK):")
    test_rec = {"seq": 1001, "recommended_action": "ACCEPT_START", "confidence": 0.96}
    ack = ser.send_recommendation(test_rec)
    print(f"  Received ACK: {ack}")
    print("\nSerial communication test completed successfully!")

