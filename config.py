import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", 5432))
    PG_DB = os.getenv("PG_DB")
    PG_USER = os.getenv("PG_USER")
    PG_PASSWORD = os.getenv("PG_PASSWORD")
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")

  
    if SECRET_KEY is None:
        raise RuntimeError("Errore di avviamento app.")

    if not DATABASE_URL and (not PG_DB or not PG_USER or not PG_PASSWORD):
        raise RuntimeError(
            "Configurazione database mancante: imposta DATABASE_URL oppure PG_DB, PG_USER e PG_PASSWORD."
        )