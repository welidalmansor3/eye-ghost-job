import os
import json
import re
import time
import streamlit as st
import requests
from groq import Groq
import io
import PyPDF2
from docx import Document

# LOGO URL
LOGO_URL = "https://z-cdn-media.chatglm.cn/files/97efb701-480f-41e8-a54d-d828ce634224.jpeg?auth_key=1880000279-e3e53963895d4cb2b17766ad29dd2480-0-3f2ced5648a41f4923250c661dc275fd"

def extract_file_text(uploaded_file):
    text = ""
    if uploaded_file is not None:
        file_type = uploaded_file.name.split('.')[-1].lower()
        try:
            if file_type == 'pdf':
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + "\n"
            elif file_type == 'docx':
                doc = Document(io.BytesIO(uploaded_file.read()))
                for para in doc.paragraphs: text += para.text + "\n"
            elif file_type == 'txt': text = uploaded_file.read().decode('utf-8')
        except Exception as e: st.error(f"⚠️ Error reading file: {e}")
    return text

# Streamlit Cloud dosya sisteminde kayıp olmaması için istatistikleri session_state'te tutuyoruz
if "global_stats" not in st.session_state:
    st.session_state.global_stats = {"visits": 0, "analyses": 0, "scams": 0}

def load_stats():
    return st.session_state.global_stats

def save_stats(stats):
    st.session_state.global_stats = stats

if "visit_counted" not in st.session_state:
    st.session_state.visit_counted = True
    stats = load_stats(); stats["visits"] += 1; save_stats(stats)

if "analysis_count" not in st.session_state: st.session_state.analysis_count = 0
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "lock_time" not in st.session_state: st.session_state.lock_time = None

SYSTEM_PROMPT = """You are Ghost Job Detector AI v2 & Career Copilot. You must output ALL TEXT IN ENGLISH. Respond with ONLY a valid JSON object. No markdown backticks:
{
  "verdict_emoji": "🟢" | "🟡" | "🟠" | "🔴",
  "verdict_label": "Legitimate" | "Suspicious" | "Ghost Job Risk" | "Potential Scam",
  "ghost_job_risk": <integer 0-100>,
  "scam_risk": <integer 0-100>,
  "authenticity_score": <integer 0-100>,
  "confidence": "Low" | "Medium" | "High",
  "key_risk_factors": ["<factor 1>", "<factor 2>"],
  "positive_signals": ["<signal 1>", "<signal 2>"],
  "external_evidence_summary": "No external evidence provided.",
  "final_reasoning": "<detailed logical explanation IN ENGLISH>",
  "recommended_action": "Safe to Apply" | "Apply with Caution" | "Investigate Further" | "Avoid",
  "match_score": <integer 0-100>,
  "matching_skills": ["<skill 1 in CV>"],
  "missing_skills": ["<skill 1 missing>"]
}"""

def extract_json(text):
    if "```json" in text: text = text.split("```json")[1].split("```")[0]
    elif "```" in text: text = text.split("```")[1].split("```")[0]
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match: return json.loads(match.group(0))
    else: raise ValueError("No JSON found.")

POLICY_TEXT = """
**Terms of Service & Privacy Policy**

**1. Acceptance of Terms**
By accessing this platform, you agree to be bound by these Terms. If you do not agree, do not use the platform.

**2. Intellectual Property & Copyrights**
All rights, intellectual property (IP) rights, algorithms, and underlying code belong exclusively to **Welid Almansor**. 
This application is developed by **GJ.AI (Great Job AI) Company**, and all copyrights are strictly reserved by GJ.AI. Unauthorized reproduction is prohibited.

**3. Logo & Trademark Protection**
The GJ.AI logo is 100% owned by GJ.AI (Great Job AI Company). Any unauthorized use, reproduction, or distribution of the logo in any context is strictly prohibited. GJ.AI reserves the full legal right to open a lawsuit and take legal action against any individual or entity that uses the logo without explicit written permission.

**4. Use of the Service**
The Service provides AI-generated probabilistic analysis for informational purposes only.

**5. Privacy & Data Handling**
Job postings and CVs are processed securely and not permanently stored.

By checking the box below, you confirm your agreement.
"""

