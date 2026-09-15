"""v0.4 DEFINE contract: coverage checks, independent rules, auditable handoff.

Structural validation is not a claim of visual or semantic correctness.
"""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / 'references/traversal-v2.json').read_text())
GROUPS = {x['id']: x for x in CATALOG['groups']}
CHECKS = {c['id']: c['name'] for g in GROUPS.values() for c in g['checks']}
SCHEMA = json.loads((ROOT / 'schemas/template-spec-v04.schema.json').read_text())


def structural(value, schema, path='$'):
    """Validate the deliberately small JSON Schema subset used by v0.4."""
    kind = schema.get('type')
    checks = {'object': lambda: isinstance(value, dict), 'array': lambda: isinstance(value, list),
              'string': lambda: isinstance(value, str), 'integer': lambda: type(value) is int,
              'boolean': lambda: type(value) is bool, 'number': lambda: type(value) in (int, float)}
    if kind and not checks[kind](): raise ValueError(f'{path}: expected {kind}')
    if 'const' in schema and value != schema['const']: raise ValueError(f'{path}: wrong constant')
    if 'enum' in schema and value not in schema['enum']: raise ValueError(f'{path}: invalid value')
    if kind == 'object':
        missing = set(schema.get('required', [])) - value.keys()
        extra = value.keys() - schema.get('properties', {}).keys()
        if missing or (schema.get('additionalProperties') is False and extra):
            raise ValueError(f'{path}: missing {sorted(missing)}, extra {sorted(extra)}')
        for key, item in value.items():
            if key in schema.get('properties', {}): structural(item, schema['properties'][key], path+'.'+key)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            raise ValueError(f'{path}: invalid item count')
        if schema.get('uniqueItems') and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            raise ValueError(f'{path}: duplicate items')
        for i, item in enumerate(value): structural(item, schema['items'], f'{path}[{i}]')
    elif kind == 'string':
        if len(value) < schema.get('minLength', 0) or ('pattern' in schema and not re.search(schema['pattern'], value)):
            raise ValueError(f'{path}: invalid text')
    elif kind in ('integer', 'number'):
        if value < schema.get('minimum', -float('inf')) or value > schema.get('maximum', float('inf')):
            raise ValueError(f'{path}: out of range')


def ready(spec):
    return ((not spec.get('reviewReport') or (spec['reviewReport']['ruleStatus']=='CONFIRMED' and consistency_passed(spec))) and spec['goal']['status'] == 'CONFIRMED' and not spec['goal']['questions']
            and not any(f['decision'] == 'PENDING_UX' for x in spec['traversal'] for f in x['findings']))


