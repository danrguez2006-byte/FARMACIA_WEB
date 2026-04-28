import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generar_ticket(venta_id, total):
    carpeta = "tickets"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    nombre = f"ticket_{venta_id}.pdf"
    ruta = os.path.join(carpeta, nombre)

    doc = SimpleDocTemplate(ruta)
    styles = getSampleStyleSheet()

    contenido = [
        Paragraph("Farmacia", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Venta ID: {venta_id}", styles["Normal"]),
        Paragraph(f"Total: ${total:.2f}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Gracias por su compra", styles["Normal"]),
        Paragraph("Sistema de Farmacia", styles["Normal"])
    ]

    doc.build(contenido)

    return nombre