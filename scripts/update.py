#!/usr/bin/env python3
"""Refresh the small public Israel playlist and its matching XMLTV guide."""
from __future__ import annotations
import datetime as dt
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M3U_URL = "https://iptv-org.github.io/iptv/countries/il.m3u"
EPG_URL = "https://iptv-epg.org/files/epg-il.xml"
EPG_PUBLIC = "https://raw.githubusercontent.com/maorprl/mptv/main/epg.xml"
CHANNELS = {
    "Kan11.il": ("Kan 11", "Kan11.il"),
    "Keshet12.il": ("Keshet 12", "Keshet12.il"),
    "Channel13.il": ("Channel 13", "Channel13.il"),
}
# EPG input may use either older Hebrew IDs or already normalized IDs.
GUIDE_IDS = {
    "כאן11.il": "Kan11.il",
    "קשת.il": "Keshet12.il",
    "רשת.il": "Channel13.il",
    "Kan11.il": "Kan11.il",
    "Keshet12.il": "Keshet12.il",
    "Channel13.il": "Channel13.il",
}

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mptv-guide/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()

def playlist() -> None:
    source = fetch(M3U_URL).decode("utf-8-sig")
    rows = source.splitlines()
    blocks = {}
    i = 0
    while i < len(rows):
        line = rows[i].strip()
        if not line.startswith("#EXTINF:"):
            i += 1
            continue
        match = re.search(r'tvg-id="([^"]+)"', line)
        key = (match.group(1).split("@", 1)[0] if match else "")
        block = [line]
        i += 1
        while i < len(rows) and not rows[i].startswith("#EXTINF:"):
            if rows[i].strip():
                block.append(rows[i].strip())
            i += 1
        if key in CHANNELS:
            if not any(item.startswith(("http://", "https://")) for item in block[1:]):
                raise ValueError(f"No stream URL for {key}")
            name, channel_id = CHANNELS[key]
            metadata = re.sub(r'tvg-id="[^"]+"', f'tvg-id="{channel_id}"', block[0])
            metadata = re.sub(r'group-title="[^"]*"', 'group-title="Israel"', metadata)
            metadata = metadata.rsplit(",", 1)[0] + "," + name
            blocks[key] = [metadata, *block[1:]]
    missing = set(CHANNELS) - set(blocks)
    if missing:
        raise ValueError(f"Missing channels in upstream playlist: {sorted(missing)}")
    out = [f'#EXTM3U url-tvg="{EPG_PUBLIC}" x-tvg-url="{EPG_PUBLIC}"']
    for key in CHANNELS:
        out.extend(blocks[key])
    (ROOT / "playlist.m3u").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("Playlist: 3 channels")

def guide() -> None:
    data = fetch(EPG_URL)
    root = ET.fromstring(data)
    output = ET.Element("tv", {"generator-info-name": "mptv", "source-info-url": EPG_URL})
    for node in root.findall("channel"):
        new_id = GUIDE_IDS.get(node.get("id"))
        if new_id:
            node.set("id", new_id)
            output.append(node)
    counts = {cid: 0 for cid in CHANNELS}
    today = dt.datetime.now(dt.timezone.utc).date()
    earliest = (today - dt.timedelta(days=1)).strftime("%Y%m%d")
    for node in root.findall("programme"):
        cid = GUIDE_IDS.get(node.get("channel"))
        start = node.get("start", "")
        if cid and start[:8] >= earliest:
            node.set("channel", cid)
            output.append(node)
            counts[cid] += 1
    if len(output.findall("channel")) != 3 or any(n == 0 for n in counts.values()):
        raise ValueError(f"Missing current EPG channels/programmes: {counts}")
    ET.indent(output, space="  ")
    ET.ElementTree(output).write(ROOT / "epg.xml", encoding="utf-8", xml_declaration=True)
    print("EPG programme counts:", counts)

if __name__ == "__main__":
    # Fail safely: only commit if both source downloads and checks pass.
    guide()
    playlist()
