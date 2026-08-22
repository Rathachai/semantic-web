"""
tbox_abox.py
------------
Chapter 04 companion script.

สร้าง Knowledge Base (TBox + ABox) ด้วย owlready2 โดยแปลง DL axiom เป็นโค้ด Python
แสดงการ map จาก DL notation -> owlready2 API ตรง ๆ

DL ที่ implement ในไฟล์นี้:
    --- TBox ---
    Student         ⊑ Person
    Professor       ⊑ Staff
    Staff           ⊑ Person
    Student ⊓ Professor ⊑ ⊥
    Parent          ≡ Person ⊓ ∃hasChild.Person
    GraduateStudent ≡ Student ⊓ ∃enrolledIn.GraduateCourse
    GraduateCourse  ⊑ Course

    --- RBox ---
    enrolledIn ⊑ involvedIn
    teaches    ⊑ involvedIn
    hasChild   ≡ hasParent⁻
    hasAncestor เป็น transitive

    --- ABox ---
    alice : Student, (alice, cs501) : enrolledIn, cs501 : GraduateCourse
    profSmith : Professor, (profSmith, cs501) : teaches
    alice ≠ profSmith

Requirements:
    pip install owlready2

Usage:
    python tbox_abox.py
"""

from owlready2 import (
    AllDifferent,
    Not,
    ObjectProperty,
    Thing,
    TransitiveProperty,
    get_ontology,
)

ONTO_IRI = "http://example.org/university.owl"

onto = get_ontology(ONTO_IRI)


# ---------------------------------------------------------------------------
# TBox -- concept
# ---------------------------------------------------------------------------

with onto:

    class Person(Thing):
        """Person ⊑ ⊤"""

    class Student(Person):
        """Student ⊑ Person"""

    class Staff(Person):
        """Staff ⊑ Person"""

    class Professor(Staff):
        """Professor ⊑ Staff"""

    class Course(Thing):
        """Course ⊑ ⊤"""

    class GraduateCourse(Course):
        """GraduateCourse ⊑ Course"""

    # ----- RBox: role -----

    class hasChild(ObjectProperty):
        """hasChild: Person -> Person"""
        domain = [Person]
        range = [Person]

    class hasParent(ObjectProperty):
        """hasParent ≡ hasChild⁻"""
        domain = [Person]
        range = [Person]
        inverse_property = hasChild

    class hasAncestor(hasParent, TransitiveProperty):
        """hasAncestor⁺ ⊑ hasAncestor  (transitive)"""

    class involvedIn(ObjectProperty):
        """involvedIn: Person -> Course"""
        domain = [Person]
        range = [Course]

    class enrolledIn(involvedIn):
        """enrolledIn ⊑ involvedIn"""
        domain = [Student]
        range = [Course]

    class teaches(involvedIn):
        """teaches ⊑ involvedIn"""
        domain = [Professor]
        range = [Course]

    # ----- disjointness: Student ⊓ Professor ⊑ ⊥ -----
    Student.is_a.append(Not(Professor))

    # ----- defined class: Parent ≡ Person ⊓ ∃hasChild.Person -----
    class Parent(Thing):
        """Parent ≡ Person ⊓ ∃hasChild.Person"""
        equivalent_to = [Person & hasChild.some(Person)]

    # ----- defined class: GraduateStudent ≡ Student ⊓ ∃enrolledIn.GraduateCourse -----
    class GraduateStudent(Thing):
        """GraduateStudent ≡ Student ⊓ ∃enrolledIn.GraduateCourse"""
        equivalent_to = [Student & enrolledIn.some(GraduateCourse)]

    # ----- defined class ที่จะกลายเป็น unsatisfiable โดยตั้งใจ -----
    class StudentProfessor(Thing):
        """StudentProfessor ≡ Student ⊓ Professor  -- ควรเป็น unsatisfiable"""
        equivalent_to = [Student & Professor]


# ---------------------------------------------------------------------------
# ABox -- individuals
# ---------------------------------------------------------------------------

with onto:
    alice = Student("alice")
    bob = Person("bob")
    carol = Person("carol")
    prof_smith = Professor("profSmith")

    cs101 = Course("cs101")
    cs501 = GraduateCourse("cs501")

    # role assertions
    alice.enrolledIn = [cs501, cs101]
    prof_smith.teaches = [cs101, cs501]
    alice.hasChild = [bob]
    bob.hasChild = [carol]

    # a ≠ b -- OWL ไม่มี Unique Name Assumption จึงต้องบอกให้ชัด
    AllDifferent([alice, bob, carol, prof_smith])


# ---------------------------------------------------------------------------
# แสดงผล
# ---------------------------------------------------------------------------


def show_tbox() -> None:
    print("=" * 72)
    print("  TBox — Concepts")
    print("=" * 72)
    for cls in onto.classes():
        parents = [p.name if hasattr(p, "name") else str(p) for p in cls.is_a]
        equiv = [str(e) for e in cls.equivalent_to]
        line = f"  {cls.name:20s} ⊑ {', '.join(parents)}"
        if equiv:
            line += f"\n  {'':20s} ≡ {', '.join(equiv)}"
        print(line)

    print("\n" + "=" * 72)
    print("  RBox — Roles")
    print("=" * 72)
    for prop in onto.object_properties():
        parents = [p.name for p in prop.is_a if hasattr(p, "name")]
        inv = prop.inverse_property.name if prop.inverse_property else "-"
        dom = [c.name for c in prop.domain]
        rng = [c.name for c in prop.range]
        print(f"  {prop.name:15s} ⊑ {', '.join(parents) or '-':20s} "
              f"inverse={inv:12s} {dom} -> {rng}")


def show_abox() -> None:
    print("\n" + "=" * 72)
    print("  ABox — Individuals (ก่อน reasoning)")
    print("=" * 72)
    for ind in onto.individuals():
        types = [c.name for c in ind.is_a if hasattr(c, "name")]
        print(f"  {ind.name:12s} : {', '.join(types)}")
        for prop in ind.get_properties():
            values = [
                v.name if hasattr(v, "name") else str(v)
                for v in prop[ind]
            ]
            print(f"      {prop.python_name:15s} -> {values}")


def main() -> None:
    show_tbox()
    show_abox()

    onto.save(file="university_tbox_abox.owl", format="rdfxml")
    print("\n  บันทึกเป็น university_tbox_abox.owl แล้ว")
    print("  ขั้นต่อไป: รัน run_hermit.py เพื่อทำ reasoning")


if __name__ == "__main__":
    main()
