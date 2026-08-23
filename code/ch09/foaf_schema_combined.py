"""
foaf_schema_combined.py
-----------------------
Chapter 09 companion script.

รวม vocabulary มาตรฐานหลายตัวไว้ใน graph เดียว แล้วสาธิตว่า
การ reuse + alignment ทำให้ query ด้วย vocabulary ใดก็ได้

vocabulary ที่ใช้:
  - FOAF      : คน องค์กร ความสัมพันธ์
  - schema.org: ข้อมูลสำหรับเว็บ
  - Dublin Core: metadata ของเอกสาร
  - SKOS      : หัวข้อ/หมวดหมู่
  - ORG       : โครงสร้างองค์กร
  - PROV-O    : provenance
  - VoID      : dataset description

Requirements:
    pip install rdflib owlrl

Usage:
    python foaf_schema_combined.py
    python foaf_schema_combined.py --jsonld    # export เป็น JSON-LD
"""

import sys
from datetime import datetime, timezone

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import (
    DCTERMS, FOAF, OWL, RDF, RDFS, SDO, SKOS, VOID, XSD,
)

EX = Namespace("http://example.org/")
ORG = Namespace("http://www.w3.org/ns/org#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def banner(title: str) -> None:
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


# ---------------------------------------------------------------------------
# 1) สร้าง graph ที่ใช้หลาย vocabulary
# ---------------------------------------------------------------------------


def build_graph() -> Graph:
    g = Graph()
    for prefix, ns in [
        ("ex", EX), ("foaf", FOAF), ("schema", SDO), ("dcterms", DCTERMS),
        ("skos", SKOS), ("org", ORG), ("prov", PROV), ("void", VOID),
    ]:
        g.bind(prefix, ns)

    # ===== PEOPLE: FOAF + schema.org =====
    alice = EX["person/alice"]
    g.add((alice, RDF.type, FOAF.Person))
    g.add((alice, RDF.type, SDO.Person))          # ประกาศทั้งสอง vocabulary
    # --- FOAF ---
    g.add((alice, FOAF.name, Literal("Alice Johnson")))
    g.add((alice, FOAF.givenName, Literal("Alice")))
    g.add((alice, FOAF.familyName, Literal("Johnson")))
    g.add((alice, FOAF.mbox, URIRef("mailto:alice@example.org")))
    g.add((alice, FOAF.homepage, URIRef("https://alice.example.org/")))
    # --- schema.org ---
    g.add((alice, SDO.jobTitle, Literal("Research Assistant", lang="en")))
    g.add((alice, SDO.birthDate, Literal("1995-04-12", datatype=XSD.date)))
    g.add((alice, SDO.affiliation, EX["org/csDept"]))
    # --- link ภายนอก ---
    g.add((alice, OWL.sameAs, URIRef("https://orcid.org/0000-0002-1825-0097")))
    g.add((alice, SDO.sameAs, URIRef("https://github.com/alicejohnson")))

    bob = EX["person/bob"]
    g.add((bob, RDF.type, FOAF.Person))
    g.add((bob, FOAF.name, Literal("Bob Smith")))
    g.add((bob, FOAF.mbox, URIRef("mailto:bob@example.org")))
    g.add((bob, SDO.jobTitle, Literal("Professor", lang="en")))

    g.add((alice, FOAF.knows, bob))
    g.add((bob, FOAF.knows, alice))

    # ===== ORGANIZATION: FOAF + ORG + schema.org =====
    university = EX["org/university"]
    g.add((university, RDF.type, FOAF.Organization))
    g.add((university, RDF.type, ORG.FormalOrganization))
    g.add((university, RDF.type, SDO.CollegeOrUniversity))
    g.add((university, FOAF.name, Literal("Example University")))
    g.add((university, SDO.url, URIRef("https://www.example.edu/")))
    g.add((university, OWL.sameAs, URIRef("http://www.wikidata.org/entity/Q1234567")))

    cs_dept = EX["org/csDept"]
    g.add((cs_dept, RDF.type, ORG.OrganizationalUnit))
    g.add((cs_dept, RDF.type, FOAF.Organization))
    g.add((cs_dept, FOAF.name, Literal("Department of Computer Science")))
    g.add((cs_dept, ORG.unitOf, university))
    g.add((university, ORG.hasUnit, cs_dept))

    g.add((alice, ORG.memberOf, cs_dept))
    g.add((bob, ORG.memberOf, cs_dept))

    # ===== SKOS: หัวข้อ =====
    scheme = EX["thesaurus"]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, DCTERMS.title, Literal("Research Topics", lang="en")))

    for cid, label, broader in [
        ("computerScience", "Computer Science", None),
        ("semanticWeb", "Semantic Web", "computerScience"),
        ("knowledgeGraphs", "Knowledge Graphs", "semanticWeb"),
    ]:
        concept = EX[f"topic/{cid}"]
        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept, SKOS.inScheme, scheme))
        if broader:
            g.add((concept, SKOS.broader, EX[f"topic/{broader}"]))
            g.add((EX[f"topic/{broader}"], SKOS.narrower, concept))
        else:
            g.add((concept, SKOS.topConceptOf, scheme))
            g.add((scheme, SKOS.hasTopConcept, concept))

    g.add((EX["topic/semanticWeb"], SKOS.altLabel, Literal("Web of Data", lang="en")))
    g.add((EX["topic/semanticWeb"], SKOS.closeMatch,
           URIRef("http://www.wikidata.org/entity/Q54837")))

    # ===== PUBLICATION: Dublin Core + schema.org + SKOS =====
    paper = EX["paper/001"]
    g.add((paper, RDF.type, SDO.ScholarlyArticle))
    g.add((paper, RDF.type, DCTERMS.BibliographicResource))
    # --- Dublin Core ---
    g.add((paper, DCTERMS.title, Literal("Knowledge Graphs in Education", lang="en")))
    g.add((paper, DCTERMS.creator, alice))
    g.add((paper, DCTERMS.contributor, bob))
    g.add((paper, DCTERMS.issued, Literal("2025-03-01", datatype=XSD.date)))
    g.add((paper, DCTERMS.language, Literal("en")))
    g.add((paper, DCTERMS.license,
           URIRef("https://creativecommons.org/licenses/by/4.0/")))
    g.add((paper, DCTERMS.subject, EX["topic/knowledgeGraphs"]))
    # --- schema.org (ทับซ้อนกับ DC โดยตั้งใจ เพื่อสาธิต alignment) ---
    g.add((paper, SDO.name, Literal("Knowledge Graphs in Education", lang="en")))
    g.add((paper, SDO.author, alice))
    g.add((paper, SDO.datePublished, Literal("2025-03-01", datatype=XSD.date)))
    # --- FOAF ---
    g.add((alice, FOAF.made, paper))
    g.add((paper, FOAF.maker, alice))

    return g


