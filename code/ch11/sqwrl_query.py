"""SQWRL: query ผ่าน rule -- เทียบกับ SPARQL ที่ให้ผลเดียวกัน

⚠️ SQWRL รันได้เฉพาะบน SWRLAPI (Protégé SWRLTab / Java) เท่านั้น
   Pellet CLI และ owlready2 ไม่รองรับ sqwrl: built-in

ไฟล์นี้จึงทำสองอย่าง
  1. แสดง SQWRL query ที่จะพิมพ์ลง Protégé SWRLTab
  2. รัน SPARQL ที่เทียบเท่าบน rdflib เพื่อยืนยันผลลัพธ์จริง

รัน:  python3 code/ch11/sqwrl_query.py
"""

from rdflib import Graph

DATA = """
@prefix uni:  <http://example.org/university#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

uni:alice a uni:Student ; rdfs:label "Alice"@en ;
    uni:gpa 3.80 ; uni:enrolledIn uni:cs501 , uni:cs502 , uni:cs503 ;
    uni:memberOf uni:csDept .
uni:bob a uni:Student ; rdfs:label "Bob"@en ;
    uni:gpa 2.10 ; uni:enrolledIn uni:cs501 ;
    uni:memberOf uni:csDept .
uni:carol a uni:Student ; rdfs:label "Carol"@en ;
    uni:gpa 3.20 ; uni:enrolledIn uni:cs501 , uni:cs502 ;
    uni:memberOf uni:mathDept .
uni:dave a uni:Student ; rdfs:label "Dave"@en ;
    uni:gpa 2.90 ; uni:enrolledIn uni:cs502 ;
    uni:memberOf uni:mathDept .

uni:cs501 a uni:Course ; rdfs:label "Advanced AI"@en ;      uni:credits 3 .
uni:cs502 a uni:Course ; rdfs:label "Machine Learning"@en ; uni:credits 4 .
uni:cs503 a uni:Course ; rdfs:label "Knowledge Graphs"@en ; uni:credits 3 .

uni:csDept   a uni:Department ; rdfs:label "Computer Science"@en .
uni:mathDept a uni:Department ; rdfs:label "Mathematics"@en .
"""

# (ชื่อ, SQWRL query, SPARQL ที่เทียบเท่า)
QUERIES = [
    (
        "1. เลือกและเรียงลำดับ",
        """Student(?s) ^ gpa(?s, ?g)
    -> sqwrl:select(?s, ?g) ^ sqwrl:orderByDescending(?g)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s ?g WHERE { ?s a uni:Student ; uni:gpa ?g }
        ORDER BY DESC(?g)
        """,
    ),
    (
        "2. กรองด้วย builtin",
        """Student(?s) ^ gpa(?s, ?g) ^ swrlb:greaterThan(?g, 3.0)
    -> sqwrl:select(?s, ?g)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s ?g WHERE { ?s a uni:Student ; uni:gpa ?g FILTER(?g > 3.0) }
        """,
    ),
    (
        "3. นับ (aggregate)",
        """Student(?s) ^ enrolledIn(?s, ?c)
    -> sqwrl:count(?c) ^ sqwrl:groupBy(?s) ^ sqwrl:columnNames("student", "courses")""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s (COUNT(?c) AS ?courses) WHERE { ?s uni:enrolledIn ?c }
        GROUP BY ?s ORDER BY DESC(?courses)
        """,
    ),
    (
        "4. ค่าเฉลี่ยต่อกลุ่ม",
        """Student(?s) ^ memberOf(?s, ?d) ^ gpa(?s, ?g)
    -> sqwrl:avg(?g) ^ sqwrl:groupBy(?d)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?d (AVG(?g) AS ?avgGpa) WHERE {
          ?s a uni:Student ; uni:memberOf ?d ; uni:gpa ?g .
        }
        GROUP BY ?d
        """,
    ),
    (
        "5. ค่าสูงสุด",
        """Student(?s) ^ gpa(?s, ?g) -> sqwrl:max(?g)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT (MAX(?g) AS ?maxGpa) WHERE { ?s a uni:Student ; uni:gpa ?g }
        """,
    ),
    (
        "6. เซตและการนับสมาชิกไม่ซ้ำ",
        """Student(?s) ^ enrolledIn(?s, ?c)
    -> sqwrl:makeSet(?set, ?c) ^ sqwrl:groupBy(?set, ?s)
       ^ sqwrl:size(?n, ?set) ^ sqwrl:select(?s, ?n)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s (COUNT(DISTINCT ?c) AS ?n) WHERE { ?s uni:enrolledIn ?c }
        GROUP BY ?s
        """,
    ),
    (
        "7. จำกัดจำนวนแถว",
        """Student(?s) ^ gpa(?s, ?g)
    -> sqwrl:select(?s, ?g) ^ sqwrl:orderByDescending(?g) ^ sqwrl:limit(2)""",
        """
        PREFIX uni: <http://example.org/university#>
        SELECT ?s ?g WHERE { ?s a uni:Student ; uni:gpa ?g }
        ORDER BY DESC(?g) LIMIT 2
        """,
    ),
]


def short(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def main() -> None:
    g = Graph().parse(data=DATA, format="turtle")
    print(f"  โหลดข้อมูล {len(g)} triples\n")

    for title, sqwrl, sparql in QUERIES:
        print("=" * 70)
        print(f"  {title}")
        print("=" * 70)
        print("  SQWRL (พิมพ์ลง Protégé SWRLTab):")
        for line in sqwrl.strip().splitlines():
            print(f"    {line}")

        print("\n  ผลลัพธ์ (รันด้วย SPARQL ที่เทียบเท่า):")
        for row in g.query(sparql):
            print("    " + "  ".join(f"{short(v):>18s}" for v in row))
        print()


if __name__ == "__main__":
    main()
