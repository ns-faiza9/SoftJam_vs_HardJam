"""
StartSense - Page 4: ML Intelligence & Model Benchmarking
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import streamlit as st
import joblib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import (
    MODELS_DIR, GENERATED_DATA_DIR,
    CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM, CLASSES,
    COLOR_NORMAL, COLOR_SOFT_JAM, COLOR_HARD_JAM, COLOR_CYAN
)
from src.model_training import train_and_compare_models, load_or_create_dataset
from src.feature_extraction import FEATURE_NAMES

def render_ml_intelligence_page():
    st.markdown("""
        <div style="background: #161B22; border-left: 5px solid #00E5FF; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #FFF; font-weight: 700;">🧠 Machine Learning Intelligence & Benchmark Lab</h3>
            <p style="margin: 4px 0 0 0; color: #8B949E; font-size: 13px;">
                Supervised classification of motor startup transient signatures. Strictly zero data leakage (split by independent runs).
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Load dataset
    df = load_or_create_dataset()

    # Load metrics
    metrics_path = MODELS_DIR / "training_metrics.joblib"
    if not metrics_path.exists():
        with st.spinner("Training baseline and ML models..."):
            metrics = train_and_compare_models()
    else:
        metrics = joblib.load(metrics_path)

    # Top Metrics Hero Row
    rf_m = metrics["random_forest"]
    dt_m = metrics["decision_tree"]

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Model Accuracy (RF)", value=f"{rf_m['accuracy']*100:.1f}%")
    with m2:
        st.metric(label="Macro F1-Score", value=f"{rf_m['macro_f1']*100:.1f}%")
    with m3:
        st.metric(label="Hard-Jam Recall", value=f"{rf_m['hard_jam_recall']*100:.1f}%", help="Critical: zero tolerance for missed Hard Jam stall")
    with m4:
        st.metric(label="False Alarm Rate", value=f"{rf_m['false_alarm_rate']*100:.1f}%", help="Normal motors incorrectly flagged as Jam")
    with m5:
        st.metric(label="Dataset Episodes", value=f"{len(df)} runs")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Retrain Models Section
    col_retrain, _ = st.columns([1.5, 3])
    with col_retrain:
        if st.button("⚡ Retrain Models with Fresh Split", use_container_width=True):
            with st.spinner("Re-training Decision Tree & Random Forest models..."):
                metrics = train_and_compare_models(random_seed=int(np.random.randint(1, 1000)))
                rf_m = metrics["random_forest"]
                dt_m = metrics["decision_tree"]
            st.success("Models retrained and updated successfully!")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Tabbed Interface: 1. Model Comparison, 2. Confusion Matrices, 3. Feature Importance, 4. Dataset Preview
    tab_comp, tab_cm, tab_feat, tab_data = st.tabs([
        "📊 Model Comparison", "🎯 Confusion Matrices", "🔍 Feature Importance", "📁 Dataset Explorer"
    ])

    with tab_comp:
        st.subheader("Decision Tree vs Random Forest Performance Benchmarking")
        st.caption("Calculated on held-out test set of independent startup runs.")

        comp_data = {
            "Metric": ["Accuracy", "Macro Precision", "Macro Recall", "Macro F1-Score", "Hard-Jam Recall (Safety)", "False-Alarm Rate"],
            "Decision Tree": [
                f"{dt_m['accuracy']*100:.2f}%",
                f"{dt_m['macro_precision']*100:.2f}%",
                f"{dt_m['macro_recall']*100:.2f}%",
                f"{dt_m['macro_f1']*100:.2f}%",
                f"{dt_m['hard_jam_recall']*100:.2f}%",
                f"{dt_m['false_alarm_rate']*100:.2f}%"
            ],
            "Random Forest": [
                f"{rf_m['accuracy']*100:.2f}%",
                f"{rf_m['macro_precision']*100:.2f}%",
                f"{rf_m['macro_recall']*100:.2f}%",
                f"{rf_m['macro_f1']*100:.2f}%",
                f"{rf_m['hard_jam_recall']*100:.2f}%",
                f"{rf_m['false_alarm_rate']*100:.2f}%"
            ]
        }
        comp_df = pd.DataFrame(comp_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # Bar chart comparison
        fig_bar = go.Figure(data=[
            go.Bar(name='Decision Tree', x=["Accuracy", "Macro F1", "Hard-Jam Recall"],
                   y=[dt_m['accuracy']*100, dt_m['macro_f1']*100, dt_m['hard_jam_recall']*100],
                   marker_color="#00B0FF"),
            go.Bar(name='Random Forest', x=["Accuracy", "Macro F1", "Hard-Jam Recall"],
                   y=[rf_m['accuracy']*100, rf_m['macro_f1']*100, rf_m['hard_jam_recall']*100],
                   marker_color="#00E676")
        ])
        fig_bar.update_layout(
            barmode='group',
            paper_bgcolor="#161B22",
            plot_bgcolor="#0E1117",
            font=dict(color="#C9D1D9"),
            height=300,
            margin=dict(t=20, b=20, l=40, r=20),
            yaxis=dict(range=[70, 105], title="Score (%)")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Per-Class Classification Metrics (Random Forest)")
        per_class_rf = rf_m["per_class"]
        pc_rows = []
        for cname in CLASSES:
            pc_rows.append({
                "Condition Class": cname,
                "Precision": f"{per_class_rf[cname]['precision']*100:.2f}%",
                "Recall": f"{per_class_rf[cname]['recall']*100:.2f}%",
                "F1-Score": f"{per_class_rf[cname]['f1']*100:.2f}%"
            })
        st.dataframe(pd.DataFrame(pc_rows), use_container_width=True, hide_index=True)

    with tab_cm:
        st.subheader("Confusion Matrices (Normalized on Independent Test Episodes)")
        col_cm1, col_cm2 = st.columns(2)

        def plot_cm(cm_matrix, title):
            fig = px.imshow(
                cm_matrix,
                x=CLASSES,
                y=CLASSES,
                color_continuous_scale="Blues",
                text_auto=True,
                labels=dict(x="Predicted Class", y="Actual Ground Truth", color="Episodes")
            )
            fig.update_layout(
                title=title,
                paper_bgcolor="#161B22",
                plot_bgcolor="#161B22",
                font=dict(color="#C9D1D9"),
                height=340,
                margin=dict(t=40, b=20, l=40, r=20)
            )
            return fig

        with col_cm1:
            st.plotly_chart(plot_cm(dt_m["confusion_matrix"], "Decision Tree Confusion Matrix"), use_container_width=True)
        with col_cm2:
            st.plotly_chart(plot_cm(rf_m["confusion_matrix"], "Random Forest Confusion Matrix"), use_container_width=True)

    with tab_feat:
        st.subheader("Feature Importance Rankings (Gini Impurity Reduction)")
        fi_dict = rf_m.get("feature_importances", {})
        fi_sorted = sorted(fi_dict.items(), key=lambda x: x[1], reverse=True)
        fi_df = pd.DataFrame(fi_sorted, columns=["Feature", "Importance Score"])

        fig_fi = go.Figure(go.Bar(
            x=fi_df["Importance Score"],
            y=fi_df["Feature"],
            orientation='h',
            marker=dict(
                color=fi_df["Importance Score"],
                colorscale="Viridis"
            )
        ))
        fig_fi.update_layout(
            paper_bgcolor="#161B22",
            plot_bgcolor="#0E1117",
            font=dict(color="#C9D1D9"),
            height=400,
            margin=dict(t=20, b=20, l=160, r=20),
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig_fi, use_container_width=True)

    with tab_data:
        st.subheader("Synthetic Dataset Preview (1 Row = 1 Independent Startup Run)")
        st.caption("Signals are simulated using electromechanical differential equations; labels are generated per episode.")
        st.dataframe(df.head(25), use_container_width=True, hide_index=True)
