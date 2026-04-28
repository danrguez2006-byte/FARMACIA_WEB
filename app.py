from flask import Flask, render_template, request, jsonify, session, redirect, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

from db import conectar, crear_tablas
from services.inventario_service import obtener_productos, agregar_producto, agregar_lote
from services.ventas_service import realizar_venta, historial_ventas, realizar_pedido_online

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


crear_tablas()


def crear_admin():
    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT * FROM usuarios WHERE email=?", ("admin@farmacia.com",))
    user = cur.fetchone()

    if not user:
        cur.execute("""
        INSERT INTO usuarios(nombre,email,password,rol)
        VALUES(?,?,?,?)
        """, (
            "Administrador",
            "admin@farmacia.com",
            generate_password_hash("1234"),
            "admin"
        ))
        con.commit()

    con.close()


crear_admin()


def rol_requerido(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if "rol" not in session:
                return redirect("/")

            if session["rol"] not in roles:
                return "No autorizado", 403

            return f(*args, **kwargs)

        return decorated
    return wrapper


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/dashboard")
@rol_requerido("admin", "vendedor")
def dashboard():
    return render_template("dashboard.html")


@app.route("/inventario")
@rol_requerido("admin", "vendedor")
def inventario():
    return render_template("inventario.html")


@app.route("/ventas")
@rol_requerido("admin", "cajero")
def ventas():
    return render_template("ventas.html")


@app.route("/reporte")
@rol_requerido("admin")
def reporte():
    return render_template("reporte.html")


@app.route("/usuarios")
@rol_requerido("admin")
def usuarios():
    return render_template("usuarios.html")


@app.route("/registro-cliente")
def registro_cliente_view():
    return render_template("registro_cliente.html")


@app.route("/cliente")
@rol_requerido("cliente")
def panel_cliente():
    return render_template("cliente.html")


@app.route("/mis-pedidos")
@rol_requerido("cliente")
def mis_pedidos_view():
    return render_template("mis_pedidos.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/ticket/<nombre>")
def ticket(nombre):
    ruta = os.path.join("tickets", nombre)
    return send_file(ruta, as_attachment=True)


@app.route("/login", methods=["POST"])
def login_post():

    data = request.json

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT id,password,rol
    FROM usuarios
    WHERE email=?
    """, (data["email"],))

    user = cur.fetchone()
    con.close()

    if user and check_password_hash(user["password"], data["password"]):

        session["user_id"] = user["id"]
        session["rol"] = user["rol"]

        return {
            "ok": True,
            "rol": user["rol"]
        }

    return {"ok": False}


@app.route("/api/registro-cliente", methods=["POST"])
def registro_cliente():
    data = request.json

    nombre = data.get("nombre", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not nombre or not email or not password:
        return {"ok": False, "error": "Todos los campos son obligatorios"}

    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT id FROM usuarios WHERE email=?", (email,))
    existe = cur.fetchone()

    if existe:
        con.close()
        return {"ok": False, "error": "Ese correo ya está registrado"}

    cur.execute("""
    INSERT INTO usuarios(nombre,email,password,rol)
    VALUES(?,?,?,?)
    """, (
        nombre,
        email,
        generate_password_hash(password),
        "cliente"
    ))

    con.commit()
    con.close()

    return {"ok": True}


@app.route("/api/usuarios")
@rol_requerido("admin")
def api_usuarios():

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT id,nombre,email,rol
    FROM usuarios
    """)

    datos = cur.fetchall()
    con.close()

    return jsonify([dict(x) for x in datos])


@app.route("/api/usuarios", methods=["POST"])
@rol_requerido("admin")
def crear_usuario():

    data = request.json

    con = conectar()
    cur = con.cursor()

    password = generate_password_hash(data["password"])

    cur.execute("""
    INSERT INTO usuarios(nombre,email,password,rol)
    VALUES(?,?,?,?)
    """, (
        data["nombre"],
        data["email"],
        password,
        data["rol"]
    ))

    con.commit()
    con.close()

    return {"ok": True}


@app.route("/api/usuarios/<int:id>", methods=["DELETE"])
@rol_requerido("admin")
def eliminar_usuario(id):

    con = conectar()
    cur = con.cursor()

    cur.execute("DELETE FROM usuarios WHERE id=?", (id,))

    con.commit()
    con.close()

    return {"ok": True}


@app.route("/api/productos")
@rol_requerido("admin", "vendedor", "cajero", "cliente")
def api_productos():
    return obtener_productos()


@app.route("/api/productos", methods=["POST"])
@rol_requerido("admin", "vendedor")
def api_add_producto():
    return agregar_producto()


@app.route("/api/lotes", methods=["POST"])
@rol_requerido("admin", "vendedor")
def api_lotes():
    return agregar_lote()


@app.route("/api/venta", methods=["POST"])
@rol_requerido("admin", "cajero")
def api_venta():
    return realizar_venta()


@app.route("/api/pedido-online", methods=["POST"])
@rol_requerido("cliente")
def api_pedido_online():
    return realizar_pedido_online()


@app.route("/api/historial")
@rol_requerido("admin")
def api_historial():
    return historial_ventas()


@app.route("/api/mis-pedidos")
@rol_requerido("cliente")
def mis_pedidos():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT id, fecha, total, estado, direccion, telefono
    FROM ventas
    WHERE usuario_id=?
    AND tipo='online'
    ORDER BY fecha DESC
    """, (session["user_id"],))

    datos = cur.fetchall()
    con.close()

    return jsonify([dict(x) for x in datos])


@app.route("/api/resumen")
@rol_requerido("admin", "vendedor")
def resumen():

    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) total FROM productos")
    productos = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) total FROM usuarios")
    usuarios = cur.fetchone()["total"]

    cur.execute("""
    SELECT IFNULL(SUM(total),0) total
    FROM ventas
    WHERE DATE(fecha)=DATE('now')
    """)
    ventas = cur.fetchone()["total"]

    con.close()

    return {
        "productos": productos,
        "usuarios": usuarios,
        "ventas": ventas
    }


@app.route("/api/ventas-dia")
@rol_requerido("admin", "vendedor")
def ventas_dia():

    con = conectar()
    cur = con.cursor()

    cur.execute("""
    SELECT DATE(fecha) fecha,
           SUM(total) total
    FROM ventas
    GROUP BY DATE(fecha)
    ORDER BY fecha
    """)

    datos = cur.fetchall()
    con.close()

    return jsonify({
        "labels": [x["fecha"] for x in datos],
        "valores": [x["total"] for x in datos]
    })


if __name__ == "__main__":
    app.run()