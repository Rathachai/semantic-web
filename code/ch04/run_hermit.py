"""
run_hermit.py
-------------
Chapter 04 companion script.

รัน HermiT reasoner บน KB จาก tbox_abox.py แล้วสาธิต reasoning task ทั้ง 6:
  1. Concept satisfiability   -- class ไหน unsatisfiable
  2. KB consistency           -- KB ขัดกันเองไหม
  3. Subsumption              -- C ⊑ D ?
  4. Equivalence              -- C ≡ D ?
  5. Instance checking        -- a : C ?
  6. Realization / Retrieval  -- a อยู่ class ไหน / C มีสมาชิกใคร

จากนั้นสาธิตการทำให้ KB inconsistent โดยตั้งใจ เพื่อดูว่า reasoner ตอบอย่างไร

Requirements:
    pip install owlready2
    ต้องมี Java 8+ ติดตั้งอยู่ (HermiT เป็นโปรแกรม Java)

Usage:
    python run_hermit.py
"""

from owlready2 import (
    Nothing,
    OwlReadyInconsistentOntologyError,
    Thing,
    World,
    sync_reasoner_hermit,
)

import tbox_abox  # โหลด KB ที่สร้างไว้

onto = tbox_abox.onto


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def type_names(individual) -> list:
    return sorted(c.name for c in individual.is_a if hasattr(c, "name"))


# ---------------------------------------------------------------------------
# 1) เก็บสภาพก่อน reasoning
# ---------------------------------------------------------------------------


def snapshot_before() -> dict:
    return {ind.name: type_names(ind) for ind in onto.individuals()}


# ---------------------------------------------------------------------------
# 2) รัน reasoner
# ---------------------------------------------------------------------------


def run_reasoner() -> bool:
    """รัน HermiT; คืน True ถ้า consistent"""
    try:
        with onto:
            sync_reasoner_hermit(infer_property_values=True)
        return True
    except OwlReadyInconsistentOntologyError:
        return False


# ---------------------------------------------------------------------------
# reasoning tasks
# ---------------------------------------------------------------------------


def task_satisfiability() -> None:
    """Task 1 -- class ไหน unsatisfiable (equivalent กับ owl:Nothing)"""
    banner("TASK 1 — Concept Satisfiability")
    unsat = [c for c in onto.classes() if Nothing in c.equivalent_to]
    if unsat:
        for cls in unsat:
            print(f"  ❌ {cls.name:20s} unsatisfiable (≡ ⊥)")
    else:
        print("  ✅ ทุก class satisfiable")
    print("\n  หมายเหตุ: StudentProfessor ≡ Student ⊓ Professor")
    print("            และ Student ⊑ ¬Professor  → จึงเป็น ⊥")


def task_consistency(consistent: bool) -> None:
    """Task 2 -- KB consistency"""
    banner("TASK 2 — KB Consistency")
    if consistent:
        print("  ✅ KB consistent — มี model อย่างน้อยหนึ่งตัว")
    else:
        print("  ❌ KB inconsistent — อนุมานได้ทุกอย่าง ผลลัพธ์ไร้ความหมาย")


def task_subsumption() -> None:
    """Task 3 -- C ⊑ D ?"""
    banner("TASK 3 — Subsumption")
    pairs = [
        (onto.GraduateStudent, onto.Student),
        (onto.GraduateStudent, onto.Person),
        (onto.Professor, onto.Person),
        (onto.Parent, onto.Person),
        (onto.Student, onto.Professor),
    ]
    for sub, sup in pairs:
        # ใน owlready2 หลัง reasoning, ancestors() ให้ superclass ทั้งหมด
        holds = sup in sub.ancestors()
        mark = "✅" if holds else "❌"
        print(f"  {mark} {sub.name:18s} ⊑ {sup.name}")


def task_equivalence() -> None:
    """Task 4 -- C ≡ D ?"""
    banner("TASK 4 — Equivalence")
    for cls in onto.classes():
        equivalents = [e.name for e in cls.equivalent_to if hasattr(e, "name")]
        if equivalents:
            print(f"  {cls.name:20s} ≡ {', '.join(equivalents)}")
    print("  (แสดงเฉพาะ named class ที่ reasoner พบว่าเท่ากัน)")


def task_instance_checking(before: dict) -> None:
    """Task 5 -- a : C ?  เทียบก่อน/หลัง reasoning"""
    banner("TASK 5 — Instance Checking (ก่อน vs หลัง reasoning)")
    for ind in onto.individuals():
        old = before.get(ind.name, [])
        new = type_names(ind)
        gained = [t for t in new if t not in old]
        gained_str = f"  ← เพิ่ม: {', '.join(gained)}" if gained else ""
        print(f"  {ind.name:12s} {old} → {new}{gained_str}")


def task_realization_retrieval() -> None:
    """Task 6 -- Realization และ Retrieval"""
    banner("TASK 6 — Realization & Retrieval")

    print("  Realization (individual อยู่ใน class ไหนบ้าง):")
    for ind in onto.individuals():
        print(f"    {ind.name:12s} : {type_names(ind)}")

    print("\n  Retrieval (แต่ละ class มีสมาชิกใครบ้าง):")
    for cls in [onto.Person, onto.Student, onto.GraduateStudent,
                onto.Parent, onto.Professor, onto.Course]:
        members = sorted(i.name for i in cls.instances())
        print(f"    {cls.name:18s} = {members}")


# ---------------------------------------------------------------------------
# สาธิต inconsistency
# ---------------------------------------------------------------------------


def demo_inconsistency() -> None:
    """สร้าง KB ที่ inconsistent โดยตั้งใจ ใน World แยกต่างหาก"""
    banner("BONUS — สาธิต KB ที่ inconsistent")

    world = World()
    bad = world.get_ontology("http://example.org/bad.owl")

    from owlready2 import Not as _Not

    with bad:
        class Person(Thing):
            pass

        class Student(Person):
            pass

        class Professor(Person):
            pass

        Student.is_a.append(_Not(Professor))

        # alice เป็นทั้ง Student และ Professor -> ขัดกับ disjointness
        alice = Student("alice")
        alice.is_a.append(Professor)

    try:
        with bad:
            sync_reasoner_hermit(x=world)
        print("  ⚠️ ไม่คาดคิด: reasoner บอกว่า consistent")
    except OwlReadyInconsistentOntologyError:
        print("  ❌ INCONSISTENT ตามที่คาดไว้")
        print("     Justification:")
        print("       1. Student ⊑ ¬Professor")
        print("       2. alice : Student")
        print("       3. alice : Professor")
        print("     → ไม่มี interpretation ใดที่ทั้งสามข้อเป็นจริงพร้อมกัน")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    before = snapshot_before()

    banner("รัน HermiT reasoner...")
    consistent = run_reasoner()

    task_consistency(consistent)
    if not consistent:
        print("  หยุดการทำงาน — ต้องแก้ inconsistency ก่อน")
        return

    task_satisfiability()
    task_subsumption()
    task_equivalence()
    task_instance_checking(before)
    task_realization_retrieval()
    demo_inconsistency()


if __name__ == "__main__":
    main()
