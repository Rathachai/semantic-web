"""
rdfs_schema.py
--------------
Chapter 03 companion script.

สร้าง RDFS schema ของมหาวิทยาลัยด้วย rdflib แล้วบันทึกเป็น Turtle
ครอบคลุม:
  - rdfs:Class + rdfs:subClassOf
  - rdf:Property + rdfs:subPropertyOf
  - rdfs:domain / rdfs:range
  - annotation: rdfs:label, rdfs:comment, rdfs:isDefinedBy
  - instance data (ABox)

Requirements:
    pip install rdflib

Usage:
    python rdfs_schema.py                 # พิมพ์ Turtle ออกหน้าจอ
    python rdfs_schema.py university.ttl  # บันทึกลงไฟล์
"""

import sys

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

EX = Namespace("http://example.org/university#")
ONTO = URIRef("http://example.org/university")


# ---------------------------------------------------------------------------
# helper: ลดโค้ดซ้ำเวลาประกาศ class / property
# ---------------------------------------------------------------------------


def declare_class(g: Graph, cls, label: str, comment: str, parent=None) -> None:
    """ประกาศ rdfs:Class พร้อม annotation ครบถ้วน"""
    g.add((cls, RDF.type, RDFS.Class))
    g.add((cls, RDFS.label, Literal(label, lang="en")))
    g.add((cls, RDFS.comment, Literal(comment, lang="en")))
    g.add((cls, RDFS.isDefinedBy, ONTO))
    if parent is not None:
        g.add((cls, RDFS.subClassOf, parent))


def declare_property(g: Graph, prop, label: str, comment: str,
                     domain=None, range_=None, parent=None) -> None:
    """ประกาศ rdf:Property พร้อม domain/range และ annotation"""
    g.add((prop, RDF.type, RDF.Property))
    g.add((prop, RDFS.label, Literal(label, lang="en")))
    g.add((prop, RDFS.comment, Literal(comment, lang="en")))
    g.add((prop, RDFS.isDefinedBy, ONTO))
    if domain is not None:
        g.add((prop, RDFS.domain, domain))
    if range_ is not None:
        g.add((prop, RDFS.range, range_))
    if parent is not None:
        g.add((prop, RDFS.subPropertyOf, parent))


# ---------------------------------------------------------------------------
# TBox: class hierarchy
# ---------------------------------------------------------------------------


def build_classes(g: Graph) -> None:
    declare_class(g, EX.Agent, "Agent",
                  "Anything that can act: a person or an organization.")

    declare_class(g, EX.Person, "Person",
                  "A human being.", parent=EX.Agent)

    declare_class(g, EX.Student, "Student",
                  "A person enrolled in at least one course.", parent=EX.Person)

    declare_class(g, EX.GraduateStudent, "Graduate Student",
                  "A student enrolled in a graduate-level programme.",
                  parent=EX.Student)

    declare_class(g, EX.Staff, "Staff",
                  "A person employed by the university.", parent=EX.Person)

    declare_class(g, EX.Professor, "Professor",
                  "A staff member who teaches and conducts research.",
                  parent=EX.Staff)

    declare_class(g, EX.Organization, "Organization",
                  "A structured group of people.", parent=EX.Agent)

    declare_class(g, EX.University, "University",
                  "An institution of higher education.", parent=EX.Organization)

    declare_class(g, EX.Department, "Department",
                  "An academic unit within a university.", parent=EX.Organization)

    declare_class(g, EX.Course, "Course",
                  "A unit of teaching delivered over one academic term.")

    # GraduateStudent มีสองพ่อแม่ -- multiple inheritance
    g.add((EX.GraduateStudent, RDFS.subClassOf, EX.Researcher))
    declare_class(g, EX.Researcher, "Researcher",
                  "A person who conducts research.", parent=EX.Person)


# ---------------------------------------------------------------------------
# TBox: property hierarchy
# ---------------------------------------------------------------------------


def build_properties(g: Graph) -> None:
    declare_property(g, EX.involvedIn, "involved in",
                     "Generic relation between a person and a course.",
                     domain=EX.Person, range_=EX.Course)

    declare_property(g, EX.enrolledIn, "enrolled in",
                     "Relates a student to a course they currently attend. "
                     "Does not cover completed or dropped courses.",
                     domain=EX.Student, range_=EX.Course,
                     parent=EX.involvedIn)

    declare_property(g, EX.teaches, "teaches",
                     "Relates a professor to a course they deliver.",
                     domain=EX.Professor, range_=EX.Course,
                     parent=EX.involvedIn)

    declare_property(g, EX.assists, "assists",
                     "Relates a teaching assistant to a course.",
                     range_=EX.Course, parent=EX.teaches)

    declare_property(g, EX.memberOf, "member of",
                     "Relates a person to the organization they belong to.",
                     domain=EX.Person, range_=EX.Organization)

    declare_property(g, EX.partOf, "part of",
                     "Relates a department to its parent university.",
                     domain=EX.Department, range_=EX.University)

    declare_property(g, EX.credits, "credits",
                     "The number of credit units awarded by a course.",
                     domain=EX.Course, range_=XSD.integer)

    declare_property(g, EX.courseCode, "course code",
                     "The official identifier of a course, e.g. CS101.",
                     domain=EX.Course, range_=XSD.string)


