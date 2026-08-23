"""
owl_reasoning.py
----------------
Chapter 08 companion script.

รัน HermiT บน Library ontology จาก library_ontology.py แล้วสาธิต:

  1. Automatic classification -- defined class จัด individual ให้เอง
  2. Property inference       -- inverse, transitive, symmetric
  3. Unsatisfiable class      -- class ที่ไม่มีวันมีสมาชิก
  4. Inconsistency detection  -- 4 กลไกที่ทำให้ KB พัง
  5. ผลของ AllDifferent ต่อ cardinality

Requirements:
    pip install owlready2   (ต้องมี Java 8+)

Usage:
    python owl_reasoning.py
"""

from owlready2 import (
    AllDifferent,
    Not,
    Nothing,
    OwlReadyInconsistentOntologyError,
    Thing,
    World,
    sync_reasoner_hermit,
)

import library_ontology
from library_ontology import onto


def banner(title: str) -> None:
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


def type_names(individual) -> list:
    return sorted(c.name for c in individual.is_a if hasattr(c, "name"))


def prop_values(individual, prop_name: str) -> list:
    values = getattr(individual, prop_name, None)
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    return sorted(v.name if hasattr(v, "name") else str(v) for v in values)


# ---------------------------------------------------------------------------
# 1) snapshot ก่อน reasoning
# ---------------------------------------------------------------------------


def snapshot() -> dict:
    return {ind.name: type_names(ind) for ind in onto.individuals()}


# ---------------------------------------------------------------------------
# main demos
# ---------------------------------------------------------------------------


def demo_classification(before: dict) -> None:
    banner("1) AUTOMATIC CLASSIFICATION — ก่อน vs หลัง reasoning")
    changed = 0
    for ind in onto.individuals():
        old = before.get(ind.name, [])
        new = type_names(ind)
        gained = [t for t in new if t not in old]
        if gained:
            changed += 1
            print(f"  {ind.name:24s} {old}")
            print(f"  {'':24s}  → {new}")
            print(f"  {'':24s}  ← เพิ่ม {gained}")
    if not changed:
        print("  (ไม่มี individual ใดได้ type เพิ่ม)")

    print("\n  Retrieval ของ defined class:")
    for cls_name in ["PublishedAuthor", "ProlificAuthor", "FictionOnlyAuthor",
                     "LoanableBook", "ActiveMember", "HeavyBorrower",
                     "SerialPublication", "CoreGenre", "LongBook"]:
        cls = onto.search_one(iri=f"*{cls_name}")
        if cls is None:
            continue
        members = sorted(i.name for i in cls.instances())
        print(f"    {cls_name:20s} = {members}")


def demo_property_inference() -> None:
    banner("2) PROPERTY INFERENCE")

    orwell = onto.search_one(iri="*georgeOrwell")
    huxley = onto.search_one(iri="*aldousHuxley")
    b1984 = onto.search_one(iri="*nineteenEightyFour")
    shelf = onto.search_one(iri="*shelfA1")

    print("  ▸ inverseOf (wrote ↔ writtenBy)")
    print(f"      orwell.wrote           = {prop_values(orwell, 'wrote')}")
    print(f"      nineteenEightyFour.writtenBy = {prop_values(b1984, 'writtenBy')}")

    print("\n  ▸ SymmetricProperty (coAuthorOf)")
    print(f"      orwell.coAuthorOf      = {prop_values(orwell, 'coAuthorOf')}")
    print(f"      huxley.coAuthorOf      = {prop_values(huxley, 'coAuthorOf')}")

    print("\n  ▸ TransitiveProperty (partOf)")
    print(f"      shelfA1.partOf         = {prop_values(shelf, 'partOf')}")
    print(f"      shelfA1.INDIRECT_partOf = "
          f"{sorted(v.name for v in shelf.INDIRECT_partOf)}")

    alice = onto.search_one(iri="*aliceMember")
    print("\n  ▸ inverseOf (borrowedBy ↔ hasLoan)")
    print(f"      alice.hasLoan          = {prop_values(alice, 'hasLoan')}")


def demo_unsatisfiable() -> None:
    banner("3) UNSATISFIABLE CLASSES")
    unsat = [c for c in onto.classes() if Nothing in c.equivalent_to]
    if unsat:
        for cls in unsat:
            print(f"  ❌ {cls.name} unsatisfiable")
    else:
        print("  ✅ ทุก class satisfiable")

    # สร้าง class ที่ unsatisfiable โดยตั้งใจ
    print("\n  สร้าง class ที่ unsatisfiable โดยตั้งใจ:")
    world = World()
    test = world.get_ontology("http://example.org/test#")
    with test:
        class Item(Thing): pass
        class Digital(Item): pass
        class Physical(Item): pass
        Digital.is_a.append(Not(Physical))

        class DigitalPhysical(Thing):
            equivalent_to = [Digital & Physical]

    with test:
        sync_reasoner_hermit(x=world, debug=0)

    for cls in test.classes():
        if Nothing in cls.equivalent_to:
            print(f"    ❌ {cls.name} ≡ ⊥")
            print("       เพราะ Digital ⊑ ¬Physical แต่ DigitalPhysical ≡ Digital ⊓ Physical")


