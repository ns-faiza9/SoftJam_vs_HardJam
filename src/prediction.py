"""
StartSense - Model Inference & Confidence Engine
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
from typing import Dict, Any, Tuple
from src.config import (
    MODELS_DIR, CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM, CLASSES
)
from src.feature_extraction import FEATURE_NAMES

class MotorConditionPredictor:
    def __init__(self, model_name: str = "random_forest"):
        self.model_name = model_name
        self.model = None
        self.load_model(model_name)

    def load_model(self, model_name: str = "random_forest"):
        self.model_name = model_name
        model_path = MODELS_DIR / f"{model_name}.joblib"
        if not model_path.exists():
            # Trigger training if models don't exist yet
            from src.model_training import train_and_compare_models
            train_and_compare_models()
        self.model = joblib.load(model_path)

    def predict(self, features: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        """
        Runs ML prediction given a feature dictionary.
        
        Returns:
            (predicted_class, confidence_score, probabilities_dict)
        """
        # Vectorize feature vector in exact training order
        feature_vector = np.array([[features[name] for name in FEATURE_NAMES]])

        pred_class = self.model.predict(feature_vector)[0]
        
        # Get probability distribution
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(feature_vector)[0]
            classes = list(self.model.classes_)
            prob_dict = {cls_name: float(probs[classes.index(cls_name)]) if cls_name in classes else 0.0 for cls_name in CLASSES}
            confidence = float(np.max(probs))
        else:
            confidence = 0.95
            prob_dict = {cls: 1.0 if cls == pred_class else 0.0 for cls in CLASSES}

        return str(pred_class), float(confidence), prob_dict

if __name__ == "__main__":
    from src.simulator import MotorStartupSimulator
    from src.feature_extraction import extract_features_from_episode

    print("Testing ML Condition Predictor in PyCharm...")
    predictor = MotorConditionPredictor(model_name="random_forest")
    sim = MotorStartupSimulator()

    for target in [CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM]:
        df_sim, meta = sim.simulate_episode(condition=target)
        feats = extract_features_from_episode(df_sim, meta)
        pred_cls, conf, probs = predictor.predict(feats)
        print(f"\nGround Truth Target: {target}")
        print(f"  ML Predicted Class: {pred_cls}")
        print(f"  Confidence:         {conf*100:.2f}%")
        print(f"  Class Probabilities:{probs}")
    print("\nPredictor test completed successfully!")

