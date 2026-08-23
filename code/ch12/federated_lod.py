"""บริโภค Linked Open Data -- เสริมข้อมูลของเราด้วยข้อมูลจากเว็บ

3 เทคนิค
--------
1. Dereference    -- ดึง RDF จาก URI ปลายทางของ owl:sameAs ตรง ๆ
2. Federated query -- ใช้ SERVICE ยิงข้าม endpoint
3. Entity linking  -- หา URI ที่ตรงกันเมื่อยังไม่มี sameAs

รัน:  python3 code/ch12/federated_lod.py

หมายเหตุ: ต้องต่ออินเทอร์เน็ต Wikidata Query Service มีการจำกัดอัตราที่เข้มงวด
          สคริปต์นี้จึงเลี่ยงไปใช้ Special:EntityData และ MediaWiki API
          ซึ่งเสถียรกว่าสำหรับการดึงข้อมูลรายตัว
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDFS, SKOS

UA = "SemanticWebCourse/1.0 (educational material; course example)"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "lod_dataset.ttl")

WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")
SCHEMA = Namespace("https://schema.org/")


def head(title: str) -> None:
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def http_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# ============================================== 1. Dereference
def dereference_wikidata(qid: str) -> Graph:
    """ดึง RDF ของ entity เดียวจาก Wikidata

    ใช้ Special:EntityData แทน Query Service เพราะไม่ติดการจำกัดอัตรา
    และเป็นวิธีที่ตรงกับหลัก Linked Data ข้อ 3 (dereference URI)
    """
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.ttl"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    g = Graph()
    g.parse(data=data, format="turtle")
    return g


def enrich_from_links(local: Graph, limit: int = 3) -> None:
    head("1. Dereference -- เสริมข้อมูลจาก URI ที่ sameAs ชี้ไป")

    targets = [o for _, _, o in local.triples((None, OWL.sameAs, None))
               if str(o).startswith(str(WD))]
    targets = sorted({str(t) for t in targets})[:limit]
    print(f"  จะดึงข้อมูลจาก {len(targets)} URI\n")

    for iri in targets:
        qid = iri.rsplit("/", 1)[-1]
        try:
            remote = dereference_wikidata(qid)
        except urllib.error.HTTPError as exc:
            print(f"  {qid}: ⚠️ ดึงไม่สำเร็จ HTTP {exc.code}")
            continue

        subj = URIRef(iri)
        labels = {o.language: str(o) for o in remote.objects(subj, RDFS.label)
                  if isinstance(o, Literal) and o.language}
        # หา local entity ที่ชี้มาที่ URI นี้
        ours = next(local.subjects(OWL.sameAs, subj), None)

        print(f"  {qid}  ({len(remote):,} triples ที่ดึงมา)")
        print(f"    entity ของเรา : {str(ours).rsplit('/', 1)[-1] if ours else '-'}")
        print(f"    ภาษาที่มี label: {len(labels)}")
        for lang in ("en", "th", "ja", "de"):
            if lang in labels:
                print(f"      {lang:3s} {labels[lang]}")
        time.sleep(1)   # มารยาทต่อ endpoint สาธารณะ


# ============================================== 2. Federated query
def federated_query() -> None:
    head("2. Federated query -- SERVICE ยิงข้าม endpoint")

    query = """
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dbo:  <http://dbpedia.org/ontology/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?uni ?studentCount ?abstract WHERE {
  # --- ส่วนนี้รันที่ DBpedia (endpoint หลัก) ---
  ?uni a dbo:University ;
       dbo:country dbr:Thailand ;
       dbo:abstract ?abstract .
  FILTER(LANG(?abstract) = "en")

  # --- ส่วนนี้ส่งต่อไป Wikidata ---
  OPTIONAL {
    ?uni owl:sameAs ?wd .
    FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/"))
    SERVICE <https://query.wikidata.org/sparql> {
      ?wd wdt:P2196 ?studentCount .
    }
  }
}
LIMIT 5"""

    print("  โครงสร้าง federated query:\n")
    for line in query.strip().splitlines():
        print(f"    {line}")

    print("\n  ⚠️ endpoint สาธารณะมักปิดหรือจำกัด SERVICE")
    print("     - Wikidata อนุญาต SERVICE เฉพาะ endpoint ใน whitelist")
    print("     - DBpedia จำกัดเวลา query อย่างเข้มงวด")
    print("     ในทางปฏิบัติจึงนิยม 'ดึงมาไว้ที่เดียวแล้ว query ในเครื่อง' มากกว่า")


# ============================================== 3. Entity linking
def entity_linking(local: Graph) -> None:
    head("3. Entity linking -- หา URI ที่ตรงกันเมื่อยังไม่มี sameAs")

    def search(term: str, limit: int = 3) -> list[dict]:
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbsearchentities", "search": term, "language": "en",
            "format": "json", "limit": limit, "type": "item"})
        return http_json(url).get("search", [])

    # เลือกเฉพาะ "ข้อมูลจริง" ที่ยังไม่มี sameAs ไป Wikidata
    #   ⚠️ ต้องกรอง term ของ vocabulary ออก มิฉะนั้นจะไปค้นคำว่า "Campus"
    #      กับ "City" ซึ่งเป็นชื่อ class ไม่ใช่ชื่อสิ่งของ
    VOC = "https://data.example.org/vocab#"
    candidates = []
    for s in set(local.subjects()):
        if not isinstance(s, URIRef):
            continue
        if not str(s).startswith("https://data.example.org/"):
            continue
        if str(s).startswith(VOC):
            continue
        has_wd = any(str(o).startswith(str(WD))
                     for o in list(local.objects(s, OWL.sameAs))
                     + list(local.objects(s, SKOS.exactMatch)))
        if has_wd:
            continue
        label = next((str(o) for o in local.objects(s, RDFS.label)
                      if isinstance(o, Literal) and o.language == "en"), None)
        if label:
            candidates.append((s, label))

    print(f"  entity ที่ยังไม่มีลิงก์ไป Wikidata : {len(candidates)}\n")

    for subj, label in sorted(candidates, key=lambda x: x[1])[:5]:
        print(f"  \"{label}\"")
        try:
            hits = search(label)
        except Exception as exc:                   # noqa: BLE001
            print(f"    ⚠️ ค้นไม่สำเร็จ: {type(exc).__name__}")
            continue
        if not hits:
            print("    ไม่พบผู้สมัคร")
        for h in hits:
            desc = h.get("description", "")[:52]
            print(f"    {h['id']:>10s}  {h.get('label', ''):<38s} {desc}")
        print("    ⚠️ ต้องมีคนตรวจก่อนเขียน owl:sameAs -- ชื่อเหมือนกันไม่ได้แปลว่าเป็นสิ่งเดียวกัน")
        time.sleep(1)


# ============================================== 4. ตรวจลิงก์ที่มีอยู่
def validate_links(local: Graph) -> None:
    head("4. ตรวจว่า URI ปลายทางยังใช้งานได้จริง")

    links = sorted({str(o) for _, _, o in local.triples((None, OWL.sameAs, None))}
                   | {str(o) for _, _, o in local.triples((None, SKOS.exactMatch, None))})
    hosts = Counter(u.split("/")[2] for u in links if "//" in u)
    print(f"  ลิงก์ทั้งหมด {len(links)} เส้น ไปยัง {len(hosts)} dataset\n")

    ok = dead = flaky = 0
    for url in links:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA},
                                         method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
            mark, ok = "✅", ok + 1
        except urllib.error.HTTPError as exc:
            # 3xx ที่หลุดมาถึงตรงนี้ยังถือว่า URI ใช้งานได้
            status = exc.code
            if status in (301, 302, 303, 307, 308):
                mark, ok = "✅", ok + 1
            else:
                mark, dead = "❌", dead + 1
        except Exception:                          # noqa: BLE001
            # timeout / DNS / connection reset -- ยังสรุปไม่ได้ว่า URI ตาย
            status, mark, flaky = "TMO", "⚠️", flaky + 1
        print(f"    {mark} {str(status):>3}  {url}")

    print(f"\n  สรุป: ใช้ได้ {ok} / ตาย {dead} / เรียกไม่สำเร็จชั่วคราว {flaky}")
    if dead:
        print("  ❌ owl:sameAs ที่ชี้ไปที่ตายแล้ว แย่กว่าไม่มี sameAs เลย")
    if flaky:
        print("  ⚠️ 'TMO' คือเรียกไม่ทันในเวลาที่กำหนด ไม่ใช่ลิงก์ตาย")
        print("     ต้องลองซ้ำหลายรอบก่อนสรุป -- endpoint สาธารณะไม่เสถียรเป็นเรื่องปกติ")


if __name__ == "__main__":
    print("=" * 70)
    print("  บริโภค Linked Open Data")
    print("=" * 70)

    graph = Graph()
    graph.parse(DATA, format="turtle")
    print(f"\n  โหลดข้อมูลของเรา: {len(graph)} triples")

    for fn in (enrich_from_links, federated_query, entity_linking, validate_links):
        try:
            fn(graph) if fn is not federated_query else fn()
        except Exception as exc:                   # noqa: BLE001
            print(f"\n  ⚠️ ขั้นตอนนี้ไม่สำเร็จ: {type(exc).__name__}: {exc}")
    print()
