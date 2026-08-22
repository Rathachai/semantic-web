"""
sparql_select.py
----------------
Chapter 06 companion script.

รัน SELECT query ทุกรูปแบบบน data/university.ttl:
  - SELECT พื้นฐาน
  - FILTER / OPTIONAL / UNION / MINUS / NOT EXISTS
  - ORDER BY / LIMIT / DISTINCT
  - COUNT / SUM / AVG / GROUP BY / HAVING / GROUP_CONCAT
  - subquery
  - property paths
  - แปลงผลลัพธ์เป็น pandas DataFrame

Requirements:
    pip install rdflib pandas

Usage:
    python sparql_select.py
    python sparql_select.py --only paths
"""

import sys
from pathlib import Path
from typing import Dict, List

from rdflib import Graph
from rdflib.query import Result

DATA = Path(__file__).resolve().parents[2] / "data" / "university.ttl"

PREFIXES = """
PREFIX uni:    <http://example.org/university#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX foaf:   <http://xmlns.com/foaf/0.1/>
PREFIX schema: <https://schema.org/>
"""


# ---------------------------------------------------------------------------
# ชุด query แบ่งตามหัวข้อ
# ---------------------------------------------------------------------------

QUERIES: Dict[str, Dict[str, str]] = {
    "basics": {
        "นักศึกษาทั้งหมด": """
            SELECT ?student ?name
            WHERE { ?student a uni:Student ; rdfs:label ?name . }
            ORDER BY ?name
        """,
        "รายวิชาพร้อมรหัสและหน่วยกิต": """
            SELECT ?code ?title ?credits
            WHERE {
              ?c uni:courseCode ?code ; rdfs:label ?title ; uni:credits ?credits .
            }
            ORDER BY ?code
        """,
        "ทุก property ของ alice": """
            SELECT ?p ?o WHERE { uni:alice ?p ?o . }
        """,
    },
    "filters": {
        "FILTER: GPA > 3.5": """
            SELECT ?name ?gpa
            WHERE { ?s a uni:Student ; rdfs:label ?name ; uni:gpa ?gpa .
                    FILTER(?gpa > 3.5) }
            ORDER BY DESC(?gpa)
        """,
        "OPTIONAL: เก็บคนที่ไม่มี GPA ไว้ด้วย": """
            SELECT ?name ?gpa
            WHERE { ?s a uni:Student ; rdfs:label ?name .
                    OPTIONAL { ?s uni:gpa ?gpa } }
            ORDER BY ?name
        """,
        "UNION: นักศึกษาและอาจารย์": """
            SELECT ?name ?role WHERE {
              { ?p a uni:Student ; rdfs:label ?name . BIND("student" AS ?role) }
              UNION
              { ?p a uni:Professor ; rdfs:label ?name . BIND("professor" AS ?role) }
            }
            ORDER BY ?role ?name
        """,
        "NOT EXISTS: วิชาที่ไม่มีคนสอน": """
            SELECT ?code ?title WHERE {
              ?c uni:courseCode ?code ; rdfs:label ?title .
              FILTER NOT EXISTS { ?prof uni:teaches ?c }
            }
            ORDER BY ?code
        """,
        "MINUS: นักศึกษาที่ไม่มี supervisor": """
            SELECT ?name WHERE {
              ?s a uni:Student ; rdfs:label ?name .
              MINUS { ?s uni:hasSupervisor ?sup }
            }
            ORDER BY ?name
        """,
        "REGEX: วิชาที่มีคำว่า programming": """
            SELECT ?title WHERE {
              ?c rdfs:label ?title .
              FILTER(REGEX(?title, "programming", "i"))
            }
        """,
    },
    "aggregates": {
        "COUNT: จำนวนวิชาที่แต่ละอาจารย์สอน": """
            SELECT ?profName (COUNT(?c) AS ?numCourses)
            WHERE { ?p uni:teaches ?c ; rdfs:label ?profName . }
            GROUP BY ?profName
            ORDER BY DESC(?numCourses)
        """,
        "GROUP_CONCAT: รายวิชาของแต่ละอาจารย์": """
            SELECT ?profName (GROUP_CONCAT(?code; SEPARATOR=", ") AS ?codes)
                             (COUNT(?c) AS ?n)
            WHERE {
              ?p uni:teaches ?c ; rdfs:label ?profName .
              ?c uni:courseCode ?code .
            }
            GROUP BY ?profName
            ORDER BY DESC(?n)
        """,
        "SUM: หน่วยกิตรวมของแต่ละคน": """
            SELECT ?name (SUM(?cr) AS ?totalCredits) (COUNT(?c) AS ?numCourses)
            WHERE {
              ?s a uni:Student ; rdfs:label ?name ; uni:enrolledIn ?c .
              ?c uni:credits ?cr .
            }
            GROUP BY ?name
            ORDER BY DESC(?totalCredits)
        """,
        "AVG/MIN/MAX: สถิติ GPA": """
            SELECT (COUNT(?s) AS ?n) (AVG(?g) AS ?avg)
                   (MIN(?g) AS ?min) (MAX(?g) AS ?max)
            WHERE { ?s a uni:Student ; uni:gpa ?g . }
        """,
        "HAVING: อาจารย์ที่สอนมากกว่า 2 วิชา": """
            SELECT ?profName (COUNT(?c) AS ?n)
            WHERE { ?p uni:teaches ?c ; rdfs:label ?profName . }
            GROUP BY ?profName
            HAVING(COUNT(?c) > 2)
        """,
        "จำนวนสมาชิกแต่ละภาควิชา": """
            SELECT ?deptName (COUNT(DISTINCT ?person) AS ?members)
            WHERE { ?person uni:memberOf ?d . ?d rdfs:label ?deptName . }
            GROUP BY ?deptName
            ORDER BY DESC(?members)
        """,
    },
    "subquery": {
        "นักศึกษาที่ GPA สูงสุด": """
            SELECT ?name ?gpa WHERE {
              ?s rdfs:label ?name ; uni:gpa ?gpa .
              { SELECT (MAX(?g) AS ?maxGpa) WHERE { ?x uni:gpa ?g } }
              FILTER(?gpa = ?maxGpa)
            }
        """,
        "top-2 GPA พร้อมรายวิชา": """
            SELECT ?name ?code WHERE {
              { SELECT ?s ?name WHERE {
                  ?s a uni:Student ; rdfs:label ?name ; uni:gpa ?g }
                ORDER BY DESC(?g) LIMIT 2 }
              ?s uni:enrolledIn ?c .
              ?c uni:courseCode ?code .
            }
            ORDER BY ?name ?code
        """,
    },
    "paths": {
        "partOf+ : csDept อยู่ใต้องค์กรอะไรบ้าง": """
            SELECT ?org WHERE { uni:csDept uni:partOf+ ?org . }
        """,
        "a/subClassOf* : ทุก Person โดยไม่ต้อง reason": """
            SELECT DISTINCT ?p WHERE { ?p a/rdfs:subClassOf* uni:Person . }
        """,
        "^enrolledIn : ใครลงเรียน cs101": """
            SELECT ?name WHERE { uni:cs101 ^uni:enrolledIn/rdfs:label ?name . }
        """,
        "memberOf/partOf* : คนกับองค์กรทุกระดับ": """
            SELECT ?personName ?orgName WHERE {
              ?p uni:memberOf/uni:partOf* ?org ; rdfs:label ?personName .
              ?org rdfs:label ?orgName .
            }
            ORDER BY ?personName ?orgName
        """,
        "enrolledIn/^enrolledIn : เพื่อนร่วมชั้นของ alice": """
            SELECT DISTINCT ?name WHERE {
              uni:alice uni:enrolledIn/^uni:enrolledIn ?mate .
              ?mate rdfs:label ?name .
              FILTER(?mate != uni:alice)
            }
        """,
        "subClassOf+ : superclass ของ Professor": """
            SELECT ?super WHERE { uni:Professor rdfs:subClassOf+ ?super . }
        """,
    },
}


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def short(term) -> str:
    """ย่อ IRI ให้อ่านง่าย"""
    if term is None:
        return "—"
    text = str(term)
    if text.startswith("http"):
        return text.split("#")[-1].split("/")[-1]
    return text


