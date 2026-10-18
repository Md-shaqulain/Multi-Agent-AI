# 🤖 Multi-Agent AI Research & Automated Report Generation Platform

Enter a topic → a LangGraph team of agents (Planner, Researcher, Fact-Verifier, Summarizer, Report Writer) researches the web and produces a PDF + DOCX report with table of contents and citations.

**Stack:** Python, FastAPI, LangGraph, Gemini API, Tavily API, MongoDB, Streamlit, ReportLab, python-docx

## Setup
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # add GEMINI_API_KEY and TAVILY_API_KEY
```
## Run
```bash
# terminal 1
cd backend && uvicorn app.main:app --reload
# terminal 2
streamlit run frontend/app.py
```
API docs: http://localhost:8000/docs · UI: http://localhost:8501

MongoDB is optional locally (falls back to in-memory storage).

## Architecture
`Planner → Researcher → Verifier → Summarizer → Writer` (LangGraph StateGraph) → `ReportLab` / `python-docx`.
Jobs run as async background tasks; the UI polls `/research/{id}` for progress.
