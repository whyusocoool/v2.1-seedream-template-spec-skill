"""Content-first review reports from the authoritative DEFINE JSON.

The canonical Prompt is never shortened to satisfy PDF layout. Prompt mappings
flow onto dedicated continuation pages while preserving copy order.
"""
import argparse,json,html,re,hashlib
from io import BytesIO
from pathlib import Path
from define_v04 import GROUPS,CHECKS,related_checks,check_disposition,consistency_passed,definition_assessment,ready,validate,audit_body
COLORS={'MUST':'#97c657','PREFERRED':'#84aef9','PENDING':'#edd154','EXCLUDE':'#c9cbd0','NOT_APPLICABLE':'#ffffff'}
LEGEND=[('MUST','MUST'),('PREFER','PREFERRED'),('待定','PENDING'),('不规定','EXCLUDE'),('无关','NOT_APPLICABLE')]
TIER_LABELS={'P0':'A 核心场景','P1':'B 拓展场景','P2':'C 边缘场景'}
FONT_CANDIDATES=(
 '/Library/Fonts/Deng.ttf',
 '/Library/Fonts/Arial Unicode.ttf',
 '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
)
CHECK_DETAIL={
'C1.01':'必要对象、对象数量及语义关系；不判断位置。','C1.02':'必须存在的部件、符号与识别线索；不判断比例。','C1.03':'实际文字、字符和符号含义；不判断字体外观。','C1.04':'输入到输出需保留的身份或标志特征。','C1.05':'是否需要增加、移除或替换画面内容。',
'C2.01':'部件比例、对象轮廓、圆角与转折。','C2.02':'可见部件的朝向、姿势和动作关系。','C2.03':'对象在画布中的位置、占比与相对大小。','C2.04':'对象之间的间距、对齐、基线与偏移。','C2.05':'可见重叠、包含及前后层次线索。','C2.06':'单元重复、行列、步距、交替与不规则性。','C2.07':'边缘裁切、空区分布、边距与留白。',
'C3.01':'主要色域、饱和程度、区域色差与允许配色变化。','C3.02':'渐变、亮暗区域、投影或反射；不反推灯位、镜头或工艺。','C3.03':'清晰或渐变边界、描边、断续与毛边；轮廓几何归 C2-1。','C3.04':'颗粒、笔触、斑驳、纤维等可见痕迹及其可见尺度。','C3.05':'支持纸艺、拼豆、黏土、水彩等整体外观的组合线索。','C3.06':'细节保留密度、平面化与概括方式。','C3.07':'字形或图标的描线、填充与外观特征。',
'C4.01':'支持范围内，单个或多个对象时如何处理。','C4.02':'复杂输入如何简化，以及简化时保留什么。','C4.03':'输入或输出比例变化时如何重排、缩放或裁切。','C4.04':'文字变长后的换行、缩放与版面策略。','C4.05':'不同背景、遮挡或输入质量下的处理策略。',
'C5.01':'在约定展示尺度下，指定文字是否可读。','C5.02':'交付时是否缺失必要内容或关键内容不可用。','C5.03':'使用场景要求的主要对象辨识条件。','C5.04':'会妨碍约定用途的具体视觉缺陷。','C5.05':'约定尺寸、比例、透明背景与文件形式。'}
def h(x):return html.escape(str(x))
def display_check(cid):
 group,item=cid.split('.')
 return group+'-'+str(int(item))
def checks(ids):return '；'.join(display_check(x)+' '+CHECKS[x] for x in ids)
def check_ids(ids):return '；'.join(display_check(x) for x in ids)
def pending_rows(s):
 rows=[]
 for row in s['traversal']:
  for f in row['findings']:
   if f['decision']=='PENDING_UX':
    rows.append([display_check(row['checkId'])+' '+CHECKS[row['checkId']],f['observation'],f['reason'],'请 UX 选择'])
 return rows
def pending_proposal_rows(s):
 return [['待定',row[1],'不保留',row[0].split()[0]] for row in pending_rows(s)]
def confirmation(s):
 if s['reviewReport']['ruleStatus']!='DRAFT':return 'Rules 已确认：'+s['reviewReport']['uxConfirmation']
 pending='；另有 '+str(len(pending_rows(s)))+' 个待定 Criteria，见 Rule 表后的黄色提议。' if pending_rows(s) else ''
 return '以下均为候选 Rules，尚未定稿。请 UX 确认规则内容及级别；需要调整时，直接回复 Rule 编号和修改意见'+pending
def rule_evidence(s):return s['reviewReport'].get('ruleEvidence',s['reviewReport'].get('consistency',[]))
def fully_supported(x):return all(e['score']==2 for e in x['evidence'])
def core_rows(s):return [[x.get('description',x.get('effect','')),checks(x['checkIds']),'/'.join(x['ruleIds'])] for x in rule_evidence(s) if fully_supported(x)]
def variation_rows(s):
 exceptions=[[x.get('description',x.get('effect','')),checks(x['checkIds']),x['conclusion']] for x in rule_evidence(s) if not fully_supported(x)]
 declared=[[v['text'],checks(v['checkIds']),v['reason']] for v in s['reviewReport']['variations']]
 return exceptions+declared
def consistency_rows(s):
 return [[x.get('description',x.get('effect','')),f"{sum(e['score']==2 for e in x['evidence'])}/{len(x['evidence'])}",x['conclusion'],checks(x['checkIds'])] for x in rule_evidence(s)]
def ux_effect_rows(s):
 rows=[];priorities={r['id']:('MUST' if r['priority']=='MUST' else 'PREFER') for r in s['rules']}
 for item in rule_evidence(s):
  supported=[e['refId'] for e in item['evidence'] if e['score']==2]
  image_basis=('–'.join([supported[0],supported[-1]]) if len(supported)>1 else supported[0])+f"（{len(supported)}/{len(item['evidence'])}）"
  rows.append([item.get('description',item.get('effect','')),image_basis,checks(item['checkIds']),' / '.join(rule_id+' · '+priorities[rule_id] for rule_id in item['ruleIds']) or '—'])
 return rows
def ux_variation_rows(s):
 preferred={r['id']:set(related_checks(s,r['id'])) for r in s['rules'] if r['priority']=='PREFERRED'}
 traversal={row['checkId']:row for row in s['traversal']}
 rows=[]
 for item in s['reviewReport']['variations']:
  mapped=[rule_id for rule_id,check_ids in preferred.items() if check_ids.intersection(item['checkIds'])]
  if mapped:destination=' / '.join(rule_id+' · PREFER' for rule_id in mapped)
  else:
   states=[state for cid in item['checkIds'] for state in check_disposition(s,traversal[cid])[0]]
   destination='待定' if 'PENDING' in states else ('无关' if states and all(x=='NOT_APPLICABLE' for x in states) else '不规定')
  rows.append([item['text'],item['reason'],checks(item['checkIds']),destination])
 return rows
def disposition_summary(s):
 traversal={row['checkId']:row for row in s['traversal']};counts={state:0.0 for _,state in LEGEND};aligned=0
 for group in GROUPS.values():
  for check in group['checks']:
   states,_=check_disposition(s,traversal[check['id']])
   if any(state in ('MUST','PREFERRED','PENDING') for state in states):aligned+=1
   for state in states:counts[state]+=1/len(states)
 return aligned,counts
