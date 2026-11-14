from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

BASE_DIR = Path(__file__).resolve().parent.parent

# Asegurar que BASE_DIR esté en sys.path para que los módulos internos encuentren 'core'
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def cargar_modulo_skill(nombre_skill: str, nombre_archivo: str) -> ModuleType:
    """
    Carga dinámicamente un módulo de Python ubicado dentro de la carpeta de una skill
    cuyo nombre contiene guiones (ej: 'extraer-vencimiento').
    Registra el módulo en sys.modules para permitir importaciones circulares o reutilización.
    """
    ruta_modulo = BASE_DIR / "skills" / nombre_skill / f"{nombre_archivo}.py"
    if not ruta_modulo.exists():
        raise FileNotFoundError(f"No existe el archivo de skill: {ruta_modulo}")

    nombre_clave = f"venceclaro_skill_{nombre_skill.replace('-', '_')}_{nombre_archivo}"
    if nombre_clave in sys.modules:
        return sys.modules[nombre_clave]

    spec = importlib.util.spec_from_file_location(nombre_clave, ruta_modulo)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo crear spec para {ruta_modulo}")

    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre_clave] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# Atajos directos a las funciones de las skills para máxima conveniencia y tipado
def obtener_extractor():
    return cargar_modulo_skill("extraer-vencimiento", "extractor")


def obtener_ordenador():
    return cargar_modulo_skill("ordenar-vencimientos", "ordenador")


def obtener_generador():
    return cargar_modulo_skill("generar-agenda", "generador")


def obtener_remitente():
    return cargar_modulo_skill("enviar-agenda", "remitente")
