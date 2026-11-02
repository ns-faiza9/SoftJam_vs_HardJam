"""
StartSense - Flask Web Application
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
Platform: STM32 NUCLEO-H753ZI + Python Flask

Run directly in PyCharm:
    Right-click app.py -> Run 'app'
    Access at http://127.0.0.1:5000
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
import joblib
import pandas as pd
from flask import Flask, render_template, request, jsonify, Response

from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM,
    ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP,
    MODELS_DIR, GENERATED_DATA_DIR, SAFETY_LIMITS
)
from src.serial_communication import get_serial_interface
from src.simulator import MotorStartupSimulator
from src.feature_extraction import extract_features_from_episode, FEATURE_NAMES
from src.baseline import RuleBasedBaselineDetector
from src.prediction import MotorConditionPredictor
from src.safety_validation import SafetyDecisionEngine
from src.experiment_logger import ExperimentLogger
from src.model_training import train_and_compare_models, load_or_create_dataset

app = Flask(__name__)
serial_if = get_serial_interface()
logger = ExperimentLogger()
sim = MotorStartupSimulator()
baseline = RuleBasedBaselineDetector()
predictor = MotorConditionPredictor()
safety = SafetyDecisionEngine()

def get_base_context():
    """Provides common context data for layout sidebar."""
    ports = serial_if.get_available_ports()
    pot = serial_if.get_potentiometer_reading()
    is_hw = not serial_if.is_mock_mode and serial_if.is_connected
    return {
        "serial_ports": ports,
        "pot": pot,
        "is_hw": is_hw,
        "is_connected": serial_if.is_connected,
        "is_mock_mode": serial_if.is_mock_mode,
        "port": serial_if.port
    }

# --- PAGE ROUTES ---

@app.route("/")
def page_overview():
    ctx = get_base_context()
    ctx["active_page"] = "overview"
    counts = logger.get_summary_counts()
    all_runs = logger.get_experiments().to_dict(orient="records")
    latest = all_runs[0] if all_runs else None

    cond = latest["ml_prediction"] if latest else CLASS_NORMAL
    conf = latest["confidence"] if latest else 0.98
    action = latest["recommended_action"] if latest else ACTION_ACCEPT_START
    ack = latest["stm32_acknowledgement"] if latest else "ACCEPTED"

    # Load ML metrics
    metrics_path = MODELS_DIR / "training_metrics.joblib"
    if not metrics_path.exists():
        metrics = train_and_compare_models()
    else:
        metrics = joblib.load(metrics_path)

    # Initial simulated waveform
    df_init, _ = sim.simulate_episode(condition=cond, load_severity=ctx["pot"]["normalized"])

    ctx.update({
        "counts": counts,
        "runs": all_runs,
        "latest": latest,
        "current_condition": cond,
        "confidence": conf,
        "rec_action": action,
        "stm32_ack": ack,
        "rf": metrics["random_forest"],
        "dt": metrics["decision_tree"],
        "telemetry_json": json.dumps(df_init.to_dict(orient="list"))
    })
    return render_template("index.html", **ctx)

@app.route("/monitoring")
def page_monitoring():
    ctx = get_base_context()
    ctx["active_page"] = "monitoring"
    preset = request.args.get("preset", "NORMAL")
    pwm = float(request.args.get("pwm", 100.0))

    if preset == "NORMAL":
        cond = CLASS_NORMAL
        load = None
    elif preset == "SOFT JAM":
        cond = CLASS_SOFT_JAM
        load = None
    elif preset == "HARD JAM":
        cond = CLASS_HARD_JAM
        load = None
    else:
        load = ctx["pot"]["normalized"]
        cond = CLASS_HARD_JAM if load > 0.8 else (CLASS_SOFT_JAM if load > 0.35 else CLASS_NORMAL)

    df_telemetry, _ = sim.simulate_episode(condition=cond, load_severity=load, pwm_duty=pwm)
    ctx.update({
        "preset": preset,
        "pwm": int(pwm),
        "peak_current": round(df_telemetry["current_sim_amp"].max(), 2),
        "max_speed": int(df_telemetry["speed_sim_rpm"].max()),
        "final_temp": round(df_telemetry["temp_sim_celsius"].iloc[-1], 1),
        "pulse_interval": round(df_telemetry["encoder_interval_ms"].iloc[-1], 1),
        "telemetry_json": json.dumps(df_telemetry.to_dict(orient="list"))
    })
    return render_template("live_monitoring.html", **ctx)

@app.route("/simulation")
def page_simulation():
    ctx = get_base_context()
    ctx["active_page"] = "simulation"
    return render_template("simulation.html", **ctx)

@app.route("/ml")
def page_ml():
    ctx = get_base_context()
    ctx["active_page"] = "ml"
    metrics_path = MODELS_DIR / "training_metrics.joblib"
    if not metrics_path.exists():
        metrics = train_and_compare_models()
    else:
        metrics = joblib.load(metrics_path)

    df_dataset = load_or_create_dataset()
    ctx.update({
        "rf": metrics["random_forest"],
        "dt": metrics["decision_tree"],
        "dataset_size": len(df_dataset),
        "dataset_preview": df_dataset.head(20).to_dict(orient="records"),
        "dataset_cols": ["run_id", "target_condition", "peak_current_amp", "max_speed_rpm", "startup_duration_sec", "temp_rise_celsius", "load_proxy"]
    })
    return render_template("ml_intelligence.html", **ctx)

@app.route("/safety")
def page_safety():
    ctx = get_base_context()
    ctx["active_page"] = "safety"
    return render_template("safety_center.html", **ctx)

@app.route("/history")
def page_history():
    ctx = get_base_context()
    ctx["active_page"] = "history"
    runs = logger.get_experiments().to_dict(orient="records")
    ctx["runs"] = runs
    return render_template("experiment_history.html", **ctx)

@app.route("/architecture")
def page_architecture():
    ctx = get_base_context()
    ctx["active_page"] = "architecture"
    ctx["logs"] = serial_if.get_logs()
    return render_template("architecture.html", **ctx)

# --- REST API ENDPOINTS ---

@app.route("/api/live_stream")
def api_live_stream():
    """Provides high-frequency live feed for PuTTY-like terminal and live ADC meters."""
    pot = serial_if.get_potentiometer_reading()
    norm = pot["normalized"]
    if norm < 0.35:
        zone = "NORMAL (Free / Nominal Load)"
        zone_color = "#00E676"
    elif norm < 0.78:
        zone = "SOFT JAM (Friction / Binding)"
        zone_color = "#FFB300"
    else:
        zone = "HARD JAM (Locked Rotor / Stall)"
        zone_color = "#FF3D00"

    return jsonify({
        "adc": pot["adc_raw"],
        "voltage": pot["voltage"],
        "normalized": norm,
        "percentage": round(norm * 100, 1),
        "zone": zone,
        "zone_color": zone_color,
        "source": pot.get("source", "MOCK"),
        "is_connected": serial_if.is_connected,
        "is_mock_mode": serial_if.is_mock_mode,
        "port": serial_if.port,
        "terminal_lines": serial_if.get_raw_terminal_lines()
    })

@app.route("/api/status")
def api_status():
    pot = serial_if.get_potentiometer_reading()
    link_info = {
        "is_connected": serial_if.is_connected,
        "is_mock_mode": serial_if.is_mock_mode,
        "port": serial_if.port
    }
    return jsonify({"pot": pot, "link": link_info})

@app.route("/api/mock_pot", methods=["POST"])
def api_mock_pot():
    data = request.get_json() or {}
    adc = int(data.get("adc", 1024))
    serial_if.set_mock_potentiometer(adc)
    return jsonify({"status": "OK", "pot": serial_if.get_potentiometer_reading()})

@app.route("/api/serial/connect", methods=["POST"])
def api_serial_connect():
    data = request.get_json() or {}
    port = data.get("port", "MOCK")
    baud = int(data.get("baudrate", 115200))
    success = serial_if.connect(port, baud)
    recent_logs = serial_if.get_logs()
    last_msg = recent_logs[0]["msg"] if recent_logs else ""
    return jsonify({
        "status": "OK" if success else "FALLBACK_MOCK",
        "is_connected": serial_if.is_connected,
        "is_mock_mode": serial_if.is_mock_mode,
        "port": serial_if.port,
        "message": last_msg
    })

@app.route("/api/serial/disconnect", methods=["POST"])
def api_serial_disconnect():
    serial_if.disconnect()
    return jsonify({
        "status": "DISCONNECTED",
        "is_connected": False,
        "is_mock_mode": True,
        "port": "MOCK"
    })

@app.route("/api/telemetry")
def api_telemetry():
    cond_param = request.args.get("condition", "NORMAL")
    pwm = float(request.args.get("pwm", 100.0))
    dir_val = request.args.get("dir", "FORWARD")

    pot = serial_if.get_potentiometer_reading()
    if cond_param == "NORMAL":
        cond = CLASS_NORMAL
        load = None
    elif cond_param == "SOFT JAM":
        cond = CLASS_SOFT_JAM
        load = None
    elif cond_param == "HARD JAM":
        cond = CLASS_HARD_JAM
        load = None
    else:
        load = pot["normalized"]
        cond = CLASS_HARD_JAM if load > 0.8 else (CLASS_SOFT_JAM if load > 0.35 else CLASS_NORMAL)

    df_tel, meta = sim.simulate_episode(condition=cond, load_severity=load, pwm_duty=pwm, direction=dir_val)
    return jsonify({
        "telemetry": df_tel.to_dict(orient="list"),
        "peak_curr": round(df_tel["current_sim_amp"].max(), 2),
        "max_spd": int(df_tel["speed_sim_rpm"].max()),
        "final_temp": round(df_tel["temp_sim_celsius"].iloc[-1], 1),
        "pulse": round(df_tel["encoder_interval_ms"].iloc[-1], 1)
    })

@app.route("/api/live_waveform")
def api_live_waveform():
    """Generates real-time motor transient telemetry dynamically matching current potentiometer position."""
    adc_param = request.args.get("adc")
    pot = serial_if.get_potentiometer_reading()
    if adc_param is not None:
        try:
            adc_val = int(adc_param)
            load = max(0.0, min(1.0, adc_val / 4095.0))
        except ValueError:
            load = pot["normalized"]
    else:
        load = pot["normalized"]

    if load < 0.35:
        target = CLASS_NORMAL
    elif load < 0.78:
        target = CLASS_SOFT_JAM
    else:
        target = CLASS_HARD_JAM

    df_tel, meta = sim.simulate_episode(
        condition=target,
        load_severity=load,
        pwm_duty=100.0,
        direction="FORWARD",
        ambient_temp=25.0,
        noise_level=0.04
    )

    feats = extract_features_from_episode(df_tel, meta)
    ml_pred, ml_conf, _ = predictor.predict(feats)
    rec = safety.formulate_recommendation(ml_pred, ml_conf, feats)
    ack_resp = serial_if.send_recommendation(rec)
    ack_str = f"{ack_resp.get('status', 'ACCEPTED')} ({ack_resp.get('reason', 'NONE_VALIDATED')})"

    # Downsample to 100 points for super-fast HTTP transfer
    df_sample = df_tel.iloc[::3]

    return jsonify({
        "ml_pred": ml_pred,
        "ml_conf": ml_conf,
        "recommended_action": rec["recommended_action"],
        "stm32_ack": ack_str,
        "features": {
            "peak_current_amp": feats["peak_current_amp"],
            "max_speed_rpm": feats["max_speed_rpm"],
            "temp_rise_celsius": feats["temp_rise_celsius"],
            "load_proxy": feats["load_proxy"]
        },
        "telemetry": df_sample.to_dict(orient="list")
    })

@app.route("/api/run_test", methods=["POST"])
def api_run_test():
    data = request.get_json() or {}
    mode = data.get("mode", "NORMAL")
    custom_load = float(data.get("load", 0.15))
    pwm = float(data.get("pwm", 100.0))
    direction = data.get("direction", "FORWARD")
    temp = float(data.get("ambient_temp", 25.0))
    noise = float(data.get("noise", 0.05))

    pot = serial_if.get_potentiometer_reading()
    if mode == "NORMAL":
        target = CLASS_NORMAL
        load_val = None
    elif mode == "SOFT JAM":
        target = CLASS_SOFT_JAM
        load_val = None
    elif mode == "HARD JAM":
        target = CLASS_HARD_JAM
        load_val = None
    else:  # POT
        load_val = pot["normalized"]
        target = CLASS_HARD_JAM if load_val > 0.8 else (CLASS_SOFT_JAM if load_val > 0.35 else CLASS_NORMAL)

    df_tel, meta = sim.simulate_episode(
        condition=target,
        load_severity=load_val if load_val is not None else custom_load,
        pwm_duty=pwm,
        direction=direction,
        ambient_temp=temp,
        noise_level=noise
    )

    feats = extract_features_from_episode(df_tel, meta)
    base_pred, base_conf, base_reason = baseline.predict(feats)
    ml_pred, ml_conf, ml_probs = predictor.predict(feats)
    rec = safety.formulate_recommendation(ml_pred, ml_conf, feats)
    ack_resp = serial_if.send_recommendation(rec)

    run_id = f"RUN_{int(time.time()) % 100000:05d}"
    ack_str = f"{ack_resp.get('status', 'ACCEPTED')} ({ack_resp.get('reason', 'NONE_VALIDATED')})"

    logger.log_experiment(
        run_id=run_id,
        condition_id=f"COND_{target.replace(' ', '_')}",
        operator_set_severity=feats["load_proxy"],
        target_condition=target,
        calibration_version="Calib_v1.0.4",
        telemetry_df=df_tel,
        features=feats,
        baseline_result=base_pred,
        ml_prediction=ml_pred,
        confidence=ml_conf,
        recommended_action=rec["recommended_action"],
        stm32_acknowledgement=ack_str
    )

    return jsonify({
        "run_id": run_id,
        "target_condition": target,
        "ml_pred": ml_pred,
        "ml_conf": ml_conf,
        "recommended_action": rec["recommended_action"],
        "stm32_ack": ack_str,
        "baseline_pred": base_pred,
        "baseline_reason": base_reason,
        "features": feats,
        "telemetry": df_tel.to_dict(orient="list")
    })

@app.route("/api/safety_test", methods=["POST"])
def api_safety_test():
    data = request.get_json() or {}
    action = data.get("action", "ACCEPT_START")
    current = float(data.get("peak_current", 8.5))
    temp = float(data.get("temp", 32.0))
    speed = float(data.get("speed", 2400.0))
    link = bool(data.get("link_healthy", True))

    rec = {"seq": 1050, "recommended_action": action, "confidence": 0.95}
    snap = {"peak_current_amp": current, "final_temp_celsius": temp, "max_speed_rpm": speed}
    val = safety.simulate_stm32_validation(rec, snap, link_healthy=link)
    return jsonify(val)

@app.route("/api/retrain", methods=["POST"])
def api_retrain():
    import numpy as np
    results = train_and_compare_models(random_seed=int(np.random.randint(1, 1000)))
    return jsonify({"status": "SUCCESS", "metrics": results})

@app.route("/api/export_csv")
def api_export_csv():
    """Exports real-time ADC samples + ML inference stream captured during the last 10 seconds."""
    csv_str = serial_if.get_recent_stream_csv(duration_sec=10.0)
    ts_file = time.strftime("%Y%m%d_%H%M%S")
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=startsense_realtime_10sec_{ts_file}.csv"}
    )

@app.route("/api/episode_telemetry")
def api_episode_telemetry():
    run_id = request.args.get("run_id", "")
    df_tel = logger.get_episode_telemetry(run_id)
    df_runs = logger.get_experiments()
    meta_row = df_runs[df_runs["run_id"] == run_id].iloc[0].to_dict() if not df_runs[df_runs["run_id"] == run_id].empty else {}
    return jsonify({
        "telemetry": df_tel.to_dict(orient="records") if df_tel is not None else [],
        "meta": meta_row
    })

if __name__ == "__main__":
    print("=" * 70)
    print("⚡ StartSense – Startup Signature Intelligence for Electric Drives (Flask)")
    print("   Variant: 02.08 – Soft-Jam vs Hard-Jam Starter")
    print("   Running locally on: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="127.0.0.1", port=5000, debug=True)
