"""
Quantum and AI Briefing, daily job.

Runs every morning in GitHub Actions:
  1. News: the most important news reports and announcements from the past 48 hours.
  2. Research roundup (every other Friday, or when forced): papers from the past 14 days.
For each run, Claude searches the web, summarizes each finding in its own words,
labels the source type, picks the most attractive items, and writes a ready-to-post
Substack Note for each pick. The script appends the citation and link to every Note,
saves everything to docs/data/findings.json, and the web page in docs/ displays it.

Optional: if NOTION_TOKEN and NOTION_DATABASE_ID are set, new findings are also
added to the Notion database so the Claude writing desk stays in sync.
"""

import datetime as dt
import json
import os
import re
import sys
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "findings.json"
MODEL = os.environ.get("MODEL", "claude-sonnet-5")
TZ = ZoneInfo("America/New_York")
ROUNDUP_ANCHOR = dt.date(2026, 10, 2)  # first research roundup, then every 14 days
KEEP_DAYS = 180

AREAS = [
    "Quantum computing", "Quantum machine learning", "Quantum and AI", "Security",
    "Healthcare", "Sustainability", "Space", "Telecom", "Optimization",
    "Smart cities", "Industry and policy",
]
NEWS_TYPES = ["News", "Press release"]
RESEARCH_TYPES = ["Peer-reviewed", "Preprint"]

PUBLICATION = """PUBLICATION AND READER
You work for Dr. Naama Yefet's publication Future Intelligence on Substack: AI leadership,
organizational change, AI literacy and trust, and quantum and AI readiness. Readers are
executives, technology leaders, transformation leaders, and people responsible for
organizational capability. Everything must stay readable for someone outside those roles.
Quantum topics are framed around business literacy, readiness, cybersecurity, workforce,
problem selection, and reading headlines well. No countdowns, no arms-race framing,
no predictions with dates, no urgency manufactured from uncertainty."""

VOICE = """VOICE FOR NOTES
Warm, measured, and curious. Plain sentences, concrete nouns, active voice.
No contractions. No em dashes; use commas or full stops. No hashtags, no emoji,
no engagement bait, no calls to action, never ask anyone to subscribe.
Never open with a question or with words like Breaking or Big news.
End on what it means for leaders: an observation, not a lesson or a slogan.
Attribute claims such as first, breakthrough, or advantage to whoever makes them.
Do not write the source name or any link at the end of a note. The citation and link
are appended automatically."""

RULES = """HARD RULES
- Summaries and notes are written entirely in your own words. Never copy sentences or
  phrases from a source. Quote nothing longer than a few words, and only when essential.
- Use only facts you actually found. Never invent or estimate numbers, dates, names,
  or results. Describe a result exactly as strongly as the source does, never stronger.
- Link: the primary source whenever one exists (the paper, the official announcement,
  the original report), not an aggregator or a roundup page.
- Date: the publication or announcement date as YYYY-MM-DD, only if you confirmed it.
  If only the month is known, use the first day of that month and say so in the summary.
- Source type, applied strictly:
    Peer-reviewed: published in a peer-reviewed journal.
    Preprint: arXiv or similar, not yet peer-reviewed.
    Press release: a company or institution describing its own work, including news
      stories that only relay that release.
    News: independent reporting.
  When unsure between News and Press release, choose Press release.
- Area: exactly one of: """ + ", ".join(AREAS) + """.
- Say so when a result ran on classical or emulated hardware, or is simulation or early
  lab work rather than a deployed product.
- Skip stock price moves, routine funding rounds, conference promotions, executive
  appointments, listicles, and explainers. Never pad: fewer findings is fine."""


def today():
    return dt.datetime.now(TZ).date()


def is_roundup_day(d):
    if os.environ.get("FORCE_RESEARCH", "").lower() in ("1", "true", "yes"):
        return True
    return d >= ROUNDUP_ANCHOR and d.weekday() == 4 and (d - ROUNDUP_ANCHOR).days % 14 == 0


def next_roundup(d):
    n = ROUNDUP_ANCHOR
    while n < d:
        n += dt.timedelta(days=14)
    return n


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"items": []}


