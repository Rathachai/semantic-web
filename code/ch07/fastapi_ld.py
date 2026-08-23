"""
fastapi_ld.py
-------------
Chapter 07 companion script.

ให้บริการ Linked Data ผ่าน FastAPI ตามหลัก Linked Data Principles:
  1. ทุก resource มี HTTP IRI
  2. dereference IRI แล้วได้ข้อมูลกลับมา
  3. รองรับ content negotiation (HTML / Turtle / JSON-LD / RDF-XML / N-Triples)
  4. มี link ไปยัง resource อื่น
  5. มี SPARQL endpoint

Endpoints:
  GET  /                          หน้าแรก + service description
  GET  /resource/{id}             dereference resource (content negotiation)
  GET  /data/{id}.{ext}           ดึงข้อมูลตรง format ที่ระบุ
  GET  /sparql?query=...          SPARQL endpoint (SELECT / CONSTRUCT / ASK)
  POST /sparql                    SPARQL endpoint (query ยาว)
  GET  /void                      VoID dataset description
  GET  /health                    health check

Requirements:
    pip install fastapi uvicorn rdflib

Usage:
    uvicorn fastapi_ld:app --reload --port 8000

    curl -H "Accept: text/turtle"        http://localhost:8000/resource/alice
    curl -H "Accept: application/ld+json" http://localhost:8000/resource/alice
    curl "http://localhost:8000/sparql?query=SELECT%20*%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%205"
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, VOID, XSD

# ---------------------------------------------------------------------------
# ตั้งค่า
# ---------------------------------------------------------------------------

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "university.ttl"
BASE_IRI = "http://example.org/university#"
UNI = Namespace(BASE_IRI)

app = FastAPI(
    title="University Linked Data Service",
    description="ตัวอย่างการให้บริการ Linked Data ด้วย FastAPI",
    version="1.0.0",
)

# โหลดกราฟครั้งเดียวตอน startup
GRAPH = Graph()
GRAPH.parse(DATA_PATH, format="turtle")
GRAPH.bind("uni", UNI)


# ---------------------------------------------------------------------------
# Content negotiation
# ---------------------------------------------------------------------------

# เรียงตามลำดับความสำคัญ: MIME type -> (rdflib format, นามสกุลไฟล์)
MIME_MAP: Dict[str, Tuple[str, str]] = {
    "text/turtle":            ("turtle", "ttl"),
    "application/x-turtle":   ("turtle", "ttl"),
    "application/ld+json":    ("json-ld", "jsonld"),
    "application/json":       ("json-ld", "jsonld"),
    "application/rdf+xml":    ("xml", "rdf"),
    "application/n-triples":  ("nt", "nt"),
    "text/n3":                ("n3", "n3"),
}

EXT_MAP: Dict[str, Tuple[str, str]] = {
    "ttl":    ("turtle", "text/turtle"),
    "jsonld": ("json-ld", "application/ld+json"),
    "rdf":    ("xml", "application/rdf+xml"),
    "xml":    ("xml", "application/rdf+xml"),
    "nt":     ("nt", "application/n-triples"),
    "n3":     ("n3", "text/n3"),
    "html":   ("html", "text/html"),
}


def parse_accept(header: str) -> list:
    """
    แยก Accept header เป็นรายการ (mime, q) เรียงตาม q จากมากไปน้อย
    ตัวอย่าง: "text/turtle;q=0.9, text/html" -> [("text/html",1.0), ("text/turtle",0.9)]
    """
    entries = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(";")
        mime = pieces[0].strip()
        quality = 1.0
        for piece in pieces[1:]:
            piece = piece.strip()
            if piece.startswith("q="):
                try:
                    quality = float(piece[2:])
                except ValueError:
                    quality = 1.0
        entries.append((mime, quality))
    return sorted(entries, key=lambda x: -x[1])


def negotiate(accept_header: Optional[str]) -> Tuple[str, str]:
    """
    เลือก format ที่ดีที่สุดจาก Accept header
    คืน (rdflib_format, content_type); "html" หมายถึงให้ render HTML
    """
    if not accept_header:
        return "turtle", "text/turtle"

    for mime, _ in parse_accept(accept_header):
        if mime in ("text/html", "application/xhtml+xml"):
            return "html", "text/html"
        if mime in MIME_MAP:
            fmt, _ext = MIME_MAP[mime]
            return fmt, mime
        if mime == "*/*":
            return "turtle", "text/turtle"

    # ไม่มีอะไรตรง -- default เป็น Turtle
    return "turtle", "text/turtle"


# ---------------------------------------------------------------------------
# ดึงข้อมูลของ resource
# ---------------------------------------------------------------------------


def describe(resource: URIRef) -> Graph:
    """
    สร้าง Concise Bounded Description แบบง่าย:
    triple ที่ resource เป็น subject + triple ที่เป็น object (inbound link)
    """
    result = Graph()
    for prefix, namespace in GRAPH.namespaces():
        result.bind(prefix, namespace)

    found = False
    for predicate, obj in GRAPH.predicate_objects(resource):
        result.add((resource, predicate, obj))
        found = True
        # ดึง label ของ object ที่เป็น IRI มาด้วย เพื่อให้ client แสดงผลได้
        if isinstance(obj, URIRef):
            for label in GRAPH.objects(obj, RDFS.label):
                result.add((obj, RDFS.label, label))

    for subject, predicate in GRAPH.subject_predicates(resource):
        result.add((subject, predicate, resource))
        found = True
        for label in GRAPH.objects(subject, RDFS.label):
            result.add((subject, RDFS.label, label))

    return result if found else Graph()


def render_html(resource: URIRef, graph: Graph) -> str:
    """สร้างหน้า HTML ที่มนุษย์อ่านได้ พร้อม link ไปยัง resource อื่น"""
    labels = list(GRAPH.objects(resource, RDFS.label))
    title = str(labels[0]) if labels else str(resource).split("#")[-1]

    def cell(term) -> str:
        if isinstance(term, URIRef):
            name = str(term).split("#")[-1].split("/")[-1]
            if str(term).startswith(BASE_IRI):
                return f'<a href="/resource/{quote(name)}">{name}</a>'
            return f'<a href="{term}" rel="external">{name}</a>'
        if isinstance(term, Literal):
            suffix = ""
            if term.language:
                suffix = f' <span class="tag">@{term.language}</span>'
            elif term.datatype:
                dt = str(term.datatype).split("#")[-1]
                suffix = f' <span class="tag">^^{dt}</span>'
            return f"{term}{suffix}"
        return str(term)

    outgoing = sorted(
        ((p, o) for s, p, o in graph if s == resource),
        key=lambda x: str(x[0]),
    )
    incoming = sorted(
        ((s, p) for s, p, o in graph if o == resource),
        key=lambda x: str(x[1]),
    )

    out_rows = "\n".join(
        f"<tr><td class='pred'>{cell(p)}</td><td>{cell(o)}</td></tr>"
        for p, o in outgoing
    )
    in_rows = "\n".join(
        f"<tr><td class='pred'>{cell(p)}</td><td>{cell(s)}</td></tr>"
        for s, p in incoming
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto;
         padding: 0 1rem; line-height: 1.5; color: #1f2937; }}
  h1 {{ margin-bottom: .25rem; }}
  .iri {{ color: #6b7280; font-family: ui-monospace, monospace; font-size: .85rem;
          word-break: break-all; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
  th, td {{ text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb;
            vertical-align: top; }}
  th {{ background: #f9fafb; }}
  .pred {{ width: 34%; font-family: ui-monospace, monospace; font-size: .9rem;
           color: #1e40af; }}
  .tag {{ color: #6b7280; font-size: .75rem; }}
  a {{ color: #1d4ed8; }}
  .formats a {{ margin-right: .75rem; font-size: .85rem; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <p class="iri">{resource}</p>

  <p class="formats">รูปแบบอื่น:
    <a href="/data/{str(resource).split('#')[-1]}.ttl">Turtle</a>
    <a href="/data/{str(resource).split('#')[-1]}.jsonld">JSON-LD</a>
    <a href="/data/{str(resource).split('#')[-1]}.rdf">RDF/XML</a>
    <a href="/data/{str(resource).split('#')[-1]}.nt">N-Triples</a>
  </p>

  <h2>Properties</h2>
  <table>
    <tr><th>Predicate</th><th>Object</th></tr>
    {out_rows or '<tr><td colspan="2">(ไม่มี)</td></tr>'}
  </table>

  <h2>Referenced by</h2>
  <table>
    <tr><th>Predicate</th><th>Subject</th></tr>
    {in_rows or '<tr><td colspan="2">(ไม่มี)</td></tr>'}
  </table>

  <p><a href="/">← กลับหน้าแรก</a></p>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """หน้าแรก: ลิสต์ resource ที่มี"""
    rows = []
    for cls in sorted({o for o in GRAPH.objects(None, RDF.type)}, key=str):
        if not str(cls).startswith(BASE_IRI):
            continue
        members = sorted(GRAPH.subjects(RDF.type, cls), key=str)
        if not members:
            continue
        links = " ".join(
            f'<a href="/resource/{str(m).split("#")[-1]}">{str(m).split("#")[-1]}</a>'
            for m in members[:12]
        )
        rows.append(
            f'<tr><td>{str(cls).split("#")[-1]}</td>'
            f"<td>{len(members)}</td><td>{links}</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>University Linked Data</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 950px; margin: 2rem auto;
        padding: 0 1rem; line-height: 1.5; }}
 table {{ border-collapse: collapse; width: 100%; }}
 th, td {{ text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb; }}
 th {{ background: #f9fafb; }}
 a {{ color: #1d4ed8; margin-right: .5rem; }}
 code {{ background: #f3f4f6; padding: .1rem .35rem; border-radius: 3px; }}
</style></head>
<body>
<h1>University Linked Data Service</h1>
<p>ข้อมูล {len(GRAPH):,} triples · <a href="/void">VoID description</a> ·
   <a href="/sparql?query=SELECT+*+WHERE+%7B%3Fs+%3Fp+%3Fo%7D+LIMIT+10">SPARQL endpoint</a></p>

<h2>Resources</h2>
<table><tr><th>Class</th><th>จำนวน</th><th>ตัวอย่าง</th></tr>
{''.join(rows)}
</table>

<h2>Content Negotiation</h2>
<pre><code>curl -H "Accept: text/turtle"         http://localhost:8000/resource/alice
curl -H "Accept: application/ld+json" http://localhost:8000/resource/alice
curl -H "Accept: text/html"           http://localhost:8000/resource/alice
curl http://localhost:8000/data/alice.ttl</code></pre>
</body></html>"""


