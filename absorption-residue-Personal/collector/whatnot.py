#!/usr/bin/env python3
"""Read-only source probe for Whatnot's employer-controlled careers site.

Whatnot's old Ashby public board endpoint returns HTTP 404. The canonical
careers catalog is https://www.whatnot.com/careers/discover. Do not treat
scraped role links as verified applicant eligibility.
"""
import argparse
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from pathlib import Path

URL = "https://www.whatnot.com/careers/discover"
ROLE = re.compile(r"^/careers/roles/([0-9a-f-]{36})/?$", re.I)
TARGET = re.compile(r"software|backend|fullstack|frontend|developer|tooling|platform|machine learning|applied ai", re.I)

class RoleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.active = None
        self.cards = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.active is not None and tag not in {"br","img","input","meta","hr","source","link"}:
            self.depth += 1
        elif tag == "a" and ROLE.match(attrs.get("href", "")):
            self.active = {"href": attrs["href"], "parts": []}
            self.depth = 1
    def handle_startendtag(self, tag, attrs):
        if tag == "a":
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)
    def handle_data(self, data):
        if self.active is not None and data.strip():
            self.active["parts"].append(data.strip())
    def handle_endtag(self, tag):
        if self.active is not None and tag not in {"br","img","input","meta","hr","source","link"}:
            self.depth -= 1
            if self.depth == 0:
                self.cards.append(self.active)
                self.active = None

def parse(html):
    parser = RoleParser()
    parser.feed(html)
    unique = {}
    for card in parser.cards:
        role_id = ROLE.match(card["href"]).group(1).lower()
        pieces = [x.strip() for x in card["parts"] if x.strip() and x.strip() != "View Job"]
        title = pieces[0] if pieces else ""
        if title:
            unique[role_id] = {"id":role_id, "title":title,
                               "context":" ".join(pieces[1:])[:250],
                               "official_url":urljoin(URL,card["href"])}
    # Location labels appear beside each linked title, not inside the title link.
    # Bound extraction by the next *different* role ID to avoid cross-card leakage.
    markers = [(m.start(), m.group(1).lower()) for m in
               re.finditer(r'href="/careers/roles/([0-9a-f-]{36})"', html, re.I)]
    cities = re.compile(r'\b(?:Los Angeles,\s*CA|San Francisco,\s*CA|Seattle,\s*WA|New York,\s*NY|Phoenix,\s*AZ|London,\s*UK|Dublin,\s*Ireland|Kraków,\s*Poland|Berlin,\s*Germany)\b', re.I)
    for i, (start, role_id) in enumerate(markers):
        if role_id not in unique or unique[role_id].get("locations"):
            continue
        stop = next((pos for pos, other in markers[i+1:] if other != role_id), min(len(html),start+4000))
        chunk = html[start:min(stop,start+4000)]
        locs = list(dict.fromkeys(m.group(0) for m in cities.finditer(chunk)))
        if locs:
            unique[role_id]["locations"] = locs
    return list(unique.values())

def collect(html_output=None):
    req = Request(URL, headers={"User-Agent":"job-cockpit-public-careers/0.1 (read-only)","Accept":"text/html"})
    with urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("Employer careers returned HTTP " + str(response.status))
        body=response.read(5_000_000).decode("utf-8",errors="replace")
    if html_output:
        Path(html_output).write_text(body, encoding="utf-8")
    rows=parse(body)
    matches=[row for row in rows if TARGET.search(row["title"])]
    return {"source":URL, "total_role_links":len(rows),"engineering_candidates":len(matches),
            "la_engineering_candidates":sum("Los Angeles, CA" in x.get("locations",[]) for x in matches),
            "new_grad_matches":[x for x in matches if "new grad" in x["title"].lower()],
            "sample_engineering":matches[:12],
            "engineering_roles":matches,
            "verification_status":"discovered_unverified"}

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--min-roles",type=int,default=25)
    parser.add_argument("--output",default=None)
    parser.add_argument("--html-output",default=None)
    args=parser.parse_args()
    result=collect(args.html_output)
    if args.output:
        destination=Path(args.output)
        destination.parent.mkdir(parents=True,exist_ok=True)
        snapshot={"source":URL,"verification_status":"discovered_unverified",
                  "engineering_roles":result["engineering_roles"]}
        destination.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="engineering_roles"},indent=2))
    if result["total_role_links"] < args.min_roles:
        raise SystemExit("Whatnot HTML role parsing below minimum; keep source unhealthy")
