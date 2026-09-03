from __future__ import annotations

import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(REPO_ROOT, "evidence", "index.json")
DATASHEET_DIR = os.path.join(REPO_ROOT, "evidence", "datasheets")

#: Every document a claim in this repository rests on. `url` is where the
#: file came from; `document_id` is the revision the file itself states,
#: which is what a later reader has to match to know they are reading the
#: same thing.
SOURCES = {
    "usb_type_c": {
        "file": "datasheets/usb_type_c_r2_0.pdf",
        "url": "https://www.usb.org/sites/default/files/"
               "USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf",
        "retrieved": "2026-09-02",
        "document_id": "USB Type-C Cable and Connector Specification, "
                       "Release 2.0, August 2019",
        "applies_to": ["Type-C sink terminations", "Type-C source pull-ups",
                       "sink current advertisement thresholds"],
    },
    "ip5306_injoinic": {
        "file": "datasheets/ip5306_injoinic.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "309666add984eaea02a8f06d99102496.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Injoinic IP5306 fully-integrated power bank "
                       "system-on-chip, V1.10",
        "applies_to": ["IP5306"],
    },
    "dw01a_puolop": {
        "file": "datasheets/dw01a_puolop.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "0d2b2b5e8d1207bf276387cb4ff3a495.pdf",
        "retrieved": "2026-09-02",
        "document_id": "PUOLOP DW01A one-cell lithium battery protection "
                       "IC, Rev B, 2016-4-12",
        "applies_to": ["DW01A"],
    },
    "ao8810_aos": {
        "file": "datasheets/ao8810_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "26d8ed0c631e45aaacbd4f8082ccbf0c.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO8810 20V common-drain dual N-channel MOSFET, "
                       "Rev 8, October 2012",
        "applies_to": ["AO8810"],
    },
    "ao3415a_aos": {
        "file": "datasheets/ao3415a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "4fe5043a2c3149108be834737fd7b448.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO3415A -20V P-channel MOSFET, Rev 3.0, June 2013",
        "applies_to": ["AO3415A"],
    },
    "ao3400a_aos": {
        "file": "datasheets/ao3400a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "130876b936da464599428c58fd8de8f6.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO3400A Rev 3, December 2011",
        "applies_to": ["AO3400A"],
    },
    "ao3401a_aos": {
        "file": "datasheets/ao3401a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "fee353dd1e9e0bc90b295f14f381aa4c.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO3401A Rev 3.1, December 2023",
        "applies_to": ["AO3401A"],
    },
    "lm393_onsemi": {
        "file": "datasheets/lm393_onsemi.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "0a7f69005bd54ef2bf3e8b1a5a2f8965.pdf",
        "retrieved": "2026-09-02",
        "document_id": "onsemi LM393, LM393E, LM293, LM2903, LM2903E, "
                       "LM2903V, NCV2903 single supply dual comparators",
        "applies_to": ["LM393DR2G"],
    },
    "tlv431_ti": {
        "file": "datasheets/tlv431_ti.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "1f0b6b30afca4cb79b547decc5f49aec.pdf",
        "retrieved": "2026-09-02",
        "document_id": "TI TLV431, TLV431A, TLV431B low-voltage adjustable "
                       "precision shunt regulator, SLVS139V, revised "
                       "January 2015",
        "applies_to": ["TLV431AIDBZR"],
    },
    "swpa8040_sunlord": {
        "file": "datasheets/swpa8040_sunlord.pdf",
        "url": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/"
               "2310251551_Sunlord-SWPA8040S1R0NT_C96968.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Sunlord SMD power inductor catalogue, revised "
                       "2023/06/01",
        "applies_to": ["SWPA8040S1R0NT"],
    },
    "tpd1e10b06_ti": {
        "file": "datasheets/tpd1e10b06_ti.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "338eb197fbc247888eaf2230887550ac.pdf",
        "retrieved": "2026-09-02",
        "document_id": "TI TPD1E10B06 single-channel ESD protection diode, "
                       "SLLSEB1",
        "applies_to": ["TPD1E10B06DPYR"],
    },
    "usbc_hro": {
        "file": "datasheets/usbc_hro_type_c_31_m_12.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "9e56b777c022540fcce7c7f67825f55e.pdf",
        "retrieved": "2026-09-02",
        "document_id": "HRO Electronics TYPE-C-31-M-12 drawing, "
                       "2020.12.08",
        "applies_to": ["TYPE-C-31-M-12"],
    },
    "jst_vh": {
        "file": "datasheets/jst_vh_b2p.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "f2527f0a1a0b17e099f1e5ddd7cdf9f3.pdf",
        "retrieved": "2026-09-02",
        "document_id": "JST VH series 3.96 mm pitch connector drawing",
        "applies_to": ["B2P-VH(LF)(SN)"],
    },
    "ts1187a_xkb": {
        "file": "datasheets/ts1187a_xkb.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "56c8799ae5193945a16a1ffbe378246a.pdf",
        "retrieved": "2026-09-02",
        "document_id": "XKB TS-1187A-X-X-X tact switch drawing, rev A0",
        "applies_to": ["TS-1187A-B-A-B"],
    },
    "kt0603g_kento": {
        "file": "datasheets/kt0603g_kento.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "69e84a3abd84e5ab5856c47a2d0334ce.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Hubei KENTO KT-0603G specification",
        "applies_to": ["KT-0603G"],
    },
    "kt0603r_kento": {
        "file": "datasheets/kt0603r_kento.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "011ec3e8cb1e825f6961d29bc4db4c7a.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Hubei KENTO KT-0603R specification",
        "applies_to": ["KT-0603R"],
    },
    "mlcc_samsung_cl": {
        "file": "datasheets/mlcc_samsung_cl.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "02336ea48ea44ca18c72517dd3cb7b47.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Samsung Electro-Mechanics multilayer ceramic "
                       "capacitor catalogue",
        "applies_to": ["CL21A106KAYNNNE", "CL10A225KO8NNNC"],
    },
    "mlcc_cctc_1206": {
        "file": "datasheets/mlcc_cctc_1206.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "7c7c1f8fb8282eab2492065cbbfa1665.pdf",
        "retrieved": "2026-09-02",
        "document_id": "CCTC multilayer ceramic chip capacitor "
                       "specification",
        "applies_to": ["TCC1206X5R226M250HT"],
    },
    "mlcc_yageo_cc0603": {
        "file": "datasheets/mlcc_yageo_cc0603.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "23ccee80ee542e7cf156a772bb589942.pdf",
        "retrieved": "2026-09-02",
        "document_id": "YAGEO CC series 0603 MLCC specification",
        "applies_to": ["CC0603KRX7R9BB104"],
    },
    "res_0603_uniroyal": {
        "file": "datasheets/res_0603_uniroyal.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "0a975aaa49b7c97f38a963127be4a823.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Uniroyal 0603W chip resistor series specification",
        "applies_to": ["0603WAJ022JT5E", "0603WAF1000T5E",
                       "0603WAF1001T5E", "0603WAF1501T5E",
                       "0603WAF4701T5E", "0603WAF5101T5E",
                       "0603WAF1002T5E", "0603WAF1003T5E",
                       "0603WAF4703T5E", "0603WAF1004T5E"],
    },
}


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_index():
    entries = {}
    for name in sorted(SOURCES):
        source = SOURCES[name]
        path = os.path.join(REPO_ROOT, "evidence", source["file"])
        entry = dict(source)
        entry["sha256"] = digest(path)
        entry["bytes"] = os.path.getsize(path)
        entries[name] = entry
    return {"schema_version": 1, "documents": entries}


def load_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_index():
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(compute_index(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return INDEX_PATH


def verify():
    """Every recorded document present and unchanged, and nothing
    unrecorded."""
    recorded = load_index()["documents"]
    present = {name for name in os.listdir(DATASHEET_DIR)
               if name.endswith((".pdf", ".json"))}
    referenced = {os.path.basename(entry["file"])
                  for entry in recorded.values()}
    problems = []
    for name in sorted(referenced - present):
        problems.append(("missing_file", name))
    for name in sorted(present - referenced):
        problems.append(("unreferenced_file", name))
    for name in sorted(recorded):
        entry = recorded[name]
        path = os.path.join(REPO_ROOT, "evidence", entry["file"])
        if not os.path.isfile(path):
            continue
        if digest(path) != entry["sha256"]:
            problems.append(("digest_mismatch", name))
    return problems


if __name__ == "__main__":
    sys.stdout.write(write_index() + "\n")
