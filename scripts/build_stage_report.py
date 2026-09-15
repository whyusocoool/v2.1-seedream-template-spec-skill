#!/usr/bin/env python3
"""Build Chinese-first FIT/TUNE/CALIBRATE reports from authoritative JSON."""

from __future__ import annotations
import argparse, base64, html, io, json, os, tempfile, warnings
from pathlib import Path
from PIL import Image, ImageOps

def fail(message:str)->None: raise ValueError(message)
def esc(v:object)->str: return html.escape(str(v),quote=True)
def atomic(path:Path,value:str)->None:
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as f:f.write(value)
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise
def compose(template:str,title:str,body:str)->str:
    return template.replace("{{DOCUMENT_TITLE}}",esc(title)).replace("{{REPORT_BODY}}",body).replace("{{COPY_SCRIPT}}","")
def status_class(v:str)->str:
    return "pass" if v in {"GO","PASS","CALIBRATE_RELEASE","SOLVED","IMPROVED"} else "fail" if v in {"STOP","FAIL","REGRESSED"} else "warn"
def hero(name:str,label:str,status:str,subtitle:str="")->str:
    return f'<header class="hero"><div><div class="eyebrow">{esc(label)}</div><h1>{esc(name)}</h1><p class="subtitle">{esc(subtitle)}</p></div><div class="status-card"><div class="label">结论</div><div class="status {status_class(status)}">{esc(status)}</div></div></header>'

def fit_hero(name:str,status:str,model:str,prompt_version:str,case_count:int)->str:
    return f'<header class="hero fit-hero"><div><div class="eyebrow">规则评分 RULE SCORING</div><div class="fit-title-line"><h1>{esc(name)}</h1><span class="prompt-version">Prompt {esc(prompt_version)}</span><span class="model-version">{esc(model)}</span></div><p class="subtitle">{case_count} 个测试</p></div><div class="status-card"><div class="label">结论</div><div class="status {status_class(status)}">{esc(status)}</div></div></header>'

def image_uri(path:Path)->str:
    Image.MAX_IMAGE_PIXELS=40_000_000
    with warnings.catch_warnings():
        warnings.simplefilter("error",Image.DecompressionBombWarning)
        with Image.open(path) as probe: probe.verify()
        with Image.open(path) as source:
            image=ImageOps.exif_transpose(source).convert("RGB"); image.thumbnail((900,900),Image.Resampling.LANCZOS)
            buf=io.BytesIO(); image.save(buf,format="JPEG",quality=82,optimize=True)
    return "data:image/jpeg;base64,"+base64.b64encode(buf.getvalue()).decode("ascii")

def load_fit_evidence(batch_path:Path|None)->tuple[dict|None,Path|None]:
    if batch_path is None: return None,None
    batch=json.loads(batch_path.read_text(encoding="utf-8"))
    return batch,batch_path.parent

