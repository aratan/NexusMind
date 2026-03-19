# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import urllib.parse
import re

def search(query):
    try:
        url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if not data['query']['search']:
                return "No se encontraron resultados."
            snippets = [item['snippet'] for item in data['query']['search'][:3]]
            texto = " ".join(snippets)
            # Limpiar HTML sencillo
            return re.sub(r'<[^>]+>', '', texto)
    except Exception as e:
        return f"Error searching: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(search(" ".join(sys.argv[1:])))
    else:
        print("Argumento requerido: query")
