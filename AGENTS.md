# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.
Read this before adding or editing any file. The decisions behind the rules are
recorded in the [ADR section](#architecture-decision-records-adr) at the bottom.

---

## 1. Project Overview

**Semantic Web & Linked Open Data with Python** is a Thai-language course
(12 chapters + appendix) on RDF, RDFS, OWL, SPARQL, SWRL, ontology design and
Linked Open Data, taught with Python.

| Item | Value |
| --- | --- |
| Content | Markdown chapters (`NN-name/NN.MM-topic.md`) |
| Runnable code | `code/chNN/*.py` |
| Notebooks | `code/chNN/chNN_notebook.ipynb` (one per chapter, Colab-openable) |
| Sample data | `data/`, `ontology/`, `shapes/` |
| Owner | Rathachai Chawuthai, KMITL |
| License | Course text **CC BY 4.0**, code **MIT** |
| Repo | https://github.com/Rathachai/semantic-web (default branch `main`) |

There is no build system and no web app. The "product" is the text, the code
that backs it, and the notebooks. "Tests" are: every script runs, every
notebook executes, every Turtle block parses.

---

## 2. Repository Layout

Chapters live at the **repo root**. Do not add a wrapper folder such as
`semantic-web-course/` or `docs/` (see ADR-003).

```
.
├── README.md / index.md        # course overview + chapter map + Colab badge table
├── AGENTS.md                   # this file
├── 01-introduction/ … 12-linked-open-data/
│       └── NN.01-*.md … NN.12-exercises.md     # 12 files per chapter
├── appendix/                   # A.01 … A.07 (cheat sheets, glossary, references)
├── code/ch01/ … ch12/          # scripts + chNN_notebook.ipynb
├── data/                       # small shared datasets (university.ttl, lod_dataset.ttl …)
├── ontology/                   # modular ontology + catalog-v001.xml (chapter 10)
└── shapes/                     # SHACL shapes (chapter 7)
```

### Chapter file pattern

Each chapter has 12 files, numbered `NN.01` … `NN.12`. The last three are
fixed roles:

| Position | File | Role |
| --- | --- | --- |
| `NN.10` | `*-python-*.md` | Full runnable Python with comments; companion file in `code/chNN/` |
| `NN.11` | `*-summary.md` | Adds a Mermaid **concept map** of the chapter |
| `NN.12` | `*-exercises.md` | 3–5 exercises as `### Exercise N: Title`, each with its **expected output** |

(Chapter 01 has 8 files; the appendix has 7. Follow the existing neighbours.)

---

## 3. Content Rules (every `.md` file)

1. Starts with a single `# Title` heading.
2. Followed by a short intro paragraph (2–3 sentences).
3. All key concepts explained in prose, not only in code.
4. At least one Mermaid diagram where a diagram helps (` ```mermaid `).
5. Code in fenced, language-tagged blocks: `turtle`, `python`, `sparql`, `json`, `bash`.
6. Ends with a `## Key Points` bullet list.
7. **No placeholder text.** Never write "TODO", "coming soon", "lorem ipsum".

### Language (ADR-001)

- Prose: **Thai**.
- Technical terms stay **English** (triple, entailment, reasoner, cardinality …).
- All data, code, URIs, labels, identifiers: **English**.
- Notebook headings and narration are Thai too; do not translate them.

### Turtle (ADR-002)

- Turtle is the default RDF format everywhere.
- **From chapter 02 onward, show Turtle in both forms** when a construct is
  introduced: a `# --- รูปแบบเต็ม ---` block (full IRIs / `rdf:type`) and a
  `# --- รูปแบบย่อ ---` block (prefixes, `a`, `;`, `,`). Use a side-by-side HTML
  table for comparisons.
- Turtle cannot put `/` in a prefixed name. Declare one prefix per path level
  (`crs:CS101`, not `uni:course/CS101`) — see ADR-007.

### Outputs must be real (ADR-004)

Any "ผลลัพธ์", "Expected output" or verified-output block must be copied from an
**actual run**. Run the script, paste what it printed. If the real output
disagrees with what you expected, fix the text and turn the discrepancy into a
teaching point; never edit the output to match the prose.

---

## 4. Code Rules

- Python 3.9+ (the course was verified on 3.9 / anaconda). Keep type hints
  compatible (`from __future__ import annotations` when using `X | Y`).
- Each script has a module docstring with purpose, requirements and a
  `python3 code/chNN/<file>.py` usage line, and runs standalone.
- Comments may be Thai; identifiers, strings in data, and URIs are English.
- Scripts that hit the network must tolerate failure and print a clear message
  (ADR-009). They must not hang: set explicit timeouts.
- Do not commit generated output other than the small, intentional artifacts
  already tracked (e.g. `code/ch12/dist/`, `code/ch11/hr_inferred.ttl`).
  `__pycache__/` must stay out of commits.

### Environment gotchas (verified; do not rediscover)

| Symptom | Cause | Rule |
| --- | --- | --- |
| `UnsupportedClassVersionError` from `sync_reasoner_pellet` | owlready2's bundled Jena jar targets a newer JDK | Call Pellet directly with `--loader OWLAPI` (`code/ch11/pellet_runner.py`) — ADR-006 |
| HermiT: "built-in atoms are not supported" | HermiT cannot run `swrlb:` builtins | HermiT for rules **without** builtins, Pellet for rules **with** them |
| SWRL rule silently does nothing; odd individual named `p` | Shared `default_world` reuses `swrl:Variable` across ontologies | One `World()` per ontology/demo |
| `differentFrom` never fires | OWL has no Unique Name Assumption | Declare `AllDifferent([...])` |
| HermiT `UnsupportedDatatypeException` | `xsd:date` is not in the OWL 2 datatype map | Use `xsd:dateTime` in ontologies fed to HermiT |
| owlrl cannot infer `minQualifiedCardinality` | OWL 2 RL forbids `minCardinality` in sub/superclass position | Use HermiT for those cases |
| `swrlb:substring` returns empty literal | XPath offset is **1-based** | Never pass offset 0 |
| Class count too high | Blank nodes counted as classes | Filter with `isinstance(c, URIRef)` |
| `defaultdict` metrics wrong | Reading a missing key creates it | Use `.get()`; compute averages before probing |
| `owlready2` cannot load `.ttl` | Only RDF/XML and N-Triples | Convert through rdflib first |
| Assigning a list to a `FunctionalProperty` fails | owlready2 uses a single-value setter | Assign one value, or demo inconsistency another way |
| SQWRL queries won't run in Python | `sqwrl:` needs SWRLAPI (Protégé SWRLTab) | Show SQWRL beside the equivalent SPARQL; label it Protégé-only |

Java 11+ is required for HermiT/Pellet/Fuseki.

---

## 5. Notebooks (ADR-008)

One notebook per chapter at `code/chNN/chNN_notebook.ipynb`.

- **Header** (in order): title cell with chapter name, Colab badge and
  Author/Affiliation/Updated-date block → license cell → `**References:**` cell →
  `---`. Style follows the author's reference notebook "A Quick Semantic
  Technology Tutorial". License cell is **CC BY 4.0** (+ MIT for code), *not* the
  reference notebook's BY-NC-SA.
- **Body**: fine-grained cells (mostly one statement per cell), Markdown
  sub-headings such as `## To Create Nodes`, show a value in its own cell
  before using it, a Setup cell with `!pip install -q …` first.
- **Footer**: `---`, closing cell pointing to the next chapter, repo link.
- **Data**: small RDF is an inline string in a cell. If a file is genuinely
  needed, link it by absolute `raw.githubusercontent.com/Rathachai/semantic-web/main/…`
  URL — never a relative path (Colab does not clone the repo).
- **Java**: notebooks using owlready2 reasoners include the Java check/install
  cell (`apt-get install openjdk-17-jre-headless` on Colab).
- **Executed**: commit notebooks **with real outputs**, run via
  `jupyter nbconvert --to notebook --execute --inplace <file>` and inspected for
  `output_type == "error"`.
- Cover the chapter's **core** concepts; they do not need to mirror every
  script in `code/chNN/`.
- When adding a notebook, add its badge row to the "Interactive Notebooks" table
  in `index.md`.

---

## 6. Verification Checklist

Run what applies before finishing a change.

```bash
# every Python script still runs
python3 code/ch02/create_graph.py

# Turtle files parse
python3 -c "from rdflib import Graph; g=Graph(); g.parse('data/lod_dataset.ttl', format='turtle'); print(len(g))"

# a notebook executes end to end
python3 -m jupyter nbconvert --to notebook --execute --inplace code/ch06/ch06_notebook.ipynb
```

- [ ] New/edited `.md` follows §3 (title, intro, diagram, code, Key Points)
- [ ] Turtle blocks parse (extract and load them with rdflib)
- [ ] Every "real output" block was produced by an actual run
- [ ] Relative links resolve (`../code/...`, `../NN-name/...`)
- [ ] Mermaid blocks use valid syntax (no unescaped quotes inside labels)
- [ ] Notebook has zero error outputs and the `index.md` badge row exists
- [ ] No personal data, credentials or API keys added
- [ ] Network-dependent code degrades gracefully

---

## 7. Do / Don't

**Do**
- Reuse standard vocabularies (schema.org, Dublin Core, SKOS, FOAF) in examples.
- Prefer OWL/SPARQL for a task; reach for SWRL only for arithmetic / string
  built-ins (it is a W3C *Member Submission*, not a Recommendation).
- Keep running examples consistent: University, Library, City/Open Data.
- State limitations honestly in the text (e.g. SQWRL is Protégé-only).

**Don't**
- Don't fabricate or hand-edit program output.
- Don't translate Thai prose to English (or vice-versa) without being asked.
- Don't add a `docs/` layer or an extra root folder around the chapters.
- Don't put URIs for real people, or personal data, in sample datasets.
- Don't publish anything to GitHub, Colab or any external service on your own;
  ask first. Pushing/merging is the owner's call.
- Don't hammer public endpoints; add delays and a descriptive `User-Agent`.

---

## Architecture Decision Records (ADR)

Format: *Context → Decision → Consequences*. Status is `Accepted` unless stated.
Add new records at the end with the next number; supersede rather than edit
history (mark the old one `Superseded by ADR-0NN`).

### ADR-001 — Thai prose, English technical terms and data

- **Context**: The audience is Thai students who will later read English
  specifications and use international tools and datasets.
- **Decision**: Explain in Thai; keep technical terms in English; write all
  data, code, URIs and labels in English.
- **Consequences**: Examples paste straight into Protégé/Fuseki/Wikidata with
  no translation; Thai-language labels appear only as deliberate multilingual
  examples (`@th`). Notebooks follow the same rule (the English-only request was
  withdrawn).

### ADR-002 — Turtle is the default format, shown full and shorthand

- **Context**: Learners find shorthand (`a`, `;`, `,`, prefixes) opaque unless
  they see what it expands to.
- **Decision**: Use Turtle throughout. From chapter 02, always pair the full
  form with the shorthand form when introducing a construct.
- **Consequences**: Longer files, but each shorthand is demonstrably equivalent
  (notebook 02 checks it with `rdflib.compare.isomorphic`). Other serialisations
  (RDF/XML, N-Triples, JSON-LD) are shown only where the topic requires them.

### ADR-003 — Flat repository layout, no wrapper or `docs/` folder

- **Context**: An early build nested chapters under `semantic-web-course/` and
  later `docs/`. The owner asked for both layers to be removed.
- **Decision**: Chapters, `appendix/`, `code/`, `data/` sit at the repo root.
- **Consequences**: Relative links use `../code/chNN/…` and `../NN-name/…`.
  Anything that assumes a `docs/` root (e.g. GitHub Pages config) must be
  adapted rather than the layout changed.

### ADR-004 — Every shown output is real

- **Context**: Early drafts contained plausible but invented "expected output"
  blocks; running the scripts showed several were wrong (e.g. class counts,
  average branching 0.57 vs 2.0).
- **Decision**: Run every script/notebook and paste actual output. Discrepancies
  become teaching notes ("an automatic checker flags suspects, it does not
  judge").
- **Consequences**: Slower authoring and outputs that depend on library
  versions or live endpoints (counts such as Wikidata's 252 labels may drift).
  When a live number changes, re-run and update it instead of leaving it stale.

### ADR-005 — Two reasoning tracks: owlrl (no Java) and owlready2 + HermiT (DL)

- **Context**: OWL 2 RL rule-based reasoning (owlrl) runs anywhere but is
  incomplete (no `minCardinality` in subclass/superclass position); HermiT is
  OWL 2 DL-complete but needs Java.
- **Decision**: Teach both. Default to owlrl for RDFS/RL demos and large data;
  use owlready2 + HermiT where DL entailment, consistency or unsatisfiability
  must be shown.
- **Consequences**: Courses/notebooks must state which track a demo uses and why
  results differ (CQ03 in chapter 10 needs HermiT). Colab needs a Java install
  cell for the DL track.

### ADR-006 — SWRL: Pellet invoked directly; HermiT only for builtin-free rules

- **Context**: `sync_reasoner_pellet` crashed with `UnsupportedClassVersionError`
  (bundled Jena jar built for a newer JDK); HermiT rejects `swrlb:` builtins;
  reusing `default_world` silently dropped `swrl:Variable` declarations.
- **Decision**: Run Pellet through `pellet.Pellet realize --loader OWLAPI` on a
  saved RDF/XML file (`code/ch11/pellet_runner.py`); use HermiT for rules with
  no builtins; give every demo its own `World()`.
- **Consequences**: Works on machines where the stock call fails, at the cost of
  parsing Pellet's text output (`PROPINST:` for object, `DATAPROPVAL:` for data
  properties) and the fact that `realize` lists only the most specific class.
  SQWRL is documented but not executed in Python.

### ADR-007 — Hash URIs for vocabulary, slash URIs for data; one prefix per path level

- **Context**: Linked Data needs dereferenceable, stable URIs; Turtle forbids
  `/` in prefixed names.
- **Decision**: Hash URIs for small fixed vocabularies, slash URIs for open-ended
  instance data (303 redirect to a document URI). Declare separate prefixes
  (`crs:`, `dept:`) instead of `ex:course/CS101`. URIs are ASCII, lowercase,
  with no file extensions or personal data; Thai names go in `rdfs:label @th`.
- **Consequences**: Prefix lists get longer; GeoNames IRIs ending in `/` must be
  written as full `<…>` IRIs.

### ADR-008 — One executed notebook per chapter, in the author's reference style

- **Context**: The owner asked for step-by-step, Colab-openable notebooks per
  chapter, styled after "A Quick Semantic Technology Tutorial". Converting all
  40+ scripts 1:1 would be large and repetitive.
- **Decision**: Build one notebook per chapter covering core concepts, small
  RDF inline, large files via absolute GitHub raw URLs, outputs captured by real
  execution, license set to CC BY 4.0 to match the README (not the reference
  notebook's BY-NC-SA). Notebook text stays Thai (ADR-001).
- **Consequences**: Colab badges and raw URLs point at `main`, so they only
  resolve after the content is pushed there. Scripts in `code/chNN/` remain the
  complete reference; notebooks are the guided path.

### ADR-009 — Public endpoints are optional, polite, and failure-tolerant

- **Context**: Wikidata/DBpedia endpoints rate-limit (HTTP 429), time out, and
  block anonymous clients; link checks produced false "dead link" results.
- **Decision**: Always send a descriptive `User-Agent`; set timeouts; prefer
  `Special:EntityData` and `wbsearchentities` over the Query Service for
  single-entity lookups; classify timeouts as "unreachable", never as "dead";
  wrap live demos in `try/except`.
- **Consequences**: Live demos can legitimately print a warning instead of data.
  Recommended production pattern is to download a dump and query locally
  (federated `SERVICE` is shown as exploratory only).

### ADR-010 — Modular ontology with `owl:imports` DAG and catalog file

- **Context**: Chapter 10 teaches modularisation and needs a checkable example.
- **Decision**: Ship `ontology/uni-core.ttl` plus academic/hr/library modules and
  `uni.ttl` importing them, resolved offline through `catalog-v001.xml`;
  verify no import cycles and no undeclared cross-module use
  (`code/ch10/check_modules.py`).
- **Consequences**: Loading `uni.ttl` yields the union of all modules (105
  triples at time of writing); changing module IRIs requires updating the
  catalog and the check script.

### ADR-011 — Dual licensing

- **Context**: The course is both teaching text and reusable code.
- **Decision**: Text under **CC BY 4.0**, code under **MIT** (stated in
  `README.md` and in each notebook). Datasets we publish use an explicit
  `dct:license` URI (CC BY 4.0 in the samples).
- **Consequences**: Third-party content must keep its own licence; do not merge
  CC BY-SA/ODbL data into samples without recording the share-alike impact
  (chapter 12.08).
