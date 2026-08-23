# A.06 อภิธานศัพท์ (Glossary)

หน้านี้รวมคำศัพท์เทคนิคที่ใช้ตลอดคอร์ส เรียงตามตัวอักษรภาษาอังกฤษ พร้อมคำอธิบายภาษาไทยสั้น ๆ และบทที่อธิบายละเอียด
ใช้เป็นพจนานุกรมด่วนเวลาเจอคำศัพท์ที่จำความหมายไม่ได้

---

## A

**ABox (Assertion Box)** — ส่วนของ knowledge base ที่เก็บข้อเท็จจริงเกี่ยวกับ individual เช่น `alice a Person` ตรงข้ามกับ TBox → [05](../05-knowledge-management/05.01-knowledge-base.md)

**ALC** — Description Logic พื้นฐานที่สุด (Attributive Language with Complement) → [04](../04-logics/04.01-why-logic.md)

**Anti-pattern** — รูปแบบการออกแบบ ontology ที่ดูเหมือนถูกแต่ก่อปัญหาในระยะยาว เช่น Class as Instance → [10.06](../10-ontology-design/10.06-anti-patterns.md)

**Axiom** — ประโยคตรรกะที่ยืนยันว่าเป็นจริงใน ontology เช่น `subClassOf`, `disjointWith`

## B

**Blank Node (BNode)** — node ที่ไม่มี URI อ้างอิงจากภายนอกไม่ได้ ใช้แทนโครงสร้างที่ไม่ต้องมีชื่อ → [02](../02-rdf/02.01-triple-model.md)

## C

**Cardinality Restriction** — ข้อจำกัดจำนวนค่าของ property เช่น `minCardinality`, `maxCardinality` → [08](../08-owl/08.01-owl-species.md)

**Closed World Assumption (CWA)** — สมมติฐานว่าสิ่งที่ไม่รู้ถือเป็นเท็จ ใช้ใน SHACL → [01](../01-introduction/01.04-key-concepts.md)

**Competency Question (CQ)** — คำถามตัวอย่างที่ ontology ต้องตอบได้ ใช้เป็นจุดเริ่มของการออกแบบ → [10.02](../10-ontology-design/10.02-competency-questions.md)

**Concise Bounded Description (CBD)** — triple ทั้งหมดที่ resource หนึ่งเป็น subject หรือ object → [12.10](../12-linked-open-data/12.10-python-lod.md)

**Content Negotiation** — กลไก HTTP ที่เลือกรูปแบบเอกสารตาม header `Accept` → [12.03](../12-linked-open-data/12.03-linked-data-principles.md)

**Cool URI** — URI ที่ออกแบบให้ไม่ต้องเปลี่ยนแปลงตลอดอายุการใช้งาน → [12.03](../12-linked-open-data/12.03-linked-data-principles.md)

## D

**DCAT (Data Catalog Vocabulary)** — vocabulary มาตรฐานสำหรับอธิบาย catalog ของ dataset → [09](../09-well-known-ontologies/09.05-prov-dcat-void.md), [12.06](../12-linked-open-data/12.06-open-gov-data.md)

**Description Logic (DL)** — ตระกูลตรรกะที่เป็นฐานของ OWL, decidable และมีความสามารถในการอนุมานพิสูจน์ได้ → [04](../04-logics/04.01-why-logic.md)

**DL-safe** — ข้อจำกัดของ SWRL ที่ตัวแปรต้อง bind กับ named individual เท่านั้น → [11.07](../11-swrl/11.07-swrl-owl-interaction.md)

**Dereference** — การเปิด URI เพื่อดึงข้อมูลที่อธิบายสิ่งนั้น → [12.09](../12-linked-open-data/12.09-consuming-lod.md)

## E

**Entailment** — ข้อสรุปที่ตามมาโดยตรรกะจาก axiom ที่มีอยู่ → [03](../03-rdfs/03.01-class-instance.md)

**Entity Linking** — กระบวนการหา URI ที่ตรงกันข้ามระบบ เพื่อสร้าง `owl:sameAs` → [12.09](../12-linked-open-data/12.09-consuming-lod.md)

## F

**First-Order Logic (FOL)** — ตรรกศาสตร์อันดับหนึ่ง พื้นฐานทางทฤษฎีของ Description Logic → [04](../04-logics/04.01-why-logic.md)

