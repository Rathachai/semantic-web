"""ประเมิน ontology 5 มิติ: consistency, CQ coverage, metrics, verbalization

รัน:  python3 code/ch10/ontology_eval.py
"""

from collections import defaultdict

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

TBOX = "code/ch05/university_tbox.ttl"
DATA = "data/university.ttl"


# ==================== มิติ 3: Structural metrics ====================

def evaluate(path: str) -> dict:
    """วัด structural metric ของ ontology"""
    g = Graph().parse(path, format="turtle")

    classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    obj_props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty)
                 if isinstance(p, URIRef)}
    dt_props = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty)
                if isinstance(p, URIRef)}
    props = obj_props | dt_props
    individuals = {i for i in g.subjects(RDF.type, OWL.NamedIndividual)
                   if isinstance(i, URIRef)}

    # --- hierarchy ---
    parents, children = defaultdict(set), defaultdict(set)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if s in classes and o in classes:
            parents[s].add(o)
            children[o].add(s)

    def depth(c, seen=frozenset()):
        if c in seen or not parents[c]:
            return 1
        return 1 + max(depth(p, seen | {c}) for p in parents[c])

    # ⚠️ คำนวณ branching ก่อน เพราะการอ่าน children[c] จาก defaultdict
    #    จะสร้าง entry ว่างขึ้นมาและทำให้ค่าเฉลี่ยเพี้ยน
    branching = [len(cs) for cs in children.values()]
    avg_branch = sum(branching) / len(branching) if branching else 0

    leaves = [c for c in classes if not children.get(c)]
    avg_depth = sum(depth(c) for c in leaves) / len(leaves) if leaves else 0

    # --- annotation coverage ---
    entities = classes | props
    with_label = {e for e in entities
                  if list(g.objects(e, RDFS.label)) or list(g.objects(e, SKOS.prefLabel))}
    with_comment = {e for e in entities if list(g.objects(e, RDFS.comment))}

    defined = {c for c in classes if list(g.objects(c, OWL.equivalentClass))}

    # --- disjointness ---
    disjoint_pairs = len(list(g.triples((None, OWL.disjointWith, None))))
    for adc in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members = g.value(adc, OWL.members)
        if members:
            n = len(list(g.items(members)))
            disjoint_pairs += n * (n - 1) // 2

    orphans = {c for c in classes
               if not parents.get(c) and not list(g.objects(c, OWL.equivalentClass))}

    return {
        "triples":       len(g),
        "classes":       len(classes),
        "objectProps":   len(obj_props),
        "dataProps":     len(dt_props),
        "individuals":   len(individuals),
        "cls/prop":      round(len(classes) / len(props), 2) if props else 0,
        "avgDepth":      round(avg_depth, 2),
        "avgBranching":  round(avg_branch, 2),
        "labelCov":      round(100 * len(with_label) / len(entities), 1) if entities else 0,
        "commentCov":    round(100 * len(with_comment) / len(entities), 1) if entities else 0,
        "definedPct":    round(100 * len(defined) / len(classes), 1) if classes else 0,
        "disjointPairs": disjoint_pairs,
        "orphanPct":     round(100 * len(orphans) / len(classes), 1) if classes else 0,
    }


RANGES = {
    "cls/prop":     (0.5, 3.0,    "class/property ไม่สมดุล"),
    "avgDepth":     (2.0, 7.0,    "hierarchy ลึกหรือตื้นผิดปกติ"),
    "avgBranching": (2.0, 12.0,   "sibling ต่อ parent ผิดปกติ"),
    "labelCov":     (90.0, 100.0, "entity หลายตัวไม่มี label"),
    "commentCov":   (50.0, 100.0, "entity หลายตัวไม่มี comment"),
    "definedPct":   (5.0, 50.0,   "defined class น้อยหรือมากเกินไป"),
    "orphanPct":    (0.0, 20.0,   "class ลอยไม่มี parent เยอะ"),
}


