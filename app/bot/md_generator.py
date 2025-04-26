from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from .config import load_config
import re

# Always resolve templates from project root
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

def sanitize_filename(s):
    return re.sub(r'[^\w\-., ]', '', s)

def make_filename(author, title):
    first = author.split()[0][0]
    last = author.split()[-1]
    base = f"{first}. {last}, {title[:50]}"
    if len(title) > 50:
        base += "..."
    return sanitize_filename(base)

def render_md(metadata: dict, with_priority: bool):
    config = load_config()
    output_folder = Path(config["output_folder"])
    output_folder.mkdir(parents=True, exist_ok=True)
    template_name = "template_with_priority.md" if with_priority else "template_without_priority.md"
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    content = template.render(**metadata)
    filename = make_filename(metadata["authors"].split(",")[0], metadata["title"])
    path = output_folder / f"{filename}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(path) 