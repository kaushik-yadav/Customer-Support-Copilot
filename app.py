import json
from pathlib import Path

import streamlit as st

from model import analyze
from rag_system.pipeline import rag_answer

# File paths
TICKETS_DIR = Path("tickets")
ANALYSIS_DIR = Path("analysis")
SAMPLE_FILE = TICKETS_DIR / "sample_tickets.json"
ANALYSIS_FILE = ANALYSIS_DIR / "analysis_tickets.json"
LAST_ID_FILE = ANALYSIS_DIR / "last_id.txt"

# Ensure dirs
TICKETS_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


# Helpers
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


def get_next_ticket_id(analyzed_tickets):
    """Generates next TICKET-X id using last_id.txt or fallback to last JSON entry."""
    if LAST_ID_FILE.exists():
        last_id = int(LAST_ID_FILE.read_text().strip())
    else:
        if analyzed_tickets:
            last_ticket = analyzed_tickets[-1]
            if "id" in last_ticket and last_ticket["id"].startswith("TICKET-"):
                last_id = int(last_ticket["id"].split("-")[1])
            else:
                last_id = 244
        else:
            last_id = 244

    next_id = last_id + 1
    LAST_ID_FILE.write_text(str(next_id))
    return f"TICKET-{next_id}"

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

# Ticket Answer + Human Feedback
def handle_ticket_answer(ticket_id):
    """Stable Streamlit ticket handler with RAG answer and feedback."""
    testing = True
    tickets = load_json(ANALYSIS_FILE)
    ticket_index = next((i for i, t in enumerate(tickets) if t["id"] == ticket_id), None)
    if ticket_index is None:
        st.error("Ticket not found!")
        return
    ticket = tickets[ticket_index]

    # Skip RAG if status is Resolved
    if ticket.get("status") == "Resolved":
        st.info("Ticket already resolved and added to ticket dashboard")
        return

    # Keys for session_state
    answer_key = f"answer_{ticket_id}"
    feedback_key = f"feedback_{ticket_id}"

    tags = ticket.get("analysis", {}).get("tags", [])

    # Case 1: Already answered → just use stored answer
    if ticket.get("status") == "Answered" and ticket.get("answer"):
        st.session_state[answer_key] = ticket["answer"]

    # Case 2: Open → run RAG if not already stored
    elif ticket.get("status") == "Open" or answer_key not in st.session_state:
        if not tags:
            st.warning("Ticket analysis not ready yet. Please try again in a moment.")
            return

        # Only run RAG for supported tags
        if any(tag in ["How-to", "Product", "Best practices", "API/SDK", "SSO"] for tag in tags):
            with st.spinner("Finding answer..."):
                try:
                    rag_response = rag_answer(ticket.get("subject", "") + " " + ticket.get("body", ""))
                except Exception as e:
                    st.error(f"RAG failed: {e}")
                    rag_response = None

            st.session_state[answer_key] = rag_response
            ticket["answer"] = rag_response
            ticket["status"] = "Answered" if rag_response else "Pending"

        else:
            st.session_state[answer_key] = None
            ticket["answer"] = None
            ticket["status"] = "Pending"

        tickets[ticket_index] = ticket
        save_json(ANALYSIS_FILE, tickets)

    # ---- Display answer (only once) ----
    stored_answer = st.session_state.get(answer_key)
    if stored_answer:
        st.info(stored_answer)
    else:
        if any(tag in ["How-to", "Product", "Best practices", "API/SDK", "SSO"] for tag in tags):
            st.warning("No answer found in knowledge base.")
        else:
            st.warning(f"ℹ️ Ticket classified as '{', '.join(tags)}'; routed to appropriate team and ticket raised in ticket dashboard")
            ticket['answer'] = f"Ticket classified as '{', '.join(tags)}'; routed to appropriate team"
            ticket['status'] = 'Rerouted'
            tickets[ticket_index] = ticket
            save_json(ANALYSIS_FILE, tickets)
            testing = False

    # ---- Feedback section ----
    if testing and stored_answer:
        st.session_state.setdefault(feedback_key, None)

        if st.session_state.get(feedback_key) is None:
            col1, col2 = st.columns(2)
            yes_clicked = col1.button("✅ YES, this helped", key=f"yes_{ticket_id}")
            no_clicked  = col2.button("❌ No, still an issue", key=f"no_{ticket_id}")

            if yes_clicked:
                st.session_state[feedback_key] = "resolved"
                ticket["status"] = "Resolved"
                tickets[ticket_index] = ticket
                save_json(ANALYSIS_FILE, tickets)
                st.success("✅ Ticket marked as Resolved and added to the dashboard.")
                st.rerun()

            if no_clicked:
                st.session_state[feedback_key] = "rerouted"
                ticket["status"] = "Rerouted"
                tickets[ticket_index] = ticket
                save_json(ANALYSIS_FILE, tickets)
                st.warning("❌ Ticket has been Rerouted and added to the dashboard.")
                st.rerun()
        else:
            if st.session_state[feedback_key] == "resolved":
                st.success("✅ Ticket marked as Resolved and added to the dashboard.")
            else:
                st.warning("❌ Ticket has been Rerouted and added to the dashboard.")


# Load base + analyzed tickets
sample_tickets = load_json(SAMPLE_FILE)
analyzed_tickets = load_json(ANALYSIS_FILE)