@app.get("/resource/{identifier}")
def resource(identifier: str, request: Request) -> Response:
    """Dereference resource พร้อม content negotiation"""
    iri = URIRef(BASE_IRI + identifier)
    graph = describe(iri)

    if len(graph) == 0:
        raise HTTPException(status_code=404, detail=f"ไม่พบ resource: {identifier}")

    fmt, content_type = negotiate(request.headers.get("accept"))

    if fmt == "html":
        return HTMLResponse(render_html(iri, graph))

    return Response(
        content=graph.serialize(format=fmt),
        media_type=content_type,
        headers={"Vary": "Accept"},          # ⚠️ สำคัญสำหรับ cache
    )


@app.get("/data/{identifier}.{ext}")
def data(identifier: str, ext: str) -> Response:
    """ดึงข้อมูลตาม format ที่ระบุในนามสกุล (ไม่ต้องใช้ Accept header)"""
    if ext not in EXT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"ไม่รองรับนามสกุล .{ext} — รองรับ: {', '.join(EXT_MAP)}",
        )

    iri = URIRef(BASE_IRI + identifier)
    graph = describe(iri)
    if len(graph) == 0:
        raise HTTPException(status_code=404, detail=f"ไม่พบ resource: {identifier}")

    fmt, content_type = EXT_MAP[ext]
    if fmt == "html":
        return HTMLResponse(render_html(iri, graph))

    return Response(content=graph.serialize(format=fmt), media_type=content_type)


