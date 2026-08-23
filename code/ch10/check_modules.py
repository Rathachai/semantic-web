"""ตรวจสอบ modularization: dependency, cycle และการใช้ term ข้าม module

รัน:  python3 code/ch10/check_modules.py
"""

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF


def check_modules(files: dict) -> None:
    """ตรวจ dependency, cycle และการรั่วของ namespace ระหว่าง module"""
    graphs = {name: Graph().parse(p, format="turtle") for name, p in files.items()}

    print("=" * 66)
    print("  MODULE CHECK")
    print("=" * 66)

    # --- 1) dependency graph ---
    deps, iri_of, ns_of = {}, {}, {}
    for name, g in graphs.items():
        onto = next(g.subjects(RDF.type, OWL.Ontology))
        iri_of[str(onto)] = name
        ns_of[name] = str(onto) + "#"
        deps[name] = [str(o) for o in g.objects(onto, OWL.imports)]

    print("\n  Dependencies:")
    for name, imports in deps.items():
        names = [iri_of.get(i, i) for i in imports]
        print(f"    {name:12s} → {names or '(none)'}")

    # --- 2) หา cycle ---
    def has_cycle(node, stack=()):
        if node in stack:
            return stack[stack.index(node):] + (node,)
        for dep in deps.get(node, []):
            dep_name = iri_of.get(dep)
            if dep_name:
                found = has_cycle(dep_name, stack + (node,))
                if found:
                    return found
        return None

    print("\n  Cycle check:")
    cycles = {c for n in deps if (c := has_cycle(n))}
    if cycles:
        for c in cycles:
            print(f"    ❌ cycle: {' → '.join(c)}")
    else:
        print("    ✅ ไม่มี cycle (เป็น DAG)")

    # --- 3) term ที่ใช้ข้าม module โดยไม่ import ---
    print("\n  Undeclared cross-module usage:")
    problems = 0
    for name, g in graphs.items():
        allowed = {ns_of[name]}
        for dep in deps[name]:
            if (dep_name := iri_of.get(dep)):
                allowed.add(ns_of[dep_name])
        for triple in g:
            for term in triple:
                if not isinstance(term, URIRef):
                    continue
                for other, other_ns in ns_of.items():
                    if (other != name and str(term).startswith(other_ns)
                            and other_ns not in allowed):
                        print(f"    ❌ {name} ใช้ {str(term).split('#')[-1]} "
                              f"จาก {other} แต่ไม่ได้ import")
                        problems += 1
    if problems == 0:
        print("    ✅ ไม่พบ")


if __name__ == "__main__":
    check_modules({
        "core":     "ontology/uni-core.ttl",
        "academic": "ontology/uni-academic.ttl",
        "hr":       "ontology/uni-hr.ttl",
        "library":  "ontology/uni-library.ttl",
    })
