"""Streamlit chat interface for the Healthcare Equipment Support Chatbot.

Run with:  streamlit run app.py
"""
import time

import streamlit as st

import config
from src import auth, db, router
from src import n8n_client

st.set_page_config(page_title="MediCorp Support Chatbot", page_icon="🩺",
                   layout="centered")

# Ensure the DB exists (schema + seed) on first run.
db.init_db()


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------------------------------- #
# Login screen
# --------------------------------------------------------------------------- #
def login_view():
    st.title("🩺 MediCorp Support")
    st.caption("Secure customer support for medical-equipment clients.")
    st.info("Demo logins — St. Mary Hospital: `admin@stmary-hospital.org` / `CLI-1001` · "
            "Green Valley Clinic: `ops@greenvalley-clinic.com` / `CLI-1002`")
    with st.form("login"):
        email = st.text_input("Email")
        client_id = st.text_input("Client ID")
        submitted = st.form_submit_button("Verify & continue")
    if submitted:
        user = auth.verify_user(email, client_id)
        if user:
            st.session_state.user = user
            st.session_state.messages = [{
                "role": "assistant",
                "text": f"Hello {user.get('contact_name') or user['org_name']}! "
                        f"You're verified for {user['org_name']}. How can I help — "
                        f"orders, warranty, complaints, invoices, spare parts, manuals, "
                        f"certificates, or scheduling?",
                "meta": None,
            }]
            st.rerun()
        else:
            st.error("Identity could not be verified. Check the email and client ID.")


# --------------------------------------------------------------------------- #
# Chat screen
# --------------------------------------------------------------------------- #
def chat_view():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"**Signed in:** {user['org_name']}")
        st.markdown(f"**Client ID:** `{user['client_id']}`")
        st.markdown(f"**AI provider:** `{config.resolve_provider()}`")
        st.markdown(f"**Orchestration:** `{'n8n' if config.N8N_WEBHOOK_URL else 'direct'}`")
        if st.button("Log out"):
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()
        st.divider()
        st.caption("The assistant only sees your organization's records and will "
                   "say \"I don't know\" when an answer isn't available.")

    st.title("🩺 MediCorp Support")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])
            if msg.get("meta"):
                st.caption(msg["meta"])

    prompt = st.chat_input("Type your question…")
    if prompt:
        st.session_state.messages.append({"role": "user", "text": prompt, "meta": None})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Looking that up…"):
                # Route through n8n if configured; otherwise call the engine directly.
                if config.N8N_WEBHOOK_URL:
                    resp = n8n_client.ask(prompt, user)
                else:
                    resp = router.handle_message(prompt, user)
            st.markdown(resp.text)
            meta_bits = [f"intent: {resp.intent}", f"source: {resp.data_source}",
                         f"{resp.latency_ms} ms"]
            if resp.sources:
                meta_bits.append("docs: " + ", ".join(resp.sources))
            meta = " · ".join(meta_bits)
            st.caption(meta)

        st.session_state.messages.append(
            {"role": "assistant", "text": resp.text, "meta": meta})


# --------------------------------------------------------------------------- #
if st.session_state.user is None:
    login_view()
else:
    chat_view()
