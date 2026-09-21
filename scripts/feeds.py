"""
Quantum and AI Briefing, free headline collector.

Runs in GitHub Actions with no API keys and no cost. Pulls recent headlines from
free news feeds (Google News searches and publisher RSS) and new papers from arXiv,
removes duplicates, and saves them to docs/data/feed.json for the web page.
It collects and links; it does not summarize or write Notes.
"""

import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.parse
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data" / "feed.json"
UA = "Mozilla/5.0 (compatible; quantum-briefing/1.0)"
KEEP_NEWS_DAYS = 10
KEEP_RESEARCH_DAYS = 21


def gnews(query):
    q = urllib.parse.urlencode({"q": query + " when:2d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return "https://news.google.com/rss/search?" + q


def arxiv(query, n=20):
    q = urllib.parse.urlencode({"search_query": query, "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": n})
    return "https://export.arxiv.org/api/query?" + q


# Topic, feed URL. Edit freely: add or remove lines to change what is collected.
NEWS_FEEDS = [
    ("Quantum computing", gnews('"quantum computing" OR "quantum computer"')),
    ("Quantum AI", gnews('"quantum AI" OR "quantum artificial intelligence"')),
    ("Quantum machine learning", gnews('"quantum machine learning"')),
    ("Quantum security", gnews('"post-quantum" OR "quantum-safe" OR "quantum cryptography"')),
    ("AI", gnews('"artificial intelligence" (enterprise OR leadership OR regulation OR workforce)')),
    ("Machine learning", gnews('"machine learning" (research OR breakthrough OR model)')),
    ("Quantum computing", "https://thequantuminsider.com/feed/"),
    ("Quantum computing", "https://www.sciencedaily.com/rss/computers_math/quantum_computers.xml"),
    ("AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
]

RESEARCH_FEEDS = [
    ("Quantum machine learning", arxiv('cat:quant-ph AND (abs:"machine learning" OR abs:"neural network")')),
    ("Quantum AI", arxiv('cat:quant-ph AND (abs:"artificial intelligence" OR abs:"language model")', 15)),
    ("Quantum computing", arxiv('cat:quant-ph AND (abs:"quantum advantage" OR abs:"error correction" OR abs:"quantum algorithm")')),
    ("Quantum security", arxiv('cat:cs.CR AND (abs:"post-quantum" OR abs:"quantum-safe")', 10)),
    ("AI", arxiv("cat:cs.AI", 15)),
    ("Machine learning", arxiv("cat:cs.LG", 15)),
]


def clean(text, limit=280):
    t = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return t


def when(entry):
    for k in ("published_parsed", "updated_parsed"):
        v = entry.get(k)
        if v:
            return dt.datetime.fromtimestamp(time.mktime(v), dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def key(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())[:80]


def collect(feeds, kind):
    out = []
    for topic, url in feeds:
        try:
            f = feedparser.parse(url, agent=UA)
        except Exception as e:
            print("Feed failed:", url, e)
            continue
        feed_name = clean(f.feed.get("title", ""), 60)
        for e in f.entries[:25]:
            title = clean(e.get("title", ""), 220)
            if not title:
                continue
            source = ""
            if kind == "news":
                src = e.get("source")
                source = (src.get("title") if isinstance(src, dict) else "") or feed_name
                if " - " in title and "news.google.com" in url:
                    title, _, tail = title.rpartition(" - ")
                    source = source or tail
                snippet = "" if "news.google.com" in url else clean(e.get("summary", ""))
            else:
                names = [a.get("name", "") for a in e.get("authors", [])]
                source = "arXiv preprint, " + (", ".join(names[:3]) + (" et al." if len(names) > 3 else ""))
                snippet = clean(e.get("summary", ""), 320)
            link = e.get("link", "")
            out.append({
                "id": hashlib.md5((link or title).encode()).hexdigest()[:12],
                "title": title, "link": link, "source": source.strip(", "),
                "published": when(e).isoformat(timespec="minutes"),
                "topic": topic, "snippet": snippet,
            })
        if kind == "research":
            time.sleep(3)  # arXiv asks for a pause between requests
    return out


def merge(old, new, days, cap):
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    seen, merged = set(), []
    for x in sorted(new + old, key=lambda i: i.get("published", ""), reverse=True):
        k = key(x.get("title", ""))
        if not k or k in seen or x.get("published", "") < cutoff:
            continue
        seen.add(k)
        merged.append(x)
    return merged[:cap]


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    news = merge(old.get("news", []), collect(NEWS_FEEDS, "news"), KEEP_NEWS_DAYS, 300)
    research = merge(old.get("research", []), collect(RESEARCH_FEEDS, "research"), KEEP_RESEARCH_DAYS, 250)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "news": news, "research": research,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(news)} news items and {len(research)} research papers.")


if __name__ == "__main__":
    main()
