#!/usr/bin/env python3
"""Generate a self-hosted Podcast RSS for RTHK 古今風雲人物 from catch-up API.

Audio remains on RTHK CDN; this script only builds metadata (no download/transcode).
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# --- URL / programme constants (change here if RTHK renames paths) ---
CHANNEL = "radio1"
PROGRAMME = "People"
CATCHUP_URL = (
    "https://www.rthk.hk/radio/catchUp?c={channel}&p={programme}&page={page}"
)
AUDIO_TMPL = (
    "https://archive.rthk.hk/mp3/radio/archive/{channel}/{programme}/m4a/{yyyymmdd}.m4a"
)
EPISODE_LINK_TMPL = (
    "https://www.rthk.hk/radio/{channel}/programme/{programme}/episode/{episode_id}"
)
PROGRAMME_LINK = f"https://www.rthk.hk/radio/{CHANNEL}/programme/{PROGRAMME}"
COVER_URL = (
    "https://podcast.rthk.hk/podcast/upload_photo/item_photo/1400x1400_287.jpg"
)
USER_AGENT = "Mozilla/5.0 (compatible; rthk-people-rss/1.0)"
HTTP_TIMEOUT = 30

HKT = timezone(timedelta(hours=8))

# RSS channel metadata
CHANNEL_TITLE = "香港電台：古今風雲人物（重溫）"
CHANNEL_DESCRIPTION = (
    "介紹古今中外歷史人物。非官方 RSS：由節目重溫頁自動生成，"
    "音頻直鏈港台 CDN，僅供個人訂閱使用。"
)
ITUNES_AUTHOR = "RTHK / 香港電台文教組"
ITUNES_OWNER = "self-hosted"

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"


def http_get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read()


def http_head_length(url: str) -> int | None:
    """Return Content-Length, 0 on soft failure, None if hard 404 (skip item)."""
    req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                print(
                    f"warning: HEAD {resp.status} for {url}; using length=0",
                    file=sys.stderr,
                )
                return 0
            length = resp.headers.get("Content-Length")
            if length is None:
                return 0
            return int(length)
    except HTTPError as e:
        if e.code == 404:
            return None
        print(f"warning: HEAD HTTPError {e.code} for {url}; using length=0", file=sys.stderr)
        return 0
    except (URLError, TimeoutError, ValueError, OSError) as e:
        print(f"warning: HEAD failed for {url}: {e}; using length=0", file=sys.stderr)
        return 0


def date_to_yyyymmdd(date_str: str) -> str:
    """Convert API date DD/MM/YYYY to YYYYMMDD."""
    day, month, year = date_str.strip().split("/")
    return f"{year}{month.zfill(2)}{day.zfill(2)}"


def parse_pubdate(date_str: str) -> datetime:
    """Broadcast time: Saturday 20:00 HKT on the episode date."""
    day, month, year = date_str.strip().split("/")
    return datetime(int(year), int(month), int(day), 20, 0, 0, tzinfo=HKT)


def audio_url(yyyymmdd: str) -> str:
    return AUDIO_TMPL.format(
        channel=CHANNEL, programme=PROGRAMME, yyyymmdd=yyyymmdd
    )


def episode_link(episode_id: str) -> str:
    return EPISODE_LINK_TMPL.format(
        channel=CHANNEL, programme=PROGRAMME, episode_id=episode_id
    )


def fetch_episodes(max_items: int = 0) -> list[dict[str, Any]]:
    """Paginate catchUp API until no more content. Newest first."""
    episodes: list[dict[str, Any]] = []
    page = 1
    max_pages = 100  # safety cap

    while page <= max_pages:
        url = CATCHUP_URL.format(channel=CHANNEL, programme=PROGRAMME, page=page)
        try:
            raw = http_get(url)
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as e:
            raise SystemExit(f"error: failed to fetch catchUp page={page}: {e}") from e

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"error: invalid JSON on page={page}: {e}") from e

        if str(data.get("status")) != "1":
            raise SystemExit(
                f"error: catchUp status={data.get('status')!r} on page={page}"
            )

        content = data.get("content") or []
        if not content:
            break

        for item in content:
            episodes.append(item)
            if max_items > 0 and len(episodes) >= max_items:
                return episodes

        next_page = data.get("nextPage")
        if next_page is None:
            break
        try:
            next_page_int = int(next_page)
        except (TypeError, ValueError):
            break
        if next_page_int <= page:
            break
        page = next_page_int

    return episodes


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, tag, attrib=attrs)
    if text is not None:
        el.text = text
    return el


def build_rss(
    episodes: list[dict[str, Any]],
    feed_self_url: str,
    *,
    skip_head: bool = False,
) -> str:
    # register_namespace emits a single xmlns:* on serialization; do not also set xmlns attrs
    ET.register_namespace("itunes", ITUNES_NS)
    ET.register_namespace("atom", ATOM_NS)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    _sub(channel, "title", CHANNEL_TITLE)
    _sub(channel, "link", PROGRAMME_LINK)
    _sub(channel, "description", CHANNEL_DESCRIPTION)
    _sub(channel, "language", "zh-hk")
    _sub(channel, f"{{{ITUNES_NS}}}author", ITUNES_AUTHOR)
    _sub(channel, f"{{{ITUNES_NS}}}summary", CHANNEL_DESCRIPTION)
    owner = ET.SubElement(channel, f"{{{ITUNES_NS}}}owner")
    _sub(owner, f"{{{ITUNES_NS}}}name", ITUNES_OWNER)
    ET.SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": COVER_URL})
    ET.SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": "History"})
    _sub(channel, f"{{{ITUNES_NS}}}explicit", "false")
    if feed_self_url:
        ET.SubElement(
            channel,
            f"{{{ATOM_NS}}}link",
            {
                "href": feed_self_url,
                "rel": "self",
                "type": "application/rss+xml",
            },
        )
    # Standard image for non-iTunes clients
    image = ET.SubElement(channel, "image")
    _sub(image, "url", COVER_URL)
    _sub(image, "title", CHANNEL_TITLE)
    _sub(image, "link", PROGRAMME_LINK)

    skipped = 0
    for raw in episodes:
        ep_id = str(raw.get("id", "")).strip()
        title = str(raw.get("title", "")).strip()
        date_str = str(raw.get("date", "")).strip()
        if not ep_id or not title or not date_str:
            print(f"warning: skipping incomplete item: {raw!r}", file=sys.stderr)
            skipped += 1
            continue

        try:
            yyyymmdd = date_to_yyyymmdd(date_str)
            pub = parse_pubdate(date_str)
        except (ValueError, AttributeError) as e:
            print(f"warning: bad date {date_str!r} for id={ep_id}: {e}", file=sys.stderr)
            skipped += 1
            continue

        enclosure = audio_url(yyyymmdd)
        if skip_head:
            length = 0
        else:
            length = http_head_length(enclosure)
            if length is None:
                print(
                    f"warning: audio 404, skip id={ep_id} title={title!r} url={enclosure}",
                    file=sys.stderr,
                )
                skipped += 1
                continue

        item = ET.SubElement(channel, "item")
        _sub(item, "title", title)
        _sub(item, "link", episode_link(ep_id))
        guid = _sub(item, "guid", f"rthk-people-{ep_id}")
        guid.set("isPermaLink", "false")
        _sub(item, "pubDate", format_datetime(pub))
        _sub(item, "description", title)
        ET.SubElement(
            item,
            "enclosure",
            {
                "url": enclosure,
                "type": "audio/mp4",
                "length": str(length),
            },
        )

    if skipped:
        print(f"info: skipped {skipped} item(s)", file=sys.stderr)

    # Pretty-print-ish: ElementTree 3.9+ has indent
    try:
        ET.indent(rss, space="  ")
    except AttributeError:
        pass

    xml_bytes = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    # Ensure declaration uses UTF-8 (tostring already does)
    text = xml_bytes.decode("utf-8")
    # Fix category empty body if any
    return text + ("\n" if not text.endswith("\n") else "")


def write_feed_atomic(path: str, content: str) -> None:
    """Write feed; only called after successful generation with items."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    # replace works on Windows for existing dest in Py3.3+
    import os

    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Podcast RSS for RTHK 古今風雲人物 (catch-up)."
    )
    parser.add_argument(
        "--out",
        default="feed.xml",
        help="Output path for feed.xml (default: feed.xml)",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=0,
        help="Keep only the newest N items; 0 = no limit (default: 0)",
    )
    parser.add_argument(
        "--self-url",
        default="",
        help="Public feed URL for atom:link rel=self (optional)",
    )
    parser.add_argument(
        "--skip-head",
        action="store_true",
        help="Skip HEAD requests; enclosure length will be 0",
    )
    args = parser.parse_args(argv)

    print("Fetching episodes from RTHK catchUp API...", file=sys.stderr)
    episodes = fetch_episodes(max_items=args.max_items)
    if not episodes:
        print("error: no episodes returned; not writing feed", file=sys.stderr)
        return 1

    print(f"Fetched {len(episodes)} episode(s). Building RSS...", file=sys.stderr)
    xml = build_rss(episodes, args.self_url, skip_head=args.skip_head)

    # Ensure at least one <item> remains after HEAD filtering
    if "<item>" not in xml:
        print("error: no items after filtering; not overwriting feed", file=sys.stderr)
        return 1

    write_feed_atomic(args.out, xml)
    print(f"Wrote {args.out}", file=sys.stderr)

    # Print latest 3 for manual verification
    print("\nLatest episodes:", file=sys.stderr)
    for raw in episodes[:3]:
        ep_id = str(raw.get("id", ""))
        title = str(raw.get("title", ""))
        date_str = str(raw.get("date", ""))
        try:
            ymd = date_to_yyyymmdd(date_str)
            aurl = audio_url(ymd)
        except ValueError:
            aurl = "?"
        print(f"  - {ep_id} | {date_str} | {title}", file=sys.stderr)
        print(f"    {aurl}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