def fit_appendix(batch:dict|None,batch_dir:Path|None,rule_scores:list[dict]|None=None)->str:
    if not batch or batch_dir is None: return '<div class="page"><h1>测试证据附录 <span>TEST EVIDENCE APPENDIX</span></h1><p>未提供 Test Batch，无法生成 Input / Output 对照。</p></div>'
    ordered=sorted(batch["cases"],key=lambda x:({"P0":0,"P1":1,"P2":2}[x["applicabilityTier"]],x["caseId"]))
    cards=[]; rule_scores=rule_scores or []
    for case in ordered:
        inputs=''.join(f'<figure><img src="{image_uri((batch_dir/a["path"]).resolve())}" alt="{esc(case["caseId"])} input"><figcaption>Input · {esc(case["caseId"])}</figcaption></figure>' for a in case["inputAssets"])
        outputs=''.join(f'<figure><img src="{image_uri((batch_dir/a["path"]).resolve())}" alt="{esc(a["outputId"])}"><figcaption>Output · {esc(a["outputId"])}</figcaption></figure>' for a in case["outputs"])
        output_ids={a["outputId"] for a in case["outputs"]}
        score_lines=[]
        for rule in rule_scores:
            matched=[x for x in rule["scores"] if x["outputId"] in output_ids]
            for score in matched:
                value='N/A' if not score["applicable"] else f'{score["score"]}分'
                critical=rule["priority"]=="MUST" and score["applicable"] and score["score"]==0
                score_lines.append(f'<div class="rule-score-line{" critical" if critical else ""}"><strong>{esc(rule["ruleId"])}</strong><span>{esc(rule["priority"])}</span><b>{value}</b></div>')
        cards.append(f'<article class="evidence-row"><div class="evidence-id"><strong>{esc(case["caseId"])}</strong><span>{esc(case["applicabilityTier"])}</span></div><div class="evidence-side">{inputs}</div><div class="evidence-side">{outputs}</div><div class="evidence-scores">{"".join(score_lines)}</div></article>')
    pages=[]
    for start in range(0,len(cards),3):
        heading='<div class="appendix-head"><h1>测试证据附录 <span>TEST EVIDENCE APPENDIX</span></h1><div><span>INPUT</span><span>OUTPUT</span><span>RULE 分数</span></div></div>' if start==0 else '<div class="appendix-head"><h1>测试证据附录 · 续</h1><div><span>INPUT</span><span>OUTPUT</span><span>RULE 分数</span></div></div>'
        pages.append(f'<div class="page">{heading}{"".join(cards[start:start+3])}</div>')
    return ''.join(pages)

def recompute_fit(data:dict)->None:
    if data.get("schemaVersion")!="0.2": return
    rules=data.get("ruleScores")
    if not isinstance(rules,list) or not rules: fail("ruleScores must not be empty")
    weighted_actual=weighted_max=pref_actual=pref_max=0
    must_pass=must_total=0; must_pass_rates=[]
    for rule in rules:
        if set(rule)!={"ruleId","priority","scores","actualPoints","maxPoints","score"}: fail(f'{rule.get("ruleId","Rule")} fields are invalid')
        applicable=[x for x in rule["scores"] if x.get("applicable")]
        if not applicable or any(x.get("score") not in {0,1,2} for x in applicable): fail(f'{rule["ruleId"]} needs 0/1/2 scores for applicable outputs')
        if any((not x.get("applicable")) and x.get("score") is not None for x in rule["scores"]): fail(f'{rule["ruleId"]} non-applicable scores must be null')
        actual=sum(x["score"] for x in applicable); maximum=2*len(applicable); score=actual/maximum*100
        if rule["actualPoints"]!=actual or rule["maxPoints"]!=maximum or abs(rule["score"]-score)>.01: fail(f'{rule["ruleId"]} aggregate is inconsistent')
        weight=3 if rule["priority"]=="MUST" else 1
        weighted_actual+=actual*weight; weighted_max+=maximum*weight
        if rule["priority"]=="MUST":
            passed=sum(x["score"]>0 for x in applicable); total=len(applicable)
            must_pass+=passed; must_total+=total; must_pass_rates.append(passed/total*100)
        else: pref_actual+=actual; pref_max+=maximum
    summary={"overall":weighted_actual/weighted_max*100,"must":must_pass/must_total*100 if must_total else 100,"preferred":pref_actual/pref_max*100 if pref_max else 100}
    for key,value in summary.items():
        if abs(data["summaryScores"][key]-value)>.01: fail(f"summaryScores.{key} is inconsistent")
    gates={"overallPass":summary["overall"]>=80,"mustPassRatePass":summary["must"]>=60,"everyMustRulePassRatePass":not any(x<70 for x in must_pass_rates)}
    gates["pass"]=all(gates.values())
    if data["hardGates"]!=gates: fail("hardGates are inconsistent with Rule scores")
    if (data["status"]=="GO")!=gates["pass"]: fail("GO is allowed only when every hard gate passes")
    priorities=set(data.get("tunePriorities",[])); valid={x["ruleId"] for x in rules}
    if not priorities<=valid or len(priorities)>10: fail("tunePriorities contains invalid Rule IDs")
    for candidate in data.get("candidateRules",[]):
        if candidate.get("uxDecision")=="MERGE" and not candidate.get("mergeTarget"): fail("MERGE Candidate Rule requires mergeTarget")

