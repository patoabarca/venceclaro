from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

# Asegurar que BASE_DIR esté en sys.path para imports de core y skills
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


@dataclass
class InfoSkill:
    """Metadatos e información de descubrimiento de una skill según su SKILL.md."""
    nombre: str
    descripcion: str
    carpeta: Path
    modulo_entrada: Path
    referencias: List[Path]


@dataclass
class Skill:
    """Representación ejecutable de una skill registrada."""
    nombre: str
    descripcion: str
    esquema_entrada: Dict[str, Any]
    invocar: Callable[[Dict[str, Any]], Dict[str, Any]]
    info: InfoSkill


def parsear_frontmatter_yaml(ruta_skill_md: Path) -> Dict[str, Any]:
    """Extrae el frontmatter YAML delimitado por --- al inicio de SKILL.md."""
    contenido = ruta_skill_md.read_text(encoding="utf-8")
    partes = re.split(r"^---\s*$", contenido, maxsplit=2, flags=re.MULTILINE)
    if len(partes) < 3:
        raise ValueError(f"El archivo {ruta_skill_md} no contiene un frontmatter YAML válido delimitado por ---.")
    bloque_yaml = partes[1]
    datos = yaml.safe_load(bloque_yaml)
    if not isinstance(datos, dict):
        raise ValueError(f"El frontmatter YAML en {ruta_skill_md} no es un diccionario válido.")
    return datos


def descubrir_skills(skills_dir: Optional[Path] = None) -> Dict[str, InfoSkill]:
    """
    Recorre skills/*/SKILL.md, parsea el frontmatter (name, description)
    y valida:
      1. name del frontmatter == nombre de la carpeta
      2. Existe un único módulo .py en la raíz de la carpeta de la skill
      3. Recopila referencias/*.md
    Devuelve un diccionario {nombre_skill: InfoSkill}.
    """
    directorio_base = skills_dir or (BASE_DIR / "skills")
    if not directorio_base.exists() or not directorio_base.is_dir():
        raise FileNotFoundError(f"El directorio de skills no existe: {directorio_base}")

    skills_descubiertas: Dict[str, InfoSkill] = {}

    for subcarpeta in sorted(directorio_base.iterdir()):
        if not subcarpeta.is_dir():
            continue

        skill_md = subcarpeta / "SKILL.md"
        if not skill_md.exists():
            continue

        frontmatter = parsear_frontmatter_yaml(skill_md)
        nombre = frontmatter.get("name")
        descripcion = frontmatter.get("description", "").strip()

        if not nombre:
            raise ValueError(f"Falta el campo 'name' en el frontmatter de {skill_md}")

        # Validación estricta: name == nombre de carpeta
        if nombre != subcarpeta.name:
            raise ValueError(
                f"Inconsistencia en skill: el 'name' en {skill_md} ('{nombre}') "
                f"no coincide con el nombre de la carpeta ('{subcarpeta.name}')."
            )

        # Validar único módulo .py en la raíz de la skill
        archivos_py_raiz = [
            f for f in subcarpeta.glob("*.py")
            if f.is_file() and not f.name.startswith("__")
        ]
        if len(archivos_py_raiz) != 1:
            raise ValueError(
                f"La skill '{nombre}' debe tener exactamente un archivo Python en su raíz, "
                f"pero se encontraron {len(archivos_py_raiz)}: {[f.name for f in archivos_py_raiz]}."
            )
        modulo_entrada = archivos_py_raiz[0]

        # Recopilar referencias/*.md
        referencias = []
        carpeta_refs = subcarpeta / "references"
        if carpeta_refs.exists() and carpeta_refs.is_dir():
            referencias = sorted(list(carpeta_refs.glob("*.md")))

        info = InfoSkill(
            nombre=nombre,
            descripcion=descripcion,
            carpeta=subcarpeta,
            modulo_entrada=modulo_entrada,
            referencias=referencias,
        )
        skills_descubiertas[nombre] = info

    return skills_descubiertas


# Cache de módulos cargados dinámicamente
_MODULOS_SKILL_CACHE: Dict[str, Any] = {}


def _cargar_modulo_python(nombre_skill: str, ruta_archivo: Path) -> Any:
    clave = f"venceclaro_skill_{nombre_skill.replace('-', '_')}"
    if clave in sys.modules:
        return sys.modules[clave]
    if clave in _MODULOS_SKILL_CACHE:
        return _MODULOS_SKILL_CACHE[clave]

    spec = importlib.util.spec_from_file_location(clave, ruta_archivo)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar el spec para {ruta_archivo}")

    modulo = importlib.util.module_from_spec(spec)
    sys.modules[clave] = modulo
    _MODULOS_SKILL_CACHE[clave] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def obtener_skill(nombre: str, skills_dir: Optional[Path] = None) -> Skill:
    """
    Obtiene la instancia de Skill para un nombre dado tras descubrirla y validarla.
    Verifica que el módulo exponga:
      - ESQUEMA_ENTRADA (dict JSON Schema)
      - invocar(entrada: dict) -> dict
    """
    skills = descubrir_skills(skills_dir)
    if nombre not in skills:
        skills_disponibles = ", ".join(sorted(skills.keys()))
        raise KeyError(f"Skill '{nombre}' no encontrada. Disponibles: [{skills_disponibles}]")

    info = skills[nombre]
    modulo = _cargar_modulo_python(info.nombre, info.modulo_entrada)

    if not hasattr(modulo, "ESQUEMA_ENTRADA"):
        raise AttributeError(
            f"El módulo {info.modulo_entrada} de la skill '{nombre}' no define 'ESQUEMA_ENTRADA'."
        )
    esquema_entrada = getattr(modulo, "ESQUEMA_ENTRADA")
    if not isinstance(esquema_entrada, dict):
        raise TypeError(
            f"'ESQUEMA_ENTRADA' en {info.modulo_entrada} debe ser un dict con JSON Schema."
        )

    if not hasattr(modulo, "invocar") or not callable(getattr(modulo, "invocar")):
        raise AttributeError(
            f"El módulo {info.modulo_entrada} de la skill '{nombre}' no expone la función 'invocar(entrada: dict)'."
        )
    invocar_fn = getattr(modulo, "invocar")

    return Skill(
        nombre=info.nombre,
        descripcion=info.descripcion,
        esquema_entrada=esquema_entrada,
        invocar=invocar_fn,
        info=info,
    )


def obtener_orquestador():
    """Atajo limpio para obtener el módulo de la skill orquestadora."""
    info = descubrir_skills()["organizar-vencimientos"]
    return _cargar_modulo_python("organizar-vencimientos", info.modulo_entrada)
