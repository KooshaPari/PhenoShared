#!/usr/bin/env python3
"""Decide whether the operator-coverage figure can be re-derived under the
operator ruling of 2026-11-12 and write the answer to coverage_q3b.json.

Ruling (2026-11-12): operator intent includes words addressed to ANY party,
not only words addressed to an agent.

Old definition: operator = words addressed to an agent. Encoded verbatim in the
nonask labeller rubric and in the adjudication rubric.

Order of operations matters and is enforced here:

  1. REPRODUCE the existing points first. The three published points
     (0.0847 labeller 1, 0.0807 labeller 2, 0.0788 adjudicated) are asserted to
     4 decimal places before any new-definition number is computed. If they do
     not reproduce, the script exits non-zero and writes nothing.
  2. Then check whether an AUDIENCE / counterparty field is recorded per row.
  3. Then compute the bound.

Usage:  redefine_coverage_q3b.py [--check]

  --check  verify the existing coverage_q3b.json agrees with this script
           (ignoring generated_at_utc) and write nothing.

Inputs read (never modified):
  coverage_consistency.json, askcue_speaker_scored.json,
  cited_speaker_scored.json, nonask_scored.json,
  cited_labels.json, askcue_labels.json,
  cited_labels_l2.json, askcue_labels_l2.json, nonask_labels_l2.json,
  nonask_speaker_key.json, askcue_speaker_key.json, cited_speaker_key.json,
  operator_coverage.json, operator_coverage_l2.json, adjudication.json
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "coverage_q3b.json")

BUCKETS = ("cited", "askcue", "nonask")
KEY_FILES = {"cited": "cited_speaker_key.json",
             "askcue": "askcue_speaker_key.json",
             "nonask": "nonask_speaker_key.json"}
LABEL_FILES = {("cited", "labeller_1"): "cited_labels.json",
               ("askcue", "labeller_1"): "askcue_labels.json",
               ("cited", "labeller_2"): "cited_labels_l2.json",
               ("askcue", "labeller_2"): "askcue_labels_l2.json",
               ("nonask", "labeller_2"): "nonask_labels_l2.json"}
# Which per-item label file backs each (baseline, bucket). None means the
# per-item attribution for that cell does not exist, so the bound falls back to
# a stated worst case. The adjudicated baseline reuses labeller 1's per-item
# labels for cited and askcue (the adjudication only re-read the nonask
# disagreements), and has per-item labels for the nonask bucket only on the 12
# disputed rows.
PER_ITEM_SOURCES = {
    "labeller_1": {"cited": "cited_labels.json", "askcue": "askcue_labels.json",
                   "nonask": None},
    "labeller_2": {"cited": "cited_labels_l2.json", "askcue": "askcue_labels_l2.json",
                   "nonask": "nonask_labels_l2.json"},
    "adjudicated": {"cited": "cited_labels.json", "askcue": "askcue_labels.json",
                    "nonask": None},
}
LOST_REASON = {
    "labeller_1": ("because labeller 1 per-item attribution is lost (nonask_scored.json "
                   "label_restore_note)"),
    "adjudicated": ("because per-item adjudicated labels exist only for the 12 disputed "
                    "rows"),
}
SCAN_FILES = [
    "nonask_candidates.json", "ask_rule_sample.json", "cited_chunk_20_39.json",
    "cited_chunk_40_59.json", "recall_candidates.json",
    "nonask_speaker_sheet.json", "askcue_speaker_sheet.json",
    "cited_speaker_sheet.json", "nonask_labels_l2.json",
    "askcue_labels_l2.json", "cited_labels_l2.json", "askcue_labels.json",
    "cited_labels.json", "adjudication.json", "adjudication_sheet.json",
    "union_channels.json", "imessage_MANIFEST.json",
]
# Candidate per-row names for an audience / counterparty fact.
AUDIENCE_NAMES = ("recipient", "recipients", "counterparty", "is_group",
                  "isgroup", "chat_kind", "chatkind", "sender", "addressee",
                  "audience", "addressed_to", "addressee_kind", "party")
# Rubrics that carry an explicit addressee filter (operator = addressed to an agent).
ADDRESS_FILTERED_RUBRICS = ("nonask_speaker_sheet.json", "adjudication_sheet.json")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def per_row_fields(doc):
    """Field names carried by the per-row records of a json document."""
    out = set()

    def walk(node, depth=0):
        if depth > 5:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                out.add(key)
                walk(value, depth + 1)
        elif isinstance(node, list):
            for value in node[:60]:
                walk(value, depth + 1)

    walk(doc)
    return out


def operator_rows(items):
    return [i for i in items if i.get("speaker") == "operator"]


def coverage(shares, populations):
    """cited operator units / total operator units; returns point, N, T, units."""
    units = {b: populations[b] * shares[b] for b in BUCKETS}
    numerator = units["cited"]
    total = sum(units.values())
    return numerator / total, numerator, total, units


def main():
    check_only = "--check" in sys.argv

    # ------------------------------------------------------------------
    # STEP 1: reproduce the existing points BEFORE computing anything new.
    # ------------------------------------------------------------------
    frame = load("coverage_consistency.json")["frame_a_set_union"]
    populations = {"cited": frame["cited"],
                   "askcue": frame["uncited_ask_cue"],
                   "nonask": frame["uncited_non_ask_cue"]}
    if frame["cited"] + frame["uncited"] != frame["units"]:
        raise SystemExit("DRIFT: cited + uncited != units")
    if frame["uncited_ask_cue"] + frame["uncited_non_ask_cue"] != frame["uncited"]:
        raise SystemExit("DRIFT: ask_cue + non_ask_cue != uncited")

    ask = load("askcue_speaker_scored.json")["operator_share"]
    cited = load("cited_speaker_scored.json")["operator_share"]
    nonask = load("nonask_scored.json")
    by_speaker = nonask["by_speaker_pass2"]
    n_sample = nonask["sample_size"]
    op_n = by_speaker["operator"]["n"]
    nonop_n = sum(v["n"] for k, v in by_speaker.items() if k != "operator")
    if op_n + nonop_n != n_sample:
        raise SystemExit("DRIFT: nonask speakers %d+%d != sample_size %d"
                         % (op_n, nonop_n, n_sample))
    shares_l1 = {"cited": cited["share"], "askcue": ask["share"],
                 "nonask": 1.0 - nonop_n / n_sample}
    point_l1, n_l1, t_l1, units_l1 = coverage(shares_l1, populations)

    l2_counts = {}
    for bucket in BUCKETS:
        items = load(LABEL_FILES[(bucket, "labeller_2")])["items"]
        if len(items) != 60:
            raise SystemExit("DRIFT: %s has %d items, expected 60"
                             % (LABEL_FILES[(bucket, "labeller_2")], len(items)))
        l2_counts[bucket] = len(operator_rows(items))
    shares_l2 = {b: l2_counts[b] / 60.0 for b in BUCKETS}
    point_l2, n_l2, t_l2, units_l2 = coverage(shares_l2, populations)

    adj_doc = load("adjudication.json")
    adj_nonask = adj_doc["bucket_operator_count"]["majority_of_three"]
    # The adjudicated point was computed with exact k/n shares (adjudication.json
    # records both the exact reproduction and the rounded-share commit), unlike
    # operator_coverage.json which multiplies the rounded stored shares.
    shares_l1_exact = {"cited": cited["n"] / 60.0, "askcue": ask["n"] / 60.0,
                        "nonask": 1.0 - nonop_n / n_sample}
    shares_adj = dict(shares_l1_exact)
    shares_adj["nonask"] = adj_nonask / 60.0
    point_adj, n_adj, t_adj, units_adj = coverage(shares_adj, populations)

    committed_l1 = load("operator_coverage.json")["coverage"]["point"]
    committed_l2 = load("operator_coverage_l2.json")["coverage"]["point"]
    committed_adj = adj_doc["coverage"]["adjudicated"]["point"]

    failures = []
    if round(point_l1, 4) != 0.0847:
        failures.append("labeller 1 point %.17f != 0.0847" % point_l1)
    if round(point_l2, 4) != 0.0807:
        failures.append("labeller 2 point %.17f != 0.0807" % point_l2)
    if round(point_adj, 4) != 0.0788:
        failures.append("adjudicated point %.17f != 0.0788" % point_adj)
    if abs(point_l1 - committed_l1) > 1e-12:
        failures.append("labeller 1 recomputed %.17f != committed %.17f"
                        % (point_l1, committed_l1))
    if abs(point_l2 - committed_l2) > 1e-12:
        failures.append("labeller 2 recomputed %.17f != committed %.17f"
                        % (point_l2, committed_l2))
    if abs(point_adj - committed_adj) > 1e-9:
        failures.append("adjudicated recomputed %.17f != committed %.17f"
                        % (point_adj, committed_adj))
    if failures:
        for f in failures:
            print("REPRODUCTION FAILURE: %s" % f)
        raise SystemExit("old points did not reproduce; nothing computed, nothing written")
    print("reproduced old points: labeller_1 %.4f (committed %.4f), "
          "labeller_2 %.4f (committed %.4f), adjudicated %.4f (committed %.4f)"
          % (point_l1, committed_l1, point_l2, committed_l2, point_adj, committed_adj))

    # ------------------------------------------------------------------
    # STEP 2: is an audience / counterparty field recorded per row?
    # ------------------------------------------------------------------
    key_fields = {}
    key_channels = {}
    for bucket in BUCKETS:
        items = load(KEY_FILES[bucket])["items"]
        fields = set()
        for item in items:
            fields.update(item.keys())
        key_fields[bucket] = sorted(fields)
        key_channels[bucket] = {i["idx"]: set(i.get("channels", [])) for i in items}
        if len(items) != 60:
            raise SystemExit("DRIFT: %s has %d items, expected 60"
                             % (KEY_FILES[bucket], len(items)))

    label_fields = set()
    for path in LABEL_FILES.values():
        for item in load(path)["items"]:
            label_fields.update(item.keys())
    label_fields = sorted(label_fields)

    observed = set()
    for bucket in BUCKETS:
        observed.update(key_fields[bucket])
    observed.update(label_fields)
    audience_hits = sorted(n for n in AUDIENCE_NAMES if n in observed)

    scanned, scanned_fields = [], set()
    for name in SCAN_FILES:
        if not os.path.exists(os.path.join(HERE, name)):
            continue
        scanned.append(name)
        scanned_fields.update(per_row_fields(load(name)))
    audience_hits_scanned = sorted(n for n in AUDIENCE_NAMES if n in scanned_fields)
    # 'sender'/'recipient' style fields may legitimately appear as manifest keys
    # at the chat level; the decisive test is the per-row one above.
    audience_present = bool(audience_hits)

    measurable = audience_present
    if measurable:
        raise SystemExit("an audience field IS present; this script only encodes the "
                         "not-measurable branch and must be revised")

    # ------------------------------------------------------------------
    # STEP 3: counts, phone-channel operator rows, bound, derived range.
    # ------------------------------------------------------------------
    old_counts = {"labeller_1": {"cited": cited["n"], "askcue": ask["n"], "nonask": op_n},
                  "labeller_2": dict(l2_counts),
                  "adjudicated": {"cited": cited["n"], "askcue": ask["n"],
                                  "nonask": adj_nonask}}
    phone_rows = {b: sum(1 for s in key_channels[b].values() if "phone" in s)
                  for b in BUCKETS}

    def phone_operator_rows(bucket, baseline):
        path = PER_ITEM_SOURCES[baseline][bucket]
        if path is None:
            return None
        items = load(path)["items"]
        return sum(1 for i in operator_rows(items)
                   if "phone" in key_channels[bucket][i["idx"]])

    def nonop_human_rows(bucket, baseline):
        path = PER_ITEM_SOURCES[baseline][bucket]
        if path is None:
            return None
        items = load(path)["items"]
        return sum(1 for i in items
                   if i.get("speaker") != "operator"
                   and key_channels[bucket][i["idx"]] & {"phone", "imessage"})

    def phone_operator_rows_for(bucket, baseline):
        """Recorded phone-channel operator rows, or a stated worst case when the
        per-item labels for that baseline do not exist."""
        recorded = phone_operator_rows(bucket, baseline)
        if recorded is not None:
            return (recorded, "recorded",
                    "%s joined to %s on idx"
                    % (PER_ITEM_SOURCES[baseline][bucket], KEY_FILES[bucket]))
        worst = min(phone_rows[bucket], old_counts[baseline][bucket])
        return (worst, "worst_case",
                "all %d phone-channel rows assumed operator-authored, %s"
                % (worst, LOST_REASON[baseline]))

    baselines = ("labeller_1", "labeller_2", "adjudicated")
    points = {"labeller_1": point_l1, "labeller_2": point_l2, "adjudicated": point_adj}
    totals = {"labeller_1": t_l1, "labeller_2": t_l2, "adjudicated": t_adj}
    shares = {"labeller_1": shares_l1, "labeller_2": shares_l2, "adjudicated": shares_adj}

    bound_by_baseline, bound_units = {}, {}
    derived_by_baseline = {}
    derived_operator_range = {}
    for baseline in baselines:
        units_per_bucket, delta_units = {}, 0.0
        for bucket in BUCKETS:
            rows, _, _ = phone_operator_rows_for(bucket, baseline)
            u = populations[bucket] * rows / 60.0
            units_per_bucket[bucket] = u
            delta_units += u
        total_units = totals[baseline]
        delta_point = delta_units / total_units
        point = points[baseline]
        bound_by_baseline[baseline] = {"low": point, "high": point + delta_point}
        bound_units[baseline] = {
            "cited": units_per_bucket["cited"],
            "askcue": units_per_bucket["askcue"],
            "nonask": units_per_bucket["nonask"],
            "delta_units": delta_units,
            "total_operator_units_old": total_units,
            "delta_point": delta_point,
        }
        # Derived range: only the nonask rubric carried the addressee filter, and
        # nonask appears in the denominator only, so newly included operator rows
        # can only push the coverage point down.
        flips = nonop_human_rows("nonask", "labeller_2")
        old_nonask = old_counts[baseline]["nonask"]
        new_nonask = old_nonask + flips
        s2 = dict(shares[baseline])
        s2["nonask"] = new_nonask / 60.0
        low, _, _, _ = coverage(s2, populations)
        derived_by_baseline[baseline] = {
            "low": low, "high": point,
            "nonask_operator_range": [old_nonask, new_nonask],
        }
        derived_operator_range[baseline] = [old_nonask, new_nonask]

    per_bucket = {}
    for bucket in BUCKETS:
        by_baseline = {}
        for baseline in baselines:
            rows, kind, source = phone_operator_rows_for(bucket, baseline)
            by_baseline[baseline] = {
                "old_operator_count": old_counts[baseline][bucket],
                "newly_included_count": None,
                "new_operator_count": None,
                "per_item_labels_available": kind == "recorded",
                "phone_operator_rows": rows,
                "phone_operator_rows_source": source,
            }
        if bucket == "nonask":
            range_basis = ("old count, to old count plus the non-operator rows in human "
                           "channels (phone or imessage), which are the only rows whose label "
                           "could have been decided by the addressee filter. Nonask labeller 2 "
                           "shows 4 such rows; labeller 1 per-item labels are LOST (aggregate "
                           "only, see nonask_scored.json label_restore_note), so 4 is carried "
                           "across and flagged.")
        else:
            range_basis = ("the cited and askcue rubrics were already authorship based "
                           "('operator = Koosha's own words', with peer defined as a person "
                           "who is not Koosha) and carried NO addressee filter, so the new "
                           "ruling changes nothing in this bucket. Range is degenerate by "
                           "construction.")
        per_bucket[bucket] = {
            "bucket": {"cited": "cited", "askcue": "uncited_ask_cue",
                       "nonask": "uncited_non_ask_cue"}[bucket],
            "n": 60,
            "population": populations[bucket],
            "fields": key_fields[bucket],
            "old_operator_count": old_counts["labeller_1"][bucket],
            "old_operator_count_baseline": "labeller_1",
            "newly_included_count": None,
            "new_operator_count": None,
            "new_operator_count_range": {
                baseline: derived_operator_range[baseline]
                if bucket == "nonask"
                else [old_counts[baseline][bucket], old_counts[baseline][bucket]]
                for baseline in baselines},
            "new_operator_count_range_basis": range_basis,
            "by_baseline": by_baseline,
        }

    doc = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "redefine_coverage_q3b.py",
        "question": ("Can the operator-coverage figure be re-derived under the operator "
                     "ruling of 2026-11-12 (operator intent includes words addressed to ANY "
                     "party)?"),
        "ruling": ("operator intent includes words addressed to ANY party, not only words "
                   "addressed to an agent"),
        "ruling_date": "2026-11-12",
        "definition_old": ("operator = words addressed to an agent. Encoded verbatim in the "
                           "nonask labeller rubric ('operator = Koosha's own words: an "
                           "instruction, question, ruling, correction, or remark addressed to "
                           "an agent') and in the adjudication rubric."),
        "definition_new": ("operator = words addressed to any party; i.e. operator authorship "
                            "with the audience unrestricted, so operator words addressed to a "
                            "human peer also count as operator intent."),
        "measurable": measurable,
        "not_measurable_reason": (
            "No per-row AUDIENCE or counterparty field is recorded anywhere in the sample "
            "lineage. The only per-row fields carried by the three speaker keys are idx, "
            "clause and channels; the label files add only speaker (authorship) and why (free "
            "text). There is no recipient, counterparty, is_group, chat_kind, sender or "
            "recipient field, so a row's addressee cannot be read from the artefacts and the "
            "set of rows whose operator status flips under the new ruling cannot be "
            "enumerated. Re-deriving the figure under the new ruling would require a NEW "
            "labelling pass under the new rubric, not a re-derivation from recorded fields."),
        "audience_field_present": audience_present,
        "fields_found": {
            "nonask_speaker_key.json": key_fields["nonask"],
            "askcue_speaker_key.json": key_fields["askcue"],
            "cited_speaker_key.json": key_fields["cited"],
            "label_files_add": label_fields,
            "searched_without_result": list(AUDIENCE_NAMES),
            "scanned_files": scanned,
            "scanned_files_audience_name_hits": audience_hits_scanned,
        },
        "old_points": {
            "labeller_1": {
                "point": point_l1, "point_4dp": round(point_l1, 4), "reproduced": True,
                "source": ("operator_coverage.json (labeller_mode l1); recomputed by this "
                           "script from coverage_consistency.json, askcue_speaker_scored.json, "
                           "cited_speaker_scored.json, nonask_scored.json")},
            "labeller_2": {
                "point": point_l2, "point_4dp": round(point_l2, 4), "reproduced": True,
                "source": ("operator_coverage_l2.json (labeller_mode l2); recomputed by this "
                           "script from cited_labels_l2.json, askcue_labels_l2.json, "
                           "nonask_labels_l2.json")},
            "adjudicated": {
                "point": point_adj, "point_4dp": round(point_adj, 4),
                "committed_point": committed_adj, "reproduced": True,
                "source": ("adjudication.json coverage.adjudicated; recomputed by this script "
                           "(cited and askcue shares from labeller 1, nonask operator count "
                           "26 = majority of three)")},
        },
        "per_bucket": per_bucket,
        "bound": {
            "type": "outer bound on the coverage point under the new ruling",
            "low": bound_by_baseline["labeller_1"]["low"],
            "high": bound_by_baseline["labeller_1"]["high"],
            "low_basis": ("the new ruling is a superset of the old one (it relaxes the "
                          "addressee filter), so operator units can only be added, never "
                          "removed. The coverage point therefore cannot fall below the old "
                          "point on this construction."),
            "formula": ("high = old_point + (sum over buckets of population_b * "
                        "phone_operator_rows_b / n_b) / total_operator_units_old"),
            "upper_end_is_a_bound_not_a_measurement": True,
            "upper_end_note": (
                "The upper end is an arithmetic bound, not a measurement and not an estimate "
                "of the figure under the new ruling. It assumes every operator-authored row "
                "in a phone-channel row is newly included AND is included in the numerator "
                "bucket, which is the allocation most favourable to coverage. It is "
                "deliberately generous: most phone-channel operator rows were ALREADY counted "
                "under the old authorship-based labels, so this bound double counts them."),
            "per_bucket_phone_operator_units": bound_units,
            "by_baseline": bound_by_baseline,
        },
        "derived_tighter_range": {
            "type": ("range derived from the rubric asymmetry actually recorded in the "
                     "artefacts"),
            "basis": (
                "The old definition was NOT applied uniformly. The cited and askcue rubrics "
                "were authorship based with no addressee filter, so those buckets are already "
                "valid under the new ruling and are unchanged. Only the nonask rubric carried "
                "the addressee filter, and the nonask bucket appears in the DENOMINATOR only, "
                "never in the numerator. So any operator rows the new ruling adds to the "
                "nonask bucket can only push the coverage point DOWN, never up. The recorded "
                "flip candidates are the non-operator rows in human channels: 4 of 60 in the "
                "nonask labeller 2 labels."),
            "by_baseline": derived_by_baseline,
            "note": ("This range is tighter than the outer bound above but it is still a bound, "
                     "not a measurement: the low end assumes every flip candidate in the "
                     "nonask bucket is operator-authored, the high end assumes none is."),
        },
        "rubric_asymmetry_finding": {
            "finding": (
                "The three old points (0.0847, 0.0807, 0.0788) do not correspond to one "
                "definition. The nonask rubric and the adjudication rubric define operator as "
                "'addressed to an agent'. The cited rubric and the askcue rubric define "
                "operator as 'Koosha's own words' with peer as 'a person who is not Koosha', "
                "i.e. authorship only, with no addressee filter. 44 of the 58 operator rows "
                "in the cited bucket are phone-channel rows counted under the authorship "
                "reading."),
            "consequence": (
                "Before the new ruling is applied, the operator-coverage figure is not a "
                "single well defined quantity. The ruling resolves the definition going "
                "forward; it does not retroactively reconcile the three existing points."),
            "evidence": list(ADDRESS_FILTERED_RUBRICS) + ["cited_speaker_sheet.json instructions",
                                                          "askcue_speaker_sheet.json instructions"],
        },
        "caveats": [
            ("channel is NOT a recorded audience. Phone and iMessage rows include operator "
             "traffic to agents through the instinct and hermes bridges, so a phone-channel row "
             "can be addressed to an agent. Channel is used here only as the recorded "
             "structural proxy that the task specifies, not as an audience fact."),
            ("the outer bound's upper end double counts: most phone-channel operator rows were "
             "already counted under the old authorship-based labels."),
            ("labeller 1 per-item labels for the nonask bucket are LOST (nonask_scored.json "
             "label_restore_note: per-item speaker attribution from pass 1 is LOST, only "
             "aggregates survive). The nonask bound therefore uses the labeller 2 per-item "
             "rows or a stated worst case."),
            ("each bucket share comes from its own n=60 sample; the three samples are not "
             "independent of each other."),
            ("shares are applied to fixed population counts with no design effect and no "
             "finite population correction."),
            ("citation precision is unmeasured, so the figure is an estimate of coverage, not "
             "a published rate."),
        ],
        "what_would_close_it": [
            ("add an audience field (recipient or counterparty or chat kind or is_group) at "
             "extraction time, per unit, so addressee is a recorded fact rather than an "
             "inference"),
            ("or re-label the nonask bucket under the new rubric (operator = Koosha's own "
             "words, any audience), with the same two independent labellers and an "
             "adjudication pass, and re-derive the figure from the new labels"),
        ],
        "not_modified": ["operator_coverage.json", "operator_coverage_l2.json",
                         "adjudication.json", "any markdown"],
    }

    if check_only:
        if not os.path.exists(OUT):
            raise SystemExit("check only: %s does not exist" % OUT)
        with open(OUT, encoding="utf-8") as fh:
            existing = json.load(fh)
        existing.pop("generated_at_utc", None)
        candidate = dict(doc)
        candidate.pop("generated_at_utc", None)
        if existing != candidate:
            a = json.dumps(existing, indent=1, sort_keys=True).splitlines()
            b = json.dumps(candidate, indent=1, sort_keys=True).splitlines()
            import difflib
            for line in list(difflib.unified_diff(a, b, "on_disk", "script", lineterm=""))[:80]:
                print(line)
            raise SystemExit("check only: %s differs from this script's output" % OUT)
        print("check only: %s matches this script's output" % os.path.basename(OUT))
        return

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print("wrote %s" % OUT)
    print("measurable=%s" % measurable)
    print("per-row fields: %s | label files add %s"
          % (key_fields["nonask"], label_fields))
    for baseline in baselines:
        b = bound_by_baseline[baseline]
        d = derived_by_baseline[baseline]
        print("%-11s old %.4f | outer bound [%.4f, %.4f] | derived range [%.4f, %.4f]"
              % (baseline, points[baseline], b["low"], b["high"], d["low"], d["high"]))


if __name__ == "__main__":
    main()