def validate(spec):
    structural(spec, SCHEMA)
    if spec.get("reviewReport"): validate_review(spec)
    refs = [x['id'] for x in spec['references']]
    if len(refs) != len(set(refs)) or spec['heroReference'] not in refs: raise ValueError('invalid reference IDs/hero')
    ids = [r['id'] for r in spec['rules']]
    if len(ids) != len(set(ids)): raise ValueError('duplicate Rule IDs')
    rules = {r['id']: r for r in spec['rules']}
    checks = [x['checkId'] for x in spec['traversal']]
    if len(checks) != len(set(checks)) or set(checks) != set(CHECKS): raise ValueError('traversal must cover every fixed check exactly once')
    confirmation = spec['goal']['uxConfirmation'].strip()
    if spec['goal']['status'] == 'CONFIRMED' and not confirmation: raise ValueError('confirmed goal needs actual UX confirmation evidence')
    if spec['goal']['status'] == 'DRAFT' and confirmation: raise ValueError('draft goal cannot claim UX confirmation')
    def sources(items):
        for item in items:
            if item['sourceId'] not in set(refs) | {'GOAL', 'USAGE', 'RUNTIME'}: raise ValueError('unknown evidence source')
            if item['kind'] == 'OBSERVED' and item['sourceId'] not in refs: raise ValueError('observations need an image reference')
            if item['kind'] == 'UX' and item['sourceId'] in refs: raise ValueError('image alone is not UX intent')
    retained = set()
    for entry in spec['traversal']:
        for finding in entry['findings']:
            sources(finding['sources'])
            targets = finding['ruleIds']
            if len(targets) != len(set(targets)) or not set(targets) <= rules.keys(): raise ValueError('invalid traversal Rule target')
            if finding['decision'] in ('RULE', 'EVIDENCE'):
                if not targets or not finding['sources']: raise ValueError('retained findings need target and evidence')
                if finding['decision'] == 'RULE': retained.update(targets)
            elif targets: raise ValueError('non-retained finding must not point to a scored Rule')
    if spec.get('reviewReport'):
        mapped_draft={rid for m in spec['promptRuleMap'] for rid in m['ruleIds']}
        if {r['id'] for r in spec['rules'] if r['implementation']['method']=='PROMPT'}-mapped_draft:
            raise ValueError('draft Prompt implementation missing mapping')
    if retained != set(ids): raise ValueError('every Rule needs a retained traversal finding')
    texts = set()
    for rule in spec['rules']:
        # v2 derives source evidence from traversal. The rule-level copy remains
        # optional only so historical 0.4 JSON continues to validate.
        sources(rule.get('evidence', []))
        text = rule['text'].strip('。；;，, ')
        if text in texts: raise ValueError('duplicate Rule text')
        texts.add(text)
        if len({rule[k].strip() for k in ('score0', 'score1', 'score2')}) != 3: raise ValueError('rubrics must differ')
        deps = rule['dependsOn']
        if len(deps) != len(set(deps)) or not set(deps) <= rules.keys() or rule['id'] in deps: raise ValueError('invalid dependency')
    def visit(rid, chain):
        if rid in chain: raise ValueError('cyclic Rule dependencies')
        for dep in rules[rid]['dependsOn']: visit(dep, chain | {rid})
    for rid in rules: visit(rid, set())
    mapped = set()
    for mapping in spec['promptRuleMap']:
        if not set(mapping['ruleIds']) <= rules.keys() or len(mapping['ruleIds']) != len(set(mapping['ruleIds'])): raise ValueError('invalid Prompt mapping')
        if mapping['sentence'] not in spec['seedreamPrompt']: raise ValueError('mapping text is absent from Prompt')
        mapped.update(mapping['ruleIds'])
    if ready(spec):
        if not rules or not spec['seedreamPrompt'].strip(): raise ValueError('ready DEFINE requires Rules and Prompt')
        if {r['id'] for r in rules.values() if r['implementation']['method'] == 'PROMPT'} - mapped:
            raise ValueError('explicit Prompt implementation missing mapping')
        for field, counts, runs in [('fitTestPlan', {'P0':4,'P1':2,'P2':2}, 1), ('tuneTestPlan', {'P0':6,'P1':4,'P2':2}, 3)]:
            found = {k:0 for k in counts}; seen=set()
            for row in spec[field]['rows']:
                found[row['tier']] += 1
                if row['testId'] in seen: raise ValueError('duplicate test ID')
                seen.add(row['testId'])
                if row['inputCount'] != 1 or row['runsPerInput'] != runs or row['totalOutputs'] != runs: raise ValueError('existing test run counts preserved')
            if found != counts: raise ValueError('existing FIT/TUNE count convention preserved')
    return spec


def esc(x): return html.escape(str(x), quote=True)
def para(text): return '<p>'+esc(text)+'</p>'
def bullets(items): return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in items)+'</ul>'
def section(title, body): return '<div class="page"><h1>'+esc(title)+'</h1>'+body+'</div>'


def related_checks(spec, rid):
    return [row['checkId'] for row in spec['traversal'] if any(rid in f['ruleIds'] for f in row['findings'])]


