"""
StartSense - Page 2: Live Monitoring & Telemetry
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import (
    COLOR_CYAN, COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM,
    COLOR_REAL_INPUT, CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM
)
from src.simulator import MotorStartupSimulator

def render_live_monitoring_page(serial_if):
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #00E5FF; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">📡 Live Telemetry & Transient Signature Monitoring</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                High-frequency real-time stream of electromechanical transient signals during starter engagement.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Hardware Potentiometer Banner vs Synthetic Signal Disclaimer
    pot_reading = serial_if.get_potentiometer_reading()
    is_hw = not serial_if.is_mock_mode
    src_tag = "REAL STM32 HARDWARE INPUT" if is_hw else "MOCK HARDWARE EMULATION"
    src_badge_bg = "rgba(224, 64, 251, 0.2)" if is_hw else "rgba(0, 229, 255, 0.15)"
    src_badge_color = COLOR_REAL_INPUT if is_hw else COLOR_CYAN

    col_pot, col_warn = st.columns([1.5, 2.0])
    with col_pot:
        st.markdown(f"""
            <div style="background: #1C192E; border: 1px solid #7B1FA2; border-radius: 10px; padding: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #E1BEE7; text-transform: uppercase;">
                        {src_tag}
                    </span>
                    <span style="background: {src_badge_bg}; color: {src_badge_color}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                        ADC1_INP15 (PA3)
                    </span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #E040FB; margin: 6px 0;">
                    {pot_reading['adc_raw']} <span style="font-size: 14px; font-weight: 400; color: #CE93D8;">counts</span> ({pot_reading['voltage']:.2f} V)
                </div>
                <div style="font-size: 12px; color: #B39DDB;">
                    Mapped Physical Load Proxy: <strong>{pot_reading['normalized']*100:.1f}%</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_warn:
        st.markdown("""
            <div style="background: #111A24; border: 1px solid #1E3A5F; border-radius: 10px; padding: 14px;">
                <div style="font-size: 11px; font-weight: 700; color: #00E5FF; text-transform: uppercase;">
                    SIGNAL AUTHENTICITY NOTICE
                </div>
                <p style="margin: 6px 0 0 0; color: #8B949E; font-size: 12px; line-height: 1.4;">
                    <strong>Notice:</strong> Physical motor, current sensor, and tachometer hardware are not present.
                    Motor current, angular velocity (RPM), encoder pulse intervals, and temperature are 
                    <span style="color: #00E5FF; font-weight: 600;">SIMULATED</span> using an electromechanical ODE model.
                    The potentiometer reading above is the 
                    <span style="color: #E040FB; font-weight: 600;">REAL PHYSICAL INPUT</span>.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Live Telemetry Snapshot Controls & Selector
    col_c1, col_c2, col_c3, col_c4 = st.columns([1.2, 1, 1, 1])
    with col_c1:
        stream_preset = st.selectbox(
            "Select Startup Signature to View:",
            ["NORMAL Startup (Healthy)", "SOFT JAM Startup (Friction / Binding)", "HARD JAM Startup (Rotor Lock)", "Use Potentiometer Load Position"],
            index=0
        )
    with col_c2:
        pwm_val = st.slider("PWM Duty Cycle (%)", min_value=30.0, max_value=100.0, value=100.0, step=5.0)
    with col_c3:
        motor_dir = st.selectbox("Motor Direction", ["FORWARD", "REVERSE"])
    with col_c4:
        st.write("")
        st.write("")
        refresh_clicked = st.button("🔄 Refresh Live Stream", use_container_width=True)

    # Generate telemetry based on choice
    sim = MotorStartupSimulator()
    if stream_preset == "NORMAL Startup (Healthy)":
        cond = CLASS_NORMAL
        load = None
    elif stream_preset == "SOFT JAM Startup (Friction / Binding)":
        cond = CLASS_SOFT_JAM
        load = None
    elif stream_preset == "HARD JAM Startup (Rotor Lock)":
        cond = CLASS_HARD_JAM
        load = None
    else:
        # Driven directly by potentiometer
        load = pot_reading["normalized"]
        cond = CLASS_HARD_JAM if load > 0.8 else (CLASS_SOFT_JAM if load > 0.35 else CLASS_NORMAL)

    telemetry_df, meta = sim.simulate_episode(
        condition=cond,
        load_severity=load,
        pwm_duty=pwm_val,
        direction=motor_dir,
        sample_rate_hz=100,
        seed=int(pot_reading["adc_raw"]) + (1 if refresh_clicked else 0)
    )

    # 4 Quick Metric Readouts of Latest Sample
    last_row = telemetry_df.iloc[-1]
    peak_curr = telemetry_df["current_sim_amp"].max()
    max_spd = telemetry_df["speed_sim_rpm"].max()

    q1, q2, q3, q4, q5 = st.columns(5)
    with q1:
        st.metric(label="Start Command", value="ENGAGED" if last_row["pwm_duty"] > 0 else "IDLE")
    with q2:
        st.metric(label="Simulated Current", value=f"{peak_curr:.2f} A (Peak)")
    with q3:
        st.metric(label="Simulated Speed", value=f"{max_spd:.0f} RPM")
    with q4:
        st.metric(label="Simulated Temp", value=f"{last_row['temp_sim_celsius']:.1f} °C")
    with q5:
        st.metric(label="Encoder Pulse Interval", value=f"{last_row['encoder_interval_ms']:.1f} ms")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 4 Real-time Line Graphs (Current, Speed, Temp, PWM vs Time)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Simulated Stator Current vs Time [SIMULATED]",
            "Simulated Angular Speed (RPM) vs Time [SIMULATED]",
            "Simulated Stator Temperature vs Time [SIMULATED]",
            "Gate Driver PWM & Pulse Intervals [SIMULATED]"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.08
    )

    t = telemetry_df["time_sec"]

    # 1. Current vs Time
    curr_color = COLOR_HARD_JAM if cond == CLASS_HARD_JAM else (COLOR_SOFT_JAM if cond == CLASS_SOFT_JAM else COLOR_NORMAL)
    fig.add_trace(
        go.Scatter(x=t, y=telemetry_df["current_sim_amp"], name="Current (A)",
                   line=dict(color=curr_color, width=2.5)),
        row=1, col=1
    )
    # Add 15A Safety Threshold Line
    fig.add_hline(y=15.0, line_dash="dash", line_color="#FF3D00",
                  annotation_text="STM32 15A Limit", row=1, col=1)

    # 2. Speed vs Time
    fig.add_trace(
        go.Scatter(x=t, y=telemetry_df["speed_sim_rpm"], name="Speed (RPM)",
                   line=dict(color=COLOR_CYAN, width=2.5)),
        row=1, col=2
    )
    fig.add_hline(y=2000.0, line_dash="dot", line_color="#8B949E",
                  annotation_text="Target 2000 RPM", row=1, col=2)

    # 3. Temperature vs Time
    fig.add_trace(
        go.Scatter(x=t, y=telemetry_df["temp_sim_celsius"], name="Temp (°C)",
                   line=dict(color="#FF8A65", width=2.5)),
        row=2, col=1
    )
    fig.add_hline(y=75.0, line_dash="dash", line_color="#FF3D00",
                  annotation_text="Max 75°C", row=2, col=1)

    # 4. PWM & Pulse Interval
    fig.add_trace(
        go.Scatter(x=t, y=telemetry_df["pwm_duty"], name="PWM (%)",
                   line=dict(color="#B388FF", width=2)),
        row=2, col=2
    )
    fig.add_trace(
        go.Scatter(x=t, y=telemetry_df["encoder_interval_ms"], name="Pulse Interval (ms)",
                   line=dict(color="#FFD54F", width=1.5, dash="dot")),
        row=2, col=2
    )

    fig.update_layout(
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#C9D1D9"),
        height=580,
        margin=dict(t=40, b=30, l=40, r=30),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    fig.update_xaxes(showgrid=True, gridcolor="#21262D", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262D", zeroline=False)

    st.plotly_chart(fig, use_container_width=True)
