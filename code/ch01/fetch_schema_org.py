"""
fetch_schema_org.py
-------------------
Chapter 01 companion script.

ดึงหน้าเว็บจริง แล้วสกัด Schema.org structured data ที่ฝังอยู่ใน 3 รูปแบบ:
  1. JSON-LD  (<script type="application/ld+json">)  -- รูปแบบที่แนะนำในปัจจุบัน
  2. Microdata (itemscope / itemtype / itemprop)
  3. RDFa     (typeof / property / vocab)

จากนั้นแปลง JSON-LD ที่ได้ให้เป็น RDF graph ด้วย rdflib และ serialize เป็น Turtle

Requirements:
    pip install requests rdflib

Usage:
    python fetch_schema_org.py
    python fetch_schema_org.py https://www.bbc.com/news
"""

import json
import re
import sys
from typing import Any, Dict, List

import requests
from rdflib import Graph

# ค่า default: หน้าเว็บที่รู้กันว่ามี JSON-LD markup อยู่จริง
DEFAULT_URLS = [
    "https://schema.org/Person",
    "https://www.wikidata.org/wiki/Q7186",
]

# ปลอมเป็น browser ทั่วไป เพราะบางเว็บบล็อก default user-agent ของ requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SemanticWebCourseBot/1.0; +http://example.org/bot)",
    "Accept": "text/html,application/xhtml+xml",
}

# ---------------------------------------------------------------------------
# 1) ดาวน์โหลดหน้าเว็บ
# ---------------------------------------------------------------------------


def fetch_html(url: str, timeout: int = 15) -> str:
    """ดึง HTML จาก url; raise requests.HTTPError ถ้า status ไม่ใช่ 2xx"""
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    # ให้ requests เดา encoding จาก content ถ้า header ไม่ได้ระบุมา
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


# ---------------------------------------------------------------------------
# 2) สกัด JSON-LD ออกจาก <script type="application/ld+json">
# ---------------------------------------------------------------------------

# หมายเหตุ: regex ใช้ได้ในระดับสอน; production ควรใช้ parser จริง (เช่น extruct + lxml)
JSONLD_PATTERN = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def extract_jsonld(html: str) -> List[Dict[str, Any]]:
    """คืน list ของ JSON-LD object ที่พบในหน้า (ข้าม block ที่ parse ไม่ผ่าน)"""
    blocks: List[Dict[str, Any]] = []
    for raw in JSONLD_PATTERN.findall(html):
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            print(f"  [warn] JSON-LD block parse ไม่ผ่าน: {exc}")
            continue
        # หนึ่ง block อาจเป็น object เดียว หรือเป็น array ของ object
        if isinstance(data, list):
            blocks.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            blocks.append(data)
    return blocks


# ---------------------------------------------------------------------------
# 3) ตรวจหา Microdata และ RDFa แบบคร่าว ๆ (นับจำนวน attribute ที่พบ)
# ---------------------------------------------------------------------------


def count_markup_signals(html: str) -> Dict[str, int]:
    """นับ attribute ที่บ่งชี้ว่ามี Microdata / RDFa อยู่ในหน้า"""
    return {
        "microdata_itemscope": len(re.findall(r"\bitemscope\b", html, re.I)),
        "microdata_itemtype": len(re.findall(r"\bitemtype\s*=", html, re.I)),
        "rdfa_typeof": len(re.findall(r"\btypeof\s*=", html, re.I)),
        "rdfa_property": len(re.findall(r"\bproperty\s*=", html, re.I)),
    }


# ---------------------------------------------------------------------------
# 4) สรุปสาระสำคัญของแต่ละ JSON-LD object
# ---------------------------------------------------------------------------


def summarize(block: Dict[str, Any]) -> str:
    """คืนบรรทัดสรุปสั้น ๆ: @type + name/headline ถ้ามี"""
    node_type = block.get("@type", "(no @type)")
    if isinstance(node_type, list):
        node_type = " | ".join(str(t) for t in node_type)
    label = block.get("name") or block.get("headline") or block.get("@id") or "(no name)"
    if isinstance(label, dict):  # กรณี {"@value": "...", "@language": "en"}
        label = label.get("@value", "(no name)")
    return f"@type={node_type}  name={label}"


# ---------------------------------------------------------------------------
# 5) แปลง JSON-LD -> RDF graph ด้วย rdflib
# ---------------------------------------------------------------------------


def jsonld_to_graph(blocks: List[Dict[str, Any]], base: str) -> Graph:
    """โหลดทุก JSON-LD block เข้า rdflib Graph เดียวกัน"""
    graph = Graph()
    for block in blocks:
        try:
            graph.parse(data=json.dumps(block), format="json-ld", publicID=base)
        except Exception as exc:  # noqa: BLE001 -- โชว์ error ให้ผู้เรียนเห็น
            print(f"  [warn] แปลงเป็น RDF ไม่สำเร็จ: {exc}")
    return graph


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def process(url: str) -> None:
    print("=" * 78)
    print(f"URL: {url}")
    print("=" * 78)

    try:
        html = fetch_html(url)
    except requests.RequestException as exc:
        print(f"  [error] ดึงหน้าเว็บไม่สำเร็จ: {exc}\n")
        return

    print(f"  ขนาด HTML: {len(html):,} characters")

    signals = count_markup_signals(html)
    print("  สัญญาณ markup อื่น ๆ:")
    for key, count in signals.items():
        print(f"    - {key:24s}: {count}")

    blocks = extract_jsonld(html)
    print(f"  พบ JSON-LD block: {len(blocks)} รายการ")

    for index, block in enumerate(blocks, start=1):
        print(f"    [{index}] {summarize(block)}")

    if not blocks:
        print("  (หน้านี้ไม่มี JSON-LD — ลอง URL อื่น เช่นหน้าข่าวหรือหน้าสินค้า)\n")
        return

    graph = jsonld_to_graph(blocks, base=url)
    print(f"  จำนวน triple ที่ได้: {len(graph)}")

    print("\n--- Turtle (10 triple แรก) ---")
    preview = Graph()
    for triple in list(graph)[:10]:
        preview.add(triple)
    # bind prefix ให้อ่านง่าย
    preview.bind("schema", "https://schema.org/")
    preview.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    print(preview.serialize(format="turtle"))


def main() -> None:
    urls = sys.argv[1:] or DEFAULT_URLS
    for url in urls:
        process(url)


if __name__ == "__main__":
    main()