def print_result(result: Result, max_rows: int = 12) -> None:
    """พิมพ์ผลลัพธ์เป็นตารางง่าย ๆ"""
    variables = [str(v) for v in result.vars]
    rows = [[short(row[v]) for v in result.vars] for row in result]

    if not rows:
        print("    (ไม่มีผลลัพธ์)")
        return

    widths = [
        max(len(variables[i]), max(len(r[i]) for r in rows))
        for i in range(len(variables))
    ]
    header = "  ".join(v.ljust(widths[i]) for i, v in enumerate(variables))
    print(f"    {header}")
    print(f"    {'-' * len(header)}")
    for row in rows[:max_rows]:
        print("    " + "  ".join(row[i].ljust(widths[i]) for i in range(len(row))))
    if len(rows) > max_rows:
        print(f"    ... อีก {len(rows) - max_rows} แถว")
    print(f"    ({len(rows)} แถว)")


def to_dataframe(result: Result):
    """แปลงผลลัพธ์เป็น pandas DataFrame (ถ้ามี pandas)"""
    try:
        import pandas as pd
    except ImportError:
        return None
    return pd.DataFrame(
        [[short(row[v]) for v in result.vars] for row in result],
        columns=[str(v) for v in result.vars],
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def run_section(graph: Graph, section: str, queries: Dict[str, str]) -> None:
    print("\n" + "=" * 78)
    print(f"  {section.upper()}")
    print("=" * 78)
    for title, body in queries.items():
        print(f"\n  ▸ {title}")
        result = graph.query(PREFIXES + body)
        print_result(result)


def main() -> None:
    only: List[str] = []
    if "--only" in sys.argv:
        only = [sys.argv[sys.argv.index("--only") + 1]]

    graph = Graph()
    graph.parse(DATA, format="turtle")
    print(f"โหลด {DATA.name}: {len(graph)} triples")

    for section, queries in QUERIES.items():
        if only and section not in only:
            continue
        run_section(graph, section, queries)

    # --- ตัวอย่างแปลงเป็น DataFrame ---
    print("\n" + "=" * 78)
    print("  PANDAS DATAFRAME")
    print("=" * 78)
    df = to_dataframe(graph.query(PREFIXES + QUERIES["aggregates"]["SUM: หน่วยกิตรวมของแต่ละคน"]))
    if df is None:
        print("  (ไม่ได้ติดตั้ง pandas)")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
