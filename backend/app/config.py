import os, logging, json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "research_platform")
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

settings = Settings()

class JsonFormatter(logging.Formatter):
    def format(self, r):
        return json.dumps({"time": self.formatTime(r), "level": r.levelname,
                           "logger": r.name, "msg": r.getMessage()})

def setup_logging():
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[h], force=True)
