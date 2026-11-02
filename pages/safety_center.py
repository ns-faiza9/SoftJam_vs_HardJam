"""
StartSense - Page 5: Safety Decision Center & Embedded Hardware Interlocks
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import time
from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM, COLOR_CYAN,
    SAFETY_LIMITS
)
from src.safety_validation import SafetyDecisionEngine

def render_safety_center_page(serial_if):
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #FF3D00; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">🛡️ Safety Decision Center & Local Hardware Boundary Enforcement</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                Decoupled architecture: ML recommends operational actions; STM32 Cortex-M7 independently validates against hard physical limits.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Architectural Rules Callout
    st.markdown("""
        <div style="background: #111A24; border: 1px solid #1E3A5F; border-radius: 8px; padding: 14px; margin-bottom: 18px;">
            <div style="font-size: 12px; font-weight: 700; color: #00E5FF; text-transform: uppercase;">
                STRICT CONTROL-PLANE ISOLATION POLICY
            </div>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #C9D1D9; line-height: 1.4;">
                The ML model running on the laptop <strong>never writes directly to motor PWM registers, H-bridge gates, or PID parameters</strong>.
                It can only submit one of 4 discrete safe operational actions. 
                The embedded STM32 NUCLEO-H753ZI firmware retains absolute supervisory authority to reject any recommendation that violates local physical limits.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 4 Allowable Actions Card Grid
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    with col_a1:
        st.markdown("""
            <div style="background: #161B22; border: 1px solid #00E676; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="color: #00E676; font-weight: 700; font-size: 14px;">1. ACCEPT_START</div>
                <div style="color: #8B949E; font-size: 12px; margin-top: 4px;">
                    Rotor accelerated cleanly; normal inrush transient confirmed; hand over drive control to governor.
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_a2:
        st.markdown("""
            <div style="background: #161B22; border: 1px solid #FFD54F; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="color: #FFD54F; font-weight: 700; font-size: 14px;">2. RETRY_SAFE_PROFILE</div>
                <div style="color: #8B949E; font-size: 12px; margin-top: 4px;">
                    Marginal binding or low ML confidence. Retry with gentle pulsing declogging ramp.
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_a3:
        st.markdown("""
            <div style="background: #161B22; border: 1px solid #FFB300; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="color: #FFB300; font-weight: 700; font-size: 14px;">3. DERATE</div>
                <div style="color: #8B949E; font-size: 12px; margin-top: 4px;">
                    Soft jam detected with moderate friction. Throttle maximum drive power by 30% to avoid winding overheating.
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_a4:
        st.markdown("""
            <div style="background: #161B22; border: 1px solid #FF3D00; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="color: #FF3D00; font-weight: 700; font-size: 14px;">4. STOP</div>
                <div style="color: #8B949E; font-size: 12px; margin-top: 4px;">
                    Severe Hard Jam or stall lockup. Immediate electrical cutoff to prevent catastrophic stator meltdown.
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Interactive Safety Decision Simulation & Interlock Tester
    st.subheader("Interactive Embedded Safety Interlock & Fault-Injection Tester")
    st.caption("Test how the STM32 Cortex-M7 local safety engine reacts when an unsafe recommendation or hardware fault occurs.")

    c_rec, c_peak, c_temp, c_speed, c_link = st.columns(5)
    with c_rec:
        selected_rec = st.selectbox("Laptop Recommendation", [ACTION_ACCEPT_START, ACTION_DERATE, ACTION_RETRY_SAFE, ACTION_STOP])
    with c_peak:
        inj_current = st.slider("Local Current (A)", 0.0, 25.0, 8.5, 0.5)
    with c_temp:
        inj_temp = st.slider("Stator Temp (°C)", 20.0, 95.0, 32.0, 1.0)
    with c_speed:
        inj_speed = st.slider("Motor Speed (RPM)", 0.0, 3200.0, 2400.0, 100.0)
    with c_link:
        link_healthy = st.checkbox("Serial Link Healthy", value=True)

    # Run Local Safety Check
    safety_engine = SafetyDecisionEngine()
    test_rec = {
        "seq": 1088,
        "model_version": "StartSense_v1.0_RF",
        "predicted_condition": CLASS_NORMAL if selected_rec == ACTION_ACCEPT_START else CLASS_SOFT_JAM,
        "confidence": 0.94,
        "recommended_action": selected_rec,
        "expiry_ms": SAFETY_LIMITS["COMMAND_EXPIRY_MS"]
    }
    telemetry_snap = {
        "peak_current_amp": inj_current,
        "final_temp_celsius": inj_temp,
        "max_speed_rpm": inj_speed
    }
    val_result = safety_engine.simulate_stm32_validation(test_rec, telemetry_snap, link_healthy=link_healthy)

    # Display Validation Result
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    is_accepted = val_result["status"] == "ACCEPTED"
    banner_border = "#00E676" if is_accepted else "#FF3D00"
    banner_title = "RECOMMENDATION VALIDATED & ACCEPTED" if is_accepted else "RECOMMENDATION REJECTED BY LOCAL STM32 LIMITS"

    st.markdown(f"""
        <div style="background: #161B22; border-left: 6px solid {banner_border}; border-radius: 10px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 11px; font-weight: 700; color: #8B949E; text-transform: uppercase;">
                        EMBEDDED VALIDATION VERDICT (SEQ: {val_result['seq']})
                    </span>
                    <div style="font-size: 24px; font-weight: 800; color: {banner_border}; margin: 4px 0;">
                        {banner_title}
                    </div>
                </div>
                <div>
                    <span style="background: rgba(255,255,255,0.1); color: #FFF; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 14px;">
                        Actual Motor Action: <span style="color: {banner_border};">{val_result['action_taken']}</span>
                    </span>
                </div>
            </div>
            <div style="margin-top: 12px; font-size: 13px; color: #C9D1D9;">
                <strong>Diagnostic Reason Code:</strong> <code>{val_result['reason_code']}</code><br>
                <strong>Firmware Explanation:</strong> {val_result['reason_description']}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Local Hard Limit Specifications Table
    st.subheader("STM32 Hard Boundaries & Safe Fallback States")
    limits_df = pd.DataFrame([
        {"Hardware Limit": "Overcurrent Ceiling", "Threshold": f"{SAFETY_LIMITS['MAX_CURRENT_AMP']} A", "Hardware Interlock": "Forces STOP immediately, overriding laptop"},
        {"Hardware Limit": "Locked Rotor Stall Limit", "Threshold": f"{SAFETY_LIMITS['STALL_TIMEOUT_SEC']} s", "Hardware Interlock": "Trips circuit breaker if motor is stalled > 0.8s"},
        {"Hardware Limit": "Maximum Stator Temp", "Threshold": f"{SAFETY_LIMITS['MAX_TEMP_CELSIUS']} °C", "Hardware Interlock": "Rejects ACCEPT_START, forces DERATE / STOP"},
        {"Hardware Limit": "Minimum Valid Speed", "Threshold": f"{SAFETY_LIMITS['MIN_SPEED_ACCEPT_RPM']} RPM", "Hardware Interlock": "Refuses ACCEPT_START if speed was never reached"},
        {"Hardware Limit": "Heartbeat Watchdog", "Threshold": f"{SAFETY_LIMITS['COMMAND_EXPIRY_MS']} ms", "Hardware Interlock": "Autonomous FALLBACK_SAFE_SHUTDOWN if serial cable is pulled"}
    ])
    st.dataframe(limits_df, use_container_width=True, hide_index=True)
