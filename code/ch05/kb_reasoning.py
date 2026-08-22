"""
kb_reasoning.py
---------------
Chapter 05 companion script.

โหลด Knowledge Base ที่แยกไฟล์ TBox / ABox แล้วรัน reasoning สองแบบ:

  A) owlrl (OWL 2 RL)  -- ไม่ต้องมี Java ทำงานบน rdflib โดยตรง
  B) owlready2 + HermiT -- OWL 2 DL เต็มรูปแบบ ตรวจ consistency ได้

จากนั้นสาธิต:
  - instance retrieval  (class มีสมาชิกใครบ้าง)
  - realization         (individual อยู่ class ไหน)
  - ผลของ Open World Assumption กับ dave ที่ไม่มี enrolledIn
  - ผลของ role chain uni:instructorOf
  - การตรวจจับ inconsistency

Requirements:
    pip install rdflib owlrl owlready2
    (owlready2 + HermiT ต้องมี Java 8+)

Usage:
    python kb_reasoning.py
"""

from pathlib import Path

import owlrl
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS

HERE = Path(__file__).parent
TBOX = HERE / "university_tbox.ttl"
ABOX = HERE / "university_abox.ttl"

UNI = Namespace("http://example.org/university#")


def banner(title: str) -> None:
    print("\n" + "=" * 74)
    print(f"  {title}")
    print("=" * 74)


def short(term) -> str:
    """ตัด namespace ออกเพื่อให้อ่านง่าย"""
    return str(term).split("#")[-1].split("/")[-1]


# ---------------------------------------------------------------------------
# A) โหลด KB แบบแยกไฟล์
# ---------------------------------------------------------------------------


def load_kb() -> Graph:
    """โหลด TBox และ ABox เข้า graph เดียวกัน"""
    g = Graph()
    g.bind("uni", UNI)
    g.parse(TBOX, format="turtle")
    tbox_size = len(g)
    g.parse(ABOX, format="turtle")

    print(f"  TBox : {tbox_size:>4} triples  ({TBOX.name})")
    print(f"  ABox : {len(g) - tbox_size:>4} triples  ({ABOX.name})")
    print(f"  รวม  : {len(g):>4} triples")
    return g


# ---------------------------------------------------------------------------
# B) reasoning ด้วย owlrl (OWL 2 RL) -- ไม่ต้องมี Java
# ---------------------------------------------------------------------------


