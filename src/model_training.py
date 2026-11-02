"""
StartSense - Machine Learning Model Training & Evaluation
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter

Algorithms:
1. Decision Tree Classifier
2. Random Forest Classifier

Features independent run splits (strictly zero data leakage) and computes
comprehensive industrial metrics: accuracy, macro F1, per-class metrics,
hard-jam recall, false-alarm rate, and confusion matrix.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

from src.config import (
    MODELS_DIR, GENERATED_DATA_DIR,
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM, CLASSES
)
from src.feature_extraction import FEATURE_NAMES
from src.data_generator import generate_startup_dataset

def load_or_create_dataset() -> pd.DataFrame:
    csv_path = GENERATED_DATA_DIR / "startup_episodes_dataset.csv"
    if not csv_path.exists():
        return generate_startup_dataset(n_samples_per_class=60, save_csv=True)
    return pd.read_csv(csv_path)

def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list = CLASSES
) -> Dict[str, Any]:
    """
    Computes rigorous metrics including hard-jam recall and false-alarm rate.
    """
    acc = float(accuracy_score(y_true, y_pred))
    macro_prec = float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))

    # Per-class metrics
    per_class_rec = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    per_class_prec = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)

    per_class_dict = {}
    for idx, name in enumerate(labels):
        per_class_dict[name] = {
            "precision": float(per_class_prec[idx]),
            "recall": float(per_class_rec[idx]),
            "f1": float(per_class_f1[idx])
        }

    # Safety-critical metric: Hard-Jam Recall
    hard_jam_idx = labels.index(CLASS_HARD_JAM)
    hard_jam_recall = float(per_class_rec[hard_jam_idx])

    # False-Alarm Rate: Normal motors incorrectly flagged as Soft or Hard Jam
    normal_mask = (y_true == CLASS_NORMAL)
    if np.sum(normal_mask) > 0:
        false_alarms = np.sum((y_pred != CLASS_NORMAL) & normal_mask)
        false_alarm_rate = float(false_alarms / np.sum(normal_mask))
    else:
        false_alarm_rate = 0.0

    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    return {
        "accuracy": acc,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "hard_jam_recall": hard_jam_recall,
        "false_alarm_rate": false_alarm_rate,
        "per_class": per_class_dict,
        "confusion_matrix": cm,
        "labels": labels
    }

def train_and_compare_models(test_size: float = 0.25, random_seed: int = 42) -> Dict[str, Any]:
    """
    Trains Decision Tree and Random Forest models on independent runs.
    Saves trained models and returns full evaluation comparison.
    """
    df = load_or_create_dataset()

    X = df[FEATURE_NAMES].to_numpy()
    y = np.array(df["target_condition"].values)

    # Independent run split (no data leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_seed, stratify=y
    )

    # 1. Decision Tree Classifier
    dt = DecisionTreeClassifier(
        max_depth=5,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=random_seed
    )
    dt.fit(X_train, y_train)
    y_pred_dt = dt.predict(X_test)
    dt_metrics = evaluate_classifier(y_test, y_pred_dt)
    dt_metrics["feature_importances"] = dict(zip(FEATURE_NAMES, dt.feature_importances_.round(4).tolist()))

    # 2. Random Forest Classifier
    rf = RandomForestClassifier(
        n_estimators=60,
        max_depth=6,
        min_samples_split=3,
        random_state=random_seed
    )
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    rf_metrics = evaluate_classifier(y_test, y_pred_rf)
    rf_metrics["feature_importances"] = dict(zip(FEATURE_NAMES, rf.feature_importances_.round(4).tolist()))

    # Save models
    joblib.dump(dt, MODELS_DIR / "decision_tree.joblib")
    joblib.dump(rf, MODELS_DIR / "random_forest.joblib")

    results = {
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_names": FEATURE_NAMES,
        "decision_tree": dt_metrics,
        "random_forest": rf_metrics
    }

    joblib.dump(results, MODELS_DIR / "training_metrics.joblib")
    print("Models successfully trained and saved!")
    return results

if __name__ == "__main__":
    train_and_compare_models()
