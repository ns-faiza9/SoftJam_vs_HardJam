"""
StartSense - Page 6: Experiment History & Persistent Audit Log
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go

from src.config import (
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM, COLOR_CYAN
)
from src.experiment_logger import ExperimentLogger

def render_experiment_history_page():
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #00E5FF; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">📜 Experiment History & Audit Trail (SQLite)</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                Comprehensive database of startup runs. Every complete startup episode is treated as an independent sample.
            </p>
        </div>
    """, unsafe_allow_html=True)

    logger = ExperimentLogger()

    # Search & Filter Row
    col_filter, col_search, col_dl = st.columns([1.2, 2, 1])

    with col_filter:
        cond_filter = st.selectbox("Filter Condition", ["ALL", CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM])

    with col_search:
        search_query = st.text_input("Search Run ID, Condition ID, or Action", placeholder="e.g. RUN_001 or ACCEPT")

    # Fetch experiments from SQLite
    df_runs = logger.get_experiments(
        condition_filter=None if cond_filter == "ALL" else cond_filter,
        search_query=search_query if search_query else None
    )

    with col_dl:
        st.write("")
        st.write("")
        csv_data = logger.export_csv()
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name="startsense_experiments.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    st.caption(f"Showing {len(df_runs)} recorded startup episodes:")

    if not df_runs.empty:
        # Display main audit table
        display_cols = [
            "run_id", "condition_id", "target_condition", "ml_prediction",
            "confidence", "peak_current", "max_speed", "startup_duration",
            "temp_rise", "recommended_action", "stm32_acknowledgement", "timestamp"
        ]
        
        st.dataframe(
            df_runs[display_cols],
            use_container_width=True,
            hide_index=True,
            height=320
        )

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Episode Deep Drill-Down
        st.subheader("🔎 Episode Transient Drill-Down & Replay")
        run_ids = df_runs["run_id"].tolist()
        selected_run = st.selectbox("Select Episode Run ID to Inspect:", run_ids)

        if selected_run:
            episode_row = df_runs[df_runs["run_id"] == selected_run].iloc[0]
            col_det1, col_det2 = st.columns([1.5, 1.2])

            with col_det1:
                st.markdown(f"**Transient Telemetry Replay for {selected_run}:**")
                telemetry_df = logger.get_episode_telemetry(selected_run)
                if telemetry_df is not None and not telemetry_df.empty:
                    fig_replay = go.Figure()
                    t = telemetry_df["time_sec"]
                    pred_cls = episode_row["ml_prediction"]
                    p_color = COLOR_HARD_JAM if pred_cls == CLASS_HARD_JAM else (COLOR_SOFT_JAM if pred_cls == CLASS_SOFT_JAM else COLOR_NORMAL)

                    fig_replay.add_trace(go.Scatter(x=t, y=telemetry_df["current_sim_amp"], name="Current (A) [SIM]", line=dict(color=p_color, width=2.5)))
                    fig_replay.add_trace(go.Scatter(x=t, y=telemetry_df["speed_sim_rpm"] / 100.0, name="Speed (x100 RPM) [SIM]", line=dict(color=COLOR_CYAN, width=2)))
                    fig_replay.update_layout(
                        paper_bgcolor="#161B22",
                        plot_bgcolor="#0E1117",
                        font=dict(color="#C9D1D9"),
                        height=280,
                        margin=dict(t=20, b=20, l=40, r=20),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig_replay, use_container_width=True)
                else:
                    st.info("Full telemetry points not archived for this specific demo record.")

            with col_det2:
                st.markdown(f"**Episode Metadata & Features ({selected_run}):**")
                st.markdown(f"""
                    - **Variant ID:** `{episode_row['variant_id']}`
                    - **Condition ID:** `{episode_row['condition_id']}`
                    - **Target Condition:** `{episode_row['target_condition']}`
                    - **ML Prediction:** **{episode_row['ml_prediction']}** ({episode_row['confidence']*100:.1f}%)
                    - **Baseline Result:** `{episode_row['baseline_result']}`
                    - **Recommended Action:** `{episode_row['recommended_action']}`
                    - **STM32 Ack:** `{episode_row['stm32_acknowledgement']}`
                    - **Timestamp:** `{episode_row['timestamp']}`
                    - **Calibration:** `{episode_row['calibration_version']}`
                """)
    else:
        st.warning("No experiment records match the search filter.")
