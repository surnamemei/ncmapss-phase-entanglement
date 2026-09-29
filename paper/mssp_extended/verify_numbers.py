"""Re-derive every number cited in the extended MSSP manuscript and enforce its wording rules.

Sources (read only; no N-CMAPSS data are read):
- Extension outputs: results/extension/ (protocol docs/extension/GENERALIZATION_PROTOCOL.md v1.0 with
  Amendments 1-3), certified by docs/extension/EXTENSION_EVIDENCE_LEDGER.csv. Every source file used
  here that the ledger names must still have the SHA-256 the ledger recorded.
- Frozen DS02/DS03 numbers: paper/manuscript_core_results.csv (display values) and the committed
  pre-extension MSSP text paper/mssp/manuscript_mssp_draft.md.

Checks:
1. Forward: each claim is rebuilt from the outputs and must appear verbatim in the draft.
2. Reverse: every decimal or percentage in the abstract, highlights and Sections 4-6 is a re-derived
   value, a frozen value or a design constant.
3. Wording: forbidden terms, abstract length, highlight count and length, keyword count, required terms.
4. Citations: every cited key has a verified spec entry and every spec entry is cited.
5. Ledger registry: every cited claim, table and figure has a row in the final evidence ledger
   (docs/extension/EXTENSION_EVIDENCE_LEDGER.csv) with the same claim text, displayed value(s), source file(s)
   and source hash. `--register` appends missing rows (append-only; existing rows are never changed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "paper/mssp_extended"
DRAFT = PKG / "manuscript_mssp_draft.md"
EXT = ROOT / "results/extension"
SUM = EXT / "summary"
LEDGER = ROOT / "docs/extension/EXTENSION_EVIDENCE_LEDGER.csv"
CORE = ROOT / "paper/manuscript_core_results.csv"
PRE_TEXT = ROOT / "paper/mssp/manuscript_mssp_draft.md"
SPEC = PKG / "references_spec.json"
NEW = ("DS01", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c")
FAMILY = {"DS01": "F1", "DS04": "F2", "DS05": "F3", "DS06": "F3", "DS07": "F3", "DS08a": "F4", "DS08c": "F5"}
ALPHA = 0.01
MINUS = "−"
WORDS = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}
ABSTRACT_WORDS = (200, 245)
HIGHLIGHTS = (3, 5)
HIGHLIGHT_CHARS = 85
KEYWORDS = (1, 7)
FORBIDDEN = ("pre-registered", "preregistered", "preregistration", "[ref:", "to verify]", "online", "causal regime",
             "causal-regime", "causal lstm", "causal arm", "non-inferior", "eliminates", "eliminate ", "deployment-ready",
             "fault sensitivity", "fault recall", "fault-state", "fault state", "independent confirmatory",
             "independent confirmation", "stabiliz", "robust", "mitigation", "limiting factor", "significant",
             "significance", "universal", "fault-tolerant", "for the first time", "first to", "novel framework",
             "proves ", "proven ", "{{", "}}", "[author to", "todo", "tbd", "xx ", "we propose a", "state-of-the-art")
REQUIRED = ("abnormal-state ($hs = 0$)", "past-only long short-term memory", "retrospective phase-conditioned",
            "healthy flights with any alarm", "between-phase disparity", "nominal calibration error",
            "pre-specified", "not a proposed method", "five top-level units", "no deployment claim",
            "### 4.9 Other post hoc checks", "### 4.8 Final focused validation (post hoc)", "were not pre-specified",
            "not registered externally")
CONSTANTS = {"0.5%", "1%", "2%", "2.5%", "5%", "10%", "15%", "20%", "0.5", "0.95", "90%", "0.5α"}


def pp(value, digits=2):
    return f"{100 * value:.{digits}f}"


def signed(value, digits=2):
    text = f"{100 * value:+.{digits}f}"
    return text.replace("-", MINUS).lstrip("+")


def pct(value, digits=0):
    return f"{100 * value:.{digits}f}%"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Sources:
    """Reads outputs and remembers which files were used, for the ledger hash check."""

    def __init__(self):
        self.used = set()

    def csv(self, path):
        self.used.add(Path(path))
        return pd.read_csv(path, float_precision="round_trip")

    def json(self, path):
        self.used.add(Path(path))
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def audit(self, key, table):
        frame = self.csv(EXT / key / "audit" / f"{table}.csv")
        return frame.assign(subset=key) if "subset" not in frame else frame


REGISTRY = []  # one entry per cited claim: text, displayed numbers, principal source(s), evidence category
_CONTEXT = {"source": None, "category": None}


def at(source, category):
    """Set the source file(s) and evidence category for the claims that follow."""
    _CONTEXT["source"], _CONTEXT["category"] = source, category


def register(text, numbers):
    if _CONTEXT["source"] is None:
        raise RuntimeError(f"claim without a source: {text!r}")
    REGISTRY.append({"text": text, "numbers": [str(n) for n in numbers], "source": _CONTEXT["source"],
                     "category": _CONTEXT["category"]})


def derive(src):
    """Return (claims, values): claims are phrases that must appear verbatim; values feed the reverse check."""
    claims, values = [], set()

    def claim(text, *numbers):
        claims.append(text)
        values.update(numbers)
        register(text, numbers)

    dec = src.json(SUM / "decisions.json")
    assert dec["alpha"] == ALPHA
    at(SUM / "decisions.json", "pre-specified")

    # H1 and pooled calibration (Section 4.2)
    h1 = dec["H1"]
    means = h1["subset_family_means_pooled_A2_P"]
    holding = [k for k in NEW if h1["subset_holds"][k]]
    assert holding == ["DS05", "DS06", "DS08a", "DS08c"] and h1["families_holding"] == 3 and h1["verdict"] == "SUPPORTED"
    claim("in DS05, DS06, DS08a and DS08c, which is three of five families")
    for key, det, label in (("DS01", "lstm_autoencoder", "LSTM"), ("DS04", "pca", "PCA"), ("DS07", "lstm_autoencoder", "LSTM")):
        value = means[key][det]
        assert value < 0.5 * ALPHA and not h1["subset_holds"][key]
        claim(f"{label} pooled A2 {pp(value)} pp" if key == "DS01" else f"{key} ({label} {pp(value)} pp)", pp(value))
    order = src.csv(SUM / "phase_ordering_pooled.csv")
    at(SUM / "phase_ordering_pooled.csv", "descriptive")
    counts = {k: order[order.subset == k].highest_phase.value_counts().to_dict() for k in NEW}
    assert counts["DS01"].get("descent") == 10 and counts["DS07"].get("descent") == 10
    assert all(counts[k].get("descent") == 9 for k in ("DS04", "DS05", "DS06"))
    claim("Descent was the highest phase under P in 10 of 10 runs in DS01 and DS07 and in 9 of 10 in DS04, DS05 and DS06")
    assert counts["DS08a"].get("cruise") == 5 and counts["DS08c"].get("climb") == 5 and counts["DS08c"].get("descent") == 5
    claim("cruise led in 5 of 10 runs in DS08a, and climb and descent split 5 and 5 in DS08c")
    ts = src.csv(SUM / "transport_summary_alpha_0.01.csv")
    at(SUM / "transport_summary_alpha_0.01.csv", "descriptive")
    d08c = ts[(ts.subset == "DS08c") & (ts.arm == "pooled")][["pooled_climb_fpr", "pooled_cruise_fpr", "pooled_descent_fpr"]]
    assert float(d08c.max().max()) < ALPHA
    claim("FPRs were below the target in every phase")
    insample = {}
    for key in NEW:
        frame = src.csv(EXT / key / "lock" / "calibration_in_sample_phase_fpr.csv")
        frame = frame[(frame.nominal_fpr == ALPHA) & (frame.arm == "pooled")]
        wide = frame.pivot_table(index=["detector", "seed"], columns="phase", values="in_sample_fpr")
        insample[key] = int((wide.idxmax(axis=1) == "descent").sum())
    middle = [insample[k] for k in ("DS04", "DS05", "DS06", "DS07", "DS08a")]
    at([EXT / k / "lock" / "calibration_in_sample_phase_fpr.csv" for k in NEW], "descriptive")
    assert insample["DS01"] == 10
    claim(f"descent highest in 10 of 10 runs in DS01 and {min(middle)} to {max(middle)} of 10 in DS04–DS08a, "
          f"but in {insample['DS08c']} of 10 in DS08c")

    # H2 / H3 (Section 4.3)
    h2, h3 = dec["H2"], dec["H3"]
    at(SUM / "decisions.json", "pre-specified")
    assert h2["cells"] == 70 and h2["verdict"] == "PARTIAL"
    claim(f"reduced pooled disparity in {pct(h2['share_cells_disparity_reduced'])} of the 70 new subset–detector cells and "
          f"in {WORDS[h2['families_holding']]} of five families (H2 partial)", pct(h2["share_cells_disparity_reduced"]))
    pca = ts[ts.detector == "pca"].pivot_table(index="subset", columns="arm", values="pooled_A2")
    at(SUM / "transport_summary_alpha_0.01.csv", "descriptive")
    claim(f"pooled A2 {pp(pca.loc['DS05', 'phase_conditioned'])} and {pp(pca.loc['DS06', 'phase_conditioned'])} pp under C, "
          f"against {pp(pca.loc['DS05', 'pooled'])} and {pp(pca.loc['DS06', 'pooled'])} pp under P",
          *(pp(pca.loc[k, a]) for k in ("DS05", "DS06") for a in ("phase_conditioned", "pooled")))
    claim(f"Q worsened it further ({pp(pca.loc['DS05', 'quantile_regression_W'])} and "
          f"{pp(pca.loc['DS06', 'quantile_regression_W'])} pp)",
          pp(pca.loc["DS05", "quantile_regression_W"]), pp(pca.loc["DS06", "quantile_regression_W"]))
    at(SUM / "decisions.json", "pre-specified")
    assert abs(h3["C"]["U"] - h3["Q"]["U"]) < 1e-12 and h3["C"]["share_cells_any_engine_worse"] == h3["Q"]["share_cells_any_engine_worse"]
    claim(f"C improved every audit engine relative to P in only {pct(h3['C']['U'])} of cells, and at least one engine was "
          f"worse in {pct(h3['C']['share_cells_any_engine_worse'])}; for Q both shares were the same",
          pct(h3["C"]["U"]), pct(h3["C"]["share_cells_any_engine_worse"]))
    at(SUM / "decisions.json", "descriptive")
    assert h3["C"]["U_by_family"]["F2"] == 0.6 and h3["Q"]["U_by_family"]["F2"] == 0.6
    claim("DS04 was the exception, where C and Q each improved every engine in 6 of 10 runs")
    engines = pd.concat([src.audit(k, "paired_transport_engines") for k in NEW + ("DS02", "DS03")], ignore_index=True)
    engines = engines[engines.nominal_fpr == ALPHA]
    residual = engines[(engines.detector != "cvae") & engines.subset.isin(NEW)]
    pooled_med = residual[residual.arm == "phase_conditioned"].groupby(["subset", "unit"]).pooled_arm_A2.median()
    c_med = residual[residual.arm == "phase_conditioned"].groupby(["subset", "unit"]).arm_A2.median()
    q_med = residual[residual.arm == "quantile_regression_W"].groupby(["subset", "unit"]).arm_A2.median()
    n_mat = [int((s >= 0.5 * ALPHA).sum()) for s in (pooled_med, c_med, q_med)]
    at([EXT / k / "audit" / "paired_transport_engines.csv" for k in NEW], "descriptive")
    assert len(pooled_med) == 30
    claim(f"reached the material line on {n_mat[0]}, {n_mat[1]} and {n_mat[2]} of the 30 audit engines under P, C and Q")
    at(EXT / "DS08c" / "audit" / "paired_transport_engines.csv", "descriptive")
    c08c = residual[(residual.subset == "DS08c") & (residual.arm == "phase_conditioned")]
    worse = c08c.groupby("unit").apply(lambda x: int((x.diff_A2 > 0).sum()))
    assert [u for u, n in worse.items() if n == 7] == [7, 8, 9]
    claim("C worsened DS08c engines 7, 8 and 9 in 7 of 7 residual runs")
    lock08a = src.json(EXT / "DS08a" / "lock" / "calibration_lock.json")["roles"]
    at(EXT / "DS08a" / "audit" / "paired_transport_engines.csv", "descriptive")
    assert lock08a["classes"]["14"] == 3 and 3 in {lock08a["classes"][str(u)] for u in lock08a["calibration"]}
    top = [pooled_med.idxmax(), c_med.idxmax(), q_med.idxmax()]
    assert all(t == ("DS08a", 14) for t in top)
    e14 = [pooled_med.loc[("DS08a", 14)], c_med.loc[("DS08a", 14)], q_med.loc[("DS08a", 14)]]
    claim(f"had a median A2 of {pp(e14[0])} pp under P, {pp(e14[1])} pp under C and {pp(e14[2])} pp under Q", *(pp(v) for v in e14))

    # Reference subsets (Section 4.1)
    for key, unit in (("DS02", 14), ("DS03", 12)):
        roles = src.json(EXT / key / "lock" / "calibration_lock.json")["roles"]
        assert roles["classes"][str(unit)] == 1 and 1 not in {roles["classes"][str(u)] for u in roles["calibration"]}
        part = engines[(engines.subset == key) & (engines.unit == unit) & (engines.arm == "phase_conditioned")]
        assert (part.diff_A2 > 0).all() and len(part) == 10
    at([EXT / k / "audit" / "paired_transport_engines.csv" for k in ("DS02", "DS03")], "descriptive")
    claim("DS02 class-1 engine 14 and DS03 class-1 engine 12, both from classes absent from calibration, were made worse "
          "calibrated by C in every residual run and every CVAE seed")

    # H5 (Section 4.4)
    h5 = dec["H5"]
    at(SUM / "decisions.json", "pre-specified")
    assert h5["verdict"] == "SURVIVES" and h5["families_WE_material_majority"] == 5
    assert h5["families_substantially_improves_b"] == 0 and h5["families_reduces_phase_dependence_a"] == 2
    claim("reached the material line in a majority of its runs in all five families")
    claim(f"reduced pooled phase dependence relative to every residual detector in only "
          f"{WORDS[h5['families_reduces_phase_dependence_a']]} families")
    ux = src.csv(SUM / "uext2_cross_dataset.csv").set_index(["detector_family", "quantity"])
    cv = ux.loc[("cvae_minus_best_residual_ME_A2_P", "cvae_minus_best_residual_ME_A2_P")]
    at(SUM / "uext2_cross_dataset.csv", "pre-specified")
    claim(f"by a median of {pp(cv.point_median_over_families)} pp (family bootstrap {pp(cv.ci_lower_95)} to "
          f"{pp(cv.ci_upper_95)} pp; five top-level units)",
          pp(cv.point_median_over_families), pp(cv.ci_lower_95), pp(cv.ci_upper_95))
    cvae_cells = 21
    at(SUM / "decisions.json", "pre-specified")
    claim(f"every audit engine improved in {round(h3['C']['U_cvae'] * cvae_cells)} of the 21 CVAE cells under C and in "
          f"{round(h3['Q']['U_cvae'] * cvae_cells)} of 21 under Q")

    # H4 (Section 4.5)
    h4 = dec["H4"]
    at(SUM / "decisions.json", "pre-specified")
    assert h4["verdict"] == "SUPPORTED" and h4["beyond_volume"] and h4["weak"]
    assert h4["qualifiers"]["pooled"]["weak"] and not h4["qualifiers"]["phase_conditioned"]["weak"]
    n_sub = sum(h4["subset_supports"].values())
    claim(f"positive in at least 7 of 10 runs under both P and C in {WORDS[n_sub]} of six eligible subsets and "
          f"{WORDS[h4['families_supporting_coverage']]} of four eligible families")
    runs = src.csv(SUM / "composition_run_summary.csv")
    at(SUM / "composition_run_summary.csv", "pre-specified")
    bal = runs.groupby(["subset", "arm"]).balance_check.sum().unstack()
    n_bal9 = int(((bal["pooled"] >= 9) & (bal["phase_conditioned"] >= 9)).sum())
    assert int(bal.loc["DS04", "phase_conditioned"]) == 0
    claim(f"beat the mean single-engine design in at least 9 of 10 runs under both arms in {WORDS[n_bal9]} of six subsets")
    claim("with DS04 under C the exception (0 of 10 runs)")
    eff = src.csv(SUM / "composition_engine_effects.csv")
    at(SUM / "composition_engine_effects.csv", "descriptive")
    vol = eff.groupby(["subset", "arm", "unit"]).delta_vol_uncovered.median().groupby(["subset", "arm"]).median()
    assert float(vol.abs().max()) < 0.0005
    claim("within 0.05 pp of zero in every subset")
    assert all(q["beyond_volume_families"] == 4 for q in h4["qualifiers"].values())
    at(SUM / "composition_run_summary.csv", "pre-specified")
    claim("F1 and F2 reached the rule with exactly 7 of 10 runs under P")
    assert int(runs[(runs.subset == "DS01") & (runs.arm == "pooled")].supports_coverage.sum()) == 7
    assert int(runs[(runs.subset == "DS04") & (runs.arm == "pooled")].supports_coverage.sum()) == 7
    boot = src.csv(SUM / "composition_bootstrap.csv").set_index("arm")
    at(SUM / "composition_bootstrap.csv", "pre-specified")
    b_p, b_c = boot.loc["pooled"], boot.loc["phase_conditioned"]
    claim(f"a median over families of {pp(b_p.point)} pp (family bootstrap {signed(b_p.ci_lower_95)} to {pp(b_p.ci_upper_95)} pp)",
          pp(b_p.point), signed(b_p.ci_lower_95), pp(b_p.ci_upper_95))
    claim(f"{pp(b_c.point)} pp ({pp(b_c.ci_lower_95)} to {pp(b_c.ci_upper_95)} pp)",
          pp(b_c.point), pp(b_c.ci_lower_95), pp(b_c.ci_upper_95))

    # H6 (Section 4.6)
    h6 = dec["H6"]
    assert h6["verdict"] == "SURVIVES"
    wf = src.csv(SUM / "we_ffr.csv")
    at(SUM / "we_ffr.csv", "pre-specified")
    wf = wf[wf.subset.isin(NEW) & (wf.detector != "cvae")]
    med = {(a, r): wf[(wf.arm == a) & (wf.rule == r)].WE_FFR for a in ("pooled", "quantile_regression_W") for r in ("R0", "R1", "R2")}
    p_med = [pct(med[("pooled", r)].median(), 1) for r in ("R0", "R1", "R2")]
    p_share = [pct((med[("pooled", r)] >= 0.10).mean()) for r in ("R0", "R1", "R2")]
    fam = [WORDS[h6["families_with_flight_level_problem"][r]] for r in ("R0", "R1", "R2")]
    claim(f"was {p_med[0]} under R0, {p_med[1]} under R1 and {p_med[2]} under R2", *p_med)
    claim(f"occurred in {p_share[0]}, {p_share[1]} and {p_share[2]} of residual cells, and in the majority of cells in "
          f"{fam[0]}, {fam[1]} and {fam[2]} of five families", *p_share)
    at(SUM / "we_ffr.csv", "descriptive")
    q_meds = sorted(med[("quantile_regression_W", r)].median() for r in ("R0", "R1", "R2"))
    claim(f"Under Q the median worst engine reached {pct(q_meds[0], 1)} to {pct(q_meds[-1], 1)}", pct(q_meds[0], 1), pct(q_meds[-1], 1))

    # H7 (Section 4.6)
    ml = src.csv(SUM / "matched_labels_alpha_0.01.csv")
    at(SUM / "matched_labels_alpha_0.01.csv", "pre-specified")
    ml = ml[ml.subset.isin(NEW) & (ml.detector != "cvae")]
    lab = ml.groupby(["arm", "rule"]).matched_label.value_counts().unstack(fill_value=0)
    c0 = lab.loc[("phase_conditioned", "R0")]
    later = WORDS[int(c0.get("later at matched burden", 0))]
    claim(f"{int(c0['earlier at matched burden'])} of 49 residual runs were earlier than P, {int(c0['equal'])} equal, "
          f"{later} later and {int(c0['mixed'])} mixed under R0")
    q_earlier = [int(lab.loc[("quantile_regression_W", r)]["earlier at matched burden"]) for r in ("R0", "R1", "R2")]
    claim(f"({q_earlier[0]}, {q_earlier[1]} and {q_earlier[2]} of 49 runs under R0, R1 and R2)")
    h7 = dec["H7"]
    at(SUM / "decisions.json", "pre-specified")
    assert not any(v["residual_improves"] for k, sub in h7.items() if k.startswith("phase_conditioned") for v in sub.values())
    q_ok = sorted({(k.split("|")[1], s) for k, sub in h7.items() if k.startswith("quantile") for s, v in sub.items()
                   if v["residual_improves"]})
    assert q_ok == [("R1", "DS04"), ("R2", "DS04")]
    claim("met the criterion only on DS04 under R1 and R2")
    claim("the criterion was met in no subset under any rule")

    # U-EXT2 and original story (Section 4.7)
    at(SUM / "uext2_cross_dataset.csv", "pre-specified")
    lstm, iso = ux.loc[("lstm_autoencoder", "diff_pooled_A1")], ux.loc[("isolation_forest", "diff_ME_A2")]
    assert (ux.ci_lower_95.loc[[i for i in ux.index if i[0] != "cvae_minus_best_residual_ME_A2_P"]] < 0).all()
    assert (ux.ci_upper_95.loc[[i for i in ux.index if i[0] != "cvae_minus_best_residual_ME_A2_P"]] > 0).all()
    claim(f"LSTM {signed(lstm.point_median_over_families)} pp, {signed(lstm.ci_lower_95)} to {pp(lstm.ci_upper_95)} pp",
          signed(lstm.point_median_over_families), signed(lstm.ci_lower_95), pp(lstm.ci_upper_95))
    claim(f"Isolation Forest {signed(iso.point_median_over_families)} pp, {signed(iso.ci_lower_95)} to {pp(iso.ci_upper_95)} pp",
          signed(iso.point_median_over_families), signed(iso.ci_lower_95), pp(iso.ci_upper_95))
    story = dec["original_story"]
    at(SUM / "decisions.json", "pre-specified")
    fc = story["family_counts"]
    assert story["class"] == "PARTIALLY GENERALIZED" and (fc["S1"], fc["S2"], fc["S3"], fc["S4"], fc["S5"]) == (3, 3, 4, 5, 5)
    claim("was classified as partially generalized")
    claim("non-transport of the phase-conditioned correction held in four of five families, and the absence of a matched-delay "
          "advantage and the failure of Q on some engine in five of five, whereas conditional miscalibration and disparity "
          "reduction by C held in three of five")
    assert dec["matrix_stories"]["headline"] == "M-C + M-B" and not any(dec["rescope_flags"].values())
    claim("no rescope flag was raised")

    # Cohort facts (Sections 1, 3)
    lk = {k: src.json(EXT / k / "lock" / "calibration_lock.json") for k in NEW}
    n_audit = sum(len(lk[k]["roles"]["audit"]) for k in NEW)
    at([EXT / k / "lock" / "calibration_lock.json" for k in NEW], "descriptive")
    assert n_audit == 30
    claim("seven unopened subsets: five fleet families with 30 held-out audit engines")
    classes08c = {lk["DS08c"]["roles"]["classes"][str(u)] for u in lk["DS08c"]["roles"]["calibration"]}
    audit08c = {lk["DS08c"]["roles"]["classes"][str(u)] for u in lk["DS08c"]["roles"]["audit"]}
    assert classes08c == {3} and audit08c == {2}
    claim("DS08c's calibration pool is class 3 only, whereas all four of its audit engines are class 2")
    meta = src.json(ROOT / "docs/extension/subset_metadata_audit.json")
    at(ROOT / "docs/extension/subset_metadata_audit.json", "descriptive")
    text = json.dumps(meta)
    assert "stored_eof = 2885034880" in text and "eof = 2885034848" in text
    claim("32 bytes shorter than its HDF5 superblock declares")
    manifest = ROOT / "docs/mssp/frozen_baseline.sha256"
    n_manifest = len(manifest.read_text().strip().splitlines())
    at(manifest, "descriptive")
    claim(f"a {n_manifest}-file manifest of the frozen evidence")
    return claims, values


def derive_post_hoc(src):
    """Section 4.8: post hoc checks, verified against paper/mssp_extended/evidence/post_hoc_checks.json."""
    claims, values = [], set()

    def claim(text, *numbers):
        claims.append(text)
        values.update(numbers)
        register(text, numbers)

    ph = src.json(PKG / "evidence/post_hoc_checks.json")
    at(PKG / "evidence/post_hoc_checks.json", "post hoc")
    assert ph["status"].startswith("post hoc")
    arms = ph["a2_noise_by_arm"]
    P, C, Q = arms["pooled"], arms["phase_conditioned"], arms["quantile_regression_W"]
    claim(f"the flight-clustered standard error of one engine's overall healthy FPR had a median of "
          f"{pp(P['se_overall_fpr_median'])} pp", pp(P["se_overall_fpr_median"]))
    claim(f"a perfectly calibrated engine would reach the material line in about {pct(P['null_p_material_mean'])} of engine–run "
          f"pairs under P, {pct(C['null_p_material_mean'])} under C and {pct(Q['null_p_material_mean'])} under Q, against observed "
          f"shares of {pct(P['observed_share_material'])}, {pct(C['observed_share_material'])} and {pct(Q['observed_share_material'])}",
          *(pct(x[k]) for x in (P, C, Q) for k in ("null_p_material_mean", "observed_share_material")))
    claim(f"observed errors exceeded the 95th percentile of this reference in {pct(P['observed_share_above_null_q95'])}, "
          f"{pct(C['observed_share_above_null_q95'])} and {pct(Q['observed_share_above_null_q95'])} of pairs",
          *(pct(x["observed_share_above_null_q95"]) for x in (P, C, Q)))
    rng = ph["we_ffr_null_range"]
    lo_med, hi_med = f"{100 * rng['median_min']:.1f}", f"{100 * rng['median_max']:.1f}%"
    claim(f"a worst engine whose median is {lo_med}–{hi_med} and which reaches 10% in "
          f"{100 * rng['p_ge_10pct_min']:.0f}–{100 * rng['p_ge_10pct_max']:.0f}% of cells", lo_med, hi_med,
          f"{100 * rng['p_ge_10pct_max']:.0f}%")
    nulls = {r["subset"]: r for r in ph["we_ffr_null"]}
    flights = [r["flights_min"] for r in ph["we_ffr_null"]] + [r["flights_max"] for r in ph["we_ffr_null"]]
    claim(f"Each audit engine contributes {min(flights)}–{max(flights)} healthy flights")
    none = [k for k in NEW if all(nulls[k][f"observed_share_above_null_q95_{r}"] == 0 for r in ("R0", "R1", "R2"))]
    some = [k for k in NEW if k not in none]
    assert none == ["DS01", "DS04", "DS07", "DS08c"] and some == ["DS05", "DS06", "DS08a"]
    counts = [round(7 * nulls[k][f"observed_share_above_null_q95_{r}"]) for k in some for r in ("R0", "R1", "R2")]
    claim(f"in none of the runs in DS01, DS04, DS07 and DS08c and in {min(counts)} to {max(counts)} of 7 runs in DS05, DS06 and DS08a")
    sub = ph["a2_noise_by_subset_pooled"]
    assert sub["DS08c"]["material_share_under_alarming"] == 1.0 and sub["DS01"]["material_share_under_alarming"] == 0.0
    assert sub["DS04"]["material_share_under_alarming"] > 0.5 and sub["DS07"]["material_share_under_alarming"] > 0.5
    claim(f"Of the material per-engine errors under P, {pct(P['material_share_under_alarming'])} were under-alarming: all of "
          f"those in DS08c and most in DS04 and DS07, but none in DS01", pct(P["material_share_under_alarming"]))
    ei = ph["engine_improvement"]
    ec, eq = ei["phase_conditioned"], ei["quantile_regression_W"]
    claim(f"On average, C improved {pct(ec['mean_share_engines_improved'])} and Q {pct(eq['mean_share_engines_improved'])} of the "
          f"audit engines in a cell", pct(ec["mean_share_engines_improved"]), pct(eq["mean_share_engines_improved"]))
    claim(f"every engine would improve in about {pct(ec['coin_flip_expectation'], 1)} of cells, against "
          f"{pct(ec['share_cells_every_engine_improved'])} observed", pct(ec["coin_flip_expectation"], 1),
          pct(ec["share_cells_every_engine_improved"]))
    w = ph["ds04_runs_every_engine_within_material_line"]
    assert w["pooled"] == w["phase_conditioned"]
    claim(f"every audit engine stayed within the material line in {w['quantile_regression_W']} of 7 residual runs under Q and in "
          f"{w['pooled']} of 7 under P and C")
    e14 = ph["ds08a_engine14"]
    assert e14["audit_flights_above_calibration_span"] == 1
    claim(f"One of DS08a engine 14's {e14['healthy_flights']} healthy flights carried {pct(e14['share_of_healthy_alarms'])} of its "
          f"healthy alarms under P; without it, the engine's FPR fell from {pct(e14['fpr_all_flights'], 2)} to "
          f"{pct(e14['fpr_without_flight'], 2)}", pct(e14["share_of_healthy_alarms"]), pct(e14["fpr_all_flights"], 2),
          pct(e14["fpr_without_flight"], 2))
    ft = lambda v: f"{v:,.0f} ft, {v * 0.3048:,.0f} m"  # noqa: E731  (SI equivalent, 1 ft = 0.3048 m)
    claim(f"That flight's altitude span ({ft(e14['flight_altitude_span_ft'])}) exceeded that of every fit (at most "
          f"{ft(e14['fit_max_altitude_span_ft'])}) and calibration (at most {ft(e14['calibration_max_altitude_span_ft'])}) "
          f"flight in DS08a, and it was the only audit flight outside the calibration altitude envelope")
    ms = ph["mission_sharing"]
    c1 = ms["same_class_by_audit_class"]["1"]
    c23 = [ms["same_class_by_audit_class"][c] for c in ("2", "3")]
    assert ms["other_class_max"] == 0
    claim(f"a class-1 audit engine shared {pct(c1['min']).rstrip('%')}–{pct(c1['max'])} of its healthy flight profiles with its "
          f"same-class calibration engine and a class-2 or class-3 engine {pct(min(x['min'] for x in c23)).rstrip('%')}–"
          f"{pct(max(x['max'] for x in c23))}, "
          f"whereas no audit engine shared a profile with a calibration engine of another class",
          pct(c1["max"]), pct(max(x["max"] for x in c23)))
    cov = ph["coverage_by_audit_class"]
    assert all(v > 0 for v in cov["phase_conditioned"].values())
    plus = "+" + pp(cov["pooled"]["1"]) if cov["pooled"]["1"] > 0 else signed(cov["pooled"]["1"])
    claim(f"Under P, the coverage effect was confined to class-1 audit engines ({plus} pp, against "
          f"{signed(cov['pooled']['2'])} and {signed(cov['pooled']['3'])} pp for classes 2 and 3); under C it was positive for every class",
          pp(cov["pooled"]["1"]), signed(cov["pooled"]["2"]), signed(cov["pooled"]["3"]))
    bd = ph["balanced_design"]
    claim(f"beat the best single-engine design in only {bd['pooled']['better_than_best_single']} of {bd['pooled']['residual_runs']} "
          f"residual runs under P and {bd['phase_conditioned']['better_than_best_single']} of "
          f"{bd['phase_conditioned']['residual_runs']} under C")
    cv = ph["cvae_vs_residual"]
    assert cv["family_vs_median"]["F1"] < 0
    claim(f"exceeded that of the median residual detector by {pp(cv['median_over_families_vs_median'])} pp (median over families), "
          f"and it was lower in F1", pp(cv["median_over_families_vs_median"]))
    claim(f"and that of the median residual detector by {pp(cv['median_over_families_vs_median'])} pp")
    om = ph["bootstrap_class_omission_probability"]
    assert len({round(om[k], 4) for k in ("DS01", "DS05", "DS06", "DS07")}) == 1
    claim(f"omits at least one class in {pct(om['DS01'])} of replicates in DS01 and DS05–DS07", pct(om["DS01"]))
    tf = ph["two_flight_confirmation"]
    tp, tq = tf["pooled"], tf["quantile_regression_W"]
    assert tp["censored_engines_two"] == 0
    claim(f"reduced the worst engine's healthy confirmed-alert rate under P to zero in {tp['we_two_zero']} of {tp['residual_runs']} "
          f"residual runs, with {tp['we_two_ge_10pct']} of {tp['residual_runs']} at or above 10%, while the median delay rose from "
          f"{tp['median_delay_single']:g} to {tp['median_delay_two']:g} flights; under Q, {tq['we_two_ge_10pct']} of "
          f"{tq['residual_runs']} runs still reached 10%", f"{tp['median_delay_single']:g}")
    es = ph["early_sensitivity_pooled"]
    claim(f"the abnormal-state row alarm rate under P was {pct(es['min'], 2).rstrip('%')}–{pct(es['max'], 2)} "
          f"(median {pct(es['median'], 2)})", pct(es["min"], 2).rstrip("%"), pct(es["max"], 2), pct(es["median"], 2))
    return claims, values


def derive_validation(src):
    """Section 4.8 and the abstract: final focused validation (results/extension/focused_validation/)."""
    claims, values = [], set()

    def claim(text, *numbers):
        claims.append(text)
        values.update(numbers)
        register(text, numbers)

    root = EXT / "focused_validation" / "summary"
    summary = src.json(root / "focused_validation_summary.json")
    at(root / "focused_validation_summary.json", "focused validation")
    assert summary["plan_sha256"].startswith("f734cdf6") and summary["G6_uext2_reproduced"]
    c1 = summary["component1"]
    cC, cP, cQ = c1["phase_conditioned"], c1["pooled"], c1["quantile_regression_W"]
    assert all(v["engines"] == 30 and v["families_showing_excess"] == 5 for v in c1.values())
    assert summary["transport_claim"] == "STRENGTHENED"
    claim(f"exceeded each engine's cross-fitted self-calibration error in {cC['clearly_exceeding']} of 30 engines")
    claim(f"They exceeded the engine's own reference in {cC['clearly_exceeding']} of 30 engines under C, "
          f"{cP['clearly_exceeding']} under P and {cQ['clearly_exceeding']} under Q, in all five families")
    eng = src.csv(root / "engine_summary.csv")
    at(root / "engine_summary.csv", "focused validation")
    ec_ = eng[eng.arm == "phase_conditioned"]
    obs, nf50 = pp(ec_.observed_A2_median.median()), pp(ec_.NF50_median.median())
    claim(f"with a median over engines of {obs} pp under C, against a median cross-fitted self-calibration reference NF50 of {nf50} pp", obs, nf50)
    exceptions = [(r.subset, r.unit) for r in ec_[~ec_.clearly_exceeds].itertuples()]
    assert exceptions == [("DS01", 8), ("DS07", 9), ("DS08a", 12)], exceptions
    claim("under C the exceptions were DS01 engine 8, DS07 engine 9 and DS08a engine 12")
    noise = src.csv(PKG / "evidence/post_hoc_engine_noise.csv")
    at(PKG / "evidence/post_hoc_engine_noise.csv", "focused validation")
    noise = noise.assign(above=noise.observed_A2 > noise.null_A2_q95)
    per_engine = noise.groupby(["arm", "subset", "unit"]).above.sum().reset_index()
    per_engine["clearly"] = per_engine.above >= 4
    per_engine["family"] = per_engine.subset.map(FAMILY)
    counts, fams = [], []
    for arm in ("phase_conditioned", "pooled", "quantile_regression_W"):
        g = per_engine[per_engine.arm == arm]
        counts.append(int(g.clearly.sum()))
        fams.append(WORDS[int((g.groupby("family").clearly.mean() >= 0.5).sum())])
    claim(f"the same rule counts {counts[0]}, {counts[1]} and {counts[2]} of 30 engines, in {fams[0]}, {fams[1]} and {fams[2]} families")
    width = src.csv(root / "bootstrap_width_comparison.csv")
    at(root / "bootstrap_width_comparison.csv", "focused validation")
    diffs = width[width.metric.str.startswith("diff")]
    med = diffs.groupby("metric").share_of_width_from_class_omission.median()
    ds01 = diffs[diffs.subset == "DS01"].share_of_width_from_class_omission
    none = diffs[diffs.subset.isin(["DS04", "DS08c"])].share_of_width_from_class_omission.abs().max()
    assert none < 0.05
    lo, hi = pct(med.min()), pct(med.max())
    claim(f"a median of {lo.rstrip('%')}–{hi} of the width of the per-subset C − P intervals ({pct(ds01.min()).rstrip('%')}–"
          f"{pct(ds01.max())} in DS01, about none in DS04 and DS08c)", hi, pct(ds01.max()))
    me = width[width.metric == "diff_ME_A2"]
    assert (me.original_includes_zero == me.class_preserving_includes_zero).all()
    claim("No per-subset interval for the C − P change in mean per-engine error changed from including to excluding zero")
    u2 = src.csv(root / "uext2_original_vs_class_preserving.csv")
    at(root / "uext2_original_vs_class_preserving.csv", "focused validation")
    cp = u2.set_index("detector_family")
    others = u2[u2.detector_family != "cvae_minus_best_residual_ME_A2_P"]
    assert others.includes_zero_class_preserving.all()
    gap = cp.loc["cvae_minus_best_residual_ME_A2_P"]
    assert not gap.includes_zero_class_preserving
    claim(f"the CVAE's gap to the best residual detector remained ({pp(gap.ci_lower_95_class_preserving)} to "
          f"{pp(gap.ci_upper_95_class_preserving)} pp)", pp(gap.ci_lower_95_class_preserving), pp(gap.ci_upper_95_class_preserving))
    loc = src.csv(root / "local_engine_summary.csv")
    at(root / "local_engine_summary.csv", "focused validation")
    lc, lp = loc[loc.arm == "phase_conditioned"], loc[loc.arm == "pooled"]
    claim(f"the median change was {signed(lc.improvement_median.median())} pp under C and {signed(lp.improvement_median.median())} pp "
          f"under P", signed(lc.improvement_median.median()), signed(lp.improvement_median.median()))
    claim(f"a majority of runs improved for only {int((lc.runs_improved >= 4).sum())} and {int((lp.runs_improved >= 4).sum())} of 30 engines")
    assert lc.fleet_within_noise_range.all() and lp.fleet_within_noise_range.all()
    claim("The fleet thresholds' errors were already within the range that random five-flight local thresholds give, for every engine")
    return claims, values


def frozen_values(src, text):
    """DS02/DS03 values cited in Section 4.1 must be frozen display values also present in the pre-extension text."""
    core = src.csv(CORE)
    pre = PRE_TEXT.read_text(encoding="utf-8")
    values = set()
    for dataset, triple in (("DS02 discovery", ("0.125%", "0.428%", "3.459%")), ("DS03", ("0.877%", "0.912%", "1.977%"))):
        rows = core[core.dataset.str.startswith(dataset) & (core.detector == "pca") & (core.nominal_fpr_target == ALPHA)
                    & core.metric.isin(["climb_fpr", "cruise_fpr", "descent_fpr"]) & (core.evaluation_unit == "pooled")]
        shown = set(rows.display_rounded_value)
        for v in triple:
            assert v in shown and v in pre, (dataset, v)
            values.add(v)
    claim = ("climb 0.125%, cruise 0.428%, descent 3.459%", "climb 0.877%, cruise 0.912%, descent 1.977%")
    assert "in all 14 detector runs" in pre
    at(CORE, "frozen")
    register(claim[0], ("0.125%", "0.428%", "3.459%"))
    register(claim[1], ("0.877%", "0.912%", "1.977%"))
    at(PRE_TEXT, "frozen")
    register("reduced pooled between-phase disparity in all 14 detector runs", ())
    return values, list(claim) + ["reduced pooled between-phase disparity in all 14 detector runs"]


def sections(text):
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    abstract = body.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0].strip()
    keywords = body.split("**Keywords:**", 1)[1].split("\n", 1)[0].strip()
    highlights = [line[2:].strip() for line in body.split("**Highlights", 1)[1].split("## 1.", 1)[0].splitlines()
                  if line.startswith("- ")]
    results = body.split("## 4. Results", 1)[1].split("## Data availability", 1)[0]
    return body, abstract, keywords, highlights, results


def ledger_hash_check(src):
    ledger = pd.read_csv(LEDGER)
    recorded = ledger.groupby("source_file").source_sha256.agg(lambda s: set(s))
    problems = []
    for path in sorted(src.used):
        rel = str(path.relative_to(ROOT))
        if rel in recorded.index:
            if len(recorded[rel]) != 1 or sha256(path) not in recorded[rel]:
                problems.append(f"ledger hash mismatch for {rel}")
    covered = sum(1 for p in src.used if str(p.relative_to(ROOT)) in recorded.index)
    return problems, covered


CLAIM_STAT, TABLE_STAT, FIGURE_STAT = "manuscript claim", "manuscript table", "manuscript figure"
REGISTRY_STATS = (CLAIM_STAT, TABLE_STAT, FIGURE_STAT)
LEDGER_COLUMNS = ("ex_id", "statistic", "value", "subset", "family", "engine", "detector", "seed", "target", "arm", "rule",
                  "aggregation", "source_file", "source_sha256", "commit", "status", "tier", "claim")


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def source_fields(source):
    """Ledger source_file and source_sha256 for one file or a set of files (hash of the sorted per-file hashes)."""
    paths = list(source) if isinstance(source, (list, tuple)) else [source]
    if len(paths) == 1:
        return rel(paths[0]), sha256(paths[0])
    pairs = sorted((rel(q), sha256(q)) for q in paths)
    combined = hashlib.sha256("\n".join(f"{d}  {r}" for r, d in pairs).encode()).hexdigest()
    return ";".join(r for r, _ in pairs), combined


def captions(body):
    figs = dict(re.findall(r"^\*\*Fig\. (\d+)\.\*\* (.+)$", body, flags=re.M))
    tabs = dict(re.findall(r"^- \*\*Table (\d+)\.\*\* (.+)$", body, flags=re.M))
    return figs, tabs


def registry_items(body):
    """Every cited claim, table and figure as a ledger item (statistic, claim text, value, source, status)."""
    items, seen = [], set()
    for entry in REGISTRY:
        if entry["text"] in seen:
            continue
        seen.add(entry["text"])
        items.append({"statistic": CLAIM_STAT, "claim": entry["text"], "value": "; ".join(entry["numbers"]) or "(no numeric token)",
                      "source": entry["source"], "status": f"manuscript claim ({entry['category']})",
                      "aggregation": "manuscript claim; re-derived by paper/mssp_extended/verify_numbers.py"})
    import importlib.util
    spec = importlib.util.spec_from_file_location("mssp_extended_build_latex", PKG / "build_latex.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    figs, tabs = captions(body)
    for number, name in builder.TABLES.items():
        path = PKG / "tables" / f"{name}.csv"
        items.append({"statistic": TABLE_STAT, "claim": f"Table {number}. {tabs[str(number)]}", "value": sha256(path),
                      "source": path, "status": "manuscript table (content hash)",
                      "aggregation": "table cells built from the listed outputs by build_figures_tables.py"})
    for number, name in builder.FIGURES.items():
        png = PKG / "figures" / f"{name}.png"  # deterministic rendering of the same drawing as the PDF (the PDF embeds a date)
        items.append({"statistic": FIGURE_STAT, "claim": f"Fig. {number}. {figs[str(number)]}", "value": sha256(png),
                      "source": png, "status": "manuscript figure (content hash of the PNG rendering)",
                      "aggregation": "figure drawn by build_figures_tables.py; inputs listed in its provenance record"})
    return items


def ledger_registry(items, register=False):
    """Check every item against its ledger row; with register=True, append the missing rows (append-only)."""
    import csv
    import subprocess
    ledger = pd.read_csv(LEDGER, dtype=str, keep_default_na=False)
    rows = {(r.statistic, r.claim): r for r in ledger[ledger.statistic.isin(REGISTRY_STATS)].itertuples()}
    problems, missing, current = [], [], set()
    for item in items:
        key = (item["statistic"], item["claim"])
        current.add(key)
        source_file, source_sha = source_fields(item["source"])
        row = rows.get(key)
        if row is None:
            missing.append((item, source_file, source_sha))
            continue
        for field, expected in (("value", item["value"]), ("source_file", source_file), ("source_sha256", source_sha),
                                ("status", item["status"])):
            if getattr(row, field) != expected:
                problems.append(f"ledger {row.ex_id} ({item['statistic']}): {field} differs from the manuscript "
                                f"({getattr(row, field)!r} vs {expected!r})")
    for key, row in rows.items():
        if key not in current:
            problems.append(f"ledger {row.ex_id}: registered {key[0]} no longer in the manuscript: {key[1][:80]!r}")
    if missing and register:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        start = len(ledger)
        with LEDGER.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(ledger.columns), lineterminator="\n")
            for i, (item, source_file, source_sha) in enumerate(missing, start=1):
                writer.writerow({"ex_id": f"EX{start + i:06d}", "statistic": item["statistic"], "value": item["value"],
                                 "subset": "", "family": "", "engine": "", "detector": "", "seed": "", "target": ALPHA,
                                 "arm": "", "rule": "", "aggregation": item["aggregation"], "source_file": source_file,
                                 "source_sha256": source_sha, "commit": commit, "status": item["status"],
                                 "tier": "manuscript", "claim": item["claim"]})
        print(f"registered {len(missing)} manuscript items in the ledger (EX{start + 1:06d}-EX{start + len(missing):06d})")
        return ledger_registry(items, register=False)
    problems += [f"not registered in the ledger: {item['statistic']}: {item['claim'][:80]!r}" for item, _, _ in missing]
    return problems, ledger


def independent_support(ledger):
    """Report: how many displayed numbers of the registered claims also occur in the pre-existing ledger rows."""
    base = ledger[~ledger.statistic.isin(REGISTRY_STATS)]
    blob = "\n".join(base.claim.astype(str))
    values = pd.to_numeric(base.value, errors="coerce").dropna().to_numpy(dtype=float)
    tokens = [n for e in REGISTRY for n in e["numbers"] if e["category"] != "frozen"]
    found = 0
    for token in tokens:
        plain = token.replace(MINUS, "-").lstrip("+").rstrip("%")
        hit = token in blob or plain in blob
        if not hit:
            try:
                x = float(plain)
            except ValueError:
                x = None
            if x is not None:
                decimals = len(plain.split(".")[1]) if "." in plain else 0
                hit = bool(np.any(np.round(values * 100, decimals) == round(x, decimals))
                           or np.any(np.round(values, decimals) == round(x, decimals)))
        found += hit
    return found, len(tokens)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", action="store_true", help="list the derived claims")
    parser.add_argument("--register", action="store_true",
                        help="append missing manuscript claims, tables and figures to the evidence ledger (append-only)")
    args = parser.parse_args()
    text = DRAFT.read_text(encoding="utf-8")
    body, abstract, keywords, highlights, results = sections(text)
    flat = re.sub(r"\s+", " ", body)
    src = Sources()
    problems = []
    claims, values = derive(src)
    post_claims, post_values = derive_post_hoc(src)
    val_claims, val_values = derive_validation(src)
    claims, values = claims + post_claims + val_claims, values | post_values | val_values
    frozen, frozen_claims = frozen_values(src, body)
    for phrase in claims + frozen_claims:
        if args.print:
            print(phrase)
        if phrase not in flat:
            problems.append(f"claim not found verbatim in draft: {phrase!r}")

    allowed = values | frozen | CONSTANTS
    scope = "\n".join([abstract] + highlights + [results.split("## 5. Discussion", 1)[0], results.split("## 5. Discussion", 1)[1]])
    scope = re.sub(r"\[N?\d+\]", "", scope)
    scope = re.sub(r"^#+ .*$", "", scope, flags=re.M)  # headings
    scope = re.sub(r"Sections? \d+(\.\d+)*((–| and )\d+(\.\d+)*)?", "", scope)  # cross-references
    for token in re.findall(r"(?<![\w.])[−-]?\d+\.\d+%?|(?<![\w.])\d+%", scope):
        if token not in allowed and token.lstrip(MINUS) not in allowed:
            problems.append(f"unsourced number in abstract/highlights/Sections 4-6: {token}")

    lower = body.lower()
    for term in FORBIDDEN:
        if term in lower:
            problems.append(f"forbidden or placeholder text: {term!r}")
    for term in REQUIRED:
        if term not in body:
            problems.append(f"required wording missing: {term!r}")
    n_words = len(re.findall(r"\S+", abstract))
    if not ABSTRACT_WORDS[0] <= n_words <= ABSTRACT_WORDS[1]:
        problems.append(f"abstract has {n_words} words")
    if not HIGHLIGHTS[0] <= len(highlights) <= HIGHLIGHTS[1]:
        problems.append(f"{len(highlights)} highlights")
    for h in highlights:
        if len(h) > HIGHLIGHT_CHARS:
            problems.append(f"highlight over {HIGHLIGHT_CHARS} characters ({len(h)}): {h}")
    n_kw = len([k for k in keywords.split(";") if k.strip()])
    if not KEYWORDS[0] <= n_kw <= KEYWORDS[1]:
        problems.append(f"{n_kw} keywords")

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    cited = set()
    for a, b, c, d in re.findall(r"\[(N?)(\d+)\]–\[(N?)(\d+)\]", body):
        cited.update((a + str(k)) for k in range(int(b), int(d) + 1))
    cited.update(re.findall(r"\[(N?\d+)\]", body))
    keys = {k if k.startswith("N") else f"ref{k}" for k in cited}
    if keys - set(spec):
        problems.append(f"cited keys without a verified spec: {sorted(keys - set(spec))}")
    if set(spec) - keys:
        problems.append(f"spec keys never cited: {sorted(set(spec) - keys)}")

    ledger_problems, covered = ledger_hash_check(src)
    problems += ledger_problems
    items = registry_items(body)
    registry_problems, ledger = ledger_registry(items, register=args.register)
    problems += registry_problems
    support, n_tokens = independent_support(ledger)
    print(f"ledger registry: {sum(i['statistic'] == CLAIM_STAT for i in items)} claims, "
          f"{sum(i['statistic'] == TABLE_STAT for i in items)} tables, {sum(i['statistic'] == FIGURE_STAT for i in items)} figures; "
          f"independent support: {support} of {n_tokens} displayed numbers also occur in pre-existing ledger rows")
    print(f"claims checked: {len(claims) + len(frozen_claims)}; numbers allowed: {len(allowed)}; "
          f"abstract words: {n_words}; highlights: {len(highlights)} (max {max(len(h) for h in highlights)} chars); "
          f"keywords: {n_kw}; cited keys: {len(keys)}; source files: {len(src.used)} ({covered} ledger-certified)")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("verify_numbers: all checks passed")


if __name__ == "__main__":
    main()
