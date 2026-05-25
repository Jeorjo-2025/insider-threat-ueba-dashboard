# =========================
# app.py - UEBA Insider Threat Dashboard (Demo)
# =========================

# --- Imports ---
import numpy as np              # For numerical operations
import pandas as pd             # For tabular data handling
from sklearn.ensemble import IsolationForest  # For anomaly detection
from sklearn.preprocessing import MinMaxScaler  # For scaling features
import streamlit as st          # For interactive web app
import plotly.express as px     # For colorful, interactive charts

# --- Page config & theming ---
st.set_page_config(
    page_title="Insider Threat UEBA Dashboard",
    page_icon="usa_map.png",   
    layout="wide"
)

# --- Title + Subtitle (with USA map icon) ---
st.markdown(
    """
    <div style='text-align:center; margin-top:10px;'>
        <img src="usa_map.png" width="80" style="margin-bottom:10px;">
        <h1 style='color:#4F46E5; margin-bottom:0;'>Insider Threat UEBA Dashboard</h1>
        <p style='color:#6B7280; font-size:16px; margin-top:4px;'>
            Detect anomalous user behavior with ML‑powered risk scoring
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# --- Sidebar controls ---
st.sidebar.header("⚙️ Controls")  # Sidebar section title

# Number of synthetic users to simulate
num_users = st.sidebar.slider("Number of users", min_value=20, max_value=200, value=80, step=10)

# Random seed for reproducibility
seed = st.sidebar.number_input("Random seed", min_value=0, max_value=9999, value=42, step=1)

# Contamination (expected anomaly proportion) for Isolation Forest
contamination = st.sidebar.slider("Expected anomaly ratio", 0.01, 0.30, 0.10, 0.01)

# --- Synthetic data generation function ---
def generate_synthetic_data(n_users: int, random_state: int = 42) -> pd.DataFrame:
    """
    Create a synthetic dataset of user activity for one day.
    Each row = one user-day with behavioral features.
    """
    rng = np.random.default_rng(random_state)  # Random generator

    # Create user IDs and assign departments
    users = [f"user_{i:03d}" for i in range(1, n_users + 1)]
    departments = rng.choice(
        ["Finance", "HR", "Engineering", "Sales", "IT"],
        size=n_users,
        p=[0.15, 0.10, 0.35, 0.25, 0.15]
    )

    # Generate behavioral features with realistic-ish distributions
    files_accessed = rng.poisson(lam=40, size=n_users)          # Typical file access count
    usb_transfers = rng.poisson(lam=1, size=n_users)            # USB usage
    external_emails = rng.poisson(lam=5, size=n_users)          # Emails to external domains
    failed_logins = rng.poisson(lam=0.5, size=n_users)          # Failed login attempts
    off_hours_ratio = rng.beta(a=1.5, b=6, size=n_users)        # Fraction of activity outside 9–5

    # Introduce some "malicious" spikes for a few users
    n_spikes = max(1, n_users // 10)                            # ~10% of users anomalous
    spike_indices = rng.choice(n_users, size=n_spikes, replace=False)

    files_accessed[spike_indices] *= rng.integers(3, 8, size=n_spikes)   # Massive file access
    usb_transfers[spike_indices] += rng.integers(3, 10, size=n_spikes)   # Heavy USB usage
    external_emails[spike_indices] *= rng.integers(2, 5, size=n_spikes)  # Many external emails
    failed_logins[spike_indices] += rng.integers(3, 8, size=n_spikes)    # Many failed logins
    off_hours_ratio[spike_indices] = np.clip(off_hours_ratio[spike_indices] + 0.4, 0, 1)

    # Build DataFrame
    df = pd.DataFrame({
        "user_id": users,
        "department": departments,
        "files_accessed": files_accessed,
        "usb_transfers": usb_transfers,
        "external_emails": external_emails,
        "failed_logins": failed_logins,
        "off_hours_ratio": off_hours_ratio
    })

    return df

# --- Generate data based on sidebar settings ---
data = generate_synthetic_data(num_users, random_state=seed)

# --- Feature scaling & anomaly detection ---
feature_cols = ["files_accessed", "usb_transfers", "external_emails", "failed_logins", "off_hours_ratio"]

# Scale features to [0, 1] for better model behavior
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(data[feature_cols])

# Train Isolation Forest
model = IsolationForest(
    n_estimators=200,
    contamination=contamination,
    random_state=seed
)
model.fit(X_scaled)

# Get anomaly scores (lower = more anomalous in IsolationForest)
raw_scores = model.decision_function(X_scaled)

# Convert to risk scores: higher = more risky (0–100)
# Invert and scale decision_function output
risk_scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)
risk_scores = (risk_scores * 100).round(1)

# Attach risk scores to data
data["risk_score"] = risk_scores

# Classify risk levels
def classify_risk(score: float) -> str:
    if score >= 80:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"

data["risk_level"] = data["risk_score"].apply(classify_risk)

# --- Compute overall organization risk index ---
org_risk = data["risk_score"].mean().round(1)

# --- Layout: top-level KPIs ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📊 Overall Risk Index", f"{org_risk} / 100")

with col2:
    st.metric("👥 Total Users Monitored", len(data))

with col3:
    st.metric("🚨 High-Risk Users", int((data["risk_level"] == "High").sum()))

st.markdown("---")

# --- Risk meter (gauge-like visualization) ---
# Use a colored bar + text instead of a true gauge for simplicity
def risk_color(score: float) -> str:
    if score < 40:
        return "#22c55e"  # green
    elif score < 70:
        return "#f97316"  # orange
    else:
        return "#ef4444"  # red

risk_bar_color = risk_color(org_risk)

st.markdown("### 🔍 Organization Risk Meter")
st.markdown(
    f"""
    <div style="background-color:#111827; padding:20px; border-radius:12px;">
        <div style="color:white; margin-bottom:8px;">Current Risk: <b>{org_risk} / 100</b></div>
        <div style="background-color:#374151; border-radius:999px; overflow:hidden; height:24px;">
            <div style="width:{org_risk}%; background:linear-gradient(90deg, #22c55e, #f97316, #ef4444); height:24px;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; color:#9CA3AF; font-size:12px; margin-top:4px;">
            <span>Low</span><span>Medium</span><span>High</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# --- High-risk user leaderboard & exfiltration modalities ---
left, right = st.columns([2, 1])

with left:
    st.subheader("🏆 High-Risk User Leaderboard")

    # Sort by risk score descending
    leaderboard = data.sort_values("risk_score", ascending=False).head(10)

    # Display a colorful table
    st.dataframe(
        leaderboard[["user_id", "department", "risk_score", "risk_level"]],
        use_container_width=True
    )

with right:
    st.subheader("📦 Exfiltration Modalities (Simulated)")

    # For demo: derive "exfil mode" from dominant feature
    def infer_mode(row):
        # Pick the feature with the highest normalized value
        vals = {
            "USB": row["usb_transfers"],
            "Web Upload": row["files_accessed"],
            "Email": row["external_emails"]
        }
        return max(vals, key=vals.get)

    data["exfil_mode"] = data.apply(infer_mode, axis=1)

    exfil_counts = data["exfil_mode"].value_counts().reset_index()
    exfil_counts.columns = ["mode", "count"]

    fig_pie = px.pie(
        exfil_counts,
        names="mode",
        values="count",
        color="mode",
        color_discrete_map={
            "USB": "#f97316",
            "Web Upload": "#3b82f6",
            "Email": "#22c55e"
        },
        title="Dominant Exfiltration Channel (by user)"
    )
    fig_pie.update_layout(showlegend=True)
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --- Risk distribution & department breakdown ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 Risk Score Distribution")
    fig_hist = px.histogram(
        data,
        x="risk_score",
        nbins=20,
        color="risk_level",
        color_discrete_map={"Low": "#22c55e", "Medium": "#f97316", "High": "#ef4444"},
        labels={"risk_score": "Risk Score"},
        title="Distribution of User Risk Scores"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with c2:
    st.subheader("🏢 Risk by Department")
    dept_risk = data.groupby("department")["risk_score"].mean().reset_index()
    fig_bar = px.bar(
        dept_risk,
        x="department",
        y="risk_score",
        color="risk_score",
        color_continuous_scale="Turbo",
        title="Average Risk Score per Department"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# --- User drill-down ---
st.subheader("🔎 User Drill-Down")

selected_user = st.selectbox(
    "Select a user to inspect:",
    options=data["user_id"].sort_values().unique()
)

user_row = data[data["user_id"] == selected_user].iloc[0]

# Show user summary in a nice card
st.markdown(
    f"""
    <div style="background-color:#111827; padding:16px; border-radius:12px; margin-bottom:12px;">
        <div style="color:#E5E7EB;"><b>User:</b> {user_row['user_id']}</div>
        <div style="color:#E5E7EB;"><b>Department:</b> {user_row['department']}</div>
        <div style="color:#E5E7EB;"><b>Risk Score:</b> {user_row['risk_score']} ({user_row['risk_level']})</div>
        <div style="color:#E5E7EB;"><b>Dominant Exfil Mode:</b> {user_row['exfil_mode']}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# Show radar-like bar chart of this user's features vs median
median_vals = data[feature_cols].median()

user_features = pd.DataFrame({
    "feature": feature_cols,
    "user_value": [user_row[col] for col in feature_cols],
    "median_value": [median_vals[col] for col in feature_cols]
})

fig_user = px.bar(
    user_features.melt(id_vars="feature", value_vars=["user_value", "median_value"],
                       var_name="type", value_name="value"),
    x="feature",
    y="value",
    color="type",
    barmode="group",
    color_discrete_map={"user_value": "#f97316", "median_value": "#4b5563"},
    title=f"Behavioral Profile: {selected_user} vs Median User"
)
st.plotly_chart(fig_user, use_container_width=True)

# Optional: show raw row for analysts
with st.expander("Show raw feature values"):
    st.write(user_row[["files_accessed", "usb_transfers", "external_emails", "failed_logins", "off_hours_ratio"]])
