"""เซิร์ฟเวอร์ Linked Data ขนาดเล็กด้วย Flask

สาธิตหลักการ Linked Data ข้อ 2 และ 3 อย่างครบถ้วน
  * URI ของ "สิ่งของ"   → ตอบ 303 See Other
  * URI ของ "เอกสาร"    → ตอบ 200 พร้อมเนื้อหาตามรูปแบบที่ขอ
  * Content negotiation ตาม HTTP header Accept

รัน:      python3 code/ch12/flask_content_neg.py
ทดสอบ:   python3 code/ch12/flask_content_neg.py --test
"""

from __future__ import annotations

import os
import sys

from flask import Flask, Response, abort, redirect, request
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "lod_dataset.ttl")

BASE = "https://data.example.org/"
PORT = 5000

# Accept header → (นามสกุลไฟล์, media type, ชื่อ serializer ของ rdflib)
FORMATS: dict[str, tuple[str, str, str]] = {
    "text/turtle":            ("ttl",    "text/turtle",            "turtle"),
    "application/ld+json":    ("jsonld", "application/ld+json",    "json-ld"),
    "application/rdf+xml":    ("rdf",    "application/rdf+xml",    "xml"),
    "application/n-triples":  ("nt",     "application/n-triples",  "nt"),
    "text/html":              ("html",   "text/html; charset=utf-8", None),
}
EXT_TO_FORMAT = {ext: (media, ser) for _, (ext, media, ser) in FORMATS.items()}

app = Flask(__name__)
GRAPH = Graph()
GRAPH.parse(DATA, format="turtle")


def pick_format() -> tuple[str, str, str | None]:
    """เลือกรูปแบบจาก Accept header -- ปริยายเป็น HTML"""
    best = request.accept_mimetypes.best_match(list(FORMATS), default="text/html")
    return FORMATS[best]


def describe(iri: str) -> Graph:
    """คืน Concise Bounded Description ของ resource หนึ่งตัว

    CBD = triple ทั้งหมดที่ resource เป็น subject บวกกับ triple ที่เป็น object
    (ให้ผู้ใช้เห็นบริบทรอบตัวด้วย ไม่ใช่แค่ขาออก)
    """
    subj = URIRef(iri)
    out = Graph()
    for prefix, ns in GRAPH.namespaces():
        out.bind(prefix, ns)
    for triple in GRAPH.triples((subj, None, None)):
        out.add(triple)
    for triple in GRAPH.triples((None, None, subj)):
        out.add(triple)
    return out


# ---------------------------------------------------------------- routes
@app.route("/<path:kind>/<ident>")
def thing(kind: str, ident: str):
    """URI ของสิ่งของ -- ตอบ 303 เสมอ ไม่เคยตอบ 200

    นี่คือหัวใจ: 200 จะแปลว่า 'URI นี้คือเอกสารที่ส่งกลับไป'
    ซึ่งผิด เพราะมหาวิทยาลัยไม่ใช่ไฟล์
    """
    if kind.startswith("doc/"):
        abort(404)
    iri = f"{BASE}{kind}/{ident}"
    if (URIRef(iri), None, None) not in GRAPH:
        abort(404)
    ext, _, _ = pick_format()
    return redirect(f"/doc/{kind}/{ident}.{ext}", code=303)


@app.route("/doc/<path:kind>/<ident>.<ext>")
def document(kind: str, ident: str, ext: str):
    """URI ของเอกสาร -- ตอบ 200 พร้อมเนื้อหา"""
    if ext not in EXT_TO_FORMAT:
        abort(406)
    iri = f"{BASE}{kind}/{ident}"
    g = describe(iri)
    if not g:
        abort(404)

    media, serializer = EXT_TO_FORMAT[ext]
    if serializer is None:
        body = render_html(iri, g)
    else:
        body = g.serialize(format=serializer)

    resp = Response(body, mimetype=media.split(";")[0])
    # บอก client ว่าเอกสารนี้อธิบาย resource ตัวไหน
    resp.headers["Link"] = f'<{iri}>; rel="describedby"'
    resp.headers["Vary"] = "Accept"
    return resp


def render_html(iri: str, g: Graph) -> str:
    label = next((str(o) for o in g.objects(URIRef(iri), RDFS.label)), iri)
    rows = []
    for s, p, o in sorted(g, key=lambda t: str(t[1])):
        arrow = "→" if str(s) == iri else "←"
        other = o if str(s) == iri else s
        rows.append(f"<tr><td>{arrow}</td><td><code>{p}</code></td>"
                    f"<td>{other}</td></tr>")
    links = " | ".join(
        f'<a href="{iri.replace(BASE, "/doc/")}.{ext}">{ext}</a>'
        for ext in ("ttl", "jsonld", "rdf", "nt"))
    return f"""<!doctype html><meta charset="utf-8">
<title>{label}</title>
<h1>{label}</h1>
<p><b>URI:</b> <code>{iri}</code></p>
<p>รูปแบบอื่น: {links}</p>
<table border="1" cellpadding="4">{''.join(rows)}</table>"""


@app.route("/.well-known/void")
def void():
    """VoID description ที่ตำแหน่งมาตรฐาน"""
    path = os.path.join(HERE, "dist", "void.ttl")
    if not os.path.exists(path):
        abort(404, "รัน publish_lod.py ก่อนเพื่อสร้าง void.ttl")
    with open(path, encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/turtle")


# ---------------------------------------------------------------- test
def self_test() -> None:
    """ทดสอบด้วย Flask test client -- ไม่ต้องเปิด server จริง"""
    print("=" * 68)
    print("  ทดสอบ content negotiation ด้วย Flask test client")
    print("=" * 68)
    print(f"\n  โหลดข้อมูล {len(GRAPH)} triples จาก {os.path.basename(DATA)}\n")

    client = app.test_client()
    cases = [
        ("/university/chula", "text/turtle"),
        ("/university/chula", "application/ld+json"),
        ("/university/chula", "text/html"),
        ("/place/bangkok",    "application/rdf+xml"),
        ("/university/nope",  "text/turtle"),
    ]
    print(f"  {'request':<24s} {'Accept':<24s} {'status':>6s}  Location")
    print(f"  {'-' * 88}")
    for path, accept in cases:
        r = client.get(path, headers={"Accept": accept})
        loc = r.headers.get("Location", "-")
        print(f"  {path:<24s} {accept:<24s} {r.status_code:>6d}  {loc}")

    print("\n  ตามลิงก์ 303 ต่อไปยังเอกสารจริง:")
    for accept, ext in [("text/turtle", "ttl"), ("application/ld+json", "jsonld")]:
        r = client.get(f"/doc/university/chula.{ext}", headers={"Accept": accept})
        body = r.get_data(as_text=True)
        print(f"\n  --- /doc/university/chula.{ext} → {r.status_code} "
              f"{r.headers.get('Content-Type')} ({len(body)} bytes) ---")
        for line in body.splitlines()[:6]:
            print(f"    {line}")

    r = client.get("/doc/university/chula.ttl")
    print(f"\n  HTTP header ที่สำคัญ:")
    for h in ("Content-Type", "Link", "Vary"):
        print(f"    {h:<14s} {r.headers.get(h)}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        print(f"เปิดที่ http://localhost:{PORT}/university/chula")
        app.run(port=PORT, debug=False)
