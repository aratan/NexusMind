---
name: wikipedia-search
description: Busca términos en la Wikipedia en español y extrae fragmentos de texto (snippets) de los primeros 3 resultados. Úsalo cuando necesites datos enciclopédicos rápidos.
author: "Aratan/Coders"
version: "1.0.0"
capabilities:
  - web_search
  - text_extraction
---

# Wikipedia Search Skill

Este skill permite al agente consultar la API de Wikipedia para obtener resúmenes rápidos sin procesar HTML complejo.

## Criterios de Activación
- Cuando el usuario pida "buscar en wikipedia", "consultar wiki" o "investigar sobre [tema]".
- Cuando se requiera una definición formal o contexto histórico rápido.

## Instrucciones de Ejecución
1. **Validación**: Asegurarse de que el argumento `query` no esté vacío.
2. **Llamada**: Ejecutar el script `run.py` pasando el término de búsqueda como argumento posicional.
3. **Procesamiento**: El script devolverá texto plano (snippets unidos). Si no hay resultados, informará al usuario.

## Interfaz del Tool

## Available scripts

- **`scripts/run.py`** — Processes input data

```bash
   python scripts/run.py --input "$query"
