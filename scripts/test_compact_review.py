"""Behavioral invariants using synthetic evidence, not model-quality tests."""
import unittest,copy,tempfile
from pathlib import Path
from test_define_v04 import fixture
from define_v04 import validate,ready,consistency_passed,check_disposition
from compact_report import definition_html,alignment_html,scoring_rows,consistency_rows,rule_rows,dots_svg,appendix_rows,chat_summary,core_rows,variation_rows,pending_rows,pending_proposal_rows,material_item_parts,resolve_font_pair,resolve_reference_paths,content_budget_issues

def sample():
 s=fixture();base=s['rules'][0];extra=[]
 for rid,category,text,priority in [('R02','C2','主体轮廓保持简洁。','MUST'),('R03','C3','使用清楚的主色关系。','MUST'),('R04','C3','保留轻微材质变化。','PREFERRED')]:
  rule=copy.deepcopy(base);rule.update(id=rid,category=category,name='模拟'+rid,text=text,priority=priority);extra.append(rule)
 s['rules']+=extra;s['seedreamPrompt']=''.join(r['text'] for r in s['rules']);s['promptRuleMap']=[{'sentence':r['text'],'ruleIds':[r['id']]} for r in s['rules']]
 for cid,rid in [('C2.01','R02'),('C3.01','R03'),('C3.04','R04')]:
  row=next(x for x in s['traversal'] if x['checkId']==cid);row['findings'][0].update(observation='模拟'+rid,sources=[base['evidence'][0]],decision='RULE',ruleIds=[rid],reason='合成定量门槛测试')
 evidence=[]
 for rule,cid in zip(s['rules'],['C2.06','C2.01','C3.01','C3.04']):
  evidence.append({'description':'模拟'+rule['id'],'checkIds':[cid],'ruleIds':[rule['id']],'evidence':[{'refId':r['id'],'score':2,'observation':'模拟测试证据'} for r in s['references']],'conclusion':'模拟支持'})
 s['reviewReport']={'version':'2','ruleStatus':'DRAFT','uxConfirmation':'','confirmationRequest':'模拟：请确认规则','pendingRuleIds':[],'referenceConsistency':{'status':'PASS','summary':'模拟可定义性','conflicts':[]},'ruleEvidence':evidence,'variations':[],'testMaterials':[{'tier':t,'definition':'模拟范围','items':['模拟材料']*n} for t,n in [('P0',6),('P1',6),('P2',4)]]};return s
class ReviewTests(unittest.TestCase):
 def test_lean_v2_omits_duplicated_evidence_and_manual_verdict(self):
  s=sample();s['reviewReport'].pop('referenceConsistency')
  for rule in s['rules']:rule.pop('evidence',None)
  validate(s);self.assertTrue(consistency_passed(s));self.assertTrue(definition_html(s,['x']*4))
 def test_required_knowledge_is_packaged_with_skill(self):
  root=Path(__file__).resolve().parent.parent
  for rel in ('references/seedream-prompt-guide.md','references/define-rules-v2.md','references/review-output-v2.md','references/traversal-v2.json'):
   self.assertTrue((root/rel).is_file(),rel)
 def test_target_confirmation_does_not_approve_rules(self):
  s=sample();validate(s);self.assertFalse(ready(s));self.assertTrue(consistency_passed(s));self.assertTrue(definition_html(s,['x']*4))
 def test_too_few_supported_rules_blocks_definition(self):
  s=sample();s['reviewReport']['ruleEvidence']=s['reviewReport']['ruleEvidence'][:3];self.assertFalse(consistency_passed(s))
 def test_must_support_threshold_is_enforced(self):
  s=sample();s['reviewReport']['ruleEvidence'][0]['evidence'][0]['score']=0;self.assertFalse(consistency_passed(s))
 def test_pending_does_not_by_itself_mean_style_is_unstable(self):
  s=sample();row=next(x for x in s['traversal'] if x['checkId']=='C4.03');row['findings'][0].update(decision='PENDING_UX',observation='画幅待定',reason='UX尚未选择');self.assertTrue(consistency_passed(s))
 def test_display_classifies_full_support_as_core_and_exception_as_variation(self):
  s=sample();self.assertEqual(len(core_rows(s)),4);s['reviewReport']['ruleEvidence'][0]['evidence'][0]['score']=1;self.assertEqual(len(core_rows(s)),3);self.assertEqual(variation_rows(s)[0][0],'模拟R01')
 def test_missing_reference_rejected(self):
  s=sample();s['reviewReport']['ruleEvidence'][0]['evidence'].pop()
  with self.assertRaises(ValueError):validate(s)
 def test_pending_and_unknown_are_distinct(self):
  s=sample();row=next(x for x in s['traversal'] if x['checkId']=='C2.06');row['findings'].append({'decision':'UNOBSERVABLE','ruleIds':[]});states,u=check_disposition(s,row);self.assertEqual(states,['MUST']);self.assertFalse(u)
 def test_only_pending_ux_creates_visible_pending_proposal(self):
  s=sample();row=next(x for x in s['traversal'] if x['checkId']=='C2.06');row['findings'].append({'observation':'不保留为Rule','decision':'PENDING_UX','ruleIds':[],'reason':'参考方向不固定','sources':[]});self.assertEqual(pending_rows(s)[0][-1],'请 UX 选择');self.assertEqual(rule_rows(s)[0][2],'MUST');self.assertEqual(pending_proposal_rows(s)[0][2],'不保留');self.assertIn('pending-row',definition_html(s,['x']*4))
 def test_mixed_omit_is_not_hidden(self):
  s=sample();row=next(x for x in s['traversal'] if x['checkId']=='C2.06');row['findings'].append({'decision':'OMIT','ruleIds':[]});self.assertEqual(check_disposition(s,row)[0],['MUST','EXCLUDE'])
 def test_must_no_score2_exposed(self):
  s=sample();row=scoring_rows(s)[0];self.assertEqual(row[1],'通过\n不通过');self.assertIn(s['rules'][0]['score0'],row[2]);self.assertIn(s['rules'][0]['score1'],row[2]);self.assertNotIn(s['rules'][0]['score2'],row[2])
 def test_prefer_card_preserves_three_judgment_descriptions(self):
  s=sample();r=s['rules'][0];r['priority']='PREFERRED';row=scoring_rows(s)[0];self.assertEqual(row[1],'2分\n1分\n0分');self.assertEqual(row[2],r['score2']+'\n'+r['score1']+'\n'+r['score0'])
 def test_material_count_enforced(self):
  s=sample();s['reviewReport']['testMaterials'][1]['items'].pop()
  with self.assertRaises(ValueError):validate(s)
 def test_material_output_removes_execution_notes(self):
  self.assertEqual(material_item_parts('招牌店面：门头完整且清晰，检查R01/R06；文字依UX决定。'),['招牌店面','门头完整且清晰'])
  self.assertEqual(material_item_parts('暗光主体：轮廓模糊，检查R01/R04；不臆造原字。'),['暗光主体','轮廓模糊'])
 def test_alignment_shows_average_and_check_origin(self):
  s=sample();row=consistency_rows(s)[0];self.assertEqual(row[1],'4/4');self.assertEqual(row[3],'C2-6 重复排列');self.assertNotIn('核心',row[0]);self.assertNotIn('辅助',row[0])
 def test_rule_table_maps_r_to_c(self):
  s=sample();self.assertEqual(rule_rows(s)[0][3],'C2-6 重复排列')
 def test_definition_puts_ux_action_before_rule_table(self):
  s=sample();text=definition_html(s,['x']*4);self.assertLess(text.index('请 UX 确认'),text.index('<table>'))
 def test_chat_rule_table_has_origin_column_and_prior_action(self):
  s=sample();text=chat_summary(s);self.assertIn('| Rule | 初版要求 | 建议级别 | 来自遍历项 |',text);self.assertLess(text.index('请 UX 确认'),text.index('| Rule |'))
 def test_standard_checklist_has_group_and_three_detail_columns(self):
  rows=appendix_rows();self.assertEqual(len(rows),29);self.assertTrue(all(len(row)==4 and row[1] and row[2] and row[3] for row in rows));self.assertEqual([r[0] for r in rows if r[0]],['C1 内容与保留','C2 形态与组织','C3 视觉表现','C4 输入适配','C5 成品可用性'])
 def test_multistate_dot_uses_split_shape_not_satellite_dot(self):
  s=sample();row=next(x for x in s['traversal'] if x['checkId']=='C2.06');row['findings'].append({'decision':'OMIT','ruleIds':[]});svg=dots_svg(s);self.assertIn('<path',svg);self.assertNotIn('C2-6',svg);self.assertIn('>7</text>',svg);self.assertNotIn('stroke="#718096"',svg)
 def test_exclude_and_not_applicable_have_distinct_states(self):
  s=sample();excluded=next(x for x in s['traversal'] if x['checkId']=='C1.01');excluded['findings'][0]['decision']='OMIT';na=next(x for x in s['traversal'] if x['checkId']=='C1.02');self.assertEqual(check_disposition(s,excluded)[0],['EXCLUDE']);self.assertEqual(check_disposition(s,na)[0],['NOT_APPLICABLE'])
 def test_user_facing_unrelated_marker_is_dashed(self):
  s=sample();svg=dots_svg(s);self.assertIn('stroke="#9aa0a6"',svg);self.assertIn('stroke-dasharray="3 2"',svg);self.assertIn('border:1px dashed #9aa0a6',definition_html(s,['x']*4));self.assertIn('>无关</span>',definition_html(s,['x']*4));self.assertIn('>不规定</span>',definition_html(s,['x']*4))
 def test_font_resolution_does_not_require_deng_bold(self):
  regular,bold=resolve_font_pair(__file__);self.assertEqual(regular,__file__);self.assertEqual(bold,__file__)
 def test_reference_resolution_accepts_documented_golden_names(self):
  with tempfile.TemporaryDirectory() as tmp:
   spec_path=Path(tmp)/'run-001'/'1.define'/'template-spec.json';spec_path.parent.mkdir(parents=True);refs=spec_path.parent.parent/'0.reference';refs.mkdir()
   for index in range(1,5):(refs/f'golden-reference-{index:02d}.jpg').write_bytes(b'x')
   found=resolve_reference_paths(spec_path,sample());self.assertTrue(all('golden-reference-' in str(x) for x in found))
 def test_preflight_never_limits_prompt_or_rule_length(self):
  s=sample();s['promptRuleMap']=[{'sentence':'很长但有意义的提示词'*100,'ruleIds':['R01']}]*8;s['rules'][0]['text']='必要规则细节'*100
  for material in s['reviewReport']['testMaterials']:material['items']=['素材：'+('必要输入特征'*30) for _ in material['items']]
  self.assertEqual(content_budget_issues(s),[])
 def test_preflight_reports_material_structure_without_truncating_it(self):
  s=sample();s['reviewReport']['testMaterials'][0]['items'][0]='缺少素材与输入特征分隔'
  self.assertIn('P0-01','\n'.join(content_budget_issues(s)))
if __name__=='__main__':unittest.main()