def demo_inconsistency() -> None:
    banner("4) INCONSISTENCY DETECTION — 4 กลไก")

    cases = [
        (
            "disjointWith",
            "item เป็นทั้ง Book และ Journal",
            lambda o, ns: _case_disjoint(o, ns),
        ),
        (
            "FunctionalProperty + AllDifferent",
            "loan มี borrowedBy 2 คนที่ต่างกัน",
            lambda o, ns: _case_functional(o, ns),
        ),
        (
            "IrreflexiveProperty",
            "author เป็น coAuthorOf ตัวเอง",
            lambda o, ns: _case_irreflexive(o, ns),
        ),
        (
            "AsymmetricProperty",
            "paper A citedBy B และ B citedBy A",
            lambda o, ns: _case_asymmetric(o, ns),
        ),
    ]

    for name, description, builder in cases:
        world = World()
        test = world.get_ontology("http://example.org/test#")
        builder(test, world)
        try:
            with test:
                sync_reasoner_hermit(x=world, debug=0)
            result = "⚠️ consistent (ไม่คาดคิด)"
        except OwlReadyInconsistentOntologyError:
            result = "❌ INCONSISTENT ตามที่คาด"
        print(f"  {result}")
        print(f"     กลไก : {name}")
        print(f"     กรณี : {description}\n")


def _case_disjoint(test, world) -> None:
    with test:
        class Publication(Thing): pass
        class Book(Publication): pass
        class Journal(Publication): pass
        Book.is_a.append(Not(Journal))
        bad = Book("badItem")
        bad.is_a.append(Journal)


def _case_functional(test, world) -> None:
    from owlready2 import FunctionalProperty, ObjectProperty

    with test:
        class Member(Thing): pass
        class Loan(Thing): pass

        # ประกาศเป็น ObjectProperty ธรรมดาก่อน เพื่อให้ใส่ค่าได้ 2 ค่า
        class borrowedBy(ObjectProperty):
            domain, range = [Loan], [Member]

        m1, m2 = Member("alice"), Member("bob")
        AllDifferent([m1, m2])                 # ⚠️ จำเป็น มิฉะนั้น reasoner แค่สรุป sameAs

        loan = Loan("loan1")
        loan.borrowedBy = [m1, m2]             # ใส่ 2 ค่า

        # แล้วค่อยประกาศให้เป็น functional -> ขัดกับ AllDifferent ทันที
        borrowedBy.is_a.append(FunctionalProperty)


def _case_irreflexive(test, world) -> None:
    from owlready2 import IrreflexiveProperty, ObjectProperty, SymmetricProperty

    with test:
        class Author(Thing): pass

        class coAuthorOf(ObjectProperty, SymmetricProperty, IrreflexiveProperty):
            domain, range = [Author], [Author]

        a = Author("selfAuthor")
        a.coAuthorOf = [a]


def _case_asymmetric(test, world) -> None:
    from owlready2 import AsymmetricProperty, ObjectProperty

    with test:
        class Paper(Thing): pass

        class citedBy(ObjectProperty, AsymmetricProperty):
            domain, range = [Paper], [Paper]

        p1, p2 = Paper("paperA"), Paper("paperB")
        p1.citedBy = [p2]
        p2.citedBy = [p1]


def demo_alldifferent_matters() -> None:
    banner("5) ผลของ AllDifferent ต่อ CARDINALITY")

    from owlready2 import ObjectProperty

    for use_all_different in (False, True):
        world = World()
        test = world.get_ontology("http://example.org/test#")
        with test:
            class Author(Thing): pass
            class Publication(Thing): pass

            class wrote(ObjectProperty):
                domain, range = [Author], [Publication]

            class ProlificAuthor(Thing):
                equivalent_to = [Author & wrote.min(3, Publication)]

            author = Author("someAuthor")
            p1, p2, p3 = (Publication(f"pub{i}") for i in range(1, 4))
            author.wrote = [p1, p2, p3]

            if use_all_different:
                AllDifferent([p1, p2, p3])

        with test:
            sync_reasoner_hermit(x=world, debug=0)

        members = sorted(i.name for i in test.ProlificAuthor.instances())
        label = "มี AllDifferent   " if use_all_different else "ไม่มี AllDifferent"
        mark = "✅" if members else "❌"
        print(f"  {mark} {label}: ProlificAuthor = {members}")

    print("\n  สรุป: cardinality ไม่ทำงานเลยถ้าไม่ประกาศ owl:AllDifferent")
    print("        เพราะ OWL ไม่มี Unique Name Assumption")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    before = snapshot()

    banner("รัน HermiT reasoner บน Library ontology")
    try:
        with onto:
            sync_reasoner_hermit(infer_property_values=True, debug=0)
        print("  ✅ ontology consistent")
    except OwlReadyInconsistentOntologyError:
        print("  ❌ ontology inconsistent — หยุดการทำงาน")
        return

    demo_classification(before)
    demo_property_inference()
    demo_unsatisfiable()
    demo_inconsistency()
    demo_alldifferent_matters()


if __name__ == "__main__":
    main()