# ---------------------------------------------------------------------------
# 2) Alignment axioms
# ---------------------------------------------------------------------------


def build_alignment() -> Graph:
    """
    เชื่อม vocabulary เข้าด้วยกัน

    ⚠️ ใช้ rdfs:subPropertyOf ทางเดียวเป็นหลัก (ปลอดภัยกว่า)
       ใช้ owl:equivalentClass เฉพาะที่พิสูจน์ได้ว่าเหมือนกันจริง
    """
    g = Graph()
    for prefix, ns in [
        ("foaf", FOAF), ("schema", SDO), ("dcterms", DCTERMS),
        ("skos", SKOS), ("org", ORG), ("owl", OWL),
    ]:
        g.bind(prefix, ns)

    # ----- class alignment (equivalent -- พิสูจน์ได้) -----
    g.add((FOAF.Person, OWL.equivalentClass, SDO.Person))
    g.add((FOAF.Organization, OWL.equivalentClass, SDO.Organization))

    # ----- class alignment (subClassOf -- ปลอดภัยกว่า) -----
    g.add((SDO.CollegeOrUniversity, RDFS.subClassOf, SDO.Organization))
    g.add((ORG.FormalOrganization, RDFS.subClassOf, FOAF.Organization))
    g.add((ORG.OrganizationalUnit, RDFS.subClassOf, FOAF.Organization))

    # ----- property alignment -----
    g.add((FOAF.name, OWL.equivalentProperty, SDO.name))
    g.add((FOAF.name, RDFS.subPropertyOf, RDFS.label))
    g.add((FOAF.givenName, OWL.equivalentProperty, SDO.givenName))
    g.add((FOAF.familyName, OWL.equivalentProperty, SDO.familyName))
    g.add((FOAF.homepage, RDFS.subPropertyOf, SDO.url))
    g.add((FOAF.knows, OWL.equivalentProperty, SDO.knows))

    g.add((SDO.author, RDFS.subPropertyOf, DCTERMS.creator))
    g.add((SDO.name, RDFS.subPropertyOf, DCTERMS.title))
    g.add((SDO.datePublished, RDFS.subPropertyOf, DCTERMS.issued))
    g.add((SDO.dateModified, RDFS.subPropertyOf, DCTERMS.modified))
    g.add((SDO.license, RDFS.subPropertyOf, DCTERMS.license))
    g.add((SDO.about, RDFS.subPropertyOf, DCTERMS.subject))

    g.add((ORG.memberOf, RDFS.subPropertyOf, SDO.affiliation))
    g.add((DCTERMS.creator, RDFS.subPropertyOf, DCTERMS.contributor))

    # ----- ⚠️ ไม่ align: foaf:mbox กับ schema:email -----
    # range ต่างกัน (IRI vs string) จึงใช้ seeAlso แทน
    g.add((FOAF.mbox, RDFS.seeAlso, SDO.email))

    return g


