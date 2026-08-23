"""สร้าง ontology จาก competency questions ด้วย rdflib แล้วทดสอบ CQ อัตโนมัติ

Workflow:
  1. เขียน CQ พร้อม SPARQL test และผลที่คาดหวัง
  2. สร้าง TBox ด้วย rdflib (conceptualization → formalization)
  3. สร้าง ABox ตัวอย่าง
  4. รัน reasoner (owlrl)
  5. ทดสอบว่า CQ ทุกข้อตอบได้

รัน:  python3 code/ch10/cq_to_sparql.py
"""

from rdflib import Graph, Literal, Namespace, BNode
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

import owlrl

LIB = Namespace("http://example.org/library#")


# ==================== 1. Competency Questions ====================

COMPETENCY_QUESTIONS = [
    {
        "id": "CQ01",
        "text": "Which books were borrowed by a given member?",
        "query": """
            PREFIX lib: <http://example.org/library#>
            SELECT ?book WHERE {
              ?loan lib:borrower lib:alice ; lib:loanedBook ?book .
            }
        """,
        "expect_min": 2,
    },
    {
        "id": "CQ02",
        "text": "Which loans are overdue?",
        "query": """
            PREFIX lib: <http://example.org/library#>
            SELECT ?loan ?due WHERE {
              ?loan a lib:OverdueLoan ; lib:dueDate ?due .
            }
        """,
        "expect_min": 1,
    },
    {
        "id": "CQ03",
        "text": "Who are the frequent borrowers (3 or more loans)?",
        "query": """
            PREFIX lib: <http://example.org/library#>
            SELECT ?member WHERE { ?member a lib:FrequentBorrower }
        """,
        "expect_min": 1,
    },
    {
        "id": "CQ04",
        "text": "What is the ISBN of a given book?",
        "query": """
            PREFIX lib: <http://example.org/library#>
            SELECT ?isbn WHERE { lib:book001 lib:isbn ?isbn }
        """,
        "expect_min": 1,
    },
]


# ==================== 2. TBox ====================

