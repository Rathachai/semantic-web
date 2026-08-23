"""SWRL use case จริง 3 โดเมน

1. Healthcare  -- แจ้งเตือนปฏิกิริยาระหว่างยา (drug-drug interaction)
2. Insurance   -- คำนวณเบี้ยประกันตามระดับความเสี่ยง
3. Smart Building -- ตัดสินใจเปิด/ปิดระบบปรับอากาศจากค่าเซนเซอร์

ทุกกรณีใช้ Pellet เพราะมี swrlb: builtin (HermiT ไม่รองรับ builtin)

รัน:  python3 code/ch11/usecase_rules.py
"""

from __future__ import annotations

import os
import sys

from owlready2 import (AllDifferent, DataProperty, FunctionalProperty, Imp,
                       ObjectProperty, Thing, World)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pellet_runner import parse_propvals, parse_realization, run_pellet  # noqa: E402


def head(title: str) -> None:
    print(f"\n{'=' * 66}\n  {title}\n{'=' * 66}")


def show(out: str, prop_filter: tuple[str, ...] = ()) -> None:
    realized = parse_realization(out)
    if realized:
        print("\n  Realization:")
        for cls, inds in sorted(realized.items()):
            print(f"    {cls:22s} → {inds}")
    vals = [v for v in parse_propvals(out) if not prop_filter or v[1] in prop_filter]
    if vals:
        print("\n  Inferred property values:")
        for subj, prop, val in sorted(vals):
            print(f"    {subj:12s} {prop:18s} = {val}")


# ================================================== 1. Healthcare
def healthcare() -> None:
    head("USE CASE 1 -- Drug-Drug Interaction Alert")
    onto = World().get_ontology("http://example.org/clinic#")
    with onto:
        class Patient(Thing):
            pass

        class Drug(Thing):
            pass

        class AtRiskPatient(Patient):
            pass

        class CriticalRiskPatient(AtRiskPatient):
            pass

        class takes(ObjectProperty):
            domain, range = [Patient], [Drug]

        class interactsWith(ObjectProperty):
            domain, range = [Drug], [Drug]
            # ปฏิกิริยาเป็นสองทางเสมอ
            python_name = "interactsWith"

        class hasAge(DataProperty, FunctionalProperty):
            range = [int]

        class riskScore(DataProperty, FunctionalProperty):
            range = [int]

        # กฎ 1: กินยา 2 ตัวที่ตีกัน → เสี่ยง
        r1 = Imp()
        r1.set_as_rule(
            "Patient(?p), takes(?p, ?d1), takes(?p, ?d2), "
            "interactsWith(?d1, ?d2), differentFrom(?d1, ?d2) "
            "-> AtRiskPatient(?p)")

        # กฎ 2: เสี่ยง + อายุเกิน 70 → ระดับวิกฤต
        r2 = Imp()
        r2.set_as_rule(
            "AtRiskPatient(?p), hasAge(?p, ?a), greaterThan(?a, 70) "
            "-> CriticalRiskPatient(?p)")

        warfarin, aspirin, vitaminC = Drug("warfarin"), Drug("aspirin"), Drug("vitaminC")
        # ประกาศทั้งสองทิศทาง เพราะ SWRL ไม่เติมทิศกลับให้เอง
        warfarin.interactsWith = [aspirin]
        aspirin.interactsWith = [warfarin]

        # ⚠️ จำเป็น! OWL ไม่มี Unique Name Assumption
        #    ถ้าไม่ประกาศ AllDifferent  differentFrom(?d1, ?d2) จะไม่เป็นจริงเลย
        #    และกฎที่ 1 จะเงียบ ๆ ไม่ทำงานโดยไม่มี error
        AllDifferent([warfarin, aspirin, vitaminC])

        somchai = Patient("somchai")
        somchai.takes = [warfarin, aspirin]
        somchai.hasAge = 75

        malee = Patient("malee")
        malee.takes = [warfarin, vitaminC]
        malee.hasAge = 68

        wichai = Patient("wichai")
        wichai.takes = [warfarin, aspirin]
        wichai.hasAge = 45

    print("  somchai: warfarin + aspirin, อายุ 75")
    print("  malee  : warfarin + vitaminC, อายุ 68")
    print("  wichai : warfarin + aspirin, อายุ 45")
    show(run_pellet(onto), ("__none__",))


