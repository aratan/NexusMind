from duckduckgo_search import DDGS
import sys

# Script para búsqueda en internet usando DuckDuckGo
# Usado por el sistema de Agents de Aratan/Coders

import httpx
from bs4 import BeautifulSoup
import random

def google_scrape(query):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        url = f"https://www.google.com/search?q={query}"
        response = httpx.get(url, headers=headers, follow_redirects=True)
        
        if response.status_code != 200:
            return f"Error en Google Scraping: Status {response.status_code}"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Google search results are usually in divs with class 'g'
        for g in soup.select('.g'):
            title_tag = g.select_one('h3')
            snippet_tag = g.select_one('.VwiC3b') # One common class for snippets
            link_tag = g.select_one('a')
            
            if title_tag and link_tag:
                title = title_tag.get_text()
                url = link_tag['href']
                snippet = snippet_tag.get_text() if snippet_tag else "No snippet available"
                results.append(f"Result: {title}\nSnippet: {snippet}\nURL: {url}\n")
            
            if len(results) >= 3:
                break
                
        if not results:
            return "No se encontraron resultados en Google Scraping."
            
        return "\n---\n".join(results)
    except Exception as e:
        return f"Error en Google Scraping: {str(e)}"

def search(query):
    results_ddg = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results_ddg.append(f"Result: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n")
    except Exception as e:
        print(f"DuckDuckGo error (falling back): {e}", file=sys.stderr)

    if results_ddg:
        return "\n---\n".join(results_ddg)
    
    # Fallback to Google Scraping
    print("DuckDuckGo fail/empty. Using Google Search fallback...", file=sys.stderr)
    return google_scrape(query)

if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(search(query))
    else:
        print("Uso: python run.py 'termino de búsqueda'")
