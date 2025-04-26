import httpx
import asyncio
from .config import load_config

async def search_openlibrary(query):
    url = "https://openlibrary.org/search.json"
    params = {"q": query}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        docs = r.json().get("docs", [])
        results = []
        for d in docs:
            results.append({
                "title": d.get("title", ""),
                "authors": ", ".join(d.get("author_name", [])),
                "year": d.get("first_publish_year", ""),
                "translator": ", ".join(d.get("translator", [])) if d.get("translator") else "",
                "translation_year": "",
                "isbn_doi": d.get("isbn", [""])[0] if d.get("isbn") else d.get("oclc", [""])[0] if d.get("oclc") else "",
                "lang": d.get("language", [""])[0] if d.get("language") else "",
            })
        return results

async def search_deepseek(query):
    # Placeholder: Deepseek API integration
    # Return empty for now
    return []

async def search_googlebooks(query):
    config = load_config()
    api_key = config.get("api_keys", {}).get("googlebooks", "")
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": 20}
    if api_key:
        params["key"] = api_key
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        items = r.json().get("items", [])
        results = []
        for item in items:
            info = item.get("volumeInfo", {})
            title = info.get("title", "")
            authors = ", ".join(info.get("authors", []))
            year = info.get("publishedDate", "")[:4] if info.get("publishedDate") else ""
            lang = info.get("language", "")
            isbn = ""
            for iden in info.get("industryIdentifiers", []):
                if iden.get("type", "").startswith("ISBN"):
                    isbn = iden.get("identifier", "")
                    break
            results.append({
                "title": title,
                "authors": authors,
                "year": year,
                "translator": "",
                "translation_year": "",
                "isbn_doi": isbn,
                "lang": lang,
            })
        return results

async def aggregate_search(query):
    ol, ds, gb = await asyncio.gather(
        search_openlibrary(query),
        search_deepseek(query),
        search_googlebooks(query)
    )
    results = ol + ds + gb
    # Deduplicate by title+author
    seen = set()
    deduped = []
    for r in results:
        key = (r["title"].lower(), r["authors"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped 