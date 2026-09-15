#!/usr/bin/env python3
"""Regression checks for the DEFINE Rule Quality Gate."""

from __future__ import annotations
import copy, json
from pathlib import Path
from build_report import validate_rule_quality, validate_spec

ROOT=Path(__file__).resolve().parent.parent
SAMPLE=ROOT/"cases/shouzhang-stickers/define/template-spec.json"

def expect_failure(data:dict,label:str)->None:
    try: validate_rule_quality(data)
    except ValueError: return
    raise AssertionError(f"{label} should fail Rule Quality Gate")

def main()->int:
    sample=json.loads(SAMPLE.read_text(encoding="utf-8"))
    validate_spec(sample)
    valid={"templateRules":copy.deepcopy(sample["templateRules"]),"visualQualityRules":copy.deepcopy(sample["visualQualityRules"]),"promptRuleMap":copy.deepcopy(sample["promptRuleMap"]),"ruleQualityReview":copy.deepcopy(sample["ruleQualityReview"])}
    validate_rule_quality(valid)

    duplicate=copy.deepcopy(valid)
    duplicate["templateRules"][0]["text"]=duplicate["visualQualityRules"][0]["text"]
    expect_failure(duplicate,"T/V duplicate")

    contained=copy.deepcopy(valid)
    contained["templateRules"][0]["text"]=contained["visualQualityRules"][0]["text"]+"，并保持完整。"
    expect_failure(contained,"T/V containment")

    broad=copy.deepcopy(valid)
    broad["promptRuleMap"][0]["ruleIds"]=["T01","V01","V02","V03","V04"]
    expect_failure(broad,"over-broad Prompt mapping")

    gap=copy.deepcopy(valid)
    gap["promptRuleMap"]=[x for x in gap["promptRuleMap"] if "V05" not in x["ruleIds"]]
    expect_failure(gap,"Prompt coverage gap")

    under_defined=copy.deepcopy(valid)
    under_defined["ruleQualityReview"][3]["stableFeatures"]=[]
    expect_failure(under_defined,"V04 under-definition")

    print("Rule Quality Gate regression checks passed")
    return 0

if __name__=="__main__": raise SystemExit(main())
