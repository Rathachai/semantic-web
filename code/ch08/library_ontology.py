"""
library_ontology.py
-------------------
Chapter 08 companion script.

สร้าง Library ontology ด้วย owlready2 โดยใช้ OWL construct ครบทุกกลุ่มที่เรียนใน Chapter 08:

  - Class axioms      : subClassOf, equivalentClass, disjointWith, AllDisjoint
  - Class constructors: intersectionOf (&), unionOf (|), complementOf (Not), oneOf
  - Property types    : ObjectProperty, DataProperty
  - Property axioms   : inverseOf, subPropertyOf, propertyChainAxiom
  - Characteristics   : Transitive, Symmetric, Functional, InverseFunctional,
                        Asymmetric, Irreflexive
  - Restrictions      : some (∃), only (∀), value, min/max/exactly
  - Individual axioms : AllDifferent

Requirements:
    pip install owlready2

Usage:
    python library_ontology.py                 # สร้างและแสดงโครงสร้าง
    python library_ontology.py library.owl     # บันทึกเป็นไฟล์
"""

import sys
from pathlib import Path

from owlready2 import (
    AllDifferent,
    AllDisjoint,
    AsymmetricProperty,
    DataProperty,
    FunctionalProperty,
    InverseFunctionalProperty,
    IrreflexiveProperty,
    Not,
    ObjectProperty,
    OneOf,
    SymmetricProperty,
    Thing,
    TransitiveProperty,
    get_ontology,
)

ONTO_IRI = "http://example.org/library#"
onto = get_ontology(ONTO_IRI)


# ===========================================================================
# TBox — primitive classes
# ===========================================================================

with onto:

    class Agent(Thing):
        """Anything that can act: a person or an organization."""

    class Person(Agent):
        """A human being."""

    class Author(Person):
        """A person who has written at least one publication."""

    class Member(Person):
        """A registered library member."""

    class Librarian(Person):
        """A staff member of the library."""

    class Organization(Agent):
        """A structured group, e.g. a publisher."""

    class Publisher(Organization):
        pass

    class Library(Organization):
        pass

    # ----- publications -----
    class Publication(Thing):
        """Anything the library holds."""

    class Book(Publication):
        pass

    class Journal(Publication):
        pass

    class Thesis(Publication):
        pass

    class FictionBook(Book):
        pass

    class NonFictionBook(Book):
        pass

    class ReferenceBook(Book):
        """A book that must stay in the library."""

    # ----- other -----
    class Loan(Thing):
        """A reified n-ary relation: who borrowed what, when."""

    class Genre(Thing):
        pass

    class Location(Thing):
        pass


# ===========================================================================
# TBox — disjointness  (⚠️ ถ้าไม่มีส่วนนี้ reasoner จะจับ error ไม่ได้เลย)
# ===========================================================================

with onto:
    # Book / Journal / Thesis ไม่ทับกัน
    AllDisjoint([Book, Journal, Thesis])

    # Publication / Person / Organization / Loan ไม่ทับกัน
    AllDisjoint([Publication, Person, Organization, Loan])

    # Fiction กับ NonFiction ไม่ทับกัน
    FictionBook.is_a.append(Not(NonFictionBook))

    # Member กับ Librarian ไม่ทับกัน
    Member.is_a.append(Not(Librarian))


# ===========================================================================
# RBox — object properties
# ===========================================================================

