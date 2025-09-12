import json
import os
from pathlib import Path

import streamlit as st

from model import analyze
from rag import rag_answer

# File paths
TICKETS_DIR = Path("tickets")
ANALYSIS_DIR = Path("analysis")
SAMPLE_FILE = TICKETS_DIR / "sample_tickets.json"
ANALYSIS_FILE = ANALYSIS_DIR / "analysis_tickets.json"

# Ensure dirs
TICKETS_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(file):
    if file.exists():
        with file.open("r") as f:
            return json.load(f)
    return []

def save_json(file, data):
    with file.open("w") as f:
        json.dump(data, f, indent=2)

def run_analysis(ticket):
    text = ticket["subject"] + " " + ticket["body"]
    raw = analyze(text)
    return {
        "tags": raw.topic_tags,
        "sentiment": raw.sentiment,
        "priority": raw.priority,
    }

# Badge styling
def badge(text, color="#7c5cff"):
    return f'<span style="background-color:{color};color:white;padding:4px 10px;border-radius:12px;margin-right:4px;font-size:12px;">{text}</span>'

priority_colors = {"P0": "#ff5f6d", "P1": "#ff9966", "P2": "#7c5cff"}
sentiment_colors = {
    "Frustrated": "#ff4c4c",
    "Angry": "#ff0000",
    "Curious": "#4cc9f0",
    "Neutral": "#999999",
    "Unknown": "#777777",
}

# Load base + analyzed tickets
sample_tickets = load_json(SAMPLE_FILE)
analyzed_tickets = load_json(ANALYSIS_FILE)

# Merge (new tickets only if not in analysis yet)
existing_subjects = {t["subject"] for t in analyzed_tickets}
for t in sample_tickets:
    if t["subject"] not in existing_subjects:
        analyzed_tickets.append(t)

# UI
st.title("Customer Support Copilot")

# Add new ticket
with st.sidebar:
    st.header("Add New Ticket")
    subj = st.text_input("Subject")
    body = st.text_area("Body")
    if st.button("Save Ticket"):
        if subj and body:
            new_ticket = {"subject": subj, "body": body}
            analyzed_tickets.append(new_ticket)
            save_json(ANALYSIS_FILE, analyzed_tickets)
            st.success("Ticket saved! Will be analyzed soon.")

# Dashboard
st.subheader("📋 Ticket Dashboard")

for i, t in enumerate(analyzed_tickets, 1):
    st.markdown(f"### Ticket {i}: {t['subject']}")
    st.write(t["body"])

    # If no analysis yet -> run now & save immediately
    if "analysis" not in t:
        with st.spinner("Analyzing..."):
            t["analysis"] = run_analysis(t)
            save_json(ANALYSIS_FILE, analyzed_tickets)

    analysis = t["analysis"]

    # Tags
    tag_html = " ".join([badge(tag, "#4cc9f0") for tag in analysis["tags"]])
    st.markdown(f"**Tags:** {tag_html}", unsafe_allow_html=True)

    # Sentiment
    st.markdown(
        f"**Sentiment:** {badge(analysis['sentiment'], sentiment_colors.get(analysis['sentiment'], '#777'))}",
        unsafe_allow_html=True,
    )

    # Priority
    st.markdown(
        f"**Priority:** {badge(analysis['priority'], priority_colors.get(analysis['priority'], '#7c5cff'))}",
        unsafe_allow_html=True,
    )