# Merge (sample tickets only if not already analyzed)
existing_subjects = {t["subject"] for t in analyzed_tickets}
for t in sample_tickets:
    if t["subject"] not in existing_subjects:
        t["id"] = get_next_ticket_id(analyzed_tickets)
        analyzed_tickets.append(t)

# Initialize session state
if "analyzed_tickets" not in st.session_state:
    st.session_state.analyzed_tickets = analyzed_tickets
if "new_ticket_submitted" not in st.session_state:
    st.session_state.new_ticket_submitted = False
if "current_ticket_id" not in st.session_state:
    st.session_state.current_ticket_id = None

# NAVIGATION
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to:", ["📋 Ticket Dashboard", "➕ Add a Ticket"])

st.title("Customer Support Copilot")


# Ticket Dashboard
if page == "📋 Ticket Dashboard":
    st.subheader("Ticket Dashboard")

    for i, t in enumerate(analyzed_tickets, 1):
        st.markdown(f"### {t['id']}: {t['subject']}")
        st.write(t["body"])

        # Ensure analysis exists
        if "analysis" not in t:
            with st.spinner("Analyzing..."):
                t["analysis"] = run_analysis(t)
                t.setdefault("status", "Open")
                save_json(ANALYSIS_FILE, analyzed_tickets)

        analysis = t.get("analysis", {})

        # Tags, Sentiment, Priority
        st.markdown(f"**Tags:** {' '.join([badge(tag, '#4cc9f0') for tag in analysis.get('tags', [])])}", unsafe_allow_html=True)
        st.markdown(f"**Sentiment:** {badge(analysis.get('sentiment','Unknown'), sentiment_colors.get(analysis.get('sentiment','Unknown'), '#777'))}", unsafe_allow_html=True)
        st.markdown(f"**Priority:** {badge(analysis.get('priority','P2'), priority_colors.get(analysis.get('priority','P2'), '#7c5cff'))}", unsafe_allow_html=True)
        st.markdown(f"**Status:** {t.get('status','Open')}")

        # Determine button text
        if t.get("status") == "Open":
            btn_text = f"💡 Answer {t['id']}"
        else:
            btn_text = f"💡 See Assistant's Answer"

        show_key = f"show_answer_{t['id']}"
        if show_key not in st.session_state:
            st.session_state[show_key] = False

        # Show the answer button for all tickets except Open's feedback handled in handle_ticket_answer
        if st.button(btn_text, key=f"answer_btn_{t['id']}"):
            st.session_state[show_key] = True
        if st.session_state[show_key]:
            ticket_status = t.get("status")

            if ticket_status in ["Open", "Answered"]:
                # Let handle_ticket_answer handle both RAG + feedback
                handle_ticket_answer(t["id"])

            elif ticket_status in ["Rerouted", "Resolved"]:
                # Just show stored answer, no feedback
                stored_answer = t.get("answer")
                if stored_answer:
                    st.info(stored_answer)
                else:
                    st.warning("No answer available for this ticket.")




# Add a Ticket
elif page == "➕ Add a Ticket":
    st.subheader("Add a New Ticket")

    if not st.session_state.new_ticket_submitted:
        subj = st.text_input("Subject", key="new_ticket_subject")
        body = st.text_area("Body", key="new_ticket_body")

        if st.button("Submit Ticket", key="submit_ticket_btn"):
            if not subj or not body:
                st.warning("Please provide both subject and body.")
            else:
                ticket_id = get_next_ticket_id(st.session_state.analyzed_tickets)
                new_ticket = {
                    "id": ticket_id,
                    "subject": subj,
                    "body": body,
                    "status": "Open",
                }

                # Run analysis
                with st.spinner("Analyzing ticket..."):
                    new_ticket["analysis"] = run_analysis(new_ticket)

                # Save ticket in session + JSON
                st.session_state.analyzed_tickets.append(new_ticket)
                save_json(ANALYSIS_FILE, st.session_state.analyzed_tickets)
                
                # Set state to show the analysis and feedback
                st.session_state.new_ticket_submitted = True
                st.session_state.current_ticket_id = ticket_id
                st.rerun()
    
    else:
        # Show analysis and feedback for the newly submitted ticket
        ticket_id = st.session_state.current_ticket_id
        ticket = next((t for t in st.session_state.analyzed_tickets if t["id"] == ticket_id), None)
        
        if ticket:
            # Display analysis
            analysis = ticket.get("analysis", {})
            st.markdown(f"**Tags:** {' '.join([badge(tag, '#4cc9f0') for tag in analysis.get('tags', [])])}", unsafe_allow_html=True)
            st.markdown(f"**Sentiment:** {badge(analysis.get('sentiment','Unknown'), sentiment_colors.get(analysis.get('sentiment','Unknown'), '#777'))}", unsafe_allow_html=True)
            st.markdown(f"**Priority:** {badge(analysis.get('priority','P2'), priority_colors.get(analysis.get('priority','P2'), '#7c5cff'))}", unsafe_allow_html=True)
            st.markdown(f"**Status:** {ticket.get('status', 'Open')}")
            
            # Handle the answer and feedback
            handle_ticket_answer(ticket_id)
            
            # Add a button to add another ticket
            if st.button("Add Another Ticket", key="add_another_ticket_btn"):
                st.session_state.new_ticket_submitted = False
                st.session_state.current_ticket_id = None
                st.rerun()
        else:
            st.error("Ticket not found!")
            st.session_state.new_ticket_submitted = False