# ================================================== 2. Insurance
def insurance() -> None:
    head("USE CASE 2 -- Insurance Premium Calculation")
    onto = World().get_ontology("http://example.org/insure#")
    with onto:
        class Policy(Thing):
            pass

        class LowRiskPolicy(Policy):
            pass

        class HighRiskPolicy(Policy):
            pass

        class baseAmount(DataProperty, FunctionalProperty):
            range = [float]

        class driverAge(DataProperty, FunctionalProperty):
            range = [int]

        class accidentCount(DataProperty, FunctionalProperty):
            range = [int]

        class riskMultiplier(DataProperty, FunctionalProperty):
            range = [float]

        class premium(DataProperty, FunctionalProperty):
            range = [float]

        # กฎ 1: ไม่เคยชน + อายุ 25-65 → ความเสี่ยงต่ำ ตัวคูณ 1.0
        r1 = Imp()
        r1.set_as_rule(
            "Policy(?p), accidentCount(?p, ?n), lessThan(?n, 1), "
            "driverAge(?p, ?a), greaterThan(?a, 24), lessThan(?a, 66) "
            "-> LowRiskPolicy(?p), riskMultiplier(?p, 1.0)")

        # กฎ 2: ชนตั้งแต่ 2 ครั้ง → ความเสี่ยงสูง ตัวคูณ 1.8
        r2 = Imp()
        r2.set_as_rule(
            "Policy(?p), accidentCount(?p, ?n), greaterThan(?n, 1) "
            "-> HighRiskPolicy(?p), riskMultiplier(?p, 1.8)")

        # กฎ 3: คนขับอายุน้อยกว่า 25 → ตัวคูณ 1.5
        r3 = Imp()
        r3.set_as_rule(
            "Policy(?p), driverAge(?p, ?a), lessThan(?a, 25) "
            "-> riskMultiplier(?p, 1.5)")

        # กฎ 4: เบี้ย = ฐาน x ตัวคูณ
        r4 = Imp()
        r4.set_as_rule(
            "Policy(?p), baseAmount(?p, ?b), riskMultiplier(?p, ?m), "
            "multiply(?prem, ?b, ?m) -> premium(?p, ?prem)")

        p1 = Policy("pol001")   # อายุ 40 ไม่เคยชน
        p1.baseAmount, p1.driverAge, p1.accidentCount = 10000.0, 40, 0
        p2 = Policy("pol002")   # อายุ 35 ชน 3 ครั้ง
        p2.baseAmount, p2.driverAge, p2.accidentCount = 10000.0, 35, 3
        p3 = Policy("pol003")   # อายุ 22 ไม่เคยชน
        p3.baseAmount, p3.driverAge, p3.accidentCount = 10000.0, 22, 0

    print("  pol001: ฐาน 10,000 อายุ 40 ชน 0 ครั้ง")
    print("  pol002: ฐาน 10,000 อายุ 35 ชน 3 ครั้ง")
    print("  pol003: ฐาน 10,000 อายุ 22 ชน 0 ครั้ง")
    show(run_pellet(onto), ("riskMultiplier", "premium"))


# ================================================== 3. Smart Building
def smart_building() -> None:
    head("USE CASE 3 -- Smart Building HVAC Control")
    onto = World().get_ontology("http://example.org/bldg#")
    with onto:
        class Room(Thing):
            pass

        class NeedsCooling(Room):
            pass

        class NeedsVentilation(Room):
            pass

        class EnergySaveMode(Room):
            pass

        class temperature(DataProperty, FunctionalProperty):
            range = [float]

        class co2Level(DataProperty, FunctionalProperty):
            range = [int]

        class occupancy(DataProperty, FunctionalProperty):
            range = [int]

        class comfortIndex(DataProperty, FunctionalProperty):
            range = [float]

        # กฎ 1: มีคน + ร้อนเกิน 26 → เปิดแอร์
        r1 = Imp()
        r1.set_as_rule(
            "Room(?r), occupancy(?r, ?o), greaterThan(?o, 0), "
            "temperature(?r, ?t), greaterThan(?t, 26.0) -> NeedsCooling(?r)")

        # กฎ 2: CO2 เกิน 1000 ppm → ต้องระบายอากาศ
        r2 = Imp()
        r2.set_as_rule(
            "Room(?r), co2Level(?r, ?c), greaterThan(?c, 1000) "
            "-> NeedsVentilation(?r)")

        # กฎ 3: ไม่มีคน → โหมดประหยัดพลังงาน
        r3 = Imp()
        r3.set_as_rule(
            "Room(?r), occupancy(?r, ?o), lessThan(?o, 1) -> EnergySaveMode(?r)")

        # กฎ 4: ดัชนีความสบาย = 100 - |t - 24| * 10
        r4 = Imp()
        r4.set_as_rule(
            "Room(?r), temperature(?r, ?t), subtract(?d, ?t, 24.0), "
            "abs(?ad, ?d), multiply(?pen, ?ad, 10.0), "
            "subtract(?ci, 100.0, ?pen) -> comfortIndex(?r, ?ci)")

        m1 = Room("meetingRoomA")   # ประชุมเต็ม อากาศร้อน CO2 สูง
        m1.temperature, m1.co2Level, m1.occupancy = 28.5, 1450, 12
        m2 = Room("officeB")        # สบาย
        m2.temperature, m2.co2Level, m2.occupancy = 24.0, 600, 5
        m3 = Room("storageC")       # ไม่มีคน
        m3.temperature, m3.co2Level, m3.occupancy = 30.0, 400, 0

    print("  meetingRoomA: 28.5°C, CO2 1450 ppm, 12 คน")
    print("  officeB     : 24.0°C, CO2  600 ppm,  5 คน")
    print("  storageC    : 30.0°C, CO2  400 ppm,  0 คน")
    show(run_pellet(onto), ("comfortIndex",))


if __name__ == "__main__":
    healthcare()
    insurance()
    smart_building()
    print()
