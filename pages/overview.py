"""
StartSense - Page 1: Overview / Command Center
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.config import (
    PROJECT_NAME, PROJECT_SUBTITLE, VARIANT_ID, VARIANT_NAME,
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM, COLOR_CYAN,
    ACTION_ACCEPT_START, ACTION_STOP
)
from src.experiment_logger import ExperimentLogger

def render_overview_page(serial_if):
    logger = ExperimentLogger()
    counts = logger.get_summary_counts()
    recent_runs_df = logger.get_experiments()

    # Title & Header Banner
    st.markdown("""
        <div style="background: linear-gradient(90deg, #101624 0%, #172338 100%); padding: 22px 26px; border-radius: 12px; border-left: 6px solid #00E5FF; margin-bottom: 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h2 style="margin: 0; color: #FFFFFF; font-weight: 700; letter-spacing: 0.5px;">⚡ StartSense Command Center</h2>
                    <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 14px;">
                        Startup Signature Intelligence for Electric Drives | Variant 02.08 – Soft-Jam vs Hard-Jam Starter
                    </p>
                </div>
                <div style="margin-top: 8px;">
                    <span style="background: rgba(0,229,255,0.12); color: #00E5FF; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; border: 1px solid rgba(0,229,255,0.3);">
                        HYBRID H/W + S/W SIMULATION
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Latest Run Data
    latest_run = recent_runs_df.iloc[0] if not recent_runs_df.empty else None
    current_condition = latest_run["ml_prediction"] if latest_run is not None else CLASS_NORMAL
    confidence = latest_run["confidence"] if latest_run is not None else 0.98
    rec_action = latest_run["recommended_action"] if latest_run is not None else ACTION_ACCEPT_START
    stm32_ack = latest_run["stm32_acknowledgement"] if latest_run is not None else "ACCEPTED"

    # Status Hero Indicator Color
    if current_condition == CLASS_NORMAL:
        status_bg = "rgba(0, 230, 118, 0.12)"
        status_color = COLOR_NORMAL
        status_border = COLOR_NORMAL
        icon = "🟢"
        badge_text = "NORMAL STARTUP"
    elif current_condition == CLASS_SOFT_JAM:
        status_bg = "rgba(255, 179, 0, 0.12)"
        status_color = COLOR_SOFT_JAM
        status_border = COLOR_SOFT_JAM
        icon = "🟡"
        badge_text = "SOFT JAM DETECTED"
    else:
        status_bg = "rgba(255, 61, 0, 0.15)"
        status_color = COLOR_HARD_JAM
        status_border = COLOR_HARD_JAM
        icon = "🔴"
        badge_text = "HARD JAM (CRITICAL STALL)"

    # Hero Banner
    col_hero, col_state = st.columns([1.8, 1.2])

    with col_hero:
        st.markdown(f"""
            <div style="background: {status_bg}; border: 2px solid {status_border}; border-radius: 12px; padding: 22px; text-align: left; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; font-weight: 700; color: #8B949E; text-transform: uppercase; letter-spacing: 1px;">
                        CURRENT DETECTED STARTUP CONDITION
                    </span>
                    <span style="font-size: 12px; background: rgba(255,255,255,0.1); color: #FFF; padding: 3px 10px; border-radius: 12px;">
                        Episode: {latest_run['run_id'] if latest_run is not None else 'DEMO_01'}
                    </span>
                </div>
                <div style="display: flex; align-items: center; gap: 14px; margin: 12px 0;">
                    <span style="font-size: 38px;">{icon}</span>
                    <span style="font-size: 32px; font-weight: 800; color: {status_color}; letter-spacing: 0.5px;">
                        {current_condition}
                    </span>
                </div>
                <div style="display: flex; gap: 20px; font-size: 14px; color: #C9D1D9; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; margin-top: 8px;">
                    <div>Confidence: <strong style="color: #FFF;">{confidence*100:.1f}%</strong></div>
                    <div>Recommended Action: <strong style="color: {status_color};">{rec_action}</strong></div>
                    <div>STM32 Status: <strong style="color: #00E5FF;">{stm32_ack}</strong></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_state:
        # Hardware & Engine health status cards
        is_hw = not serial_if.is_mock_mode
        hw_label = "HARDWARE (USB SERIAL)" if is_hw else "MOCK MODE (EMULATED)"
        hw_color = "#00E676" if is_hw else "#00E5FF"
        pot = serial_if.get_potentiometer_reading()

        st.markdown(f"""
            <div style="background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 18px; height: 100%;">
                <div style="font-size: 12px; font-weight: 700; color: #8B949E; margin-bottom: 12px; text-transform: uppercase;">
                    SYSTEM ENGINE STATUS
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #C9D1D9; font-size: 14px;">STM32 Link:</span>
                    <span style="background: rgba(0,229,255,0.15); color: {hw_color}; font-weight: 700; font-size: 12px; padding: 3px 8px; border-radius: 6px;">
                        ● {hw_label}
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #C9D1D9; font-size: 14px;">Physical Potentiometer:</span>
                    <span style="color: #E040FB; font-weight: 700; font-size: 14px;">
                        {pot['adc_raw']} counts ({pot['voltage']} V)
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #C9D1D9; font-size: 14px;">ML Inference Core:</span>
                    <span style="color: #00E676; font-weight: 700; font-size: 13px;">ACTIVE (Random Forest)</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #C9D1D9; font-size: 14px;">Signal Pipeline:</span>
                    <span style="color: #8B949E; font-size: 12px;">Real Pot + Simulated Motor</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 4 Quick Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Total Startup Runs", value=counts["TOTAL"])
    with c2:
        st.metric(label="Normal Starts", value=counts[CLASS_NORMAL])
    with c3:
        st.metric(label="Soft Jam Starts", value=counts[CLASS_SOFT_JAM])
    with c4:
        st.metric(label="Hard Jam Starts", value=counts[CLASS_HARD_JAM])

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Condition Distribution Chart and Recent Experiments Table
    col_chart, col_table = st.columns([1, 1.8])

    with col_chart:
        st.subheader("Condition Distribution")
        fig_pie = go.Figure(data=[go.Pie(
            labels=[CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM],
            values=[counts[CLASS_NORMAL], counts[CLASS_SOFT_JAM], counts[CLASS_HARD_JAM]],
            marker=dict(colors=[COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM]),
            hole=0.55,
            textinfo='label+percent'
        )])
        fig_pie.update_layout(
            paper_bgcolor="#161B22",
            plot_bgcolor="#161B22",
            font=dict(color="#C9D1D9"),
            margin=dict(t=20, b=20, l=20, r=20),
            height=280,
            showlegend=False
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_table:
        st.subheader("Recent Startup History")
        if not recent_runs_df.empty:
            display_df = recent_runs_df[[
                "run_id", "target_condition", "ml_prediction", "peak_current",
                "max_speed", "recommended_action", "stm32_acknowledgement"
            ]].head(6)
            display_df.columns = ["Run ID", "Target", "ML Result", "Peak I (A)", "Speed (RPM)", "Action", "STM32 Ack"]
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recorded startup runs yet.")
