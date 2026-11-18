#!/usr/bin/env python3
"""Fetch RSS headlines, publisher-provided images and original article links."""
import os, json, re, hashlib, html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher
from pathlib import Path
import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
BD = ZoneInfo("Asia/Dhaka")
NOW = datetime.now(timezone.utc)
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "36"))
MAX_STORIES = int(os.getenv("MAX_STORIES", "120"))

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()

def norm(s):
    return re.sub(r"[\W_]+", "", (s or "").lower(), flags=re.UNICODE)

def category(text):
    t = (text or "").lower()
    rules = [
        ("রাজনীতি", ["রাজনীতি","নির্বাচন","সংসদ","দল","মন্ত্রী","প্রধানমন্ত্রী","সরকার","politic","election","parliament","minister","government"]),
        ("অর্থনীতি", ["অর্থনীতি","ব্যবসা","বাজার","দাম","ব্যাংক","রপ্তানি","আমদানি","শেয়ার","economy","business","market","bank","export","inflation"]),
        ("খেলা", ["ক্রিকেট","ফুটবল","খেলা","ম্যাচ","বিশ্বকাপ","cricket","football","sports","match"]),
        ("শিক্ষা", ["শিক্ষা","বিশ্ববিদ্যালয়","পরীক্ষা","ভর্তি","স্কুল","education","university","exam","school"]),
        ("স্বাস্থ্য", ["স্বাস্থ্য","হাসপাতাল","ডেঙ্গু","চিকিৎসা","health","hospital","dengue","medical"]),
        ("আন্তর্জাতিক", ["বিশ্ব","আন্তর্জাতিক","যুক্তরাষ্ট্র","ভারত","পাকিস্তান","ইরান","ইসরায়েল","world","international","united states","india","pakistan","iran","israel"]),
        ("প্রযুক্তি", ["প্রযুক্তি","প্রযুক্তি","মোবাইল","কৃত্রিম বুদ্ধিমত্তা","technology","tech","ai","software"]),
        ("অপরাধ", ["হত্যা","মামলা","গ্রেপ্তার","দুর্ঘটনা","আদালত","পুলিশ","crime","murder","arrest","court","police","accident"]),
    ]
    for label, words in rules:
        if any(w in t for w in words):
            return label
    return "জাতীয়"

def parse_date(entry):
    for key in ("published_parsed","updated_parsed","created_parsed"):
        val = entry.get(key)
        if val:
            try:
                import time
                return datetime.fromtimestamp(time.mktime(val), timezone.utc)
            except Exception:
                pass
    return NOW

def image_from_entry(entry):
    """Only use publisher-provided RSS image URLs; never scrape full articles."""
    candidates = []
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key, []):
            candidates.append(media.get("url", ""))
    for link in entry.get("links", []):
        if (link.get("type") or "").startswith("image/"):
            candidates.append(link.get("href", ""))
    for enclosure in entry.get("enclosures", []):
        if (enclosure.get("type") or "").startswith("image/"):
            candidates.append(enclosure.get("href", ""))
    raw = entry.get("summary") or entry.get("description") or ""
    match = re.search(r'<img[^>]+src=[\"\']([^\"\']+)', raw, re.I)
    if match:
        candidates.append(html.unescape(match.group(1)))
    for candidate in candidates:
        if candidate.startswith("https://") or candidate.startswith("http://"):
            return candidate
    return ""

def fetch():
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    records, status = [], []
    for src in sources:
        try:
            r = requests.get(src["url"], timeout=18, headers={"User-Agent":"BangladeshNewsHub/1.0 (RSS reader; contact: admin@example.invalid)"})
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            added = 0
            for e in parsed.entries[:50]:
                title = clean(e.get("title"))
                link = e.get("link","").strip()
                if not title or not link.startswith("http"):
                    continue
                dt = parse_date(e)
                age = (NOW - dt).total_seconds()/3600
                if age > MAX_AGE_HOURS or age < -2:
                    continue
                summary = clean(e.get("summary") or e.get("description") or "")
                records.append({"title":title,"url":link,"source":src["name"],"published":dt.isoformat(),"image":image_from_entry(e)})
                added += 1
            status.append({"source":src["name"],"ok":True,"items":added})
        except Exception as ex:
            status.append({"source":src["name"],"ok":False,"error":str(ex)[:180]})
    # Exact URL/title dedupe, then fuzzy cluster on headline.
    unique, seen = [], set()
    for x in sorted(records, key=lambda z:z["published"], reverse=True):
        key = x["url"].split("?")[0].rstrip("/") or x["url"]
        if key in seen: continue
        seen.add(key)
        x["category"] = category(x["title"])
        x["sources"] = [{"name":x["source"],"url":x["url"]}]
        match = None
        nt = norm(x["title"])
        for existing in unique:
            if existing["category"] != x["category"]: continue
            ratio = SequenceMatcher(None, nt, norm(existing["title"])).ratio()
            if ratio >= 0.84:
                match = existing; break
        if match:
            if x["source"] not in [s["name"] for s in match["sources"]]:
                match["sources"].append({"name":x["source"],"url":x["url"]})
            if not match.get("image") and x.get("image"):
                match["image"] = x["image"]
            continue
        unique.append(x)
    unique = unique[:MAX_STORIES]
    for i,x in enumerate(unique,1):
        x["id"] = hashlib.sha1((x["url"]+x["title"]).encode()).hexdigest()[:12]
        x["rank"] = i
    return unique, status

def main():
    items, statuses = fetch()
    for x in items:
        x.pop("language", None)
        x.pop("source", None)
    now_local = datetime.now(BD)
    output = {
        "edition_date": now_local.strftime("%Y-%m-%d"),
        "updated_at": now_local.isoformat(),
        "timezone": "Asia/Dhaka",
        "count": len(items),
        "summary_mode": "Original headlines and publisher links; no AI summaries",
        "stories": items,
        "feed_status": statuses,
    }
    (ROOT / "news.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = ROOT / "data" / "archive" / f'{now_local.strftime("%Y-%m-%d")}.json'
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Published {len(items)} stories; feeds ok: {sum(1 for s in statuses if s['ok'])}/{len(statuses)}")

if __name__ == "__main__":
    main()