st.set_page_config(page_title="EYE Ghost Job AI", page_icon="👻", layout="wide")
if "policy_accepted" not in st.session_state: st.session_state.policy_accepted = False

if not st.session_state.policy_accepted:
    st.markdown("<h1 style='text-align: center; color: #FFFFFF;'>👻 EYE Ghost Job AI</h1><p style='text-align: center; color: #AAAAAA;'>Global Job Authenticity Auditor & CV Matcher</p><hr style='border: 1px solid #333333;'>", unsafe_allow_html=True)
    st.warning("⚠️ **Authorization Required:** You must accept the Terms of Service.")
    with st.expander("📜 READ: Terms of Service & Privacy Policy", expanded=True): st.markdown(POLICY_TEXT)
    agreed = st.checkbox("I have read and I agree to the Terms of Service and Privacy Policy.")
    if st.button("🔓 Access Platform", disabled=not agreed, type="primary", use_container_width=True): st.session_state.policy_accepted = True; st.rerun()
else:
    st.markdown("<h1 style='text-align: center; color: #FFFFFF;'>👻 EYE Ghost Job AI</h1><p style='text-align: center; color: #AAAAAA;'>Detect scams, analyze legitimacy, and match your CV.</p><hr style='border: 1px solid #333333;'>", unsafe_allow_html=True)
    with st.sidebar:
        st.image(LOGO_URL, use_container_width=True); st.markdown("---")
        st.header("⚙️ Settings"); api_key_input = st.text_input("Groq API Key (Free)", type="password")
        st.markdown("---"); st.header("📖 How to Get Free API Key")
        with st.expander("👀 Step-by-Step Guide", expanded=True): st.markdown("👀 Go to [Groq Console](https://console.groq.com) -> Log In -> API Keys -> Create API Key -> Copy `gsk_...` -> Paste above.")
        st.header("🕵️ External Evidence (Optional)"); external_evidence = st.text_area("Company news, links, etc.", height=100)
        st.markdown("---"); st.header("📈 Platform Statistics"); current_stats = load_stats()
        st.metric("👥 Total Visitors", current_stats["visits"]); st.metric("🔍 Analyses Performed", current_stats["analyses"]); st.metric("🚨 Scams/Ghost Jobs Detected", current_stats["scams"])
        st.markdown("---")
        if st.button("🔒 Revoke Policy Consent"): st.session_state.policy_accepted = False; st.rerun()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Job Post Input"); job_post = st.text_area("Paste the job posting here:", height=350)
        st.markdown("---"); st.subheader("📄 Your CV (Optional)"); uploaded_cv = st.file_uploader("📂 Upload your CV (PDF, DOCX, TXT):", type=['pdf', 'docx', 'txt'])
        cv_file_text = ""
        if uploaded_cv is not None:
            cv_file_text = extract_file_text(uploaded_cv)
            if cv_file_text.strip(): st.success(f"✅ {uploaded_cv.name} uploaded!")
            else: st.warning("⚠️ Could not extract text. Paste below.")
        cv_text_manual = st.text_area("📝 Or paste your CV text here:", height=150)
        analyze_btn = st.button("🔍 Analyze Job Post & Match", type="primary", use_container_width=True)

    with col2:
        st.subheader("📊 Analysis Report"); count = st.session_state.analysis_count; is_unlocked = st.session_state.unlocked
        if count >= 5 and not is_unlocked and st.session_state.lock_time:
            if time.time() - st.session_state.lock_time >= 86400: st.session_state.unlocked = True; is_unlocked = True
        if is_unlocked: st.info("💎 **Premium Access:** Unlimited analyses!")
        elif count < 5: st.info(f"💡 You have **{5 - count}** free analyses left.")
        
        if analyze_btn and not api_key_input: st.error("🚫 Please enter your Groq API key.")
        elif analyze_btn and not job_post.strip(): st.warning("⚠️ Please paste a job post.")
        elif analyze_btn:
            if count >= 5 and not is_unlocked:
                if st.session_state.lock_time is None: st.session_state.lock_time = time.time()
                st.error("🚫 **Free Limit Reached!**"); st.markdown("---")
                st.info("📧 Send feedback to **velitgone31@gmail.com** to unlock!")
                with st.form("unlock_form"):
                    user_email = st.text_input("✉️ Email used for feedback:"); submit_email = st.form_submit_button("🔓 Unlock Instantly")
                    if submit_email and user_email.strip() and "@" in user_email:
                        try: requests.post("https://formsubmit.co/ajax/velitgone31@gmail.com", data={"email": user_email.strip(), "message": "Unlocked"})
                        except: pass
                        st.session_state.unlocked = True; st.success("✅ Unlocked!"); st.rerun()
            else:
                final_cv_text = cv_file_text if (uploaded_cv and cv_file_text.strip()) else cv_text_manual
                user_message = f"JOB POST TO ANALYZE:\n\n{job_post}"
                if final_cv_text.strip(): user_message += f"\n\nUSER CV TO MATCH:\n\n{final_cv_text.strip()}"
                if external_evidence.strip(): user_message += f"\n\nSUPPLIED EXTERNAL EVIDENCE:\n\n{external_evidence.strip()}"
                with st.spinner("🕵️ Conducting 5-stage pipeline analysis..."):
                    try:
                        client = Groq(api_key=api_key_input)
                        raw_response = client.chat.completions.create(messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}], model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4096).choices[0].message.content
                        data = extract_json(raw_response); v_emoji = data.get("verdict_emoji", "⚪"); v_label = data.get("verdict_label", "Unknown")
                        st.session_state.analysis_count += 1; stats = load_stats(); stats["analyses"] += 1
                        if "Scam" in v_label or "Ghost" in v_label: stats["scams"] += 1
                        save_stats(stats)
                        if "🟢" in v_emoji: st.success(f"**VERDICT: {v_emoji} {v_label}**")
                        elif "🟡" in v_emoji: st.warning(f"**VERDICT: {v_emoji} {v_label}**")
                        elif "🟠" in v_emoji: st.error(f"**VERDICT: {v_emoji} {v_label}**")
                        elif "🔴" in v_emoji: st.error(f"**VERDICT: {v_emoji} {v_label}**")
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("👻 Ghost Job Risk", f"{data.get('ghost_job_risk', 'N/A')}%"); sc2.metric("🚨 Scam Risk", f"{data.get('scam_risk', 'N/A')}%"); sc3.metric("✅ Authenticity", f"{data.get('authenticity_score', 'N/A')}%")
                        action = data.get("recommended_action", "N/A")
                        if "Safe" in action: st.success(f"**Recommended Action:** Safe to Apply")
                        elif "Caution" in action: st.warning(f"**Recommended Action:** Apply with Caution")
                        else: st.error(f"**Recommended Action:** Investigate Further / Avoid")
                        if final_cv_text.strip() and data.get("match_score", 0) > 0:
                            st.markdown("---"); st.subheader("🤝 CV Match Analysis"); st.metric("🎯 Job Match Score", f"%{data.get('match_score')}")
                            mc, ms = st.columns(2)
                            with mc: st.markdown("### ✅ Skills You Have"); [st.success(f"✔️ {s}") for s in data.get("matching_skills", [])]
                            with ms: st.markdown("### ❌ Skills Missing"); [st.error(f"❌ {s}") for s in data.get("missing_skills", [])]
                        st.markdown("---"); cr, cp = st.columns(2)
                        with cr: st.markdown("### 🚩 Key Risk Factors"); [st.markdown(f"- {r}") for r in data.get("key_risk_factors", [])]
                        with cp: st.markdown("### ✨ Positive Signals"); [st.markdown(f"- {p}") for p in data.get("positive_signals", [])]
                        st.markdown("### 🧠 Final Reasoning"); st.write(data.get("final_reasoning"))
                    except Exception as e: st.error(f"🚫 Error: {str(e)}")
