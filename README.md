# Fitness CRM

A simple web application for managing fitness club clients. Built with FastAPI and SQLite.

## Features

- Add new clients with name, phone, and payment date
- View the list of all clients
- Delete clients from the database
- Modern, clean UI with CSS
- Data is saved in a SQLite database

## Technologies

- **Python 3.12**
- **FastAPI** — web framework
- **SQLite** — database
- **HTML/CSS** — frontend
- **Uvicorn** — server

## How to run

1. Install dependencies:
   pip install -r requirements.txt

2. Run the server:
   python -m uvicorn.main main:app --reload

3. Open in browser:
   http://127.0.0.1:8000