def related_sources(spec, rid):
    """Return each retained source once, derived from the traversal fact source."""
    found=[]; seen=set()
    for row in spec['traversal']:
        for finding in row['findings']:
            if rid not in finding['ruleIds'] or finding['decision'] not in ('RULE','EVIDENCE'):
                continue
            for source in finding['sources']:
                key=(source['sourceId'],source['location'],source['claim'],source['kind'])
                if key not in seen: seen.add(key); found.append(source)
    return found


def coverage_body(spec):
    recorded={r['checkId'] for r in spec['traversal'] if r['findings']}
    return bullets([g['id']+' '+g['name']+'：'+str(sum(c['id'] in recorded for c in g['checks']))+'/'+str(len(g['checks'])) for g in GROUPS.values()])+para('覆盖含舍弃、不适用与无法判断；不等于每项都有 Rule 或判断已验证。')


def alignment_body(spec, uris):
    goal=spec['goal']
    pics=''.join('<figure class="reference"><img src="'+u+'"><figcaption>'+esc(r['id']+' '+r['caption'])+'</figcaption></figure>' for r,u in zip(spec['references'],uris))
    body=para(spec['targetVisual'])+para('状态：'+('可交付 DEFINE' if ready(spec) else '等待 UX 确认或解决目标问题'))
    body+='<h2>实际遍历覆盖</h2>'+coverage_body(spec)
    body+='<h2>必须保留</h2>'+bullets(goal['mustPreserve'])+'<h2>允许变化</h2>'+bullets(goal['allowedVariation'])
    body+='<h2>使用范围</h2>'+para(goal['scope'])+'<h2>待确认</h2>'+bullets(goal['questions'])
    pending=[f['observation']+'：'+f['reason'] for row in spec['traversal'] for f in row['findings'] if f['decision']=='PENDING_UX']
    body+=bullets(pending)+para('确认依据：'+(goal['uxConfirmation'] or '尚无真实确认'))
    body+='<div class="references" style="--ref-count:3">'+pics+'</div>'
    return section(spec['templateName']+' · 目标与参考图', body)


def definition_body(spec, uris, final_define=False):
    from build_report import score_sheet, blank_stage_sheet
    pages=[alignment_body(spec, uris)]
    for rule in sorted(spec['rules'], key=lambda r: r['category']):
        body=para(rule['category']+' '+GROUPS[rule['category']]['name']+' · '+rule['priority'])+para(rule['text'])
        body+=para('关联遍历项：'+'；'.join(cid+' '+CHECKS[cid] for cid in related_checks(spec,rule['id'])))
        for label,key in [('保留理由','retentionReason'),('优先级理由','priorityReason'),('检查范围','checkScope'),('允许变化','allowedVariation')]:
            body+='<h2>'+label+'</h2>'+para(rule[key])
        body+='<h2>必要条件</h2>'+bullets(rule['necessaryConditions'])+'<h2>辅助证据（不独立计分）</h2>'+bullets(rule['supportingCues'])
        body+='<h2>参考依据</h2>'+bullets([f"{x['sourceId']} / {x['location']} / {x['kind']}：{x['claim']}" for x in related_sources(spec,rule['id'])])
        for label,key in [('2 分','score2'),('1 分：MUST 的最低合格','score1'),('0 分','score0'),('无法判断','unobservableWhen'),('不适用','notApplicableWhen')]:body+=para(label+'：'+rule[key])
        body+=para('依赖：'+(', '.join(rule['dependsOn']) or '无')+'；不重复计分')
        body+=para('实现方式：'+rule['implementation']['method']+'；'+rule['implementation']['detail'])
        pages.append(section(rule['id']+' · '+rule['name'],body))
    pages.append(section('规则评分表',score_sheet(spec['rules'])+para('无法判断写 U 并暂停该项汇总，补证据后再计分；不适用写 N/A。整体方向偏离另记，不能用总分掩盖。')))
    guide=spec['promptGuideReview']
    body=para('Prompt '+spec['promptVersion'])+para(spec['seedreamPrompt'])+'<h2>Prompt 与 Rule 对应</h2>'
    body+=bullets([x['sentence']+' → '+', '.join(x['ruleIds']) for x in spec['promptRuleMap']])
    body+='<h2>指南与模型</h2>'+para(guide['targetModel']+' / '+guide['sourceStatus'])+para(guide['reviewNote'])
    body+='<p>每次修改 Prompt 均应用随包 <a href="seedream-prompt-guide.md">Seedream Skill 内置结构化指南</a>，按任务选择模块和 S01-S12 要点；无需访问网页。测试人员可以自主调优；表达与映射不是生图成功证明。</p>'
    pages.append(section('初版 Prompt 与调优依据', body))
    for field,stage,runs in [('fitTestPlan','FIT',1),('tuneTestPlan','TUNE',3)]:
        body=para(spec[field]['summary'])+bullets([f"{r['testId']} / {r['tier']} / {r['inputDescription']} / {r['challengeVariable']} / {r['runsPerInput']} 次" for r in spec[field]['rows']])
        body+='<h2>初始适用性（尚未验证）</h2>'+bullets([tier+'：'+x['description']+'；'+x['rationale'] for tier in ('p0Advantage','p1Supported','p2BoundaryNotRecommended') for x in spec['initialApplicability'][tier]])
        pages.append(section(stage+' 测试计划',body))
        pages.append(blank_stage_sheet(spec['rules'],stage,runs).replace('不适用写 N/A','无法判断写 U，补证据后再汇总；不适用写 N/A'))
    return ''.join(pages)


