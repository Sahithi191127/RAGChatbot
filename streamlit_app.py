"""Streamlit deployment entrypoint — calls app.rag.chat in-process."""

from __future__ import annotations

import streamlit as st

from app.rag import chat
from app.security import contains_pii, validate_message_length
from config.loader import get_corpus_config

st.set_page_config(page_title="FundFacts Assistant", page_icon="📊", layout="centered")

config = get_corpus_config()

st.title("FundFacts Assistant")
st.caption("Facts-only FAQ for five HDFC schemes on Groww. No investment advice.")

with st.expander("Supported schemes", expanded=False):
    for scheme in config.schemes:
        st.markdown(f"- {scheme.scheme_name}")

EXAMPLES = [
    "What is the expense ratio of HDFC Mid Cap Fund Direct Growth?",
    "What is the exit load on HDFC Defence Fund Direct Growth?",
    "Who manages HDFC Small Cap Fund Direct Growth?",
]

for question in EXAMPLES:
    if st.button(question, key=question):
        st.session_state["pending"] = question

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citation"):
            label = msg.get("citation_label", "Source")
            st.markdown(f"[{label}]({msg['citation']})")
        if msg.get("last_updated"):
            st.caption(f"Last updated from sources: {msg['last_updated']}")

prompt = st.session_state.pop("pending", None) or st.chat_input(
    "Ask a factual question about one of the supported schemes…"
)

if prompt:
    try:
        validate_message_length(prompt)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if contains_pii(prompt):
        st.error("Please remove personal identifiers (PAN, Aadhaar, email, phone, etc.).")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            response = chat(prompt)
        st.markdown(response.answer)
        citation_label = "Learn more" if response.is_refusal else "Source"
        if response.citation_url:
            st.markdown(f"[{citation_label}]({response.citation_url})")
        st.caption(f"Last updated from sources: {response.last_updated}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "citation": str(response.citation_url) if response.citation_url else None,
            "citation_label": citation_label,
            "last_updated": str(response.last_updated),
        }
    )
    st.rerun()

st.warning("Do not enter PAN, Aadhaar, email, phone, or account numbers.", icon="⚠️")
st.error("DISCLAIMER: Facts-only. No investment advice.", icon="ℹ️")
