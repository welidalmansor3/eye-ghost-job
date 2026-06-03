import streamlit as st
from groq import Groq
import os
import io
import re
import json
import PyPDF2
from docx import Document

# Logo URL (çalışan bir logo)
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/4284/4284787.png"

st.set_page_config(page_title="EYE Ghost Job AI", page_icon="👻", layout="wide")

# Dosya okuma
def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif uploaded_file.name.endswith('.docx'):
            doc = Document(io.BytesIO(uploaded_file.read()))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif uploaded_file.name.endswith('.txt'):
            text = uploaded_file.read().decode('utf-8')
    except Exception as e:
        st.error(f"Error: {e}")
    return text

# System prompt
SYSTEM_PROMPT = """You are EYE Ghost Job AI. Analyze the job posting. Return ONLY valid JSON. No markdown.

{
  "verdict": "Legitimate" | "Suspicious" | "Ghost Job" | "Scam",
  "confidence": "Low" | "Medium" | "High",
  "ghost_job_risk": 0-100,
  "scam_risk": 0-100,
  "key_risk_factors": ["factor1", "factor2"],
  "positive_signals": ["signal1", "signal2"],
  "recommendation": "Safe to Apply" | "Apply with Caution" | "Avoid",
  "reasoning": "brief explanation"
}"""

def extract_json(text):
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None

# Policy
POLICY = """
**Terms of Service**

By using EYE Ghost Job AI, you agree that this is an AI-powered analysis tool. 
Always verify job postings independently. No data is permanently stored.
All rights belong to GJ.AI Company.
"""

if "accepted" not in st.session_state:
    st.session_state.accepted = False

if not st.session_state.accepted:
    st.markdown("<h1 style='text-align: center;'>👻 EYE Ghost Job AI</h1>", unsafe_allow_html=True)
    st.warning("You must accept the Terms of Service.")
    with st.expander("📜 Terms of Service"):
        st.markdown(POLICY)
    if st.button("Accept and Continue"):
        st.session_state.accepted = True
        st.rerun()
else:
    if "count" not in st.session_state:
        st.session_state.count = 0

    with st.sidebar:
        st.image(LOGO_URL, width=80)
        st.markdown("---")
        api_key = st.text_input("Groq API Key", type="password")
        st.markdown("[Get free key](https://console.groq.com)")
        st.markdown("---")
        st.metric("Analyses", st.session_state.count)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Job Posting")
        job_text = st.text_area("Paste job description here:", height=300)
        
        st.subheader("📄 Your CV (Optional)")
        cv_file = st.file_uploader("Upload CV (PDF/DOCX/TXT)", type=['pdf', 'docx', 'txt'])
        cv_text = ""
        if cv_file:
            cv_text = extract_text_from_file(cv_file)
            if cv_text:
                st.success("CV uploaded!")

    with col2:
        st.subheader("🔍 Analysis Result")
        
        if st.button("🔍 Analyze", type="primary", use_container_width=True):
            if not api_key:
                st.error("Enter API key")
            elif not job_text.strip():
                st.warning("Paste a job posting")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        client = Groq(api_key=api_key)
                        user_msg = f"JOB:\n{job_text}"
                        if cv_text:
                            user_msg += f"\n\nCV:\n{cv_text}"
                        
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_msg}
                            ],
                            temperature=0.1,
                            max_tokens=2000
                        )
                        
                        data = extract_json(response.choices[0].message.content)
                        st.session_state.count += 1
                        
                        if data:
                            verdict = data.get("verdict", "Unknown")
                            if verdict == "Legitimate":
                                st.success(f"### ✅ VERDICT: {verdict}")
                            elif verdict == "Suspicious":
                                st.warning(f"### ⚠️ VERDICT: {verdict}")
                            else:
                                st.error(f"### 🚨 VERDICT: {verdict}")
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Ghost Risk", f"%{data.get('ghost_job_risk', 0)}")
                            c2.metric("Scam Risk", f"%{data.get('scam_risk', 0)}")
                            c3.metric("Confidence", data.get("confidence", "N/A"))
                            
                            st.markdown(f"**Recommendation:** {data.get('recommendation', 'N/A')}")
                            
                            if data.get("key_risk_factors"):
                                st.markdown("### 🚩 Risk Factors")
                                for f in data["key_risk_factors"]:
                                    st.markdown(f"- {f}")
                            
                            if data.get("positive_signals"):
                                st.markdown("### ✅ Positive Signals")
                                for s in data["positive_signals"]:
                                    st.markdown(f"- {s}")
                            
                            st.markdown(f"**Reasoning:** {data.get('reasoning', 'N/A')}")
                        else:
                            st.error("Could not parse response")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("<p style='text-align: center;'>© 2026 EYE Ghost Job AI | GJ.AI Company</p>", unsafe_allow_html=True)