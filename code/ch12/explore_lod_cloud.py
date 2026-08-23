"""สำรวจ LOD Cloud -- ดูว่า hub แต่ละแห่งเชื่อมไปที่ไหนบ้าง

รัน:  python3 code/ch12/explore_lod_cloud.py

หมายเหตุ: ต้องต่ออินเทอร์เน็ต และ endpoint สาธารณะอาจช้าหรือล่มได้
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import Counter

UA = "SemanticWebCourse/1.0 (educational material)"
WIKIDATA = "https://query.wikidata.org/sparql"
DBPEDIA = "https://dbpedia.org/sparql"


def sparql(endpoint: str, query: str, timeout: int = 60) -> list[dict[str, str]]:
    """ยิง SPARQL แบบ GET แล้วคืนผลเป็น list ของ dict ที่แบนแล้ว"""
    url = endpoint + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return [{k: v["value"] for k, v in row.items()}
            for row in data["results"]["bindings"]]


def head(title: str) -> None:
    print(f"\n{'=' * 66}\n  {title}\n{'=' * 66}")


# ---------------------------------------------------------------- 1
def external_ids(qid: str = "Q1861") -> None:
    """นับว่า entity หนึ่งใน Wikidata เชื่อมออกไปกี่ฐานข้อมูล"""
    head(f"1. Wikidata {qid} เชื่อมออกไปกี่แหล่ง")

    rows = sparql(WIKIDATA, f"""
SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {{
  wd:{qid} ?p ?v .
  ?prop wikibase:directClaim ?p ;
        wikibase:propertyType wikibase:ExternalId .
}}""")
    print(f"  จำนวน external identifier ที่ต่างกัน : {rows[0]['n']}")

    rows = sparql(WIKIDATA, f"""
SELECT ?propLabel ?value WHERE {{
  VALUES ?p {{ wdt:P646 wdt:P1566 wdt:P214 wdt:P227 wdt:P402 }}
  wd:{qid} ?p ?value .
  ?prop wikibase:directClaim ?p .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}""")
    print("\n  ตัวอย่างลิงก์ออกที่สำคัญ:")
    for r in rows:
        print(f"    {r['propLabel']:26s} {r['value']}")


# ---------------------------------------------------------------- 2
def label_languages(qid: str = "Q1861") -> None:
    """ประโยชน์ที่ได้ฟรีจากการเชื่อมเข้า Wikidata: label หลายภาษา"""
    head(f"2. ประโยชน์ที่ได้ฟรี -- label ของ {qid}")

    rows = sparql(WIKIDATA, f"""
SELECT (COUNT(?label) AS ?n) WHERE {{
  wd:{qid} rdfs:label ?label .
}}""")
    print(f"  จำนวนภาษาที่มี label : {rows[0]['n']}")

    rows = sparql(WIKIDATA, f"""
SELECT ?lang ?label WHERE {{
  VALUES ?lang {{ "en" "th" "ja" "zh" "de" "fr" }}
  wd:{qid} rdfs:label ?label .
  FILTER(LANG(?label) = ?lang)
}}""")
    for r in rows:
        print(f"    {r['lang']:4s} {r['label']}")


# ---------------------------------------------------------------- 3
def dbpedia_sameas(resource: str = "Bangkok") -> None:
    """ดูว่า DBpedia เชื่อม owl:sameAs ออกไปยัง dataset ใดบ้าง"""
    head(f"3. DBpedia :{resource} เชื่อม owl:sameAs ไปที่ไหน")

    rows = sparql(DBPEDIA, f"""
SELECT ?same WHERE {{
  <http://dbpedia.org/resource/{resource}> owl:sameAs ?same .
}}
LIMIT 500""")

    hosts = Counter(r["same"].split("/")[2] for r in rows if "//" in r["same"])
    print(f"  จำนวน owl:sameAs ทั้งหมด : {len(rows)}")
    print("\n  dataset ปลายทาง (ไม่รวม DBpedia ภาษาอื่น):")
    for host, n in hosts.most_common():
        if host.endswith("dbpedia.org") and host != "dbpedia.org":
            continue
        print(f"    {n:>3}  {host}")


if __name__ == "__main__":
    print("=" * 66)
    print("  สำรวจ LOD Cloud ผ่าน Wikidata")
    print("=" * 66)
    try:
        external_ids()
        label_languages()
        dbpedia_sameas()
    except Exception as exc:                       # noqa: BLE001
        print(f"\n⚠️ เรียก endpoint ไม่สำเร็จ: {type(exc).__name__}: {exc}")
        print("   endpoint สาธารณะอาจถูกจำกัดอัตราหรือปิดปรับปรุงชั่วคราว")
    print()
