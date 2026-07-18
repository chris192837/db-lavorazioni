import psycopg2
from psycopg2.extras import DictCursor
from config import Config
from datetime import datetime


def get_connection():
    if Config.DATABASE_URL:
        conn = psycopg2.connect(Config.DATABASE_URL)
                
    else:
        conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        dbname=Config.PG_DB,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD,
    )
    return conn
    


def init_db():
    create_table_users = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        ruolo VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        nome VARCHAR(100) NOT NULL,
        cognome VARCHAR(100) NOT NULL,
        data_nascita DATE,
        sesso VARCHAR(10),
        indirizzo TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """

    create_table_lavorazioni = """
    CREATE TABLE IF NOT EXISTS lavorazioni (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        tipo_record VARCHAR(20) NOT NULL,
        tipologia VARCHAR(50),
        data_lavorazione DATE NOT NULL,
        codice_pratica VARCHAR(50),
        coda_lavorazione VARCHAR(100),
        note TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_users)
            cur.execute(create_table_lavorazioni)
        conn.commit()
    finally:
        conn.close()


def insert_users_db(
    ruolo,    
    email,
    password_hash,
    nome,
    cognome,
    data_nascita,
    sesso,
    indirizzo,
):
    insert_sql = """
    INSERT INTO users (
        ruolo,
        email,
        password_hash,
        nome,
        cognome,
        data_nascita,
        sesso,
        indirizzo,
        created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (   
                    ruolo,
                    email,
                    password_hash,
                    nome,
                    cognome,
                    data_nascita,
                    sesso,
                    indirizzo,
                    datetime.utcnow(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def insert_lavorazioni_db(
    user_id,
    tipo_record,
    tipologia,
    data_lavorazione,
    codice_pratica,
    coda_lavorazione,
    note,
):
    insert_sql = """
    INSERT INTO lavorazioni (
        user_id,
        tipo_record,
        tipologia,
        data_lavorazione,
        codice_pratica,
        coda_lavorazione,
        note,
        created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    user_id,
                    tipo_record,
                    tipologia,
                    data_lavorazione,
                    codice_pratica,
                    coda_lavorazione,
                    note,
                    datetime.utcnow(),
                ),
            )
        conn.commit()
    finally:
        conn.close()