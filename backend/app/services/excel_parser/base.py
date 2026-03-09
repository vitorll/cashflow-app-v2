from pathlib import Path

from .template_parser import TemplateParser


def parse_excel(path: Path | str) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    return TemplateParser(path).parse()