**FOAF (Friend of a Friend)** — vocabulary สำหรับอธิบายบุคคลและความสัมพันธ์ทางสังคม → [09](../09-well-known-ontologies/09.02-foaf.md)

## H

**Horn Clause** — ประโยคตรรกะรูปแบบ `body → head` ที่ SWRL ใช้ → [11.02](../11-swrl/11.02-rule-anatomy.md)

**Hash URI** — URI ที่ใช้ `#` คั่นส่วนท้าย เหมาะกับ vocabulary → [12.04](../12-linked-open-data/12.04-uri-design.md)

## I

**Inference** — กระบวนการอนุมานความรู้ใหม่จาก axiom และข้อเท็จจริงที่มีอยู่

**IRI (Internationalized Resource Identifier)** — รูปแบบขยายของ URI ที่รองรับอักขระ Unicode

## K

**Knowledge Graph (KG)** — กราฟความรู้ที่เชื่อม entity ด้วยความสัมพันธ์ที่มีความหมาย

## L

**Linked Data** — แนวปฏิบัติ 4 ข้อของ Tim Berners-Lee สำหรับเผยแพร่ข้อมูลที่เชื่อมโยงกันบนเว็บ → [12.03](../12-linked-open-data/12.03-linked-data-principles.md)

**LOD Cloud** — แผนภาพรวม dataset ของ Linked Open Data ทั่วโลก → [12.05](../12-linked-open-data/12.05-lod-cloud.md)

## M

**Manchester Syntax** — วิธีเขียน OWL axiom ให้อ่านเหมือนภาษาอังกฤษ เช่น `Class: Dog SubClassOf: Animal`

**METHONTOLOGY** — ระเบียบวิธีออกแบบ ontology แบบมีขั้นตอนชัดเจน → [10.01](../10-ontology-design/10.01-methodology.md)

**MIREOT** — เทคนิคดึงเฉพาะบางส่วนของ ontology ใหญ่มาใช้ → [10.07](../10-ontology-design/10.07-modularization.md)

## N

**Named Graph** — กราฟ RDF ที่มีชื่อ (URI) กำกับ ใช้แยกแหล่งที่มาของข้อมูล

## O

**ODP (Ontology Design Pattern)** — รูปแบบการออกแบบที่ใช้ซ้ำได้เพื่อแก้ปัญหาการสร้างแบบจำลองที่พบบ่อย → [10.05](../10-ontology-design/10.05-odp.md)

**Open World Assumption (OWA)** — สมมติฐานว่าสิ่งที่ไม่รู้ถือเป็น "ไม่รู้" ไม่ใช่ "เท็จ" — พื้นฐานของ RDF/OWL → [01](../01-introduction/01.04-key-concepts.md)

**OOPS!** — เครื่องมือออนไลน์ตรวจ pitfall ของ OWL ontology → [10.08](../10-ontology-design/10.08-evaluation.md)

**OWL (Web Ontology Language)** — ภาษามาตรฐานสำหรับนิยาม ontology ด้วยตรรกะเข้มงวด → [08](../08-owl/08.01-owl-species.md)

## P

**Property Chain** — การนิยาม property จากการต่อ property หลายตัวเข้าด้วยกัน (`owl:propertyChainAxiom`)

**Property Path** — ไวยากรณ์ SPARQL สำหรับเดินตาม property หลายขั้นในคำสั่งเดียว → [06](../06-sparql/06.01-sparql-intro.md)

**PROV-O** — vocabulary มาตรฐานสำหรับบันทึกที่มาของข้อมูล (provenance) → [09](../09-well-known-ontologies/09.05-prov-dcat-void.md)

**Punning** — การใช้ IRI เดียวเป็นทั้ง class และ individual ใน OWL 2 DL

## Q

**Qualified Cardinality** — ข้อจำกัดจำนวนค่าที่ระบุประเภทของค่านั้นด้วย เช่น `hasWheel exactly 4 Wheel`

## R

**RBox (Role Box)** — ส่วนของ knowledge base ที่เก็บ axiom เกี่ยวกับ property/role → [05](../05-knowledge-management/05.01-knowledge-base.md)

**Reasoner** — โปรแกรมที่คำนวณ entailment และตรวจ consistency ของ ontology เช่น HermiT, Pellet → [04](../04-logics/04.01-why-logic.md)

