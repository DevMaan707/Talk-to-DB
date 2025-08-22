from datetime import datetime

def log_query(db_uri, user_query, result):
    with open("query_logs.txt", "a", encoding="utf-8") as f:   # 👈 force utf-8
        f.write(f"[{datetime.now()}] DB: {db_uri}\nQ: {user_query}\nA: {result}\n\n")