def audit_body(spec):
    pages=[]
    for group in GROUPS.values():
        body=''
        for row in spec['traversal']:
            if row['checkId'].startswith(group['id']+'.'):
                body+='<h2>'+esc(row['checkId']+' '+CHECKS[row['checkId']])+'</h2>'
                for f in row['findings']:
                    body+=para(f['decision']+' / '+(', '.join(f['ruleIds']) or '无独立规则')+'：'+f['observation'])+para('理由：'+f['reason'])
                    body+=bullets([s['sourceId']+' / '+s['location']+' / '+s['kind']+'：'+s['claim'] for s in f['sources']])
        pages.append(section(group['name']+' · 遍历审计',body))
    return ''.join(pages)


def consistency_passed(spec):
    review=spec['reviewReport']
    if review.get('ruleEvidence'):
        return definition_assessment(spec)['definable']
    # Historical reviewReport compatibility only.
    rows=review.get('consistency',[])
    return bool(rows) and any(x.get('essential') for x in rows) and all(not x.get('essential') or all(e['score']==2 for e in x['evidence']) for x in rows)


def validate_review(spec):
    r=spec['reviewReport']; ids={x['id'] for x in spec['rules']}; refs={x['id'] for x in spec['references']}
    if r['ruleStatus']=='CONFIRMED' and (not r['uxConfirmation'].strip() or r['pendingRuleIds']): raise ValueError('Rules confirmation requires actual confirmation and no pending Rules')
    if r['ruleStatus']=='DRAFT' and r['uxConfirmation']: raise ValueError('draft Rules must not claim confirmation')
    if not set(r['pendingRuleIds'])<=ids: raise ValueError('unknown pending Rule')
    # Historical field only. New v2 work computes the conclusion and does not
    # store a second manual consistency verdict.
    rc=r.get('referenceConsistency')
    if rc:
        for conflict in rc['conflicts']:
            if conflict['checkId'] not in CHECKS or not set(conflict['referenceIds'])<=refs: raise ValueError('invalid reference consistency record')
    for row in r['ruleEvidence']:
        if not row['checkIds'] or not set(row['checkIds'])<=set(CHECKS) or not row['ruleIds'] or not set(row['ruleIds'])<=ids: raise ValueError('invalid Rule evidence mapping')
        if {e['refId'] for e in row['evidence']}!=refs or len(row['evidence'])!=len(refs): raise ValueError('Rule evidence requires every reference')
    for row in r['variations']:
        if not row['checkIds'] or not set(row['checkIds'])<=set(CHECKS): raise ValueError('unknown variation check')
    tiers=r['testMaterials']
    if len(tiers)!=3 or {x['tier'] for x in tiers}!={'P0','P1','P2'}: raise ValueError('test tiers must cover P0-P2')
    if any(len(x['items'])!=({'P0':6,'P1':6,'P2':4}[x['tier']]) for x in tiers): raise ValueError('test materials must be 6/6/4')


