"""SWRL ทำงานร่วมกับ OWL -- 5 กรณีศึกษา

แสดงให้เห็นว่า reasoner ประมวลผล OWL axiom กับ SWRL rule "พร้อมกัน"
ไม่ใช่แยกเฟส  ผลของฝ่ายหนึ่งจึงป้อนกลับให้อีกฝ่ายได้จนถึง fixpoint

รัน:  python3 code/ch11/swrl_owl_loop.py

หมายเหตุ
--------
* กรณีที่มี swrlb: builtin ต้องใช้ Pellet (HermiT ไม่รองรับ builtin)
* ทุกกรณีใช้ World() ของตัวเอง มิฉะนั้นตัวแปร SWRL ชื่อซ้ำจะถูก reuse
  ข้าม ontology แล้วกฎจะเงียบ ๆ ไม่ทำงาน
"""

from __future__ import annotations

import os
import sys

from owlready2 import (DataProperty, FunctionalProperty, Imp, ObjectProperty,
                       OwlReadyInconsistentOntologyError, SymmetricProperty,
                       Thing, TransitiveProperty, World, sync_reasoner_hermit)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pellet_runner import parse_realization, run_pellet  # noqa: E402


def head(n: int, title: str) -> None:
    print(f"\n{'=' * 66}\n  [กรณี {n}] {title}\n{'=' * 66}")


def names(individuals) -> list[str]:
    return sorted(i.name for i in individuals)


# ---------------------------------------------------------------- กรณี 1
def case1_owl_feeds_swrl() -> None:
    """rdfs:domain สร้าง type ให้ก่อน แล้ว class atom ของ rule จึงจับได้"""
    head(1, "OWL → SWRL")
    onto = World().get_ontology("http://example.org/med#")
    with onto:
        class Patient(Thing):
            pass

        class ElderlyPatient(Patient):
            pass

        class hasDiagnosis(ObjectProperty):
            domain = [Patient]          # ⬅️ OWL จะอนุมาน type ให้

        class hasAge(DataProperty, FunctionalProperty):
            range = [int]

        r = Imp()
        r.set_as_rule("Patient(?p), hasAge(?p, ?a), greaterThan(?a, 65) "
                      "-> ElderlyPatient(?p)")

        john = Thing("john")            # ไม่ได้ประกาศเป็น Patient
        diabetes = Thing("diabetes")
        john.hasDiagnosis = [diabetes]
        john.hasAge = 72

    realized = parse_realization(run_pellet(onto))
    print(f"  Patient        : {realized.get('Patient', [])}")
    print(f"  ElderlyPatient : {realized.get('ElderlyPatient', [])}")
    print("  ⚠️ Pellet realize รายงานเฉพาะ class ที่เจาะจงที่สุด")
    print("     john อยู่ใต้ ElderlyPatient ⊑ Patient จึงเป็น Patient ด้วย")
    print("     → rule ทำงานได้ก็เพราะ rdfs:domain อนุมาน Patient(john) ให้ก่อน")


# ---------------------------------------------------------------- กรณี 2
def case2_swrl_feeds_owl() -> None:
    """rule สร้าง property assertion แล้ว OWL ไล่ transitive ต่อ"""
    head(2, "SWRL → OWL")
    onto = World().get_ontology("http://example.org/fam#")
    with onto:
        class Person(Thing):
            pass

        class hasParent(ObjectProperty):
            domain, range = [Person], [Person]

        class hasAncestor(ObjectProperty, TransitiveProperty):
            domain, range = [Person], [Person]

        r = Imp()
        r.set_as_rule("hasParent(?x, ?y) -> hasAncestor(?x, ?y)")

        john, mary, susan = Person("john"), Person("mary"), Person("susan")
        john.hasParent = [mary]
        mary.hasParent = [susan]

    sync_reasoner_hermit(onto.world, infer_property_values=True, debug=0)
    print(f"  john hasAncestor : {names(john.hasAncestor)}")
    print("  ⬅️ john→susan ไม่มีกฎไหนสร้าง เกิดจาก owl:TransitiveProperty")


