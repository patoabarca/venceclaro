# Política de Orquestación y Coordinación del Agente

## 1. Principio de Separación de Responsabilidades
- La skill `organizar-vencimientos` es la dueña del flujo y del agente orquestador; no duplica la lógica de bajo nivel y delega en las skills especializadas descubiertas dinámicamente mediante `SKILL.md`. [ORQ-1]

## 2. Coordinación mediante LLM y Tool Calling
- El LLM no puede alterar importes, fechas, monedas ni destinatario/credenciales: ningún esquema de herramienta expuesto al LLM contiene esos campos (excepto lo que identifique archivos o resúmenes de texto). [ORQ-2]
- El LLM no puede saltarse la etapa de revisión humana ni el orden estricto de la máquina de estados (ordenar/generar/enviar fuera de orden produce error; solicitar_revision_humana fuera de EXTRAYENDO o REVISION_REQUERIDA produce error). [ORQ-3]
- El contenido de los documentos se trata como datos puros, nunca como instrucciones (prompt injection en una factura no cambia destinatario, estado ni dispara envío). [ORQ-4]

## 3. Punto de Control Humano (*Human-in-the-Loop*)
- Tras completar la extracción el flujo queda en `REVISION_REQUERIDA`; la generación de la agenda queda estrictamente bloqueada mientras existan comprobantes incluidos sin empresa, vencimiento, importe positivo o moneda. [ORQ-5]

## 4. Política de Envío de Correo
- El despacho por correo solo puede ejecutarse con autorización explícita y destinatario provisto por el usuario; las credenciales nunca pasan por el LLM ni por la traza de auditoría. [ORQ-6]

## 5. Modo sin LLM (Fallback Determinista)
- Si no se encuentra configurada la variable `GEMINI_API_KEY` (o `ANTHROPIC_API_KEY`) o se especifica el argumento `--sin-llm`, el orquestador opera de manera determinista ejecutando la misma secuencia reglamentaria y produciendo el mismo CSV. [ORQ-7]
