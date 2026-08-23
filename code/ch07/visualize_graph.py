"""
visualize_graph.py
------------------
Chapter 07 companion script.

แปลง RDF graph -> networkx -> pyvis เพื่อสร้างกราฟ interactive ในไฟล์ HTML
พร้อมวิเคราะห์โครงสร้างกราฟด้วย networkx (degree, centrality, component, path)

Requirements:
    pip install rdflib networkx pyvis

Usage:
    python visualize_graph.py                       # ใช้ data/university.ttl
    python visualize_graph.py path/to/graph.ttl
    python visualize_graph.py --no-literals         # ซ่อน literal node
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import networkx as nx
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "university.ttl"
OUTPUT_HTML = "graph.html"

# สีตามชนิดของ node
COLORS = {
    "class": "#a78bfa",       # ม่วง  -- rdfs:Class / owl:Class
    "property": "#fbbf24",    # เหลือง -- property
    "individual": "#60a5fa",  # ฟ้า   -- individual
    "literal": "#fde68a",     # ครีม  -- literal
    "bnode": "#d1d5db",       # เทา   -- blank node
}

# predicate ที่ไม่ต้องแสดงเป็นเส้น (รกเกินไป)
SKIP_PREDICATES = {
    RDF.first, RDF.rest,
    URIRef("http://www.w3.org/2002/07/owl#members"),
}


def short(term, graph: Graph) -> str:
    """ย่อ IRI เป็น prefixed name หรือคืนค่า literal"""
    if isinstance(term, Literal):
        text = str(term)
        return text if len(text) <= 40 else text[:37] + "…"
    if isinstance(term, BNode):
        return f"_:{str(term)[:8]}"
    try:
        return term.n3(graph.namespace_manager)
    except Exception:  # noqa: BLE001
        return str(term).split("#")[-1].split("/")[-1]


def node_kind(term, graph: Graph) -> str:
    """เดาว่า node นี้เป็นชนิดไหน เพื่อกำหนดสี"""
    if isinstance(term, Literal):
        return "literal"
    if isinstance(term, BNode):
        return "bnode"

    types = set(graph.objects(term, RDF.type))
    class_types = {
        RDFS.Class,
        URIRef("http://www.w3.org/2002/07/owl#Class"),
    }
    property_types = {
        RDF.Property,
        URIRef("http://www.w3.org/2002/07/owl#ObjectProperty"),
        URIRef("http://www.w3.org/2002/07/owl#DatatypeProperty"),
        URIRef("http://www.w3.org/2002/07/owl#AnnotationProperty"),
    }
    if types & class_types:
        return "class"
    if types & property_types:
        return "property"
    return "individual"


# ---------------------------------------------------------------------------
# 1) RDF -> networkx
# ---------------------------------------------------------------------------


def rdf_to_networkx(graph: Graph, include_literals: bool = True) -> nx.MultiDiGraph:
    """แปลง rdflib Graph เป็น networkx MultiDiGraph"""
    nx_graph = nx.MultiDiGraph()

    for subject, predicate, obj in graph:
        if predicate in SKIP_PREDICATES:
            continue
        if not include_literals and isinstance(obj, Literal):
            continue

        s_label = short(subject, graph)
        o_label = short(obj, graph)
        p_label = short(predicate, graph)

        nx_graph.add_node(s_label, kind=node_kind(subject, graph), iri=str(subject))
        nx_graph.add_node(o_label, kind=node_kind(obj, graph), iri=str(obj))
        nx_graph.add_edge(s_label, o_label, key=p_label, label=p_label)

    return nx_graph


# ---------------------------------------------------------------------------
# 2) วิเคราะห์โครงสร้างด้วย networkx
# ---------------------------------------------------------------------------


def analyse(nx_graph: nx.MultiDiGraph) -> None:
    """พิมพ์สถิติและ metric ของกราฟ"""
    print("\n" + "=" * 74)
    print("  โครงสร้างกราฟ")
    print("=" * 74)
    print(f"  nodes            : {nx_graph.number_of_nodes()}")
    print(f"  edges            : {nx_graph.number_of_edges()}")
    print(f"  density          : {nx.density(nx_graph):.4f}")

    undirected = nx_graph.to_undirected()
    components = list(nx.connected_components(undirected))
    print(f"  connected comps  : {len(components)}")
    if components:
        largest = max(components, key=len)
        print(f"  largest comp     : {len(largest)} nodes")

    # นับ node แต่ละชนิด
    kinds: Dict[str, int] = {}
    for _, data in nx_graph.nodes(data=True):
        kinds[data.get("kind", "?")] = kinds.get(data.get("kind", "?"), 0) + 1
    print("  node types       :", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))

    # --- degree ---
    print("\n  ▸ node ที่มีการเชื่อมต่อมากที่สุด (degree)")
    for node, degree in sorted(nx_graph.degree(), key=lambda x: -x[1])[:10]:
        kind = nx_graph.nodes[node].get("kind", "?")
        print(f"      {node:<38} {degree:>3}  ({kind})")

    # --- centrality (บน simple graph เพราะ MultiDiGraph บาง metric ใช้ไม่ได้) ---
    simple = nx.DiGraph(nx_graph)
    print("\n  ▸ betweenness centrality สูงสุด (node ที่เป็นสะพาน)")
    centrality = nx.betweenness_centrality(simple)
    for node, score in sorted(centrality.items(), key=lambda x: -x[1])[:5]:
        if score > 0:
            print(f"      {node:<38} {score:.4f}")

    print("\n  ▸ predicate ที่ใช้บ่อยที่สุด")
    predicate_count: Dict[str, int] = {}
    for _, _, key in nx_graph.edges(keys=True):
        predicate_count[key] = predicate_count.get(key, 0) + 1
    for predicate, count in sorted(predicate_count.items(), key=lambda x: -x[1])[:10]:
        print(f"      {predicate:<38} {count:>3}")


def find_path(nx_graph: nx.MultiDiGraph, source: str, target: str) -> None:
    """หาเส้นทางสั้นที่สุดระหว่างสอง node"""
    print("\n" + "=" * 74)
    print(f"  เส้นทางจาก {source} ไป {target}")
    print("=" * 74)
    undirected = nx_graph.to_undirected()
    if source not in undirected or target not in undirected:
        print("  (ไม่พบ node)")
        return
    try:
        path = nx.shortest_path(undirected, source, target)
        print("  " + "  →  ".join(path))
        print(f"  ({len(path) - 1} hop)")
    except nx.NetworkXNoPath:
        print("  (ไม่มีเส้นทางเชื่อมถึงกัน)")


# ---------------------------------------------------------------------------
# 3) networkx -> pyvis (interactive HTML)
# ---------------------------------------------------------------------------


def to_pyvis(nx_graph: nx.MultiDiGraph, output: str = OUTPUT_HTML) -> Optional[str]:
    """สร้างไฟล์ HTML ที่โต้ตอบได้"""
    try:
        from pyvis.network import Network
    except ImportError:
        print("\n  ⚠️ ไม่ได้ติดตั้ง pyvis — ข้ามการสร้าง HTML")
        return None

    net = Network(
        height="800px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#1f2937",
        notebook=False,
        cdn_resources="in_line",     # ฝัง JS ในไฟล์ ไม่ต้องต่อ internet
    )

    for node, data in nx_graph.nodes(data=True):
        kind = data.get("kind", "individual")
        net.add_node(
            node,
            label=node,
            title=f"{data.get('iri', node)}\n({kind})",
            color=COLORS.get(kind, "#9ca3af"),
            size=15 + min(nx_graph.degree(node), 20),
            shape="box" if kind == "literal" else "dot",
        )

    for source, target, key in nx_graph.edges(keys=True):
        net.add_edge(source, target, title=key, label=key, arrows="to")

    # physics ที่ทำให้กราฟจัดตัวสวย
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -60,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": { "iterations": 200 }
      },
      "edges": {
        "font": { "size": 10, "align": "middle" },
        "smooth": { "type": "continuous" }
      },
      "nodes": { "font": { "size": 14 } },
      "interaction": { "hover": true, "tooltipDelay": 100 }
    }
    """)

    net.save_graph(output)
    print(f"\n  ✅ บันทึก {output} — เปิดในเบราว์เซอร์เพื่อดูกราฟแบบโต้ตอบ")
    return output


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else DEFAULT_DATA
    include_literals = "--no-literals" not in sys.argv

    graph = Graph()
    graph.parse(path, format="turtle")
    print(f"โหลด {path.name}: {len(graph)} triples")
    print(f"literal nodes: {'แสดง' if include_literals else 'ซ่อน'}")

    nx_graph = rdf_to_networkx(graph, include_literals=include_literals)
    analyse(nx_graph)
    find_path(nx_graph, "uni:alice", "uni:exampleUniversity")
    to_pyvis(nx_graph)


if __name__ == "__main__":
    main()
