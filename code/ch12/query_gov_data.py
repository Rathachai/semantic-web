"""ค้นข้อมูลเปิดภาครัฐ -- CKAN API และ SPARQL endpoint

1. data.go.th   -- ศูนย์กลางข้อมูลเปิดภาครัฐไทย ใช้ CKAN (REST API)
2. data.europa.eu -- EU Open Data Portal ใช้ DCAT + SPARQL endpoint

รัน:  python3 code/ch12/query_gov_data.py
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = "SemanticWebCourse/1.0 (educational material)"
CKAN_TH = "https://data.go.th/api/3/action"
EU_SPARQL = "https://data.europa.eu/sparql"


def head(title: str) -> None:
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def sparql(endpoint: str, query: str, timeout: int = 60) -> list[dict[str, str]]:
    url = endpoint + "?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return [{k: v["value"] for k, v in row.items()}
            for row in data["results"]["bindings"]]


# ================================================== 1. CKAN (data.go.th)
def thai_open_data() -> None:
    """CKAN คือระบบ catalog ที่พอร์ทัลข้อมูลเปิดส่วนใหญ่ใช้"""
    head("1. data.go.th -- นับชุดข้อมูลและแยกตามรูปแบบไฟล์")

    facet = urllib.parse.quote('["res_format"]')
    data = get_json(f"{CKAN_TH}/package_search"
                    f"?rows=0&facet.field={facet}&facet.limit=12")
    result = data["result"]
    print(f"  จำนวนชุดข้อมูลทั้งหมด : {result['count']:,}")

    items = result["search_facets"]["res_format"]["items"]
    items.sort(key=lambda x: -x["count"])
    total = sum(i["count"] for i in items)

    print("\n  รูปแบบไฟล์ที่พบมากที่สุด:")
    print(f"  {'รูปแบบ':<10} {'จำนวน':>8}  {'สัดส่วน':>7}  ระดับดาว")
    print(f"  {'-' * 46}")
    stars = {"CSV": "⭐⭐⭐", "JSON": "⭐⭐⭐", "XML": "⭐⭐⭐", "API": "⭐⭐⭐",
             "RDF": "⭐⭐⭐⭐", "XLSX": "⭐⭐", "XLS": "⭐⭐", "XSL": "⭐⭐",
             "DOC": "⭐⭐", "PDF": "⭐", "IMAGE": "⭐", "ZIP": "?", "URL": "?"}
    for it in items:
        pct = 100 * it["count"] / total
        print(f"  {it['name']:<10} {it['count']:>8,}  {pct:>6.1f}%  "
              f"{stars.get(it['name'], '?')}")

    rdf = next((i["count"] for i in items if i["name"] == "RDF"), 0)
    print(f"\n  ⚠️ ทรัพยากรที่เป็น RDF (4 ดาวขึ้นไป) : {rdf:,} "
          f"= {100 * rdf / total:.1f}% ของทั้งหมด")


# ================================================== 2. SPARQL (EU)
def eu_open_data() -> None:
    """EU Open Data Portal เผยแพร่ catalog เป็น DCAT พร้อม SPARQL endpoint"""
    head("2. data.europa.eu -- catalog ที่เป็น Linked Data จริง")

    rows = sparql(EU_SPARQL, """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
SELECT (COUNT(*) AS ?n) WHERE { ?s a dcat:Dataset }""")
    print(f"  จำนวน dcat:Dataset : {int(rows[0]['n']):,}")

    rows = sparql(EU_SPARQL, """
PREFIX dcat: <http://www.w3.org/ns/dcat#>
SELECT ?f (COUNT(*) AS ?n) WHERE {
  ?d a dcat:Distribution ; dcat:mediaType ?f .
}
GROUP BY ?f
ORDER BY DESC(?n)
LIMIT 8""")
    print("\n  media type ที่พบมากที่สุด:")
    for r in rows:
        short = r["f"].rsplit("/media-types/", 1)[-1]
        print(f"    {int(r['n']):>9,}  {short}")

    print("\n  💡 ต่างจาก CKAN ตรงที่ catalog ทั้งชุดค้นด้วย SPARQL ได้")
    print("     ไม่ต้องเรียก REST API ทีละหน้าแล้วประกอบเอง")


if __name__ == "__main__":
    print("=" * 70)
    print("  ข้อมูลเปิดภาครัฐ -- CKAN REST API เทียบกับ DCAT + SPARQL")
    print("=" * 70)
    for fn in (thai_open_data, eu_open_data):
        try:
            fn()
        except Exception as exc:                   # noqa: BLE001
            print(f"\n  ⚠️ เรียกไม่สำเร็จ: {type(exc).__name__}: {exc}")
    print()