def check_disposition(spec, row):
    rules={r['id']:r for r in spec['rules']}; pending=set(spec['reviewReport']['pendingRuleIds']); states=set(); unknown=False
    for f in row['findings']:
        if f['decision']=='PENDING_UX': states.add('PENDING')
        elif f['decision']=='UNOBSERVABLE': pass
        elif f['decision']=='OMIT': states.add('EXCLUDE')
        elif f['decision']=='NOT_APPLICABLE': states.add('NOT_APPLICABLE')
        for rid in f['ruleIds']: states.add('PENDING' if rid in pending else rules[rid]['priority'])
    return [x for x in ('MUST','PREFERRED','PENDING','EXCLUDE','NOT_APPLICABLE') if x in states],unknown


def definition_assessment(spec):
    """Quantified, visible draft test for whether references can define one template."""
    counts={x:0.0 for x in ('MUST','PREFERRED','PENDING','EXCLUDE','NOT_APPLICABLE')}
    for row in spec['traversal']:
        states,_=check_disposition(spec,row)
        if states:
            weight=1.0/len(states)
            for state in states: counts[state]+=weight
    denominator=sum(counts[x] for x in ('MUST','PREFERRED','PENDING','EXCLUDE'))
    convergence=(counts['MUST']+counts['PREFERRED'])/denominator if denominator else 0.0

    rules={r['id']:r for r in spec['rules']}; refs={r['id'] for r in spec['references']}
    evidence_by_rule={rid:{} for rid in rules}; checks_by_rule={rid:set() for rid in rules}
    for record in spec['reviewReport'].get('ruleEvidence',[]):
        for rid in record['ruleIds']:
            checks_by_rule[rid].update(record['checkIds'])
            for item in record['evidence']:
                if item.get('observable',True):
                    evidence_by_rule[rid][item['refId']]=max(item['score'],evidence_by_rule[rid].get(item['refId'],-1))
    qualified=[]; support={}
    for rid,rule in rules.items():
        scores=evidence_by_rule[rid]; observable=len(scores); supported=sum(score==2 for score in scores.values()); ratio=supported/observable if observable else 0.0
        minimum=3 if rule['priority']=='MUST' else 2; threshold=.8 if rule['priority']=='MUST' else .5
        ok=observable>=minimum and ratio>=threshold
        support[rid]={'observable':observable,'supported':supported,'ratio':ratio,'qualified':ok}
        if ok: qualified.append(rid)
    qualified_must=[rid for rid in qualified if rules[rid]['priority']=='MUST']
    covered={check.split('.')[0] for rid in qualified_must for check in checks_by_rule[rid]}
    rule_set_ok=4<=len(qualified)<=12 and len(qualified_must)>=3 and {'C2','C3'}<=covered
    definable=rule_set_ok and convergence>=.4
    convergence_label='明确收敛' if convergence>=.6 else ('基本收敛' if convergence>=.4 else '方向分散')
    return {'definable':definable,'ruleSetPassed':rule_set_ok,'qualifiedRuleIds':qualified,'support':support,
            'convergence':convergence,'convergenceLabel':convergence_label,'counts':counts}
