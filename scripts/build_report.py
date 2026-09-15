#!/usr/bin/env python3
"""Build Chinese-first DEFINE reports from authoritative Seedream spec JSON."""

from __future__ import annotations
import argparse, base64, hashlib, html, io, json, os, tempfile, warnings
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps

VISUAL_IDS = ("V01","V02","V03","V04","V05","V06")
VISUAL_NAMES = ("主体处理","构图与布局","材质与视觉质感","色彩与光线","图形与文字","写实程度")
INTENT_IDS = ("I01","I02","I03")
INTENT_NAMES = ("Input Match","Transformation Match","Output Match")
LEVEL_SCORE = {0:0,1:25,2:50,3:75,4:100}
RUNTIME_INPUTS = {"Text only","Single image","Multiple images"}

def fail(message: str) -> None: raise ValueError(message)
def esc(value: object) -> str: return html.escape(str(value), quote=True)
def require_text(value: object, field: str, empty: bool=False) -> str:
    if not isinstance(value,str) or (not empty and not value.strip()): fail(f"{field} must be a non-empty string")
    return value

def validate_dimensions(items: object, ids: tuple[str,...], names: tuple[str,...], field: str) -> list[dict]:
    if not isinstance(items,list) or len(items)!=len(ids): fail(f"{field} must contain {len(ids)} dimensions")
    for i,(item,rid,name) in enumerate(zip(items,ids,names)):
        required={"id","name","level","score","commonPattern","variation","coverage","reason","conflictingReferences","severeConflict"}
        if not isinstance(item,dict) or set(item)!=required: fail(f"{field}[{i}] has invalid fields")
        if item["id"]!=rid or item["name"]!=name: fail(f"{field}[{i}] must be {rid} {name}")
        if item["level"] not in LEVEL_SCORE or item["score"]!=LEVEL_SCORE[item["level"]]: fail(f"{field}[{i}] score must match anchored level")
        require_text(item["commonPattern"],f"{field}[{i}].commonPattern"); require_text(item["reason"],f"{field}[{i}].reason")
        if not isinstance(item["variation"],str) or item["coverage"] not in {"ALL","ALMOST_ALL","MULTIPLE_MODES","WEAK","CONFLICTED"}: fail(f"{field}[{i}] evidence fields are invalid")
        if item["level"]==4 and (item["coverage"] not in {"ALL","ALMOST_ALL"} or item["variation"].strip()): fail(f"{field}[{i}] level 4 requires near-total coverage and no meaningful variation")
        if item["level"]==3 and not item["variation"].strip(): fail(f"{field}[{i}] level 3 must name its meaningful variation axis")
        if not isinstance(item["conflictingReferences"],list) or not all(isinstance(x,str) and x.strip() for x in item["conflictingReferences"]): fail(f"{field}[{i}].conflictingReferences is invalid")
        if not isinstance(item["severeConflict"],bool): fail(f"{field}[{i}].severeConflict must be boolean")
    return items

def validate_rule(rule: object, rid: str, field: str) -> dict:
    keys={"id","name","text","priority","score2","score1","score0"}
    if not isinstance(rule,dict) or set(rule)!=keys or rule["id"]!=rid: fail(f"{field} must define {rid} with the complete rubric")
    for key in ("name","text","score2","score1","score0"): require_text(rule[key],f"{field}.{key}")
    if rule["priority"] not in {"MUST","PREFERRED"}: fail(f"{field}.priority must be MUST or PREFERRED")
    if len(rule["text"]) > 70 or any(len(rule[key]) > 55 for key in ("score2","score1","score0")):
        fail(f"{field} definition and rubrics must stay concise")
    return rule

