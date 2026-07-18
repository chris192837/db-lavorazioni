from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from datetime import date, datetime, timedelta
from db import init_db, insert_users_db, insert_lavorazioni_db, get_connection
import psycopg2
from psycopg2.extras import DictCursor
from flask_wtf import CSRFProtect
import itertools
import re


app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
csrf = CSRFProtect(app)

init_db()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

LOGIN_ATTEMPS = {}
MAX_TENTATIVI = 5
BLOCCO_MINUTI = 15

def delete_lavorazioni_bulk_db(record_ids, user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM lavorazioni WHERE id = ANY(%s) AND user_id = %s;
                """,
                (record_ids, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def delete_lavorazione_db(record_id, user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM lavorazioni WHERE id = %s AND user_id = %s;
                """,
                (record_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()

def update_ruolo_db(user_id, ruolo):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET ruolo = %s WHERE id = %s;",
                (ruolo, user_id),
            )
        conn.commit()
    finally:
        conn.close()

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        ruolo = "lavoratore"
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        nome = request.form.get("nome")
        cognome = request.form.get("cognome")
        data_nascita = request.form.get("data_nascita")
        sesso = request.form.get("sesso")
        indirizzo = request.form.get("indirizzo")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT id FROM users WHERE email = %s", (email,),
                )
                existing = cur.fetchone()
        finally:
            conn.close()

        if not EMAIL_REGEX.match(email):
            error = "Indirizzo email non valido."
        elif len(password) < 8:
            error = "La password deve contenere almeno 8 caratteri."
        elif not nome or not cognome:
            error = "Nome e cognome sono obbligatori."
        elif password != password_confirm:
            error = "Le password non coincidono."
        else:
            if existing is not None:
                error = "Questa email è già registrata. Effettua il login oppure usa un'altra email."
            else:
                password_hash = generate_password_hash(password)

                try:
                    insert_users_db(
                        ruolo=ruolo,
                        email=email,
                        password_hash=password_hash,
                        nome=nome,
                        cognome=cognome,
                        data_nascita=data_nascita,
                        sesso=sesso,
                        indirizzo=indirizzo,
                    )

                except psycopg2.errors.UniqueViolation:
                    error = "Questa email è già registrata. Effettua il login oppure un'altra email."
                else:
                    flash("Registrazione effettuata con successo. Puoi effettuare il login.", "success")
                    return redirect(url_for("login"))
    return render_template("register.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method== "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        tentativo = LOGIN_ATTEMPS.get(email)
        if tentativo and tentativo["blocked_until"] and tentativo["blocked_until"] > datetime.utcnow():
            return "Troppi tentativi falliti. Riprova più tardi.", 429
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT id, ruolo, nome, cognome, email, password_hash FROM users WHERE email = %s", (email,),
                )
                user = cur.fetchone()
        finally:
            conn.close()

        if user is None:
            tentativo = LOGIN_ATTEMPS.setdefault(email, {"count": 0, "blocked_until": None})
            tentativo["count"] += 1
            if tentativo["count"] >= MAX_TENTATIVI:
                tentativo["blocked_until"] = datetime.utcnow() + timedelta(minutes=BLOCCO_MINUTI)
            return "Email o password non corretti", 400
        
        if not check_password_hash(user["password_hash"], password):
            tentativo = LOGIN_ATTEMPS.setdefault(email, {"count": 0, "blocked_until": None})
            tentativo["count"] += 1
            if tentativo["count"] >= MAX_TENTATIVI:
                tentativo["blocked_until"] = datetime.utcnow() + timedelta(minutes=BLOCCO_MINUTI)
            return "Email o password non corretti", 400
        
        LOGIN_ATTEMPS.pop(email, None)

        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["ruolo"] = user["ruolo"]
        session["nome"] = user["nome"]
        session["cognome"] = user["cognome"]

        flash("Accesso effettuato con successo.", "success")

        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    email = session.get("email")
    nome = session.get("nome")
    cognome = session.get("cognome")
    today = date.today().isoformat()

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    u.id,
                    u.email,
                    SUM(CASE WHEN l.tipo_record = 'chiamata' THEN 1 ELSE 0 END) AS chiamate,
                    SUM(CASE WHEN l.tipo_record = 'documento' THEN 1 ELSE 0 END) AS documenti,
                    COUNT(l.id) AS totale
                FROM users u
                LEFT JOIN lavorazioni l ON l.user_id = u.id AND l.data_lavorazione = %s
                WHERE u.id = %s
                GROUP BY u.id, u.email;
                """,
                (today, user_id,),
            )
            stats = cur.fetchone()
    finally:
        conn.close()

    return render_template("dashboard.html", nome=nome, cognome=cognome, stats=stats)


@app.route("/admin/set_ruolo/<int:user_id>", methods=["POST"])
def set_ruolo(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("ruolo") != "admin":
        return redirect(url_for("dashboard"))
    
    nuovo_ruolo = request.form.get("ruolo")

    if nuovo_ruolo not in ("admin", "lavoratore"):
        flash("Ruolo non valido.", "error")
        return redirect(url_for("reports"))
    
    update_ruolo_db(user_id, nuovo_ruolo)
    flash("Ruolo aggiornato con successo.", "success")

    return redirect(url_for("reports"))


@app.route("/new_record", methods=["GET", "POST"])
def new_record():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        user_id = session["user_id"]
        tipo_record = request.form.get("tipo_record")
        tipologia = request.form.get("tipologia")
        data_lavorazione_form = request.form.get("data_lavorazione")
        codice_pratica = request.form.get("codice_pratica")
        coda_lavorazione = request.form.get("coda_lavorazione")
        note = request.form.get("note")

        if tipo_record == "documento":
            data_lavorazione = data_lavorazione_form
        else:
            data_lavorazione = date.today().isoformat()

        insert_lavorazioni_db(
            user_id=user_id,
            tipo_record=tipo_record,
            tipologia=tipologia,
            data_lavorazione=data_lavorazione,
            codice_pratica=codice_pratica,
            coda_lavorazione=coda_lavorazione,
            note=note,
        )

        flash("Lavorazione salvata con successo.", "success")
        
        return redirect(url_for("dashboard"))
    
    return render_template("new_record.html")


@app.route("/records")
def records():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    id,
                    tipo_record,
                    tipologia,
                    data_lavorazione,
                    codice_pratica,
                    coda_lavorazione,
                    note,
                    created_at
                FROM lavorazioni
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows =cur.fetchall()
            record_by_date = []
            for data, gruppo in itertools.groupby(rows, key=lambda r: r["created_at"].date()):
                gruppo_lista = list(gruppo)
                record_by_date.append({
                    "data": data,
                    "totale": len(gruppo_lista),
                    "records": gruppo_lista,
                })
    finally:
        conn.close()
    
    return render_template("records.html", record_by_date=record_by_date)

@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("ruolo") != "admin":
        return redirect(url_for("dashboard"))
    
    user_id = session["user_id"]

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    tipo_record,
                    tipologia,
                    COUNT(*) AS totale
                FROM lavorazioni
                WHERE user_id = %s
                GROUP BY tipo_record, tipologia
                ORDER BY tipo_record, tipologia;
                """,
                (user_id,),
            )
            summary_by_type = cur.fetchall()
    finally:
        conn.close()
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    u.id,
                    u.nome,
                    u.cognome,
                    u.ruolo,
                    SUM(CASE WHEN l.tipo_record = 'documento' THEN 1 ELSE 0 END) AS documenti,
                    SUM(CASE WHEN l.tipo_record = 'chiamata' THEN 1 ELSE 0 END) AS chiamate,
                    COUNT(l.id) AS totale
                FROM users u
                LEFT JOIN lavorazioni l ON l.user_id = u.id
                GROUP BY u.id, u.nome, u.cognome, ruolo
                ORDER BY u.cognome, u.nome;
                """

            )
            per_user_stats = cur.fetchall()
    finally:
        conn.close()

    return render_template("reports.html", summary_by_type=summary_by_type, per_user_stats=per_user_stats)


@app.route("/records/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    delete_lavorazione_db(record_id, user_id)
    flash("Lavorazione eliminata con successo!", "success")

    return redirect(url_for("records"))


@app.route("/records/delete_selected", methods=["POST"])
def delete_selected_records():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    record_ids = request.form.getlist("record_ids", type=int)

    if record_ids:
        delete_lavorazioni_bulk_db(record_ids, user_id)
        flash("Lavorazioni selezionate eliminate con successo!", "success")
    else:
        flash("Nessuna lavorazione selezionata.", "error")

    return redirect(url_for("records"))


if __name__ == "__main__":
    app.run()
