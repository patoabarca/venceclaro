"""
Generador de facturas sintéticas en PDF con texto seleccionable para VenceClaro.
Todos los datos son ficticios y educativos, creados sin información de personas reales.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def crear_factura_edesur(ruta: Path):
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "EDESUR S.A. - Factura de Electricidad")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Razón Social: Edesur S.A. | CUIT: 30-65511697-3")
    c.drawString(50, 715, "Domicilio de suministro: Av. Ejemplo 1234, CABA")
    c.line(50, 705, 550, 705)

    c.drawString(50, 680, "Fecha de Emisión: 01/06/2026")
    c.drawString(50, 665, "Período Facturado: Mayo 2026")
    c.drawString(50, 650, "Servicio: Suministro de Energía Eléctrica Residencial T1R")

    c.drawString(50, 610, "Detalle del Consumo: 380 kWh")
    c.drawString(50, 595, "Subtotal Cargo Fijo y Variable: $ 21.017,15")
    c.drawString(50, 580, "IVA (21%): $ 4.413,60")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 540, "FECHA DE VENCIMIENTO: 15/06/2026")
    c.drawString(50, 520, "TOTAL A PAGAR: ARS 25.430,75")
    c.setFont("Helvetica", 9)
    c.drawString(50, 480, "Moneda: Pesos Argentinos (ARS)")
    c.save()


def crear_factura_telecom(ruta: Path):
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "TELECOM ARGENTINA S.A.")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Servicio de Conectividad Fibra Óptica e Internet Banda Ancha")
    c.drawString(50, 715, "Cliente N°: 88472910 | Cuenta: 001-992384")
    c.line(50, 705, 550, 705)

    c.drawString(50, 680, "Fecha de emisión: 10/05/2026")
    c.drawString(50, 665, "Plan Fibra 500 Megas Simétricos")

    c.drawString(50, 620, "Subtotal de servicios: $ 123.100,00")
    c.drawString(50, 605, "Impuestos y percepciones: $ 25.850,25")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 550, "1er Vto.: 28/05/2026")
    c.drawString(50, 530, "IMPORTE TOTAL: ARS 148.950,25")
    c.save()


def crear_factura_aysa(ruta: Path):
    # Vence en 2027 para comprobar ordenamiento multianual
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "AySA - Agua y Saneamientos Argentinos S.A.")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Factura de Agua Potable y Desagües Cloacales")
    c.line(50, 715, 550, 715)

    c.drawString(50, 690, "Fecha de Emisión: 15/12/2026")
    c.drawString(50, 675, "Régimen No Medido Residencial")

    c.drawString(50, 630, "Subtotal: $ 10.165,29")
    c.drawString(50, 615, "IVA: $ 2.134,71")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 560, "Vencimiento Actual: 10/01/2027")
    c.drawString(50, 540, "Total Factura: ARS 12.300,00")
    c.save()


def crear_factura_ambigua(ruta: Path):
    # Contiene múltiples vencimientos y ambigüedad de símbolo '$'
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "METROGAS S.A.")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Distribución de Gas Natural")
    c.line(50, 715, 550, 715)

    c.drawString(50, 680, "Fecha de Emisión: 05/06/2026")
    c.drawString(50, 650, "Subtotal: $ 15.000,00")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 600, "1er Vencimiento: 20/06/2026  - Total a pagar: $ 18.500,00")
    c.drawString(50, 580, "2do Vencimiento: 30/06/2026  - Total a pagar: $ 19.200,00")
    c.setFont("Helvetica", 9)
    c.drawString(50, 550, "Nota: Los importes incluyen recargo por pago fuera de término.")
    c.save()


def crear_factura_usd_cloud(ruta: Path):
    # Factura en moneda extranjera (USD)
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Amazon Web Services Inc.")
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Invoice for Cloud Computing and Hosting Services")
    c.line(50, 715, 550, 715)

    c.drawString(50, 680, "Date of Issue: 01/08/2026")
    c.drawString(50, 665, "Services: EC2, S3 Storage, Route53")

    c.drawString(50, 620, "Subtotal: USD 45,50")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 560, "Payment Due: 05/08/2026")
    c.drawString(50, 540, "Total a pagar: USD 45,50")
    c.save()


def crear_factura_sin_texto(ruta: Path):
    # Simula un documento escaneado o dibujo vectorial sin capa de texto seleccionable
    c = canvas.Canvas(str(ruta), pagesize=letter)
    c.rect(100, 400, 400, 250, fill=0)
    c.line(100, 600, 500, 600)
    c.line(100, 550, 500, 550)
    c.circle(300, 480, 40, stroke=1, fill=0)
    # No se escribe ningún texto con c.drawString
    c.save()


def generar_todas():
    base = Path(__file__).resolve().parent
    print(f"Generando facturas sintéticas en {base}...")

    crear_factura_edesur(base / "factura_edesur_luz.pdf")
    crear_factura_telecom(base / "factura_telecom_internet.pdf")
    crear_factura_aysa(base / "factura_aysa_agua.pdf")
    crear_factura_ambigua(base / "factura_ambigua_montos.pdf")
    crear_factura_usd_cloud(base / "factura_usd_nube.pdf")
    crear_factura_sin_texto(base / "factura_sin_texto.pdf")

    print("Generación completada: 6 facturas sintéticas creadas.")


if __name__ == "__main__":
    generar_todas()
