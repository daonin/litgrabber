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
    wiki = wikipediaapi.Wikipedia('LitGrabberBot/1.0 (https://github.com/yourrepo; youremail@example.com)', 'ru')
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

async def get_wikidata_book_metadata(title):
    url_search = "https://www.wikidata.org/w/api.php"
    params_search = {
        "action": "wbsearchentities",
        "search": title,
        "language": "ru",
        "format": "json",
        "type": "item",
        "limit": 1,
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url_search, params=params_search)
        r.raise_for_status()
        search_results = r.json().get("search", [])
        if not search_results:
            return {
                "title": title,
                "authors": "",
                "year": "",
                "translator": "",
                "isbn_doi": "",
                "lang": "",
                "translations": [],
                "wikidata_url": "",
            }
        entity_id = search_results[0]["id"]
        params_entity = {
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "props": "claims|labels|sitelinks",
            "languages": "ru|en",
        }
        r2 = await client.get(url_search, params=params_entity)
        r2.raise_for_status()
        entity = r2.json()["entities"][entity_id]
        claims = entity.get("claims", {})
        def get_claim(prop):
            vals = claims.get(prop, [])
            if not vals:
                return ""
            mainsnak = vals[0].get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", "")
            if isinstance(value, dict) and "id" in value:
                return value["id"]
            if isinstance(value, dict) and "time" in value:
                return value["time"][1:5]  # +1 чтобы убрать знак
            return value
        # Автор
        author_id = get_claim("P50")
        author = ""
        if author_id:
            params_author = {
                "action": "wbgetentities",
                "ids": author_id,
                "format": "json",
                "props": "labels",
                "languages": "ru|en",
            }
            r3 = await client.get(url_search, params=params_author)
            r3.raise_for_status()
            labels = r3.json()["entities"][author_id]["labels"]
            author = labels.get("ru", {}).get("value") or labels.get("en", {}).get("value", "")
        # Год публикации
        year = get_claim("P577")
        # Переводчик
        translator_id = get_claim("P655")
        translator = ""
        if translator_id:
            params_trans = {
                "action": "wbgetentities",
                "ids": translator_id,
                "format": "json",
                "props": "labels",
                "languages": "ru|en",
            }
            r4 = await client.get(url_search, params=params_trans)
            r4.raise_for_status()
            labels = r4.json()["entities"][translator_id]["labels"]
            translator = labels.get("ru", {}).get("value") or labels.get("en", {}).get("value", "")
        # ISBN
        isbn = get_claim("P212") or get_claim("P957")
        # Язык
        lang_id = get_claim("P407")
        lang = ""
        if lang_id:
            params_lang = {
                "action": "wbgetentities",
                "ids": lang_id,
                "format": "json",
                "props": "labels",
                "languages": "ru|en",
            }
            r5 = await client.get(url_search, params=params_lang)
            r5.raise_for_status()
            labels = r5.json()["entities"][lang_id]["labels"]
            lang = labels.get("ru", {}).get("value") or labels.get("en", {}).get("value", "")
        # Ссылки на переводы (sitelinks)
        sitelinks = entity.get("sitelinks", {})
        translations = [k for k in sitelinks.keys() if k.endswith("wiki")]
        return {
            "title": entity.get("labels", {}).get("ru", {}).get("value", title),
            "authors": author,
            "year": year,
            "translator": translator,
            "isbn_doi": isbn,
            "lang": lang,
            "translations": translations,
            "wikidata_url": f"https://www.wikidata.org/wiki/{entity_id}",
        } 