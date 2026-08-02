#!/usr/bin/env python3
"""Scan, index, and publish QSL card images.

The workflow is intentionally simple:

1. Scan two sides of a card into a dated folder.
2. Generate per-card HTML that shows the front and back.
3. Generate date galleries with 24 fronts per page.
4. Optionally run a publish command such as rsync or scp.
5. Accept a cheap `poke` command so upload jobs can trigger a rebuild.

The script avoids third-party dependencies so it stays easy to run on a fresh
Debian install.
"""

from __future__ import annotations

import argparse
import configparser
import datetime as dt
import html
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_CONFIG = """\
[scanner]
device = brother5:bus2;dev6
resolution = 100
source = Automatic Document Feeder(left aligned,Duplex)
format = png

[paths]
output_root = ~/QSL/cards

[publish]
# Example rsync target:
# command = rsync -a --delete "{output_root}/" "user@example.com:/srv/www/qsl/cards/"
command =
"""


@dataclass(frozen=True)
class Card:
    date: dt.date
    callsign: str
    front: Path
    back: Path

    @property
    def day_dir(self) -> Path:
        return self.front.parent

    @property
    def slug(self) -> str:
        return self.callsign.lower()


def load_config(config_path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read_string(DEFAULT_CONFIG)
    if config_path.exists():
        parser.read(config_path)
    return parser


def config_path_from_args(args: argparse.Namespace) -> Path:
    if args.config:
        return Path(args.config).expanduser()
    return Path(__file__).with_name("config.ini")


def output_root(config: configparser.ConfigParser) -> Path:
    raw = config.get("paths", "output_root", fallback="~/QSL/cards")
    return Path(raw).expanduser()


def normalize_callsign(callsign: str) -> str:
    return callsign.strip().upper()


def parse_date(value: str | None) -> dt.date:
    if not value:
        return dt.date.today()
    return dt.date.fromisoformat(value)


def card_paths(root: Path, scan_date: dt.date, callsign: str) -> tuple[Path, Path, Path]:
    day_dir = root / f"{scan_date:%Y}" / f"{scan_date:%m}" / f"{scan_date:%d}"
    base = day_dir / normalize_callsign(callsign)
    return day_dir, day_dir / f"{base.name}.front.png", day_dir / f"{base.name}.back.png"


def card_html_path(card: Card) -> Path:
    return card.front.parent / f"{card.callsign}.html"


def scan_card(config: configparser.ConfigParser, callsign: str, scan_date: dt.date) -> Card:
    root = output_root(config)
    day_dir, front_path, back_path = card_paths(root, scan_date, callsign)
    day_dir.mkdir(parents=True, exist_ok=True)

    if front_path.exists() or back_path.exists():
        raise FileExistsError(f"card already exists: {front_path.stem.rsplit('.', 1)[0]}")

    scanner = config["scanner"]
    scanimage = shutil.which("scanimage")
    if not scanimage:
        raise RuntimeError("scanimage is not installed or not on PATH")

    temp_dir = Path(tempfile.mkdtemp(prefix="qslscan-"))
    try:
        batch_pattern = temp_dir / "scan-%d.png"
        command = [
            scanimage,
            "-d",
            scanner.get("device", "brother5:bus2;dev6"),
            "--format",
            scanner.get("format", "png"),
            "--resolution",
            scanner.get("resolution", "100"),
            "--AutoDocumentSize=yes",
            "--source",
            scanner.get("source", "Automatic Document Feeder(left aligned,Duplex)"),
            "--batch-count=2",
            "--batch-start=1",
            "--batch-print",
            f"--batch={batch_pattern}",
        ]
        subprocess.run(command, check=True)

        first = temp_dir / "scan-1.png"
        second = temp_dir / "scan-2.png"
        if not first.exists() or not second.exists():
            raise RuntimeError("scanner did not produce both output pages")

        shutil.move(str(first), front_path)
        shutil.move(str(second), back_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return Card(date=scan_date, callsign=normalize_callsign(callsign), front=front_path, back=back_path)


def discover_cards(root: Path) -> list[Card]:
    cards: list[Card] = []
    for front in sorted(root.rglob("*.front.png")):
        if len(front.parts) < 4:
            continue
        try:
            year = int(front.parent.parent.parent.name)
            month = int(front.parent.parent.name)
            day = int(front.parent.name)
            scan_date = dt.date(year, month, day)
        except ValueError:
            continue

        back = front.with_name(front.name.replace(".front.png", ".back.png"))
        if not back.exists():
            continue

        callsign = front.name[: -len(".front.png")]
        cards.append(Card(date=scan_date, callsign=callsign, front=front, back=back))
    return cards


def relative_link(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, start=from_file.parent).replace(os.sep, "/")


def html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f1e8;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #607080;
      --line: #d7d0c2;
      --accent: #8b5e34;
    }}
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      background: linear-gradient(180deg, #fff9f0, var(--bg));
      color: var(--ink);
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(31, 41, 51, 0.06);
    }}
    .grid {{
      display: grid;
      gap: 16px;
    }}
    .gallery {{
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    }}
    .pages {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 16px 0;
    }}
    .thumb img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .thumb strong {{
      display: block;
      margin-top: 10px;
    }}
    .card-view {{
      display: grid;
      gap: 18px;
    }}
    .card-view img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .side-label {{
      color: var(--muted);
      font-size: 0.95rem;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .meta {{
      color: var(--muted);
    }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def render_card_page(card: Card, prev_card: Card | None, next_card: Card | None) -> str:
    prev_link = (
        f'<a href="{relative_link(card_html_path(card), card_html_path(prev_card))}">Previous</a>'
        if prev_card
        else "<span>Previous</span>"
    )
    next_link = (
        f'<a href="{relative_link(card_html_path(card), card_html_path(next_card))}">Next</a>'
        if next_card
        else "<span>Next</span>"
    )
    gallery_link = relative_link(card_html_path(card), card.day_dir / "index.html")
    body = f"""
<div class="topbar">
  <div>
    <h1>{html.escape(card.callsign)}</h1>
    <div class="meta">{card.date:%Y-%m-%d}</div>
  </div>
  <div class="pages">
    <a href="{gallery_link}">Back to gallery</a>
    {prev_link}
    {next_link}
  </div>
</div>
<div class="grid card-view">
  <section class="card">
    <div class="side-label">Front</div>
    <img src="{relative_link(card_html_path(card), card.front)}" alt="{html.escape(card.callsign)} front">
  </section>
  <section class="card">
    <div class="side-label">Back</div>
    <img src="{relative_link(card_html_path(card), card.back)}" alt="{html.escape(card.callsign)} back">
  </section>
</div>
"""
    return html_page(f"{card.callsign} - {card.date:%Y-%m-%d}", body)


def render_gallery_page(day_dir: Path, cards: list[Card], page_number: int, page_count: int) -> str:
    start = page_number * 24
    page_cards = cards[start : start + 24]
    prev_link = (
        '<a href="index.html">Previous</a>'
        if page_number == 1
        else (f'<a href="index-{page_number}.html">Previous</a>' if page_number > 0 else "<span>Previous</span>")
    )
    next_link = (
        f'<a href="index-{page_number + 2}.html">Next</a>' if page_number + 1 < page_count else "<span>Next</span>"
    )
    cards_html = []
    for card in page_cards:
        card_html = f"{card.callsign}.html"
        cards_html.append(
            f"""
<a class="thumb card" href="{card_html}">
  <img src="{card.front.name}" alt="{html.escape(card.callsign)} front">
  <strong>{html.escape(card.callsign)}</strong>
  <span class="meta">{card.date:%Y-%m-%d}</span>
</a>
"""
        )
    body = f"""
<div class="topbar">
  <div>
    <h1>{cards[0].date:%Y-%m-%d}</h1>
    <div class="meta">{len(cards)} card(s)</div>
  </div>
  <div class="pages">
    <a href="../index.html">All dates</a>
    {prev_link}
    {next_link}
  </div>
</div>
<div class="pages">
  {f'<a href="index.html">Page 1</a>' if page_count > 1 else '<span>Page 1</span>'}
"""
    if page_count > 1:
        for idx in range(page_count):
            if idx == page_number:
                body += f"<span>Page {idx + 1}</span>"
            else:
                body += f'<a href="index-{idx + 1}.html">Page {idx + 1}</a>'
    body += "</div>"
    body += f'<div class="grid gallery">{"".join(cards_html)}</div>'
    return html_page(f"{day_dir.as_posix()} gallery", body)


def render_root_index(root: Path, cards: list[Card]) -> str:
    by_day: dict[dt.date, list[Card]] = {}
    for card in cards:
        by_day.setdefault(card.date, []).append(card)

    items = []
    for day in sorted(by_day, reverse=True):
        day_dir = root / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}"
        items.append(
            f'<li><a href="{os.path.relpath(day_dir / "index.html", start=root).replace(os.sep, "/")}">{day:%Y-%m-%d}</a> '
            f'({len(by_day[day])} card(s))</li>'
        )

    body = f"""
<div class="topbar">
  <div>
    <h1>QSL Index</h1>
    <div class="meta">{len(cards)} card(s) across {len(by_day)} day(s)</div>
  </div>
</div>
<section class="card">
  <h2>Dates</h2>
  <ul>
    {"".join(items) if items else "<li>No cards scanned yet.</li>"}
  </ul>
</section>
"""
    return html_page("QSL Index", body)


def write_pages(root: Path, cards: list[Card]) -> None:
    root.mkdir(parents=True, exist_ok=True)

    by_day: dict[dt.date, list[Card]] = {}
    for card in cards:
        by_day.setdefault(card.date, []).append(card)

    for day, day_cards in by_day.items():
        day_cards.sort(key=lambda item: item.callsign)
        day_dir = root / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}"
        day_dir.mkdir(parents=True, exist_ok=True)
        page_count = max(1, math.ceil(len(day_cards) / 24))
        for index, card in enumerate(day_cards):
            prev_card = day_cards[index - 1] if index > 0 else None
            next_card = day_cards[index + 1] if index + 1 < len(day_cards) else None
            card_html = card_html_path(card)
            card_html.write_text(render_card_page(card, prev_card, next_card), encoding="utf-8")

        for page_number in range(page_count):
            page_name = "index.html" if page_number == 0 else f"index-{page_number + 1}.html"
            (day_dir / page_name).write_text(render_gallery_page(day_dir, day_cards, page_number, page_count), encoding="utf-8")

    (root / "index.html").write_text(render_root_index(root, cards), encoding="utf-8")


def publish(config: configparser.ConfigParser, root: Path) -> None:
    command = config.get("publish", "command", fallback="").strip()
    if not command:
        return

    rendered = command.format(output_root=str(root), root=str(root))
    subprocess.run(rendered, shell=True, check=True)


def build_site(config: configparser.ConfigParser) -> None:
    root = output_root(config)
    cards = discover_cards(root)
    write_pages(root, cards)
    publish(config, root)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan and build QSL card galleries.")
    parser.add_argument("-c", "--config", help="Path to config.ini")

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan a new card")
    scan.add_argument("callsign", help="Card callsign")
    scan.add_argument("date", nargs="?", help="Card date in YYYY-MM-DD format")

    subparsers.add_parser("build", help="build HTML for all existing scans")
    subparsers.add_parser("poke", help="rebuild HTML after an upload or sync")

    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    config = load_config(config_path_from_args(args))

    if args.command == "scan":
        scan_date = parse_date(args.date)
        scan_card(config, args.callsign, scan_date)
        build_site(config)
        return 0

    if args.command in {"build", "poke"}:
        build_site(config)
        return 0

    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