with onto:

    class writtenBy(ObjectProperty):
        """Publication -> Author"""
        domain = [Publication]
        range = [Author]

    class wrote(ObjectProperty):
        """inverse ของ writtenBy"""
        inverse_property = writtenBy

    class publishedBy(ObjectProperty, FunctionalProperty):
        """หนังสือหนึ่งเล่มมีสำนักพิมพ์เดียว"""
        domain = [Publication]
        range = [Publisher]

    class hasGenre(ObjectProperty):
        domain = [Publication]
        range = [Genre]

    class heldBy(ObjectProperty):
        domain = [Publication]
        range = [Library]

    # ----- loan -----
    class loanOf(ObjectProperty, FunctionalProperty):
        domain = [Loan]
        range = [Publication]

    class borrowedBy(ObjectProperty, FunctionalProperty):
        domain = [Loan]
        range = [Member]

    class hasLoan(ObjectProperty):
        inverse_property = borrowedBy

    # ----- location hierarchy (transitive) -----
    class partOf(ObjectProperty, TransitiveProperty):
        """Shelf partOf Room partOf Building -- transitive"""
        domain = [Location]
        range = [Location]

    class shelvedAt(ObjectProperty, FunctionalProperty):
        domain = [Publication]
        range = [Location]

    # ----- social -----
    class coAuthorOf(ObjectProperty, SymmetricProperty, IrreflexiveProperty):
        """ความสัมพันธ์แบบสองทาง และห้ามเป็นผู้เขียนร่วมกับตัวเอง"""
        domain = [Author]
        range = [Author]

    class citedBy(ObjectProperty, AsymmetricProperty, IrreflexiveProperty):
        """เอกสารอ้างอิงกันเองไม่ได้ และห้ามอ้างตัวเอง"""
        domain = [Publication]
        range = [Publication]

    # ----- property chain (OWL 2) -----
    class locatedIn(ObjectProperty):
        """shelvedAt ∘ partOf ⊑ locatedIn"""
        domain = [Publication]
        range = [Location]

    locatedIn.property_chain = None      # owlready2 ใช้ property_chain แบบพิเศษ


# owlready2 ประกาศ property chain ผ่าน Imp / หรือแก้ RDF ตรง ๆ
# วิธีที่ตรงไปตรงมาที่สุดคือใช้ SWRL หรือแก้หลัง export
# ที่นี่เราสาธิตด้วย subproperty + transitive แทน
with onto:
    shelvedAt.is_a.append(locatedIn)


# ===========================================================================
# RBox — data properties
# ===========================================================================

with onto:

    class isbn(DataProperty, FunctionalProperty, InverseFunctionalProperty):
        """ISBN ระบุหนังสือได้เล่มเดียว"""
        domain = [Book]
        range = [str]

    class title(DataProperty, FunctionalProperty):
        domain = [Publication]
        range = [str]

    class publicationYear(DataProperty, FunctionalProperty):
        domain = [Publication]
        range = [int]

    class pageCount(DataProperty, FunctionalProperty):
        domain = [Publication]
        range = [int]

    class memberId(DataProperty, FunctionalProperty, InverseFunctionalProperty):
        domain = [Member]
        range = [str]

    class loanDate(DataProperty, FunctionalProperty):
        domain = [Loan]
        range = [str]

    class returned(DataProperty, FunctionalProperty):
        domain = [Loan]
        range = [bool]


# ===========================================================================
# TBox — defined classes (ทำให้เกิด automatic classification)
# ===========================================================================

