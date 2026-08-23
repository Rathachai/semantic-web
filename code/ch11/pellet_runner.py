"""เรียก Pellet โดยตรงผ่าน OWLAPI loader

ทำไมต้องมีไฟล์นี้
-----------------
`owlready2.sync_reasoner_pellet()` เรียก Pellet ด้วย `--loader Jena` ซึ่งบาง
environment จะพังด้วย `UnsupportedClassVersionError` เพราะ jena jar ที่มากับ
owlready2 ถูก compile ด้วย JDK ที่ใหม่กว่า Java ในเครื่อง

ทางแก้: บันทึกเป็น RDF/XML แล้วเรียก Pellet ด้วย `--loader OWLAPI` ซึ่งไม่แตะ
jena เลย -- SWRL builtin ทำงานได้ครบ

รัน:  python3 code/ch11/pellet_runner.py
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import tempfile

import owlready2

PELLET_DIR = os.path.join(os.path.dirname(owlready2.__file__), "pellet")


def _classpath() -> str:
    jars = sorted(glob.glob(os.path.join(PELLET_DIR, "*.jar")))
    return ":".join(jars + [PELLET_DIR])


def run_pellet(onto, infer_values: bool = True, timeout: int = 300) -> str:
    """รัน Pellet realize บน ontology แล้วคืน stdout ดิบ"""
    with tempfile.NamedTemporaryFile("wb", suffix=".owl", delete=False) as tmp:
        path = tmp.name
    onto.save(path, format="rdfxml")

    cmd = [owlready2.JAVA_EXE, "-Xmx2000M", "-cp", _classpath(),
           "pellet.Pellet", "realize", "--loader", "OWLAPI", "--ignore-imports"]
    if infer_values:
        cmd += ["--infer-prop-values", "--infer-data-prop-values"]
    cmd.append(path)

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    os.unlink(path)
    if proc.returncode != 0:
        raise RuntimeError(f"Pellet failed:\n{proc.stderr[:1500]}")
    return proc.stdout


# ----- parsing -----

_HIER = re.compile(r"^(\s*)(\S+)(?:\s+-\s+\((.+)\))?$")
_PROP = re.compile(r"^(?:DATAPROPVAL|PROPINST):\s+(\S+)\s+(\S+)\s+(.+)$")


def short(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1].strip("()")


def parse_realization(output: str) -> dict[str, list[str]]:
    """คืน {class_name: [individual, ...]} จากส่วน hierarchy ของ Pellet"""
    result: dict[str, list[str]] = {}
    for line in output.splitlines():
        if line.startswith(("DATAPROPVAL", "PROPINST")) or not line.strip():
            continue
        m = _HIER.match(line.rstrip())
        if not m or "http" not in line:
            continue
        _, cls, inds = m.groups()
        if inds:
            result[short(cls)] = [short(i) for i in inds.split(",")]
    return result


def parse_propvals(output: str) -> list[tuple[str, str, str]]:
    """คืน [(subject, property, value), ...]

    Pellet ใช้สองคำนำหน้าที่ต่างกัน
      DATAPROPVAL: สำหรับ data property   → ค่าเป็น literal(...)
      PROPINST:    สำหรับ object property → ค่าเป็น IRI
    """
    vals = []
    for line in output.splitlines():
        m = _PROP.match(line.strip())
        if not m:
            continue
        subj, prop, obj = m.groups()
        lit = re.match(r"literal\(([^,]+),", obj)
        vals.append((short(subj), short(prop), lit.group(1) if lit else short(obj)))
    return vals


# ==================== demo ====================

def _demo() -> None:
    from owlready2 import (DataProperty, FunctionalProperty, Imp, Thing,
                           get_ontology)

    onto = get_ontology("http://example.org/health#")
    with onto:
        class Patient(Thing):
            pass

        class Obese(Patient):
            pass

        class hasWeight(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        class hasHeight(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        class hasBMI(DataProperty, FunctionalProperty):
            domain = [Patient]
            range = [float]

        # BMI = weight / (height * height)
        r1 = Imp()
        r1.set_as_rule("Patient(?p), hasWeight(?p, ?w), hasHeight(?p, ?h), "
                       "multiply(?hh, ?h, ?h), divide(?bmi, ?w, ?hh) "
                       "-> hasBMI(?p, ?bmi)")

        r2 = Imp()
        r2.set_as_rule("Patient(?p), hasBMI(?p, ?b), greaterThan(?b, 30.0) "
                       "-> Obese(?p)")

        john = Patient("john")
        john.hasWeight, john.hasHeight = 95.0, 1.75
        mary = Patient("mary")
        mary.hasWeight, mary.hasHeight = 55.0, 1.65

    print("=" * 66)
    print("  PELLET (OWLAPI loader) -- SWRL builtins")
    print("=" * 66)
    out = run_pellet(onto)

    print("\n  Realization:")
    for cls, inds in parse_realization(out).items():
        print(f"    {cls:12s} → {inds}")

    print("\n  Inferred data property values:")
    for subj, prop, val in parse_propvals(out):
        if prop == "hasBMI":
            print(f"    {subj:6s} {prop} = {float(val):.2f}")


if __name__ == "__main__":
    _demo()
