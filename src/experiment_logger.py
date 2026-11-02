"""
StartSense - Experiment Logger & Persistent Database
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Stores every complete startup episode in SQLite with CSV export and fallback.
Every startup episode is treated as an independent sample.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import json
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from src.config import (
    DB_PATH, CSV_FALLBACK_PATH, VARIANT_ID,
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP
)

class ExperimentLogger:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes SQLite tables if they do not exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id TEXT NOT NULL,
                condition_id TEXT NOT NULL,
                run_id TEXT UNIQUE NOT NULL,
                operator_set_severity REAL,
                target_condition TEXT,
                calibration_version TEXT,
                peak_current REAL,
                max_speed REAL,
                startup_duration REAL,
                temp_rise REAL,
                baseline_result TEXT,
                ml_prediction TEXT,
                confidence REAL,
                recommended_action TEXT,
                stm32_acknowledgement TEXT,
                features_json TEXT,
                telemetry_json TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
        self._seed_initial_records_if_empty()

    def _seed_initial_records_if_empty(self):
        """Pre-populates the database with 15 initial experiments if empty for immediate demo value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiment_runs")
        count = cursor.fetchone()[0]
        conn.close()

        if count == 0:
            from src.simulator import MotorStartupSimulator
            from src.feature_extraction import extract_features_from_episode
            from src.baseline import RuleBasedBaselineDetector
            from src.prediction import MotorConditionPredictor
            from src.safety_validation import SafetyDecisionEngine

            sim = MotorStartupSimulator()
            baseline = RuleBasedBaselineDetector()
            predictor = MotorConditionPredictor()
            safety = SafetyDecisionEngine()

            demo_runs = [
                (CLASS_NORMAL, 0.10, "NORMAL"),
                (CLASS_NORMAL, 0.15, "NORMAL"),
                (CLASS_NORMAL, 0.08, "NORMAL"),
                (CLASS_NORMAL, 0.20, "NORMAL"),
                (CLASS_NORMAL, 0.12, "NORMAL"),
                (CLASS_SOFT_JAM, 0.50, "SOFT JAM"),
                (CLASS_SOFT_JAM, 0.58, "SOFT JAM"),
                (CLASS_SOFT_JAM, 0.45, "SOFT JAM"),
                (CLASS_SOFT_JAM, 0.62, "SOFT JAM"),
                (CLASS_SOFT_JAM, 0.52, "SOFT JAM"),
                (CLASS_HARD_JAM, 0.90, "HARD JAM"),
                (CLASS_HARD_JAM, 0.95, "HARD JAM"),
                (CLASS_HARD_JAM, 0.88, "HARD JAM"),
                (CLASS_HARD_JAM, 1.00, "HARD JAM"),
                (CLASS_HARD_JAM, 0.92, "HARD JAM")
            ]

            for idx, (cond, load, target) in enumerate(demo_runs):
                df_telemetry, meta = sim.simulate_episode(
                    condition=cond, load_severity=load, seed=100 + idx
                )
                feats = extract_features_from_episode(df_telemetry, meta)
                base_pred, _, _ = baseline.predict(feats)
                ml_pred, conf, _ = predictor.predict(feats)
                rec = safety.formulate_recommendation(ml_pred, conf, feats)
                ack = safety.simulate_stm32_validation(rec, feats)

                self.log_experiment(
                    run_id=f"INIT_RUN_{idx+1:03d}",
                    condition_id=f"COND_{cond.replace(' ', '_')}_{idx+1}",
                    operator_set_severity=load,
                    target_condition=target,
                    calibration_version="Calib_v1.0.4",
                    telemetry_df=df_telemetry,
                    features=feats,
                    baseline_result=base_pred,
                    ml_prediction=ml_pred,
                    confidence=conf,
                    recommended_action=rec["recommended_action"],
                    stm32_acknowledgement=ack["stm32_ack"],
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - (15 - idx) * 300))
                )

    def log_experiment(
        self,
        run_id: str,
        condition_id: str,
        operator_set_severity: float,
        target_condition: str,
        calibration_version: str,
        telemetry_df: pd.DataFrame,
        features: Dict[str, float],
        baseline_result: str,
        ml_prediction: str,
        confidence: float,
        recommended_action: str,
        stm32_acknowledgement: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Stores a completed startup run into SQLite."""
        if timestamp is None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Downsample telemetry for compact storage in database
        telemetry_sample = telemetry_df.iloc[::2].to_dict(orient="records")
        telemetry_json = json.dumps(telemetry_sample)
        features_json = json.dumps(features)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO experiment_runs (
                variant_id, condition_id, run_id, operator_set_severity,
                target_condition, calibration_version, peak_current, max_speed,
                startup_duration, temp_rise, baseline_result, ml_prediction,
                confidence, recommended_action, stm32_acknowledgement,
                features_json, telemetry_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            VARIANT_ID, condition_id, run_id, operator_set_severity,
            target_condition, calibration_version,
            features.get("peak_current_amp", 0.0),
            features.get("max_speed_rpm", 0.0),
            features.get("startup_duration_sec", 0.0),
            features.get("temp_rise_celsius", 0.0),
            baseline_result, ml_prediction, round(confidence, 3),
            recommended_action, stm32_acknowledgement,
            features_json, telemetry_json, timestamp
        ))
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def get_experiments(
        self,
        condition_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> pd.DataFrame:
        """Queries stored experiments with filtering."""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM experiment_runs WHERE 1=1"
        params = []

        if condition_filter and condition_filter != "ALL":
            query += " AND (ml_prediction = ? OR target_condition = ?)"
            params.extend([condition_filter, condition_filter])

        if search_query:
            query += " AND (run_id LIKE ? OR condition_id LIKE ? OR recommended_action LIKE ?)"
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard])

        query += " ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_summary_counts(self) -> Dict[str, int]:
        """Returns total counts per condition."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ml_prediction, COUNT(*) FROM experiment_runs GROUP BY ml_prediction")
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM experiment_runs")
        total = cursor.fetchone()[0]
        conn.close()

        counts = {CLASS_NORMAL: 0, CLASS_SOFT_JAM: 0, CLASS_HARD_JAM: 0, "TOTAL": total}
        for pred, cnt in rows:
            if pred in counts:
                counts[pred] = cnt
        return counts

    def get_episode_telemetry(self, run_id: str) -> Optional[pd.DataFrame]:
        """Retrieves raw telemetry dataframe for a specific run."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT telemetry_json FROM experiment_runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            data = json.loads(row[0])
            return pd.DataFrame(data)
        return None

    def export_csv(self) -> str:
        """Exports all experiments to CSV format."""
        df = self.get_experiments()
        # Drop heavy json column for export
        export_df = df.drop(columns=["telemetry_json", "features_json"], errors="ignore")
        return export_df.to_csv(index=False)

if __name__ == "__main__":
    print("Testing Experiment Logger (SQLite) in PyCharm...")
    logger = ExperimentLogger()
    counts = logger.get_summary_counts()
    print(f"\nDatabase Summary Counts: {counts}")
    recent = logger.get_experiments().head(5)
    print("\nRecent 5 Recorded Startup Runs:")
    print(recent[["run_id", "condition_id", "ml_prediction", "confidence", "recommended_action", "timestamp"]])
    print("\nExperiment logger test completed successfully!")