# ---------------------------------------------------------------- กรณี 3
def case3_round_trip() -> None:
    """SWRL → OWL → SWRL วนกลับไปกลับมาในรอบเดียว"""
    head(3, "วนกลับไปกลับมา")
    onto = World().get_ontology("http://example.org/uni#")
    with onto:
        class Person(Thing):
            pass

        class Colleague(Person):
            pass

        class hasAdvisor(ObjectProperty):
            domain, range = [Person], [Person]

        class knows(ObjectProperty, SymmetricProperty):
            domain, range = [Person], [Person]

        r1 = Imp()
        r1.set_as_rule("hasAdvisor(?x, ?y) -> knows(?x, ?y)")
        r2 = Imp()
        r2.set_as_rule("knows(?x, ?y) -> Colleague(?x)")

        alice, prof1 = Person("alice"), Person("prof1")
        alice.hasAdvisor = [prof1]

    sync_reasoner_hermit(onto.world, infer_property_values=True, debug=0)
    print(f"  alice knows : {names(alice.knows)}")
    print(f"  prof1 knows : {names(prof1.knows)}    ⬅️ OWL SymmetricProperty")
    print(f"  Colleague   : {names(onto.Colleague.instances())}")


# ---------------------------------------------------------------- กรณี 4
def case4_dl_safe() -> None:
    """SWRL ทำงานกับ named individual เท่านั้น"""
    head(4, "DL-safe")

    def build(with_named_child: bool):
        onto = World().get_ontology("http://example.org/dls#")
        with onto:
            class Person(Thing):
                pass

            class HasDescendant(Person):
                pass

            class hasChild(ObjectProperty):
                domain, range = [Person], [Person]

            class Parent(Person):
                pass

            Parent.is_a.append(hasChild.some(Person))

            r = Imp()
            r.set_as_rule("hasChild(?x, ?y) -> HasDescendant(?x)")

            carol = Parent("carol")
            if with_named_child:
                carol.hasChild = [Person("kid1")]
        sync_reasoner_hermit(onto.world, infer_property_values=True, debug=0)
        return names(onto.HasDescendant.instances())

    print("  carol เป็น Parent (มีลูกแน่ ๆ แต่ไม่รู้ว่าใคร)")
    print(f"  HasDescendant : {build(False)}          ⬅️ ว่างเปล่า! rule ไม่ทำงาน")
    print("  ถ้าเพิ่ม hasChild(carol, kid1) ที่มีชื่อจริง :")
    print(f"  HasDescendant : {build(True)}   ⬅️ ทำงานทันที")


# ---------------------------------------------------------------- กรณี 5
def case5_inconsistency() -> None:
    """rule ที่ชนกับ owl:disjointWith ทำให้ ontology inconsistent"""
    head(5, "rule ทำให้ inconsistent")
    from owlready2 import AllDisjoint

    onto = World().get_ontology("http://example.org/food#")
    with onto:
        class Person(Thing):
            pass

        class Food(Thing):
            pass

        class Meat(Food):
            pass

        class Vegetarian(Person):
            pass

        class MeatEater(Person):
            pass

        AllDisjoint([Vegetarian, MeatEater])

        class eats(ObjectProperty):
            domain, range = [Person], [Food]

        r = Imp()
        r.set_as_rule("eats(?p, ?f), Meat(?f) -> MeatEater(?p)")

        alice = Vegetarian("alice")
        alice.eats = [Meat("bacon")]

    try:
        sync_reasoner_hermit(onto.world, debug=0)
        print("  ❌ ไม่พบ inconsistency (ผิดคาด)")
    except OwlReadyInconsistentOntologyError:
        print("  ✅ ตรวจพบ inconsistency ตามคาด")
        print("     OwlReadyInconsistentOntologyError")


if __name__ == "__main__":
    case1_owl_feeds_swrl()
    case2_swrl_feeds_owl()
    case3_round_trip()
    case4_dl_safe()
    case5_inconsistency()
    print()
