import httpx
import asyncio
from .config import load_config
import re
import wikipediaapi

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

async def search_wikipedia_ru(query):
    # Поиск по русской Википедии через API
    url = "https://ru.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": 1,
        "srlimit": 20,
    }
    headers = {"User-Agent": "LitGrabberBot/1.0 (https://github.com/yourrepo; youremail@example.com)"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        items = r.json().get("query", {}).get("search", [])
        results = []
        for item in items:
            title = item.get("title", "")
            # В Википедии нет авторов, переводчиков, ISBN и года публикации в API поиска
            results.append({
                "title": title,
                "authors": "Wikipedia contributors",
                "year": "",
                "translator": "",
                "translation_year": "",
                "isbn_doi": "",
                "lang": "ru",
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

async def get_wikipedia_book_metadata(title):
    wiki = wikipediaapi.Wikipedia('ru', user_agent='LitGrabberBot/1.0 (https://github.com/yourrepo; youremail@example.com)')
    page = wiki.page(title)
    if not page.exists():
        return {"summary": "", "wikipedia_url": "", "year": ""}
    summary = page.summary
    fullurl = page.fullurl
    year_match = re.search(r"(1[89][0-9]{2}|20[0-2][0-9])", summary)
    year = year_match.group(0) if year_match else ""
    return {
        "summary": summary,
        "wikipedia_url": fullurl,
        "year": year,
    } 