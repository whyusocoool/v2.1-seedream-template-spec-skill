#!/usr/bin/env python3
"""Synthetic regression cases only; no UX confirmation or Seedream evaluation is real."""
import copy
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from define_v04 import CHECKS, validate, ready, SCHEMA, structural
from build_report import validate_spec
from detect_stage import detect

ROOT=Path(__file__).resolve().parent.parent


def fixture():
    old=json.loads((ROOT/'cases/shouzhang-stickers/define/template-spec.json').read_text())
    source={'sourceId':'REF01','location':'示意区域（合成测试）','claim':'虚构视觉证据，只测结构','kind':'OBSERVED'}
    rule={'id':'R01','category':'C2','name':'测试单元排列','text':'单元沿规则网格排列。','priority':'MUST','retentionReason':'合成测试：排列是测试目标','priorityReason':'合成测试：缺失则不符合目标','evidence':[source],'checkScope':'测试区域','allowedVariation':'配色可以变化','necessaryConditions':['网格可辨认'],'supportingCues':['相邻间距近似一致'],'score2':'行列规律且间距一致','score1':'网格仍可辨认，存在轻微间距波动','score0':'无法辨认网格排列','unobservableWhen':'图像模糊时记录 U 并补充证据','notApplicableWhen':'本测试不允许不适用','dependsOn':[],'implementation':{'method':'PROMPT','detail':'直接表达网格要求'}}
    rows=[]
    for cid in CHECKS:
        finding={'observation':'合成用例未涉及此检查项','sources':[],'decision':'NOT_APPLICABLE','ruleIds':[],'reason':'仅用于结构验证，不代表真实图像分析'}
        if cid=='C2.06':finding={'observation':'合成用例中的网格要求','sources':[source],'decision':'RULE','ruleIds':['R01'],'reason':'需要独立检查排列'}
        rows.append({'checkId':cid,'findings':[finding]})
    return {'specVersion':'0.4','templateName':'合成结构测试（非真实模板）','runtimeInput':'Single image','runtimeInputInferred':False,'usageScenario':'测试 schema 与流程，不评估模型','targetVisual':'验证独立规则和完整遍历','references':[{'id':f'REF{i:02d}','caption':'合成测试输入'} for i in range(1,5)],'heroReference':'REF01','goal':{'status':'CONFIRMED','mustPreserve':['合成网格要求'],'allowedVariation':['配色'],'scope':'仅回归测试','questions':[],'uxConfirmation':'模拟确认 fixture；非真实 UX 决定'},'traversal':rows,'rules':[rule],'promptGuideReview':{'path':'references/seedream-prompt-guide.md','targetModel':'Seedream 4.0（测试元数据）','sourceStatus':'LOCAL_ONLY','reviewNote':'只验证记录存在，不宣称生图效果'},'initialApplicability':old['initialApplicability'],'fitTestPlan':old['fitTestPlan'],'tuneTestPlan':old['tuneTestPlan'],'promptVersion':'0.0','seedreamPrompt':'单元沿规则网格排列。','promptRuleMap':[{'sentence':'单元沿规则网格排列。','ruleIds':['R01']}]}


