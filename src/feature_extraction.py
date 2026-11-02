"""
StartSense - Feature Extraction Pipeline
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Extracts key temporal, kinematic, and electrical features from a 3.0s startup episode.
Every complete startup episode is treated as one independent sample.
"""

import sys
from pathlib import Path

# Add project root to path for PyCharm standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from typing import Dict, Any

FEATURE_NAMES = [
    "peak_current_amp",
    "avg_current_amp",
    "current_rise_rate_amps_per_sec",
    "startup_duration_sec",
    "time_to_target_speed_sec",
    "max_speed_rpm",
    "speed_rise_rate_rpm_per_sec",
    "final_temp_celsius",
    "temp_rise_celsius",
    "encoder_pulse_interval_mean_ms",
    "encoder_pulse_interval_std_ms",
    "load_proxy",
    "pwm_duty"
]

def extract_features_from_episode(telemetry_df: pd.DataFrame, meta: Dict[str, Any] = None) -> Dict[str, float]:
    """
    Extracts high-order engineering features from startup transient telemetry.
    """
    time = telemetry_df["time_sec"].values
    current = telemetry_df["current_sim_amp"].values
    speed = telemetry_df["speed_sim_rpm"].values
    temp = telemetry_df["temp_sim_celsius"].values
    pulses = telemetry_df["encoder_interval_ms"].values
    pwm = float(telemetry_df["pwm_duty"].iloc[0])

    meta = meta or {}
    load_proxy = float(meta.get("load_severity_proxy", 0.0))

    # 1. Electrical Current Features
    peak_current = float(np.max(current))
    avg_current = float(np.mean(current))

    # Current rise rate (measured across initial 80ms)
    idx_80ms = np.searchsorted(time, 0.08)
    if idx_80ms > 0:
        current_rise_rate = float((current[idx_80ms] - current[0]) / max(0.001, time[idx_80ms]))
    else:
        current_rise_rate = float(peak_current / 0.05)

    # 2. Kinematic & Speed Features
    max_speed = float(np.max(speed))
    
    # Startup duration: Time taken to reach 80% of max speed or end if stalled
    target_80pct = 0.8 * max_speed
    if target_80pct > 200.0:
        reach_indices = np.where(speed >= target_80pct)[0]
        startup_duration = float(time[reach_indices[0]]) if len(reach_indices) > 0 else float(time[-1])
    else:
        # Motor failed to accelerate significantly (Hard Jam stall)
        startup_duration = float(time[-1])

    # Time to reach target speed (nominal 2000 RPM)
    nominal_target_rpm = 2000.0
    reach_target_idx = np.where(speed >= nominal_target_rpm)[0]
    if len(reach_target_idx) > 0:
        time_to_target = float(time[reach_target_idx[0]])
    else:
        time_to_target = float(time[-1])  # Capped at episode max duration if never reached

    # Speed rise rate (acceleration) from 0 to 0.4s
    idx_400ms = np.searchsorted(time, 0.4)
    if idx_400ms > 0:
        speed_rise_rate = float((speed[idx_400ms] - speed[0]) / max(0.001, time[idx_400ms]))
    else:
        speed_rise_rate = float(max_speed / 0.5)

    # 3. Thermal Features
    final_temp = float(temp[-1])
    temp_rise = float(temp[-1] - temp[0])

    # 4. Encoder Pulse Interval Statistics (post initial transient)
    # Exclude initial standstill if any
    steady_pulses = pulses[int(len(pulses) * 0.2):]
    encoder_mean = float(np.mean(steady_pulses))
    encoder_std = float(np.std(steady_pulses))

    return {
        "peak_current_amp": round(peak_current, 3),
        "avg_current_amp": round(avg_current, 3),
        "current_rise_rate_amps_per_sec": round(current_rise_rate, 2),
        "startup_duration_sec": round(startup_duration, 3),
        "time_to_target_speed_sec": round(time_to_target, 3),
        "max_speed_rpm": round(max_speed, 1),
        "speed_rise_rate_rpm_per_sec": round(speed_rise_rate, 1),
        "final_temp_celsius": round(final_temp, 2),
        "temp_rise_celsius": round(temp_rise, 2),
        "encoder_pulse_interval_mean_ms": round(encoder_mean, 2),
        "encoder_pulse_interval_std_ms": round(encoder_std, 2),
        "load_proxy": round(load_proxy, 3),
        "pwm_duty": round(pwm, 1)
    }

if __name__ == "__main__":
    from src.simulator import MotorStartupSimulator
    print("Testing Feature Extraction Pipeline in PyCharm...")
    sim = MotorStartupSimulator()
    df_test, meta = sim.simulate_episode()
    feats = extract_features_from_episode(df_test, meta)
    print("\nExtracted Feature Vector:")
    for k, v in feats.items():
        print(f"  {k:35s}: {v}")
    print("\nFeature extraction test completed successfully!")

