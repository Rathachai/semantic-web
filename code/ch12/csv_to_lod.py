"""ไปป์ไลน์ CSV → 5-star Linked Open Data

ขั้นตอน
-------
1. อ่าน CSV (ข้อมูล 3 ดาว)
2. ทำความสะอาดและออกแบบ URI              → 4 ดาว
3. แม็ปคอลัมน์เข้า vocabulary มาตรฐาน
4. เชื่อม owl:sameAs ไป Wikidata          → 5 ดาว
5. ตรวจคุณภาพก่อนเผยแพร่

รัน:  python3 code/ch12/csv_to_lod.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

UA = "SemanticWebCourse/1.0 (educational material)"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dist")

BASE = "https://data.example.org/"
VOC = Namespace(BASE + "vocab#")
UNI = Namespace(BASE + "university/")
PLACE = Namespace(BASE + "place/")
SCHEMA = Namespace("https://schema.org/")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

# ---- ข้อมูลตั้งต้น: CSV ระดับ 3 ดาว ที่มีปัญหาแบบที่เจอจริง ----
RAW_CSV = """name_en,name_th,founded,city,website
Chulalongkorn University,จุฬาลงกรณ์มหาวิทยาลัย,1917,Bangkok,https://www.chula.ac.th/
King Mongkut's Institute of Technology Ladkrabang,สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง,1960, Bangkok ,www.kmitl.ac.th
Chiang Mai University,มหาวิทยาลัยเชียงใหม่,1964,Chiang Mai,https://www.cmu.ac.th/
Mahidol University,มหาวิทยาลัยมหิดล,1888,Nakhon Pathom,https://mahidol.ac.th
Thammasat University,มหาวิทยาลัยธรรมศาสตร์,1934,bangkok,https://tu.ac.th/
"""


def head(n: int, title: str) -> None:
    print(f"\n{'─' * 68}\n  ขั้นที่ {n}: {title}\n{'─' * 68}")


def slugify(text: str) -> str:
    """แปลงข้อความเป็นส่วนของ URI ที่ปลอดภัย

    กฎ: ตัวพิมพ์เล็ก, ASCII เท่านั้น, ใช้ '-' คั่นคำ, ไม่มีอักขระพิเศษ
    """
    s = text.lower()
    s = re.sub(r"[''`]", "", s)          # ตัด apostrophe ออกก่อน ไม่แทนด้วย -
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# ================================================== 1
def read_csv() -> list[dict[str, str]]:
    head(1, "อ่าน CSV (ข้อมูลระดับ 3 ดาว)")
    rows = list(csv.DictReader(io.StringIO(RAW_CSV)))
    print(f"  อ่านได้ {len(rows)} แถว, {len(rows[0])} คอลัมน์")
    print(f"  คอลัมน์: {list(rows[0])}")
    print("\n  ⚠️ ปัญหาที่พบในข้อมูลดิบ:")
    print("     - 'Bangkok', ' Bangkok ', 'bangkok'  → ชื่อเมืองเดียวกันสะกดต่างกัน 3 แบบ")
    print("     - website บางแถวไม่มี scheme (www.kmitl.ac.th)")
    print("     - ชื่อมี apostrophe ซึ่งใช้ใน URI ไม่ได้")
    return rows


# ================================================== 2
def normalise(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    head(2, "ทำความสะอาดและออกแบบ URI")
    cleaned = []
    for r in rows:
        city_raw = r["city"]
        city = city_raw.strip()
        site = r["website"].strip()
        if site and not site.startswith(("http://", "https://")):
            site = "https://" + site
        cleaned.append({
            "name_en": r["name_en"].strip(),
            "name_th": r["name_th"].strip(),
            "founded": r["founded"].strip(),
            "city": city.title(),          # 'bangkok' และ ' Bangkok ' → 'Bangkok'
            "city_raw": city_raw,
            "website": site,
            "uri": UNI[slugify(r["name_en"])],
            "city_uri": PLACE[slugify(city)],
        })

    print(f"  {'ชื่อ':<52s} URI")
    for c in cleaned:
        print(f"  {c['name_en'][:50]:<52s} {str(c['uri']).replace(BASE, '')}")

    cities = sorted({c["city"] for c in cleaned})
    print(f"\n  เมืองหลังทำความสะอาด: {cities}")
    print(f"  ⬅️ จาก {len({r['city'] for r in rows})} ค่าที่ต่างกัน เหลือ {len(cities)}")
    return cleaned


# ================================================== 3
def build_graph(rows: list[dict[str, str]]) -> Graph:
    head(3, "แม็ปเข้า vocabulary มาตรฐาน → RDF (4 ดาว)")
    g = Graph()
    for prefix, ns in [("voc", VOC), ("uni", UNI), ("place", PLACE),
                       ("schema", SCHEMA), ("geo", GEO), ("skos", SKOS),
                       ("owl", OWL), ("rdfs", RDFS)]:
        g.bind(prefix, ns)

    g.add((VOC.University, RDF.type, OWL.Class))
    g.add((VOC.University, RDFS.subClassOf, SCHEMA.CollegeOrUniversity))
    g.add((VOC.City, RDF.type, OWL.Class))
    g.add((VOC.City, RDFS.subClassOf, SCHEMA.City))

    for r in rows:
        u = r["uri"]
        g.add((u, RDF.type, VOC.University))
        g.add((u, RDFS.label, Literal(r["name_en"], lang="en")))
        g.add((u, RDFS.label, Literal(r["name_th"], lang="th")))
        g.add((u, VOC.foundingYear, Literal(r["founded"], datatype=XSD.gYear)))
        g.add((u, VOC.locatedIn, r["city_uri"]))
        if r["website"]:
            g.add((u, SCHEMA.url, URIRef(r["website"])))

        c = r["city_uri"]
        g.add((c, RDF.type, VOC.City))
        g.add((c, RDFS.label, Literal(r["city"], lang="en")))

    print(f"  สร้าง RDF ได้ {len(g)} triples")
    print(f"  entity: {len(set(g.subjects(RDF.type, None)))} ตัว")
    print("\n  ตัวอย่างผลลัพธ์:")
    sample = Graph()
    for prefix, ns in g.namespaces():
        sample.bind(prefix, ns)
    for t in g.triples((UNI[slugify("Chulalongkorn University")], None, None)):
        sample.add(t)
    for line in sample.serialize(format="turtle").splitlines():
        if line.strip() and not line.startswith("@prefix"):
            print(f"    {line}")
    return g


# ================================================== 4
def link_to_wikidata(g: Graph, rows: list[dict[str, str]]) -> None:
    head(4, "เชื่อม owl:sameAs ไป Wikidata (5 ดาว)")

    def search(term: str) -> list[dict]:
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbsearchentities", "search": term, "language": "en",
            "format": "json", "limit": 3, "type": "item"})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp).get("search", [])

    print(f"  {'ชื่อ':<40s} {'QID':>12s}  คำอธิบายจาก Wikidata")
    linked = 0
    for r in rows:
        try:
            hits = search(r["name_en"])
        except Exception as exc:                   # noqa: BLE001
            print(f"  {r['name_en'][:38]:<40s} ⚠️ {type(exc).__name__}")
            continue

        # เกณฑ์อัตโนมัติ: label ต้องตรงกันเป๊ะ และคำอธิบายต้องบ่งบอกว่าเป็นสถาบันการศึกษา
        best = None
        for h in hits:
            desc = h.get("description", "").lower()
            if h.get("label", "").lower() == r["name_en"].lower() and \
               any(k in desc for k in ("universit", "institute", "college")):
                best = h
                break

        if best:
            g.add((r["uri"], OWL.sameAs, URIRef(f"http://www.wikidata.org/entity/{best['id']}")))
            linked += 1
            print(f"  {r['name_en'][:38]:<40s} {best['id']:>12s}  "
                  f"{best.get('description', '')[:44]}")
        else:
            top = hits[0]["id"] if hits else "-"
            print(f"  {r['name_en'][:38]:<40s} {'ไม่ผ่านเกณฑ์':>12s}  "
                  f"(ผู้สมัครอันดับ 1 คือ {top})")
        time.sleep(0.5)

    print(f"\n  เชื่อมอัตโนมัติได้ {linked}/{len(rows)} รายการ")
    if linked < len(rows):
        print("  ⚠️ ที่เหลือไม่ผ่านเกณฑ์อัตโนมัติ ต้องให้คนตรวจ -- ไม่ควรเดา")
    else:
        print("  ⚠️ ผ่านเกณฑ์ครบไม่ได้แปลว่าถูกทุกรายการ")
        print("     เกณฑ์นี้แค่ 'ชื่อตรงเป๊ะ + คำอธิบายบ่งบอกว่าเป็นสถาบันการศึกษา'")
        print("     ยังควรสุ่มตรวจก่อนเผยแพร่เสมอ")


# ================================================== 5
def quality_report(g: Graph) -> None:
    head(5, "ตรวจคุณภาพก่อนเผยแพร่")

    entities = {s for s in g.subjects(RDF.type, None) if isinstance(s, URIRef)}
    ours = {s for s in entities if str(s).startswith(BASE)
            and not str(s).startswith(str(VOC))}
    with_label = {s for s in ours if (s, RDFS.label, None) in g}
    with_th = {s for s in ours
               if any(isinstance(o, Literal) and o.language == "th"
                      for o in g.objects(s, RDFS.label))}
    with_link = {s for s in ours if (s, OWL.sameAs, None) in g}

    checks = [
        ("มี rdfs:label", len(with_label), len(ours)),
        ("มี label ภาษาไทย", len(with_th), len(ours)),
        ("มี owl:sameAs ออกนอก", len(with_link), len(ours)),
    ]
    print(f"  {'เกณฑ์':<26s} {'ผ่าน':>6s} {'ทั้งหมด':>8s}  สถานะ")
    for name, ok, total in checks:
        pct = 100 * ok / total if total else 0
        mark = "✅" if pct == 100 else ("⚠️" if pct >= 50 else "❌")
        print(f"  {name:<26s} {ok:>6d} {total:>8d}  {mark} {pct:.0f}%")

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "universities_from_csv.ttl")
    g.serialize(path, format="turtle")
    print(f"\n  💾 บันทึก {len(g)} triples → "
          f"{os.path.relpath(path, os.path.dirname(HERE))}")

    stars = 5 if with_link else 4
    print(f"\n  ⭐ ระดับที่ได้: {'⭐' * stars}")
    print("  💡 ตัวเลข 62% มาจากการที่ entity เมือง 3 ตัวยังไม่มี label ไทย")
    print("     และยังไม่ได้เชื่อมออก -- เป็นงานรอบถัดไปที่ต้องทำ")


if __name__ == "__main__":
    print("=" * 68)
    print("  ไปป์ไลน์ CSV → 5-star Linked Open Data")
    print("=" * 68)
    raw = read_csv()
    clean = normalise(raw)
    graph = build_graph(clean)
    try:
        link_to_wikidata(graph, clean)
    except Exception as exc:                       # noqa: BLE001
        print(f"  ⚠️ เชื่อมไม่สำเร็จ: {type(exc).__name__}: {exc}")
    quality_report(graph)
    print()