def build_tbox() -> Graph:
    """สร้าง TBox จาก conceptualization -- แต่ละส่วนมาจาก CQ ข้อใดข้อหนึ่ง"""
    g = Graph()
    g.bind("lib", LIB)
    g.bind("owl", OWL)

    onto = LIB[""]
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Library Ontology", lang="en")))

    # ----- classes -----
    for name, label, parent in [
        ("Person",   "Person",   None),
        ("Member",   "Library Member", "Person"),
        ("Book",     "Book",     None),
        ("Loan",     "Loan",     None),
    ]:
        cls = LIB[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(label, lang="en")))
        if parent:
            g.add((cls, RDFS.subClassOf, LIB[parent]))

    g.add((LIB.Loan, RDFS.comment,
           Literal("A time-indexed situation: a member borrowed a book.", lang="en")))
    g.add((LIB.Person, OWL.disjointWith, LIB.Book))
    g.add((LIB.Person, OWL.disjointWith, LIB.Loan))
    g.add((LIB.Book, OWL.disjointWith, LIB.Loan))

    # ----- object properties (CQ01) -----
    for name, label, dom, rng, functional in [
        ("borrower",   "borrower",    "Loan", "Member", True),
        ("loanedBook", "loaned book", "Loan", "Book",   True),
    ]:
        p = LIB[name]
        g.add((p, RDF.type, OWL.ObjectProperty))
        g.add((p, RDFS.label, Literal(label, lang="en")))
        g.add((p, RDFS.domain, LIB[dom]))
        g.add((p, RDFS.range, LIB[rng]))
        if functional:
            g.add((p, RDF.type, OWL.FunctionalProperty))

    # inverse ให้ query จากฝั่ง member ได้ (CQ03)
    g.add((LIB.hasLoan, RDF.type, OWL.ObjectProperty))
    g.add((LIB.hasLoan, RDFS.label, Literal("has loan", lang="en")))
    g.add((LIB.hasLoan, OWL.inverseOf, LIB.borrower))

    # ----- datatype properties (CQ02, CQ04) -----
    for name, label, dom, rng in [
        ("isbn",     "ISBN",     "Book", XSD.string),
        # ⚠️ ใช้ xsd:dateTime ไม่ใช่ xsd:date -- xsd:date ไม่อยู่ใน OWL 2 datatype map
        ("dueDate",  "due date", "Loan", XSD.dateTime),
        ("returned", "returned", "Loan", XSD.boolean),
    ]:
        p = LIB[name]
        g.add((p, RDF.type, OWL.DatatypeProperty))
        g.add((p, RDF.type, OWL.FunctionalProperty))
        g.add((p, RDFS.label, Literal(label, lang="en")))
        g.add((p, RDFS.domain, LIB[dom]))
        g.add((p, RDFS.range, rng))

    # ----- defined class: OverdueLoan (CQ02) -----
    # Loan ⊓ ∃overdueFlag.{true}  -- ใช้ hasValue เพราะ owlrl เทียบวันที่ไม่ได้
    g.add((LIB.overdue, RDF.type, OWL.DatatypeProperty))
    g.add((LIB.overdue, RDFS.label, Literal("overdue", lang="en")))
    g.add((LIB.overdue, RDFS.domain, LIB.Loan))

    overdue_restr = BNode()
    g.add((overdue_restr, RDF.type, OWL.Restriction))
    g.add((overdue_restr, OWL.onProperty, LIB.overdue))
    g.add((overdue_restr, OWL.hasValue, Literal(True)))

    overdue_inter = BNode()
    g.add((overdue_inter, RDF.type, OWL.Class))
    members = BNode()
    Collection(g, members, [LIB.Loan, overdue_restr])
    g.add((overdue_inter, OWL.intersectionOf, members))

    g.add((LIB.OverdueLoan, RDF.type, OWL.Class))
    g.add((LIB.OverdueLoan, RDFS.label, Literal("Overdue Loan", lang="en")))
    g.add((LIB.OverdueLoan, OWL.equivalentClass, overdue_inter))

    # ----- defined class: FrequentBorrower (CQ03) -----
    # Member ⊓ ≥3 hasLoan.Loan
    freq_restr = BNode()
    g.add((freq_restr, RDF.type, OWL.Restriction))
    g.add((freq_restr, OWL.onProperty, LIB.hasLoan))
    g.add((freq_restr, OWL.onClass, LIB.Loan))
    g.add((freq_restr, OWL.minQualifiedCardinality,
           Literal(3, datatype=XSD.nonNegativeInteger)))

    freq_inter = BNode()
    freq_members = BNode()
    Collection(g, freq_members, [LIB.Member, freq_restr])
    g.add((freq_inter, RDF.type, OWL.Class))
    g.add((freq_inter, OWL.intersectionOf, freq_members))

    g.add((LIB.FrequentBorrower, RDF.type, OWL.Class))
    g.add((LIB.FrequentBorrower, RDFS.label, Literal("Frequent Borrower", lang="en")))
    g.add((LIB.FrequentBorrower, OWL.equivalentClass, freq_inter))

    return g


# ==================== 3. ABox ====================

