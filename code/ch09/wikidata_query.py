"""
wikidata_query.py
-----------------
Chapter 09 companion script.

Query Wikidata และ DBpedia แล้วแปลงผลเป็น RDF ของเราเอง

สาธิต:
  1. Wikidata: wdt: (truthy) vs p:/ps:/pq: (มี qualifier)
  2. Wikidata: P31/P279* pattern
  3. Wikidata: label service
  4. DBpedia: dbo: vs dbp:
  5. DBpedia: owl:sameAs links
  6. Entity linking ด้วย VALUES + chunking
  7. แปลงผลเป็น schema.org RDF

Requirements:
    pip install SPARQLWrapper rdflib

Usage:
    python wikidata_query.py                # รันทุก demo (ต้องต่อ internet)
    python wikidata_query.py --offline      # แสดงเฉพาะ query ไม่ยิง network
    python wikidata_query.py --demo 3       # รันเฉพาะ demo ที่ระบุ
"""

import sys
import time
from typing import Any, Dict, List, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SDO, XSD
from SPARQLWrapper import JSON, POST, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

WIKIDATA = "https://query.wikidata.org/sparql"
DBPEDIA = "https://dbpedia.org/sparql"

# ⚠️ Wikidata บล็อก request ที่ไม่ระบุตัวตน
USER_AGENT = "SemanticWebCourse/1.0 (https://example.org/course; contact@example.org)"

WD_PREFIXES = """
PREFIX wd:       <http://www.wikidata.org/entity/>
PREFIX wdt:      <http://www.wikidata.org/prop/direct/>
PREFIX p:        <http://www.wikidata.org/prop/>
PREFIX ps:       <http://www.wikidata.org/prop/statement/>
PREFIX pq:       <http://www.wikidata.org/prop/qualifier/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd:       <http://www.bigdata.com/rdf#>
PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema:   <http://schema.org/>
"""

DB_PREFIXES = """
PREFIX dbr:     <http://dbpedia.org/resource/>
PREFIX dbo:     <http://dbpedia.org/ontology/>
PREFIX dbp:     <http://dbpedia.org/property/>
PREFIX dbc:     <http://dbpedia.org/resource/Category:>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
"""