def reason_owlrl(g: Graph) -> set:
    """รัน OWL 2 RL closure; คืนเซตของ inferred triple"""
    asserted = set(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return set(g) - asserted


QUERIES = {
    "ทุกคนที่เป็น uni:Person": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?p WHERE { ?p a uni:Person . }
    """,
    "ทุกอย่างที่เป็น uni:Course": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?c WHERE { ?c a uni:Course . }
    """,
    "uni:GraduateStudent (defined class)": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s WHERE { ?s a uni:GraduateStudent . }
    """,
    "uni:PublishedResearcher (defined class)": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?p WHERE { ?p a uni:PublishedResearcher . }
    """,
    "csDept partOf อะไรบ้าง (transitive)": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?o WHERE { uni:csDept uni:partOf ?o . }
    """,
    "ใคร involvedIn cs501 (subPropertyOf)": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?p WHERE { ?p uni:involvedIn uni:cs501 . }
    """,
    "cs501 taughtBy ใคร (inverse)": """
        PREFIX uni: <http://example.org/university#>
        SELECT ?p WHERE { uni:cs501 uni:taughtBy ?p . }
    """,
}


def run_queries(g: Graph, header: str) -> None:
    banner(header)
    for title, query in QUERIES.items():
        rows = sorted({short(r[0]) for r in g.query(query)})
        print(f"  {title}")
        print(f"    → {len(rows):>2} : {rows or '(ไม่มี)'}")


# ---------------------------------------------------------------------------
# C) reasoning ด้วย owlready2 + HermiT (OWL 2 DL)
# ---------------------------------------------------------------------------


def reason_hermit() -> None:
    """โหลด KB เข้า owlready2 แล้วรัน HermiT"""
    banner("OWL 2 DL REASONING (owlready2 + HermiT)")

    try:
        from owlready2 import (
            OwlReadyInconsistentOntologyError,
            World,
            sync_reasoner_hermit,
        )
    except ImportError:
        print("  ข้าม: ไม่ได้ติดตั้ง owlready2")
        return

    # owlready2 อ่าน Turtle ไม่ได้โดยตรง -> แปลงเป็น RDF/XML ก่อน
    merged = Graph()
    merged.parse(TBOX, format="turtle")
    merged.parse(ABOX, format="turtle")

    # ตัด owl:imports ออก มิฉะนั้น owlready2 จะพยายามดึง IRI นั้นผ่าน network
    # (เราโหลด TBox เข้ามาเองแล้ว จึงไม่ต้อง import ซ้ำ)
    merged.remove((None, OWL.imports, None))

    tmp = HERE / "_merged_kb.owl"
    merged.serialize(destination=str(tmp), format="xml")

    world = World()
    onto = world.get_ontology(f"file://{tmp}").load()

    def types_of(name: str) -> list:
        ind = onto.search_one(iri=f"*{name}")
        if ind is None:
            return []
        return sorted(c.name for c in ind.is_a if hasattr(c, "name"))

    before = {n: types_of(n) for n in
              ["alice", "bob", "carol", "dave", "profSmith", "profJones"]}

    try:
        with onto:
            sync_reasoner_hermit(x=world, infer_property_values=True)
        print("  ✅ KB consistent")
    except OwlReadyInconsistentOntologyError:
        print("  ❌ KB inconsistent")
        tmp.unlink(missing_ok=True)
        return

    print("\n  Realization — ก่อน vs หลัง reasoning:")
    for name, old in before.items():
        new = types_of(name)
        gained = [t for t in new if t not in old]
        mark = f"  ← เพิ่ม {gained}" if gained else ""
        print(f"    {name:12s} {old} → {new}{mark}")

    print("\n  Retrieval:")
    for cls_name in ["Person", "Student", "GraduateStudent", "UndergraduateStudent",
                     "Professor", "BusyProfessor", "Supervisor", "PublishedResearcher"]:
        cls = onto.search_one(iri=f"*{cls_name}")
        if cls is None:
            continue
        members = sorted(i.name for i in cls.instances())
        print(f"    {cls_name:22s} = {members}")

    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# D) สาธิต Open World Assumption
# ---------------------------------------------------------------------------


def demo_owa(g: Graph) -> None:
    banner("OPEN WORLD ASSUMPTION — กรณีของ dave")

    q_enrolled = """
        PREFIX uni: <http://example.org/university#>
        SELECT ?c WHERE { uni:dave uni:enrolledIn ?c . }
    """
    rows = list(g.query(q_enrolled))
    print(f"  dave enrolledIn : {len(rows)} รายการ")
    print("""
  ใน SPARQL ได้ 0 ผลลัพธ์ แต่สำหรับ reasoner ความหมายคือ "ไม่ทราบ"
  ไม่ใช่ "ไม่ได้ลงเรียนอะไรเลย"

  ดังนั้น reasoner จึงสรุปไม่ได้ว่า:
    - dave เป็น UndergraduateStudent  (ต้องมี enrolledIn อย่างน้อย 1)
    - dave ไม่ได้ลงเรียนอะไรเลย

  ถ้าต้องการให้สรุปได้ ต้องเพิ่ม closure axiom:
    uni:dave a [ a owl:Restriction ;
                 owl:onProperty     uni:enrolledIn ;
                 owl:maxCardinality "0"^^xsd:nonNegativeInteger ] .

  หรือใช้ SHACL ซึ่งทำงานแบบ closed world (ดู Chapter 07)
""")


# ---------------------------------------------------------------------------
# E) สาธิต inconsistency
# ---------------------------------------------------------------------------


def demo_inconsistency(base: Graph) -> None:
    banner("สาธิต INCONSISTENCY — เพิ่ม triple ที่ขัดกับ TBox")

    bad_data = """
        @prefix uni: <http://example.org/university#> .
        # alice เป็นทั้ง Student และ Staff -- ขัดกับ uni:Student owl:disjointWith uni:Staff
        uni:alice a uni:Staff .
    """
    print("  เพิ่ม: uni:alice a uni:Staff .")
    print("  TBox มี: uni:Student owl:disjointWith uni:Staff")
    print("""
  Justification:
    1. uni:Student owl:disjointWith uni:Staff
    2. uni:alice a uni:Student
    3. uni:alice a uni:Staff
    → ไม่มี interpretation ใดที่ทั้งสามข้อเป็นจริงพร้อมกัน  ⇒ INCONSISTENT

  หมายเหตุ: owlrl (OWL 2 RL) ตรวจ inconsistency ได้จำกัด
            ต้องใช้ HermiT/Pellet จึงจะรายงานได้ครบถ้วน
""")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    banner("โหลด KNOWLEDGE BASE (แยกไฟล์ TBox / ABox)")
    graph = load_kb()

    run_queries(graph, "ก่อน REASONING")

    banner("OWL 2 RL REASONING (owlrl — ไม่ต้องมี Java)")
    inferred = reason_owlrl(graph)
    print(f"  inferred : {len(inferred)} triples")
    print(f"  total    : {len(graph)} triples")

    run_queries(graph, "หลัง REASONING")

    demo_owa(graph)
    reason_hermit()
    demo_inconsistency(graph)


if __name__ == "__main__":
    main()
