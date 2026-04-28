from flask import request, jsonify
from db import conectar


def obtener_productos():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT 
        p.id,
        p.nombre,
        p.precio,
        p.imagen,
        IFNULL(SUM(l.stock),0) AS stock
    FROM productos p
    LEFT JOIN lotes l ON p.id = l.producto_id
    GROUP BY p.id, p.nombre, p.precio, p.imagen
    ORDER BY p.nombre ASC
    """)

    datos = cur.fetchall()
    con.close()

    return jsonify([
        {
            "id": x["id"],
            "nombre": x["nombre"],
            "precio": x["precio"],
            "imagen": x["imagen"],
            "stock": x["stock"]
        }
        for x in datos
    ])


def agregar_producto():
    data = request.json

    nombre = data.get("nombre", "").strip()
    precio = data.get("precio")
    imagen = data.get("imagen", "").strip()

    if not nombre or precio in ("", None):
        return {"ok": False, "error": "Nombre y precio son obligatorios"}

    if not imagen:
        imagen = "https://images.unsplash.com/photo-1587854692152-cbe660dbde88"

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO productos(nombre, precio, imagen)
    VALUES(?, ?, ?)
    """, (
        nombre,
        float(precio),
        imagen
    ))

    con.commit()
    con.close()

    return {"ok": True}


def agregar_lote():
    data = request.json

    producto_id = data.get("producto_id")
    lote = data.get("lote", "").strip()
    stock = data.get("stock")
    caducidad = data.get("caducidad")

    if not producto_id or not lote or stock in ("", None) or not caducidad:
        return {"ok": False, "error": "Todos los campos del lote son obligatorios"}

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO lotes(producto_id, lote, stock, caducidad)
    VALUES(?, ?, ?, ?)
    """, (
        int(producto_id),
        lote,
        int(stock),
        caducidad
    ))

    con.commit()
    con.close()

    return {"ok": True}