def validate_rule_quality(data: dict) -> None:
    rules=data["templateRules"]+data["visualQualityRules"]
    ids={r["id"] for r in rules}
    texts=[r["text"].strip("。；;，, ") for r in rules]
    if len(texts)!=len(set(texts)): fail("Rule Quality Gate: duplicate Rule definitions")
    for i,left in enumerate(texts):
        for right in texts[i+1:]:
            if len(left)>=8 and len(right)>=8 and (left in right or right in left):
                fail("Rule Quality Gate: one Rule contains another Rule")
    mapped={rid for item in data["promptRuleMap"] for rid in item["ruleIds"]}
    missing=ids-mapped
    if missing: fail(f"Rule Quality Gate: Prompt coverage missing for {sorted(missing)}")
    if any(len(item["ruleIds"])>=5 for item in data["promptRuleMap"]):
        fail("Rule Quality Gate: a Prompt sentence maps to five or more Rules; review overlap or compound wording")
    reviews=data.get("ruleQualityReview",[])
    if [x.get("ruleId") for x in reviews] != list(VISUAL_IDS): fail("Rule Quality Gate: V01–V06 completeness reviews must be present and ordered")
    for item in reviews:
        if not item.get("coverageComplete") or not item.get("stableFeatures") or not item.get("identityFeatures"):
            fail(f'Rule Quality Gate: {item.get("ruleId","V Rule")} is under-defined')

def validate_v03(data: dict) -> dict:
    required={"specVersion","templateName","runtimeInput","runtimeInputInferred","usageScenario","alignment","targetVisual","heroReference","templateRuleSearch","templateRules","visualQualityRules","ruleQualityReview","initialApplicability","fitTestPlan","tuneTestPlan","promptVersion","seedreamPrompt","promptRuleMap"}
    if set(data)!=required: fail("v0.3 spec fields do not match the contract")
    require_text(data["templateName"],"templateName"); require_text(data["usageScenario"],"usageScenario")
    if data["runtimeInput"] not in RUNTIME_INPUTS or not isinstance(data["runtimeInputInferred"],bool): fail("runtime input fields are invalid")
    alignment=data["alignment"]
    if not isinstance(alignment,dict) or set(alignment)!={"status","visual","intent","conflicts","recommendations"}: fail("alignment fields are invalid")
    for part,ids,names in (("visual",VISUAL_IDS,VISUAL_NAMES),("intent",INTENT_IDS,INTENT_NAMES)):
        value=alignment[part]
        if not isinstance(value,dict) or set(value)!={"score","status","severeConflict","reason","dimensions"}: fail(f"alignment.{part} fields are invalid")
        dims=validate_dimensions(value["dimensions"],ids,names,f"alignment.{part}.dimensions")
        expected=sum(x["score"] for x in dims)/len(dims)
        if abs(value["score"]-expected)>0.01: fail(f"alignment.{part}.score must equal anchored dimension average")
        passed=expected>=80 and not value["severeConflict"] and not any(x["severeConflict"] for x in dims)
        if value["status"]!=("PASS" if passed else "FAIL"): fail(f"alignment.{part}.status is inconsistent")
        require_text(value["reason"],f"alignment.{part}.reason")
    passed=alignment["visual"]["status"]=="PASS" and alignment["intent"]["status"]=="PASS"
    if alignment["status"]!=("ALIGNED" if passed else "NOT ALIGNED"): fail("alignment.status is inconsistent with both gates")
    for key in ("conflicts","recommendations"):
        if not isinstance(alignment[key],list) or not all(isinstance(x,str) and x.strip() for x in alignment[key]): fail(f"alignment.{key} is invalid")
    if passed:
        require_text(data["targetVisual"],"targetVisual"); require_text(data["heroReference"],"heroReference")
        if not isinstance(data["templateRules"],list): fail("templateRules must be an array and may be empty")
        for i,rule in enumerate(data["templateRules"],1): validate_rule(rule,f"T{i:02d}",f"templateRules[{i}]")
        if not isinstance(data["visualQualityRules"],list) or len(data["visualQualityRules"])!=6: fail("visualQualityRules must contain V01–V06")
        for i,rule in enumerate(data["visualQualityRules"],1):
            validate_rule(rule,f"V{i:02d}",f"visualQualityRules[{i}]")
            if rule["name"]!=VISUAL_NAMES[i-1]: fail(f"V{i:02d}.name must use the fixed taxonomy")
        search=data["templateRuleSearch"]
        if not isinstance(search,list) or not search: fail("templateRuleSearch must document an active Candidate T Rule search")
        retained={x.get("ruleId") for x in search if x.get("disposition")=="RETAINED"}
        if retained != {x["id"] for x in data["templateRules"]}: fail("templateRuleSearch retained IDs must match templateRules")
        app=data["initialApplicability"]
        if not isinstance(app,dict) or set(app)!={"status","p0Advantage","p1Supported","p2BoundaryNotRecommended"} or app["status"]!="INITIAL_HYPOTHESIS": fail("initialApplicability is invalid")
        for tier in ("p0Advantage","p1Supported","p2BoundaryNotRecommended"):
            if not isinstance(app[tier],list) or not app[tier]: fail(f"{tier} must not be empty")
            for item in app[tier]:
                if not isinstance(item,dict) or set(item)!={"description","rationale"}: fail(f"{tier} item is invalid")
                require_text(item["description"],tier); require_text(item["rationale"],tier)
        for plan_name,expected_runs,expected_counts in (("fitTestPlan",1,{"P0":4,"P1":2,"P2":2}),("tuneTestPlan",3,{"P0":6,"P1":4,"P2":2})):
            plan=data[plan_name]
            if not isinstance(plan,dict) or set(plan)!={"summary","rows"}: fail(f"{plan_name} is invalid")
            require_text(plan["summary"],f"{plan_name}.summary")
            tier_counts={"P0":0,"P1":0,"P2":0}; seen_test_ids=set()
            for row in plan.get("rows",[]):
                if not isinstance(row,dict) or set(row)!={"testId","tier","inputDescription","challengeVariable","inputCount","runsPerInput","totalOutputs"}: fail(f"{plan_name} row is invalid")
                require_text(row["inputDescription"],f"{plan_name}.inputDescription"); require_text(row["challengeVariable"],f"{plan_name}.challengeVariable")
                if row["inputCount"]!=1 or row["runsPerInput"]!=expected_runs or row["totalOutputs"]!=expected_runs: fail(f"{plan_name} rows must each use one distinct input × {expected_runs} run(s)")
                tier_counts[row["tier"]]+=1
                if row["testId"] != f'{row["tier"]}-{tier_counts[row["tier"]]:02d}' or row["testId"] in seen_test_ids: fail(f"{plan_name} IDs must be unique and sequential")
                seen_test_ids.add(row["testId"])
            if tier_counts != expected_counts: fail(f"{plan_name} default tier counts must be {expected_counts}")
        if data["promptVersion"]!="0.0": fail("DEFINE Prompt version must be 0.0")
        require_text(data["seedreamPrompt"],"seedreamPrompt")
        valid_ids={r["id"] for r in data["templateRules"]+data["visualQualityRules"]}
        if not isinstance(data["promptRuleMap"],list) or not data["promptRuleMap"]: fail("promptRuleMap must not be empty")
        for item in data["promptRuleMap"]:
            if not isinstance(item,dict) or set(item)!={"sentence","ruleIds"}: fail("promptRuleMap item is invalid")
            require_text(item["sentence"],"promptRuleMap.sentence")
            if not isinstance(item["ruleIds"],list) or not item["ruleIds"] or len(item["ruleIds"])!=len(set(item["ruleIds"])) or not set(item["ruleIds"])<=valid_ids: fail("promptRuleMap.ruleIds contains duplicate or unknown Rules")
        validate_rule_quality(data)
    else:
        empties=("targetVisual","heroReference","templateRuleSearch","templateRules","visualQualityRules","ruleQualityReview","fitTestPlan","tuneTestPlan","promptVersion","seedreamPrompt","promptRuleMap")
        if any(data[k] not in ("",[],{}) for k in empties): fail("Template Definition and Prompt must be empty when Alignment fails")
    return data

