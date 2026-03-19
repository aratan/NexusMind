---
name: duckduckgo-search
description: Realiza búsquedas en tiempo real en internet mediante DuckDuckGo, con fallback a Google Scraping si no hay resultados. Ideal para obtener noticias actuales, datos técnicos o información que no está en el entrenamiento del modelo.
author: "Aratan/Coders"
version: "1.0.0"
capabilities:
  - web_search
  - internet_access
---

# DuckDuckGo Search Skill

Este skill permite al agente navegar por la web abierta para encontrar información actualizada.

## Criterios de Activación
- Cuando el usuario pregunte por noticias recientes.
- Cuando se requiera verificar un dato actual o buscar documentación técnica online.
- Cuando la información solicitada sea posterior al corte de conocimiento del modelo.

## Instrucciones de Ejecución
1. El worker ejecutará el archivo `run.py`.
2. Se debe pasar la consulta como argumento.
3. El resultado será una lista de títulos y fragmentos (snippets) de los primeros 3 resultados.

## Formato de Uso para el LLM
<TOOL>duckduckgo-search|tu consulta de búsqueda aquí</TOOL>