def format_count(value):return str(int(value)) if value.is_integer() else f'{value:g}'
def material_item_parts(item):
 text=str(item).strip().rstrip('。')
 # Legacy specs sometimes appended scoring/generation instructions to a material.
 # They belong in Rules or the scorecard, never in the material suggestion page.
 text=re.sub(r'(?:[，,；;]\s*)?检查\s*R\d+(?:\s*/\s*R\d+)*', '', text, flags=re.I)
 text=re.sub(r'[；;]\s*(?:文字依\s*UX\s*决定|不臆造[^；;。]*)', '', text, flags=re.I)
 text=text.strip(' ，,；;。')
 if '：' in text:name,features=text.split('：',1)
 elif ':' in text:name,features=text.split(':',1)
 else:name,features=text,'—'
 return [name.strip(),features.strip(' ，,；;。') or '—']
def material_rows(material):
 return [[str(i),*material_item_parts(item)] for i,item in enumerate(material['items'],1)]

def resolve_font_pair(requested=None):
 """Return a usable CJK regular/bold pair without assuming Deng.ttf exists."""
 candidates=([str(requested)] if requested else [])+list(FONT_CANDIDATES)
 for value in candidates:
  regular=Path(value).expanduser()
  if not regular.is_file():continue
  preferred=regular.with_name('Dengb.ttf') if regular.name=='Deng.ttf' else regular
  bold=preferred if preferred.is_file() else regular
  return str(regular),str(bold)
 tried='; '.join(candidates)
 raise ValueError('No usable Chinese TTF font found. Pass --font explicitly. Tried: '+tried)

def resolve_reference_paths(spec_path,s):
 """Accept the canonical REFxx name and the documented golden-reference-xx name."""
 folder=spec_path.parent.parent/'0.reference';resolved=[];missing=[]
 for index,ref in enumerate(s['references'],1):
  stems=(ref['id'],f'golden-reference-{index:02d}')
  found=next((folder/(stem+ext) for stem in stems for ext in ('.png','.jpg','.jpeg','.webp') if (folder/(stem+ext)).is_file()),None)
  if found is None:missing.append(ref['id'])
  else:resolved.append(found)
 if missing:raise ValueError('Missing Golden References in '+str(folder)+': '+', '.join(missing))
 return resolved

def content_budget_issues(s):
 """Report structural formatting errors without limiting authored content."""
 issues=[]
 malformed=[]
 for material in s.get('reviewReport',{}).get('testMaterials',[]):
  for index,item in enumerate(material.get('items',[]),1):
   if '：' not in item and ':' not in item:malformed.append(f'{material.get("tier")}-{index:02d}')
 if malformed:issues.append('Test materials need “素材：输入特征” separation: '+', '.join(malformed))
 return issues
def rules_basis_rows(s):
 rows=[];missing=[]
 covered=set()
 for effect,image_basis,criteria,rules in ux_effect_rows(s):
  rows.append([rules,effect,image_basis,criteria]);covered.update(item['id'] for item in s['rules'] if item['id'] in rules)
 for treatment,image_basis,criteria,destination in ux_variation_rows(s):
  rows.append([destination,treatment,image_basis,criteria]);covered.update(rule['id'] for rule in s['rules'] if rule['id'] in destination)
 for rule in s['rules']:
  if rule['id'] not in covered:
   criteria=checks(related_checks(s,rule['id'])) or '依据不足'
   missing.append([rule['id']+' · 待定',rule['name'],'缺少独立图片依据，待 UX 判断',criteria])
 return missing+rows
def rule_rows(s):
 def level(r):
  if r['id'] in s['reviewReport']['pendingRuleIds']:return '待确认'
  value='MUST' if r['priority']=='MUST' else 'PREFER'
  return value
 return [[r['id'],r['text'],level(r),checks(related_checks(s,r['id']))] for r in s['rules']]
def rule_rows_ids(s):
 image_supported={rule_id for item in rule_evidence(s) for rule_id in item['ruleIds']}
 for variation in s['reviewReport']['variations']:
  image_supported.update(rule['id'] for rule in s['rules'] if set(related_checks(s,rule['id'])).intersection(variation['checkIds']))
 return [[row[0],row[1],('待确认' if row[0] not in image_supported else row[2]),check_ids(related_checks(s,row[0]))] for row in rule_rows(s)]
def scoring_rows(s):
 return [[r['id']+' '+r['name'],('通过\n不通过') if r['priority']=='MUST' else '2分\n1分\n0分',r['score1']+'\n'+r['score0'] if r['priority']=='MUST' else r['score2']+'\n'+r['score1']+'\n'+r['score0']] for r in s['rules']]
def rule_judgments(r):
 if r['priority']=='MUST':return [('通过',r['score1'],'normal'),('不通过',r['score0'],'fail')]
 return [('2分',r['score2'],'normal'),('1分',r['score1'],'partial'),('0分',r['score0'],'fail')]
def scoring_items(s,priority):
 return [r for r in s['rules'] if r['priority']==priority]
def appendix_rows():
 rows=[]
 for g in GROUPS.values():
  for i,c in enumerate(g['checks']):rows.append([g['id']+' '+g['name'] if i==0 else '',display_check(c['id']),c['name'],CHECK_DETAIL[c['id']]])
 return rows
CONSISTENCY_NOTE='“满足项”统计清楚支持该效果的参考图数量。6/6进入核心效果；存在例外的效果进入允许变化并说明差异。详细逐图证据保留在结构化记录中；该结论不代表 Seedream 已能稳定生成。'
SCORE_NOTE='请测试参照此表，为每条 Rule 评分。先完成 MUST，再评价 PREFER。'
CALC_ROWS=[
 ['MUST 通过率','(N - 不通过图片数) / N × 100%','每条 MUST Rule 在 A、B、C 类内分别计算。'],
 ['PREFER 得分率','[2N - 1分图片数 - 2 × 0分图片数] / 2N × 100%','先算每条 PREFER Rule；Gate 使用指定类别内各 PREFER Rule 得分率的平均值。']]
FIT_GATE_ROWS=[
 ['优秀','每条 ≥90%','平均分 ≥50%','每条 ≥70%'],
 ['通过','每条 ≥80%','—','每条 ≥60%'],
 ['待定','至多2条为60%–<80%','—','未全部达到60%，由UX判断'],
 ['不通过','任意一条 <60%','—','—']]
TUNE_GATE_ROWS=[
 ['优秀','每条 ≥90%','平均分 ≥60%','每条 ≥70%'],
 ['通过','每条 ≥85%','—','每条 ≥70%'],
 ['待定','至多2条为70%–<85%','—','未全部达到70%，由UX判断'],
 ['不通过','任意一条 <70%','—','—']]
