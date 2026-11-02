"""
StartSense - Page 3: Startup Simulation & Live Testing
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import time
import pandas as pd
import plotly.graph_objects as go
from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM, COLOR_CYAN,
    ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP
)
from src.simulator import MotorStartupSimulator
from src.feature_extraction import extract_features_from_episode
from src.baseline import RuleBasedBaselineDetector
from src.prediction import MotorConditionPredictor
from src.safety_validation import SafetyDecisionEngine
from src.experiment_logger import ExperimentLogger

def render_simulation_page(serial_if):
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #00E5FF; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">🧪 Interactive Startup Scenario Generator & Test Suite</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                Execute simulated startup transients, extract high-order features, run ML inference, validate safety, and record to database.
            </p>
        </div>
    """, unsafe_allow_html=True)

    pot_reading = serial_if.get_potentiometer_reading()

    # Form / Controls Container
    with st.container():
        col_preset, col_load, col_pwm = st.columns(3)
        with col_preset:
            test_mode = st.radio(
                "Condition Scenario Preset:",
                ["NORMAL Startup", "SOFT JAM Startup", "HARD JAM Startup", "Hardware Potentiometer Dial"],
                index=0
            )
        with col_load:
            pot_norm = pot_reading["normalized"]
            use_pot = (test_mode == "Hardware Potentiometer Dial")
            custom_load = st.slider(
                "Mechanical Load Severity Proxy (0.0 = Free, 1.0 = Jam)",
                min_value=0.0, max_value=1.0,
                value=float(pot_norm) if use_pot else 0.15,
                step=0.02,
                disabled=use_pot,
                help="When using Potentiometer Dial, this tracks the real hardware ADC position"
            )
        with col_pwm:
            pwm_duty = st.slider("Gate Driver PWM (%)", min_value=40.0, max_value=100.0, value=100.0, step=5.0)

        col_dir, col_temp, col_noise = st.columns(3)
        with col_dir:
            direction = st.selectbox("Starter Direction", ["FORWARD", "REVERSE"])
        with col_temp:
            amb_temp = st.number_input("Ambient Temperature (°C)", min_value=15.0, max_value=60.0, value=25.0, step=1.0)
        with col_noise:
            noise_pct = st.slider("Stochastic Noise (%)", min_value=1.0, max_value=15.0, value=5.0, step=1.0) / 100.0

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Action Buttons: START TEST and RESET
    btn_start, btn_reset, _ = st.columns([1.2, 1, 3])
    with btn_start:
        start_clicked = st.button("🚀 START TEST RUN", type="primary", use_container_width=True)
    with btn_reset:
        reset_clicked = st.button("🧹 Reset System", use_container_width=True)

    if reset_clicked:
        st.session_state["latest_test_result"] = None
        st.success("Test session reset to clean state.")

    # Execution Pipeline
    if start_clicked:
        # Determine condition and load
        if test_mode == "NORMAL Startup":
            target_cond = CLASS_NORMAL
            load_to_use = None
        elif test_mode == "SOFT JAM Startup":
            target_cond = CLASS_SOFT_JAM
            load_to_use = None
        elif test_mode == "HARD JAM Startup":
            target_cond = CLASS_HARD_JAM
            load_to_use = None
        else:
            load_to_use = pot_reading["normalized"]
            target_cond = CLASS_HARD_JAM if load_to_use > 0.8 else (CLASS_SOFT_JAM if load_to_use > 0.35 else CLASS_NORMAL)

        progress_bar = st.progress(0, text="1/5: Simulating 3.0s motor electromechanical transient...")
        sim = MotorStartupSimulator()
        telemetry_df, meta = sim.simulate_episode(
            condition=target_cond,
            load_severity=load_to_use if load_to_use is not None else custom_load,
            pwm_duty=pwm_duty,
            direction=direction,
            ambient_temp=amb_temp,
            noise_level=noise_pct,
            duration_sec=3.0,
            sample_rate_hz=100
        )
        time.sleep(0.1)

        progress_bar.progress(30, text="2/5: Extracting kinematic & electrical features...")
        feats = extract_features_from_episode(telemetry_df, meta)
        time.sleep(0.1)

        progress_bar.progress(55, text="3/5: Running Rule-Based Baseline & ML Intelligence...")
        baseline = RuleBasedBaselineDetector()
        base_pred, base_conf, base_reason = baseline.predict(feats)

        predictor = MotorConditionPredictor()
        ml_pred, ml_conf, ml_probs = predictor.predict(feats)
        time.sleep(0.1)

        progress_bar.progress(80, text="4/5: Formulating safety action & querying STM32 validator...")
        safety = SafetyDecisionEngine()
        rec = safety.formulate_recommendation(ml_pred, ml_conf, feats)

        # Transmit recommendation over serial link to STM32 (or mock engine)
        serial_resp = serial_if.send_recommendation(rec)
        ack_status = serial_resp.get("status", "ACCEPTED")
        ack_reason = serial_resp.get("reason", "NONE_VALIDATED")

        progress_bar.progress(95, text="5/5: Storing episode in SQLite database...")
        logger = ExperimentLogger()
        run_id = f"RUN_{int(time.time()) % 100000:05d}"
        logger.log_experiment(
            run_id=run_id,
            condition_id=f"COND_{target_cond.replace(' ', '_')}",
            operator_set_severity=feats["load_proxy"],
            target_condition=target_cond,
            calibration_version="Calib_v1.0.4",
            telemetry_df=telemetry_df,
            features=feats,
            baseline_result=base_pred,
            ml_prediction=ml_pred,
            confidence=ml_conf,
            recommended_action=rec["recommended_action"],
            stm32_acknowledgement=f"{ack_status} ({ack_reason})"
        )
        progress_bar.progress(100, text="Test execution complete!")
        time.sleep(0.1)
        progress_bar.empty()

        # Save to session state
        st.session_state["latest_test_result"] = {
            "run_id": run_id,
            "target_condition": target_cond,
            "telemetry_df": telemetry_df,
            "features": feats,
            "baseline_pred": base_pred,
            "baseline_reason": base_reason,
            "ml_pred": ml_pred,
            "ml_conf": ml_conf,
            "ml_probs": ml_probs,
            "rec": rec,
            "ack": serial_resp
        }

    # Render latest test results if available
    res = st.session_state.get("latest_test_result", None)
    if res is not None:
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        # Color coding
        ml_cls = res["ml_pred"]
        badge_color = COLOR_HARD_JAM if ml_cls == CLASS_HARD_JAM else (COLOR_SOFT_JAM if ml_cls == CLASS_SOFT_JAM else COLOR_NORMAL)

        # Result Banner
        st.markdown(f"""
            <div style="background: #161B22; border-left: 6px solid {badge_color}; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="font-size: 12px; font-weight: 700; color: #8B949E; text-transform: uppercase;">
                            RUN RESULT: {res['run_id']} | TARGET: {res['target_condition']}
                        </span>
                        <div style="font-size: 28px; font-weight: 800; color: {badge_color}; margin: 4px 0;">
                            {ml_cls}
                        </div>
                    </div>
                    <div style="display: flex; gap: 24px; font-size: 14px;">
                        <div>ML Confidence: <br><strong style="font-size: 18px; color: #FFF;">{res['ml_conf']*100:.1f}%</strong></div>
                        <div>Recommended Action: <br><strong style="font-size: 18px; color: {badge_color};">{res['rec']['recommended_action']}</strong></div>
                        <div>STM32 Status: <br><strong style="font-size: 18px; color: #00E5FF;">{res['ack'].get('status', 'ACCEPTED')}</strong></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1.5, 1.2])

        with col_left:
            st.subheader("Episode Transient Curves [SIMULATED]")
            df_plot = res["telemetry_df"]
            t = df_plot["time_sec"]

            fig_run = go.Figure()
            fig_run.add_trace(go.Scatter(x=t, y=df_plot["current_sim_amp"], name="Current (A)",
                                         line=dict(color=badge_color, width=2.5)))
            fig_run.add_trace(go.Scatter(x=t, y=df_plot["speed_sim_rpm"] / 100.0, name="Speed (x100 RPM)",
                                         line=dict(color=COLOR_CYAN, width=2)))
            fig_run.add_hline(y=15.0, line_dash="dash", line_color="#FF3D00",
                              annotation_text="STM32 15A Limit")
            fig_run.update_layout(
                paper_bgcolor="#161B22",
                plot_bgcolor="#0E1117",
                font=dict(color="#C9D1D9"),
                height=320,
                margin=dict(t=20, b=20, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
            )
            fig_run.update_xaxes(showgrid=True, gridcolor="#21262D")
            fig_run.update_yaxes(showgrid=True, gridcolor="#21262D")
            st.plotly_chart(fig_run, use_container_width=True)

        with col_right:
            st.subheader("Extracted Features")
            feats = res["features"]
            feat_display_df = pd.DataFrame([
                {"Feature": "Peak Current", "Value": f"{feats['peak_current_amp']} A"},
                {"Feature": "Max Speed Attained", "Value": f"{feats['max_speed_rpm']} RPM"},
                {"Feature": "Startup Duration", "Value": f"{feats['startup_duration_sec']} s"},
                {"Feature": "Time to Target (2000 RPM)", "Value": f"{feats['time_to_target_speed_sec']} s"},
                {"Feature": "Current Rise Rate", "Value": f"{feats['current_rise_rate_amps_per_sec']} A/s"},
                {"Feature": "Speed Rise Rate", "Value": f"{feats['speed_rise_rate_rpm_per_sec']} RPM/s"},
                {"Feature": "Temp Rise (ΔT)", "Value": f"{feats['temp_rise_celsius']} °C"},
                {"Feature": "Encoder Pulse Mean", "Value": f"{feats['encoder_pulse_interval_mean_ms']} ms"},
                {"Feature": "Load Proxy", "Value": f"{feats['load_proxy']}"}
            ])
            st.dataframe(feat_display_df, use_container_width=True, hide_index=True, height=280)

        # Baseline vs ML Comparison Box
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.subheader("Intelligence Comparison: Rule-Based Baseline vs Machine Learning")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.markdown(f"""
                <div style="background: #111A24; border: 1px solid #1E3A5F; border-radius: 8px; padding: 14px;">
                    <div style="font-size: 11px; font-weight: 700; color: #8B949E; text-transform: uppercase;">
                        ENGINEERING RULE-BASED BASELINE
                    </div>
                    <div style="font-size: 18px; font-weight: 700; color: #FFF; margin: 4px 0;">
                        {res['baseline_pred']}
                    </div>
                    <div style="font-size: 12px; color: #8B949E;">{res['baseline_reason']}</div>
                </div>
            """, unsafe_allow_html=True)

        with b_col2:
            st.markdown(f"""
                <div style="background: #111A24; border: 1px solid #1E3A5F; border-radius: 8px; padding: 14px;">
                    <div style="font-size: 11px; font-weight: 700; color: #00E5FF; text-transform: uppercase;">
                        RANDOM FOREST ML CLASSIFIER
                    </div>
                    <div style="font-size: 18px; font-weight: 700; color: {badge_color}; margin: 4px 0;">
                        {res['ml_pred']} ({res['ml_conf']*100:.1f}% confidence)
                    </div>
                    <div style="font-size: 12px; color: #8B949E;">Multivariate feature probability distribution across independent runs.</div>
                </div>
            """, unsafe_allow_html=True)
