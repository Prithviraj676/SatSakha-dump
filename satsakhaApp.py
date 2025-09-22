import streamlit as st
from satsakha_rag import answer_question   # import from your current script

st.set_page_config(page_title="SatSakha GeoAI Demo", layout="wide")

st.title("🌱 SatSakha: GeoAI Assistant for Farmers")

# User input box
question = st.text_input("Ask a question about Wardha region (code IN-MH-WRD):")

if st.button("Get Answer"):
    if question.strip():
        with st.spinner("Fetching data from Neo4j and generating answer..."):
            answer = answer_question(question, region_code="IN-MH-WRD")
        st.subheader("✅ SatSakha Answer")
        st.write(answer)
    else:
        st.warning("Please enter a question first.")