def validate_fit(data:dict)->None:
    if data.get("reportType")!="FIT": fail("reportType must be FIT")
    if data.get("schemaVersion")=="0.2":
        recompute_fit(data)
        for failure in data.get("failures",[]):
            if not failure.get("evidenceCases") or not failure.get("evidenceOutputs"): fail(f'{failure.get("id","Failure")} requires evidenceCases and evidenceOutputs')

def validate_round1(data:dict)->None:
    if data.get("reportType")!="TUNE_ROUND_1": fail("reportType must be TUNE_ROUND_1")
    if data.get("schemaVersion")=="0.2":
        if not data.get("scoreSheets") or not data.get("promptRevision"): fail("TUNE round requires scoreSheets and promptRevision")

def validate_comparison(data:dict)->None:
    if data.get("reportType")!="TUNE_COMPARISON": fail("reportType must be TUNE_COMPARISON")
    if data.get("schemaVersion")=="0.2" and (not data.get("scoreSheets") or not data.get("comparisons")): fail("TUNE comparison requires complete scoreSheets and comparisons")

def validate_final(data:dict)->None:
    if data.get("reportType")!="FINAL_TEMPLATE_SPEC": fail("reportType must be FINAL_TEMPLATE_SPEC")

def fit_body(data:dict,batch:dict|None=None,batch_dir:Path|None=None)->str:
    recompute_fit(data); s=data["summaryScores"]; priorities=set(data["tunePriorities"])
    if batch:
        case_ids={x["caseId"] for x in batch["cases"]}; output_ids={a["outputId"] for x in batch["cases"] for a in x["outputs"]}
        for failure in data["failures"]:
            if not set(failure["evidenceCases"])<=case_ids or not set(failure["evidenceOutputs"])<=output_ids: fail(f'{failure["id"]} references unknown test evidence')
    rows=[]
    for x in data["ruleScores"]:
        if x["priority"]=="MUST":
            applicable=[s["score"] for s in x["scores"] if s["applicable"]]
            counts={score:applicable.count(score) for score in (0,1,2)}
            result=f'<span class="score-count{" score-zero" if counts[0] else ""}">0分 {counts[0]}</span><span class="score-count">1分 {counts[1]}</span><span class="score-count">2分 {counts[2]}</span>'
            rate=f'{counts[1]+counts[2]}/{len(applicable)}'
        else:
            result=f'{x["actualPoints"]}/{x["maxPoints"]}'; rate=f'{x["score"]:.1f}'
        rows.append(f'<tr><td>{x["ruleId"]}{" 🔥" if x["ruleId"] in priorities else ""}</td><td>{x["priority"]}</td><td>{result}</td><td>{rate}</td></tr>')
    rows=''.join(rows)
    gates=''.join(f'<div class="gate"><strong>{label}</strong><span class="{status_class("PASS" if data["hardGates"][key] else "FAIL")}">{"通过" if data["hardGates"][key] else "未通过"}</span><span>{threshold}</span></div>' for key,label,threshold in (("overallPass","总分门槛","≥ 80"),("mustPassRatePass","MUST 总体通过率","≥ 60%"),("everyMustRulePassRatePass","单条 MUST 通过率","每条 ≥ 70%")))
    level={"High":"高","Medium":"中","Low":"低"}
    failures=''.join(f'<article class="card failure-card"><h3>{esc(x["id"])} · {esc(x["name"])}</h3><p>{esc(x["description"])}</p><div class="meta"><span class="pill">关联 Rule：{", ".join(x["relatedRules"])}</span><span class="pill">影响程度：{level[x["severity"]]}</span><span class="pill">Prompt 可修复性：{level[x["promptFixability"]]}</span></div><p class="evidence-line"><strong>问题图片：</strong>{", ".join(x["evidenceCases"])}</p></article>' for x in data["failures"]) or '<p>未识别到补充失败模式。</p>'
    failure_ids='、'.join(x["id"] for x in data["failures"]) or '本轮 Failure Diagnosis'
    ux_review=f'<div class="ux-review"><strong>下一步需要 UX 判断</strong><p>请逐项确认 {failure_ids}：保留、合并还是删除；如有新增建议，请明确它应作为 MUST 还是 PREFERRED。</p><p>Agent 收到反馈后不会机械照搬：可独立成立的补充为新的 Fxx，并形成 Candidate Rule；能融入现有 T/V Rule 的内容将合并改写。Agent 会先汇报整理后的 Fxx 与 T/V Rule 修改，等待 UX 最终确认。</p></div>'
    decision_note='UX 最终确认后，所有 Rule 才会被冻结并交付给测试人员，<br>并重新输出完整的 Final Define Report，<br>作为TUNE阶段的优化依据。'
    candidate_rows=''.join(f'<tr><td>{x["id"]}</td><td>{esc(x["text"])}</td><td>{x["proposedPriority"]}</td><td>{x["uxDecision"]}</td></tr>' for x in data["candidateRules"])
    candidate_section=(f'<table><thead><tr><th>ID</th><th>Candidate Rule 建议</th><th>建议优先级</th><th>Accept / Merge / Reject</th></tr></thead><tbody>{candidate_rows}</tbody></table><p class="decision-note">{decision_note}</p>' if candidate_rows else f'<p class="decision-note no-candidate">本轮未识别到 Candidate Rule。<br>{decision_note}</p>')
    must_scores=[s for r in data["ruleScores"] if r["priority"]=="MUST" for s in r["scores"] if s["applicable"]]
    must_pass=sum(x["score"]>0 for x in must_scores)
    summary=f'''<div class="page">{fit_hero(data["templateName"],data["status"],data["model"],data["promptVersion"],data["caseCount"])}<section><h2>评分概览 SCORE OVERVIEW</h2><div class="grid-3"><article class="card"><div class="label">总分 OVERALL</div><div class="status">{s["overall"]:.1f}</div></article><article class="card"><div class="label">MUST 总体通过率</div><div class="status">{must_pass}/{len(must_scores)}</div></article><article class="card"><div class="label">PREFERRED 分数</div><div class="status">{s["preferred"]:.1f}</div></article></div></section><section><h2>硬门槛 HARD GATES</h2>{gates}</section><section><h2>全部 RULE 评分</h2><table><thead><tr><th>Rule</th><th>类型</th><th>得分分布</th><th>通过率 / Rule Score</th></tr></thead><tbody>{rows}</tbody></table></section><section><h2>失败诊断 FAILURE DIAGNOSIS</h2><div class="grid-2">{failures}</div></section><section><h2>UX RULE REVIEW · 必须确认后才能冻结</h2>{ux_review}{candidate_section}</section></div>'''
    return summary+fit_appendix(batch,batch_dir,data["ruleScores"])

