import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from .config import load_config
from .access_control import is_allowed
from .search import aggregate_search, search_openlibrary, search_deepseek, search_googlebooks, search_wikipedia_ru, get_wikidata_book_metadata
from .md_generator import render_md
import re
import logging
import datetime

config = load_config()
tg_bot_token = config.get("telegram_bot_token")
bot = Bot(token=tg_bot_token)
dp = Dispatcher()

user_search_results = {}
START_TIME = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@dp.message(CommandStart())
async def start(msg: Message):
    if not is_allowed(msg.from_user.id):
        return
    await msg.answer("Send metadata: title, author, year, DOI, ISBN")

@dp.message(Command("version"))
async def version(msg: Message):
    if not is_allowed(msg.from_user.id):
        return
    await msg.answer(f"Build/start time: {START_TIME} UTC")

@dp.message()
async def handle_message(msg: Message):
    if not is_allowed(msg.from_user.id):
        return
    text = msg.text.strip()
    # If user replies with number, tags, priority
    m = re.match(r"^(\d+),\s*(.+)\.\s*(\d+)$", text)
    if m and msg.from_user.id in user_search_results:
        idx = int(m.group(1)) - 1
        tags = m.group(2)
        priority = m.group(3)
        results = user_search_results[msg.from_user.id]
        if 0 <= idx < len(results):
            item = results[idx]
            item["tags"] = tags
            item["priority"] = priority
            # --- enrich with Wikipedia metadata if needed ---
            if item.get("lang") == "ru" and item.get("authors") == "Wikipedia contributors":
                meta = await get_wikidata_book_metadata(item["title"])
                if meta.get("authors"): item["authors"] = meta["authors"]
                if meta.get("year"): item["year"] = meta["year"]
                if meta.get("translator"): item["translator"] = meta["translator"]
                if meta.get("isbn_doi"): item["isbn_doi"] = meta["isbn_doi"]
                if meta.get("lang"): item["lang"] = meta["lang"]
                if meta.get("wikidata_url"): item["wikidata_url"] = meta["wikidata_url"]
            # --- end enrich ---
            path = render_md(item, with_priority=True)
            await msg.answer(f"Saved to {path}")
        else:
            await msg.answer("Invalid item number.")
        return
    # If user replies with number and tags only (no priority)
    m2 = re.match(r"^(\d+),\s*(.+)$", text)
    if m2 and msg.from_user.id in user_search_results:
        idx = int(m2.group(1)) - 1
        tags = m2.group(2)
        results = user_search_results[msg.from_user.id]
        if 0 <= idx < len(results):
            item = results[idx]
            item["tags"] = tags
            item["priority"] = ""
            # --- enrich with Wikipedia metadata if needed ---
            if item.get("lang") == "ru" and item.get("authors") == "Wikipedia contributors":
                meta = await get_wikidata_book_metadata(item["title"])
                if meta.get("authors"): item["authors"] = meta["authors"]
                if meta.get("year"): item["year"] = meta["year"]
                if meta.get("translator"): item["translator"] = meta["translator"]
                if meta.get("isbn_doi"): item["isbn_doi"] = meta["isbn_doi"]
                if meta.get("lang"): item["lang"] = meta["lang"]
                if meta.get("wikidata_url"): item["wikidata_url"] = meta["wikidata_url"]
            # --- end enrich ---
            path = render_md(item, with_priority=False)
            await msg.answer(f"Saved to {path}")
        else:
            await msg.answer("Invalid item number.")
        return
    # Otherwise, treat as search
    await msg.answer("Searching...")
    # --- BEGIN: explicit source search support ---
    if ">" in text:
        prefix, real_query = text.split("<", 1)[0].split(">", 1)
        prefix = prefix.strip().lower()
        real_query = real_query.strip()
        if prefix == "google":
            results = await search_googlebooks(real_query)
        elif prefix == "openlib":
            results = await search_openlibrary(real_query)
        elif prefix == "deepseek":
            results = await search_deepseek(real_query)
        elif prefix == "wiki":
            results = await search_wikipedia_ru(real_query)
        else:
            results = await aggregate_search(text)
    else:
        results = await aggregate_search(text)
    # --- END: explicit source search support ---
    user_search_results[msg.from_user.id] = results
    if not results:
        await msg.answer("No results found.")
        return
    # Sort by language priority
    lang_priority = {l['code']: l['priority'] for l in config['languages']}
    def lang_sort_key(r):
        return lang_priority.get(r.get('lang', ''), 999)
    results.sort(key=lang_sort_key)
    # Show first 5
    msg_text = "".join([
        f"{i+1}. {r['title']} | {r['authors']} | {r['year']} | {r['lang']}\n"
        for i, r in enumerate(results[:5])
    ])
    if len(results) > 5:
        msg_text += "Send 'more' to see next 5."
    await msg.answer(msg_text)
    # Handle 'more' pagination
    user_search_results[msg.from_user.id+1000000] = 5  # offset

@dp.message(lambda m: m.text.strip().lower() == 'more')
async def more_results(msg: Message):
    if not is_allowed(msg.from_user.id):
        return
    results = user_search_results.get(msg.from_user.id, [])
    offset = user_search_results.get(msg.from_user.id+1000000, 0)
    if not results or offset >= len(results):
        await msg.answer("No more results.")
        return
    msg_text = "".join([
        f"{i+1}. {r['title']} | {r['authors']} | {r['year']} | {r['lang']}\n"
        for i, r in enumerate(results[offset:offset+5], start=offset)
    ])
    if offset+5 < len(results):
        msg_text += "Send 'more' to see next 5."
    await msg.answer(msg_text)
    user_search_results[msg.from_user.id+1000000] = offset+5

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main()) 
