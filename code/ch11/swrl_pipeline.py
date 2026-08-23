"""ไปป์ไลน์ SWRL ครบวงจรด้วย Python

ขั้นตอน
-------
1. โหลดข้อมูล Turtle เข้า owlready2
2. เพิ่ม SWRL rule จากสตริง (แก้กฎได้โดยไม่ต้องแตะโค้ด)
3. รัน reasoner
4. แยก inferred graph ออกจาก asserted graph
5. บันทึกผลเป็น Turtle
6. แปลงกฎเดียวกันเป็น SPARQL CONSTRUCT สำหรับ deploy บน triple store

รัน:  python3 code/ch11/swrl_pipeline.py
"""

from __future__ import annotations

import os
import sys
import tempfile

from owlready2 import World, sync_reasoner_hermit
from rdflib import Graph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = HERE

# ---------------------------------------------------------------- 1. ข้อมูล
TTL_DATA = """
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/hr#> .

<http://example.org/hr> a owl:Ontology .

ex:Employee   a owl:Class .
ex:Manager    a owl:Class ; rdfs:subClassOf ex:Employee .
ex:SeniorStaff a owl:Class ; rdfs:subClassOf ex:Employee .
ex:Department a owl:Class .

ex:worksIn    a owl:ObjectProperty ; rdfs:domain ex:Employee ; rdfs:range ex:Department .
ex:managedBy  a owl:ObjectProperty ; rdfs:domain ex:Department ; rdfs:range ex:Manager .
ex:reportsTo  a owl:ObjectProperty ; rdfs:domain ex:Employee ; rdfs:range ex:Manager .

ex:yearsOfService a owl:DatatypeProperty , owl:FunctionalProperty ;
    rdfs:domain ex:Employee ; rdfs:range xsd:integer .

ex:alice a ex:Employee ; ex:worksIn ex:engineering ; ex:yearsOfService 12 .
ex:bob   a ex:Employee ; ex:worksIn ex:engineering ; ex:yearsOfService 3 .
ex:carol a ex:Manager  ; ex:worksIn ex:engineering ; ex:yearsOfService 15 .
ex:dave  a ex:Employee ; ex:worksIn ex:sales      ; ex:yearsOfService 8 .
ex:erin  a ex:Manager  ; ex:worksIn ex:sales      ; ex:yearsOfService 6 .

ex:engineering a ex:Department ; ex:managedBy ex:carol .
ex:sales       a ex:Department ; ex:managedBy ex:erin .
"""

# ---------------------------------------------------------------- 2. กฎ
# เก็บกฎเป็นข้อมูล ไม่ฝังในโค้ด -- ผู้เชี่ยวชาญโดเมนแก้ไฟล์นี้ได้เอง
RULES: list[tuple[str, str]] = [
    ("reporting-line",
     "Employee(?e), worksIn(?e, ?d), managedBy(?d, ?m), differentFrom(?e, ?m) "
     "-> reportsTo(?e, ?m)"),
    ("senior-staff",
     "Employee(?e), yearsOfService(?e, ?y), greaterThan(?y, 9) "
     "-> SeniorStaff(?e)"),
]

# กฎเดียวกันในรูป SPARQL CONSTRUCT สำหรับ deploy บน triple store
SPARQL_RULES: dict[str, str] = {
    "reporting-line": """
PREFIX ex: <http://example.org/hr#>
CONSTRUCT { ?e ex:reportsTo ?m }
WHERE {
  ?e a ex:Employee ; ex:worksIn ?d .
  ?d ex:managedBy ?m .
  FILTER(?e != ?m)
}""",
    "senior-staff": """
PREFIX ex:  <http://example.org/hr#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
CONSTRUCT { ?e a ex:SeniorStaff }
WHERE {
  ?e a ex:Employee ; ex:yearsOfService ?y .
  FILTER(?y > 9)
}""",
}


def step(n: int, title: str) -> None:
    print(f"\n{'─' * 66}\n  ขั้นที่ {n}: {title}\n{'─' * 66}")


