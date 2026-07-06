from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    chroma_db_path: str = str(BASE_DIR / "data" / "chromadb")
    sqlite_db_path: str = str(BASE_DIR / "data" / "coach.db")
    uploads_path: str = str(BASE_DIR / "data" / "uploads")
    reports_path: str = str(BASE_DIR / "data" / "reports")
 
    class Config:
        env_file = ".env"
 
 
# Instance unique importée partout dans le projet
settings = Settings()
 