def table_html(headers,rows,pending_from=None):
 def cell(x):
  cls=' class="must-text"' if x=='MUST' else (' class="prefer-text"' if x=='PREFER' else '')
  return '<td'+cls+'>'+h(x).replace('\n','<br>')+'</td>'
 return '<table><thead><tr>'+''.join('<th>'+h(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr'+(' class="pending-row"' if pending_from is not None and i>=pending_from else '')+'>'+''.join(cell(x) for x in row)+'</tr>' for i,row in enumerate(rows))+'</tbody></table>'
def scoring_table_html(s,priority):
 rows=[]
 for r in scoring_items(s,priority):
  judgments=rule_judgments(r)
  for i,(result,criterion,state) in enumerate(judgments):
   classes=[]
   if state!='normal':classes.append('score-'+state)
   cls=' class="'+' '.join(classes)+'"' if classes else ''
   rule_cell='<td rowspan="'+str(len(judgments))+'">'+h(r['id']+' '+r['name'])+'</td>' if i==0 else ''
   rows.append('<tr'+cls+'>'+rule_cell+'<td>'+h(result)+'</td><td>'+h(criterion)+'</td></tr>')
 return '<table><thead><tr><th>Rule</th><th>结果</th><th>判断标准</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
def callout_html(text):return '<div class="attention">'+h(text)+'</div>'
def legend_html():
 return '<div class="legend">'+''.join('<span style="background:'+COLORS[state]+';'+('color:#243746;border:1px dashed #9aa0a6' if state=='NOT_APPLICABLE' else '')+'">'+label+'</span>' for label,state in LEGEND)+'</div>'
def dots_svg(s):
 shape='M942.5 291.3C925 183.4 840.6 99 732.7 81.5C662.6 70.1 588.6 64 512 64S361.4 70.1 291.3 81.5C183.4 99 99 183.4 81.5 291.3C70.1 361.4 64 435.4 64 512S70.1 662.6 81.5 732.7C99 840.6 183.4 925 291.3 942.5C361.4 953.9 435.4 960 512 960S662.6 953.9 732.7 942.5C840.6 925 925 840.6 942.5 732.7C953.9 662.6 960 588.6 960 512S953.9 361.4 942.5 291.3Z'
 out=['<svg viewBox="0 0 620 240" xmlns="http://www.w3.org/2000/svg"><defs>']; rows={r['checkId']:r for r in s['traversal']}
 for g in GROUPS.values():
  for c in g['checks']:
   cid=c['id'].replace('.','-');out.append(f'<clipPath id="right-{cid}"><rect x="0" y="-20" width="20" height="40"/></clipPath>')
 out.append('</defs>')
 for j in range(7):out.append(f'<text x="{160+j*62}" y="11" text-anchor="middle" font-size="9" font-weight="700" fill="#526171">{j+1}</text>')
 for i,g in enumerate(GROUPS.values()):
  y=32+i*42;out.append(f'<text x="0" y="{y+4}" font-size="12" font-weight="700">{h(g["id"]+" "+g["name"])}</text>')
  for j,c in enumerate(g['checks']):
   x=160+j*62;states,u=check_disposition(s,rows[c['id']]);fill=COLORS.get(states[0],'white') if states else 'white'
   transform=f'translate({x-12} {y-12}) scale(0.023438)'
   outline=' stroke="#9aa0a6" stroke-width="1" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"' if states and states[0]=='NOT_APPLICABLE' else ''
   out.append(f'<path d="{shape}" transform="{transform}" fill="{fill}"{outline}/>')
   if len(states)>1:
    cid=c['id'].replace('.','-');out.append(f'<g transform="translate({x} {y})" clip-path="url(#right-{cid})"><path d="{shape}" transform="translate(-12 -12) scale(0.023438)" fill="{COLORS[states[1]]}"/></g>')
 out.append('</svg>');return ''.join(out)
CSS='<style>.compact.page{padding:28px!important}.compact table{width:100%;border-collapse:collapse;font-size:11px}.compact td,.compact th{padding:6px;border-bottom:1px solid #dce4e8;text-align:left;vertical-align:top}.compact th{background:#edf2f5;font-weight:700}.compact tr.pending-row td{background:#fff4c7}.compact tr.score-fail td{color:#e65043}.compact tr.score-partial td{color:#ee7a2f}.compact td.must-text{color:#97c657;font-weight:700}.compact td.prefer-text{color:#648fdc;font-weight:700}.compact p,.compact pre,.compact td{font-size:12px;line-height:1.55}.compact .small{font-size:9px;color:#526171}.compact .reference-label{font-size:17px;font-weight:700;color:#243746;margin-bottom:5px}.compact h1{font-size:24px;font-weight:700}.compact h2{font-size:17px;font-weight:700}.compact img{object-fit:contain}.compact .refs{display:flex;gap:8px;flex-wrap:wrap}.compact figure{margin:0;width:30%}.compact figure img{width:100%;height:140px}.compact pre{white-space:pre-wrap;font-family:sans-serif}.compact pre.prompt-bg{background:#eaf0f4;padding:10px 12px}.compact .hero{float:right;width:110px;height:110px;margin-left:16px}.compact .legend{display:flex;gap:7px;margin:7px 0 9px}.compact .legend span{padding:3px 9px;border-radius:7px;color:white;font-size:9px}.compact .legend span:nth-child(3),.compact .legend span:nth-child(5){color:#243746}.compact .attention{background:#fff4c7;border-radius:8px;padding:9px 12px;margin:8px 0 10px;font-size:11px;line-height:1.5}</style>'
def page(title,body):return '<div class="page compact"><h1>'+h(title)+'</h1>'+body+'</div>'
def reference_page(body):return '<div class="page compact"><p class="reference-label">REFERENCE</p><h1>标准遍历表 Criteria Check List</h1>'+body+'</div>'
def p(x):return '<p>'+h(x)+'</p>'
def header(s,uris,hero=False):
 right='<img class="hero" src="'+uris[[r['id'] for r in s['references']].index(s['heroReference'])]+'">' if hero else '<p style="float:right">一致性：'+('通过' if consistency_passed(s) else '待解决')+'</p>'
 return right+p(s['targetVisual'])+p('使用情景：'+s['usageScenario'])
def alignment_html(s,uris):
 pics='<div class="refs">'+''.join('<figure><img src="'+u+'"><figcaption>'+h(r['id']+' '+r['caption'])+'</figcaption></figure>' for r,u in zip(s['references'],uris))+'</div>'
 a=header(s,uris)+pics+'<h2>参考方向一致性</h2>'+table_html(['效果总结','满足项','结论','来自遍历项'],consistency_rows(s))+p(CONSISTENCY_NOTE)
 b='<h2>核心效果</h2>'+table_html(['效果','关联检查项','Rules'],core_rows(s))+'<h2>允许变化</h2>'+table_html(['处理','检查项','理由'],variation_rows(s))
 return CSS+page(s['templateName'],a)+page('效果与允许变化',b)+reference_page(table_html(['一级 Criteria','子项编号','检查项','观察或判断内容'],appendix_rows()))
def definition_html(s,uris,final_define=False):
 base_rules=rule_rows(s);proposals=pending_proposal_rows(s)
 a=header(s,uris,True)+'<h2>初版 Rules · '+('待 UX 确认' if s['reviewReport']['ruleStatus']=='DRAFT' else '已确认')+'</h2>'+callout_html(confirmation(s))+table_html(['Rule','要求','建议级别','来自遍历项'],base_rules+proposals,len(base_rules) if proposals else None)
 a+='<h2>初版 Prompt '+h(s['promptVersion'])+'</h2><pre class="prompt-bg">'+h(s['seedreamPrompt'])+'</pre><p class="small">依据 Skill 内置 Seedream Prompt 指南 2026-09-10.1；'+h(s['promptGuideReview']['targetModel'])+'。尚未实测。</p>'
 b='<p class="reference-label">REFERENCE</p><h2>1 Criteria-Rules映射</h2>'+dots_svg(s)+legend_html()+'<h2>2 Rules-Prompt映射</h2>'+table_html(['Prompt','Rules'],[[m['sentence'],' / '.join(m['ruleIds'])] for m in s['promptRuleMap']])
 c=callout_html(SCORE_NOTE)+'<h2>MUST Rules</h2>'+scoring_table_html(s,'MUST')+'<h2>PREFER Rules</h2>'+scoring_table_html(s,'PREFERRED')
 d=''
 for t in s['reviewReport']['testMaterials']:
  d+='<h2>'+h(TIER_LABELS[t['tier']])+'</h2>'+p('输入范围：'+t['definition'])+table_html(['序号','建议素材','输入特征'],material_rows(t))
 return CSS+page(s['templateName']+' · DEFINE 初版',a)+page('Criteria-Rules-Prompt映射',b)+page('测试评分卡',c)+page('测试材料',d)+reference_page(table_html(['一级 Criteria','子项编号','检查项','观察或判断内容'],appendix_rows()))


def chat_summary(s):
    assessment=definition_assessment(s)
    lines=['**'+s['templateName']+'**',s['targetVisual'],'使用情景：'+s['usageScenario'],
           '**模板可定义性：'+('可定义' if assessment['definable'] else '待补充')+'。** 收敛度 '+format(assessment['convergence']*100,'.1f')+'%，有效 Rules '+str(len(assessment['qualifiedRuleIds']))+' 条。',
           '> '+confirmation(s),
           '| Rule | 初版要求 | 建议级别 | 来自遍历项 |','| --- | --- | --- | --- |']
    lines+=['| '+' | '.join(row)+' |' for row in rule_rows(s)]
    lines+=['初版 Prompt '+s['promptVersion']+'：','```text',s['seedreamPrompt'],'```','依据本地 Seedream 指南；'+s['promptGuideReview']['reviewNote'],'状态：尚未进行 Seedream 生图测试。']
    return '\n\n'.join(lines[:4])+'\n\n'+'\n'.join(lines[4:])+'\n'

def export_pdf(s,refs,out,font,include_examples=False,revision=1):
 from reportlab.pdfgen import canvas
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.ttfonts import TTFont
 from reportlab.platypus import Paragraph,Table,TableStyle
 from reportlab.lib.styles import ParagraphStyle
 from reportlab.lib import colors
 from PIL import Image
 font,bold_font=resolve_font_pair(font)
 pdfmetrics.registerFont(TTFont('ReportCJK',font));pdfmetrics.registerFont(TTFont('ReportCJKBold',bold_font))
 W,H=595,842;left=38;width=519
 BODY=9.5;TABLE=8.5;SMALL=7.5;H1=20;H2=12
 style=ParagraphStyle('body',fontName='ReportCJK',fontSize=BODY,leading=13.5,textColor=colors.HexColor('#243746'),wordWrap='CJK')
 def para(text,size=BODY,bold=False,color=None):
  st=ParagraphStyle('s',parent=style,fontName='ReportCJKBold' if bold else 'ReportCJK',fontSize=size,leading=size*1.42,textColor=colors.HexColor(color) if color else style.textColor)
  return Paragraph(h(text).replace('\n','<br/>'),st)
 class Doc:
  def __init__(self,name,footer='DEFINE 初版 / 未经 Seedream 实测',header_label='DEFINE'):self.c=canvas.Canvas(str(out/name),pagesize=(W,H));self.n=0;self.y=H-38;self.footer=footer;self.header_label=header_label
  def start(self,title,eyebrow=None,title_note=None):
   if self.n:self.c.showPage()
   self.n+=1;self.y=H-38
   label=eyebrow or self.header_label
   if label:
    label_text=label.upper()
    if label_text=='REFERENCE':label_text+='  附录仅供 UX 参考'
    elif label_text=='DEFINE':label_text+='  请 UX 逐项查对、修正或补充'
    self.c.setFont('ReportCJKBold',8);self.c.setFillColor(colors.HexColor('#7b8791'));self.c.drawString(left,self.y,label_text);self.y-=18
   title_top=self.y;self.text(title,H1,bold=True)
   if title_note:
    self.c.setFont('ReportCJK',7.2);self.c.setFillColor(colors.HexColor('#7b8791'));self.c.drawRightString(W-left,title_top-17,title_note)
   self.y-=8
   self.c.setFont('ReportCJK',8);self.c.setFillColor(colors.HexColor('#687785'));self.c.drawString(left,22,s['templateName']+' / '+self.footer);self.c.drawRightString(W-left,22,str(self.n))
  def report_header(self,prompt_version,conclusion,test_count,model='Seedream（待填写）'):
   if self.n:self.c.showPage()
   self.n+=1;self.y=H-38
   self.c.setFillColor(colors.HexColor('#687785'));self.c.setFont('ReportCJKBold',8);self.c.drawString(left,802,'规则评分  R U L E  S C O R I N G')
   self.c.setFillColor(colors.HexColor('#243746'));self.c.setFont('ReportCJKBold',20);self.c.drawString(left,770,s['templateName'])
   self.c.setFillColor(colors.HexColor('#f4f4f1'));self.c.setStrokeColor(colors.HexColor('#c9c9c4'));self.c.roundRect(190,753,82,24,12,fill=1,stroke=1)
   self.c.setFillColor(colors.HexColor('#243746'));self.c.setFont('ReportCJKBold',10);self.c.drawCentredString(231,761,'Prompt '+prompt_version)
   self.c.setFillColor(colors.white);self.c.roundRect(280,753,128,24,12,fill=1,stroke=1);self.c.setFillColor(colors.HexColor('#687785'));self.c.setFont('ReportCJK',8);self.c.drawCentredString(344,761,model)
   self.c.setStrokeColor(colors.HexColor('#d6d6d2'));self.c.line(455,746,455,804)
   self.c.setFillColor(colors.HexColor('#687785'));self.c.setFont('ReportCJKBold',8);self.c.drawString(480,794,'本轮结论')
   status_color={'优秀':'#78b83e','通过':'#6f9fdf','待定':'#d5a91d','不通过':'#e65043'}.get(conclusion,'#243746')
   self.c.setFillColor(colors.HexColor(status_color));self.c.setFont('ReportCJKBold',17);self.c.drawString(480,766,conclusion)
   self.c.setFillColor(colors.HexColor('#687785'));self.c.setFont('ReportCJK',8);self.c.drawString(left,738,str(test_count)+' 个测试输入')
   self.c.setStrokeColor(colors.HexColor('#d6d6d2'));self.c.line(left,726,W-left,726)
   self.c.setFont('ReportCJK',8);self.c.setFillColor(colors.HexColor('#687785'));self.c.drawString(left,22,s['templateName']+' / '+self.footer);self.c.drawRightString(W-left,22,str(self.n));self.y=706
  def text(self,t,size=BODY,w=width,bold=False):
   p=para(t,size,bold);_,hh=p.wrap(w,800)
   if self.y-hh<42:raise ValueError(f'page {self.n} text overflow: {t[:30]}')
   p.drawOn(self.c,left,self.y-hh);self.y-=hh+6
  def title(self,t):self.y-=5;self.text(t,H2,bold=True)
  def colored_title(self,t,color):
   self.y-=5;p=para(t,H2,True,color);_,hh=p.wrap(width,800)
   if self.y-hh<42:raise ValueError(f'page {self.n} title overflow: {t}')
   p.drawOn(self.c,left,self.y-hh);self.y-=hh+6
  def callout(self,t,size=9):
   p=para(t,size);_,hh=p.wrap(width-16,800);box_h=hh+14
   if self.y-box_h<42:raise ValueError(f'page {self.n} callout overflow: {t[:30]}')
   self.c.setFillColor(colors.HexColor('#fff4c7'));self.c.roundRect(left,self.y-box_h,width,box_h,7,fill=1,stroke=0)
   p.drawOn(self.c,left+8,self.y-hh-7);self.y-=box_h+8
  def title_callout(self,t):
   x=345;w=W-left-x;box_h=34;y=self.y+5
   p=para(t,7.6);_,hh=p.wrap(w-16,box_h-8)
   self.c.setFillColor(colors.HexColor('#fff4c7'));self.c.roundRect(x,y,w,box_h,7,fill=1,stroke=0)
   p.drawOn(self.c,x+8,y+(box_h-hh)/2)
  def boxtext(self,t,size=8.8):
   p=para(t,size);_,hh=p.wrap(width-18,800);box_h=hh+14
   if self.y-box_h<42:raise ValueError(f'page {self.n} box text overflow: {t[:30]}')
   self.c.setFillColor(colors.HexColor('#eaf0f4'));self.c.rect(left,self.y-box_h,width,box_h,fill=1,stroke=0)
   p.drawOn(self.c,left+9,self.y-hh-7);self.y-=box_h+7
  def table(self,heads,rows,widths,size=TABLE,pending_from=None):
   cells=[]
   for ri,row in enumerate([heads]+rows):
    built=[]
    for x in row:
     color='#97c657' if x=='MUST' else ('#648fdc' if x=='PREFER' else None)
     built.append(para(x,size,bold=(ri==0 or color is not None),color=color))
    cells.append(built)
   tab=Table(cells,colWidths=widths)
   tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d6e0e7')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
   if pending_from is not None:tab.setStyle(TableStyle([('BACKGROUND',(0,pending_from+1),(-1,-1),colors.HexColor('#fff4c7'))]))
   for row_index,row in enumerate(rows,1):
    if any(str(value) in ('待确认','待定') or '· 待定' in str(value) for value in row):tab.setStyle(TableStyle([('BACKGROUND',(0,row_index),(-1,row_index),colors.HexColor('#fff4c7'))]))
   _,hh=tab.wrap(width,800)
   if self.y-hh<42:raise ValueError(f'page {self.n} table overflow: {hh}, available {self.y-42}')
   tab.drawOn(self.c,left,self.y-hh);self.y-=hh+9
  def scoring_table(self,spec,priority):
   cells=[[para('Rule',TABLE,True),para('结果',TABLE,True),para('判断标准',TABLE,True)]];spans=[];colored=[]
   for r in scoring_items(spec,priority):
    first=len(cells);judgments=rule_judgments(r)
    for i,(result,criterion,state) in enumerate(judgments):
     color='#e65043' if state=='fail' else ('#ee7a2f' if state=='partial' else None)
     cells.append([para(r['id']+' '+r['name'],TABLE) if i==0 else '',para(result,TABLE,color=color),para(criterion,TABLE,color=color)])
     if color:colored.append((len(cells)-1,color))
    spans.append(('SPAN',(0,first),(0,first+len(judgments)-1)))
   tab=Table(cells,colWidths=[108,54,357])
   commands=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d6e0e7')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]
   commands.extend(spans)
   for ri,color in colored:commands.append(('TEXTCOLOR',(1,ri),(2,ri),colors.HexColor(color)))
   tab.setStyle(TableStyle(commands));_,hh=tab.wrap(width,800)
   if self.y-hh<42:raise ValueError(f'page {self.n} scoring table overflow: {hh}, available {self.y-42}')
   tab.drawOn(self.c,left,self.y-hh);self.y-=hh+9
  def prompt_mapping(self,mappings,size=8.2):
   priorities={r['id']:r['priority'] for r in s['rules']}
   rule_style=ParagraphStyle('rule-map',parent=style,fontName='ReportCJKBold',fontSize=size,leading=size*1.42,textColor=colors.HexColor('#243746'))
   prompt_cells=[];rule_cells=[];row_heights=[]
   for mapping in mappings:
    tokens=[]
    for rule_id in mapping['ruleIds']:
     color='#97c657' if priorities.get(rule_id)=='MUST' else '#648fdc';tokens.append('<font color="'+color+'">'+h(rule_id)+'</font>')
    prompt_cell=para(mapping['sentence'],size);rule_cell=Paragraph(' / '.join(tokens),rule_style)
    _,prompt_h=prompt_cell.wrap(424,800);_,rule_h=rule_cell.wrap(61,800)
    prompt_cells.append(prompt_cell);rule_cells.append(rule_cell);row_heights.append(max(prompt_h,rule_h)+8)
   header_h=27;hh=header_h+sum(row_heights);left_w=438;gap=6;right_w=75
   if self.y-hh<42:raise ValueError(f'page {self.n} prompt mapping overflow: {hh}, available {self.y-42}')
   bottom=self.y-hh;right_x=left+left_w+gap
   self.c.saveState()
   self.c.setFillColor(colors.HexColor('#eaf0f4'));self.c.rect(left,self.y-header_h,left_w,header_h,fill=1,stroke=0);self.c.rect(right_x,self.y-header_h,right_w,header_h,fill=1,stroke=0)
   self.c.setFillColor(colors.HexColor('#f4f7f9'));self.c.rect(left,bottom,left_w,hh-header_h,fill=1,stroke=0)
   self.c.setStrokeColor(colors.HexColor('#d6e0e7'));self.c.setLineWidth(.3)
   self.c.rect(left,bottom,left_w,hh,fill=0,stroke=1);self.c.rect(right_x,bottom,right_w,hh,fill=0,stroke=1)
   self.c.line(left,self.y-header_h,left+left_w,self.y-header_h);self.c.line(right_x,self.y-header_h,right_x+right_w,self.y-header_h)
   self.c.restoreState()
   prompt_header=para('Prompt',size,True);rule_header=para('Rules',size,True)
   prompt_header.wrapOn(self.c,left_w-14,header_h-8);prompt_header.drawOn(self.c,left+7,self.y-header_h+6)
   rule_header.wrapOn(self.c,right_w-14,header_h-8);rule_header.drawOn(self.c,right_x+7,self.y-header_h+6)
   # Emit the complete Prompt column before the Rules column. This preserves
   # continuous Prompt copy/paste order in PDF readers while rows stay aligned.
   cursor=self.y-header_h
   for cell,row_h in zip(prompt_cells,row_heights):
    _,cell_h=cell.wrap(left_w-14,row_h-8);cell.drawOn(self.c,left+7,cursor-4-cell_h);cursor-=row_h
   cursor=self.y-header_h
   for cell,row_h in zip(rule_cells,row_heights):
    _,cell_h=cell.wrap(right_w-14,row_h-8);cell.drawOn(self.c,right_x+7,cursor-4-cell_h);cursor-=row_h
   self.y-=hh+9
  def prompt_mapping_height(self,mappings,size=8.2):
   priorities={r['id']:r['priority'] for r in s['rules']};rule_style=ParagraphStyle('rule-map-measure',parent=style,fontName='ReportCJKBold',fontSize=size,leading=size*1.42)
   total=27
   for mapping in mappings:
    prompt_cell=para(mapping['sentence'],size);rule_cell=Paragraph(' / '.join(mapping['ruleIds']),rule_style)
    _,prompt_h=prompt_cell.wrap(424,800);_,rule_h=rule_cell.wrap(61,800);total+=max(prompt_h,rule_h)+8
   return total
  def prompt_mapping_pages(self,mappings,size=8.2,title='初始 Prompt v1.0',eyebrow=None):
   remaining=list(mappings);page_index=0
   while remaining:
    page_index+=1;self.start(title if page_index==1 else title+'（续）',eyebrow)
    chunk=[]
    for mapping in remaining:
     candidate=chunk+[mapping]
     if self.prompt_mapping_height(candidate,size)<=self.y-62:chunk=candidate
     else:break
    if not chunk:raise ValueError('A single Prompt mapping segment is too large for one page; split that segment without deleting content')
    self.prompt_mapping(chunk,size);remaining=remaining[len(chunk):]
   self.text('本 Prompt 依据 Seedream 官方提示词指南编写。',7.5)
  def gate_table(self,rows):
   status_colors={'优秀':'#78b83e','通过':'#6f9fdf','待定':'#d5a91d','不通过':'#e65043'}
   cells=[[para('结论',10,True),para('A / B · MUST',10,True),para('A / B · PREFER',10,True),para('C · MUST',10,True)]]
   for status,must,pref,cgate in rows:cells.append([para(status,10,True,status_colors[status]),para(must,10),para(pref,10),para(cgate,10)])
   tab=Table(cells,colWidths=[52,174,135,158]);tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d6e0e7')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));_,hh=tab.wrap(width,800)
   if self.y-hh<42:raise ValueError(f'page {self.n} gate table overflow: {hh}, available {self.y-42}')
   tab.drawOn(self.c,left,self.y-hh);self.y-=hh+7
  def image(self,path,x,y,w,hh):
   with Image.open(path) as im:iw,ih=im.size
   scale=min(w/iw,hh/ih);dw,dh=iw*scale,ih*scale
   self.c.drawImage(str(path),x+(w-dw)/2,y-hh+(hh-dh)/2,dw,dh,mask='auto')
  def score_matrix(self,rules,priority):
   sample={'R01':['100%','100%','75%','92%'],'R02':['100%','83%','75%','86%'],'R03':['100%','100%','75%','92%'],'R04':['83%','83%','75%','81%'],'R05':['75%','67%','50%','66%'],'R06':['100%','100%','100%','100%'],'R07':['100%','83%','75%','86%'],'R08':['83%','67%','50%','69%']}
   filtered=[r for r in rules if r['priority']==priority];rows=[]
   for r in filtered:rows.append([r['id']+' '+r['name']]+sample.get(r['id'],['—','—','—','—']))
   cells=[[para(x,9.2,True) for x in ['Rule','A 核心场景','B 拓展场景','C 边缘场景','Rule 总分']]]
   failure_cells={'R05':{1,4},'R07':{3,4},'R08':{2,4}}
   for r,row in zip(filtered,rows):
    built=[para(row[0],9.2)]
    for ci,value in enumerate(row[1:],1):built.append(para(value,9.2,bold=(ci==4),color='#e65043' if ci in failure_cells.get(r['id'],set()) else None))
    cells.append(built)
   tab=Table(cells,colWidths=[167,88,88,88,88])
   cmds=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ef')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#c8d5dc')),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#d6e0e7')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(1,1),(-1,-1),'CENTER'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]
   tab.setStyle(TableStyle(cmds));_,hh=tab.wrap(width,800);tab.drawOn(self.c,left,self.y-hh);self.y-=hh+10
  def evidence_pair(self,test_id,rule_lines):
   block_h=178;y=self.y-block_h
   self.c.setFillColor(colors.HexColor('#f1f3f5'));self.c.roundRect(left,y,152,142,6,fill=1,stroke=0);self.c.roundRect(left+164,y,152,142,6,fill=1,stroke=0)
   self.c.setFillColor(colors.HexColor('#9aa4ad'));self.c.setFont('ReportCJKBold',9);self.c.drawCentredString(left+76,y+70,'INPUT 待补');self.c.drawCentredString(left+240,y+70,'OUTPUT 待补')
   self.c.setFillColor(colors.HexColor('#243746'));self.c.setFont('ReportCJKBold',9);self.c.drawString(left,y+151,test_id)
   self.c.drawString(left+332,y+151,'RULE 评分')
   ty=y+128
   for line,color in rule_lines:
    self.c.setFont('ReportCJK',7.5);self.c.setFillColor(colors.HexColor(color));self.c.drawString(left+332,ty,line);ty-=14
   self.y=y-10
  def finish(self):self.c.save()
 def draw_legend(d,counts=None):
  x=left;y=d.y-12
  for label,state in LEGEND:
   display=label+(f' {format_count(counts[state])}/29' if counts is not None else '')
   w=72 if counts is not None else (54 if label not in ('不规定',) else 66)
   d.c.setFillColor(colors.HexColor(COLORS[state]));d.c.setStrokeColor(colors.HexColor('#9aa0a6'));d.c.setLineWidth(.8);d.c.setDash(3,2) if state=='NOT_APPLICABLE' else d.c.setDash()
   d.c.roundRect(x,y-7,w,18,6,fill=1,stroke=1 if state=='NOT_APPLICABLE' else 0);d.c.setDash()
   d.c.setFillColor(colors.white if state in ('MUST','PREFERRED') else colors.HexColor('#243746'));d.c.setFont('ReportCJKBold',7);d.c.drawCentredString(x+w/2,y-1,display)
   x+=w+7
  d.y-=30
 def squircle_path(c,x,y,r=13):
  # The supplied 1024-viewBox path normalized to a centered 2r box.
  q=c.beginPath();k=(2*r)/896;v=lambda n:(n-512)*k
  q.moveTo(x+v(942.5),y-v(291.3));q.curveTo(x+v(925),y-v(183.4),x+v(840.6),y-v(99),x+v(732.7),y-v(81.5))
  q.curveTo(x+v(662.6),y-v(70.1),x+v(588.6),y-v(64),x,y-v(64));q.curveTo(x+v(435.4),y-v(64),x+v(361.4),y-v(70.1),x+v(291.3),y-v(81.5))
  q.curveTo(x+v(183.4),y-v(99),x+v(99),y-v(183.4),x+v(81.5),y-v(291.3));q.curveTo(x+v(70.1),y-v(361.4),x+v(64),y-v(435.4),x+v(64),y)
  q.curveTo(x+v(64),y-v(588.6),x+v(70.1),y-v(662.6),x+v(81.5),y-v(732.7));q.curveTo(x+v(99),y-v(840.6),x+v(183.4),y-v(925),x+v(291.3),y-v(942.5))
  q.curveTo(x+v(361.4),y-v(953.9),x+v(435.4),y-v(960),x,y-v(960));q.curveTo(x+v(588.6),y-v(960),x+v(662.6),y-v(953.9),x+v(732.7),y-v(942.5))
  q.curveTo(x+v(840.6),y-v(925),x+v(925),y-v(840.6),x+v(942.5),y-v(732.7));q.curveTo(x+v(953.9),y-v(662.6),x+v(960),y-v(588.6),x+v(960),y)
  q.curveTo(x+v(960),y-v(435.4),x+v(953.9),y-v(361.4),x+v(942.5),y-v(291.3));q.close();return q
 def draw_squircle(c,x,y,state,r=13):
  c.setFillColor(colors.HexColor(COLORS[state]))
  if state=='NOT_APPLICABLE':
   c.setStrokeColor(colors.HexColor('#9aa0a6'));c.setLineWidth(.8);c.setDash(3,2);c.drawPath(squircle_path(c,x,y,r),fill=1,stroke=1);c.setDash()
  else:c.drawPath(squircle_path(c,x,y,r),fill=1,stroke=0)
 def draw_criteria_map(doc,compact=False,legend_counts=None,show_legend=True):
  traversal={row['checkId']:row for row in s['traversal']};start=doc.y;step_y=27 if compact else 37;start_x=left+151;step_x=51
  for j in range(7):
   x=start_x+j*step_x;doc.c.setFont('ReportCJKBold',7.5);doc.c.setFillColor(colors.HexColor('#526171'));doc.c.drawCentredString(x,start-3,str(j+1))
  for i,g in enumerate(GROUPS.values()):
   y=start-22-i*step_y;doc.c.setFont('ReportCJKBold',8.5);doc.c.setFillColor(colors.HexColor('#243746'));doc.c.drawString(left,y-3,g['id']+' '+g['name'])
   for j,ch in enumerate(g['checks']):
    x=start_x+j*step_x;states,_=check_disposition(s,traversal[ch['id']]);draw_squircle(doc.c,x,y,states[0] if states else 'NOT_APPLICABLE',7.8 if compact else 9.1)
    if len(states)>1:
     doc.c.saveState();clip=doc.c.beginPath();clip.rect(x,y-10,10,20);doc.c.clipPath(clip,stroke=0,fill=0);draw_squircle(doc.c,x,y,states[1],7.8 if compact else 9.1);doc.c.restoreState()
  doc.y=start-(5*step_y+25)
  if show_legend:draw_legend(doc,legend_counts)
 def top(d,hero=False):
  if hero:
   pos=[r['id'] for r in s['references']].index(s['heroReference']);start=d.y;frame=140;frame_x=W-left-frame
   d.c.setFillColor(colors.HexColor('#f1f3f5'));d.c.rect(frame_x,start-frame,frame,frame,fill=1,stroke=0);d.image(refs[pos],frame_x,start,frame,frame)
   input_text=s.get('inputSummary') or ('单张图片。' if s.get('runtimeInput')=='Single image' else s.get('runtimeInput','输入内容。'))
   copy_w=frame_x-left-18
   d.text(s['targetVisual'],12,copy_w,bold=True);d.y-=8
   d.text('Input：',10.5,copy_w);d.text(input_text,11.5,copy_w);d.y-=5
   d.text('Scenario：',10.5,copy_w);d.text(s['usageScenario'],11.5,copy_w)
   d.y=min(d.y,start-frame-10)
  else:
   d.c.setFont('ReportCJKBold',12);d.c.setFillColor(colors.HexColor('#278464' if consistency_passed(s) else '#ab7020'));d.c.drawRightString(557,800,'可定义性：'+('可定义' if consistency_passed(s) else '待补充'))
   d.text(s['targetVisual']);d.text('使用情景：'+s['usageScenario'])
 def appendix(d):d.start('标准遍历表 Criteria Check List','REFERENCE');d.table(['一级 Criteria','子项编号','检查项','观察或判断内容'],appendix_rows(),[91,43,91,294],7.2)
 assessment=definition_assessment(s)
 u=Doc('ux-review-summary.pdf','模板定义 / TO UX','REFERENCE');u.start('模板可定义性')
 u.c.setStrokeColor(colors.HexColor('#d6d6d2'));u.c.line(455,746,455,804)
 u.c.setFont('ReportCJKBold',8);u.c.setFillColor(colors.HexColor('#687785'));u.c.drawString(480,794,'结论')
 u.c.setFont('ReportCJKBold',17);u.c.setFillColor(colors.HexColor('#278464' if assessment['definable'] else '#d5a91d'));u.c.drawString(480,766,'可定义' if assessment['definable'] else '待补充')
 u.text('判断规则：有效 Rule Set 成立，且 Criteria 收敛度 ≥40%，判定为“可定义”。Rule Set 需有 4–12 条获得足够图片支持的独立 Rules，其中至少 3 条 MUST，并以 MUST 覆盖 C2 形态与组织和 C3 视觉表现。',8.2)
 u.text('本组：收敛度 '+format(assessment['convergence']*100,'.1f')+'%（'+assessment['convergenceLabel']+'） · 有效 Rules '+str(len(assessment['qualifiedRuleIds']))+' 条 · Rule Set '+('成立' if assessment['ruleSetPassed'] else '未成立'),8.5,bold=True)
 _,counts=disposition_summary(s);draw_legend(u,counts);draw_criteria_map(u,True,show_legend=False)
 u.text('黄金参考图',9.5,bold=True);strip_top=u.y;gap=7;frame_w=(width-gap*(len(refs)-1))/len(refs);frame_h=51
 for index,(ref,path) in enumerate(zip(s['references'],refs)):
  x=left+index*(frame_w+gap);u.c.setFillColor(colors.HexColor('#f1f3f5'));u.c.rect(x,strip_top-frame_h,frame_w,frame_h,fill=1,stroke=0);u.image(path,x,strip_top,frame_w,frame_h)
  u.c.setFont('ReportCJK',6.8);u.c.setFillColor(colors.HexColor('#687785'));u.c.drawCentredString(x+frame_w/2,strip_top-frame_h-10,ref['id'])
 u.y=strip_top-frame_h-22
 u.title('Rules依据');u.table(['Rules','效果描述','图片依据','Criteria依据'],rules_basis_rows(s),[78,118,112,211],7.5);u.finish()
 d=Doc('template-definition-report.pdf',header_label='DEFINE');d.start(s['templateName']+' · 模板定义');top(d,True)
 d.title('初版 Rules · '+('待 UX 确认' if s['reviewReport']['ruleStatus']=='DRAFT' else '已确认'));base_rules=rule_rows_ids(s);proposals=pending_proposal_rows(s);d.table(['Rule','要求','建议级别'],[[row[0],row[1],row[2]] for row in base_rules+proposals],[42,405,72],7.6,pending_from=len(base_rules) if proposals else None)
 d.start('Criteria-Rules映射','REFERENCE');rows={r['checkId']:r for r in s['traversal']};start=d.y
 for j in range(7):
  x=left+151+j*51;d.c.setFont('ReportCJKBold',7.5);d.c.setFillColor(colors.HexColor('#526171'));d.c.drawCentredString(x,start-3,str(j+1))
 for i,g in enumerate(GROUPS.values()):
  y=start-26-i*37;d.c.setFont('ReportCJKBold',9);d.c.setFillColor(colors.HexColor('#243746'));d.c.drawString(left,y-3,g['id']+' '+g['name'])
  for j,ch in enumerate(g['checks']):
   x=left+151+j*51;states,u=check_disposition(s,rows[ch['id']]);draw_squircle(d.c,x,y,states[0] if states else 'NOT_APPLICABLE',9.1)
   if len(states)>1:
    d.c.saveState();clip=d.c.beginPath();clip.rect(x,y-10,10,20);d.c.clipPath(clip,stroke=0,fill=0);draw_squircle(d.c,x,y,states[1],9.1);d.c.restoreState()
 d.y=start-206;draw_legend(d)
 d.prompt_mapping_pages(s['promptRuleMap'],9.8,'初始 Prompt v1.0','DEFINE')
 d.start('测试评分卡');d.title('MUST Rules');d.scoring_table(s,'MUST');d.title('PREFER Rules');d.scoring_table(s,'PREFERRED')
 d.start('测试材料建议',title_note='以下为测试材料建议，供测试人员参考，不必严格执行')
 for t in s['reviewReport']['testMaterials']:
  d.title(TIER_LABELS[t['tier']]);d.text('输入范围：'+t['definition'],9)
  d.table(['序号','建议素材','输入特征'],material_rows(t),[38,155,326],8.2)
 appendix(d);d.finish()
 def evidence_lines(fails=(),partials=(),zeros=()):
  lines=[]
  for rule in s['rules']:
   if rule['priority']=='MUST':label='MUST '+('不通过' if rule['id'] in fails else '通过');color='#e65043' if rule['id'] in fails else '#243746'
   else:
    score='0分' if rule['id'] in zeros else ('1分' if rule['id'] in partials else '2分');label='PREFER '+score;color='#e65043' if score=='0分' else ('#ee7a2f' if score=='1分' else '#243746')
   lines.append((rule['id']+' '+label,color))
  return lines
 if include_examples:
  r=Doc('fit-tune-gate-reference.pdf','FIT / TUNE REFERENCE');r.start('FIT / TUNE 计算规则','REFERENCE');r.text('假定当前类别测试图总数为 N。MUST 保留单条 Rule 统计；PREFER 在 Gate 中使用类内多条 PREFER Rule 的平均分。');r.table(['指标','公式','统计方式'],CALC_ROWS,[96,217,206],9.5);r.title('FIT GATE');r.gate_table(FIT_GATE_ROWS);r.title('TUNE GATE');r.gate_table(TUNE_GATE_ROWS)
  r.start('测试图片','REFERENCE');r.callout('以下图片位置为灰色占位。正式测试时替换为实际 Input / Output；请 UX 根据测试图片与失败诊断决定是否接受结论及 Prompt 修改。')
  r.evidence_pair('A-01',evidence_lines(fails=('R04',),partials=('R05',)));r.evidence_pair('B-01',evidence_lines(zeros=('R08',)));r.evidence_pair('C-01',evidence_lines(fails=('R07',),partials=('R05',)));r.finish()
  m=Doc('fit-tune-report-format.pdf','FIT 格式示例 / 模拟数据');m.report_header(s['promptVersion'],'通过',16);m.title('场景应用表现');m.table(['指标','A 核心场景','B 拓展场景','C 边缘场景'],[['MUST','93%','90%','79%'],['PREFER','79%','67%','50%']],[112,136,136,135],12);m.title('单项 Rules 表现');m.text('MUST Rules',10,bold=True);m.score_matrix(s['rules'],'MUST');m.text('PREFER Rules',10,bold=True);m.score_matrix(s['rules'],'PREFERRED');m.title('失败诊断与 Prompt 修改');m.table(['问题','关联 Rule','Prompt 修改','测试图片'],[['背景干扰主体','R08','加强“背景元素少且不抢主体”的约束。','B-04、B-06'],['内部细节过多','R07','补充“内部纹样压缩为少量短线或色块”。','C-02'],['轮廓过于规整','R05','强调边缘保留轻微、不均匀起伏。','A-05']],[116,72,243,88],7.8);m.finish()
  # FIT report and its calculation/evidence reference are one delivery.
  from pypdf import PdfReader,PdfWriter
  combined=PdfWriter()
  for source_name in ('fit-tune-report-format.pdf','fit-tune-gate-reference.pdf'):
   for source_page in PdfReader(str(out/source_name)).pages:combined.add_page(source_page)
  for page_number,page_obj in enumerate(combined.pages,1):
   overlay_buffer=BytesIO();overlay_canvas=canvas.Canvas(overlay_buffer,pagesize=(W,H))
   overlay_canvas.setFillColor(colors.white);overlay_canvas.rect(0,0,W,34,fill=1,stroke=0)
   overlay_canvas.setFont('ReportCJK',8);overlay_canvas.setFillColor(colors.HexColor('#687785'))
   overlay_canvas.drawString(left,22,s['templateName']+' / FIT 测试报告 / 格式示例');overlay_canvas.drawRightString(W-left,22,str(page_number));overlay_canvas.save();overlay_buffer.seek(0)
   page_obj.merge_page(PdfReader(overlay_buffer).pages[0])
  with open(out/'fit-report-with-reference.pdf','wb') as combined_file:combined.write(combined_file)

 # Final tester handoff: only the information needed to execute and score the test.
 if ready(s):
  t=Doc('testing-guide.pdf','测试指南 / DEFINE 最终交付','TEST');t.start(s['templateName']+' · 测试指南');top(t,True)
  t.title('Rules');t.table(['Rule','要求','级别'],[[row[0],row[1],row[2]] for row in rule_rows(s)],[42,408,69],8.5)
  t.prompt_mapping_pages(s['promptRuleMap'],10.2,'初始 Prompt v1.0','TEST')
  t.start('测试评分卡');t.title('MUST Rules');t.scoring_table(s,'MUST');t.title('PREFER Rules');t.scoring_table(s,'PREFERRED')
  t.start('测试材料建议',title_note='以下为测试材料建议，供测试人员参考，不必严格执行')
  for material in s['reviewReport']['testMaterials']:
   t.title(TIER_LABELS[material['tier']]);t.text('输入范围：'+material['definition'],9)
   t.table(['序号','建议素材','输入特征'],material_rows(material),[38,155,326],8.2)
  t.finish()
 # UX review combines Alignment and Definition, but keeps the duplicated Criteria appendix only once.
 from pypdf import PdfReader,PdfWriter
 review=PdfWriter();summary=PdfReader(str(out/'ux-review-summary.pdf'));definition=PdfReader(str(out/'template-definition-report.pdf'))
 for page in definition.pages[:-1]:review.add_page(page)
 review.add_page(summary.pages[0]);review.add_page(definition.pages[-1])
 for page_number,page_obj in enumerate(review.pages,1):
  overlay_buffer=BytesIO();overlay_canvas=canvas.Canvas(overlay_buffer,pagesize=(W,H))
  overlay_canvas.setFillColor(colors.white);overlay_canvas.rect(0,0,W,34,fill=1,stroke=0)
  overlay_canvas.setFont('ReportCJK',8);overlay_canvas.setFillColor(colors.HexColor('#687785'))
  overlay_canvas.drawString(left,22,s['templateName']+' / 模板定义 / TO UX');overlay_canvas.drawRightString(W-left,22,str(page_number));overlay_canvas.save();overlay_buffer.seek(0)
  page_obj.merge_page(PdfReader(overlay_buffer).pages[0])
 with open(out/'definition-review-to-ux.pdf','wb') as review_file:review.write(review_file)
 named_review=out/(s['templateName']+'_模板定义_to UX_v'+str(revision)+'.pdf')
 named_review.write_bytes((out/'definition-review-to-ux.pdf').read_bytes())
 if ready(s):(out/(s['templateName']+'_测试指南_to 测试.pdf')).write_bytes((out/'testing-guide.pdf').read_bytes())
 for intermediate in ('ux-review-summary.pdf','template-definition-report.pdf'):
  (out/intermediate).unlink(missing_ok=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('spec',type=Path);ap.add_argument('--font');ap.add_argument('--revision',type=int,default=1);ap.add_argument('--check-only',action='store_true');ap.add_argument('--include-examples',action='store_true',help='also build optional FIT/TUNE format examples');args=ap.parse_args()
 s=validate(json.loads(args.spec.read_text()));font,_=resolve_font_pair(args.font);refs=resolve_reference_paths(args.spec,s);issues=content_budget_issues(s)
 if issues:raise ValueError('DEFINE preflight found '+str(len(issues))+' issue(s):\n- '+'\n- '.join(issues))
 if args.check_only:
  print('DEFINE preflight passed: schema, font, references, and structural material formatting')
  return
 out=args.spec.parent;canonical_prompt=s['seedreamPrompt'].encode('utf-8');prompt_hash=hashlib.sha256(canonical_prompt).hexdigest();export_pdf(s,refs,out,font,args.include_examples,args.revision)
 prompt_paths=(out/('prompt-'+s['promptVersion']+'.txt'),out/'prompt.txt')
 for prompt_path in prompt_paths:prompt_path.write_bytes(canonical_prompt)
 if any(prompt_path.read_bytes()!=canonical_prompt for prompt_path in prompt_paths):raise ValueError('PDF export changed the canonical Prompt artifact')
 (out/'prompt.sha256').write_text(prompt_hash+'\n')
 (out/'seedream-prompt-guide.md').write_text((Path(__file__).resolve().parent.parent/'references/seedream-prompt-guide.md').read_text())
 (out/'traversal-audit.html').write_text('<meta charset="utf-8">'+CSS+audit_body(s))
if __name__=='__main__':main()
