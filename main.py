import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import psycopg2
from datetime import datetime, timedelta

load_dotenv()
app = FastAPI()
PG_CONN = os.environ.get("DATABASE_URL")

DAYS_MAP = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}

def calculate_expiry(start_date_str, visits, days_str):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        days_list = [d.strip() for d in days_str.split(",") if d.strip() in DAYS_MAP]
        if not days_list:
            return (start_date + timedelta(days=30)).strftime("%Y-%m-%d")
        
        target_weekdays = set(DAYS_MAP[d] for d in days_list)
        sessions_count = 0
        current_date = start_date
        
        while sessions_count < visits:
            if current_date.weekday() in target_weekdays:
                sessions_count += 1
                if sessions_count == visits:
                    break
            current_date += timedelta(days=1)
        
        return current_date.strftime("%Y-%m-%d")
    except:
        return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

def init_db():
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY, 
            last_name TEXT, 
            visits INTEGER,
            payment_date TEXT,
            start_date TEXT,
            expiry_date TEXT,
            phone TEXT,
            days_of_week TEXT
        )
    """)
    cursor.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS start_date TEXT;")
    cursor.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS days_of_week TEXT;")
    conn.commit()
    conn.close()
init_db()

def get_html(clients_html, search_query=""):
    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Фитнес CRM</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f4f7f6; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #2c3e50; }}
            .search-box {{ display: flex; gap: 10px; margin-bottom: 20px; background: #ecf0f1; padding: 15px; border-radius: 5px; }}
            .search-box input {{ flex: 1; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; }}
            .form-group {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 30px; background: #e8f4f8; padding: 15px; border-radius: 5px; }}
            input, button {{ padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; }}
            button {{ background: #3498db; color: white; border: none; cursor: pointer; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ background: #ecf0f1; margin-bottom: 10px; padding: 15px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
            .client-info {{ flex: 1; min-width: 250px; }}
            .client-name {{ font-weight: bold; font-size: 18px; color: #2c3e50; text-decoration: none; }}
            .client-name:hover {{ color: #3498db; }}
            .actions {{ display: flex; gap: 5px; }}
            .btn-extend {{ background: #27ae60; color: white; padding: 8px; border-radius: 5px; text-decoration: none; font-size: 14px; }}
            .btn-delete {{ background: #e74c3c; color: white; padding: 8px; border-radius: 5px; text-decoration: none; font-size: 14px; }}
            .warning {{ color: #e74c3c; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>База клиентов</h1>
            
            <form action="/" method="get" class="search-box">
                <input type="text" name="search" placeholder="Поиск по фамилии..." value="{search_query}">
                <button type="submit">Найти</button>
                <a href="/" style="padding:10px; text-decoration:none; color:#7f8c8d;">Сбросить</a>
            </form>

            <h3>Добавить клиента:</h3>
            <form action="/add_client" method="post" class="form-group">
                <input type="text" name="last_name" placeholder="Фамилия и Имя" required>
                <input type="number" name="visits" placeholder="Занятий (8/12)" required style="width:100px;">
                <input type="date" name="payment_date" required title="Дата оплаты">
                <input type="date" name="start_date" required title="Первое занятие">
                <input type="text" name="days_of_week" placeholder="Дни (Пн, Ср, Пт)" required style="width:130px;">
                <input type="text" name="phone" placeholder="Телефон" required>
                <button type="submit">Добавить</button>
            </form>

            <ul>{clients_html}</ul>
        </div>
    </body>
    </html>
    """

@app.get("/")
def read_index(search: str = ""):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    
    if search:
        cursor.execute("SELECT id, last_name, visits, payment_date, start_date, expiry_date, phone, days_of_week FROM clients WHERE last_name ILIKE %s ORDER BY last_name", (f"%{search}%",))
    else:
        cursor.execute("SELECT id, last_name, visits, payment_date, start_date, expiry_date, phone, days_of_week FROM clients ORDER BY last_name")
    
    rows = cursor.fetchall()
    conn.close()

    clients_html = ""
    for row in rows:
        client_id = row[0]
        expiry = row[5] or ""
        days = row[7] or "Не указаны"
        
        warning = ""
        try:
            exp_date = datetime.strptime(expiry, "%Y-%m-%d")
            if exp_date < datetime.now():
                warning = " <span class='warning'>(ПРОСРОЧЕН!)</span>"
        except:
            pass

        clients_html += f"""
        <li>
            <div class="client-info">
                <a href="/edit/{client_id}" class="client-name">✏️ {row[1]}</a>{warning}<br>
                <small>🏋️ {row[2]} зан. | 📅 Оплата: {row[3]} | 🚀 Старт: {row[4] or ''} | ⌛ До: {expiry} | 🗓️ {days} | 📞 {row[6]}</small>
            </div>
            <div class="actions">
                <a href="/extend/{client_id}" class="btn-extend">Продлить</a>
                <a href="/delete/{client_id}" class="btn-delete">Удалить</a>
            </div>
        </li>
        """
    return HTMLResponse(content=get_html(clients_html, search))