def recent_lines(items, limit=60):
    rows = sorted(items, key=lambda x: x.get("date", ""), reverse=True)[:limit]
    return "\n".join("- " + r.get("headline", "") + " | " + r.get("link", "") for r in rows) or "None."


def build_prompt(mode, d, items):
    if mode == "news":
        task = f"""TASK: DAILY NEWS
Today is {d.isoformat()}. Search the web for the most important NEWS REPORTS and
ANNOUNCEMENTS published since {(d - dt.timedelta(days=2)).isoformat()} about quantum
computing, quantum machine learning, and quantum and AI, including their effects on
cybersecurity, healthcare, telecom, sustainability, space, optimization, smart cities,
and industry and policy. Company and government announcements, policy and standards,
security developments, and significant industry moves.
Check primary sources: company newsrooms (IBM, Google Quantum AI, Quantinuum, IonQ,
NVIDIA, Microsoft, Pasqal, D-Wave, others), NIST, CISA, NSA, DOE, national programs,
and independent outlets such as The Quantum Insider, IEEE Spectrum, Reuters, and Nature news.
Record 5 to 8 findings. Source type must be News or Press release."""
        notes = """TOP PICKS AND NOTES
Mark the 2 or 3 findings most worth posting for this readership as top_pick true, and
write a note for each: 40 to 90 words, one or two short paragraphs, opening with what
happened in plain words and who did it, saying what kind of evidence it is when that
matters for trust, and closing on what it means for leaders. No title line."""
    else:
        task = f"""TASK: RESEARCH ROUNDUP
Today is {d.isoformat()}. Search for RESEARCH papers published or posted since
{(d - dt.timedelta(days=14)).isoformat()} on quantum computing, quantum machine learning,
and quantum and AI, with applications in cybersecurity, healthcare, telecom,
sustainability, space, optimization, and smart cities. Look at arXiv (quant-ph, cs.LG,
cs.CR), Nature, Science, Science Advances, PRX Quantum, the Physical Review journals,
npj Quantum Information, Optica Quantum, and IEEE journals.
Record the 4 to 6 papers that matter most for leaders, covering different areas where
the material genuinely exists. Source type must be Peer-reviewed or Preprint."""
        notes = """TOP PICKS AND NOTES
Mark the 2 to 4 papers most worth posting for this readership as top_pick true, and
write a note for each: a title line stating the idea plainly in sentence case, a blank
line, then two or three paragraphs of 100 to 170 words in total. Explain what the
researchers did and actually showed, fair to the strength of the evidence, say whether
it is peer-reviewed or a preprint, name the authors or institution and the journal or
arXiv inline, and close on what it means for leaders."""

    return f"""{PUBLICATION}

{task}

{RULES}

{notes}

{VOICE}

ALREADY RECORDED, do not repeat these stories or papers unless there is genuinely new information:
{recent_lines(items)}

OUTPUT
After searching, reply with JSON only, wrapped in <findings></findings> tags, in exactly this shape:
<findings>{{"items":[{{"headline":"plain words, under 20 words, not the source's headline","date":"YYYY-MM-DD","area":"one of the areas","source_type":"one of the source types","source":"publication name; for research, authors and journal or arXiv","link":"primary source URL","summary":"2 to 3 sentences in your own words","why":"1 to 2 sentences on what it means for leaders","top_pick":false,"note":"the note for top picks, paragraphs separated by a blank line; empty string otherwise"}}]}}</findings>"""


def call_claude(prompt):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}]
    text = ""
    for _ in range(8):
        resp = client.messages.create(model=MODEL, max_tokens=16000, tools=tools, messages=messages)
        text += "".join(getattr(b, "text", "") for b in resp.content if b.type == "text")
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    m = re.search(r"<findings>(.*?)</findings>", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip())
    return json.loads(raw).get("items", [])


def with_citation(note, source, link):
    t = (note or "").rstrip()
    for _ in range(3):
        t = re.sub(r"\n*\s*https?://\S+\s*$", "", t).rstrip()
        t = re.sub(r"\n+\s*Source:[^\n]*$", "", t, flags=re.I).rstrip()
    if not t:
        return ""
    return t + "\n\nSource: " + (source or "Read more") + ("\n" + link if link else "")


