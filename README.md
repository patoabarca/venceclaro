# VenceClaro - Organizador de Vencimientos con Agente LLM y 5 Skills

**VenceClaro** es un proyecto educativo (Python 3.10+, Windows, Streamlit) que organiza vencimientos de facturas en PDF. Demuestra la arquitectura solicitada por la cátedra: **un agente orquestador que usa un Modelo de Lenguaje (LLM) y delega en skills especializadas descubiertas dinámicamente desde sus especificaciones `SKILL.md`**, incorporando **envío de agenda por correo electrónico real** mediante Gmail SMTP con TLS.

---

## 1. Arquitectura: Agente con LLM y 5 Skills

El orquestador central (`organizar-vencimientos`) es el dueño del flujo y del agente. Descubre las skills disponibles en `skills/`, extrae sus contratos (`SKILL.md` y `ESQUEMA_ENTRADA`) y las pone a disposición del LLM como herramientas (*Tool Calling* / *Function Calling*):

```mermaid
flowchart TD
    Usuario([Usuario]) -->|1. Carga comprobantes PDF| UI[Interfaz Streamlit / CLI]
    UI -->|2. Inicia procesamiento| Orq["Skill Orquestadora: organizar-vencimientos (OrquestadorVencimientos)"]

    subgraph Registro ["Registro Dinámico de Skills (core/skill_loader.py)"]
        Orq -->|Descubre metadatos YAML y Esquemas JSON| Discovery[Descubrimiento de Skills]
        Discovery -.-> S1["extraer-vencimiento/SKILL.md"]
        Discovery -.-> S2["ordenar-vencimientos/SKILL.md"]
        Discovery -.-> S3["generar-agenda/SKILL.md"]
        Discovery -.-> S4["enviar-agenda/SKILL.md"]
    end

    subgraph AgenteLLM ["Bucle de Agente con LLM y Guardas de Estado"]
        Orq <-->|Prompt + Herramientas <-> Tool Call| LLM["LLM: Anthropic Claude / Fallback Determinista"]
        Orq -->|Guarda de Estado y Validación| Ejecutor[Despachador de Herramientas]
    end

    Ejecutor -->|Tool Call 1| SkillExt["Skill: extraer-vencimiento"]
    SkillExt -->|Retorna FacturaExtraida + Evidencia| Orq

    Orq -->|Punto de Control Obligatorio: Human-in-the-Loop| Revision{Revisión Humana Requerida}
    Revision -->|Usuario edita campos o excluye facturas| Usuario
    Usuario -->|3. Confirmación explícita de datos| Orq

    Orq -->|Tool Call 2| SkillOrd["Skill: ordenar-vencimientos"]
    SkillOrd -->|Retorna lista ordenada cronológicamente| Orq

    Orq -->|Tool Call 3| SkillGen["Skill: generar-agenda"]
    SkillGen -->|Retorna CSV regional ; + BOM + Totales| Orq

    opt Si el usuario autoriza explícitamente el envío
        Usuario -->|Autoriza envío a correo@dominio.com| Orq
        Orq -->|Tool Call 4: Con credenciales protegidas| SkillEnv["Skill: enviar-agenda"]
        SkillEnv -->|SMTP Gmail TLS 587 / Dry-Run| SMTP[Servidor Gmail / Simulación]
    end

    Orq -->|4. Entrega agenda, traza y métricas| UI
    UI -->|5. Descarga agenda_vencimientos.csv| Usuario
```

---

## 2. Roles y Responsabilidades de las 5 Skills

1. **`organizar-vencimientos` (Skill Orquestadora)**:
   - Dueña del flujo y del agente (`OrquestadorVencimientos`).
   - Descubre dinámicamente las demás skills inspeccionando sus `SKILL.md`.
   - Consulta al LLM (Anthropic Claude) para decidir qué herramienta ejecutar y redactar resúmenes explicativos para el usuario.
   - Aplica **guardas deterministas en código**: el LLM no puede saltarse la revisión humana, ni calcular importes, ni enviar correos sin autorización.
2. **`extraer-vencimiento` (Skill Especializada)**:
   - Transforma cada documento PDF con texto seleccionable en un registro estructurado (`FacturaExtraida`), preservando la evidencia textual de respaldo.
3. **`ordenar-vencimientos` (Skill Especializada)**:
   - Ordena cronológicamente los registros confirmados por fecha de vencimiento ascendente (`AAAA-MM-DD`). Desempate estable por empresa emisora y archivo.
4. **`generar-agenda` (Skill Especializada)**:
   - Produce el archivo CSV con delimitador punto y coma (`;`), separador decimal coma (`,`), codificación `UTF-8 con BOM` para Microsoft Excel y **segregación estricta de monedas** (nunca mezcla pesos con dólares).
5. **`enviar-agenda` (Skill Especializada)**:
   - Despacha la agenda vía Gmail SMTP con cifrado STARTTLS en el puerto 587, adjuntando el CSV y presentando el resumen financiero en el cuerpo del correo.
   - **Envío real y explícito:** si faltan credenciales y no se solicita `dry_run=True`, devuelve un error claro (no simula en silencio).