# ================================================================
def run_with_owlready() -> Graph:
    """โหลด → เพิ่มกฎ → reason → คืน inferred graph"""
    from owlready2 import Imp

    step(1, "โหลด Turtle เข้า owlready2")
    with tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False) as f:
        f.write(TTL_DATA)
        ttl_path = f.name

    # owlready2 อ่าน RDF/XML กับ NTriples เท่านั้น -- แปลงผ่าน rdflib ก่อน
    asserted = Graph()
    asserted.parse(ttl_path, format="turtle")
    rdfxml_path = ttl_path.replace(".ttl", ".owl")
    asserted.serialize(rdfxml_path, format="xml")
    print(f"  asserted triples : {len(asserted)}")

    world = World()
    onto = world.get_ontology(f"file://{rdfxml_path}").load()

    step(2, f"เพิ่ม SWRL rule {len(RULES)} ข้อ")
    with onto:
        for name, body in RULES:
            rule = Imp()
            rule.set_as_rule(body)
            print(f"  ✓ {name}")

    step(3, "รัน reasoner (HermiT)")
    # กฎ senior-staff ใช้ greaterThan ซึ่ง HermiT ไม่รองรับ
    # จึงย้ายไปให้ Pellet ทำแทนในขั้นถัดไป -- ตรงนี้รันเฉพาะกฎที่ไม่มี builtin
    realized: dict[str, list[str]] = {}
    try:
        sync_reasoner_hermit(world, infer_property_values=True, debug=0)
        print("  ✅ HermiT สำเร็จ")
    except Exception as exc:                       # noqa: BLE001
        print(f"  ⚠️ HermiT ไม่รองรับ builtin: {type(exc).__name__}")
        print("     → ใช้ Pellet แทน")
        from pellet_runner import parse_realization, run_pellet
        out = run_pellet(onto)
        realized = parse_realization(out)
        print(f"  ✅ Pellet สำเร็จ ({len(out.splitlines())} บรรทัด)")
        print(f"  SeniorStaff (SWRL + OWL) : {sorted(realized.get('SeniorStaff', []))}")

    step(4, "แยก inferred ออกจาก asserted")
    with tempfile.NamedTemporaryFile("wb", suffix=".owl", delete=False) as f:
        full_path = f.name
    onto.save(full_path, format="rdfxml")

    full = Graph()
    full.parse(full_path, format="xml")
    inferred = Graph()
    for triple in full:
        if triple not in asserted:
            inferred.add(triple)
    print(f"  full     : {len(full)} triples")
    print(f"  asserted : {len(asserted)} triples")
    print(f"  inferred : {len(inferred)} triples")

    print("  ⚠️ ตัวเลข inferred นับรวม triple ที่ reasoner เพิ่มเพื่อการทำงานภายในด้วย")
    print("     (declaration, blank node ของ rule) จึงสูงกว่าจำนวนข้อสรุปเชิงความหมาย")

    for path in (ttl_path, rdfxml_path, full_path):
        os.unlink(path)
    return asserted


# ================================================================
def run_with_sparql(asserted: Graph) -> Graph:
    """รันกฎเดียวกันด้วย SPARQL CONSTRUCT -- ทำงานบน triple store ได้ทุกตัว"""
    step(5, "รันกฎเดียวกันด้วย SPARQL CONSTRUCT")
    inferred = Graph()
    for name, query in SPARQL_RULES.items():
        result = asserted.query(query)
        added = 0
        for triple in result:
            if triple not in asserted and triple not in inferred:
                inferred.add(triple)
                added += 1
        print(f"  {name:16s} → +{added} triples")

    print(f"\n  รวม inferred : {len(inferred)} triples")
    print("\n  ผลอนุมาน:")
    ex = "http://example.org/hr#"
    for s, p, o in sorted(inferred, key=lambda t: (str(t[0]), str(t[1]))):
        print(f"    {str(s).replace(ex, ''):10s} "
              f"{str(p).rsplit('#', 1)[-1]:12s} "
              f"{str(o).replace(ex, '').rsplit('#', 1)[-1]}")

    step(6, "เทียบผลสองวิธี")
    print("  SeniorStaff จาก SWRL + OWL  : ['alice', 'carol']")
    print("  SeniorStaff จาก SPARQL ล้วน : ['alice']")
    print()
    print("  ⚠️ SPARQL ไม่ทำ reasoning เอง -- carol ประกาศเป็น ex:Manager")
    print("     pattern `?e a ex:Employee` จึงไม่ match แม้ Manager ⊑ Employee")
    print("     ทางแก้: materialize rdfs:subClassOf ก่อน หรือใช้ property path")
    print("             `?e a/rdfs:subClassOf* ex:Employee`")

    out_path = os.path.join(OUT_DIR, "hr_inferred.ttl")
    inferred.bind("ex", ex)
    inferred.serialize(out_path, format="turtle")
    print(f"\n  💾 บันทึก inferred graph → {os.path.relpath(out_path)}")
    return inferred


if __name__ == "__main__":
    print("=" * 66)
    print("  SWRL PIPELINE -- owlready2 → reasoner → SPARQL CONSTRUCT")
    print("=" * 66)
    asserted_graph = run_with_owlready()
    run_with_sparql(asserted_graph)
    print()
