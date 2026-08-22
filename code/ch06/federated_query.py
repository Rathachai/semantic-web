"""
federated_query.py
------------------
Chapter 06 companion script.

Query SPARQL endpoint สาธารณะด้วย SPARQLWrapper และทำ federated query
โดยเน้นเทคนิคที่ทำให้เร็วและไม่ถูก block:

  1. query endpoint เดียว (Wikidata / DBpedia)
  2. federated ด้วย SERVICE keyword (บน endpoint ที่รองรับ)
  3. federation แบบ manual: query แยกกันแล้ว join เอง (ใช้ได้กับ rdflib)
  4. ใช้ VALUES ส่งค่าเป็นชุดเพื่อลดจำนวน request
  5. error handling + retry + timeout

Requirements:
    pip install SPARQLWrapper rdflib

Usage:
    python federated_query.py                 # รันทุก demo (ต้องต่อ internet)
    python federated_query.py --offline       # ข้าม demo ที่ต้องใช้ network
"""

import sys
import time
from typing import Any, Dict, List, Optional

from SPARQLWrapper import JSON, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

WIKIDATA = "https://query.wikidata.org/sparql"
DBPEDIA = "https://dbpedia.org/sparql"

# endpoint สาธารณะบังคับให้ระบุตัวตน -- ไม่ใส่อาจถูก block
USER_AGENT = "SemanticWebCourse/1.0 (https://example.org/course; contact@example.org)"


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# 1) helper: query endpoint พร้อม retry และ timeout
# ---------------------------------------------------------------------------


