"""
serialize_formats.py
--------------------
Chapter 02 companion script.

แสดง RDF graph เดียวกันในทุก serialization format และพิสูจน์ว่า
round-trip (serialize -> parse) แล้วได้ graph เดิมทุกประการ

Formats: turtle, ntriples, rdf/xml, json-ld, n3, trig, nquads

Requirements:
    pip install rdflib

Usage:
    python serialize_formats.py
    python serialize_formats.py --write-files
"""

import sys
from pathlib import Path

from rdflib import BNode, Dataset, Graph, Literal, Namespace
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF, RDF, RDFS, XSD

EX = Namespace("http://example.org/")

# format -> นามสกุลไฟล์ที่ใช้กันทั่วไป
FORMATS = {
    "turtle": "ttl",
    "nt": "nt",
    "xml": "rdf",
    "json-ld": "jsonld",
    "n3": "n3",
}


def build_sample_graph() -> Graph:
    """สร้าง graph ตัวอย่างที่ครอบคลุม node ทุกชนิด"""
    g = Graph()
    g.bind("ex", EX)
    g.bind("foaf", FOAF)
    g.bind("rdfs", RDFS)

    g.add((EX.MarieCurie, RDF.type, FOAF.Person))
    g.add((EX.MarieCurie, FOAF.name, Literal("Marie Curie")))
    g.add((EX.MarieCurie, RDFS.label, Literal("Marie Curie", lang="en")))
    g.add((EX.MarieCurie, EX.birthDate, Literal("1867-11-07", datatype=XSD.date)))
    g.add((EX.MarieCurie, EX.awardCount, Literal(2)))
    g.add((EX.MarieCurie, FOAF.knows, EX.PierreCurie))

    # blank node เพื่อดูว่าแต่ละ format แสดงอย่างไร
    address = BNode()
    g.add((EX.MarieCurie, EX.hasAddress, address))
    g.add((address, EX.city, Literal("Paris")))
    g.add((address, EX.street, Literal("12 Rue Cuvier")))

    return g


def show_all_formats(g: Graph) -> None:
    """พิมพ์ graph เดียวกันในทุก format"""
    for fmt in FORMATS:
        text = g.serialize(format=fmt)
        print("=" * 72)
        print(f"  FORMAT: {fmt}   ({len(text):,} characters)")
        print("=" * 72)
        print(text)


def verify_round_trip(g: Graph) -> None:
    """serialize -> parse กลับ แล้วเทียบว่าเป็น graph เดียวกัน"""
    print("=" * 72)
    print("  ROUND-TRIP TEST")
    print("=" * 72)
    for fmt in FORMATS:
        text = g.serialize(format=fmt)
        reloaded = Graph()
        reloaded.parse(data=text, format=fmt)
        same = isomorphic(g, reloaded)
        status = "OK " if same else "FAIL"
        print(f"  [{status}] {fmt:<10} {len(g)} -> {len(reloaded)} triples")


def compare_sizes(g: Graph) -> None:
    """เทียบขนาดไฟล์ของแต่ละ format"""
    print("=" * 72)
    print("  SIZE COMPARISON")
    print("=" * 72)
    sizes = {fmt: len(g.serialize(format=fmt)) for fmt in FORMATS}
    smallest = min(sizes.values())
    for fmt, size in sorted(sizes.items(), key=lambda kv: kv[1]):
        ratio = size / smallest
        bar = "#" * int(ratio * 20)
        print(f"  {fmt:<10} {size:>7,} chars  ({ratio:4.2f}x)  {bar}")


def demo_jsonld_context(g: Graph) -> None:
    """JSON-LD แบบ compacted ด้วย @context ที่กำหนดเอง"""
    print("=" * 72)
    print("  JSON-LD with custom @context (compacted form)")
    print("=" * 72)
    context = {
        "ex": "http://example.org/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "name": "foaf:name",
        "knows": {"@id": "foaf:knows", "@type": "@id"},
        "birthDate": {"@id": "ex:birthDate", "@type": "http://www.w3.org/2001/XMLSchema#date"},
    }
    print(g.serialize(format="json-ld", context=context, indent=2))


def demo_named_graph() -> None:
    """TriG / N-Quads ต้องใช้ Dataset ไม่ใช่ Graph ธรรมดา"""
    print("=" * 72)
    print("  NAMED GRAPHS (TriG / N-Quads)")
    print("=" * 72)

    ds = Dataset()
    ds.bind("ex", EX)
    ds.bind("foaf", FOAF)

    wikipedia = ds.graph(EX["graph/wikipedia"])
    wikipedia.add((EX.MarieCurie, FOAF.name, Literal("Marie Curie")))
    wikipedia.add((EX.MarieCurie, EX.birthYear, Literal(1867)))

    archive = ds.graph(EX["graph/old-archive"])
    archive.add((EX.MarieCurie, EX.birthYear, Literal(1868)))

    # metadata อยู่ใน default graph
    ds.default_context.add((EX["graph/wikipedia"], EX.trustScore, Literal(0.9)))
    ds.default_context.add((EX["graph/old-archive"], EX.trustScore, Literal(0.3)))

    print("--- TriG ---")
    print(ds.serialize(format="trig"))
    print("--- N-Quads ---")
    print(ds.serialize(format="nquads"))


def write_files(g: Graph, outdir: Path) -> None:
    """บันทึกทุก format ลงไฟล์"""
    outdir.mkdir(parents=True, exist_ok=True)
    for fmt, ext in FORMATS.items():
        path = outdir / f"scientists.{ext}"
        g.serialize(destination=str(path), format=fmt)
        print(f"  wrote {path}  ({path.stat().st_size:,} bytes)")


def main() -> None:
    graph = build_sample_graph()
    print(f"graph ตัวอย่าง: {len(graph)} triples\n")

    show_all_formats(graph)
    verify_round_trip(graph)
    compare_sizes(graph)
    demo_jsonld_context(graph)
    demo_named_graph()

    if "--write-files" in sys.argv:
        print("=" * 72)
        print("  WRITING FILES")
        print("=" * 72)
        write_files(graph, Path("output"))


if __name__ == "__main__":
    main()