def build_abox() -> Graph:
    """สร้างข้อมูลตัวอย่างที่ครอบคลุมทุก CQ"""
    g = Graph()
    g.bind("lib", LIB)

    for m in ["alice", "bob"]:
        g.add((LIB[m], RDF.type, LIB.Member))
        g.add((LIB[m], RDFS.label, Literal(m.capitalize(), lang="en")))

    books = {
        "book001": ("Semantic Web Primer", "978-0262012423"),
        "book002": ("Foundations of Rule Learning", "978-3540753964"),
        "book003": ("Linked Data Patterns", "978-1105080562"),
    }
    for bid, (title, isbn) in books.items():
        g.add((LIB[bid], RDF.type, LIB.Book))
        g.add((LIB[bid], RDFS.label, Literal(title, lang="en")))
        g.add((LIB[bid], LIB.isbn, Literal(isbn, datatype=XSD.string)))

    loans = [
        ("loan001", "alice", "book001", "2025-01-15T00:00:00", True),
        ("loan002", "alice", "book002", "2025-02-20T00:00:00", False),
        ("loan003", "alice", "book003", "2025-03-10T00:00:00", False),
        ("loan004", "bob",   "book001", "2025-03-25T00:00:00", False),
    ]
    for lid, member, book, due, overdue in loans:
        g.add((LIB[lid], RDF.type, LIB.Loan))
        g.add((LIB[lid], LIB.borrower, LIB[member]))
        g.add((LIB[lid], LIB.loanedBook, LIB[book]))
        g.add((LIB[lid], LIB.dueDate, Literal(due, datatype=XSD.dateTime)))
        g.add((LIB[lid], LIB.overdue, Literal(overdue)))

    # ต้องประกาศ AllDifferent -- ไม่มี UNA! ไม่งั้น ≥3 ไม่ทำงาน
    all_diff = BNode()
    g.add((all_diff, RDF.type, OWL.AllDifferent))
    members_list = BNode()
    Collection(g, members_list, [LIB[f"loan00{i}"] for i in range(1, 5)])
    g.add((all_diff, OWL.distinctMembers, members_list))

    return g


# ==================== 4-5. Reason + test ====================

def test_cqs(g: Graph) -> int:
    print("=" * 68)
    print("  CQ TEST")
    print("=" * 68)
    passed = 0
    for cq in COMPETENCY_QUESTIONS:
        rows = list(g.query(cq["query"]))
        ok = len(rows) >= cq["expect_min"]
        print(f"  {'✅' if ok else '❌'} {cq['id']}: {len(rows)} results "
              f"(expect ≥{cq['expect_min']}) -- {cq['text']}")
        for row in rows[:3]:
            vals = [str(v).split("#")[-1] for v in row]
            print(f"         {vals}")
        passed += ok
    print(f"\n  Coverage: {passed}/{len(COMPETENCY_QUESTIONS)} "
          f"({100 * passed / len(COMPETENCY_QUESTIONS):.0f}%)")
    return passed


def run_hermit(tbox: Graph, abox: Graph) -> None:
    """CQ03 ต้องใช้ minQualifiedCardinality ซึ่ง OWL 2 RL อนุมานไม่ได้
    -- ต้องใช้ reasoner ระดับ OWL 2 DL แทน"""
    try:
        from owlready2 import get_ontology, sync_reasoner
    except ImportError:
        print("  ⏭  ข้าม HermiT (ยังไม่ได้ติดตั้ง owlready2)")
        return

    merged = tbox + abox
    merged.remove((None, OWL.imports, None))     # กัน owlready2 ออกเน็ต
    merged.serialize("/tmp/library.owl", format="xml")

    onto = get_ontology("file:///tmp/library.owl").load()
    with onto:
        sync_reasoner(infer_property_values=True)

    freq = onto.search(type=onto.FrequentBorrower)
    print(f"  HermiT → FrequentBorrower: {[i.name for i in freq]}")
    overdue = onto.search(type=onto.OverdueLoan)
    print(f"  HermiT → OverdueLoan     : {[i.name for i in overdue]}")


def main() -> None:
    tbox = build_tbox()
    abox = build_abox()
    g = tbox + abox
    print(f"  TBox {len(tbox)} + ABox {len(abox)} = {len(g)} triples")

    print("\n  --- ก่อน reasoning ---")
    before = test_cqs(g)

    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    print(f"\n  หลัง reasoning: {len(g)} triples")

    print("\n  --- หลัง reasoning ---")
    after = test_cqs(g)

    print("\n" + "=" * 68)
    if after > before:
        print(f"  🎯 reasoning ทำให้ CQ ผ่านเพิ่ม {after - before} ข้อ")
    print("\n  ⚠️ CQ03 ยังไม่ผ่าน -- minQualifiedCardinality อยู่นอก OWL 2 RL")
    print("     ลองใช้ HermiT (OWL 2 DL) แทน:")
    run_hermit(tbox, abox)

    tbox.serialize("code/ch10/library_tbox.ttl", format="turtle")
    print("\n  ✅ เขียน code/ch10/library_tbox.ttl แล้ว")


if __name__ == "__main__":
    main()