def run_query(
    endpoint: str,
    query: str,
    timeout: int = 60,
    retries: int = 3,
    backoff: float = 2.0,
) -> Optional[List[Dict[str, Any]]]:
    """
    ส่ง SELECT query ไปยัง endpoint แล้วคืน list ของ binding
    คืน None ถ้าล้มเหลวหลัง retry ครบ
    """
    sparql = SPARQLWrapper(endpoint, agent=USER_AGENT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(timeout)

    for attempt in range(1, retries + 1):
        try:
            data = sparql.query().convert()
            return data["results"]["bindings"]
        except SPARQLWrapperException as exc:
            print(f"    [attempt {attempt}/{retries}] SPARQL error: {exc}")
        except Exception as exc:  # noqa: BLE001 -- network error หลายชนิด
            print(f"    [attempt {attempt}/{retries}] {type(exc).__name__}: {exc}")

        if attempt < retries:
            wait = backoff ** attempt
            print(f"    รอ {wait:.1f} วินาทีแล้วลองใหม่...")
            time.sleep(wait)

    return None


def show(rows: Optional[List[Dict[str, Any]]], columns: List[str], limit: int = 10) -> None:
    """พิมพ์ผลลัพธ์เป็นตาราง"""
    if rows is None:
        print("    ❌ query ล้มเหลว")
        return
    if not rows:
        print("    (ไม่มีผลลัพธ์)")
        return

    widths = {c: max(len(c), max(len(r.get(c, {}).get("value", "")) for r in rows)) for c in columns}
    widths = {c: min(w, 45) for c, w in widths.items()}

    print("    " + "  ".join(c.ljust(widths[c]) for c in columns))
    print("    " + "  ".join("-" * widths[c] for c in columns))
    for row in rows[:limit]:
        cells = []
        for c in columns:
            value = row.get(c, {}).get("value", "—")
            if len(value) > widths[c]:
                value = value[: widths[c] - 1] + "…"
            cells.append(value.ljust(widths[c]))
        print("    " + "  ".join(cells))
    if len(rows) > limit:
        print(f"    ... อีก {len(rows) - limit} แถว")
    print(f"    ({len(rows)} แถว)")


# ---------------------------------------------------------------------------
# 2) Query endpoint เดียว
# ---------------------------------------------------------------------------


def demo_wikidata() -> None:
    banner("1) WIKIDATA — นักฟิสิกส์ที่ได้รางวัลโนเบล")

    query = """
    PREFIX wd:   <http://www.wikidata.org/entity/>
    PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
    PREFIX wikibase: <http://wikiba.se/ontology#>
    PREFIX bd:   <http://www.bigdata.com/rdf#>

    SELECT ?person ?personLabel ?birthDate
    WHERE {
      ?person wdt:P166 wd:Q38104 ;      # award received = Nobel Prize in Physics
              wdt:P569 ?birthDate .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    ORDER BY ?birthDate
    LIMIT 10
    """
    show(run_query(WIKIDATA, query), ["personLabel", "birthDate"])


def demo_dbpedia() -> None:
    banner("2) DBPEDIA — นักวิทยาศาสตร์ที่เกิดในโปแลนด์")

    query = """
    PREFIX dbo:  <http://dbpedia.org/ontology/>
    PREFIX dbr:  <http://dbpedia.org/resource/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?scientist ?name ?birthDate
    WHERE {
      ?scientist a dbo:Scientist ;
                 dbo:birthPlace dbr:Poland ;
                 rdfs:label ?name .
      OPTIONAL { ?scientist dbo:birthDate ?birthDate }
      FILTER(LANG(?name) = "en")
    }
    LIMIT 10
    """
    show(run_query(DBPEDIA, query), ["name", "birthDate"])


# ---------------------------------------------------------------------------
# 3) Federated query ด้วย SERVICE
# ---------------------------------------------------------------------------


def demo_service_keyword() -> None:
    banner("3) FEDERATED ด้วย SERVICE — DBpedia เรียก Wikidata")

    query = """
    PREFIX dbo:  <http://dbpedia.org/ontology/>
    PREFIX dbr:  <http://dbpedia.org/resource/>
    PREFIX owl:  <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wdt:  <http://www.wikidata.org/prop/direct/>

    SELECT ?name ?wdEntity ?occupation
    WHERE {
      # --- ส่วนที่รันบน DBpedia ---
      ?scientist a dbo:Scientist ;
                 dbo:birthPlace dbr:Poland ;
                 rdfs:label ?name ;
                 owl:sameAs ?wdEntity .
      FILTER(LANG(?name) = "en")
      FILTER(STRSTARTS(STR(?wdEntity), "http://www.wikidata.org/entity/"))

      # --- ส่งไปรันที่ Wikidata แล้ว join กลับ ---
      SERVICE SILENT <https://query.wikidata.org/sparql> {
        ?wdEntity wdt:P106/rdfs:label ?occupation .
        FILTER(LANG(?occupation) = "en")
      }
    }
    LIMIT 10
    """
    print("  ⚠️ query นี้อาจ timeout — endpoint สาธารณะจำกัดเวลาประมวลผล")
    show(run_query(DBPEDIA, query, timeout=90), ["name", "occupation"])


# ---------------------------------------------------------------------------
# 4) Manual federation -- ใช้ได้กับ rdflib ที่ไม่รองรับ SERVICE
# ---------------------------------------------------------------------------


def demo_manual_federation() -> None:
    banner("4) MANUAL FEDERATION — query แยกกันแล้ว join เอง")

    print("  ขั้นที่ 1: ดึง Wikidata entity ของนักวิทยาศาสตร์จาก DBpedia")
    dbpedia_query = """
    PREFIX dbo:  <http://dbpedia.org/ontology/>
    PREFIX dbr:  <http://dbpedia.org/resource/>
    PREFIX owl:  <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?wdEntity WHERE {
      ?s a dbo:Scientist ;
         dbo:birthPlace dbr:Poland ;
         rdfs:label ?name ;
         owl:sameAs ?wdEntity .
      FILTER(LANG(?name) = "en")
      FILTER(STRSTARTS(STR(?wdEntity), "http://www.wikidata.org/entity/"))
    }
    LIMIT 8
    """
    dbpedia_rows = run_query(DBPEDIA, dbpedia_query)
    if not dbpedia_rows:
        print("    ❌ ขั้นที่ 1 ล้มเหลว")
        return

    name_by_entity = {r["wdEntity"]["value"]: r["name"]["value"] for r in dbpedia_rows}
    print(f"    ได้ {len(name_by_entity)} entity")

    print("\n  ขั้นที่ 2: สร้าง VALUES แล้วยิง Wikidata **ครั้งเดียว**")
    values = " ".join(f"<{iri}>" for iri in name_by_entity)
    wikidata_query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wdt:  <http://www.wikidata.org/prop/direct/>

    SELECT ?item ?occupationLabel WHERE {{
      VALUES ?item {{ {values} }}
      ?item wdt:P106 ?occupation .
      ?occupation rdfs:label ?occupationLabel .
      FILTER(LANG(?occupationLabel) = "en")
    }}
    """
    wikidata_rows = run_query(WIKIDATA, wikidata_query)
    if not wikidata_rows:
        print("    ❌ ขั้นที่ 2 ล้มเหลว")
        return

    print("\n  ขั้นที่ 3: join ผลลัพธ์ใน Python")
    merged: Dict[str, set] = {}
    for row in wikidata_rows:
        entity = row["item"]["value"]
        merged.setdefault(name_by_entity.get(entity, entity), set()).add(
            row["occupationLabel"]["value"]
        )

    for name, occupations in sorted(merged.items()):
        print(f"    {name:35s} {', '.join(sorted(occupations))}")

    print(f"\n  ✅ ใช้ HTTP request ทั้งหมดเพียง 2 ครั้ง (ไม่ใช่ {len(name_by_entity)} ครั้ง)")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    if "--offline" in sys.argv:
        print("โหมด offline — ข้าม demo ที่ต้องใช้ network")
        print("\nเทคนิคสำคัญที่สาธิตในไฟล์นี้:")
        print("  1. ใส่ User-Agent เสมอเมื่อเรียก endpoint สาธารณะ")
        print("  2. ตั้ง timeout และทำ retry แบบ exponential backoff")
        print("  3. ใช้ SERVICE SILENT เพื่อกัน endpoint ล่ม")
        print("  4. ใช้ VALUES ส่งค่าเป็นชุด -- ลดจาก N request เหลือ 1")
        print("  5. rdflib ไม่รองรับ SERVICE -> ทำ manual federation แทน")
        return

    demo_wikidata()
    demo_dbpedia()
    demo_service_keyword()
    demo_manual_federation()


if __name__ == "__main__":
    main()