EX = Namespace("http://example.org/imported/")


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def run_query(
    endpoint: str,
    query: str,
    *,
    timeout: int = 60,
    retries: int = 3,
) -> Optional[List[Dict[str, Any]]]:
    """ยิง SELECT query พร้อม retry แบบ exponential backoff"""
    sparql = SPARQLWrapper(endpoint, agent=USER_AGENT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(timeout)
    sparql.setMethod(POST)

    for attempt in range(1, retries + 1):
        try:
            return sparql.query().convert()["results"]["bindings"]
        except SPARQLWrapperException as exc:
            print(f"    [{attempt}/{retries}] SPARQL error: {str(exc)[:120]}")
        except Exception as exc:                          # noqa: BLE001
            print(f"    [{attempt}/{retries}] {type(exc).__name__}: {str(exc)[:120]}")
        if attempt < retries:
            wait = 2.0 ** attempt
            print(f"    รอ {wait:.0f} วินาที...")
            time.sleep(wait)
    return None


def show(rows: Optional[List[Dict[str, Any]]], columns: List[str],
         limit: int = 12, width: int = 40) -> None:
    if rows is None:
        print("    ❌ query ล้มเหลว")
        return
    if not rows:
        print("    (ไม่มีผลลัพธ์)")
        return

    widths = {
        c: min(width, max(len(c), max((len(r.get(c, {}).get("value", "")) for r in rows), default=0)))
        for c in columns
    }
    print("    " + "  ".join(c.ljust(widths[c]) for c in columns))
    print("    " + "  ".join("-" * widths[c] for c in columns))
    for row in rows[:limit]:
        cells = []
        for c in columns:
            value = row.get(c, {}).get("value", "—")
            if value.startswith("http://www.wikidata.org/entity/"):
                value = value.rsplit("/", 1)[-1]
            if len(value) > widths[c]:
                value = value[: widths[c] - 1] + "…"
            cells.append(value.ljust(widths[c]))
        print("    " + "  ".join(cells))
    if len(rows) > limit:
        print(f"    ... อีก {len(rows) - limit} แถว")
    print(f"    ({len(rows)} แถว)")


# ---------------------------------------------------------------------------
# DEMO 1: wdt: (truthy) -- เร็ว ไม่มี qualifier
# ---------------------------------------------------------------------------

Q1 = WD_PREFIXES + """
SELECT ?award ?awardLabel WHERE {
  wd:Q7186 wdt:P166 ?award .              # Marie Curie -> award received
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
"""


def demo1() -> None:
    banner("1) wdt: (truthy) — ค่าโดยตรง ไม่มีบริบท")
    print("  query:\n" + "\n".join(f"    {l}" for l in Q1.strip().splitlines()[-5:]))
    print()
    show(run_query(WIKIDATA, Q1), ["award", "awardLabel"])


# ---------------------------------------------------------------------------
# DEMO 2: p:/ps:/pq: -- ได้ qualifier
# ---------------------------------------------------------------------------

Q2 = WD_PREFIXES + """
SELECT ?awardLabel ?year ?togetherWithLabel WHERE {
  wd:Q7186 p:P166 ?statement .
  ?statement ps:P166 ?award .
  OPTIONAL { ?statement pq:P585  ?time . BIND(YEAR(?time) AS ?year) }
  OPTIONAL { ?statement pq:P1706 ?togetherWith }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY ?year
"""


def demo2() -> None:
    banner("2) p:/ps:/pq: — statement node พร้อม qualifier")
    show(run_query(WIKIDATA, Q2), ["awardLabel", "year", "togetherWithLabel"])
    print("\n  💡 qualifier บอกปีที่ได้รับและได้ร่วมกับใคร -- wdt: ให้ข้อมูลนี้ไม่ได้")


# ---------------------------------------------------------------------------
# DEMO 3: P31/P279* -- pattern ที่ต้องใช้เกือบทุก query
# ---------------------------------------------------------------------------

Q3_NARROW = WD_PREFIXES + """
SELECT (COUNT(DISTINCT ?item) AS ?n) WHERE {
  ?item wdt:P31 wd:Q3918 ;          # instance of university (ตรง ๆ)
        wdt:P17 wd:Q869 .           # country = Thailand
}
"""

Q3_WIDE = WD_PREFIXES + """
SELECT (COUNT(DISTINCT ?item) AS ?n) WHERE {
  ?item wdt:P31/wdt:P279* wd:Q3918 ;    # รวม subclass ทุกระดับ
        wdt:P17 wd:Q869 .
}
"""

Q3_LIST = WD_PREFIXES + """
SELECT ?uni ?uniLabel ?inception WHERE {
  ?uni wdt:P31/wdt:P279* wd:Q3918 ;
       wdt:P17 wd:Q869 .
  OPTIONAL { ?uni wdt:P571 ?inception }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,th" . }
}
ORDER BY ?inception
LIMIT 15
"""


def demo3() -> None:
    banner("3) P31 vs P31/P279* — ทำไมต้องใช้ property path")

    narrow = run_query(WIKIDATA, Q3_NARROW)
    wide = run_query(WIKIDATA, Q3_WIDE)

    n1 = narrow[0]["n"]["value"] if narrow else "?"
    n2 = wide[0]["n"]["value"] if wide else "?"
    print(f"  wdt:P31 wd:Q3918          → {n1} มหาวิทยาลัยในไทย")
    print(f"  wdt:P31/wdt:P279* wd:Q3918 → {n2} มหาวิทยาลัยในไทย")
    print("\n  💡 ต่างกันเพราะ Wikidata มี subclass ของ university หลายชั้น")
    print("     เช่น public university, private university, technical university\n")

    show(run_query(WIKIDATA, Q3_LIST), ["uniLabel", "inception"])


# ---------------------------------------------------------------------------
# DEMO 4: DBpedia -- dbo: vs dbp:
# ---------------------------------------------------------------------------

Q4_DBO = DB_PREFIXES + """
SELECT ?p ?o WHERE {
  dbr:Marie_Curie ?p ?o .
  FILTER(STRSTARTS(STR(?p), "http://dbpedia.org/ontology/"))
  FILTER(!isLiteral(?o) || LANG(?o) IN ("", "en"))
  FILTER(?p != dbo:abstract && ?p != dbo:wikiPageWikiLink)
}
LIMIT 15
"""

Q4_DBP = DB_PREFIXES + """
SELECT ?p ?o WHERE {
  dbr:Marie_Curie ?p ?o .
  FILTER(STRSTARTS(STR(?p), "http://dbpedia.org/property/"))
  FILTER(!isLiteral(?o) || LANG(?o) IN ("", "en"))
}
LIMIT 15
"""


def demo4() -> None:
    banner("4) DBpedia — dbo: (curated) vs dbp: (raw infobox)")

    print("  ▸ dbo: — ผ่าน mapping และ normalize แล้ว")
    show(run_query(DBPEDIA, Q4_DBO, timeout=90), ["p", "o"], limit=10, width=45)

    print("\n  ▸ dbp: — ค่าดิบจาก infobox")
    show(run_query(DBPEDIA, Q4_DBP, timeout=90), ["p", "o"], limit=10, width=45)

    print("\n  💡 dbo: ให้ IRI และ typed literal — dbp: ให้ string ดิบ")
    print("     ใช้ dbo: เสมอถ้ามี")


# ---------------------------------------------------------------------------
# DEMO 5: DBpedia owl:sameAs -- ทำไม DBpedia เป็น hub ของ LOD
# ---------------------------------------------------------------------------

Q5 = DB_PREFIXES + """
SELECT ?external WHERE {
  dbr:Marie_Curie owl:sameAs ?external .
}
"""


def demo5() -> None:
    banner("5) DBpedia เป็น hub ของ LOD — owl:sameAs links")

    rows = run_query(DBPEDIA, Q5, timeout=90)
    if not rows:
        return

    grouped: Dict[str, List[str]] = {}
    for row in rows:
        iri = row["external"]["value"]
        if "wikidata.org" in iri:
            key = "Wikidata"
        elif "viaf.org" in iri:
            key = "VIAF"
        elif "id.loc.gov" in iri:
            key = "Library of Congress"
        elif "yago" in iri:
            key = "YAGO"
        elif ".dbpedia.org" in iri:
            key = "DBpedia (ภาษาอื่น)"
        else:
            key = "อื่น ๆ"
        grouped.setdefault(key, []).append(iri)

    for key, iris in sorted(grouped.items(), key=lambda x: -len(x[1])):
        print(f"  {key:24s} {len(iris):>3} links")
        for iri in iris[:2]:
            print(f"      {iri}")
    print(f"\n  รวม {len(rows)} owl:sameAs links")


# ---------------------------------------------------------------------------
# DEMO 6: Entity linking ด้วย VALUES + chunking
# ---------------------------------------------------------------------------


def lookup_entities(qids: List[str], chunk_size: int = 25) -> List[Dict[str, Any]]:
    """ดึงข้อมูลหลาย entity ด้วย VALUES -- ลดจาก N request เหลือ ceil(N/chunk)"""
    results: List[Dict[str, Any]] = []
    requests_made = 0

    for i in range(0, len(qids), chunk_size):
        chunk = qids[i:i + chunk_size]
        values = " ".join(f"wd:{qid}" for qid in chunk)
        rows = run_query(WIKIDATA, WD_PREFIXES + f"""
        SELECT ?item ?itemLabel ?itemDescription WHERE {{
          VALUES ?item {{ {values} }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,th" . }}
        }}
        """)
        requests_made += 1
        if rows:
            results.extend(rows)
        time.sleep(1)                                    # มารยาท

    print(f"    entity ที่ค้นหา : {len(qids)}")
    print(f"    HTTP requests  : {requests_made}  (ไม่ใช่ {len(qids)}!)")
    return results


def demo6() -> None:
    banner("6) ENTITY LINKING — VALUES + chunking")

    qids = [
        "Q7186",     # Marie Curie
        "Q937",      # Albert Einstein
        "Q9095",     # Wilhelm Röntgen
        "Q935",      # Isaac Newton
        "Q1035",     # Charles Darwin
        "Q39599",    # Ada Lovelace
        "Q7259",     # Alan Turing
        "Q11812",    # Thomas Jefferson
    ]
    show(lookup_entities(qids), ["item", "itemLabel", "itemDescription"], width=45)


# ---------------------------------------------------------------------------
# DEMO 7: แปลงผลเป็น RDF ของเราเอง
# ---------------------------------------------------------------------------

Q7 = WD_PREFIXES + """
SELECT ?person ?personLabel ?birthDate ?countryLabel WHERE {
  ?person wdt:P166 wd:Q38104 ;          # Nobel Prize in Physics
          wdt:P569 ?birthDate .
  OPTIONAL { ?person wdt:P27 ?country }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY ?birthDate
LIMIT 10
"""


def wikidata_to_rdf(rows: List[Dict[str, Any]]) -> Graph:
    """แปลงผล Wikidata เป็น RDF ที่ใช้ schema.org"""
    g = Graph()
    g.bind("ex", EX)
    g.bind("schema", SDO)
    g.bind("owl", OWL)

    for row in rows:
        wd_iri = row["person"]["value"]
        qid = wd_iri.rsplit("/", 1)[-1]
        person = EX[qid]

        g.add((person, RDF.type, SDO.Person))
        # ⚠️ ใส่ owl:sameAs ชี้กลับต้นทางเสมอ เพื่อให้ตรวจสอบย้อนกลับได้
        g.add((person, OWL.sameAs, URIRef(wd_iri)))

        if "personLabel" in row:
            name = row["personLabel"]["value"]
            g.add((person, SDO.name, Literal(name)))
            g.add((person, RDFS.label, Literal(name, lang="en")))
        if "birthDate" in row:
            g.add((person, SDO.birthDate,
                   Literal(row["birthDate"]["value"][:10], datatype=XSD.date)))
        if "countryLabel" in row:
            g.add((person, SDO.nationality, Literal(row["countryLabel"]["value"])))

    return g


def demo7() -> None:
    banner("7) แปลงผล Wikidata เป็น RDF ของเราเอง (schema.org)")

    rows = run_query(WIKIDATA, Q7)
    if not rows:
        return

    show(rows, ["personLabel", "birthDate", "countryLabel"])

    graph = wikidata_to_rdf(rows)
    print(f"\n  แปลงเป็น RDF: {len(graph)} triples\n")

    sample = Graph()
    for prefix, ns in graph.namespaces():
        sample.bind(prefix, ns)
    first = next(iter(set(graph.subjects())), None)
    if first:
        for triple in graph.triples((first, None, None)):
            sample.add(triple)
        print(sample.serialize(format="turtle"))

    graph.serialize(destination="nobel-physics.ttl", format="turtle")
    print("  บันทึก nobel-physics.ttl")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

DEMOS = {
    1: demo1, 2: demo2, 3: demo3, 4: demo4, 5: demo5, 6: demo6, 7: demo7,
}


def main() -> None:
    if "--offline" in sys.argv:
        banner("โหมด OFFLINE — แสดงเฉพาะ query")
        for label, query in [
            ("1) wdt: truthy", Q1),
            ("2) p:/ps:/pq: qualifier", Q2),
            ("3) P31/P279*", Q3_LIST),
            ("4) DBpedia dbo:", Q4_DBO),
            ("5) DBpedia sameAs", Q5),
            ("7) Nobel laureates", Q7),
        ]:
            print(f"\n▸ {label}")
            body = query.split("\n\n")[-1] if "\n\n" in query else query
            for line in body.strip().splitlines():
                print(f"    {line}")
        print("\n\nเทคนิคสำคัญ:")
        print("  1. ใส่ User-Agent เสมอ -- Wikidata บล็อกถ้าไม่มี")
        print("  2. ใช้ wdt: เป็น default (เร็วกว่า + ตัด deprecated ออกให้)")
        print("  3. ใช้ p:/ps:/pq: เมื่อต้องการ qualifier")
        print("  4. ใช้ wdt:P31/wdt:P279* เกือบทุกครั้ง")
        print("  5. SERVICE wikibase:label ต้องอยู่ท้ายสุด")
        print("  6. ใช้ VALUES + chunking แทนการยิงทีละ entity")
        print("  7. ใส่ owl:sameAs ชี้กลับต้นทางเสมอ")
        return

    if "--demo" in sys.argv:
        index = int(sys.argv[sys.argv.index("--demo") + 1])
        DEMOS[index]()
        return

    for demo in DEMOS.values():
        demo()


if __name__ == "__main__":
    main()
