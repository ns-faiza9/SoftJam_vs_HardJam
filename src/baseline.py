"""
StartSense - Rule-Based Engineering Baseline Detection
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Provides a traditional static thresholding baseline to evaluate against ML algorithms.
"""

import sys
from pathlib import Path

# Add project root to path for PyCharm standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any, Tuple
from src.config import CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM, SAFETY_LIMITS

class RuleBasedBaselineDetector:
    def __init__(self):
        self.hard_current_thresh = 14.2
        self.soft_current_thresh = 9.2
        self.hard_speed_floor_rpm = 600.0
        self.soft_speed_ceiling_rpm = 2300.0

    def predict(self, features: Dict[str, float]) -> Tuple[str, float, str]:
        """
        Classifies startup based on deterministic threshold rules.
        
        Returns:
            (predicted_class, confidence, rule_reason)
        """
        peak_curr = features["peak_current_amp"]
        max_spd = features["max_speed_rpm"]
        time_to_target = features["time_to_target_speed_sec"]
        temp_rise = features["temp_rise_celsius"]

        # Hard Jam condition: Locked rotor, severe current, or failure to escape stall
        if peak_curr >= self.hard_current_thresh or max_spd < self.hard_speed_floor_rpm or (time_to_target >= 2.8 and max_spd < 1000.0):
            conf = 0.90 if peak_curr >= 15.0 or max_spd < 300.0 else 0.75
            return CLASS_HARD_JAM, conf, f"Rule: Peak I ({peak_curr}A) >= {self.hard_current_thresh}A or Max Speed ({max_spd} RPM) < {self.hard_speed_floor_rpm}"

        # Soft Jam condition: Elevated current or sluggish acceleration
        if peak_curr >= self.soft_current_thresh or max_spd < self.soft_speed_ceiling_rpm or time_to_target > 1.2:
            conf = 0.82
            return CLASS_SOFT_JAM, conf, f"Rule: Peak I ({peak_curr}A) in [{self.soft_current_thresh}-{self.hard_current_thresh}] or Speed ({max_spd} RPM) < {self.soft_speed_ceiling_rpm}"

        # Normal condition
        return CLASS_NORMAL, 0.88, f"Rule: Nominal current ({peak_curr}A) and healthy acceleration ({max_spd} RPM)"

if __name__ == "__main__":
    print("Testing Baseline Detector in PyCharm...")
    detector = RuleBasedBaselineDetector()
    samples = [
        {"peak_current_amp": 7.5, "max_speed_rpm": 2900, "time_to_target_speed_sec": 0.35, "temp_rise_celsius": 1.2},
        {"peak_current_amp": 12.0, "max_speed_rpm": 1800, "time_to_target_speed_sec": 1.8, "temp_rise_celsius": 4.5},
        {"peak_current_amp": 18.5, "max_speed_rpm": 120, "time_to_target_speed_sec": 3.0, "temp_rise_celsius": 14.0}
    ]
    for s in samples:
        cls, conf, reason = detector.predict(s)
        print(f"\nInputs: {s}")
        print(f"  -> Prediction: {cls} (conf: {conf})")
        print(f"  -> Reason:     {reason}")
    print("\nBaseline test completed successfully!")