---

## 3. Lo que el LLM HACE y lo que el LLM NO HACE (Seguridad y Veracidad)

### Lo que el LLM SÍ hace:
- Evalúa el estado del lote y decide dinámicamente qué skill invocar mediante llamadas a herramientas (*Tool Calling*).
- Redacta el resumen explicativo de la extracción para el usuario (qué se detectó, qué es ambiguo y qué requiere atención).
- Redacta el saludo y texto introductorio personalizado que acompaña el correo electrónico.

### Lo que el LLM NUNCA hace (Guardas de Seguridad):
- **NO calcula, modifica ni inventa importes, fechas ni monedas:** Esas tareas son realizadas 100% por código determinista y validadas por el usuario.
- **NO define el destinatario del correo:** El correo de destino lo ingresa el usuario en la UI o en el CLI; el LLM jamás lo inventa ni lo extrae del PDF.
- **NO manipula credenciales:** La contraseña de aplicación de Gmail se lee del entorno `.env` en la skill de envío; nunca pasa por el LLM ni por logs.
- **Protección contra Prompt Injection:** El texto extraído de las facturas se trata estrictamente como **datos inofensivos**, nunca como órdenes o comandos para el modelo.

---

## 4. Instalación y Configuración

### 4.1. Requisitos
- Python 3.10 o superior (probado en Windows con Python 3.13).
- Dependencias declaradas en `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

### 4.2. Variables de Entorno (`.env`)
Creá un archivo `.env` en la raíz de `venceclaro` (basado en `.env.example`):

```bash
# 1. Clave de API de Anthropic Claude (para el Agente Orquestador con LLM)
ANTHROPIC_API_KEY=tu_clave_de_anthropic_aqui
LLM_MODEL=claude-3-5-sonnet-20241022

# 2. Credenciales para envío real por Gmail (Skill: enviar-agenda)
GMAIL_REMITENTE=tu_cuenta@gmail.com
# Contraseña de Aplicación de 16 letras generada en Google > Seguridad > Contraseñas de aplicaciones:
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

> [!NOTE]
> **Modo sin LLM (Fallback Determinista):** Si no contás con una clave de Anthropic, el sistema funciona automáticamente en modo determinista local con guardas de estado completas.

---

## 5. Ejecución del Proyecto

### 5.1. Interfaz Web (Streamlit)
```bash
streamlit run app.py
```
Permite cargar facturas PDF de a una o en lotes acumulativos, ver la **traza de decisiones del agente**, revisar los comprobantes, confirmar la agenda, descargar el CSV para Excel y despachar el correo (real o simulado).

### 5.2. Terminal / CLI (Skill Orquestadora)

#### En Windows (PowerShell / CMD) con Python directo:
- **Flujo completo con autoconfirmación y salida CSV:**
  ```bash
  python skills/organizar-vencimientos/scripts/ejecutar.py ejemplos/factura_edesur_luz.pdf ejemplos/factura_telecom_internet.pdf --salida agenda.csv --auto-confirmar
  ```
- **Flujo completo con envío de correo real:**
  ```bash
  python skills/organizar-vencimientos/scripts/ejecutar.py ejemplos/factura_edesur_luz.pdf --salida agenda.csv --auto-confirmar --enviar-a tu_correo@gmail.com
  ```
- **Flujo en modo simulación (dry-run):**
  ```bash
  python skills/organizar-vencimientos/scripts/ejecutar.py ejemplos/factura_edesur_luz.pdf --salida agenda.csv --auto-confirmar --enviar-a tu_correo@gmail.com --dry-run
  ```
- **Modo puramente determinista (sin LLM):**
  ```bash
  python skills/organizar-vencimientos/scripts/ejecutar.py ejemplos/factura_edesur_luz.pdf --salida agenda.csv --auto-confirmar --sin-llm
  ```

#### En entornos Bash (Linux, macOS, Git Bash o WSL):
Los scripts `.sh` tienen formato de fin de línea Unix (LF) y delegan en el CLI:
```bash
bash skills/organizar-vencimientos/scripts/ejecutar.sh ejemplos/factura_edesur_luz.pdf --salida agenda.csv --auto-confirmar --dry-run
```

---

## 6. Pruebas Automatizadas

La suite completa se ejecuta sin requerir conexión a internet ni consumir credenciales reales (utiliza `ClienteLLMFalso` y mocks de `smtplib.SMTP`):

```bash
pytest tests -v
```

Cobertura verificada:
- Descubrimiento de las 5 skills y validación de `SKILL.md` y `ESQUEMA_ENTRADA`.
- Delegación por nombre e invocación mediante el contrato `invocar(entrada)`.
- Orquestación con LLM falso guionado (orden estricto y resumen).
- Rechazo de guardas (intento de enviar antes de confirmar, ordenamiento sin revisión).
- Protección anti prompt-injection en facturas.
- Envío real mockeado con STARTTLS y manejo de `SMTPAuthenticationError` sin exponer contraseñas.
- Fallback determinista sin LLM que genera exactamente el mismo CSV regional.