class DefineTests(unittest.TestCase):
    def assert_invalid(self,spec):
        with self.assertRaises(ValueError):validate_spec(spec)
    def test_valid_five_groups_no_quota(self):
        s=fixture();validate_spec(s);self.assertTrue(ready(s));self.assertEqual(len(s['rules']),1)
    def test_legacy(self):
        validate_spec(json.loads((ROOT/'cases/shouzhang-stickers/define/template-spec.json').read_text()))
    def test_reference_stage_ignores_metadata(self):
        refs=sorted((ROOT/'cases/shouzhang-stickers/define/references').glob('golden-reference-*.jpg'))
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp); folder=run/'0.reference'; folder.mkdir()
            (folder/'notes.json').write_text('{}')
            (folder/'broken.jpg').write_bytes(b'not an image')
            self.assertEqual(detect(run)['action'],'WAIT_DEFINE')
            for ref in refs[:3]: shutil.copyfile(ref,folder/ref.name)
            self.assertEqual(detect(run)['action'],'RUN_DEFINE')
    def test_missing_and_duplicate_checks(self):
        s=fixture();s['traversal'].pop();self.assert_invalid(s)
        s=fixture();s['traversal'][-1]=s['traversal'][0];self.assert_invalid(s)
    def test_bad_target_and_evidence(self):
        s=fixture();s['rules'][0]['evidence'][0]['sourceId']='REF99';self.assert_invalid(s)
        s=fixture();s['traversal'][10]['findings'][0]['ruleIds']=['R99'];self.assert_invalid(s)
    def test_omitted_findings_cannot_create_rules(self):
        s=fixture()
        for row in s['traversal']:
            for f in row['findings']:
                if f['decision']=='RULE':f.update(decision='OMIT',ruleIds=[])
        self.assert_invalid(s)
    def test_unconfirmed_and_pending_are_not_ready(self):
        s=fixture();s['goal'].update(status='DRAFT',uxConfirmation='');validate(s);self.assertFalse(ready(s))
        s=fixture();s['goal']['uxConfirmation']='';self.assert_invalid(s)
        s=fixture();s['traversal'][0]['findings'][0]['decision']='PENDING_UX';validate(s);self.assertFalse(ready(s))
    def test_distinct_rubrics(self):
        s=fixture();s['rules'][0]['score1']=s['rules'][0]['score0'];self.assert_invalid(s)
    def test_reference_and_config_not_forced_into_text(self):
        s=fixture();s['rules'][0]['implementation']['method']='CONFIG';s['promptRuleMap']=[];validate(s)
        s['rules'][0]['implementation']['method']='PROMPT';self.assert_invalid(s)
    def test_mapping_not_present(self):
        s=fixture();s['promptRuleMap'][0]['sentence']='不在文案中';self.assert_invalid(s)
    def test_dependency_cycle(self):
        s=fixture();s['rules'][0]['dependsOn']=['R01'];self.assert_invalid(s)
    def test_render_and_routing(self):
        refs=sorted((ROOT/'cases/shouzhang-stickers/define/references').glob('golden-reference-*.jpg'))
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);out=run/'1.define';out.mkdir();path=out/'template-spec.json'
            s=fixture();path.write_text(json.dumps(s,ensure_ascii=False))
            cmd=[sys.executable,str(ROOT/'scripts/build_report.py'),str(path),'--output-dir',str(out)]
            for ref in refs:cmd+=['--reference',str(ref)]
            subprocess.run(cmd,check=True,capture_output=True)
            body=(out/'template-definition-report.html').read_text()
            self.assertIn('必要条件',body);self.assertIn('无法判断',body);self.assertIn('R01',body)
            self.assertEqual((out/'prompt-0.0.txt').read_text(),s['seedreamPrompt'])
            self.assertTrue((out/'traversal-audit.html').exists())
            self.assertTrue((out/'seedream-prompt-guide.md').exists())
            self.assertEqual(detect(run)['action'],'REBUILD_DEFINE')
            (out/'traversal-audit.html').unlink()
            (out/'seedream-prompt-guide.md').unlink()
            missing=detect(run)['missing']
            self.assertIn(str((out/'traversal-audit.html').resolve()),missing)
            self.assertIn(str((out/'seedream-prompt-guide.md').resolve()),missing)
            s['goal'].update(status='DRAFT',uxConfirmation='');path.write_text(json.dumps(s))
            self.assertEqual(detect(run)['action'],'WAIT_UX_TARGET_CONFIRMATION')
            # Even stale formal artifacts cannot bypass target confirmation.
            subprocess.run(cmd,check=True,capture_output=True)
            self.assertEqual(detect(run)['action'],'WAIT_UX_TARGET_CONFIRMATION')
    def test_later_schemas_accept_R_ids(self):
        for name in ('fit-analysis','ux-rule-review','tuning-analysis','final-template-spec'):
            schema=json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text())
            def walk(x):
                if isinstance(x,dict):
                    for k,v in x.items():
                        if k=='pattern' and '[TV]' in str(v):self.fail(f'{name} still rejects R IDs')
                        walk(v)
                elif isinstance(x,list):
                    for v in x:walk(v)
            walk(schema)
    def test_fit_numeric_contract_with_R_rule(self):
        from build_stage_report import validate_fit
        data={'reportType':'FIT','schemaVersion':'0.2','ruleScores':[{'ruleId':'R01','priority':'MUST','scores':[{'caseId':'P0-01','outputId':'O01','applicable':True,'score':2}], 'actualPoints':2,'maxPoints':2,'score':100}], 'summaryScores':{'overall':100,'must':100,'preferred':100}, 'hardGates':{'overallPass':True,'mustPassRatePass':True,'everyMustRulePassRatePass':True,'pass':True},'status':'GO','candidateRules':[],'failures':[],'tunePriorities':['R01']}
        validate_fit(data)
        data['ruleScores'][0]['scores'][0]['score']=None
        with self.assertRaises(ValueError):validate_fit(data)

    def test_parent_schema_references_resolve(self):
        schema=json.loads((ROOT/'schemas/template-spec.schema.json').read_text())
        def walk(x):
            if isinstance(x,dict):
                if '$ref' in x:
                    ref=x['$ref']
                    if ref.startswith('#/'):
                        target=schema
                        for key in ref[2:].split('/'):target=target[key]
                    else:self.assertTrue((ROOT/'schemas'/ref).exists())
                for v in x.values():walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        walk(schema)

if __name__=='__main__':unittest.main()
