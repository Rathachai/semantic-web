"""ตัวอย่าง SWRL rule 4 ชุด: family, BMI, discount, course prerequisite

รัน:  python3 code/ch11/swrl_rules.py

หมายเหตุ: กฎที่ใช้ builtin ต้องใช้ Pellet -- HermiT ไม่รองรับ builtin
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from owlready2 import (AllDifferent, DataProperty, FunctionalProperty, Imp,
                       ObjectProperty, Thing, World, sync_reasoner_hermit)

from pellet_runner import parse_propvals, parse_realization, run_pellet


# ⚠️ ทุก demo ต้องใช้ World ของตัวเอง
#    ถ้าใช้ default_world ร่วมกัน ตัวแปร SWRL ชื่อซ้ำ (เช่น ?p) จะถูก reuse
#    ข้าม ontology ทำให้ swrl:Variable ไม่ถูกบันทึกลงไฟล์ที่ส่งให้ Pellet
#    → atom กลายเป็น ground atom และกฎเงียบ ๆ ไม่ทำงาน


def banner(title: str) -> None:
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)


# ==================== 1. Family rules (ไม่ใช้ builtin → HermiT พอ) ====================

def demo_family() -> None:
    banner("1. FAMILY RULES (HermiT -- ไม่มี builtin)")

    onto = World().get_ontology("http://example.org/family#")
    with onto:
        class Person(Thing):
            pass

        class Male(Person):
            pass

        class Female(Person):
            pass

        class hasParent(ObjectProperty):
            pass

        class hasBrother(ObjectProperty):
            pass

        class hasUncle(ObjectProperty):
            pass

        class hasSibling(ObjectProperty):
            pass

        class hasGrandparent(ObjectProperty):
            pass

        # ลุง = พี่ชายของพ่อแม่  (OWL ทำได้ด้วย propertyChainAxiom เช่นกัน)
        Imp().set_as_rule(
            "Person(?x), hasParent(?x, ?y), hasBrother(?y, ?z) -> hasUncle(?x, ?z)")

        # พี่น้อง = มีพ่อแม่คนเดียวกัน  (OWL ทำไม่ได้!)
        Imp().set_as_rule(
            "Person(?x), Person(?y), hasParent(?x, ?p), hasParent(?y, ?p), "
            "differentFrom(?x, ?y) -> hasSibling(?x, ?y)")

        # ปู่ย่าตายาย = พ่อแม่ของพ่อแม่
        Imp().set_as_rule(
            "hasParent(?x, ?y), hasParent(?y, ?z) -> hasGrandparent(?x, ?z)")

        # ----- ABox -----
        george = Male("george")
        mary = Female("mary")
        bob = Male("bob")
        john = Male("john")
        jane = Female("jane")

        mary.hasParent = [george]
        bob.hasParent = [george]
        mary.hasBrother = [bob]
        john.hasParent = [mary]
        jane.hasParent = [mary]

        AllDifferent([george, mary, bob, john, jane])

    sync_reasoner_hermit(onto.world, infer_property_values=True)

    print(f"  john.hasUncle       = {[p.name for p in john.hasUncle]}")
    print(f"  john.hasSibling     = {[p.name for p in john.hasSibling]}")
    print(f"  john.hasGrandparent = {[p.name for p in john.hasGrandparent]}")
    print(f"  mary.hasSibling     = {[p.name for p in mary.hasSibling]}")


# ==================== 2. BMI (ใช้ builtin → Pellet) ====================

def demo_bmi() -> None:
    banner("2. BMI CATEGORY (Pellet -- ใช้ builtin)")

    onto = World().get_ontology("http://example.org/health#")
    with onto:
        class Patient(Thing):
            pass

        class Underweight(Patient):
            pass

        class NormalWeight(Patient):
            pass

        class Overweight(Patient):
            pass

        class Obese(Patient):
            pass

        class weightKg(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        class heightM(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        class bmi(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        # BMI = weight / height²
        Imp().set_as_rule(
            "Patient(?p), weightKg(?p, ?w), heightM(?p, ?h), "
            "multiply(?hh, ?h, ?h), divide(?b, ?w, ?hh) -> bmi(?p, ?b)")

        # จัดหมวดตามเกณฑ์ WHO
        Imp().set_as_rule(
            "Patient(?p), bmi(?p, ?b), lessThan(?b, 18.5) -> Underweight(?p)")
        Imp().set_as_rule(
            "Patient(?p), bmi(?p, ?b), greaterThanOrEqual(?b, 18.5), "
            "lessThan(?b, 25.0) -> NormalWeight(?p)")
        Imp().set_as_rule(
            "Patient(?p), bmi(?p, ?b), greaterThanOrEqual(?b, 25.0), "
            "lessThan(?b, 30.0) -> Overweight(?p)")
        Imp().set_as_rule(
            "Patient(?p), bmi(?p, ?b), greaterThanOrEqual(?b, 30.0) -> Obese(?p)")

        for name, w, h in [("john", 95.0, 1.75), ("mary", 55.0, 1.65),
                           ("sara", 45.0, 1.70), ("dave", 80.0, 1.72)]:
            p = Patient(name)
            p.weightKg, p.heightM = w, h

    out = run_pellet(onto)
    print("  Classification:")
    for cls, inds in parse_realization(out).items():
        print(f"    {cls:14s} → {inds}")
    print("\n  Computed BMI:")
    for subj, prop, val in sorted(parse_propvals(out)):
        if prop == "bmi":
            print(f"    {subj:6s} = {float(val):.2f}")


# ==================== 3. Discount eligibility ====================

def demo_discount() -> None:
    banner("3. DISCOUNT ELIGIBILITY (Pellet)")

    onto = World().get_ontology("http://example.org/shop#")
    with onto:
        class Customer(Thing):
            pass

        class Order(Thing):
            pass

        class GoldCustomer(Customer):
            pass

        class RegularCustomer(Customer):
            pass

        class placedBy(ObjectProperty, FunctionalProperty):
            domain = [Order]
            range = [Customer]

        class subtotal(DataProperty, FunctionalProperty):
            domain = [Order]
            range = [float]

        class memberYears(DataProperty, FunctionalProperty):
            domain = [Customer]
            range = [int]

        class discountRate(DataProperty, FunctionalProperty):
            domain = [Order]
            range = [float]

        class finalPrice(DataProperty, FunctionalProperty):
            domain = [Order]
            range = [float]

        # ลูกค้าระดับ Gold = เป็นสมาชิกเกิน 5 ปี
        Imp().set_as_rule(
            "Customer(?c), memberYears(?c, ?y), greaterThan(?y, 5) -> GoldCustomer(?c)")

        # ส่วนลด 15% สำหรับ Gold ที่ซื้อเกิน 1000
        Imp().set_as_rule(
            "Order(?o), placedBy(?o, ?c), GoldCustomer(?c), subtotal(?o, ?s), "
            "greaterThan(?s, 1000.0) -> discountRate(?o, 0.15)")

        # ⚠️ SWRL ไม่มี negation -- เขียน "ถ้าไม่ใช่ Gold" ไม่ได้
        #    ต้องนิยาม RegularCustomer ด้วยเงื่อนไขบวกแทน
        Imp().set_as_rule(
            "Customer(?c), memberYears(?c, ?y), lessThanOrEqual(?y, 5) "
            "-> RegularCustomer(?c)")

        # ส่วนลด 5% สำหรับลูกค้าทั่วไปที่ซื้อเกิน 1000
        Imp().set_as_rule(
            "Order(?o), placedBy(?o, ?c), RegularCustomer(?c), subtotal(?o, ?s), "
            "greaterThan(?s, 1000.0) -> discountRate(?o, 0.05)")

        # ราคาสุทธิ = subtotal × (1 − rate)
        Imp().set_as_rule(
            "Order(?o), subtotal(?o, ?s), discountRate(?o, ?r), "
            "subtract(?keep, 1.0, ?r), multiply(?f, ?s, ?keep) -> finalPrice(?o, ?f)")

        alice = Customer("alice")
        alice.memberYears = 7
        bob = Customer("bob")
        bob.memberYears = 2

        o1 = Order("order001")
        o1.placedBy, o1.subtotal = alice, 1500.0
        o2 = Order("order002")
        o2.placedBy, o2.subtotal = bob, 1500.0

    out = run_pellet(onto)
    print("  Classification:")
    for cls, inds in parse_realization(out).items():
        print(f"    {cls:14s} → {inds}")
    print("\n  Order values:")
    for subj, prop, val in sorted(parse_propvals(out)):
        if prop in ("discountRate", "finalPrice"):
            print(f"    {subj:10s} {prop:13s} = {val}")


# ==================== 4. Course prerequisite ====================

def demo_prerequisite() -> None:
    banner("4. COURSE PREREQUISITE (Pellet)")

    onto = World().get_ontology("http://example.org/uni#")
    with onto:
        class Student(Thing):
            pass

        class Course(Thing):
            pass

        class EligibleStudent(Student):
            pass

        class hasPrerequisite(ObjectProperty):
            domain = [Course]
            range = [Course]

        class completed(ObjectProperty):
            domain = [Student]
            range = [Course]

        class eligibleFor(ObjectProperty):
            domain = [Student]
            range = [Course]

        class gpa(DataProperty, FunctionalProperty):
            domain = [Student]
            range = [float]

        # นักศึกษาที่เรียนวิชาบังคับก่อนหน้าครบ + GPA ≥ 2.5 → ลงทะเบียนได้
        Imp().set_as_rule(
            "Student(?s), Course(?c), hasPrerequisite(?c, ?pre), completed(?s, ?pre), "
            "gpa(?s, ?g), greaterThanOrEqual(?g, 2.5) -> eligibleFor(?s, ?c), "
            "EligibleStudent(?s)")

        cs101 = Course("cs101")
        cs201 = Course("cs201")
        cs301 = Course("cs301")
        cs201.hasPrerequisite = [cs101]
        cs301.hasPrerequisite = [cs201]

        alice = Student("alice")
        alice.completed = [cs101]
        alice.gpa = 3.2

        bob = Student("bob")
        bob.completed = [cs101]
        bob.gpa = 2.1

        AllDifferent([cs101, cs201, cs301, alice, bob])

    out = run_pellet(onto)
    print("  Classification:")
    for cls, inds in parse_realization(out).items():
        print(f"    {cls:16s} → {inds}")
    print("\n  eligibleFor:")
    found = False
    for subj, prop, obj in parse_propvals(out):
        if prop == "eligibleFor":
            print(f"    {subj:8s} → {obj}")
            found = True
    if not found:
        print("    (none)")


if __name__ == "__main__":
    demo_family()
    demo_bmi()
    demo_discount()
    demo_prerequisite()