**RDF (Resource Description Framework)** — โมเดลข้อมูลพื้นฐานของ Semantic Web ในรูป subject-predicate-object → [02](../02-rdf/02.01-triple-model.md)

**RDFS (RDF Schema)** — ส่วนขยายของ RDF ที่เพิ่ม class hierarchy และ property → [03](../03-rdfs/03.01-class-instance.md)

## S

**SAMOD** — ระเบียบวิธีออกแบบ ontology แบบ agile ทำทีละส่วนเล็ก ๆ → [10.01](../10-ontology-design/10.01-methodology.md)

**SHACL (Shapes Constraint Language)** — ภาษาสำหรับตรวจความถูกต้องของข้อมูล RDF ยึด Closed World → [07](../07-python-semantic-web/07.01-ecosystem.md)

**skos:exactMatch / closeMatch** — predicate เชื่อมโยง concept ที่ผ่อนปรนกว่า `owl:sameAs` → [12.09](../12-linked-open-data/12.09-consuming-lod.md)

**Slash URI** — URI ที่ใช้ `/` แยกลำดับชั้น เหมาะกับข้อมูล instance → [12.04](../12-linked-open-data/12.04-uri-design.md)

**SPARQL** — ภาษา query มาตรฐานสำหรับ RDF → [06](../06-sparql/06.01-sparql-intro.md)

**SQWRL** — ส่วนขยายของ SWRL ที่เปลี่ยน rule ให้เป็น query → [11.06](../11-swrl/11.06-sqwrl.md)

**SROIQ** — Description Logic ที่ทรงพลังที่สุดที่ OWL 2 DL รองรับ → [04](../04-logics/04.01-why-logic.md)

**SWRL (Semantic Web Rule Language)** — ภาษากฎแบบ if-then ที่ทำงานร่วมกับ OWL → [11](../11-swrl/11.01-swrl-intro.md)

## T

**TBox (Terminology Box)** — ส่วนของ knowledge base ที่เก็บนิยาม class และ property → [05](../05-knowledge-management/05.01-knowledge-base.md)

**Triple** — หน่วยข้อมูลพื้นฐานของ RDF ในรูป subject-predicate-object → [02](../02-rdf/02.01-triple-model.md)

**Turtle** — รูปแบบไฟล์ข้อความสำหรับเขียน RDF ที่อ่านง่าย ใช้ตลอดคอร์สนี้ → [02](../02-rdf/02.01-triple-model.md)

## U

**Unsatisfiable Class** — class ที่ไม่มีทางมี instance ได้เลยเพราะขัดแย้งในตัวเอง → [10.08](../10-ontology-design/10.08-evaluation.md)

**Unique Name Assumption (UNA)** — สมมติฐานว่าชื่อต่างกันคือสิ่งต่างกัน — **OWL ไม่ยึดสมมติฐานนี้**

**URI (Uniform Resource Identifier)** — สตริงที่ใช้ระบุตัวตนของทรัพยากรอย่างไม่ซ้ำกัน

## V

**VoID (Vocabulary of Interlinked Datasets)** — vocabulary สำหรับอธิบายสถิติและลิงก์ของ dataset → [12.07](../12-linked-open-data/12.07-publishing-lod.md)

## W

**WebVOWL** — เครื่องมือออนไลน์วาด ontology เป็นแผนภาพ → [A.05](A.05-tools-setup.md)

**Wikidata** — knowledge base ที่แก้ไขร่วมกันได้ของมูลนิธิวิกิมีเดีย เป็น hub สำคัญของ LOD Cloud → [12.05](../12-linked-open-data/12.05-lod-cloud.md)

---

## Key Points

- คำศัพท์แบ่งกลุ่มหลักได้เป็น 4 กลุ่ม: **โมเดลข้อมูล** (RDF, Triple, IRI), **ตรรกะ** (DL, TBox/ABox/RBox, OWA/CWA), **เครื่องมือ** (Reasoner, SHACL, SPARQL), **การเผยแพร่** (URI design, VoID, DCAT, LOD)
- คำที่ผู้เรียนสับสนบ่อยที่สุด: **OWA vs CWA**, **TBox vs ABox**, **owl:sameAs vs skos:exactMatch**, **Hash URI vs Slash URI**
- แต่ละคำมีลิงก์ไปยังบทที่อธิบายละเอียด — ใช้หน้านี้เป็นจุดเริ่มค้นหา ไม่ใช่คำอธิบายฉบับเต็ม