def tune_body(data:dict)->str:
    sheets=data["scoreSheets"]; first,last=sheets[0],sheets[-1]
    summary=hero(data["templateName"],"TUNE · Tune Review",last["gateResult"],f'Prompt {first["promptVersion"]} → {last["promptVersion"]}')
    summary+=f'<section><div class="grid-3"><article class="card"><h3>Overall</h3><p>{first["overallScore"]:.1f} → {last["overallScore"]:.1f}</p></article><article class="card"><h3>MUST</h3><p>{first["mustScore"]:.1f} → {last["mustScore"]:.1f}</p></article><article class="card"><h3>PREFERRED</h3><p>{first["preferredScore"]:.1f} → {last["preferredScore"]:.1f}</p></article></div></section>'
    comparisons=data.get("comparisons",[])
    rows=''.join(f'<tr><td>{x["ruleId"]}</td><td>{x["initialScore"]:.1f}</td><td>{x["finalScore"]:.1f}</td><td>{x["finalScore"]-x["initialScore"]:+.1f}</td><td class="{status_class(x["outcome"])}">{x["outcome"]}</td></tr>' for x in comparisons)
    all_sheets=''.join('<h2>Prompt '+esc(sheet["promptVersion"])+'</h2><table><thead><tr><th>Rule</th><th>Score</th></tr></thead><tbody>'+''.join(f'<tr><td>{r["ruleId"]}</td><td>{r["score"]:.1f}</td></tr>' for r in sheet["ruleScores"])+'</tbody></table>' for sheet in sheets)
    reviews=''.join(f'<article class="card"><h3>{x["ruleId"]}</h3><p><strong>Original:</strong> {esc(x["originalSentence"])}</p><p><strong>Final:</strong> {esc(x["finalSentence"] or "未发现针对该 Rule 的 Prompt 调整")}</p><p>{x["initialScore"]:.1f} → {x["finalScore"]:.1f} · {esc(x["explanation"])}</p></article>' for x in data.get("promptChangeReview",[]))
    appendix=''.join(f'<article class="card"><h3>{x["caseId"]}</h3><p>Inputs: {", ".join(map(esc,x["inputAssets"]))}</p><p>Outputs: '+ ' · '.join(f'{esc(k)}: {", ".join(map(esc,v))}' for k,v in x["outputsByVersion"].items())+'</p></article>' for x in data.get("evidenceAppendix",[]))
    return f'''<div class="page">{summary}</div><div class="page"><h1>完整 Rule 分数比较</h1><table><thead><tr><th>Rule</th><th>Initial</th><th>Final</th><th>Δ</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table>{all_sheets}</div><div class="page"><h1>Prompt Change Review</h1><div class="grid-2">{reviews or "<p>尚无 Prompt Change Review。</p>"}</div></div><div class="page"><h1>完整 Test Evidence Appendix</h1><div class="grid-2">{appendix or "<p>尚无 evidence appendix。</p>"}</div></div>'''

