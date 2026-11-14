import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EJEMPLOS_DIR = BASE_DIR / "ejemplos"


def test_cli_extraer_vencimiento():
    script = BASE_DIR / "skills" / "extraer-vencimiento" / "scripts" / "ejecutar.py"
    factura = EJEMPLOS_DIR / "factura_edesur_luz.pdf"

    proc = subprocess.run(
        [sys.executable, str(script), str(factura), "--json"],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert proc.returncode == 0, f"Error en CLI extraer: {proc.stderr}"
    datos = json.loads(proc.stdout)
    assert isinstance(datos, list)
    assert len(datos) == 1
    assert datos[0]["empresa"] == "Edesur"
    assert datos[0]["fecha_vencimiento_visual"] == "15/06/2026"


def test_cli_ordenar_vencimientos(tmp_path):
    script = BASE_DIR / "skills" / "ordenar-vencimientos" / "scripts" / "ejecutar.py"
    entrada_json = tmp_path / "facturas.json"

    datos_entrada = [
        {
            "id": "1", "archivo_origen": "b.pdf", "empresa": "Telecom", "servicio": "Internet",
            "importe": 100.0, "moneda": "ARS", "fecha_vencimiento": "2026-07-01"
        },
        {
            "id": "2", "archivo_origen": "a.pdf", "empresa": "Edesur", "servicio": "Luz",
            "importe": 200.0, "moneda": "ARS", "fecha_vencimiento": "2026-05-10"
        }
    ]
    entrada_json.write_text(json.dumps(datos_entrada), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script), str(entrada_json), "--json"],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert proc.returncode == 0, f"Error en CLI ordenar: {proc.stderr}"
    ordenados = json.loads(proc.stdout)
    assert [r["id"] for r in ordenados] == ["2", "1"]


def test_cli_generar_agenda(tmp_path):
    script = BASE_DIR / "skills" / "generar-agenda" / "scripts" / "ejecutar.py"
    entrada_json = tmp_path / "ordenados.json"
    salida_csv = tmp_path / "agenda.csv"

    datos_entrada = [
        {
            "id": "1", "archivo_origen": "factura.pdf", "empresa": "Edesur", "servicio": "Luz",
            "importe": 25430.75, "moneda": "ARS", "fecha_vencimiento": "2026-06-15"
        }
    ]
    entrada_json.write_text(json.dumps(datos_entrada), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script), str(entrada_json), "--salida", str(salida_csv)],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert proc.returncode == 0, f"Error en CLI generar: {proc.stderr}"
    assert salida_csv.exists()
    contenido = salida_csv.read_text(encoding="utf-8-sig")
    assert "15/06/2026;Edesur;Luz;25.430,75;ARS;factura.pdf" in contenido


def test_cli_organizar_vencimientos_completo(tmp_path):
    script = BASE_DIR / "skills" / "organizar-vencimientos" / "scripts" / "ejecutar.py"
    factura1 = EJEMPLOS_DIR / "factura_edesur_luz.pdf"
    factura2 = EJEMPLOS_DIR / "factura_telecom_internet.pdf"
    salida_csv = tmp_path / "agenda_completa.csv"

    proc = subprocess.run(
        [
            sys.executable, str(script),
            str(factura1), str(factura2),
            "--salida", str(salida_csv),
            "--auto-confirmar",
            "--json"
        ],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert proc.returncode == 0, f"Error en CLI orquestador: {proc.stderr}"
    res = json.loads(proc.stdout)
    assert res["estado"] == "AGENDA_LISTA"
    assert salida_csv.exists()
    assert len(res["registros_ordenados"]) == 2


def test_cli_enviar_agenda_dry_run(tmp_path):
    script = BASE_DIR / "skills" / "enviar-agenda" / "scripts" / "ejecutar.py"
    csv_dummy = tmp_path / "agenda_prueba.csv"
    csv_dummy.write_text("Vencimiento;Empresa;Servicio;Importe;Moneda;Archivo\r\n", encoding="utf-8-sig")

    proc = subprocess.run(
        [
            sys.executable, str(script),
            "--destino", "prueba@diplomatura.com",
            "--csv", str(csv_dummy),
            "--dry-run"
        ],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert proc.returncode == 0, f"Error en CLI enviar: {proc.stderr}"
    assert "[SIMULACION]" in proc.stdout
    assert "prueba@diplomatura.com" in proc.stdout
