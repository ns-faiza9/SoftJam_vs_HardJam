"""
StartSense - Synthetic Dataset Generator
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Generates batches of independent startup episodes with natural physics variation
and extracts dataset features for ML model training.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    GENERATED_DATA_DIR
)
from src.simulator import MotorStartupSimulator
from src.feature_extraction import extract_features_from_episode, FEATURE_NAMES

def generate_startup_dataset(
    n_samples_per_class: int = 50,
    random_seed: int = 42,
    save_csv: bool = True
) -> pd.DataFrame:
    """
    Generates a balanced dataset of independent startup runs.
    Each row represents one full 3.0s startup episode.
    """
    np.random.seed(random_seed)
    simulator = MotorStartupSimulator()
    records = []
    
    classes = [CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM]
    run_idx = 1

    for cond in classes:
        for i in range(n_samples_per_class):
            # Vary initial condition & noise
            pwm = float(np.random.choice([80.0, 90.0, 100.0], p=[0.2, 0.3, 0.5]))
            ambient_temp = float(np.random.uniform(20.0, 32.0))
            noise = float(np.random.uniform(0.02, 0.08))
            direction = "FORWARD" if np.random.rand() > 0.1 else "REVERSE"

            # Vary load severity within class boundaries
            if cond == CLASS_NORMAL:
                load = float(np.random.uniform(0.02, 0.28))
            elif cond == CLASS_SOFT_JAM:
                load = float(np.random.uniform(0.42, 0.72))
            else:  # HARD JAM
                load = float(np.random.uniform(0.82, 1.00))

            telemetry_df, meta = simulator.simulate_episode(
                condition=cond,
                load_severity=load,
                pwm_duty=pwm,
                direction=direction,
                ambient_temp=ambient_temp,
                noise_level=noise,
                duration_sec=3.0,
                sample_rate_hz=150,
                seed=random_seed + run_idx
            )

            feats = extract_features_from_episode(telemetry_df, meta)
            feats["run_id"] = f"RUN_{run_idx:04d}"
            feats["target_condition"] = cond
            records.append(feats)
            run_idx += 1

    dataset_df = pd.DataFrame(records)

    # Reorder columns with run_id and target_condition first
    cols = ["run_id", "target_condition"] + [c for c in dataset_df.columns if c not in ["run_id", "target_condition"]]
    dataset_df = dataset_df[cols]

    if save_csv:
        output_path = GENERATED_DATA_DIR / "startup_episodes_dataset.csv"
        dataset_df.to_csv(output_path, index=False)
        print(f"Dataset generated with {len(dataset_df)} episodes and saved to {output_path}")

    return dataset_df

if __name__ == "__main__":
    generate_startup_dataset(n_samples_per_class=60)
