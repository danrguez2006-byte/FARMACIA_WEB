from flask import request, jsonify, session
from db import conectar
from utils.tickets import generar_ticket


def stock_disponible(cur, producto_id):
    cur.execute("""
    SELECT IFNULL(SUM(stock),0) AS stock
    FROM lotes
    WHERE producto_id=?
    AND stock > 0
    AND DATE(caducidad) >= DATE('now')
    """, (producto_id,))

    return cur.fetchone()["stock"]


def descontar_stock(cur, producto_id, cantidad):

    cur.execute("""
    SELECT id, stock
    FROM lotes
    WHERE producto_id=?
    AND stock > 0
    AND DATE(caducidad) >= DATE('now')
    ORDER BY caducidad ASC
    """, (producto_id,))

    lotes = cur.fetchall()
    restante = cantidad

    for lote in lotes:

        if restante <= 0:
            break

        lote_id = lote["id"]
        stock = lote["stock"]

        if stock <= restante:

            cur.execute("""
            UPDATE lotes
            SET stock=0
            WHERE id=?
            """, (lote_id,))

            restante -= stock

        else:

            cur.execute("""
            UPDATE lotes
            SET stock = stock - ?
            WHERE id=?
            """, (restante, lote_id))

            restante = 0

    return restante == 0


def realizar_venta():

    data = request.json
    carrito = data.get("carrito", [])

    if not carrito:
        return {"ok": False, "error": "Carrito vacío"}

    con = conectar()
    cur = con.cursor()

    try:

        total = 0

        for item in carrito:

            producto_id = int(item["id"])
            cantidad = int(item["cantidad"])

            cur.execute("""
            SELECT nombre, precio
            FROM productos
            WHERE id=?
            """, (producto_id,))

            producto = cur.fetchone()

            if not producto:
                con.close()
                return {"ok": False, "error": "Producto no existe"}

            disponible = stock_disponible(cur, producto_id)

            if disponible < cantidad:
                con.close()
                return {
                    "ok": False,
                    "error": f"Stock insuficiente para {producto['nombre']}"
                }

            total += producto["precio"] * cantidad

        cur.execute("""
        INSERT INTO ventas(usuario_id,total,tipo,estado)
        VALUES(?,?,?,?)
        """, (
            session["user_id"],
            total,
            "mostrador",
            "pagado"
        ))

        venta_id = cur.lastrowid

        for item in carrito:

            producto_id = int(item["id"])
            cantidad = int(item["cantidad"])

            cur.execute("""
            SELECT precio
            FROM productos
            WHERE id=?
            """, (producto_id,))

            precio = cur.fetchone()["precio"]

            descontar_stock(cur, producto_id, cantidad)

            cur.execute("""
            INSERT INTO detalle_venta(venta_id,producto_id,cantidad,precio)
            VALUES(?,?,?,?)
            """, (
                venta_id,
                producto_id,
                cantidad,
                precio
            ))

        con.commit()

        ticket = generar_ticket(venta_id, total)

        con.close()

        return {
            "ok": True,
            "ticket": ticket,
            "total": total
        }

    except Exception as e:
        con.rollback()
        con.close()
        return {"ok": False, "error": str(e)}


def realizar_pedido_online():

    data = request.json
    carrito = data.get("carrito", [])
    direccion = data.get("direccion", "").strip()
    telefono = data.get("telefono", "").strip()

    if not carrito:
        return {"ok": False, "error": "Carrito vacío"}

    if not direccion or not telefono:
        return {"ok": False, "error": "Falta dirección o teléfono"}

    con = conectar()
    cur = con.cursor()

    try:

        total = 0

        for item in carrito:

            producto_id = int(item["id"])
            cantidad = int(item["cantidad"])

            cur.execute("""
            SELECT nombre, precio
            FROM productos
            WHERE id=?
            """, (producto_id,))

            producto = cur.fetchone()

            disponible = stock_disponible(cur, producto_id)

            if disponible < cantidad:
                con.close()
                return {
                    "ok": False,
                    "error": f"Stock insuficiente para {producto['nombre']}"
                }

            total += producto["precio"] * cantidad

        cur.execute("""
        INSERT INTO ventas(
            usuario_id,total,tipo,estado,direccion,telefono
        )
        VALUES(?,?,?,?,?,?)
        """, (
            session["user_id"],
            total,
            "online",
            "pendiente",
            direccion,
            telefono
        ))

        venta_id = cur.lastrowid

        for item in carrito:

            producto_id = int(item["id"])
            cantidad = int(item["cantidad"])

            cur.execute("""
            SELECT precio
            FROM productos
            WHERE id=?
            """, (producto_id,))

            precio = cur.fetchone()["precio"]

            descontar_stock(cur, producto_id, cantidad)

            cur.execute("""
            INSERT INTO detalle_venta(
                venta_id,producto_id,cantidad,precio
            )
            VALUES(?,?,?,?)
            """, (
                venta_id,
                producto_id,
                cantidad,
                precio
            ))

        con.commit()
        con.close()

        return {
            "ok": True,
            "pedido_id": venta_id,
            "total": total
        }

    except Exception as e:
        con.rollback()
        con.close()
        return {"ok": False, "error": str(e)}


def historial_ventas():

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT
        v.id,
        v.fecha,
        v.total,
        v.tipo,
        v.estado,
        IFNULL(u.nombre,'Sin usuario') usuario
    FROM ventas v
    LEFT JOIN usuarios u ON v.usuario_id = u.id
    ORDER BY v.fecha DESC
    """)

    datos = cur.fetchall()
    con.close()

    return jsonify([dict(x) for x in datos])