#!/usr/bin/env python3
"""Create a separate experimental list of publicly indexed Israeli streams.

Discovery does not establish permission to redistribute or that a stream plays.
Keep production playlist.m3u untouched.
"""
from __future__ import annotations
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://iptv-org.github.io/iptv/countries/il.m3u"
EPG = "https://raw.githubusercontent.com/maorprl/mptv/main/epg.xml"
MAIN_IDS = {"Kan11.il", "Keshet12.il", "Channel13.il"}

def main() -> None:
    req = urllib.request.Request(UPSTREAM, headers={"User-Agent": "mptv/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read().decode("utf-8-sig")
    blocks = []
    current = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            if current:
                blocks.append(current)
            current = [line]
        elif current and line:
            current.append(line)
    if current:
        blocks.append(current)
    selected = []
    seen = set()
    for block in blocks:
        match = re.search(r'tvg-id="([^"]+)"', block[0])
        channel_id = match.group(1).split("@", 1)[0] if match else ""
        url = next((x for x in block[1:] if x.startswith(("http://", "https://"))), None)
        if not url or channel_id in MAIN_IDS or url in seen:
            continue
        seen.add(url)
        header = block[0]
        if match:
            header = re.sub(r'tvg-id="[^"]+"', f'tvg-id="{channel_id}"', header)
        selected.append([header, *block[1:]])
    if len(selected) < 4:
        raise RuntimeError(f"Unexpectedly few extra channels: {len(selected)}")
    output = [f'#EXTM3U url-tvg="{EPG}" x-tvg-url="{EPG}"']
    for block in selected:
        output.extend(block)
    (ROOT / "israel-experimental.m3u").write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Experimental Israel channels: {len(selected)}")

if __name__ == "__main__":
    main()