def report_metrics(path: str) -> None:
    m = evaluate(path)
    print("=" * 66)
    print(f"  METRICS: {path}")
    print("=" * 66)
    for key, val in m.items():
        if key in RANGES:
            lo, hi, msg = RANGES[key]
            ok = lo <= val <= hi
            print(f"  {'✅' if ok else '⚠️ '} {key:15s} {val:>8}"
                  + ("" if ok else f"   ← {msg}"))
        else:
            print(f"     {key:15s} {val:>8}")


# ==================== มิติ 2: CQ coverage ====================

CQ_TESTS = [
    {
        "id": "CQ01",
        "question": "Which students are enrolled in a given course?",
        "query": """
            PREFIX uni: <http://example.org/university#>
            SELECT ?student WHERE { ?student uni:enrolledIn uni:cs501 }
        """,
        "min_results": 1,
    },
    {
        "id": "CQ02",
        "question": "Who supervises which graduate students?",
        "query": """
            PREFIX uni: <http://example.org/university#>
            SELECT ?prof ?student WHERE { ?prof uni:supervises ?student }
        """,
        "min_results": 1,
    },
    {
        "id": "CQ03",
        "question": "What is the grade of a student in a course?",
        "query": """
            PREFIX uni: <http://example.org/university#>
            SELECT ?student ?course ?grade WHERE {
              ?e uni:enrolledStudent ?student ;
                 uni:enrolledCourse  ?course ;
                 uni:hasGrade        ?grade .
            }
        """,
        "min_results": 1,
    },
]


def test_cq_coverage(data_path: str) -> None:
    g = Graph().parse(data_path, format="turtle")
    print("\n" + "=" * 66)
    print("  CQ COVERAGE TEST")
    print("=" * 66)
    passed = 0
    for cq in CQ_TESTS:
        rows = list(g.query(cq["query"]))
        ok = len(rows) >= cq["min_results"]
        print(f"  {'✅' if ok else '❌'} {cq['id']}: {len(rows):3d} results "
              f"-- {cq['question']}")
        passed += ok
    pct = 100 * passed / len(CQ_TESTS)
    print(f"\n  Coverage: {passed}/{len(CQ_TESTS)} ({pct:.0f}%)")
    if pct < 100:
        print("  ⚠️ CQ ที่ตอบไม่ได้ = ontology ยังขาดโครงสร้างหรือขาดข้อมูล")


# ==================== มิติ 4: Verbalization ====================

def verbalize(path: str, limit: int = 8) -> None:
    """แปลง axiom เป็นประโยคอังกฤษให้ domain expert ตรวจ"""
    g = Graph().parse(path, format="turtle")

    def name(t):
        return str(t).split("#")[-1].split("/")[-1]

    print("\n" + "=" * 66)
    print("  VERBALIZATION -- ให้ domain expert ตอบว่า จริง / เท็จ")
    print("=" * 66)

    lines = []
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            lines.append(f"Every {name(s)} is a {name(o)}.")
    for s, _, o in g.triples((None, OWL.disjointWith, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            lines.append(f"Nothing can be both a {name(s)} and a {name(o)}.")
    for p in g.subjects(RDF.type, OWL.FunctionalProperty):
        lines.append(f"Anything has at most one value for '{name(p)}'.")
    for p in g.subjects(RDF.type, OWL.TransitiveProperty):
        n = name(p)
        lines.append(f"If A {n} B and B {n} C, then A {n} C.")
    for s, _, o in g.triples((None, RDFS.domain, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            lines.append(f"Anything that '{name(s)}' something is a {name(o)}.")

    for line in sorted(set(lines))[:limit]:
        print(f"  [ ] {line}")
    print(f"  ... ({len(set(lines))} ประโยคทั้งหมด)")


if __name__ == "__main__":
    report_metrics(TBOX)
    test_cq_coverage(DATA)
    verbalize(TBOX)
