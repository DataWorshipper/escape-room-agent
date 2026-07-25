import glob
import html
import json
import os
import re
import time

import streamlit as st

st.set_page_config(page_title="Escape Room Agents", page_icon="🚪", layout="wide")

STYLE = """
<style>
.stApp { background: radial-gradient(circle at 50% 0%, #1a0938, #0a0417 70%); }
.title { font-family:'Courier New',monospace; color:#00e5ff; text-align:center; font-size:2.4rem; font-weight:bold; letter-spacing:4px; text-shadow:0 0 14px #00e5ff; margin-bottom:0; }
.subtitle { font-family:'Courier New',monospace; color:#ff3fbf; text-align:center; margin-top:2px; letter-spacing:2px; }
.hud { display:flex; justify-content:space-around; align-items:center; background:#160a30; border:2px solid #00e5ff; border-radius:14px; padding:16px; margin:14px 0; box-shadow:0 0 22px rgba(0,229,255,.35); font-family:'Courier New',monospace; }
.hud .label { font-size:.72rem; color:#8a8ab0; letter-spacing:2px; }
.hud .big { font-size:1.7rem; color:#fff; margin-top:4px; }
.won { color:#5dff9b !important; text-shadow:0 0 12px #5dff9b; }
.lost { color:#ff5d6c !important; text-shadow:0 0 12px #ff5d6c; }
.feed { display:flex; flex-direction:column; gap:10px; padding:6px; }
.row { display:flex; }
.row.left { justify-content:flex-start; }
.row.right { justify-content:flex-end; }
.bubble { max-width:72%; padding:10px 14px; border-radius:16px; font-family:'Courier New',monospace; font-size:.86rem; line-height:1.4; }
.bubble.operator { background:#062830; border:1px solid #00e5ff; color:#c9f7ff; border-bottom-left-radius:3px; }
.bubble.expert { background:#2a0824; border:1px solid #ff3fbf; color:#ffd6f2; border-bottom-right-radius:3px; }
.bubble.operator.active { box-shadow:0 0 18px #00e5ff; }
.bubble.expert.active { box-shadow:0 0 18px #ff3fbf; }
.who { font-size:.68rem; opacity:.7; margin-bottom:5px; letter-spacing:1px; text-transform:uppercase; }
.tool { color:#ffd166; font-weight:bold; }
.result { color:#7CFC97; }
.think { font-style:italic; opacity:.85; }
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)
st.markdown("<div class='title'>ESCAPE ROOM AGENTS</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>two AIs · one MCP server · one way out</div>", unsafe_allow_html=True)


def load_logs():
    return sorted(glob.glob(os.path.join("logs", "*.json")), reverse=True)


def short(text, n=200):
    return text if len(text) <= n else text[:n] + " ..."


def total_modules(events):
    total = 1
    for event in events:
        for action in event["actions"]:
            match = re.search(r"Module \d+ of (\d+)", action["result"])
            if match:
                total = max(total, int(match.group(1)))
    return total


def state_at(events, idx):
    strikes = 0
    module = 1
    status = "playing"
    for event in events[:idx + 1]:
        status = event["status"]
        for action in event["actions"]:
            result = action["result"]
            match = re.search(r"Module (\d+) of \d+", result)
            if match:
                module = int(match.group(1))
            if result.startswith("Wrong"):
                strikes += 1
    return strikes, module, status


def bubble_html(event, active):
    role = event["role"]
    side = "left" if role == "operator" else "right"
    icon = "🔧" if role == "operator" else "📖"
    lines = []
    if event["said"]:
        lines.append(f"<div class='think'>{html.escape(event['said'])}</div>")
    for action in event["actions"]:
        arg_text = ", ".join(f"{k}: {v}" for k, v in action["args"].items())
        head = f"<span class='tool'>{html.escape(action['tool'])}</span>"
        if arg_text:
            head += " " + html.escape(short(arg_text, 240))
        lines.append(head)
        lines.append(f"<div class='result'>{html.escape(short(action['result']))}</div>")
    cls = "active" if active else ""
    return f"<div class='row {side}'><div class='bubble {role} {cls}'><div class='who'>{icon} {role} · turn {event['turn']}</div>{'<br>'.join(lines)}</div></div>"


files = load_logs()
if not files:
    st.warning("No logs yet. Run  python orchestrator.py  first, then refresh.")
    st.stop()

choice = st.selectbox("Pick a run", files, index=0)
if st.session_state.get("file") != choice:
    st.session_state.file = choice
    st.session_state.idx = 0

trace = json.load(open(choice, "r", encoding="utf-8"))
events = trace["events"]
meta = trace["meta"]
n = len(events) - 1
total = total_modules(events)

if "idx" not in st.session_state:
    st.session_state.idx = 0
st.session_state.idx = min(st.session_state.idx, n)

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
if c1.button("⏮ Restart", use_container_width=True):
    st.session_state.idx = 0
if c2.button("◀ Prev", use_container_width=True):
    st.session_state.idx = max(0, st.session_state.idx - 1)
if c3.button("Next ▶", use_container_width=True):
    st.session_state.idx = min(n, st.session_state.idx + 1)
auto = c4.toggle("Auto-play ▶")

idx = st.session_state.idx
st.progress((idx + 1) / (n + 1), text=f"Turn {idx} / {n}")

strikes, module, status = state_at(events, idx)
marks = "❌ " * strikes + "⬜ " * max(0, 3 - strikes)
if status == "won":
    banner = "<span class='won'>✅ ESCAPED</span>"
elif status == "lost":
    banner = "<span class='lost'>💀 TRAPPED</span>"
else:
    banner = "🎮 IN PROGRESS"

st.markdown(
    f"<div class='hud'>"
    f"<div><div class='label'>MODULE</div><div class='big'>{module} / {total}</div></div>"
    f"<div><div class='label'>STRIKES</div><div class='big'>{marks}</div></div>"
    f"<div><div class='label'>STATUS</div><div class='big'>{banner}</div></div>"
    f"</div>",
    unsafe_allow_html=True,
)

window = events[max(0, idx - 7):idx + 1]
feed = "".join(bubble_html(event, event is events[idx]) for event in window)
st.markdown(f"<div class='feed'>{feed}</div>", unsafe_allow_html=True)

st.caption(f"model: {meta.get('model', '?')}  ·  result: {meta.get('result', '?')}  ·  turns: {meta.get('turns', '?')}  ·  tokens: {meta.get('total_tokens', '?')}")

if auto and idx < n:
    time.sleep(0.9)
    st.session_state.idx = idx + 1
    st.rerun()