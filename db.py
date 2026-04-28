import sqlite3

DB_NAME = "farmacia.db"


def conectar():
    con = sqlite3.connect(DB_NAME, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def crear_tablas():
    con = conectar()
    cur = con.cursor()

    with open("database.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    cur.executescript(sql)

    con.commit()
    con.close()