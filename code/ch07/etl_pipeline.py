"""
etl_pipeline.py
---------------
Chapter 07 companion script.

ETL pipeline เต็มรูปแบบ: CSV -> RDF -> validate -> reason -> load เข้า Fuseki -> query

  [1] EXTRACT   อ่าน CSV ด้วย pandas (สร้างไฟล์ตัวอย่างให้ถ้ายังไม่มี)
  [2] TRANSFORM แปลง DataFrame -> RDF ด้วย rdflib (จัดการ datatype, IRI, ค่าว่าง)
  [3] VALIDATE  ตรวจด้วย pySHACL ก่อนโหลด
  [4] ENRICH    รัน RDFS/OWL RL reasoning
  [5] LOAD      ส่งเข้า Fuseki ผ่าน Graph Store Protocol (ข้ามได้ถ้าไม่มี server)
  [6] QUERY     ตรวจผลด้วย SPARQL

Requirements:
    pip install pandas rdflib pyshacl owlrl requests

Usage:
    python etl_pipeline.py                        # รันทุกขั้น (ข้าม LOAD ถ้าไม่มี Fuseki)
    python etl_pipeline.py --fuseki http://localhost:3030/university
    python etl_pipeline.py --skip-load
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

HERE = Path(__file__).parent
CSV_PATH = HERE / "courses_enrollment.csv"
OUTPUT_TTL = HERE / "etl_output.ttl"
SHAPES_PATH = Path(__file__).resolve().parents[2] / "shapes" / "university-shapes.ttl"

EX = Namespace("http://example.org/etl#")
UNI = Namespace("http://example.org/university#")


def banner(step: str, title: str) -> None:
    print("\n" + "=" * 76)
    print(f"  [{step}] {title}")
    print("=" * 76)


# ---------------------------------------------------------------------------
# [1] EXTRACT
# ---------------------------------------------------------------------------

SAMPLE_CSV = """student_id,student_name,email,course_code,course_title,credits,term,grade,department
S-2024-0421,Alice Johnson,alice@example.edu,CS501,Knowledge Graphs,4,2024-2,A,Computer Science
S-2024-0421,Alice Johnson,alice@example.edu,CS601,Advanced Machine Learning,4,2024-2,A,Computer Science
S-2024-0512,Bob Martinez,bob@example.edu,CS101,Introduction to Programming,3,2024-1,B+,Computer Science
S-2024-0512,Bob Martinez,bob@example.edu,CS201,Data Structures,3,2024-2,B,Computer Science
S-2023-0198,Carol Nguyen,carol@example.edu,MA101,Calculus I,4,2024-1,A,Mathematics
S-2023-0198,Carol Nguyen,carol@example.edu,CS101,Introduction to Programming,3,2024-2,A-,Mathematics
S-2025-0033,Daniel Kim,,CS101,Introduction to Programming,3,2024-2,,Computer Science
S-2025-0044,Emma Wilson,emma@example.edu,CS301,Database Systems,3,2024-2,B+,Computer Science
"""


def extract(path: Path) -> pd.DataFrame:
    """อ่าน CSV; สร้างไฟล์ตัวอย่างถ้ายังไม่มี"""
    if not path.exists():
        path.write_text(SAMPLE_CSV, encoding="utf-8")
        print(f"  สร้างไฟล์ตัวอย่าง {path.name}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["credits"] = pd.to_numeric(df["credits"], errors="coerce")

    print(f"  อ่าน {path.name}: {len(df)} แถว, {len(df.columns)} คอลัมน์")
    print(f"  คอลัมน์: {list(df.columns)}")
    print(f"\n  นักศึกษาที่ไม่ซ้ำ : {df['student_id'].nunique()}")
    print(f"  รายวิชาที่ไม่ซ้ำ  : {df['course_code'].nunique()}")

    # ตรวจค่าว่าง
    empty = {c: (df[c] == "").sum() for c in df.columns if (df[c] == "").sum() > 0}
    if empty:
        print(f"  ⚠️ คอลัมน์ที่มีค่าว่าง: {empty}")
    return df


# ---------------------------------------------------------------------------
# [2] TRANSFORM
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """แปลงข้อความเป็นส่วนหนึ่งของ IRI ที่ปลอดภัย"""
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text.strip()).strip("-")


def transform(df: pd.DataFrame) -> Graph:
    """DataFrame -> RDF Graph"""
    g = Graph()
    g.bind("ex", EX)
    g.bind("uni", UNI)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    students, courses, departments = set(), set(), set()

    for _, row in df.iterrows():
        student = EX[f"student/{slugify(row['student_id'])}"]
        course = EX[f"course/{slugify(row['course_code'])}"]
        dept = EX[f"department/{slugify(row['department'])}"]
        enrollment = EX[f"enrollment/{slugify(row['student_id'])}-{slugify(row['course_code'])}"]

        # ----- student (เขียนครั้งเดียวต่อคน) -----
        if student not in students:
            students.add(student)
            g.add((student, RDF.type, UNI.Student))
            g.add((student, RDFS.label, Literal(row["student_name"], lang="en")))
            g.add((student, UNI.studentId, Literal(row["student_id"], datatype=XSD.string)))
            g.add((student, UNI.memberOf, dept))
            # ข้ามค่าว่าง -- อย่าสร้าง literal ว่างเปล่า
            if row["email"]:
                g.add((student, EX.email, Literal(row["email"], datatype=XSD.string)))

        # ----- course -----
        if course not in courses:
            courses.add(course)
            g.add((course, RDF.type, UNI.Course))
            g.add((course, RDFS.label, Literal(row["course_title"], lang="en")))
            g.add((course, UNI.courseCode, Literal(row["course_code"], datatype=XSD.string)))
            if pd.notna(row["credits"]):
                g.add((course, UNI.credits, Literal(int(row["credits"]), datatype=XSD.integer)))

        # ----- department -----
        if dept not in departments:
            departments.add(dept)
            g.add((dept, RDF.type, UNI.Department))
            g.add((dept, RDFS.label, Literal(row["department"], lang="en")))

        # ----- ความสัมพันธ์หลัก -----
        g.add((student, UNI.enrolledIn, course))

        # ----- n-ary relation: reify การลงทะเบียนเพื่อเก็บ term และ grade -----
        g.add((enrollment, RDF.type, EX.Enrollment))
        g.add((enrollment, EX.enrolledStudent, student))
        g.add((enrollment, EX.enrolledCourse, course))
        # ⚠️ ใช้ EX["term"] ไม่ใช่ EX.term -- "term" ชนกับ method Namespace.term() ของ rdflib
        g.add((enrollment, EX["term"], Literal(row["term"], datatype=XSD.string)))
        if row["grade"]:
            g.add((enrollment, EX.grade, Literal(row["grade"], datatype=XSD.string)))

    print(f"  สร้าง {len(g)} triples")
    print(f"    students    : {len(students)}")
    print(f"    courses     : {len(courses)}")
    print(f"    departments : {len(departments)}")
    return g


# ---------------------------------------------------------------------------
# [3] VALIDATE
# ---------------------------------------------------------------------------


def validate_graph(g: Graph, shapes_path: Path) -> bool:
    """ตรวจข้อมูลด้วย pySHACL"""
    try:
        from pyshacl import validate as shacl_validate
    except ImportError:
        print("  ข้าม: ไม่ได้ติดตั้ง pyshacl")
        return True

    if not shapes_path.exists():
        print(f"  ข้าม: ไม่พบ {shapes_path}")
        return True

    shapes = Graph().parse(shapes_path, format="turtle")
    conforms, _, text = shacl_validate(
        data_graph=g,
        shacl_graph=shapes,
        inference="rdfs",
        allow_warnings=True,
    )

    if conforms:
        print("  ✅ ข้อมูลผ่านการตรวจสอบ")
    else:
        print("  ❌ พบ violation:")
        for line in text.splitlines():
            if line.strip().startswith(("Focus Node", "Message", "Result Path")):
                print(f"     {line.strip()}")
    return conforms


# ---------------------------------------------------------------------------
# [4] ENRICH
# ---------------------------------------------------------------------------


def enrich(g: Graph, tbox_path: Optional[Path] = None) -> Graph:
    """เพิ่ม TBox แล้วรัน reasoning"""
    try:
        import owlrl
    except ImportError:
        print("  ข้าม: ไม่ได้ติดตั้ง owlrl")
        return g

    before = len(g)

    if tbox_path and tbox_path.exists():
        g.parse(tbox_path, format="turtle")
        print(f"  โหลด TBox: +{len(g) - before} triples")
        before = len(g)

    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(g)
    print(f"  หลัง RDFS reasoning: {len(g)} triples  (+{len(g) - before} inferred)")
    return g


# ---------------------------------------------------------------------------
# [5] LOAD
# ---------------------------------------------------------------------------


def load_to_fuseki(g: Graph, base_url: str, graph_iri: Optional[str] = None) -> bool:
    """ส่งข้อมูลเข้า Fuseki ผ่าน Graph Store Protocol"""
    try:
        import requests
    except ImportError:
        print("  ข้าม: ไม่ได้ติดตั้ง requests")
        return False

    data_url = f"{base_url.rstrip('/')}/data"
    params = {"graph": graph_iri} if graph_iri else {"default": ""}

    try:
        response = requests.put(
            data_url,
            params=params,
            data=g.serialize(format="turtle").encode("utf-8"),
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            timeout=30,
        )
        response.raise_for_status()
        print(f"  ✅ โหลดเข้า {data_url} สำเร็จ (HTTP {response.status_code})")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ โหลดไม่สำเร็จ: {exc}")
        print("     (ข้ามได้ — รัน Fuseki ด้วย ./fuseki-server --mem /university)")
        return False


# ---------------------------------------------------------------------------
# [6] QUERY
# ---------------------------------------------------------------------------

VERIFY_QUERIES = {
    "จำนวนนักศึกษา": """
        PREFIX uni: <http://example.org/university#>
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a uni:Student }
    """,
    "หน่วยกิตรวมต่อคน": """
        PREFIX uni:  <http://example.org/university#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?name (SUM(?cr) AS ?total) (COUNT(?c) AS ?courses)
        WHERE {
          ?s a uni:Student ; rdfs:label ?name ; uni:enrolledIn ?c .
          ?c uni:credits ?cr .
        }
        GROUP BY ?name ORDER BY DESC(?total)
    """,
    "เกรดต่อรายวิชา": """
        PREFIX ex:   <http://example.org/etl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?courseTitle ?grade (COUNT(*) AS ?n)
        WHERE {
          ?e a ex:Enrollment ; ex:enrolledCourse ?c ; ex:grade ?grade .
          ?c rdfs:label ?courseTitle .
        }
        GROUP BY ?courseTitle ?grade ORDER BY ?courseTitle
    """,
    "นักศึกษาที่ไม่มี email": """
        PREFIX uni:  <http://example.org/university#>
        PREFIX ex:   <http://example.org/etl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?name WHERE {
          ?s a uni:Student ; rdfs:label ?name .
          FILTER NOT EXISTS { ?s ex:email ?e }
        }
    """,
}


def verify(g: Graph) -> None:
    for title, query in VERIFY_QUERIES.items():
        print(f"\n  ▸ {title}")
        rows = list(g.query(query))
        if not rows:
            print("      (ไม่มีผลลัพธ์)")
            continue
        for row in rows:
            values = [str(v).split("#")[-1].split("/")[-1] if v else "—" for v in row]
            print("      " + "  |  ".join(values))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV -> RDF ETL pipeline")
    parser.add_argument("--fuseki", default="http://localhost:3030/university",
                        help="base URL ของ Fuseki dataset")
    parser.add_argument("--skip-load", action="store_true", help="ข้ามขั้นตอน LOAD")
    parser.add_argument("--graph", default="http://example.org/graph/enrollment",
                        help="named graph IRI ปลายทาง")
    args = parser.parse_args()

    banner("1/6", "EXTRACT — อ่าน CSV")
    df = extract(CSV_PATH)

    banner("2/6", "TRANSFORM — CSV -> RDF")
    graph = transform(df)
    graph.serialize(destination=str(OUTPUT_TTL), format="turtle")
    print(f"  บันทึก {OUTPUT_TTL.name}")

    banner("3/6", "VALIDATE — pySHACL")
    conforms = validate_graph(graph, SHAPES_PATH)
    if not conforms:
        print("\n  ⚠️ ข้อมูลไม่ผ่าน แต่จะทำต่อเพื่อสาธิต")
        print("     ใน production ควรหยุด pipeline ตรงนี้")

    banner("4/6", "ENRICH — RDFS reasoning")
    graph = enrich(graph)

    banner("5/6", "LOAD — Fuseki")
    if args.skip_load:
        print("  ข้ามตามที่ระบุ (--skip-load)")
    else:
        load_to_fuseki(graph, args.fuseki, args.graph)

    banner("6/6", "QUERY — ตรวจผลลัพธ์")
    verify(graph)

    print("\n" + "=" * 76)
    print(f"  เสร็จสิ้น — graph สุดท้ายมี {len(graph)} triples")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
