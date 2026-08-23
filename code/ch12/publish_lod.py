"""เตรียมชุดข้อมูลให้พร้อมเผยแพร่เป็น 5-star Linked Open Data

สิ่งที่สคริปต์นี้ทำ
------------------
1. ตรวจสุขภาพชุดข้อมูล (URI, label, สัญญาอนุญาต, ลิงก์ออก)
2. สร้าง VoID description อัตโนมัติจากสถิติจริงของกราฟ
3. สร้าง DCAT catalog entry
4. ส่งออกหลายรูปแบบ (Turtle, N-Triples, JSON-LD, RDF/XML)

รัน:  python3 code/ch12/publish_lod.py
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import date

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "lod_dataset.ttl")
OUT = os.path.join(HERE, "dist")

VOID = Namespace("http://rdfs.org/ns/void#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")

BASE = "https://data.example.org/"
DATASET = URIRef(BASE + "dataset/universities")
CATALOG = URIRef(BASE + "catalog")
PUBLISHER = URIRef(BASE + "org/example")
LICENSE = URIRef("https://creativecommons.org/licenses/by/4.0/")
SPARQL_EP = URIRef(BASE + "sparql")

# dataset ปลายทางที่เรารู้จัก -- ใช้จัดกลุ่ม owl:sameAs
KNOWN_TARGETS = {
    "www.wikidata.org": ("Wikidata", "https://query.wikidata.org/sparql"),
    "dbpedia.org": ("DBpedia", "https://dbpedia.org/sparql"),
    "sws.geonames.org": ("GeoNames", None),
}


# predicate ที่นับว่าเป็น "ลิงก์ออก" ตามนิยามของ VoID
LINK_PREDICATES = [OWL.sameAs, SKOS.exactMatch, SKOS.closeMatch, RDFS.seeAlso]


def head(title: str) -> None:
    print(f"\n{'=' * 68}\n  {title}\n{'=' * 68}")


def link_triples(g: Graph) -> list[tuple]:
    """คืน triple ที่ชี้ออกไปนอก namespace ของเรา"""
    out = []
    for pred in LINK_PREDICATES:
        for s, p, o in g.triples((None, pred, None)):
            if isinstance(o, URIRef) and not str(o).startswith(BASE):
                out.append((s, p, o))
    return out


# ================================================== 1. health check
def health_check(g: Graph) -> None:
    head("1. ตรวจสุขภาพชุดข้อมูล")

    subjects = set(g.subjects())
    named = {s for s in subjects if isinstance(s, URIRef)}
    blanks = subjects - named
    print(f"  triples ทั้งหมด        : {len(g)}")
    print(f"  subject ที่มี URI      : {len(named)}")
    print(f"  blank node ที่เป็น subject : {len(blanks)}"
          f"  {'✅' if not blanks else '⚠️ ควรให้ URI'}")

    # label coverage -- นับเฉพาะ subject ที่อยู่ใน namespace ของเรา
    ours = {s for s in named if str(s).startswith(BASE)}
    labelled = {s for s in ours
                if (s, RDFS.label, None) in g or (s, SKOS.prefLabel, None) in g}
    pct = 100 * len(labelled) / len(ours) if ours else 0
    print(f"  entity ของเรา          : {len(ours)}")
    print(f"  มี label               : {len(labelled)} ({pct:.0f}%)"
          f"  {'✅' if pct == 100 else '⚠️'}")

    # multilingual coverage
    langs = Counter(o.language for _, _, o in g.triples((None, RDFS.label, None))
                    if isinstance(o, Literal) and o.language)
    print(f"  ภาษาของ label          : {dict(langs)}")

    # outgoing links
    out_links = link_triples(g)
    hosts = Counter(str(o).split("/")[2] for _, _, o in out_links if "//" in str(o))
    preds = Counter(p.split("#")[-1] for _, p, _ in out_links)
    print(f"  ลิงก์ออกทั้งหมด        : {len(out_links)}  {dict(preds)}")
    for host, n in hosts.most_common():
        name = KNOWN_TARGETS.get(host, (host, None))[0]
        print(f"      {n:>3}  {name}")

    print(f"\n  ⭐ ระดับดาวที่ประเมินได้ : "
          f"{'⭐⭐⭐⭐⭐' if out_links else '⭐⭐⭐⭐'}")


# ================================================== 2. VoID
def build_void(g: Graph) -> Graph:
    head("2. สร้าง VoID description จากสถิติจริง")

    v = Graph()
    for p, ns in [("void", VOID), ("dcterms", DCTERMS), ("foaf", FOAF),
                  ("rdf", RDF), ("rdfs", RDFS)]:
        v.bind(p, ns)

    classes = {o for _, _, o in g.triples((None, RDF.type, None))}
    props = {p for _, p, _ in g}
    entities = {s for s in g.subjects(RDF.type, None) if isinstance(s, URIRef)}

    v.add((DATASET, RDF.type, VOID.Dataset))
    v.add((DATASET, DCTERMS.title, Literal("Thai Universities Linked Data", lang="en")))
    v.add((DATASET, DCTERMS.description, Literal(
        "Universities, campuses, cities and fields of study in Thailand, "
        "linked to Wikidata, DBpedia and GeoNames.", lang="en")))
    v.add((DATASET, DCTERMS.publisher, PUBLISHER))
    v.add((DATASET, DCTERMS.license, LICENSE))
    v.add((DATASET, DCTERMS.modified, Literal(date(2026, 1, 15), datatype=XSD.date)))
    v.add((DATASET, VOID.sparqlEndpoint, SPARQL_EP))
    v.add((DATASET, VOID.dataDump, URIRef(BASE + "dump/universities.ttl")))
    v.add((DATASET, VOID.uriSpace, Literal(BASE)))
    v.add((DATASET, VOID.feature, URIRef("http://www.w3.org/ns/formats/Turtle")))

    v.add((DATASET, VOID.triples, Literal(len(g), datatype=XSD.integer)))
    v.add((DATASET, VOID.entities, Literal(len(entities), datatype=XSD.integer)))
    v.add((DATASET, VOID.classes, Literal(len(classes), datatype=XSD.integer)))
    v.add((DATASET, VOID.properties, Literal(len(props), datatype=XSD.integer)))
    v.add((DATASET, VOID.distinctSubjects,
           Literal(len(set(g.subjects())), datatype=XSD.integer)))
    v.add((DATASET, VOID.distinctObjects,
           Literal(len(set(g.objects())), datatype=XSD.integer)))

    # linkset: หนึ่งก้อนต่อคู่ (dataset ปลายทาง, predicate)
    #   VoID กำหนดให้ linkset หนึ่งก้อนมี linkPredicate เดียว
    #   จึงต้องแยกตาม predicate ด้วย ไม่ใช่แยกตามปลายทางอย่างเดียว
    buckets: Counter = Counter()
    for _, p, o in link_triples(g):
        buckets[(str(o).split("/")[2], p)] += 1

    for (host, pred), n in sorted(buckets.items(), key=lambda x: -x[1]):
        name = KNOWN_TARGETS.get(host, (host, None))[0]
        short = pred.split("#")[-1]
        ls = URIRef(f"{BASE}linkset/{name.lower()}-{short.lower()}")
        v.add((ls, RDF.type, VOID.Linkset))
        v.add((ls, VOID.subjectsTarget, DATASET))
        v.add((ls, VOID.linkPredicate, pred))
        v.add((ls, VOID.triples, Literal(n, datatype=XSD.integer)))
        v.add((ls, DCTERMS.title, Literal(f"{short} links to {name}", lang="en")))
        v.add((DATASET, VOID.subset, ls))
        print(f"  linkset → {name:10s} {short:12s} {n} links")

    print(f"\n  VoID graph : {len(v)} triples")
    return v


# ================================================== 3. DCAT
def build_dcat() -> Graph:
    head("3. สร้าง DCAT catalog entry")

    d = Graph()
    for p, ns in [("dcat", DCAT), ("dcterms", DCTERMS), ("foaf", FOAF)]:
        d.bind(p, ns)

    d.add((CATALOG, RDF.type, DCAT.Catalog))
    d.add((CATALOG, DCTERMS.title, Literal("Example Open Data Catalog", lang="en")))
    d.add((CATALOG, DCAT.dataset, DATASET))

    d.add((DATASET, RDF.type, DCAT.Dataset))
    d.add((DATASET, DCTERMS.title, Literal("Thai Universities Linked Data", lang="en")))
    d.add((DATASET, DCTERMS.license, LICENSE))
    d.add((DATASET, DCTERMS.publisher, PUBLISHER))
    d.add((DATASET, DCTERMS.accrualPeriodicity,
           URIRef("http://publications.europa.eu/resource/authority/frequency/ANNUAL")))

    # หนึ่ง distribution ต่อหนึ่งรูปแบบไฟล์
    for ext, media in [("ttl", "text/turtle"), ("nt", "application/n-triples"),
                       ("jsonld", "application/ld+json"),
                       ("rdf", "application/rdf+xml")]:
        dist = URIRef(f"{BASE}dataset/universities/{ext}")
        d.add((DATASET, DCAT.distribution, dist))
        d.add((dist, RDF.type, DCAT.Distribution))
        d.add((dist, DCAT.mediaType, Literal(media)))
        d.add((dist, DCAT.downloadURL,
               URIRef(f"{BASE}dump/universities.{ext}")))
        d.add((dist, DCTERMS.license, LICENSE))
        print(f"  distribution : {ext:7s} {media}")

    ep = URIRef(f"{BASE}dataset/universities/sparql")
    d.add((DATASET, DCAT.distribution, ep))
    d.add((ep, RDF.type, DCAT.Distribution))
    d.add((ep, DCAT.accessURL, SPARQL_EP))
    d.add((ep, DCAT.mediaType, Literal("application/sparql-results+json")))
    print(f"  distribution : sparql  {SPARQL_EP}")

    print(f"\n  DCAT graph : {len(d)} triples")
    return d


# ================================================== 4. export
def export_all(g: Graph, void_g: Graph, dcat_g: Graph) -> None:
    head("4. ส่งออกไฟล์สำหรับเผยแพร่")
    os.makedirs(OUT, exist_ok=True)

    formats = [("ttl", "turtle"), ("nt", "nt"),
               ("jsonld", "json-ld"), ("rdf", "xml")]
    for ext, fmt in formats:
        path = os.path.join(OUT, f"universities.{ext}")
        g.serialize(path, format=fmt, encoding="utf-8")
        print(f"  universities.{ext:<7s} {os.path.getsize(path):>7,} bytes")

    for name, graph in [("void.ttl", void_g), ("catalog.ttl", dcat_g)]:
        path = os.path.join(OUT, name)
        graph.serialize(path, format="turtle")
        print(f"  {name:<20s} {os.path.getsize(path):>7,} bytes")

    print(f"\n  📁 ทั้งหมดอยู่ใน {os.path.relpath(OUT, ROOT)}/")


if __name__ == "__main__":
    print("=" * 68)
    print("  เตรียมชุดข้อมูลให้พร้อมเผยแพร่เป็น 5-star LOD")
    print("=" * 68)

    graph = Graph()
    graph.parse(DATA, format="turtle")

    health_check(graph)
    void_graph = build_void(graph)
    dcat_graph = build_dcat()
    export_all(graph, void_graph, dcat_graph)
    print()
