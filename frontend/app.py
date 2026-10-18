import os, time
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
AGENTS = [
    ("planner", "🧭", "Planner", "Plans the research questions"),
    ("researcher", "🔎", "Researcher", "Searches the live web"),
    ("verifier", "✅", "Verifier", "Cross-checks the facts"),
    ("summarizer", "🧠", "Summarizer", "Condenses the findings"),
    ("writer", "✍️", "Writer", "Writes the final report"),
]
EXAMPLES = ["Agentic AI in software engineering", "Future of electric vehicles in India",
            "Impact of generative AI on jobs", "Quantum computing explained"]

st.set_page_config(page_title="AI Research Studio", page_icon="🤖", layout="wide")

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1100px;}
.hero {padding: 2.2rem 2rem; border-radius: 20px; margin-bottom: 1.5rem;
  background: linear-gradient(135deg, #1b1442 0%, #2b1d6b 45%, #0f3b63 100%);
  border: 1px solid rgba(255,255,255,.08);}
.hero h1 {margin: 0; font-size: 2.3rem; font-weight: 800; color: #fff;}
.hero p {margin: .5rem 0 0; color: #c9d1ea; font-size: 1.05rem;}
.agents {display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 1rem 0 1.5rem;}
.agent {background: #131A2B; border: 1px solid #222c45; border-radius: 14px; padding: 14px 12px; text-align: center;}
.agent.done {border-color: #3ddc97; background: #0f2a22;}
.agent.active {border-color: #7C5CFF; background: #1c1745; box-shadow: 0 0 18px rgba(124,92,255,.35);}
.agent .ic {font-size: 1.6rem;}
.agent .nm {font-weight: 700; margin-top: 4px; color: #fff;}
.agent .ds {font-size: .75rem; color: #9aa6c4; margin-top: 2px;}
.stat {background: #131A2B; border: 1px solid #222c45; border-radius: 14px; padding: 16px; text-align: center;}
.stat b {display: block; font-size: 1.8rem; color: #a99bff;}
.stat span {color: #9aa6c4; font-size: .85rem;}
.badge {display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700;}
.badge.high {background: #123d2c; color: #3ddc97;}
.badge.medium {background: #473a12; color: #ffc857;}
div.stButton > button[kind="primary"] {width: 100%; padding: .7rem; font-weight: 700; border-radius: 12px;}
@media (max-width: 800px) {.agents {grid-template-columns: repeat(2, 1fr);} .hero h1 {font-size: 1.6rem;}}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><h1>🤖 AI Research Studio</h1>
<p>Give a topic. A team of 5 AI agents researches the web, verifies facts and delivers a PDF &amp; DOCX report with citations.</p></div>""",
            unsafe_allow_html=True)


def agents_html(done=0, active=-1):
    out = '<div class="agents">'
    for i, (_, ic, nm, ds) in enumerate(AGENTS):
        cls = "done" if i < done else ("active" if i == active else "")
        out += f'<div class="agent {cls}"><div class="ic">{ic}</div><div class="nm">{nm}</div><div class="ds">{ds}</div></div>'
    return out + "</div>"


def api(method, path, **kw):
    return requests.request(method, f"{BACKEND}{path}", timeout=kw.pop("timeout", 60), **kw)


# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### 🕘 History")
    try:
        jobs = api("GET", "/jobs", timeout=20).json()
        if not jobs:
            st.caption("No reports yet.")
        for j in jobs[:10]:
            icon = {"completed": "✅", "failed": "❌"}.get(j["status"], "⏳")
            if st.button(f"{icon} {j['topic'][:28]}", key=j["job_id"], use_container_width=True):
                st.session_state.job_id = j["job_id"]
    except Exception:
        st.warning("Backend is waking up or unreachable. Refresh in a minute.")

# ---------- input ----------
if "topic" not in st.session_state:
    st.session_state.topic = ""

def set_topic(t):
    st.session_state.topic = t

st.text_input("What do you want to research?", key="topic",
              placeholder="Type your topic here, e.g. Agentic AI in software engineering")
st.caption("Try an example:")
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    c.button(ex, on_click=set_topic, args=(ex,), use_container_width=True, key="ex_" + ex)

mode = st.radio("Research depth", ["⚡ Quick (3)", "📘 Standard (4)", "🔬 Deep (6)"],
                index=1, horizontal=True)
depth = int(mode.split("(")[1].strip(")"))

go = st.button("🚀 Generate Report", type="primary", disabled=len(st.session_state.topic.strip()) < 3)

if go:
    try:
        r = api("POST", "/research", json={"topic": st.session_state.topic.strip(), "depth": depth}, timeout=90)
        if r.ok:
            st.session_state.job_id = r.json()["job_id"]
        else:
            st.error(r.text)
    except Exception as e:
        st.error(f"Could not reach backend (it may be waking up). Please retry in a minute. ({e})")

# ---------- result ----------
jid = st.session_state.get("job_id")
if jid:
    holder = st.empty()
    bar = st.progress(0)
    while True:
        try:
            j = api("GET", f"/research/{jid}", timeout=30).json()
        except Exception:
            time.sleep(3)
            continue
        if j["status"] in ("queued", "running"):
            prog = j.get("progress", "")
            last = next((i for i, (k, *_) in enumerate(AGENTS) if f"done: {k}" in prog), -1)
            done = last + 1 if last >= 0 else 0
            holder.markdown(agents_html(done, min(done, 4)), unsafe_allow_html=True)
            bar.progress(min(0.1 + done * 0.18, 0.95), text=prog or "Starting...")
            time.sleep(2)
            continue
        break
    bar.empty()

    if j["status"] == "failed":
        holder.empty()
        st.error(f"Report failed: {j['error']}")
    else:
        holder.markdown(agents_html(5), unsafe_allow_html=True)
        rep = j["report"]
        st.success("Report ready! 🎉")

        c = st.columns(3)
        stats = [(len(rep["sections"]) + 2, "Sections"), (len(rep["sources"]), "Sources"),
                 (len(rep["fact_check"]), "Verified facts")]
        for col, (n, label) in zip(c, stats):
            col.markdown(f'<div class="stat"><b>{n}</b><span>{label}</span></div>', unsafe_allow_html=True)

        st.write("")
        d1, d2 = st.columns(2)
        for col, fmt, label in ((d1, "pdf", "📄 Download PDF"), (d2, "docx", "📝 Download DOCX")):
            try:
                data = api("GET", f"/research/{jid}/download/{fmt}", timeout=60).content
                col.download_button(label, data, f"research_report.{fmt}", use_container_width=True)
            except Exception:
                col.caption(f"{fmt.upper()} not available")

        t1, t2, t3 = st.tabs(["📖 Report", "✅ Fact-check", "📚 Sources"])
        with t1:
            st.header(rep["title"])
            st.subheader("Executive Summary"); st.write(rep["executive_summary"])
            for s in rep["sections"]:
                st.subheader(s["heading"]); st.write(s["content"])
            st.subheader("Conclusion"); st.write(rep["conclusion"])
        with t2:
            for f in rep["fact_check"]:
                conf = f["confidence"]
                st.markdown(f'<span class="badge {conf}">{conf.upper()}</span> {f["claim"]} '
                            f'<small>— sources {f["source_ids"]}</small>', unsafe_allow_html=True)
        with t3:
            for s in rep["sources"]:
                st.markdown(f"**[{s['id']}]** [{s['title']}]({s['url']})")
else:
    st.markdown(agents_html(), unsafe_allow_html=True)
    st.caption("Powered by LangGraph · Gemini · Tavily · FastAPI · MongoDB")