def run_sparql(query: str, accept: Optional[str]) -> Response:
    """รัน SPARQL query แล้วคืนผลตาม Accept header"""
    try:
        result = GRAPH.query(query)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"SPARQL error: {exc}") from exc

    accept = accept or ""

    # CONSTRUCT / DESCRIBE -> คืน graph
    if result.type in ("CONSTRUCT", "DESCRIBE"):
        fmt, content_type = negotiate(accept)
        if fmt == "html":
            fmt, content_type = "turtle", "text/turtle"
        return Response(content=result.graph.serialize(format=fmt),
                        media_type=content_type)

    # SELECT / ASK -> คืน SPARQL Results
    if "text/csv" in accept:
        return Response(content=result.serialize(format="csv"), media_type="text/csv")
    if "application/sparql-results+xml" in accept or "application/xml" in accept:
        return Response(content=result.serialize(format="xml"),
                        media_type="application/sparql-results+xml")

    return Response(content=result.serialize(format="json"),
                    media_type="application/sparql-results+json")


@app.get("/sparql")
def sparql_get(request: Request, query: str = Query(..., description="SPARQL query")) -> Response:
    return run_sparql(query, request.headers.get("accept"))


@app.post("/sparql")
async def sparql_post(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")
    body = (await request.body()).decode("utf-8")

    if "application/sparql-query" in content_type:
        query = body
    else:
        from urllib.parse import parse_qs
        parsed = parse_qs(body)
        if "query" not in parsed:
            raise HTTPException(status_code=400, detail="ไม่พบ parameter 'query'")
        query = parsed["query"][0]

    return run_sparql(query, request.headers.get("accept"))


@app.get("/void")
def void_description() -> Response:
    """VoID description ของ dataset"""
    g = Graph()
    g.bind("void", VOID)
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)

    dataset = URIRef("http://localhost:8000/void#dataset")
    g.add((dataset, RDF.type, VOID.Dataset))
    g.add((dataset, DCTERMS.title, Literal("University Linked Data", lang="en")))
    g.add((dataset, DCTERMS.description,
           Literal("Example dataset for the Semantic Web course.", lang="en")))
    g.add((dataset, DCTERMS.license,
           URIRef("https://creativecommons.org/licenses/by/4.0/")))
    g.add((dataset, VOID.sparqlEndpoint, URIRef("http://localhost:8000/sparql")))
    g.add((dataset, VOID.uriSpace, Literal(BASE_IRI)))
    g.add((dataset, VOID.triples, Literal(len(GRAPH), datatype=XSD.integer)))

    subjects = len(set(GRAPH.subjects()))
    predicates = len(set(GRAPH.predicates()))
    g.add((dataset, VOID.distinctSubjects, Literal(subjects, datatype=XSD.integer)))
    g.add((dataset, VOID.properties, Literal(predicates, datatype=XSD.integer)))

    for fmt in ("text/turtle", "application/ld+json", "application/rdf+xml"):
        g.add((dataset, VOID.feature, URIRef(f"http://www.w3.org/ns/formats/{fmt}")))

    return Response(content=g.serialize(format="turtle"), media_type="text/turtle")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "triples": len(GRAPH),
        "subjects": len(set(GRAPH.subjects())),
        "source": DATA_PATH.name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
