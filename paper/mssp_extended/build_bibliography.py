"""Build the MSSP BibTeX file from verified metadata and check every DOI.

Input:
- paper/mssp_extended/references_spec.json: the cited keys, in manuscript form ([n] -> "ref<n>", [N#] -> "N#"),
  each with a DOI (metadata from Crossref) or a complete manual entry (books, proceedings without DOI).
- paper/mssp_extended/manuscript_mssp_draft.md: only keys actually cited there are written.

Crossref responses are cached in paper/mssp_extended/literature_evidence/crossref/ (Crossref metadata is
CC0), so the check can be rerun offline with --offline. Requests use a generic User-Agent and carry
no personal data.

Output:
- paper/mssp_extended/latex/references_mssp.bib;
- paper/mssp_extended/literature_evidence/bibliography_check.csv: one row per key with the Crossref title, year,
  first author, venue, volume, issue, pages or article number, and a status. The status is "ok",
  "manual", or a list of mismatches against the expected title and year recorded in the spec.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "paper/mssp_extended"
SPEC = PKG / "references_spec.json"
DRAFT = PKG / "manuscript_mssp_draft.md"
BIB = PKG / "latex/references_mssp.bib"
CACHE = PKG / "literature_evidence/crossref"
REPORT = PKG / "literature_evidence/bibliography_check.csv"
USER_AGENT = "Mozilla/5.0 (research-bibliography-check)"
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")


def cited_keys(text):
    keys = set()
    for a, b, c, d in re.findall(r"\[(N?)(\d+)\]–\[(N?)(\d+)\]", text):
        keys.update(f"{a}{k}" for k in range(int(b), int(d) + 1))
    keys.update(re.findall(r"\[(N?\d+)\]", text))
    return {k if k.startswith("N") else f"ref{k}" for k in keys}


def cache_path(doi):
    return CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", doi) + ".json")


def crossref(doi, offline):
    path = cache_path(doi)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if offline:
        raise SystemExit(f"no cached Crossref record for {doi}")
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        message = json.loads(response.read().decode("utf-8"))["message"]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(message, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    time.sleep(1.0)
    return message


def clean(text):
    import html
    text = html.unescape(re.sub(r"<[^>]+>", "", text or ""))
    for dash in ("\u2010", "\u2011"):
        text = text.replace(dash, "-")
    return " ".join(text.split())


def protect(title):
    """Brace words containing capitals after their first letter or digits mixed with capitals."""
    def repl(match):
        word = match.group(0)
        return "{" + word + "}" if re.search(r"[A-Z].*[A-Z]|[A-Z].*\d|\d.*[A-Z]", word) or word in ("Gaussian",) else word
    return re.sub(r"[A-Za-z0-9][A-Za-z0-9\-]*", repl, title)


def latex_escape(text):
    return text.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")


def authors(message):
    names = []
    for person in message.get("author", []):
        family, given = person.get("family", ""), person.get("given", "")
        names.append(f"{family}, {given}" if given else family)
    return " and ".join(names)


def year(message):
    for field in ("published-print", "published-online", "issued"):
        parts = message.get(field, {}).get("date-parts", [[None]])[0]
        if parts and parts[0]:
            return str(parts[0])
    return ""


def normalize(text):
    text = unicodedata.normalize("NFKD", clean(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def full_title(message, spec):
    """Crossref title plus subtitle; a spec override (documented in the spec) takes precedence."""
    if spec.get("title_override"):
        return spec["title_override"]
    title = clean(message["title"][0])
    if message.get("subtitle") and clean(message["subtitle"][0]).lower() not in title.lower():
        title += ": " + clean(message["subtitle"][0])
    return title


def entry_from_crossref(key, spec, message):
    kind = {"journal-article": "article", "proceedings-article": "inproceedings",
            "book-chapter": "incollection", "book": "book"}.get(message.get("type"), "article")
    fields = {"author": authors(message), "title": "{" + protect(latex_escape(full_title(message, spec))) + "}",
              "year": year(message), "doi": spec["doi"]}
    container = clean((message.get("container-title") or [""])[0])
    if kind == "article":
        fields["journal"] = latex_escape(spec.get("journal", container))
    elif kind in ("inproceedings", "incollection"):
        fields["booktitle"] = latex_escape(spec.get("booktitle", container))
    for source, target in (("volume", "volume"), ("issue", "number")):
        if message.get(source):
            fields[target] = message[source]
    pages = message.get("page") or message.get("article-number") or spec.get("pages", "")
    if pages:
        fields["pages"] = pages.replace("-", "--")
    fields.update(spec.get("override", {}))
    return kind, fields


def render(key, kind, fields):
    order = ("author", "title", "journal", "booktitle", "publisher", "address", "year", "volume", "number",
             "pages", "note", "doi", "url")
    lines = [f"@{kind}{{{key},"]
    for name in order:
        if fields.get(name):
            lines.append(f"  {name} = {{{fields[name]}}},")
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use cached Crossref records only")
    args = parser.parse_args()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    cited = cited_keys(DRAFT.read_text(encoding="utf-8"))
    missing = sorted(cited - set(spec))
    if missing:
        raise SystemExit(f"cited keys without a reference spec: {missing}")
    entries, rows, problems = [], [], []
    for key in sorted(cited, key=lambda k: (k.startswith("N"), int(re.sub(r"\D", "", k)))):
        item = spec[key]
        if "doi" in item:
            if not DOI_PATTERN.match(item["doi"]):
                problems.append(f"{key}: malformed DOI {item['doi']}")
            message = crossref(item["doi"], args.offline)
            kind, fields = entry_from_crossref(key, item, message)
            status = []
            if normalize(full_title(message, item)) != normalize(item["expected_title"]):
                status.append("title differs from expected")
            if year(message) != str(item["expected_year"]):
                status.append(f"year {year(message)} != expected {item['expected_year']}")
            if item.get("expected_first_author") and normalize(item["expected_first_author"]) not in normalize(
                    (message.get("author") or [{}])[0].get("family", "")):
                status.append("first author differs")
            rows.append({"key": key, "doi": item["doi"], "title": full_title(message, item), "year": year(message),
                         "first_author": (message.get("author") or [{}])[0].get("family", ""),
                         "venue": clean((message.get("container-title") or [""])[0]),
                         "volume": message.get("volume", ""), "issue": message.get("issue", ""),
                         "pages_or_article": message.get("page") or message.get("article-number") or "",
                         "status": "; ".join(status) or "ok"})
            problems += [f"{key}: {s}" for s in status]
        else:
            kind, fields = item["manual"]["type"], dict(item["manual"]["fields"])
            rows.append({"key": key, "doi": "", "title": fields.get("title", ""), "year": fields.get("year", ""),
                         "first_author": fields.get("author", "").split(",")[0], "venue":
                         fields.get("booktitle", fields.get("publisher", "")), "volume": "", "issue": "",
                         "pages_or_article": fields.get("pages", ""), "status": "manual"})
        entries.append(render(key, kind, fields))
    BIB.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    with open(REPORT, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    unused = sorted(set(spec) - cited)
    print(f"wrote {len(entries)} entries to {BIB.relative_to(ROOT)}; unused spec keys: {unused or 'none'}")
    if problems:
        sys.exit("\n".join(problems))


if __name__ == "__main__":
    main()
