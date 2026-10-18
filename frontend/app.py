import os, time
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
st.set_page_config(page_title="AI Research Platform", page_icon="🤖", layout="wide")
st.title("🤖 Multi-Agent AI Research Platform")
st.caption("Planner → Researcher → Fact-Verifier → Summarizer → Report Writer")

with st.sidebar:
    st.header("History")
    try:
        for j in requests.get(f"{BACKEND}/jobs", timeout=5).json():
            if st.button(f"{j['topic'][:30]} ({j['status']})", key=j["job_id"]):
                st.session_state.job_id = j["job_id"]
    except Exception:
        st.warning("Backend not reachable")

topic = st.text_input("Research topic", placeholder="Future of electric vehicles in India")
depth = st.slider("Research depth (questions)", 2, 8, 4)

if st.button("🚀 Generate Report", type="primary", disabled=len(topic) < 3):
    r = requests.post(f"{BACKEND}/research", json={"topic": topic, "depth": depth}, timeout=10)
    if r.ok:
        st.session_state.job_id = r.json()["job_id"]
    else:
        st.error(r.text)

jid = st.session_state.get("job_id")
if jid:
    box = st.empty()
    while True:
        j = requests.get(f"{BACKEND}/research/{jid}", timeout=10).json()
        if j["status"] in ("queued", "running"):
            box.info(f"⏳ {j['progress']}")
            time.sleep(2)
            continue
        box.empty()
        break
    if j["status"] == "failed":
        st.error(f"Failed: {j['error']}")
    else:
        rep = j["report"]
        st.success("Report ready!")
        c1, c2 = st.columns(2)
        for col, fmt in ((c1, "pdf"), (c2, "docx")):
            data = requests.get(f"{BACKEND}/research/{jid}/download/{fmt}").content
            col.download_button(f"⬇️ Download {fmt.upper()}", data, f"report.{fmt}")
        st.header(rep["title"])
        st.subheader("Executive Summary"); st.write(rep["executive_summary"])
        for s in rep["sections"]:
            st.subheader(s["heading"]); st.write(s["content"])
        st.subheader("Conclusion"); st.write(rep["conclusion"])
        with st.expander("✅ Fact-check results"):
            for f in rep["fact_check"]:
                st.write(f"**[{f['confidence']}]** {f['claim']} — sources {f['source_ids']}")
        with st.expander("📚 Sources"):
            for s in rep["sources"]:
                st.markdown(f"[{s['id']}] [{s['title']}]({s['url']})")
