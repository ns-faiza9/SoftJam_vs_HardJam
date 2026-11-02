"""
StartSense - Page 7: System Architecture & Telemetry Pipeline
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import pandas as pd
from src.config import (
    COLOR_CYAN, COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM,
    COLOR_REAL_INPUT, VARIANT_ID, HARDWARE_PLATFORM
)

def render_architecture_page(serial_if):
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #00E5FF; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">🏗️ System Architecture & Signal Topology</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                Hybrid Hardware + Software Simulation Architecture: Real Potentiometer Dial on STM32 + Virtual Motor ODE + Edge Validation.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Signal Classification Matrix (Real vs Simulated)
    st.subheader("1. Signal Authenticity & Provenance Matrix")
    sig_df = pd.DataFrame([
        {
            "Signal Name": "Potentiometer Position (ADC)",
            "Hardware Source": "100 kΩ Potentiometer on Breadboard",
            "Classification": "REAL HARDWARE INPUT",
            "Hardware Pin": "PA3 (ADC1_INP15 / A0)",
            "Role": "Physical dial providing real manual load/friction proxy input"
        },
        {
            "Signal Name": "Stator Winding Current",
            "Hardware Source": "Simulated ODE (V=IR+Ldi/dt+e)",
            "Classification": "SIMULATED SYNTHETIC SIGNAL",
            "Hardware Pin": "Software Engine",
            "Role": "Inrush transient and stall current simulation"
        },
        {
            "Signal Name": "Rotor Speed (RPM)",
            "Hardware Source": "Simulated ODE (J dω/dt = Kt*i - Tload)",
            "Classification": "SIMULATED SYNTHETIC SIGNAL",
            "Hardware Pin": "Software Engine",
            "Role": "Kinematic acceleration curve under mechanical drag"
        },
        {
            "Signal Name": "Encoder Pulse Interval",
            "Hardware Source": "Simulated Incremental Encoder (24 CPR)",
            "Classification": "SIMULATED SYNTHETIC SIGNAL",
            "Hardware Pin": "Software Engine",
            "Role": "Pulse-to-pulse jitter and period timing"
        },
        {
            "Signal Name": "Stator Temperature",
            "Hardware Source": "Simulated Joulean Heating (I^2*R)",
            "Classification": "SIMULATED SYNTHETIC SIGNAL",
            "Hardware Pin": "Software Engine",
            "Role": "Thermal accumulation under prolonged jam"
        },
        {
            "Signal Name": "User LED Indicators",
            "Hardware Source": "NUCLEO-H753ZI Onboard LEDs",
            "Classification": "REAL HARDWARE OUTPUT",
            "Hardware Pin": "PB0 (LD1), PE1 (LD2), PB14 (LD3)",
            "Role": "Physical visual indicator of validated action (Green/Yellow/Red)"
        }
    ])
    st.dataframe(sig_df, use_container_width=True, hide_index=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # End-to-End Pipeline Flow Diagram
    st.subheader("2. End-to-End Signal & Decision Topology")
    st.markdown("""
        <div style="background: #0E1117; border: 1px solid #30363D; border-radius: 12px; padding: 22px; text-align: center;">
            <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="background: #2D143D; border: 2px solid #E040FB; border-radius: 8px; padding: 12px; width: 140px;">
                    <span style="color: #E040FB; font-size: 11px; font-weight: 700;">REAL HARDWARE</span><br>
                    <strong style="color: #FFF; font-size: 13px;">100kΩ Potentiometer</strong><br>
                    <span style="color: #8B949E; font-size: 11px;">PA3 / ADC1</span>
                </div>
                <span style="font-size: 22px; color: #00E5FF;">➔</span>
                <div style="background: #102A43; border: 2px solid #00E5FF; border-radius: 8px; padding: 12px; width: 150px;">
                    <span style="color: #00E5FF; font-size: 11px; font-weight: 700;">EMBEDDED MCU</span><br>
                    <strong style="color: #FFF; font-size: 13px;">STM32 NUCLEO-H753ZI</strong><br>
                    <span style="color: #8B949E; font-size: 11px;">Cortex-M7 @ 480MHz</span>
                </div>
                <span style="font-size: 22px; color: #00E5FF;">➔</span>
                <div style="background: #1E293B; border: 2px solid #38BDF8; border-radius: 8px; padding: 12px; width: 140px;">
                    <span style="color: #38BDF8; font-size: 11px; font-weight: 700;">COMM LINK</span><br>
                    <strong style="color: #FFF; font-size: 13px;">USB Serial / VCP</strong><br>
                    <span style="color: #8B949E; font-size: 11px;">115200 Baud JSON</span>
                </div>
                <span style="font-size: 22px; color: #00E5FF;">➔</span>
                <div style="background: #111A24; border: 2px solid #00B0FF; border-radius: 8px; padding: 12px; width: 150px;">
                    <span style="color: #00B0FF; font-size: 11px; font-weight: 700;">LAPTOP ML ENGINE</span><br>
                    <strong style="color: #FFF; font-size: 13px;">Random Forest & Feature Extractor</strong><br>
                    <span style="color: #8B949E; font-size: 11px;">Python / Scikit-Learn</span>
                </div>
                <span style="font-size: 22px; color: #00E5FF;">➔</span>
                <div style="background: #2A1215; border: 2px solid #FF3D00; border-radius: 8px; padding: 12px; width: 140px;">
                    <span style="color: #FF3D00; font-size: 11px; font-weight: 700;">SAFETY VALIDATION</span><br>
                    <strong style="color: #FFF; font-size: 13px;">STM32 Local Check</strong><br>
                    <span style="color: #8B949E; font-size: 11px;">Hardware Bounds</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Live Serial Bus Inspector & Packet Traffic Log
    st.subheader("3. Live USB Serial Communication Traffic (PySerial)")
    st.caption("Inspect live incoming (RX) and outgoing (TX) JSON packets transmitted across the physical/mock USB serial link.")

    logs = serial_if.get_logs()
    if logs:
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True, hide_index=True, height=220)
    else:
        st.info("Serial communication buffer is currently idle.")