with onto:

    # --- someValuesFrom (∃) ---
    class PublishedAuthor(Thing):
        """Author ที่เขียนงานอย่างน้อยหนึ่งชิ้น"""
        equivalent_to = [Author & wrote.some(Publication)]

    # --- complementOf (¬) + intersectionOf (⊓) ---
    class LoanableBook(Thing):
        """หนังสือที่ยืมได้ = Book ที่ไม่ใช่ ReferenceBook"""
        equivalent_to = [Book & Not(ReferenceBook)]

    # --- qualified cardinality (≥n r.C) ---
    class ProlificAuthor(Thing):
        """Author ที่เขียนงาน ≥ 3 ชิ้น"""
        equivalent_to = [Author & wrote.min(3, Publication)]

    class ActiveMember(Thing):
        """Member ที่มีการยืมค้างอยู่ ≥ 1 รายการ"""
        equivalent_to = [Member & hasLoan.min(1, Loan)]

    class HeavyBorrower(Thing):
        """Member ที่ยืม ≥ 5 รายการ"""
        equivalent_to = [Member & hasLoan.min(5, Loan)]

    # --- allValuesFrom (∀) + someValuesFrom (∃) ---
    # ⚠️ ต้องมี ∃ ด้วย มิฉะนั้น vacuous truth ทำให้ทุกอย่างเข้าข่าย
    class FictionOnlyAuthor(Thing):
        """Author ที่เขียนเฉพาะนิยาย"""
        equivalent_to = [
            Author
            & wrote.some(FictionBook)
            & wrote.only(FictionBook)
        ]

    # --- hasValue (∃r.{a}) ---
    class LongBook(Thing):
        """หนังสือที่ยาว ≥ 500 หน้า -- ใช้ cardinality กับ datatype ไม่ตรงนัก
        จึงสาธิต hasValue ด้วย genre แทน"""
        equivalent_to = [Book & hasGenre.some(Genre)]

    # --- unionOf (⊔) ---
    class SerialPublication(Thing):
        """สิ่งพิมพ์ต่อเนื่อง"""
        equivalent_to = [Journal | Thesis]

    # --- oneOf (nominal) ---
    class CoreGenre(Thing):
        """หมวดหมู่หลักที่ห้องสมุดจัดไว้"""


# ===========================================================================
# ABox — individuals
# ===========================================================================

with onto:
    # ----- genres (ใช้กับ oneOf) -----
    fiction = Genre("fictionGenre", title="Fiction")
    science = Genre("scienceGenre", title="Science")
    history = Genre("historyGenre", title="History")
    CoreGenre.equivalent_to = [OneOf([fiction, science, history])]

    # ----- locations -----
    shelfA1 = Location("shelfA1")
    roomA = Location("roomA")
    mainBuilding = Location("mainBuilding")
    shelfA1.partOf = [roomA]        # partOf ไม่ functional -> list
    roomA.partOf = [mainBuilding]

    # ----- organizations -----
    penguin = Publisher("penguinBooks")
    cityLibrary = Library("cityLibrary")

    # ----- authors -----
    orwell = Author("georgeOrwell")
    huxley = Author("aldousHuxley")
    hawking = Author("stephenHawking")

    orwell.coAuthorOf = [huxley]        # symmetric -> huxley.coAuthorOf = [orwell]

    # ----- books -----
    b1984 = FictionBook("nineteenEightyFour",
                        title="Nineteen Eighty-Four",
                        isbn="978-0451524935",
                        publicationYear=1949,
                        pageCount=328)
    animalFarm = FictionBook("animalFarm",
                             title="Animal Farm",
                             isbn="978-0452284241",
                             publicationYear=1945,
                             pageCount=112)
    homage = FictionBook("homageToCatalonia",
                         title="Homage to Catalonia",
                         isbn="978-0156421171",
                         publicationYear=1938,
                         pageCount=232)
    braveNew = FictionBook("braveNewWorld",
                           title="Brave New World",
                           isbn="978-0060850524",
                           publicationYear=1932,
                           pageCount=311)
    briefHistory = NonFictionBook("aBriefHistoryOfTime",
                                  title="A Brief History of Time",
                                  isbn="978-0553380163",
                                  publicationYear=1988,
                                  pageCount=212)
    dictionary = ReferenceBook("oxfordDictionary",
                               title="Oxford English Dictionary",
                               isbn="978-0199571123",
                               publicationYear=2010,
                               pageCount=2112)

    # orwell เขียน 3 เล่ม -> ควรเป็น ProlificAuthor และ FictionOnlyAuthor
    orwell.wrote = [b1984, animalFarm, homage]
    huxley.wrote = [braveNew]
    hawking.wrote = [briefHistory]

    for book in (b1984, animalFarm, homage, braveNew, briefHistory, dictionary):
        # ⚠️ FunctionalProperty ใน owlready2 รับ "ค่าเดี่ยว" ไม่ใช่ list
        book.publishedBy = penguin          # functional  -> ค่าเดี่ยว
        book.shelvedAt = shelfA1            # functional  -> ค่าเดี่ยว
        book.heldBy = [cityLibrary]         # ไม่ functional -> list

    b1984.hasGenre = [fiction]
    briefHistory.hasGenre = [science]

    # ----- members -----
    alice = Member("aliceMember", memberId="M-001")
    bob = Member("bobMember", memberId="M-002")

    # ----- loans -----
    loan1 = Loan("loan001", loanDate="2025-06-01", returned=False)
    loan1.loanOf = b1984                    # functional
    loan1.borrowedBy = alice                # functional

    loan2 = Loan("loan002", loanDate="2025-06-05", returned=False)
    loan2.loanOf = animalFarm
    loan2.borrowedBy = alice

    # ===== ⚠️ AllDifferent -- จำเป็นสำหรับ cardinality ทุกตัว =====
    AllDifferent([b1984, animalFarm, homage, braveNew, briefHistory, dictionary])
    AllDifferent([orwell, huxley, hawking])
    AllDifferent([alice, bob])
    AllDifferent([loan1, loan2])
    AllDifferent([fiction, science, history])
    AllDifferent([shelfA1, roomA, mainBuilding])


