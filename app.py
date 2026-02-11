import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="Port Ops • Video + Positioning Twin", layout="wide")

st.title("🚢 Container Unloading • Video + Positioning Twin")
st.caption("Left: port operations video | Right: simulated container/crane positioning telemetry (demo).")

# -----------------------------
# Load videos from repo
# -----------------------------
VIDEO_DIR = Path("videos")
if not VIDEO_DIR.exists():
    st.error("❌ Missing folder: /videos. Create it and add MP4 files.")
    st.stop()

video_files = sorted([p for p in VIDEO_DIR.glob("*.mp4")])
if not video_files:
    st.error("❌ No MP4 files found inside /videos.")
    st.stop()

# -----------------------------
# Controls
# -----------------------------
with st.sidebar:
    st.header("Controls")
    autoplay = st.toggle("Autoplay videos", value=False)
    autoplay_seconds = st.slider("Autoplay advance every (seconds)", 5, 45, 12, 1)
    show_trail = st.toggle("Show position trail", value=True)
    jitter = st.slider("Telemetry noise (demo realism)", 0.0, 2.0, 0.6, 0.1)

    st.divider()
    st.subheader("Video selection")
    if "video_idx" not in st.session_state:
        st.session_state.video_idx = 0

    chosen = st.selectbox(
        "Pick a video",
        options=list(range(len(video_files))),
        format_func=lambda i: f"{i+1}. {video_files[i].name}",
        index=st.session_state.video_idx
    )
    st.session_state.video_idx = chosen

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("⏮ Prev"):
            st.session_state.video_idx = (st.session_state.video_idx - 1) % len(video_files)
    with colB:
        if st.button("▶ Next"):
            st.session_state.video_idx = (st.session_state.video_idx + 1) % len(video_files)
    with colC:
        if st.button("🔁 Reset"):
            st.session_state.video_idx = 0

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([1.35, 1])

# -----------------------------
# Left: Video player
# -----------------------------
current_video = video_files[st.session_state.video_idx]

with left:
    st.subheader("🎬 Live Operations Feed")
    st.write(f"**Now playing:** {current_video.name}")
    st.video(str(current_video))

# -----------------------------
# Right: “Amazing positioning” graph
# -----------------------------
def make_position_series(seed: int, n: int = 140, noise: float = 0.6):
    """
    Generate a smooth-ish path that looks like crane/container movement:
    - x: along quay
    - y: along yard
    - z: hoist height
    """
    rng = np.random.default_rng(seed)

    t = np.linspace(0, 1, n)

    # Base motion (curvy path)
    x = 20 + 60 * t + 8 * np.sin(2 * np.pi * t)
    y = 10 + 30 * np.sin(np.pi * t) + 5 * np.sin(4 * np.pi * t)

    # Hoist profile: lift -> move -> lower
    z = 2 + 18 * np.sin(np.pi * t) ** 1.6

    # Add noise to feel “sensor-like”
    x = x + rng.normal(0, noise, size=n)
    y = y + rng.normal(0, noise, size=n)
    z = z + rng.normal(0, noise * 0.25, size=n)

    return t, x, y, z

# Seed varies per video so each looks different
seed = abs(hash(current_video.name)) % (10**6)
t, x, y, z = make_position_series(seed=seed, noise=jitter)

# Use a “time cursor” that advances if autoplay is on
if "cursor" not in st.session_state:
    st.session_state.cursor = 0

if st.session_state.get("last_video") != current_video.name:
    st.session_state.last_video = current_video.name
    st.session_state.cursor = 0

# Autoplay cursor advance
if autoplay:
    # advance cursor once per rerun tick
    st.session_state.cursor = min(st.session_state.cursor + 4, len(t) - 1)
    time.sleep(0.15)
    st.rerun()

cursor = st.session_state.cursor

# Build a slick dual-panel chart:
# Top: XY yard map with current point + trail
# Bottom: Height over time with current marker
with right:
    st.subheader("📍 Positioning Twin (Simulated Telemetry)")

    # KPIs (for client wow)
    c1, c2, c3 = st.columns(3)
    c1.metric("Container ID", f"CONT-{(seed % 9000) + 1000}")
    c2.metric("Hoist Height (m)", f"{z[cursor]:.1f}")
    c3.metric("Status", "UNLOADING" if cursor < len(t) * 0.7 else "PLACED")

    fig = go.Figure()

    # Trail
    if show_trail and cursor > 2:
        fig.add_trace(go.Scatter(
            x=x[:cursor],
            y=y[:cursor],
            mode="lines",
            name="Path",
            line=dict(width=3),
            hoverinfo="skip",
        ))

    # Current position marker
    fig.add_trace(go.Scatter(
        x=[x[cursor]],
        y=[y[cursor]],
        mode="markers+text",
        name="Current",
        marker=dict(size=16),
        text=["●"],
        textposition="middle center",
        hovertemplate="X=%{x:.1f}<br>Y=%{y:.1f}<extra></extra>",
    ))

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Quay Axis (X)",
        yaxis_title="Yard Axis (Y)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Height chart
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=t, y=z, mode="lines", name="Hoist Height",
        hovertemplate="t=%{x:.2f}<br>z=%{y:.1f}m<extra></extra>"
    ))
    fig2.add_trace(go.Scatter(
        x=[t[cursor]], y=[z[cursor]], mode="markers",
        marker=dict(size=12),
        hovertemplate="NOW<br>z=%{y:.1f}m<extra></extra>",
        showlegend=False
    ))
    fig2.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Progress",
        yaxis_title="Height (m)"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Manual advance button for demos
    colX, colY = st.columns([1, 2])
    with colX:
        if st.button("⏩ Advance telemetry"):
            st.session_state.cursor = min(st.session_state.cursor + 8, len(t) - 1)
            st.rerun()
    with colY:
        st.progress(int((cursor / (len(t) - 1)) * 100))