# ---------------------------------------------------------------------------
# 3) Query -- พิสูจน์ว่า alignment ทำงาน
# ---------------------------------------------------------------------------

PREFIXES = """
PREFIX ex:      <http://example.org/>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX schema:  <https://schema.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX org:     <http://www.w3.org/ns/org#>
"""

QUERIES = {
    "หาคนด้วย foaf:Person": """
        SELECT ?p WHERE { ?p a foaf:Person }
    """,
    "หาคนด้วย schema:Person (ต้อง align)": """
        SELECT ?p WHERE { ?p a schema:Person }
    """,
    "หาชื่อด้วย rdfs:label (ผ่าน foaf:name)": """
        SELECT ?p ?label WHERE { ?p rdfs:label ?label }
    """,
    "หาผู้แต่งด้วย dcterms:creator (ผ่าน schema:author)": """
        SELECT ?doc ?creator WHERE { ?doc dcterms:creator ?creator }
    """,
    "หาชื่อเอกสารด้วย dcterms:title (ผ่าน schema:name)": """
        SELECT ?doc ?title WHERE { ?doc dcterms:title ?title }
    """,
    # ⚠️ IRI ที่มี "/" ใน local name ใช้เป็น prefixed name ไม่ได้
    #    ต้องเขียนเป็น IRI เต็มใน < > หรือ escape ด้วย \/
    "หัวข้อทั้งหมดที่กว้างกว่า knowledgeGraphs": """
        SELECT ?topic ?label WHERE {
          <http://example.org/topic/knowledgeGraphs> skos:broader+ ?topic .
          ?topic skos:prefLabel ?label .
        }
    """,
    "องค์กรที่ alice สังกัด (ทุกระดับ)": """
        SELECT ?orgName WHERE {
          <http://example.org/person/alice> org:memberOf/org:unitOf* ?o .
          ?o foaf:name ?orgName .
        }
    """,
    "link ภายนอกทั้งหมด": """
        SELECT ?s ?external WHERE {
          { ?s owl:sameAs ?external } UNION { ?s schema:sameAs ?external }
        }
    """,
}


