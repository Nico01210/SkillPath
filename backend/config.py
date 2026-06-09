from dotenv import load_dotenv
from pydantic_settings import BaseSettings
 
load_dotenv()
 
 
class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    chroma_db_path: str = "./data/chromadb"
    sqlite_db_path: str = "./data/coach.db"
    uploads_path: str = "./data/uploads"
    reports_path: str = "./data/reports"
 
    class Config:
        env_file = ".env"
 
 
# Instance unique importée partout dans le projet
settings = Settings()
 