# ---------------------------------------------------------------------------
# ABox: instance data
# ---------------------------------------------------------------------------


def build_instances(g: Graph) -> None:
    # people
    g.add((EX.alice, RDF.type, EX.GraduateStudent))
    g.add((EX.alice, RDFS.label, Literal("Alice Johnson", lang="en")))
    g.add((EX.alice, EX.enrolledIn, EX.cs101))
    g.add((EX.alice, EX.enrolledIn, EX.cs501))
    g.add((EX.alice, EX.memberOf, EX.csDept))

    g.add((EX.bob, RDF.type, EX.Student))
    g.add((EX.bob, RDFS.label, Literal("Bob Smith", lang="en")))
    g.add((EX.bob, EX.enrolledIn, EX.cs101))
    g.add((EX.bob, EX.assists, EX.cs101))       # bob เป็น TA ด้วย

    g.add((EX.profSmith, RDF.type, EX.Professor))
    g.add((EX.profSmith, RDFS.label, Literal("Prof. Jane Smith", lang="en")))
    g.add((EX.profSmith, EX.teaches, EX.cs101))
    g.add((EX.profSmith, EX.teaches, EX.cs501))
    g.add((EX.profSmith, EX.memberOf, EX.csDept))

    # courses -- สังเกตว่าไม่ได้ประกาศ rdf:type ให้ cs101 เลย
    # reasoner จะอนุมานเองจาก rdfs:range ของ enrolledIn / teaches
    g.add((EX.cs101, RDFS.label, Literal("Introduction to Programming", lang="en")))
    g.add((EX.cs101, EX.courseCode, Literal("CS101")))
    g.add((EX.cs101, EX.credits, Literal(3)))

    g.add((EX.cs501, RDFS.label, Literal("Advanced Knowledge Graphs", lang="en")))
    g.add((EX.cs501, EX.courseCode, Literal("CS501")))
    g.add((EX.cs501, EX.credits, Literal(4)))

    # organizations
    g.add((EX.csDept, RDF.type, EX.Department))
    g.add((EX.csDept, RDFS.label, Literal("Department of Computer Science", lang="en")))
    g.add((EX.csDept, EX.partOf, EX.exampleUniversity))

    g.add((EX.exampleUniversity, RDF.type, EX.University))
    g.add((EX.exampleUniversity, RDFS.label, Literal("Example University", lang="en")))


# ---------------------------------------------------------------------------
# ontology header
# ---------------------------------------------------------------------------


def build_header(g: Graph) -> None:
    g.add((ONTO, RDF.type, OWL.Ontology))
    g.add((ONTO, DCTERMS.title, Literal("University RDFS Schema", lang="en")))
    g.add((ONTO, DCTERMS.description,
           Literal("A small RDFS vocabulary for students, courses and staff.", lang="en")))
    g.add((ONTO, DCTERMS.created, Literal("2025-01-15", datatype=XSD.date)))
    g.add((ONTO, OWL.versionInfo, Literal("1.0.0")))


def build_graph() -> Graph:
    g = Graph()
    g.bind("ex", EX)
    g.bind("rdfs", RDFS)
    g.bind("dcterms", DCTERMS)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    build_header(g)
    build_classes(g)
    build_properties(g)
    build_instances(g)
    return g


def print_summary(g: Graph) -> None:
    classes = list(g.subjects(RDF.type, RDFS.Class))
    props = list(g.subjects(RDF.type, RDF.Property))
    print(f"  classes    : {len(classes)}")
    print(f"  properties : {len(props)}")
    print(f"  triples    : {len(g)}")

    print("\n  Class hierarchy:")
    for cls in sorted(classes):
        parents = list(g.objects(cls, RDFS.subClassOf))
        parent_str = ", ".join(str(p).split("#")[-1] for p in parents) or "-"
        print(f"    {str(cls).split('#')[-1]:20s} ⊑ {parent_str}")


def main() -> None:
    graph = build_graph()
    print("สร้าง RDFS schema เรียบร้อย")
    print_summary(graph)

    if len(sys.argv) > 1:
        path = sys.argv[1]
        graph.serialize(destination=path, format="turtle")
        print(f"\nบันทึกลง {path}")
    else:
        print("\n" + "=" * 70)
        print(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
