import json
import os

import streamlit as st

# Load JSON tickets
tickets_file = "tickets/sample_tickets.json"

def load_tickets():
    if os.path.exists(tickets_file):
        with open(tickets_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tickets(tickets):
    with open(tickets_file, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2)

tickets = load_tickets()

# Page config
st.set_page_config(page_title="Customer Support Copilot", layout="wide")

# Custom CSS for styling (using Card style styling)
st.markdown("""
    <style>
    .app-title {
        text-align: center;
        font-size: 36px;
        font-weight: 700;
        color: #2563EB;
        margin-bottom: 30px;
    }
    .card {
        background-color: #ffffff;
        border-radius: 15px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        padding: 20px;
        margin: 10px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 18rem;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0px 8px 20px rgba(0,0,0,0.15);
    }
    .ticket-id {
        font-size: 14px;
        font-weight: bold;
        color: #6B7280;
        margin-bottom: 1rem;
    }
    .ticket-subject {
        font-size: 20px;
        font-weight: 600;
        color: #111827;
        margin-bottom: 1rem;
        margin-top: 1rem;
    }
    .ticket-body {
        font-size: 16px;
        color: #374151;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)

# App title
st.markdown('<div class="app-title">Customer Support Copilot</div>', unsafe_allow_html=True)

# Adding new ticket
with st.expander("+ Add a New Ticket", expanded=False):
    with st.form("new_ticket_form", clear_on_submit=True):
        subject = st.text_input("Subject")
        body = st.text_area("Body")
        submitted = st.form_submit_button("Add Ticket")

        if submitted:
            ticket_number = int(tickets[-1]["id"].split("-")[1]) + 1
            new_ticket = {
                "id": f"TICKET-{ticket_number}",
                "subject": subject if subject.strip() else "Untitled",
                "body": body if body.strip() else "No content"
            }
            tickets.append(new_ticket)
            save_tickets(tickets)
            st.success(f"Ticket {new_ticket['id']} added successfully!")
            st.rerun()

# Display cards (2 columns)
if tickets:
    cols = st.columns(2)
    for i, ticket in enumerate(tickets):
        with cols[i % 2]:
            st.markdown(f"""
                <div class="card">
                    <div class="ticket-id">#{ticket.get("id", "Unknown")}</div>
                    <div class="ticket-subject">{ticket.get("subject", "No Subject")}</div>
                    <div class="ticket-body">{ticket.get("body", "No Body")}</div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.warning("No tickets found. Please check if 'tickets/sample_tickets.json' exists.")
