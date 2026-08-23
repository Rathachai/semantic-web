# A.04 Prefix Registry

หน้านี้รวบรวม prefix มาตรฐานทั้งหมดที่ใช้ตลอดคอร์สไว้ในที่เดียว เพื่อคัดลอกไปวางต้นไฟล์ Turtle หรือ SPARQL ได้ทันที
แบ่งเป็นกลุ่มตามหมวดหมู่การใช้งาน

---

## กลุ่มแกนของ RDF/OWL

| Prefix | Namespace URI | ใช้ทำอะไร |
| --- | --- | --- |
| `rdf` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | `rdf:type`, collection |
| `rdfs` | `http://www.w3.org/2000/01/rdf-schema#` | class hierarchy, label, comment |
| `owl` | `http://www.w3.org/2002/07/owl#` | ontology axiom |
| `xsd` | `http://www.w3.org/2001/XMLSchema#` | ชนิดข้อมูล literal |
| `shacl` / `sh` | `http://www.w3.org/ns/shacl#` | shape สำหรับตรวจข้อมูล |

```turtle
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
```

---

## กลุ่ม Vocabulary มาตรฐาน (บทที่ 9)

| Prefix | Namespace URI | ใช้ทำอะไร |
| --- | --- | --- |
| `dc` | `http://purl.org/dc/elements/1.1/` | Dublin Core (เวอร์ชันเก่า) |
| `dct` / `dcterms` | `http://purl.org/dc/terms/` | Dublin Core Terms |
| `foaf` | `http://xmlns.com/foaf/0.1/` | Friend of a Friend |
| `skos` | `http://www.w3.org/2004/02/skos/core#` | อนุกรมวิธาน/thesaurus |
| `schema` | `https://schema.org/` | schema.org |
| `prov` | `http://www.w3.org/ns/prov#` | ที่มาของข้อมูล |
| `dcat` | `http://www.w3.org/ns/dcat#` | catalog ของ dataset |
| `void` | `http://rdfs.org/ns/void#` | metadata ของ dataset |
| `time` | `http://www.w3.org/2006/time#` | เวลาและช่วงเวลา |
| `geo` | `http://www.w3.org/2003/01/geo/wgs84_pos#` | พิกัดภูมิศาสตร์ |
| `org` | `http://www.w3.org/ns/org#` | โครงสร้างองค์กร |
| `vcard` | `http://www.w3.org/2006/vcard/ns#` | ข้อมูลติดต่อ |

```turtle
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix foaf:   <http://xmlns.com/foaf/0.1/> .
@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <https://schema.org/> .
@prefix prov:   <http://www.w3.org/ns/prov#> .
@prefix dcat:   <http://www.w3.org/ns/dcat#> .
@prefix void:   <http://rdfs.org/ns/void#> .
```

---

## กลุ่ม SWRL (บทที่ 11)

| Prefix | Namespace URI | ใช้ทำอะไร |
| --- | --- | --- |
| `swrl` | `http://www.w3.org/2003/11/swrl#` | โครงสร้าง rule |
| `swrlb` | `http://www.w3.org/2003/11/swrlb#` | built-in function |
| `sqwrl` | `http://sqwrl.stanford.edu/ontologies/built-ins/3.4/sqwrl.owl#` | SQWRL query operator |
| `ruleml` | `http://www.w3.org/2003/11/ruleml#` | RuleML (พื้นฐานของ SWRL) |

---

## กลุ่ม Linked Open Data (บทที่ 12)

| Prefix | Namespace URI | ใช้ทำอะไร |
| --- | --- | --- |
| `wd` | `http://www.wikidata.org/entity/` | Wikidata item |
| `wdt` | `http://www.wikidata.org/prop/direct/` | Wikidata truthy statement |
| `p` / `ps` / `pq` | `http://www.wikidata.org/prop/` และ derivatives | Wikidata full statement |
| `wikibase` | `http://wikiba.se/ontology#` | Wikidata query service |
| `bd` | `http://www.bigdata.com/rdf#` | Blazegraph (ใช้ใน Wikidata) |
| `dbo` | `http://dbpedia.org/ontology/` | DBpedia ontology (mapped) |
| `dbp` | `http://dbpedia.org/property/` | DBpedia raw property |
| `dbr` | `http://dbpedia.org/resource/` | DBpedia resource |
| `gn` | `http://www.geonames.org/ontology#` | GeoNames ontology |
| `cc` | `http://creativecommons.org/ns#` | สัญญาอนุญาต Creative Commons |

```turtle
@prefix wd:  <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
@prefix dbo: <http://dbpedia.org/ontology/> .
@prefix dbr: <http://dbpedia.org/resource/> .
```

---

## เทมเพลตต้นไฟล์ครบชุด

```turtle
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:    <http://www.w3.org/2002/07/owl#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix foaf:   <http://xmlns.com/foaf/0.1/> .
@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <https://schema.org/> .
@prefix wd:     <http://www.wikidata.org/entity/> .
@prefix dbr:    <http://dbpedia.org/resource/> .
@prefix ex:     <http://example.org/> .
```

```python
# rdflib -- ผูก prefix ทั้งชุดเวลา serialize
from rdflib import Graph, Namespace

g = Graph()
g.bind("dct", "http://purl.org/dc/terms/")
g.bind("foaf", "http://xmlns.com/foaf/0.1/")
g.bind("skos", "http://www.w3.org/2004/02/skos/core#")
g.bind("schema", "https://schema.org/")
g.bind("wd", "http://www.wikidata.org/entity/")
g.bind("dbr", "http://dbpedia.org/resource/")
```

> 💡 **ค้นหา prefix ที่ยังไม่รู้จักได้ที่ [prefix.cc](https://prefix.cc/) และ [Linked Open Vocabularies (LOV)](https://lov.linkeddata.es/dataset/lov/)**

---

## Key Points

- แบ่ง prefix เป็น 4 กลุ่ม: **แกน RDF/OWL**, **vocabulary มาตรฐาน**, **SWRL**, **Linked Open Data**
- prefix ที่ใช้แทบทุกไฟล์ในคอร์ส: **`rdf`, `rdfs`, `owl`, `xsd`**
- **`dbo:` (mapped) ต่างจาก `dbp:` (raw)** ใน DBpedia — ใช้ `dbo:` เป็นหลัก
- **`wdt:` คือ truthy statement** ของ Wikidata ส่วน `p:`/`ps:`/`pq:` ใช้เข้าถึง qualifier และแหล่งอ้างอิง
- ค้นหา prefix ใหม่ได้จาก **prefix.cc** และ **Linked Open Vocabularies (LOV)**