def validate_spec(data: object) -> dict:
    if not isinstance(data,dict): fail("spec root must be an object")
    if data.get("specVersion")=="0.4":
        from define_v04 import validate
        return validate(data)
    if data.get("specVersion")=="0.3": return validate_v03(data)
    # Preserve v0.2/legacy reads without changing their authoritative structure.
    for key in ("templateName","runtimeInput","runtimeInputInferred","alignment","targetVisual","visualDNA","keywords","must","avoid","seedreamPrompt"):
        if key not in data: fail(f"legacy spec missing {key}")
    return data

def image_uri(path: Path) -> str:
    Image.MAX_IMAGE_PIXELS=40_000_000
    with warnings.catch_warnings():
        warnings.simplefilter("error",Image.DecompressionBombWarning)
        with Image.open(path) as probe: probe.verify()
        with Image.open(path) as source:
            image=ImageOps.exif_transpose(source).convert("RGB"); image.thumbnail((720,720),Image.Resampling.LANCZOS)
            buf=io.BytesIO(); image.save(buf,format="JPEG",quality=82,optimize=True)
    return "data:image/jpeg;base64,"+base64.b64encode(buf.getvalue()).decode("ascii")

def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as f: f.write(value)
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise

def figures(uris:list[str], hero:str="") -> str:
    return '<div class="references" style="--ref-count:%d">%s</div>'%(len(uris),''.join(f'<figure class="reference"><img src="{u}" alt="参考图 {i}"><figcaption>{"★ Hero · " if hero==f"R{i:02d}" else ""}参考图 {i}</figcaption></figure>' for i,u in enumerate(uris,1)))