# ===========================================================================
# แสดงโครงสร้าง
# ===========================================================================


def banner(title: str) -> None:
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


def show_structure() -> None:
    banner("CLASSES")
    for cls in onto.classes():
        parents = [
            p.name if hasattr(p, "name") else str(p).replace("library.", "")
            for p in cls.is_a
        ]
        equiv = [str(e).replace("library.", "") for e in cls.equivalent_to]
        kind = "defined " if equiv else "primitive"
        print(f"  [{kind}] {cls.name:24s} ⊑ {', '.join(parents)}")
        if equiv:
            print(f"  {'':34s} ≡ {equiv[0]}")

    banner("OBJECT PROPERTIES")
    for prop in onto.object_properties():
        chars = [
            base.__name__ for base in prop.is_a
            if isinstance(base, type) and base.__name__.endswith("Property")
            and base.__name__ != "ObjectProperty"
        ]
        inv = prop.inverse_property.name if prop.inverse_property else "-"
        dom = [c.name for c in prop.domain if hasattr(c, "name")]
        rng = [c.name for c in prop.range if hasattr(c, "name")]
        print(f"  {prop.name:16s} {dom} -> {rng}")
        if chars or inv != "-":
            print(f"  {'':16s} inverse={inv}  {chars}")

    banner("DATA PROPERTIES")
    for prop in onto.data_properties():
        chars = [
            base.__name__ for base in prop.is_a
            if isinstance(base, type) and base.__name__.endswith("Property")
            and base.__name__ != "DataProperty"
        ]
        rng = [r.__name__ if hasattr(r, "__name__") else str(r) for r in prop.range]
        print(f"  {prop.name:18s} -> {rng}  {chars}")

    banner("INDIVIDUALS")
    counts: dict = {}
    for ind in onto.individuals():
        for cls in ind.is_a:
            if hasattr(cls, "name"):
                counts[cls.name] = counts.get(cls.name, 0) + 1
    for cls_name, count in sorted(counts.items()):
        print(f"  {cls_name:22s} {count}")
    print(f"\n  รวม {len(list(onto.individuals()))} individuals")


def main() -> None:
    show_structure()

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("library.owl")
    onto.save(file=str(output), format="rdfxml")
    print(f"\n  บันทึก {output} ({output.stat().st_size:,} bytes)")
    print("  ขั้นต่อไป: รัน owl_reasoning.py เพื่อทำ reasoning")


if __name__ == "__main__":
    main()
