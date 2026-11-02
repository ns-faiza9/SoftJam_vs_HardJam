"""
StartSense - Safety Decision Engine & Local Hardware Validation
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Architectural Rule:
The ML model CANNOT write PWM registers or PID values directly.
It recommends strictly one of four safe operational actions:
1. ACCEPT_START
2. RETRY_SAFE_PROFILE
3. DERATE
4. STOP

The embedded STM32 NUCLEO-H753ZI firmware independently checks this recommendation
against hardware safety envelopes (Current limit, Thermal headroom, Stall time, Watchdog heartbeat).
"""

import sys
from pathlib import Path

# Add project root to path for PyCharm standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
from typing import Dict, Any, Tuple
from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP,
    SAFETY_LIMITS
)

class SafetyDecisionEngine:
    def __init__(self, model_version: str = "StartSense_v1.0_RF"):
        self.model_version = model_version
        self.sequence_counter = 1000

    def formulate_recommendation(
        self,
        predicted_condition: str,
        confidence: float,
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Translates ML prediction & feature boundaries into a safe operational recommendation.
        """
        self.sequence_counter += 1
        seq = self.sequence_counter

        # Decision rules
        if predicted_condition == CLASS_NORMAL:
            if confidence >= 0.70:
                action = ACTION_ACCEPT_START
                rationale = "Healthy rotor acceleration and nominal inrush profile within safety bounds."
            else:
                action = ACTION_RETRY_SAFE
                rationale = "Normal pattern detected but low ML confidence; recommended retry with safe soft ramp."
        elif predicted_condition == CLASS_SOFT_JAM:
            # Check thermal headroom and duration
            if features.get("final_temp_celsius", 25.0) < 55.0 and features.get("peak_current_amp", 10.0) < 13.0:
                action = ACTION_DERATE
                rationale = "Moderate mechanical resistance detected; recommended derating drive torque/PWM by 30%."
            else:
                action = ACTION_RETRY_SAFE
                rationale = "Elevated current under soft jam; retry with pulsing declogging profile."
        else:  # HARD JAM
            action = ACTION_STOP
            rationale = "Severe rotor blockage or lockup detected! Immediate shutdown commanded to protect stator windings."

        return {
            "seq": seq,
            "model_version": self.model_version,
            "predicted_condition": predicted_condition,
            "confidence": round(confidence, 3),
            "recommended_action": action,
            "rationale": rationale,
            "timestamp": time.time(),
            "expiry_ms": SAFETY_LIMITS["COMMAND_EXPIRY_MS"]
        }

    def simulate_stm32_validation(
        self,
        recommendation: Dict[str, Any],
        live_telemetry_snapshot: Dict[str, float],
        link_healthy: bool = True
    ) -> Dict[str, Any]:
        """
        Simulates the embedded Cortex-M7 local safety boundary check on STM32.
        
        NOTE:
        In hardware mode, this exact logic executes in C on the STM32 NUCLEO-H753ZI.
        Here it acts as a high-fidelity software safety simulation.
        """
        rec_action = recommendation["recommended_action"]
        seq = recommendation["seq"]

        # 1. Check Watchdog & Link Heartbeat
        if not link_healthy:
            return {
                "seq": seq,
                "stm32_ack": "HEARTBEAT_TIMEOUT",
                "status": "REJECTED",
                "action_taken": "FALLBACK_SAFE_SHUTDOWN",
                "reason_code": "ERR_LINK_OFFLINE",
                "reason_description": "Laptop serial link timeout (>500ms). Embedded drive entered autonomous safe shutdown."
            }

        peak_curr = live_telemetry_snapshot.get("peak_current_amp", 0.0)
        temp = live_telemetry_snapshot.get("final_temp_celsius", 25.0)
        max_speed = live_telemetry_snapshot.get("max_speed_rpm", 0.0)

        # 2. Local Hardware Interlocks on STM32
        # Rule A: If current exceeds 15.0A, only STOP is permitted
        if peak_curr > SAFETY_LIMITS["MAX_CURRENT_AMP"] and rec_action != ACTION_STOP:
            return {
                "seq": seq,
                "stm32_ack": "LOCAL_OVERRIDE_STOP",
                "status": "REJECTED",
                "action_taken": ACTION_STOP,
                "reason_code": "ERR_OVERCURRENT_HARDWARE",
                "reason_description": f"Local hardware detected {peak_curr}A > limit {SAFETY_LIMITS['MAX_CURRENT_AMP']}A. Recommendation {rec_action} rejected."
            }

        # Rule B: If stator temp > 75C, ACCEPT_START is rejected
        if temp > SAFETY_LIMITS["MAX_TEMP_CELSIUS"] and rec_action == ACTION_ACCEPT_START:
            return {
                "seq": seq,
                "stm32_ack": "LOCAL_DERATE_OVERRIDE",
                "status": "REJECTED",
                "action_taken": ACTION_DERATE,
                "reason_code": "ERR_OVERTEMP_HARDWARE",
                "reason_description": f"Stator temp {temp}°C > max limit {SAFETY_LIMITS['MAX_TEMP_CELSIUS']}°C. ACCEPT rejected."
            }

        # Rule C: If ACCEPT_START is recommended but speed is below minimum threshold
        if rec_action == ACTION_ACCEPT_START and max_speed < SAFETY_LIMITS["MIN_SPEED_ACCEPT_RPM"]:
            return {
                "seq": seq,
                "stm32_ack": "LOCAL_RETRY_OVERRIDE",
                "status": "REJECTED",
                "action_taken": ACTION_RETRY_SAFE,
                "reason_code": "ERR_SPEED_NOT_REACHED",
                "reason_description": f"Motor only reached {max_speed} RPM (< {SAFETY_LIMITS['MIN_SPEED_ACCEPT_RPM']} RPM). ACCEPT rejected."
            }

        # Recommendation passed all local firmware checks!
        return {
            "seq": seq,
            "stm32_ack": "ACCEPTED",
            "status": "ACCEPTED",
            "action_taken": rec_action,
            "reason_code": "NONE_VALIDATED",
            "reason_description": f"Validated against STM32 local limits. Action '{rec_action}' confirmed."
        }

if __name__ == "__main__":
    print("Testing Safety Decision Engine in PyCharm...")
    engine = SafetyDecisionEngine()
    test_cases = [
        (CLASS_NORMAL, 0.95, {"peak_current_amp": 7.0, "final_temp_celsius": 26.0, "max_speed_rpm": 2900.0}),
        (CLASS_SOFT_JAM, 0.90, {"peak_current_amp": 11.5, "final_temp_celsius": 38.0, "max_speed_rpm": 1800.0}),
        (CLASS_HARD_JAM, 0.98, {"peak_current_amp": 19.5, "final_temp_celsius": 65.0, "max_speed_rpm": 150.0}),
        # Safety limit violation test: ML mistakenly recommends ACCEPT_START when current is 22A!
        ("UNSAFE_ATTEMPT", 0.90, {"peak_current_amp": 22.0, "final_temp_celsius": 82.0, "max_speed_rpm": 400.0})
    ]

    for cond, conf, snap in test_cases:
        if cond == "UNSAFE_ATTEMPT":
            rec = {"seq": 1099, "recommended_action": ACTION_ACCEPT_START}
        else:
            rec = engine.formulate_recommendation(cond, conf, snap)
        val = engine.simulate_stm32_validation(rec, snap)
        print(f"\nCondition: {cond}")
        print(f"  Recommended Action: {rec['recommended_action']}")
        print(f"  STM32 Local Verdict: {val['status']} -> Action: {val['action_taken']}")
        print(f"  Reason:             {val['reason_description']}")
    print("\nSafety validation test completed successfully!")

