"""
sparql_construct.py
-------------------
Chapter 06 companion script.

สาธิต query form ที่ไม่ใช่ SELECT:
  - CONSTRUCT : แปลง vocabulary, materialize inference, สร้าง link ใหม่
  - ASK       : data quality check
  - DESCRIBE  : สำรวจ resource
  - UPDATE    : INSERT DATA / DELETE-INSERT WHERE / INSERT WHERE

Requirements:
    pip install rdflib

Usage:
    python sparql_construct.py
"""

from pathlib import Path

from rdflib import Graph, Namespace, URIRef

DATA = Path(__file__).resolve().parents[2] / "data" / "university.ttl"

UNI = Namespace("http://example.org/university#")
SCHEMA = Namespace("https://schema.org/")

PREFIXES = """
PREFIX uni:    <http://example.org/university#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX schema: <https://schema.org/>
"""


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# CONSTRUCT
# ---------------------------------------------------------------------------


def demo_construct_vocabulary_mapping(g: Graph) -> Graph:
    """แปลง uni: vocabulary -> schema.org"""
    banner("CONSTRUCT 1 — Vocabulary mapping (uni: -> schema.org)")

    query = PREFIXES + """
    CONSTRUCT {
      ?person a schema:Person ;
              schema:name        ?name ;
              schema:affiliation ?org .
      ?org a schema:Organization ;
           schema:name ?orgName .
    }
    WHERE {
      ?person a uni:Student ;
              rdfs:label ?name ;
              uni:memberOf ?org .
      ?org rdfs:label ?orgName .
    }
    """
    result = g.query(query).graph
    result.bind("schema", SCHEMA)
    result.bind("uni", UNI)
    print(f"  ได้ {len(result)} triples\n")
    print(result.serialize(format="turtle"))
    return result


def demo_construct_materialize(g: Graph) -> Graph:
    """materialize subClassOf transitivity"""
    banner("CONSTRUCT 2 — Materialize subClassOf inference")

    query = PREFIXES + """
    CONSTRUCT { ?s a ?superClass }
    WHERE {
      ?s a ?class .
      ?class rdfs:subClassOf+ ?superClass .
      FILTER(?superClass != owl:NamedIndividual)
    }
    """
    result = g.query(query).graph
    result.bind("uni", UNI)
    print(f"  ได้ {len(result)} inferred type triples")

    by_subject: dict = {}
    for s, _, o in result:
        by_subject.setdefault(str(s).split("#")[-1], []).append(str(o).split("#")[-1])
    for subject, types in sorted(by_subject.items()):
        print(f"    {subject:20s} -> {sorted(set(types))}")
    return result


def demo_construct_new_links(g: Graph) -> Graph:
    """สร้างความสัมพันธ์ใหม่จากข้อมูลที่มี"""
    banner("CONSTRUCT 3 — สร้าง uni:classmateOf จากการลงเรียนวิชาเดียวกัน")

    query = PREFIXES + """
    CONSTRUCT { ?a uni:classmateOf ?b }
    WHERE {
      ?a uni:enrolledIn ?c .
      ?b uni:enrolledIn ?c .
      FILTER(?a != ?b)
    }
    """
    result = g.query(query).graph
    result.bind("uni", UNI)
    print(f"  ได้ {len(result)} triples\n")
    print(result.serialize(format="turtle"))
    return result


# ---------------------------------------------------------------------------
# ASK
# ---------------------------------------------------------------------------

QUALITY_CHECKS = {
    "นักศึกษาที่ไม่มี studentId": """
        ASK { ?s a uni:Student . FILTER NOT EXISTS { ?s uni:studentId ?id } }
    """,
    "วิชาที่ไม่มีอาจารย์สอน": """
        ASK { ?c uni:courseCode ?code . FILTER NOT EXISTS { ?p uni:teaches ?c } }
    """,
    "GPA ที่อยู่นอกช่วง 0.0-4.0": """
        ASK { ?s uni:gpa ?g . FILTER(?g < 0.0 || ?g > 4.0) }
    """,
    "วิชาที่หน่วยกิตไม่ใช่จำนวนบวก": """
        ASK { ?c uni:credits ?cr . FILTER(?cr <= 0) }
    """,
    "resource ที่ไม่มี rdfs:label": """
        ASK { ?s a uni:Student . FILTER NOT EXISTS { ?s rdfs:label ?l } }
    """,
}