def run_queries(g: Graph, header: str) -> None:
    banner(header)
    for title, query in QUERIES.items():
        rows = list(g.query(PREFIXES + query))
        values = sorted({
            str(cell).split("/")[-1].split("#")[-1]
            for row in rows for cell in row if cell
        })
        print(f"  ▸ {title}")
        print(f"      {len(rows)} แถว: {values[:6]}{' ...' if len(values) > 6 else ''}")


# ---------------------------------------------------------------------------
# 4) วิเคราะห์การ reuse
# ---------------------------------------------------------------------------

WELL_KNOWN = {
    "http://xmlns.com/foaf/0.1/": "FOAF",
    "http://purl.org/dc/terms/": "Dublin Core",
    "https://schema.org/": "schema.org",
    "http://www.w3.org/2004/02/skos/core#": "SKOS",
    "http://www.w3.org/ns/org#": "ORG",
    "http://www.w3.org/ns/prov#": "PROV-O",
    "http://www.w3.org/2002/07/owl#": "OWL",
    "http://www.w3.org/2000/01/rdf-schema#": "RDFS",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "RDF",
}


def analyse_reuse(g: Graph) -> None:
    banner("การใช้ VOCABULARY")
    counts: dict = {}
    own = 0
    for _, p, _ in g:
        matched = False
        for ns, name in WELL_KNOWN.items():
            if str(p).startswith(ns):
                counts[name] = counts.get(name, 0) + 1
                matched = True
                break
        if not matched:
            own += 1

    total = sum(counts.values()) + own
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "#" * int(count / total * 40)
        print(f"  {name:16s} {count:>4}  {bar}")
    print(f"  {'(ของเราเอง)':16s} {own:>4}")
    print(f"\n  reuse ratio: {sum(counts.values()) / total:.0%}")


# ---------------------------------------------------------------------------
# 5) Export JSON-LD
# ---------------------------------------------------------------------------


def export_jsonld(g: Graph) -> str:
    context = {
        "ex": "http://example.org/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "org": "http://www.w3.org/ns/org#",
        "name": "foaf:name",
        "knows": {"@id": "foaf:knows", "@type": "@id"},
        "title": "dcterms:title",
        "creator": {"@id": "dcterms:creator", "@type": "@id"},
        "sameAs": {"@id": "http://www.w3.org/2002/07/owl#sameAs", "@type": "@id"},
    }
    return g.serialize(format="json-ld", context=context, indent=2)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    data = build_graph()
    print(f"สร้าง graph: {len(data)} triples")

    run_queries(data, "ก่อน ALIGNMENT")

    alignment = build_alignment()
    print(f"\nalignment axioms: {len(alignment)} triples")

    combined = data + alignment

    try:
        import owlrl
        before = len(combined)
        owlrl.DeductiveClosure(owlrl.RDFS_OWLRL_Semantics).expand(combined)
        print(f"หลัง reasoning: {len(combined)} triples (+{len(combined) - before})")
    except ImportError:
        print("⚠️ ไม่ได้ติดตั้ง owlrl — ข้าม reasoning")

    run_queries(combined, "หลัง ALIGNMENT + REASONING")
    analyse_reuse(data)

    if "--jsonld" in sys.argv:
        banner("JSON-LD EXPORT")
        print(export_jsonld(data)[:2000])
    else:
        banner("TURTLE (ตัวอย่าง)")
        sample = Graph()
        for prefix, ns in data.namespaces():
            sample.bind(prefix, ns)
        alice = URIRef("http://example.org/person/alice")
        for triple in data.triples((alice, None, None)):
            sample.add(triple)
        print(sample.serialize(format="turtle"))


if __name__ == "__main__":
    main()