def normalize(x, d, mode):
    allowed = NEWS_TYPES if mode == "news" else RESEARCH_TYPES
    st = x.get("source_type") if x.get("source_type") in allowed else allowed[-1]
    area = x.get("area") if x.get("area") in AREAS else "Quantum computing"
    date = str(x.get("date") or d.isoformat())[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        date = d.isoformat()
    top = bool(x.get("top_pick"))
    note = with_citation(x.get("note", ""), x.get("source", ""), x.get("link", "")) if top else ""
    return {
        "id": uuid.uuid4().hex[:12], "found": d.isoformat(), "date": date,
        "kind": mode, "area": area, "source_type": st,
        "headline": (x.get("headline") or "").strip(), "source": (x.get("source") or "").strip(),
        "link": (x.get("link") or "").strip(), "summary": (x.get("summary") or "").strip(),
        "why": (x.get("why") or "").strip(), "top_pick": top and bool(note), "note": note,
    }


def key(x):
    link = (x.get("link") or "").lower().rstrip("/")
    generic = link.endswith("/news") or link.count("/") <= 3
    return link if link and not generic else (x.get("headline") or "").lower()


def notion_push(new_items):
    token, db = os.environ.get("NOTION_TOKEN"), os.environ.get("NOTION_DATABASE_ID")
    if not token or not db or not new_items:
        return
    import requests

    def rt(s):
        s = s or ""
        return [{"type": "text", "text": {"content": s[i:i + 1900]}} for i in range(0, len(s), 1900)] or []

    for x in new_items:
        props = {
            "Headline": {"title": rt(x["headline"])},
            "Date": {"date": {"start": x["date"]}},
            "Area": {"select": {"name": x["area"]}},
            "Source type": {"select": {"name": x["source_type"]}},
            "Source": {"rich_text": rt(x["source"])},
            "Link": {"url": x["link"] or None},
            "Summary": {"rich_text": rt(x["summary"])},
            "Why it matters": {"rich_text": rt(x["why"])},
            "Status": {"select": {"name": "New"}},
            "Found by": {"select": {"name": "Claude"}},
            "Note": {"rich_text": rt(x["note"])},
            "Top pick": {"checkbox": bool(x["top_pick"])},
        }
        r = requests.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            json={"parent": {"database_id": db}, "properties": props}, timeout=30)
        if r.status_code >= 300:
            print("Notion write failed:", r.status_code, r.text[:300], file=sys.stderr)


def main():
    d = today()
    data = load()
    items = data.get("items", [])
    modes = ["news"] + (["research"] if is_roundup_day(d) else [])
    added = []
    for mode in modes:
        try:
            found = call_claude(build_prompt(mode, d, items + added))
        except Exception as e:  # keep the site up even if one run fails
            print(f"{mode} run failed: {e}", file=sys.stderr)
            continue
        seen = {key(x) for x in items + added}
        for raw in found:
            x = normalize(raw, d, mode)
            if not x["headline"] or not x["summary"] or key(x) in seen:
                continue
            seen.add(key(x))
            added.append(x)
        print(f"{mode}: {len(found)} returned, {sum(1 for a in added if a['kind'] == mode)} new")

    cutoff = (d - dt.timedelta(days=KEEP_DAYS)).isoformat()
    items = [x for x in added + items if x.get("found", x.get("date", "")) >= cutoff]
    items.sort(key=lambda x: (x.get("date", ""), x.get("found", "")), reverse=True)

    data.update({
        "updated": dt.datetime.now(TZ).isoformat(timespec="minutes"),
        "next_roundup": next_roundup(d + dt.timedelta(days=1) if "research" in modes else d).isoformat(),
        "items": items,
    })
    if "research" in modes:
        data["last_roundup"] = d.isoformat()
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    notion_push(added)
    print(f"Saved {len(items)} findings, {len(added)} new.")


if __name__ == "__main__":
    main()