def demo_ask(g: Graph) -> None:
    banner("ASK — Data quality checks")
    problems = 0
    for name, query in QUALITY_CHECKS.items():
        found = bool(g.query(PREFIXES + query))
        if found:
            problems += 1
        mark = "⚠️  พบปัญหา" if found else "✅ ผ่าน    "
        print(f"  {mark}  {name}")
    print(f"\n  สรุป: พบปัญหา {problems}/{len(QUALITY_CHECKS)} รายการ")


# ---------------------------------------------------------------------------
# DESCRIBE
# ---------------------------------------------------------------------------


def demo_describe(g: Graph) -> None:
    banner("DESCRIBE — สำรวจ resource")

    result = g.query(PREFIXES + "DESCRIBE uni:alice").graph
    result.bind("uni", UNI)
    print(f"  DESCRIBE uni:alice -> {len(result)} triples\n")
    print(result.serialize(format="turtle"))

    print("\n  หมายเหตุ: ผลของ DESCRIBE ขึ้นกับ engine")
    print("  ถ้าต้องการผลที่แน่นอน ให้ใช้ CONSTRUCT แทน:")

    controlled = g.query(PREFIXES + """
    CONSTRUCT {
      uni:alice ?p ?o .
      ?s ?p2 uni:alice .
    }
    WHERE {
      { uni:alice ?p ?o } UNION { ?s ?p2 uni:alice }
    }
    """).graph
    print(f"  CONSTRUCT (ทั้งสองทิศทาง) -> {len(controlled)} triples")


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


def demo_update(g: Graph) -> None:
    banner("SPARQL UPDATE")

    before = len(g)
    print(f"  ก่อนเริ่ม: {before} triples")

    # --- INSERT DATA ---
    g.update(PREFIXES + """
    INSERT DATA {
      uni:eve a owl:NamedIndividual , uni:Student ;
          rdfs:label         "Eve Chen"@en ;
          uni:studentId      "S-2025-0001" ;
          uni:enrollmentYear 2025 ;
          uni:gpa            3.60 ;
          uni:memberOf       uni:csDept ;
          uni:enrolledIn     uni:cs101 .
    }
    """)
    print(f"  หลัง INSERT DATA (เพิ่ม eve): {len(g)} triples  (+{len(g) - before})")

    # --- DELETE/INSERT WHERE ---
    g.update(PREFIXES + """
    DELETE { uni:eve uni:gpa ?old }
    INSERT { uni:eve uni:gpa 3.80 }
    WHERE  { uni:eve uni:gpa ?old }
    """)
    new_gpa = g.value(UNI.eve, UNI.gpa)
    print(f"  หลัง DELETE/INSERT: eve gpa = {new_gpa}")

    # --- INSERT WHERE (materialize) ---
    count_before = len(g)
    g.update(PREFIXES + """
    INSERT { ?a uni:classmateOf ?b }
    WHERE {
      ?a uni:enrolledIn ?c .
      ?b uni:enrolledIn ?c .
      FILTER(?a != ?b)
    }
    """)
    print(f"  หลัง INSERT WHERE (classmateOf): {len(g)} triples  (+{len(g) - count_before})")

    # --- DELETE WHERE ---
    g.update(PREFIXES + "DELETE WHERE { uni:eve ?p ?o }")
    print(f"  หลัง DELETE WHERE (ลบ eve): {len(g)} triples")

    print("\n  ⚠️ ทดสอบด้วย SELECT ที่ pattern เดียวกันก่อนลบจริงเสมอ")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    graph = Graph()
    graph.parse(DATA, format="turtle")
    print(f"โหลด {DATA.name}: {len(graph)} triples")

    demo_construct_vocabulary_mapping(graph)
    demo_construct_materialize(graph)
    demo_construct_new_links(graph)
    demo_ask(graph)
    demo_describe(graph)
    demo_update(graph)


if __name__ == "__main__":
    main()