def compose(template:str,title:str,body:str)->str:
    return template.replace("{{DOCUMENT_TITLE}}",esc(title)).replace("{{REPORT_BODY}}",body).replace("{{COPY_SCRIPT}}","")

def alignment_body(spec:dict,uris:list[str])->str:
    a=spec["alignment"]; v=a["visual"]; intent=a["intent"]; passed=a["status"]=="ALIGNED"
    cards=''.join(f'<article class="metric"><div class="label">{d["id"]} · {esc(d["name"])}</div><div class="verdict">{round(d["score"])}</div><p>{esc(d["reason"])}</p></article>' for d in v["dimensions"])
    conflicts=''.join(f'<li>{esc(x)}</li>' for x in a["conflicts"]) or "<li>未发现严重冲突</li>"
    recs=''.join(f'<li>{esc(x)}</li>' for x in a["recommendations"]) or "<li>继续 DEFINE</li>"
    fail_evidence="" if passed else f'<article class="card"><h2>冲突原文与证据</h2><p><strong>Usage Scenario：</strong>{esc(spec["usageScenario"])}</p><p><strong>Input：</strong>{esc(spec["runtimeInput"])}</p><ul>{conflicts}</ul></article>'
    return f'''<div class="page alignment-page"><header class="hero"><div><div class="eyebrow">DEFINE · 一致性报告 ALIGNMENT REPORT</div><h1>{esc(spec["templateName"])}</h1><p>Input：{esc(spec["runtimeInput"])}</p><p>Usage Scenario：{esc(spec.get("usageScenario","旧版未记录"))}</p></div><div class="score-card"><div class="label">结论</div><div class="status {"pass" if passed else "fail"}">{"PASS" if passed else "FAIL"}</div></div></header><section><h2>视觉一致性 VISUAL ALIGNMENT · {round(v["score"])}</h2><div class="alignment-grid">{cards}</div></section><section><h2>参考图 REFERENCE EVIDENCE</h2>{figures(uris)}</section><section class="grid-2"><article class="card"><h2>意图一致性 INTENT ALIGNMENT · {round(intent["score"])}</h2><p>{esc(intent["reason"])}</p></article><article class="card"><h2>UX 下一步</h2><ul>{recs}</ul></article>{fail_evidence}</section></div>'''

def rule_cards(rules:list[dict])->str:
    cards=[]
    for rule in rules:
        badge='<span class="pill must-badge">MUST</span>' if rule["priority"]=="MUST" else ""
        cards.append(f'<article class="card"><h3>{rule["id"]} · {esc(rule["name"])} {badge}</h3><p>{esc(rule["text"])}</p></article>')
    return ''.join(cards)

def score_sheet(rules:list[dict])->str:
    groups=[]
    for priority in ("MUST","PREFERRED"):
        rows=''.join(f'<tr><td>{r["id"]} · {esc(r["name"])}</td><td>{esc(r["score2"])}</td><td>{esc(r["score1"])}</td><td>{esc(r["score0"])}</td></tr>' for r in rules if r["priority"]==priority)
        if rows: groups.append(f'<h2>{priority}</h2><table><thead><tr><th>Rule</th><th>2 分</th><th>1 分</th><th>0 分</th></tr></thead><tbody>{rows}</tbody></table>')
    return ''.join(groups)

def blank_stage_sheet(rules:list[dict], stage:str, runs:int)->str:
    hint="记录该输入的 0 / 1 / 2" if runs==1 else "按运行顺序记录 0 / 1 / 2，例如 2 / 1 / 2"
    rows=''.join(f'<tr><td>{r["id"]}</td><td>{r["priority"]}</td><td class="blank-cell"></td><td></td></tr>' for r in rules)
    return f'''<div class="page"><div class="title-row"><h1>{stage} 评分表 <span>{stage} SCORE SHEET</span></h1><div class="prompt-version-fill">Prompt v____</div></div><p class="muted">{hint}；不适用写 N/A，最后填写 Rule Score。</p><table><thead><tr><th>Rule</th><th>类型</th><th>测试结果记录</th><th>Rule Score</th></tr></thead><tbody>{rows}</tbody></table></div>'''

