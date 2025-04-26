# LitGrabber Telegram Bot

## Features
- Search books/articles by metadata (title, author, year, DOI, ISBN)
- Aggregates from Open Library, Deepseek (WIP)
- Returns 5 results at a time, with lazy loading
- Supports language/translation priority
- Save selected item as Markdown with tags and priority
- Access control by Telegram ID
- Dockerized, .md files saved outside container

## Setup
1. `cp config.yaml.example config.yaml` and edit your settings (Telegram token, allowed IDs, etc)
2. `docker build -t litgrabber .`
3. `docker run -v $(pwd)/output:/app/output litgrabber`

## Usage
- Send metadata to the bot (e.g. `Title: Foo, Author: Bar, Year: 2020`)
- Bot replies with 5 results
- Reply with `2, philosophy, logic. 10` to save item 2 with tags and priority
- Markdown file appears in `output/`
