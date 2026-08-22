"""
rdfs_reasoning.py
-----------------
Chapter 03 companion script.

รัน RDFS reasoning ด้วย owlrl บน schema จาก rdfs_schema.py แล้ว:
  1. เทียบ asserted vs inferred
  2. แสดง triple ที่อนุมานได้ พร้อมบอกว่ามาจากกฎข้อไหน
  3. กรอง axiomatic noise ออก
  4. query ก่อนและหลัง reasoning เพื่อให้เห็นความต่าง
  5. แยก inferred ไว้ใน named graph

Requirements:
    pip install rdflib owlrl

Usage:
    python rdfs_reasoning.py
"""

from typing import Iterable, Set, Tuple

import owlrl
from rdflib import Dataset, Graph, URIRef
from rdflib.namespace import RDF, RDFS

from rdfs_schema import EX, build_graph

Triple = Tuple

# node เหล่านี้ปรากฏใน triple พื้นฐานที่ RDFS สร้างมหาศาลแต่ไม่มีค่าเชิงข้อมูล
NOISE_OBJECTS = {RDFS.Resource, RDFS.Literal, RDFS.Class, RDF.Property}


# ---------------------------------------------------------------------------
# 1) reasoning
# ---------------------------------------------------------------------------


def run_rdfs_closure(g: Graph) -> Set[Triple]:
    """รัน RDFS deductive closure แบบ in-place แล้วคืนเซตของ triple ที่เพิ่มมา"""
    asserted = set(g)
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(g)
    return set(g) - asserted


# ---------------------------------------------------------------------------
# 2) กรอง noise
# ---------------------------------------------------------------------------


def is_useful(triple: Triple) -> bool:
    """คัดเฉพาะ inferred triple ที่มีความหมายเชิงข้อมูลจริง"""
    s, p, o = triple
    if o in NOISE_OBJECTS:
        return False
    # reflexive subClassOf / subPropertyOf ที่กฎ rdfs10/rdfs6 สร้าง
    if p in (RDFS.subClassOf, RDFS.subPropertyOf) and s == o:
        return False
    # สนใจเฉพาะ term ใน namespace ของเรา
    return str(s).startswith(str(EX))


def explain(triple: Triple) -> str:
    """เดาว่า triple นี้น่าจะมาจากกฎข้อไหน (แบบง่าย เพื่อการเรียนรู้)"""
    _, p, _ = triple
    if p == RDF.type:
        return "rdfs2/rdfs3 (domain/range) หรือ rdfs9 (subClassOf)"
    if p == RDFS.subClassOf:
        return "rdfs11 (subClassOf transitivity)"
    if p == RDFS.subPropertyOf:
        return "rdfs5 (subPropertyOf transitivity)"
    return "rdfs7 (subPropertyOf propagation)"


# ---------------------------------------------------------------------------
# 3) query ก่อน/หลัง
# ---------------------------------------------------------------------------

QUERIES = {
    "ทุกคนที่เป็น ex:Person": """
        PREFIX ex: <http://example.org/university#>
        SELECT ?p WHERE { ?p a ex:Person . }
    """,
    "ทุกอย่างที่เป็น ex:Course": """
        PREFIX ex: <http://example.org/university#>
        SELECT ?c WHERE { ?c a ex:Course . }
    """,
    "ทุกคนที่ ex:involvedIn cs101": """
        PREFIX ex: <http://example.org/university#>
        SELECT ?p WHERE { ?p ex:involvedIn ex:cs101 . }
    """,
}


def run_queries(g: Graph, header: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {header}")
    print("=" * 70)
    for title, query in QUERIES.items():
        rows = list(g.query(query))
        names = sorted(str(r[0]).split("#")[-1] for r in rows)
        print(f"  {title}")
        print(f"    -> {len(names)} ผลลัพธ์: {names or '(ไม่มี)'}")


# ---------------------------------------------------------------------------
# 4) แยก inferred ไปไว้ใน named graph
# ---------------------------------------------------------------------------


def split_into_named_graphs(asserted: Iterable[Triple],
                            inferred: Iterable[Triple]) -> Dataset:
    """สร้าง Dataset ที่แยก asserted / inferred เป็นคนละ named graph"""
    ds = Dataset()
    ds.bind("ex", EX)

    g_asserted = ds.graph(URIRef("http://example.org/graph/asserted"))
    g_inferred = ds.graph(URIRef("http://example.org/graph/inferred"))

    for t in asserted:
        g_asserted.add(t)
    for t in inferred:
        g_inferred.add(t)

    return ds


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    graph = build_graph()
    asserted = set(graph)

    run_queries(graph, "ก่อน REASONING")

    inferred = run_rdfs_closure(graph)

    run_queries(graph, "หลัง REASONING")

    print(f"\n{'=' * 70}")
    print("  สถิติ")
    print("=" * 70)
    print(f"  asserted : {len(asserted):>4} triples")
    print(f"  inferred : {len(inferred):>4} triples")
    print(f"  total    : {len(graph):>4} triples")

    useful = sorted(t for t in inferred if is_useful(t))
    print(f"  inferred ที่มีความหมายจริง : {len(useful)} triples")

    print(f"\n{'=' * 70}")
    print("  INFERRED TRIPLES (กรอง noise แล้ว)")
    print("=" * 70)
    nsm = graph.namespace_manager
    for triple in useful:
        s, p, o = triple
        print(f"  {s.n3(nsm):<28} {p.n3(nsm):<20} {o.n3(nsm):<28}  # {explain(triple)}")

    dataset = split_into_named_graphs(asserted, inferred)
    print(f"\n  แยกเป็น named graph แล้ว: "
          f"{len(list(dataset.contexts()))} contexts")


if __name__ == "__main__":
    main()