@app.get("/extend/{client_id}")
def extend_client(client_id: int):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("SELECT visits, expiry_date, days_of_week FROM clients WHERE id = %s", (client_id,))
    row = cursor.fetchone()
    visits, old_expiry, days = row
    
    new_payment = datetime.now().strftime("%Y-%m-%d")
    try:
        old_date = datetime.strptime(old_expiry, "%Y-%m-%d")
        new_start = (old_date + timedelta(days=1)).strftime("%Y-%m-%d")
    except:
        new_start = new_payment

    new_expiry = calculate_expiry(new_start, visits, days or "")

    cursor.execute("UPDATE clients SET payment_date=%s, start_date=%s, expiry_date=%s WHERE id=%s", (new_payment, new_start, new_expiry, client_id))
    conn.commit()
    conn.close()
    return HTMLResponse("<script>window.location.href='/';</script>")

@app.post("/add_client")
def add_client(last_name: str = Form(...), visits: int = Form(...), payment_date: str = Form(...), start_date: str = Form(...), days_of_week: str = Form(...), phone: str = Form(...)):
    expiry_date = calculate_expiry(start_date, visits, days_of_week)
    
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (last_name, visits, payment_date, start_date, expiry_date, phone, days_of_week) VALUES (%s,%s,%s,%s,%s,%s,%s)", (last_name, visits, payment_date, start_date, expiry_date, phone, days_of_week))
    conn.commit()
    conn.close()
    return HTMLResponse("<script>window.location.href='/';</script>")

@app.get("/edit/{client_id}")
def edit_page(client_id: int):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("SELECT last_name, visits, payment_date, start_date, phone, days_of_week FROM clients WHERE id = %s", (client_id,))
    c = cursor.fetchone()
    conn.close()
    
    return HTMLResponse(f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Редактировать</title>
    <style>body{{font-family:sans-serif;padding:20px}} .container{{max-width:500px;margin:auto;background:white;padding:20px;border-radius:10px}} input{{width:100%;padding:10px;margin-bottom:10px;box-sizing:border-box}} button{{width:100%;padding:10px;background:#3498db;color:white;border:none}}</style>
    </head><body><div class="container">
        <h2>Редактировать: {c[0]}</h2>
        <form action="/update/{client_id}" method="post">
            <label>Фамилия и Имя:</label><input type="text" name="last_name" value="{c[0]}" required>
            <label>Количество занятий:</label><input type="number" name="visits" value="{c[1]}" required>
            <label>Дата оплаты:</label><input type="date" name="payment_date" value="{c[2]}" required>
            <label>Дата первого занятия:</label><input type="date" name="start_date" value="{c[3] or ''}" required>
            <label>Дни недели:</label><input type="text" name="days_of_week" value="{c[5] or ''}" placeholder="Пн, Ср, Пт" required>
            <label>Телефон:</label><input type="text" name="phone" value="{c[4]}" required>
            <button type="submit">Сохранить изменения</button>
        </form>
        <p style="text-align:center;"><a href="/">Отмена</a></p>
    </div></body></html>
    """)

@app.post("/update/{client_id}")
def update_client(client_id: int, last_name: str = Form(...), visits: int = Form(...), payment_date: str = Form(...), start_date: str = Form(...), days_of_week: str = Form(...), phone: str = Form(...)):
    expiry_date = calculate_expiry(start_date, visits, days_of_week)
    
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET last_name=%s, visits=%s, payment_date=%s, start_date=%s, expiry_date=%s, phone=%s, days_of_week=%s WHERE id=%s", (last_name, visits, payment_date, start_date, expiry_date, phone, days_of_week, client_id))
    conn.commit()
    conn.close()
    return HTMLResponse("<script>window.location.href='/';</script>")

@app.get("/delete/{client_id}")
def delete_client(client_id: int):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = %s", (client_id,))
    conn.commit()
    conn.close()
    return HTMLResponse("<script>window.location.href='/';</script>")