def definition_body(spec:dict,uris:list[str],final_define:bool=False)->str:
    rules=spec["templateRules"]+spec["visualQualityRules"]; app=spec["initialApplicability"]; fit_plan=spec["fitTestPlan"]; tune_plan=spec["tuneTestPlan"]
    app_html=''.join(f'<article class="card"><h3>{label}</h3>'+''.join(f'<p><strong>{esc(x["description"])}</strong><br><span class="muted">{esc(x["rationale"])}</span></p>' for x in app[key])+'</article>' for label,key in (("P0 Advantage","p0Advantage"),("P1 Supported","p1Supported"),("P2 Boundary / Not Recommended","p2BoundaryNotRecommended")))
    last_tier=None
    plan_rows=[]
    for r in fit_plan["rows"]:
        tier=r["tier"] if r["tier"]!=last_tier else ""
        plan_rows.append(f'<tr><td><strong>{tier}</strong></td><td>{r["testId"]}</td><td>{esc(r["inputDescription"])}</td><td>{esc(r["challengeVariable"])}</td><td>{r["runsPerInput"]}</td></tr>')
        last_tier=r["tier"]
    plan_rows=''.join(plan_rows)
    tune_plan_rows=''.join(f'<tr><td>{r["tier"]}</td><td>{r["testId"]}</td><td>{esc(r["inputDescription"])}</td><td>{esc(r["challengeVariable"])}</td><td>{r["runsPerInput"]}</td></tr>' for r in tune_plan["rows"])
    mapping=''.join(f'<tr><td>{esc(x["sentence"])}</td><td>{", ".join(x["ruleIds"])}</td></tr>' for x in spec["promptRuleMap"])
    fit_sheet=blank_stage_sheet(rules,"FIT",1)
    tune_sheet=blank_stage_sheet(rules,"TUNE",3)
    hero_index=int(spec["heroReference"][1:])-1 if spec["heroReference"].startswith("R") else 0
    t_rules=rule_cards(spec["templateRules"]) if spec["templateRules"] else '<p class="empty-note">已主动搜索 Candidate Template Rules；经 overlap review 后没有独立 T Rule 被保留。</p>'
    return f'''
<div class="page"><div class="eyebrow">{"FINAL DEFINE · 最终模板定义报告 FINAL TEMPLATE DEFINITION REPORT" if final_define else "DEFINE · 模板定义报告 TEMPLATE DEFINITION REPORT"}</div><h1>{esc(spec["templateName"])}</h1><section class="grid-2 snapshot"><article><h2>模板描述 TEMPLATE DESCRIPTION</h2><p>{esc(spec["targetVisual"])}</p><h2>使用场景 USAGE SCENARIO</h2><p>{esc(spec["usageScenario"])}</p></article><figure class="reference hero-reference"><img src="{uris[hero_index]}" alt="Hero Reference"><figcaption>Hero Reference · {esc(spec["heroReference"])}</figcaption></figure></section><section><h2>模板规则 TEMPLATE RULES</h2><div class="grid-2">{t_rules}</div></section><section><h2>视觉品质规则 VISUAL QUALITY RULES</h2><div class="grid-2">{rule_cards(spec["visualQualityRules"])}</div></section><section><h2>支持输入 SUPPORTED INPUTS</h2><div class="grid-3">{app_html}</div></section></div>
<div class="page"><h1>规则评分表 <span>RULE SCORING SHEET</span></h1>{score_sheet(rules)}</div>
<div class="page"><h1>FIT 测试计划 <span>FIT TEST PLAN</span></h1><p>{esc(fit_plan["summary"])}</p><table><thead><tr><th></th><th>Test ID</th><th>建议测试输入</th><th>主要挑战变量</th><th>每图运行</th></tr></thead><tbody>{plan_rows}</tbody></table><section class="prompt-box"><div class="prompt-head"><strong>Prompt v{esc(spec["promptVersion"])}</strong><span>当前 Prompt CURRENT PROMPT</span></div><p class="prompt">{esc(spec["seedreamPrompt"])}</p></section><h2>Prompt–Rule 映射表</h2><table><thead><tr><th>Prompt 内容</th><th>对应 Rule</th></tr></thead><tbody>{mapping}</tbody></table></div>
{fit_sheet}
<div class="page"><div class="title-row"><h1>TUNE 测试计划 <span>TUNE TEST PLAN</span></h1><div class="prompt-version-fill">Prompt v____</div></div><p>{esc(tune_plan["summary"])}</p><table><thead><tr><th>Tier</th><th>Test ID</th><th>固定测试输入</th><th>主要挑战变量</th><th>每图运行</th></tr></thead><tbody>{tune_plan_rows}</tbody></table></div>
{tune_sheet}'''

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("spec",type=Path); p.add_argument("--output-dir",required=True,type=Path); p.add_argument("--reference",action="append",required=True,type=Path,dest="references"); p.add_argument("--template",type=Path,default=Path(__file__).resolve().parent.parent/"templates/report.html"); p.add_argument("--final-define",action="store_true"); return p.parse_args()

