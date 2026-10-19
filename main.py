import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import psycopg2
from sentence_transformers import SentenceTransformer

load_dotenv()
app = FastAPI()
PG_CONN = os.environ.get("DATABASE_URL")
model = SentenceTransformer('all-MiniLM-L6-v2')

def init_db():
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS clients (id SERIAL PRIMARY KEY, last_name TEXT, visits INTEGER, payment_date TEXT, expiry_date TEXT, phone TEXT)")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.execute("CREATE TABLE IF NOT EXISTS documents (id SERIAL PRIMARY KEY, content TEXT, embedding vector(384))")
    conn.commit()
    conn.close()
init_db()

def get_ai_html(result_html="", msg=""):
    return f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>AI Поиск</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f7f6; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #8e44ad; text-align: center; }}
        .nav {{ text-align: center; margin-bottom: 20px; }}
        .nav a {{ text-decoration: none; background: #3498db; color: white; padding: 10px 20px; border-radius: 5px; }}
        .form-group {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        input {{ padding: 12px; border: 1px solid #bdc3c7; border-radius: 5px; flex: 1; }}
        button {{ padding: 12px 20px; background: #8e44ad; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        .result {{ background: #fdf2e9; padding: 20px; border-left: 5px solid #e67e22; border-radius: 5px; margin-top: 20px; }}
        .msg {{ background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
    </style></head>
    <body><div class="container">
        <h1>Умный поиск по базе знаний</h1>
        <div class="nav"><a href="/">Вернуться к CRM</a></div>
        {msg}
        <h3>1. Добавить новый текст в базу знаний:</h3>
        <form action="/add_doc" method="post" class="form-group">
            <input type="text" name="doc_text" placeholder="Введите текст (например, правила возврата денег)" required>
            <button type="submit">Добавить</button>
        </form>
        <h3>2. Найти ответ по смыслу:</h3>
        <form action="/ai-search" method="post" class="form-group">
            <input type="text" name="query" placeholder="Задайте вопрос..." required>
            <button type="submit">Найти</button>
        </form>
        {result_html}
    </div></body></html>
    """

@app.get("/ai-search")
def ai_page(): return HTMLResponse(content=get_ai_html())

@app.post("/add_doc")
def add_doc(doc_text: str = Form(...)):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    emb = model.encode(doc_text)
    cursor.execute("INSERT INTO documents (content, embedding) VALUES (%s, %s)", (doc_text, emb.tolist()))
    conn.commit()
    conn.close()
    return HTMLResponse(content=get_ai_html(msg="<div class='msg'>Текст успешно добавлен в базу!</div>"))

@app.post("/ai-search")
def search(query: str = Form(...)):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    emb = model.encode(query)
    cursor.execute("SELECT content FROM documents ORDER BY embedding <=> %s::vector LIMIT 1", (emb.tolist(),))
    res = cursor.fetchone()
    conn.close()
    res_html = f"<div class='result'><h3>Самый подходящий ответ:</h3><p>{res[0]}</p></div>" if res else "<p>Ничего не найдено.</p>"
    return HTMLResponse(content=get_ai_html(result_html=res_html))

@app.get("/")
def read_index():
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("SELECT id, last_name, visits, payment_date, expiry_date, phone FROM clients")
    rows = cursor.fetchall()
    conn.close()
    clients_html = "".join([f"<li><div><strong>{r[1]}</strong><br><small>{r[2]} | {r[3]} | {r[4]} | {r[5]}</small></div><a href='/delete/{r[0]}' style='color:red;'>Удалить</a></li>" for r in rows])
    return HTMLResponse(content=f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>CRM</title>
    <style>body{{font-family:sans-serif;background:#f4f7f6;padding:20px}} .container{{max-width:800px;margin:auto;background:white;padding:30px;border-radius:10px}} h1{{text-align:center;color:#2c3e50}} .nav{{text-align:center;margin-bottom:20px}} .nav a{{text-decoration:none;background:#8e44ad;color:white;padding:10px 20px;border-radius:5px}} .form-group{{display:flex;gap:10px;margin-bottom:20px}} input{{padding:12px;border:1px solid #ccc;border-radius:5px;flex:1}} button{{padding:12px;background:#3498db;color:white;border:none;border-radius:5px;cursor:pointer}} ul{{list-style:none;padding:0}} li{{background:#ecf0f1;margin-bottom:10px;padding:15px;border-radius:5px;display:flex;justify-content:space-between}}</style></head>
    <body><div class="container"><h1>База клиентов</h1><div class="nav"><a href="/ai-search">Перейти к AI-Поиску</a></div>
    <form action="/add_client" method="post" class="form-group"><input type="text" name="last_name" placeholder="Имя" required><input type="number" name="visits" placeholder="Посещений" required><input type="date" name="payment_date" required><input type="date" name="expiry_date" required><input type="text" name="phone" placeholder="Телефон" required><button type="submit">Добавить</button></form>
    <ul>{clients_html}</ul></div></body></html>
    """)

@app.post("/add_client")
def add_client(last_name: str = Form(...), visits: int = Form(...), payment_date: str = Form(...), expiry_date: str = Form(...), phone: str = Form(...)):
    conn = psycopg2.connect(PG_CONN)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (last_name, visits, payment_date, expiry_date, phone) VALUES (%s,%s,%s,%s,%s)", (last_name, visits, payment_date, expiry_date, phone))
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