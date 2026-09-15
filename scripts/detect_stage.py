#!/usr/bin/env python3
"""Detect the earliest valid next action for a local Seedream template case."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Tuple

from build_report import validate_spec
from build_stage_report import validate_comparison, validate_final, validate_fit, validate_round1


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
BATCH_KEYS = {"schemaVersion", "batchId", "lineageId", "defineSpecSha256", "purpose", "model", "promptArtifact", "promptSha256", "fixedSetId", "ready", "cases"}
CASE_KEYS = {"caseId", "applicabilityTier", "inputText", "inputAssets", "outputs", "notes"}
ASSET_KEYS = {"path", "sha256"}
OUTPUT_KEYS = {"outputId", "path", "sha256"}


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def result(stage: str, action: str, reason: str, missing: Optional[List[str]] = None, warnings: Optional[List[str]] = None) -> dict:
    return {"stage": stage, "action": action, "reason": reason, "missing": missing or [], "warnings": warnings or []}


def validate_asset(item: object, folder: Path, *, output: bool, seen_ids: set) -> List[str]:
    label = "output" if output else "input asset"
    required = OUTPUT_KEYS if output else ASSET_KEYS
    if not isinstance(item, dict) or set(item) != required:
        return [f"{label} must contain exactly {', '.join(sorted(required))}"]
    errors = []
    if output:
        output_id = item.get("outputId")
        if not isinstance(output_id, str) or not ID_RE.fullmatch(output_id) or output_id in seen_ids:
            errors.append("outputId is missing, invalid, or duplicated")
        seen_ids.add(output_id)
    rel = item.get("path")
    digest = item.get("sha256")
    if not isinstance(rel, str) or not rel.strip():
        return errors + [f"{label}.path is required"]
    asset_path = (folder / rel).resolve()
    if not inside(asset_path, folder):
        errors.append(f"{label} path escapes its batch folder: {rel}")
    elif not asset_path.is_file():
        errors.append(f"{label} does not exist: {asset_path}")
    elif not isinstance(digest, str) or not HASH_RE.fullmatch(digest) or digest != sha256_file(asset_path):
        errors.append(f"{label} hash mismatch: {asset_path}")
    return errors


def batch_state(path: Path, purpose: str, expected_prompt: Path, case_dir: Path, define_spec_hash: str) -> Tuple[Optional[dict], List[str], List[str]]:
    if not path.is_file():
        return None, [str(path)], []
    batch = load_json(path)
    errors: List[str] = []
    warnings: List[str] = []
    if set(batch) != BATCH_KEYS:
        errors.append(f"{path} must contain exactly the test-batch schema fields")
    for key in ("batchId", "lineageId", "fixedSetId"):
        if not isinstance(batch.get(key), str) or not ID_RE.fullmatch(batch[key]):
            errors.append(f"{key} is missing or invalid")
    if batch.get("defineSpecSha256") != define_spec_hash:
        errors.append("defineSpecSha256 does not match the current DEFINE spec")
    if batch.get("schemaVersion") != "0.1" or batch.get("purpose") != purpose:
        errors.append(f"schemaVersion must be 0.1 and purpose must be {purpose}")
    if not isinstance(batch.get("model"), str) or not batch["model"].strip():
        errors.append("model is required")
    if batch.get("ready") is not True:
        errors.append("ready must be true only after the user confirms the batch is complete")
    prompt_ref = batch.get("promptArtifact")
    if not isinstance(prompt_ref, str) or not prompt_ref.strip():
        errors.append("promptArtifact is required")
    else:
        prompt_path = (path.parent / prompt_ref).resolve()
        if not inside(prompt_path, case_dir):
            errors.append("promptArtifact must stay inside the current case")
        elif prompt_path != expected_prompt.resolve():
            errors.append(f"promptArtifact must reference the authoritative stage prompt: {expected_prompt}")
        elif not prompt_path.is_file():
            errors.append(f"authoritative prompt does not exist: {prompt_path}")
        elif batch.get("promptSha256") != sha256_file(prompt_path):
            errors.append("promptSha256 does not match the authoritative prompt")
    cases = batch.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array")
        cases = []
    elif len(cases) < 8:
        warnings.append(f"Limited evidence: {len(cases)} cases; 8–12 are recommended, not a scientific threshold.")
    seen_cases, seen_outputs = set(), set()
    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict) or not set(case) <= CASE_KEYS or not {"caseId", "applicabilityTier", "inputAssets", "outputs"} <= set(case):
            errors.append(f"case #{index} has invalid fields")
            continue
        case_id = case.get("caseId")
        if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id) or case_id in seen_cases:
            errors.append(f"case #{index} has a missing, invalid, or duplicate caseId")
        seen_cases.add(case_id)
        if case.get("applicabilityTier") not in {"P0", "P1", "P2"}:
            errors.append(f"{case_id or index} has an invalid applicabilityTier")
        inputs, outputs = case.get("inputAssets"), case.get("outputs")
        if not isinstance(inputs, list):
            errors.append(f"{case_id or index}.inputAssets must be an array")
            inputs = []
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"{case_id or index}.outputs must be a non-empty array")
            outputs = []
        input_text = case.get("inputText")
        if (input_text is not None and (not isinstance(input_text, str) or not input_text.strip())) or (not input_text and not inputs):
            errors.append(f"{case_id or index} must have non-empty inputText or at least one input asset")
        for item in inputs:
            errors.extend(validate_asset(item, path.parent, output=False, seen_ids=seen_outputs))
        for item in outputs:
            errors.extend(validate_asset(item, path.parent, output=True, seen_ids=seen_outputs))
    return (batch if not errors else None), errors, warnings


def fixed_set_signature(batch: dict) -> tuple:
    cases = []
    for case in batch["cases"]:
        inputs = tuple(item["sha256"] for item in case["inputAssets"])
        cases.append((case["caseId"], case["applicabilityTier"], case.get("inputText"), inputs))
    return batch["lineageId"], batch["model"], batch["fixedSetId"], tuple(sorted(cases))


def same_fixed_set(baseline: dict, candidate: dict, candidate_path: Path) -> List[str]:
    if fixed_set_signature(baseline) == fixed_set_signature(candidate):
        return []
    return [f"{candidate_path} must match baseline lineage, model, fixedSetId, case IDs, tiers, text, and ordered input hashes"]


def analysis_link(analysis: dict, batch: dict, *, fit: bool = False) -> List[str]:
    errors = []
    if analysis.get("sourceBatch") != batch.get("batchId") or analysis.get("lineageId") != batch.get("lineageId"):
        errors.append("analysis sourceBatch/lineageId does not match its authoritative batch")
    if fit and (analysis.get("model") != batch.get("model") or analysis.get("caseCount") != len(batch.get("cases", []))):
        errors.append("FIT model/caseCount does not match its authoritative batch")
    return errors


def prompt_matches(spec: dict, prompt_path: Path) -> bool:
    return prompt_path.is_file() and isinstance(spec.get("seedreamPrompt"), str) and prompt_path.read_text(encoding="utf-8") == spec["seedreamPrompt"]

def stage_dir(case_dir:Path,canonical:str,legacy:str)->Path:
    canonical_path=case_dir/canonical; legacy_path=case_dir/legacy
    return canonical_path if canonical_path.exists() or not legacy_path.exists() else legacy_path

def validate_ux_rule_review(review:dict,fit:dict,base_hash:str)->List[str]:
    required={"schemaVersion","status","baseDefineSpecSha256","updatedDefineSpecSha256","failureDecisions","newSuggestions","organizedRuleChanges","uxSummary","uxConfirmed"}
    errors=[]
    if set(review)!=required or review.get("schemaVersion")!="0.1": return ["UX Rule Review fields or schemaVersion are invalid"]
    if review.get("baseDefineSpecSha256")!=base_hash: errors.append("baseDefineSpecSha256 does not match the FIT DEFINE spec")
    if review.get("status") not in {"DRAFT","CONFIRMED"}: errors.append("status must be DRAFT or CONFIRMED")
    if not isinstance(review.get("uxSummary"),str) or not review["uxSummary"].strip(): errors.append("uxSummary is required")
    decisions=review.get("failureDecisions")
    if not isinstance(decisions,list): decisions=[]; errors.append("failureDecisions must be an array")
    expected={x["id"] for x in fit.get("failures",[])}; actual={x.get("failureId") for x in decisions if isinstance(x,dict)}
    if actual!=expected: errors.append("failureDecisions must cover every current Fxx exactly")
    for item in decisions:
        if not isinstance(item,dict) or item.get("decision") not in {"RETAIN","MERGE","REMOVE"} or item.get("proposedPriority") not in {"MUST","PREFERRED"} or not isinstance(item.get("rationale"),str) or not item["rationale"].strip():
            errors.append("each failure decision needs decision, MUST/PREFERRED, and rationale")
    suggestions=review.get("newSuggestions")
    if not isinstance(suggestions,list): suggestions=[]; errors.append("newSuggestions must be an array")
    for item in suggestions:
        if not isinstance(item,dict) or item.get("proposedPriority") not in {"MUST","PREFERRED"} or item.get("disposition") not in {"ADD_FAILURE","MERGE_RULE","REJECT"}:
            errors.append("each new suggestion needs MUST/PREFERRED and an agent disposition")
    changes=review.get("organizedRuleChanges")
    if not isinstance(changes,list): errors.append("organizedRuleChanges must be an array")
    if review.get("status")=="CONFIRMED":
        if review.get("uxConfirmed") is not True: errors.append("CONFIRMED review requires uxConfirmed=true")
        if not isinstance(review.get("updatedDefineSpecSha256"),str) or not HASH_RE.fullmatch(review["updatedDefineSpecSha256"]): errors.append("CONFIRMED review requires updatedDefineSpecSha256")
    elif review.get("uxConfirmed") is not False or review.get("updatedDefineSpecSha256") is not None:
        errors.append("DRAFT review must remain unconfirmed and have null updatedDefineSpecSha256")
    return errors


def detect(case_dir: Path) -> dict:
    case_dir = case_dir.resolve()
    define = stage_dir(case_dir,"1.define","define")
    fit_dir = stage_dir(case_dir,"2.fit","fit")
    tune_dir = stage_dir(case_dir,"3.tune","tune")
    release_dir = stage_dir(case_dir,"5.release","release")
    spec_path = define / "template-spec.json"
    if not spec_path.is_file() and (define / "spec.json").is_file():
        spec_path = define / "spec.json"
    if not spec_path.is_file():
        from PIL import Image
        reference_dir = case_dir / "0.reference"
        if not reference_dir.is_dir():
            reference_dir = define / "references"
        refs = []
        for path in reference_dir.glob("*"):
            if not path.is_file():
                continue
            try:
                with Image.open(path) as image:
                    image.verify()
                refs.append(path)
            except (OSError, ValueError):
                continue
        return result("DEFINE", "RUN_DEFINE" if 3 <= len(refs) <= 6 else "WAIT_DEFINE", "A valid Template Spec has not been created.", [] if 3 <= len(refs) <= 6 else [str(define / "template-spec.json"), "3–6 readable Golden References"])
    try:
        spec = validate_spec(load_json(spec_path))
    except (ValueError, KeyError, TypeError) as exc:
        return result("DEFINE", "FIX_DEFINE", f"Template Spec validation failed: {exc}", [str(spec_path)])
    v04 = spec.get("specVersion") == "0.4"
    if v04:
        from define_v04 import ready
        if spec.get("reviewReport") and not ready(spec):
            return result("DEFINE", "WAIT_UX_RULE_CONFIRMATION", "Review the initial Rules and priorities; reference consistency and target confirmation are separate from Rules approval.")
        if not ready(spec):
            return result("DEFINE", "WAIT_UX_TARGET_CONFIRMATION", "Complete actual UX target confirmation and resolve pending target questions; draft reports are not a formal handoff.")
    v03 = spec.get("specVersion") in {"0.3", "0.4"}
    aligned = True if v04 else (spec["alignment"]["status"] == "ALIGNED" if v03 else spec["alignment"]["score"] >= 80)
    if not aligned:
        return result("DEFINE", "DEFINE_STOP", "Visual Alignment or Intent Alignment failed; later stages are not allowed.")
    prompt_v01 = define / (f"prompt-{spec['promptVersion']}.txt" if v03 else "prompt-v01.txt")
    if not prompt_v01.is_file() and (define / "prompt.txt").is_file():
        prompt_v01 = define / "prompt.txt"
    if not prompt_matches(spec, prompt_v01):
        return result("DEFINE", "FIX_PROMPT_DRIFT", "Current Prompt artifact is missing or differs from the Template Spec.", [str(prompt_v01)])
    if v04 and spec.get("reviewReport"):
        define_deliverables = (define / "definition-review-to-ux.pdf", define / "testing-guide.pdf", define / "traversal-audit.html", define / "seedream-prompt-guide.md")
    elif v03:
        define_deliverables = (define / "alignment-report.html", define / "alignment-report.pdf", define / "template-definition-report.html", define / "template-definition-report.pdf")
        if v04:
            define_deliverables += (define / "traversal-audit.html", define / "seedream-prompt-guide.md")
    else:
        define_deliverables = (define / "report.html", define / "report.pdf")
    missing = [str(path) for path in define_deliverables if not path.is_file()]
    if missing:
        return result("DEFINE", "REBUILD_DEFINE", "DEFINE JSON is valid but reports are missing.", missing)

    if spec.get("reviewReport"):
        return result("TEST", "COLLECT_TEMPLATE_TESTS", "Use the 6/6/4 material suggestions and binary MUST criteria. Legacy numeric FIT/TUNE automation is not applicable to this report format.")

    fit_batch_path = fit_dir / "tests/batch.json"
    fit_analysis_path = fit_dir / "fit-analysis.json"
    spec_hash = sha256_file(spec_path)
    fit_batch, fit_errors, fit_warnings = batch_state(fit_batch_path, "FIT", prompt_v01, case_dir, spec_hash)
    if not fit_analysis_path.is_file():
        if any("defineSpecSha256" in error for error in fit_errors):
            return result("FIT", "NEW_LINEAGE_REQUIRED", "The existing FIT manifest belongs to a different DEFINE spec fingerprint.", [str(fit_batch_path)])
        if fit_errors:
            return result("FIT", "WAIT_FIT_RESULTS", "DEFINE is complete. Collect and confirm the FIT batch.", fit_errors, fit_warnings)
        return result("FIT", "RUN_FIT", "The FIT batch is complete and ready for failure diagnosis.", warnings=fit_warnings)
    if fit_errors:
        if any("defineSpecSha256" in error for error in fit_errors):
            return result("FIT", "NEW_LINEAGE_REQUIRED", "The existing FIT manifest belongs to a different DEFINE spec fingerprint.", [str(fit_batch_path)])
        return result("FIT", "FIX_FIT_BATCH", "FIT analysis exists but its source batch is invalid.", fit_errors, fit_warnings)
    fit = load_json(fit_analysis_path)
    try:
        validate_fit(fit)
    except (ValueError, KeyError, TypeError) as exc:
        return result("FIT", "FIX_FIT_ANALYSIS", f"FIT analysis validation failed: {exc}", [str(fit_analysis_path)])
    links = analysis_link(fit, fit_batch, fit=True)
    if links:
        return result("FIT", "FIX_FIT_ANALYSIS", "FIT analysis is not linked to its source batch.", links)
    fit_report = fit_dir / "fit-report.html"
    fit_pdf = fit_dir / "fit-report.pdf"
    missing_fit = [str(path) for path in ((fit_report, fit_pdf) if v03 else (fit_report,)) if not path.is_file()]
    if missing_fit:
        return result("FIT", "REBUILD_FIT_REPORT", "FIT analysis is valid but its formal report is missing.", missing_fit)
    if fit["status"] == "STOP":
        return result("FIT", "TERMINAL_FIT_STOP", "FIT concluded that prompt optimization is not recommended for this lineage.")

    if v03:
        review_path=fit_dir/"ux-rule-review.json"
        if not review_path.is_file():
            return result("FIT","WAIT_UX_RULE_REVIEW","FIT Report is complete. Ask UX to review every Fxx, provide any new suggestions, and state MUST or PREFERRED for each resulting Rule proposal.",[str(review_path)])
        review=load_json(review_path); review_errors=validate_ux_rule_review(review,fit,spec_hash)
        if review_errors: return result("FIT","FIX_UX_RULE_REVIEW","UX Rule Review is invalid.",review_errors)
        if review["status"]=="DRAFT":
            return result("FIT","WAIT_UX_FINAL_CONFIRMATION","Agent has organized UX feedback into Fxx and Rule changes. Report the organized changes and wait for explicit UX confirmation.",[str(review_path)])
        unresolved=[x["id"] for x in fit.get("candidateRules",[]) if x.get("uxDecision")=="PENDING"]
        if unresolved: return result("FIT","FIX_UX_RULE_REVIEW","Confirmed review still has unresolved Candidate Rules in FIT analysis.",unresolved)
        final_spec_path=define/"final-template-spec.json"
        if not final_spec_path.is_file():
            return result("DEFINE","APPLY_CONFIRMED_RULE_REVIEW","UX confirmed the organized changes. Apply them to a complete final DEFINE spec and rebuild Prompt mapping.",[str(final_spec_path)])
        try: final_spec=validate_spec(load_json(final_spec_path))
        except (ValueError,KeyError,TypeError) as exc: return result("DEFINE","FIX_FINAL_DEFINE",f"Final DEFINE validation failed: {exc}",[str(final_spec_path)])
        final_hash=sha256_file(final_spec_path)
        if review["updatedDefineSpecSha256"]!=final_hash: return result("DEFINE","FIX_FINAL_DEFINE","Final DEFINE hash does not match the UX-confirmed review.",[str(final_spec_path),str(review_path)])
        final_prompt=define/"prompt-final-define.txt"
        final_html=define/"final-template-definition-report.html"; final_pdf=define/"final-template-definition-report.pdf"
        if not prompt_matches(final_spec,final_prompt): return result("DEFINE","FIX_FINAL_DEFINE_PROMPT","Final DEFINE Prompt is missing or drifted.",[str(final_prompt)])
        missing_final=[str(x) for x in (final_html,final_pdf) if not x.is_file()]
        if missing_final: return result("DEFINE","REBUILD_FINAL_DEFINE_REPORT","UX confirmed the final Rule structure, but the complete Final Define Report is missing.",missing_final)
        tune_spec_hash=final_hash; tune_prompt=final_prompt
        tune_baseline_path = tune_dir / "tests/baseline/batch.json"
        tune_baseline, tune_errors, tune_warnings = batch_state(tune_baseline_path, "TUNE_BASELINE", tune_prompt, case_dir, tune_spec_hash)
        if tune_errors:
            return result("TUNE", "WAIT_TUNE_BASELINE", "Rule Freeze is complete. Collect the larger frozen TUNE baseline set; do not reuse the FIT breadth batch.", tune_errors, tune_warnings)
        if tune_baseline["lineageId"] != fit_batch["lineageId"] or tune_baseline["model"] != fit_batch["model"]:
            return result("TUNE", "NEW_LINEAGE_REQUIRED", "The TUNE baseline changes lineage or model relative to FIT.", [str(tune_baseline_path)])
        tune_path = tune_dir / "round-1-analysis.json"
        if not tune_path.is_file():
            return result("TUNE", "RUN_TESTER_TUNE", "The larger TUNE baseline is frozen. Tester may author the next Prompt and reuse this TUNE fixed set for every revision.", [str(tune_path)], tune_warnings)
        tune = load_json(tune_path)
        try:
            validate_round1(tune)
        except (ValueError, KeyError, TypeError) as exc:
            return result("TUNE", "FIX_TUNE_ANALYSIS", f"TUNE analysis validation failed: {exc}", [str(tune_path)])
        tune_report = tune_dir / "tuning-round-1.html"
        tune_pdf = tune_dir / "tuning-round-1.pdf"
        missing_tune = [str(path) for path in (tune_report, tune_pdf) if not path.is_file()]
        if missing_tune:
            return result("TUNE", "REBUILD_TUNE_REVIEW", "TUNE JSON is valid but the formal Tune Review is missing.", missing_tune)
        return result("TUNE", "REVIEW_TUNE_EVIDENCE", "Tester evidence is ready for agent review and final comparison.")

    baseline_path = tune_dir / "tests/baseline/batch.json"
    round1_path = tune_dir / "round-1-analysis.json"
    baseline, errors, warnings = batch_state(baseline_path, "TUNE_BASELINE", prompt_v01, case_dir, spec_hash)
    if not round1_path.is_file():
        if errors:
            return result("TUNE", "WAIT_TUNE_BASELINE", "FIT permits tuning. Collect the formal baseline batch.", errors, warnings)
        return result("TUNE", "RUN_TUNE_ROUND_1", "The formal baseline is complete; create consolidated Revision A.", warnings=warnings)
    if errors:
        return result("TUNE", "FIX_TUNE_BASELINE", "Round 1 exists but the formal baseline is invalid.", errors, warnings)
    if baseline["lineageId"] != fit_batch["lineageId"] or baseline["model"] != fit_batch["model"]:
        return result("TUNE", "NEW_LINEAGE_REQUIRED", "The formal baseline changes lineage or model relative to FIT; rerun FIT for the new definition/model.", [str(baseline_path)])
    round1 = load_json(round1_path)
    try:
        validate_round1(round1)
    except (ValueError, KeyError, TypeError) as exc:
        return result("TUNE", "FIX_TUNE_ROUND_1", f"Round 1 validation failed: {exc}", [str(round1_path)])
    links = analysis_link(round1, baseline)
    if links:
        return result("TUNE", "FIX_TUNE_ROUND_1", "Round 1 is not linked to the formal baseline.", links)
    prompt_a = tune_dir / "prompt-revision-a.txt"
    report_a = tune_dir / "tuning-round-1.html"
    if not prompt_a.is_file() or prompt_a.read_text(encoding="utf-8") != round1["promptRevision"]["text"] or not report_a.is_file():
        return result("TUNE", "REBUILD_TUNE_ROUND_1", "Revision A or its report is missing or drifted.", [str(prompt_a), str(report_a)])

    revision_a_path = tune_dir / "tests/revision-a/batch.json"
    round2_path = tune_dir / "round-2-analysis.json"
    revision_a, errors, warnings = batch_state(revision_a_path, "REVISION_A", prompt_a, case_dir, spec_hash)
    if not round2_path.is_file():
        if errors:
            return result("TUNE", "WAIT_REVISION_A_RESULTS", "Test Revision A on the identical fixed set.", errors, warnings)
        mismatch = same_fixed_set(baseline, revision_a, revision_a_path)
        if mismatch:
            return result("TUNE", "FIX_REVISION_A_TEST_SET", "Revision A did not use the formal fixed set.", mismatch)
        return result("TUNE", "RUN_TUNE_ROUND_2", "Revision A is complete; compare it with baseline.", warnings=warnings)
    if errors:
        return result("TUNE", "FIX_REVISION_A_BATCH", "Round 2 exists but the Revision A batch is invalid.", errors, warnings)
    mismatch = same_fixed_set(baseline, revision_a, revision_a_path)
    if mismatch:
        return result("TUNE", "FIX_REVISION_A_TEST_SET", "Revision A did not use the formal fixed set.", mismatch)
    round2 = load_json(round2_path)
    try:
        validate_comparison(round2)
    except (ValueError, KeyError, TypeError) as exc:
        return result("TUNE", "FIX_TUNE_ROUND_2", f"Round 2 validation failed: {exc}", [str(round2_path)])
    if round2.get("baselineBatch") != baseline["batchId"] or round2.get("candidateBatch") != revision_a["batchId"] or analysis_link(round2, revision_a):
        return result("TUNE", "FIX_TUNE_ROUND_2", "Round 2 batch or lineage links are invalid.", [str(round2_path)])
    if round2.get("testedPromptVersion") != "Revision A" or round2.get("testedPromptSha256") != revision_a["promptSha256"]:
        return result("TUNE", "FIX_TUNE_ROUND_2", "Round 2 does not identify the tested Revision A prompt.", [str(round2_path)])
    if round2.get("functionalRevisionCount") != 1:
        return result("TUNE", "FIX_TUNE_ROUND_2", "Round 2 must record exactly one tested functional revision (Revision A).", [str(round2_path)])
    tracked_ids = {item["id"] for item in round1["failures"]}
    compared_ids = {item["failureId"] for item in round2["comparisons"]}
    if compared_ids != tracked_ids or any(item["baselineFrequency"]["total"] != len(baseline["cases"]) for item in round2["comparisons"]):
        return result("TUNE", "FIX_TUNE_COMPARISON", "Round 2 must compare every Round 1 failure using the complete fixed-set denominator.", [str(round2_path)])
    if round2.get("nextAction") == "TEST_FINAL_PATCH":
        return result("TUNE", "FIX_TUNING_BUDGET", "Optional Final Patch is available only after a tested Revision B comparison.", [str(round2_path)])
    if round2["nextAction"] in {"CALIBRATE_RELEASE", "STOP"} and sha256_text(round2["releaseCandidatePrompt"]["text"]) != revision_a["promptSha256"]:
        return result("TUNE", "FIX_TUNE_ROUND_2", "Round 2 release candidate differs from the tested Revision A prompt.", [str(round2_path)])
    comparison_report = tune_dir / "tuning-comparison.html"
    if not comparison_report.is_file():
        return result("TUNE", "REBUILD_TUNING_COMPARISON", "Round 2 is valid but its report is missing.", [str(comparison_report)])

    final_evidence = revision_a
    final_analysis = round2
    next_action = round2["nextAction"]
    is_b = next_action == "TEST_REVISION_B"
    while next_action in {"TEST_REVISION_B", "TEST_FINAL_PATCH"}:
        if not is_b and next_action != "TEST_FINAL_PATCH":
            return result("TUNE", "FIX_TUNING_BUDGET", "No prompt may be proposed after the final patch.", [str(round2_path)])
        folder, purpose = ("revision-b", "REVISION_B") if is_b else ("final-patch", "FINAL_PATCH")
        expected_prompt = tune_dir / ("prompt-revision-b.txt" if is_b else "prompt-final-patch.txt")
        source_prompt = final_analysis.get("releaseCandidatePrompt", {}) if is_b else final_analysis.get("optionalFinalPatch", {}).get("prompt", {})
        expected_text = source_prompt.get("text") if isinstance(source_prompt, dict) else None
        if not expected_prompt.is_file() or not isinstance(expected_text, str) or expected_prompt.read_text(encoding="utf-8") != expected_text:
            return result("TUNE", "FIX_PROMPT_DRIFT", "The candidate prompt file differs from the prompt produced by the preceding analysis.", [str(expected_prompt)])
        candidate_path = tune_dir / f"tests/{folder}/batch.json"
        candidate, errors, warnings = batch_state(candidate_path, purpose, expected_prompt, case_dir, spec_hash)
        if errors:
            return result("TUNE", f"WAIT_{folder.replace('-', '_').upper()}_RESULTS", "Test the final prompt candidate on the identical fixed set.", errors, warnings)
        mismatch = same_fixed_set(baseline, candidate, candidate_path)
        if mismatch:
            return result("TUNE", "FIX_FINAL_TEST_SET", "The final prompt candidate did not use the formal fixed set.", mismatch)
        final_compare_path = tune_dir / "final-candidate-analysis.json" if is_b else tune_dir / "final-patch-analysis.json"
        if not final_compare_path.is_file():
            return result("TUNE", "RUN_FINAL_CANDIDATE_COMPARISON", "The final candidate results are complete; compare them before calibration.")
        final_analysis = load_json(final_compare_path)
        try:
            validate_comparison(final_analysis)
        except (ValueError, KeyError, TypeError) as exc:
            return result("TUNE", "FIX_FINAL_CANDIDATE_ANALYSIS", f"Final candidate comparison failed validation: {exc}", [str(final_compare_path)])
        expected_version = "Revision B" if is_b else "Final Patch"
        allowed_actions = {"CALIBRATE_RELEASE", "STOP", "TEST_FINAL_PATCH"} if is_b else {"CALIBRATE_RELEASE", "STOP"}
        invalid = (
            final_analysis.get("sourceBatch") != candidate["batchId"]
            or final_analysis.get("baselineBatch") != baseline["batchId"]
            or final_analysis.get("candidateBatch") != candidate["batchId"]
            or final_analysis.get("evaluatedBatch") != candidate["batchId"]
            or final_analysis.get("lineageId") != candidate["lineageId"]
            or final_analysis.get("testedPromptVersion") != expected_version
            or final_analysis.get("testedPromptSha256") != candidate["promptSha256"]
            or final_analysis.get("nextAction") not in allowed_actions
            or final_analysis.get("functionalRevisionCount") != (2 if is_b else 3)
        )
        if invalid:
            return result("TUNE", "FIX_FINAL_CANDIDATE_ANALYSIS", "Final candidate comparison is not linked to the tested candidate or tries to exceed the 2 + 1 budget.", [str(final_compare_path)])
        if {item["failureId"] for item in final_analysis["comparisons"]} != compared_ids or any(item["baselineFrequency"]["total"] != len(baseline["cases"]) for item in final_analysis["comparisons"]):
            return result("TUNE", "FIX_FINAL_CANDIDATE_ANALYSIS", "Final candidate comparison must cover every tracked failure using the complete fixed-set denominator.", [str(final_compare_path)])
        tested_prompt = final_analysis.get("releaseCandidatePrompt", {}).get("text")
        if final_analysis["nextAction"] == "TEST_FINAL_PATCH":
            patch_prompt = final_analysis.get("optionalFinalPatch", {}).get("prompt", {}).get("text")
            if not final_analysis.get("optionalFinalPatch", {}).get("eligible") or not isinstance(patch_prompt, str):
                return result("TUNE", "FIX_TUNING_BUDGET", "Revision B may request a Final Patch only when it is explicitly eligible.", [str(final_compare_path)])
        elif not isinstance(tested_prompt, str) or sha256_text(tested_prompt) != candidate["promptSha256"]:
            return result("TUNE", "FIX_FINAL_CANDIDATE_ANALYSIS", "Final release candidate differs from the tested prompt artifact.", [str(final_compare_path)])
        final_report = tune_dir / ("tuning-final-comparison.html" if is_b else "tuning-final-patch-comparison.html")
        if not final_report.is_file():
            return result("TUNE", "REBUILD_FINAL_COMPARISON", "Final candidate analysis is valid but its report is missing.", [str(final_report)])
        final_evidence = candidate
        next_action = final_analysis["nextAction"]
        is_b = False
    if next_action not in {"CALIBRATE_RELEASE", "STOP"}:
        return result("TUNE", "FIX_TUNING_ANALYSIS", "Round 2 nextAction is invalid.", [str(round2_path)])

    final_path = release_dir / "final-template-spec.json"
    if not final_path.is_file():
        action = "RUN_CALIBRATE_RELEASE_FAIL" if next_action == "STOP" else "RUN_CALIBRATE_RELEASE"
        return result("CALIBRATE", action, "Tuning evidence is complete; reconcile the spec and evaluate release gates.")
    final = load_json(final_path)
    try:
        validate_final(final)
    except (ValueError, KeyError, TypeError) as exc:
        return result("RELEASE", "FIX_FINAL_SPEC", f"Final Template Spec validation failed: {exc}", [str(final_path)])
    if final.get("lineageId") != final_evidence["lineageId"] or final.get("evidenceBatch") != final_evidence["batchId"] or final.get("testedPromptSha256") != final_evidence["promptSha256"]:
        return result("RELEASE", "FIX_FINAL_SPEC", "Final Template Spec is not bound to the final tested batch and prompt.", [str(final_path)])
    if sha256_text(final["releaseCandidatePrompt"]) != final_evidence["promptSha256"]:
        return result("RELEASE", "FIX_FINAL_SPEC", "Final release prompt differs from the tested prompt artifact.", [str(final_path)])
    if next_action == "STOP" and final["release"]["status"] != "FAIL":
        return result("RELEASE", "FIX_FINAL_SPEC", "A tuning STOP must produce Release FAIL.", [str(final_path)])
    initial_core = {item["id"] for group in (spec.get("must", []), spec.get("avoid", [])) for item in group if isinstance(item, dict) and item.get("constraintType") == "core"}
    final_core = {item["id"] for kind in ("must", "avoid") for item in final["coreConstraints"][kind]}
    final_preference = {item["id"] for kind in ("must", "avoid") for item in final["preferenceConstraints"][kind]}
    if not initial_core <= final_core or initial_core & final_preference:
        return result("RELEASE", "FIX_FINAL_SPEC", "Initial Core constraint IDs must remain Core and cannot be deleted or downgraded.", [str(final_path)])
    missing = [str(path) for path in (release_dir / "final-template-spec.html", release_dir / "release-package.html", release_dir / "release-package.pdf") if not path.is_file()]
    if missing:
        return result("RELEASE", "REBUILD_RELEASE_PACKAGE", "Final decisions are valid but release deliverables are missing.", missing)
    return result("RELEASE", "RELEASED", f"Release package is complete with status {final['release']['status']}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_directory", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        state = detect(args.case_directory)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(f"Stage: {state['stage']}")
        print(f"Action: {state['action']}")
        print(state["reason"])
        for item in state["missing"]:
            print(f"Missing: {item}")
        for item in state["warnings"]:
            print(f"Warning: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
