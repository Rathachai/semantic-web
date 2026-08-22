"""
create_graph.py
---------------
Chapter 02 companion script.

สร้าง RDF graph ตั้งแต่ศูนย์ด้วย rdflib แสดง:
  1. การใช้ URIRef, Literal, BNode
  2. การใช้ Namespace และ bind() เพื่อให้ serialize ออกมาสวย
  3. การ add / remove / set triple
  4. การค้นหา triple ด้วย triples(), value(), objects()
  5. การใช้ Collection สำหรับ rdf:List
  6. graph operations: union, intersection, difference, isomorphic

Requirements:
    pip install rdflib

Usage:
    python create_graph.py
"""

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF, RDF, RDFS, XSD

# ---------------------------------------------------------------------------
# 1) เตรียม namespace
# ---------------------------------------------------------------------------

EX = Namespace("http://example.org/")

# rdflib มี namespace มาตรฐานให้แล้ว: RDF, RDFS, OWL, XSD, FOAF, DC, DCTERMS, SKOS


def build_graph() -> Graph:
    """สร้าง graph ของนักวิทยาศาสตร์"""
    g = Graph()

    # bind prefix -> ทำให้ serialize ออกมาใช้ ex: แทน IRI เต็ม
    g.bind("ex", EX)
    g.bind("foaf", FOAF)
    g.bind("rdfs", RDFS)

    # -- (a) triple ที่ object เป็น IRI --
    g.add((EX.MarieCurie, RDF.type, EX.Scientist))
    g.add((EX.MarieCurie, FOAF.knows, EX.PierreCurie))
    g.add((EX.MarieCurie, EX.worksAt, EX.UniversityOfParis))

    # -- (b) triple ที่ object เป็น plain literal --
    g.add((EX.MarieCurie, FOAF.name, Literal("Marie Curie")))

    # -- (c) language-tagged literal --
    g.add((EX.MarieCurie, RDFS.label, Literal("Marie Curie", lang="en")))
    g.add((EX.MarieCurie, RDFS.label, Literal("มารี กูว์รี", lang="th")))

    # -- (d) typed literal --
    g.add((EX.MarieCurie, EX.birthDate, Literal("1867-11-07", datatype=XSD.date)))
    g.add((EX.MarieCurie, EX.awardCount, Literal(2)))          # rdflib เดา xsd:integer ให้
    g.add((EX.MarieCurie, EX.isLaureate, Literal(True)))       # xsd:boolean

    # -- (e) blank node สำหรับ structured value --
    address = BNode()
    g.add((EX.MarieCurie, EX.hasAddress, address))
    g.add((address, EX.street, Literal("12 Rue Cuvier")))
    g.add((address, EX.city, Literal("Paris")))

    # -- (f) เพื่อนร่วมงาน --
    g.add((EX.PierreCurie, RDF.type, EX.Scientist))
    g.add((EX.PierreCurie, FOAF.name, Literal("Pierre Curie")))
    g.add((EX.PierreCurie, FOAF.knows, EX.MarieCurie))

    return g


# ---------------------------------------------------------------------------
# 2) RDF Collection (ordered list)
# ---------------------------------------------------------------------------


def add_award_list(g: Graph) -> None:
    """เพิ่ม rdf:List ของรางวัลที่มีลำดับ"""
    list_head = BNode()
    g.add((EX.MarieCurie, EX.awardList, list_head))
    Collection(
        g,
        list_head,
        [EX.NobelPrizeInPhysics, EX.NobelPrizeInChemistry],
    )


# ---------------------------------------------------------------------------
# 3) การค้นหาใน graph
# ---------------------------------------------------------------------------


def explore(g: Graph) -> None:
    print("\n--- ค้นหาแบบ pattern matching ---")

    # triples((s, p, o)) -- ใส่ None ตรงตำแหน่งที่เป็น wildcard
    print("ทุก triple ที่ subject = MarieCurie:")
    for _, p, o in g.triples((EX.MarieCurie, None, None)):
        print(f"  {p.n3(g.namespace_manager):>18}  {o.n3(g.namespace_manager)}")

    print("\nทุก Scientist ใน graph:")
    for subject in g.subjects(RDF.type, EX.Scientist):
        name = g.value(subject, FOAF.name)   # value() คืนค่าเดียว (หรือ None)
        print(f"  {subject}  ->  {name}")

    print("\nทุก label ของ MarieCurie (objects คืน generator):")
    for label in g.objects(EX.MarieCurie, RDFS.label):
        print(f"  {label!r}  lang={label.language}")

    # ตรวจว่ามี triple นี้หรือไม่
    exists = (EX.MarieCurie, FOAF.knows, EX.PierreCurie) in g
    print(f"\nMarie knows Pierre? {exists}")

    # นับ triple ตาม predicate
    print("\nจำนวน triple ต่อ predicate:")
    counts: dict = {}
    for _, p, _ in g:
        counts[p] = counts.get(p, 0) + 1
    for p, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>3}  {p.n3(g.namespace_manager)}")


# ---------------------------------------------------------------------------
# 4) แก้ไข graph
# ---------------------------------------------------------------------------


def modify(g: Graph) -> None:
    print("\n--- แก้ไข graph ---")
    print(f"ก่อนแก้: {len(g)} triples")

    # remove -- ลบตาม pattern (None = wildcard)
    g.remove((EX.MarieCurie, EX.awardCount, None))
    print(f"หลังลบ awardCount: {len(g)} triples")

    # set -- แทนที่ค่าเดิมทั้งหมดของ (subject, predicate) ด้วยค่าใหม่
    g.set((EX.MarieCurie, EX.awardCount, Literal(2)))
    print(f"หลัง set awardCount: {len(g)} triples")


# ---------------------------------------------------------------------------
# 5) Graph operations
# ---------------------------------------------------------------------------


def graph_algebra() -> None:
    print("\n--- Graph operations ---")

    g1 = Graph()
    g1.add((EX.A, EX.p, Literal("1")))
    g1.add((EX.B, EX.p, Literal("2")))

    g2 = Graph()
    g2.add((EX.B, EX.p, Literal("2")))
    g2.add((EX.C, EX.p, Literal("3")))

    print(f"g1 = {len(g1)} triples, g2 = {len(g2)} triples")
    print(f"union        (g1 + g2): {len(g1 + g2)} triples")
    print(f"intersection (g1 * g2): {len(g1 * g2)} triples")
    print(f"difference   (g1 - g2): {len(g1 - g2)} triples")
    print(f"xor          (g1 ^ g2): {len(g1 ^ g2)} triples")

    # เทียบ graph สองอันอย่างถูกต้อง (จัดการ blank node ให้)
    g3 = Graph()
    g3.add((EX.B, EX.p, Literal("2")))
    g3.add((EX.A, EX.p, Literal("1")))
    print(f"g1 isomorphic g3? {isomorphic(g1, g3)}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    graph = build_graph()
    add_award_list(graph)

    print("=" * 70)
    print(f"สร้าง graph สำเร็จ: {len(graph)} triples")
    print("=" * 70)
    print(graph.serialize(format="turtle"))

    explore(graph)
    modify(graph)
    graph_algebra()

    # บันทึกลงไฟล์
    graph.serialize(destination="scientists.ttl", format="turtle")
    print("\nบันทึกเป็น scientists.ttl แล้ว")


if __name__ == "__main__":
    main()