def legacy_body(data:dict)->str:
    return hero(data.get("templateName","Seedream Template"),data.get("reportType","Stage"),data.get("status",data.get("nextAction","完成")),"Legacy v0.1 compatibility")+f'<section><pre>{esc(json.dumps(data,ensure_ascii=False,indent=2))}</pre></section>'

def parse_args():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("analysis",type=Path);p.add_argument("--output-dir",required=True,type=Path);p.add_argument("--batch",type=Path);p.add_argument("--template",type=Path,default=Path(__file__).resolve().parent.parent/"templates/stage-report.html");p.add_argument("--reference",action="append",default=[],type=Path);return p.parse_args()

def main()->int:
    a=parse_args(); data=json.loads(a.analysis.read_text(encoding="utf-8")); template=a.template.read_text(encoding="utf-8"); out=a.output_dir
    if data.get("reportType")=="FIT" and data.get("schemaVersion")=="0.2":
        validate_fit(data); batch_path=a.batch or (out/"tests/batch.json" if (out/"tests/batch.json").is_file() else None); batch,batch_dir=load_fit_evidence(batch_path); body=fit_body(data,batch,batch_dir); name="fit-report.html"
    elif data.get("reportType") in {"TUNE_ROUND_1","TUNE_COMPARISON"} and data.get("schemaVersion")=="0.2": body=tune_body(data); name="tuning-round-1.html" if data["reportType"]=="TUNE_ROUND_1" else "tuning-comparison.html"
    elif data.get("reportType")=="FINAL_TEMPLATE_SPEC": body=legacy_body(data); name="final-template-spec.html"
    else: body=legacy_body(data); name={"FIT":"fit-report.html","TUNE_ROUND_1":"tuning-round-1.html","TUNE_COMPARISON":"tuning-comparison.html"}.get(data.get("reportType"),"stage-report.html")
    atomic(out/name,compose(template,f'{data.get("templateName","Seedream")} · {data.get("reportType","Stage")}',body)); return 0
if __name__=="__main__": raise SystemExit(main())