def main()->int:
    args=parse_args()
    if not 3<=len(args.references)<=6: fail("provide 3–6 reference images")
    spec=validate_spec(json.loads(args.spec.read_text(encoding="utf-8"))); uris=[image_uri(p) for p in args.references]; template=args.template.read_text(encoding="utf-8"); out=args.output_dir
    if spec.get("specVersion")=="0.4":
        from define_v04 import ready, alignment_body as v04_alignment, definition_body as v04_definition, audit_body
        if spec.get('reviewReport'):
            from compact_report import definition_html as v04_definition, chat_summary
            atomic_write(out/"define-review.md", chat_summary(spec))
        if len(uris) != len(spec['references']): fail('reference argument count differs from reference manifest')
        if not spec.get('reviewReport'):
            atomic_write(out/'alignment-report.html', compose(template, spec['templateName']+' · 目标确认', v04_alignment(spec, uris)))
        atomic_write(out/'traversal-audit.html', compose(template, spec['templateName']+' · 遍历审计', audit_body(spec)))
        if ready(spec) or spec.get('reviewReport'):
            name='final-template-definition-report.html' if args.final_define else 'template-definition-report.html'
            atomic_write(out/name, compose(template, spec['templateName']+' · DEFINE', v04_definition(spec, uris, args.final_define)))
            atomic_write(out/('prompt-final-define.txt' if args.final_define else 'prompt-'+spec['promptVersion']+'.txt'), spec['seedreamPrompt'])
            if not args.final_define: atomic_write(out/'prompt.txt', spec['seedreamPrompt'])
            atomic_write(out/'seedream-prompt-guide.md', (Path(__file__).resolve().parent.parent/'references/seedream-prompt-guide.md').read_text())
    elif spec.get("specVersion")=="0.3":
        if not args.final_define:
            alignment=compose(template,f'{spec["templateName"]} · Alignment',alignment_body(spec,uris)); atomic_write(out/"alignment-report.html",alignment)
        if spec["alignment"]["status"]=="ALIGNED":
            report_name="final-template-definition-report.html" if args.final_define else "template-definition-report.html"
            prompt_name="prompt-final-define.txt" if args.final_define else "prompt.txt"
            definition=compose(template,f'{spec["templateName"]} · {"Final " if args.final_define else ""}Template Definition',definition_body(spec,uris,args.final_define)); atomic_write(out/report_name,definition); atomic_write(out/prompt_name,spec["seedreamPrompt"])
            if not args.final_define: atomic_write(out/f'prompt-{spec["promptVersion"]}.txt',spec["seedreamPrompt"])
    else:
        # Legacy cases remain rebuildable through a compact compatibility view.
        body=f'<div class="page"><h1>{esc(spec["templateName"])}</h1><p>{esc(spec["targetVisual"])}</p>{figures(uris)}<section class="prompt-box"><h2>Prompt V0.1</h2><p class="prompt">{esc(spec["seedreamPrompt"])}</p></section></div>'
        atomic_write(out/"report.html",compose(template,spec["templateName"],body))
        if spec["seedreamPrompt"]: atomic_write(out/"prompt.txt",spec["seedreamPrompt"])
    return 0

if __name__=="__main__": raise SystemExit(main())
