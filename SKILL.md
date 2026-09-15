---
name: seedream-template-spec-v2-1
description: Define, test, tune, calibrate, and release a rule-driven local Seedream image template from 3–6 UX-selected golden references and staged user-supplied Seedream outputs. Use for a new template direction or an existing local case; do not use it to generate images or search for references.
---

# Seedream Template Spec 2.1

Help UX answer five questions: what the template should be, whether Seedream can do it, what currently fails, what is worth tuning versus calibrating, and whether the result is ready for users. Preserve DEFINE; continue through FIT, TUNE, CALIBRATE, and RELEASE only as evidence becomes available.

## Seedream Prompt guide: required throughout the workflow

The bundled guide at `references/seedream-prompt-guide.md` is the operational knowledge source and travels with the Skill: use its structured task modules, S01–S12 techniques, and revision checklist. Routine DEFINE/tuning never requires browsing the official page or reading a machine-global file. Consult the web only for an explicitly requested knowledge/version update. Record the packaged knowledge version and applied modules/techniques in promptGuideReview.reviewNote.

Read and apply [references/seedream-prompt-guide.md](references/seedream-prompt-guide.md) when drafting or reviewing candidate Rules and before writing, revising, or reviewing any Prompt. This includes provisional DEFINE drafts, Rule Quality Gate retries, FIT recommendations, Final DEFINE recompilation, TUNE revisions, and final patches. Reuse an already-loaded unchanged guide in the current context; load it again when resuming without that context or when the guide changes.

Use the guide to assess how a requirement can be expressed for the target Seedream version. It does not establish template intent, justify extra Rules, set MUST/PREFERRED, or prove generation success. Preserve requirements that lack a proven expression and identify them for testing rather than weakening them to fit convenient wording.

Testers remain responsible for running and tuning Prompts. Include the guide link and the relevant guidance in tester handoffs; when a tester supplies a revision, apply the guide during review without silently rewriting their Prompt or requiring AI approval for each experiment. Byte-identical artifact export is not a Prompt revision. This requirement does not reopen tuning after CALIBRATE.

## Start naturally

Unless the user explicitly asks to continue an existing template project, supplies its directory, or the current conversation already has one established, default to a new template and begin DEFINE. Do not scan the workspace for existing projects, list candidate directories, ask the user to choose between “new” and “existing,” or announce that the Skill was triggered.

Ask only for missing UX inputs, in natural Chinese. When none have been supplied, use this shape:

> 我们来做一个新模板。先把这几样给我就行：
>
> - 模板名称
> - 使用场景：用户从哪里进入、为什么会用、希望得到什么结果
> - 运行时输入：文本、单张图片，还是多张图片
> - 3–6 张黄金参考图，推荐 4–5 张
>
> 可以一次发完，也可以先发参考图，我会帮你整理。

Do not say “case” to UX. Use “模板” or “模板项目” in user-facing Chinese; reserve case directory for internal filesystem instructions.

## Runtime storage boundary

Treat the installed Skill directory as read-only package code. Never write reference images, template JSON, Prompts, reports, caches, indexes, or user project state into the Skill root, its bundled `cases/`, `references/`, `scripts/`, or `schemas/` directories.

For an ordinary new template, use a project path supplied by the user. If none is supplied, create the project under the current working workspace at `seedream-template-projects/<template-slug>/run-001/`. Continue all later stages in that same run. Do not redirect ordinary work to a machine-global or Skill-relative corpus. If the current workspace is disposable, that is still the active task location unless the user asks for a persistent destination.

## DEFINE collaboration loop

Read [references/ux-define-quick-start.md](references/ux-define-quick-start.md) when explaining the workflow to UX. Treat DEFINE as one review loop with two named deliverables: `模板定义` for UX and `测试指南` for testers. Use these names consistently in user-facing messages:

1. Collect the template name, intended use, accepted input, 3–6 golden references, and any known non-negotiable or allowed changes. Organize incomplete input instead of demanding a form.
2. Review the UX brief semantically before drafting. A slogan such as “一键进入动漫世界” does not specify a visible result: ask UX what concrete transformation and output they mean, store the question in `goal.questions`, and stop before Rules, Prompt, and PDF generation. Never copy product-facing benefit language into the Prompt.
3. Analyze the references and all 29 Criteria, draft no more than 12 Rules, map them to an initial Prompt, and generate the first version of `模板定义` as `<模板名>_模板定义_to UX_v1.pdf`.
4. Tell UX what the draft contains, what changed or remains uncertain, which yellow rows require a decision, and that only the pages explicitly labeled REFERENCE are appendices for UX context.
5. Apply feedback to the authoritative JSON, Rules, levels, Prompt, scorecard, and material coverage together. Generate v2, v3, and later `模板定义` PDFs as needed; never patch only the visible PDF or silently discard earlier decisions.
6. Continue until UX explicitly says the definition is ready for testing. Resolve every yellow item before handoff. Then generate `测试指南` as `<模板名>_测试指南_to 测试.pdf`; this is the only DEFINE PDF sent to testers.

For every UX review revision, summarize the revision number, material changes, remaining decisions, and the single next action. Ask UX to review the whole document and answer yellow items first; yellow marks priority, not the only content requiring review. Do not treat silence, a general positive reaction, or approval of the visual direction as approval of every Rule and level.

## Continue an existing template project

Treat an existing template project as selected only when the user explicitly names or supplies its path, or when the current conversation has already established one unambiguous active project. Do not discover or scan for projects merely because the Skill was invoked. If the user explicitly asks to find existing projects, discovery may identify candidates, but do not open their contents, run the detector, or continue one until the user selects it. Do not choose by recency, completeness, folder name, or apparent relevance.

For a user-selected existing template project, first read [references/optimization-workflow.md](references/optimization-workflow.md) and run:

```bash
python3 scripts/detect_stage.py <case-directory>
```

Follow the earliest unmet dependency and the single reported action. Do not ask the user to select a mode, skip an invalid earlier stage, or infer that a report alone proves its JSON analysis exists. At every Seedream-generation pause, tell the user only which current materials to supply and where to place them.

## DEFINE: 2.1 contract (specVersion 0.4)

For new DEFINE work, read [references/define-rules-v2.md](references/define-rules-v2.md), [references/review-output-v2.md](references/review-output-v2.md), [references/traversal-v2.json](references/traversal-v2.json), and the Prompt guide. These files own the detailed Criteria, Rule thresholds, report layout, scoring, and A/B/C material rules; do not restate or invent parallel versions.

### Fast preflight

Before writing the complete spec or making a PDF, inspect all references once and make a compact working pass:

1. Assign one short disposition to each of the 29 Criteria. Do not write report prose or full Rule cards yet.
2. Draft candidate Rules, merge rules that test the same property, and record only the per-reference support scores needed by the quantitative test.
3. Compute the effective Rule Set and Criteria convergence with `definition_assessment`.
4. If the references are not `可定义`, stop before Prompt, scorecards, material lists, and PDF generation. Report the numbers and the smallest reference change needed.
5. If they are `可定义`, reuse the same observations to finish the authoritative JSON. Do not analyze the images a second time.

Preflight is an internal working pass, not another persisted artifact or user deliverable. It may be summarized in chat when the references fail. A passing preflight proceeds directly to the first `模板定义`.

### One source for each fact

Write each fact once in new 2.1 JSON:

- `traversal.findings` owns Criteria disposition, source location, rationale, and Rule links.
- `rules` owns the requirement, priority, rubric, scope, and implementation. Do not write `rules[].evidence`; derive source evidence from linked traversal findings.
- `reviewReport.ruleEvidence` owns only the per-reference observable/support matrix used by the quantitative assessment. It may group Rules only when they share the same actual evidence.
- `referenceConsistency` is legacy-only. Do not write it in new cases. The conclusion, counts, support rates, qualified Rules, and Criteria links are computed.

Do not copy derived values into summaries or JSON fields. Reports and chat summaries must call the shared calculation functions. Preserve old fields when reading historical cases, but never add them to a new case.

### Formal DEFINE

After preflight passes, complete the 29 findings, no more than 12 independently scoreable Rules, Prompt mapping, scorecards, and 6/6/4 A/B/C material suggestions. Keep `targetVisual`, `inputSummary`, and `usageScenario` short and non-overlapping. Yellow means only `PENDING_UX`; unresolved target questions or pending findings block the tester handoff. The initial Prompt remains an untested implementation hypothesis.

Keep 7–10 top-level Rules when that covers the independently meaningful failure modes; 12 remains the ordinary maximum because testers must score every Rule repeatedly. Do not merge independent Rules merely to fit a report page. Preserve rich implementation detail inside each Rule's `necessaryConditions` and `supportingCues`: those details may all appear in the Prompt and map back to the same Rule without becoming separately scored PREFERRED Rules. A PREFERRED Rule is warranted only when its failure remains usable and testers benefit from evaluating or tuning it independently.

Keep test material suggestions limited to a material subject and observable input traits. Do not put Rule IDs, scoring instructions, Prompt edits, UX decisions, or generation constraints into material items; place those in the Rule set, scorecard, or Prompt instead.

On the test-material page, place the small gray note `以下为测试材料建议，供测试人员参考，不必严格执行` to the right of the main title.

In every PDF Prompt-to-Rules mapping, render Prompt and Rules as independent text regions and emit the full Prompt region first. Copying the Prompt column must return continuous Prompt text without interleaved Rule IDs; keep the plain-text Prompt artifact as the canonical copyable version.

In UX template-definition PDFs, append `请 UX 逐项查对、修正或补充` to every gray `DEFINE` eyebrow.

Generate the current deliverable directly from the authoritative JSON:

```bash
scripts/run_compact_report.sh <run>/1.define/template-spec.json --check-only
scripts/run_compact_report.sh <run>/1.define/template-spec.json --revision 1
```

Use the wrapper for ordinary DEFINE work. It prefers the Codex bundled Python runtime, verifies the required PDF libraries, discovers a usable Chinese font, accepts either `REF01.png` or `golden-reference-01.png` style filenames, and runs a fixed-page content-budget preflight before ReportLab. If the bundled runtime is not found automatically, call `load_workspace_dependencies` and pass its Python path through `CODEX_BUNDLED_PYTHON` for this command. Do not repeatedly invoke a system `python3` that is blocked by an Xcode license prompt.

Run `--check-only` before the first PDF build and after large Rule, Prompt, evidence, or material revisions. It checks schema, runtime, fonts, references, and structural material formatting. It must never impose Prompt length, sentence-count, Rule-text, evidence-row, or material-length limits. The ReportLab renderer must add pages when content grows.

By default this creates both the internal generic artifact and the correctly named UX review PDF; `--revision N` controls the visible revision suffix. Once confirmed it also creates the correctly named tester guide plus required audit/prompt support files. It does not generate FIT/TUNE example PDFs. Use `--include-examples` only when UX explicitly asks to inspect those formats. Do not run `build_report.py` before `compact_report.py` for a new reviewReport case; it is retained for historical formats.

Rules grounded in an explicit UX runtime or usage requirement may remain in `rules` and traversal even when the Golden References cannot visually demonstrate them. Record the UX source with `RUNTIME`, `USAGE`, or `GOAL`; omit that Rule from `reviewReport.ruleEvidence` until there is observable image support. The report will show the Rule as lacking independent image evidence and the quantitative assessment will not count it as qualified. This is not a builder defect and is not a reason to delete, weaken, or fabricate support for the requirement.

Content precedes presentation. Finish the best Prompt supported by the Rules and the bundled Prompt guide before adapting the report. Every visual or behavioral Prompt clause must map to at least one Rule; several clauses may map to the same Rule's necessary conditions or supporting cues. Pure execution syntax may map to an existing input/output Rule or be recorded as CONFIG. Do not add ungrounded aesthetic instructions. Before and after PDF generation, verify that the canonical `seedreamPrompt` and exported Prompt text are byte-identical; layout work may paginate or move content but must never shorten, merge, paraphrase, or otherwise revise the Prompt.

The Prompt is an execution specification, not a restatement of `usageScenario`. Its opening sentence must state a concrete transformation, input subject, output visual form, and the most important preservation target. Reject vague or user-facing phrases such as `让用户进入…世界`, `一键`, or `沉浸式体验`; if those phrases are the only available intent, return to UX clarification before authoring any Prompt.

Use these deliverable names in user-facing messages:

- Draft/revision: `<模板名>_模板定义_to UX_vN.pdf`
- After explicit confirmation: `<模板名>_测试指南_to 测试.pdf`

Validate with `python3 scripts/test_define_v04.py`, `python3 scripts/test_compact_review.py`, and `python3 scripts/test_rule_quality.py`. Structural tests do not prove semantic correctness or Seedream performance.

## FIT, TUNE, CALIBRATE, RELEASE

For historical non-reviewReport cases, apply [references/optimization-workflow.md](references/optimization-workflow.md) exactly for rule scoring and hard gates, Candidate Rules, tester-driven tuning, manifest hashes, fixed-set comparison, regression tracking, calibration actions, and release gates.

Use these schemas as the JSON contracts:

- Test evidence: [schemas/test-batch.schema.json](schemas/test-batch.schema.json)
- FIT: [schemas/fit-analysis.schema.json](schemas/fit-analysis.schema.json)
- TUNE rounds: [schemas/tuning-analysis.schema.json](schemas/tuning-analysis.schema.json)
- CALIBRATE + RELEASE: [schemas/final-template-spec.schema.json](schemas/final-template-spec.schema.json)

Build stage deliverables from authoritative JSON:

```bash
python3 scripts/build_stage_report.py <fit-analysis.json> \
  --output-dir <case>/2.fit --batch <case>/2.fit/tests/batch.json
python3 scripts/build_stage_report.py <analysis.json> --output-dir <stage-directory>
python3 scripts/build_stage_report.py <final-template-spec.json> \
  --output-dir <case>/5.release \
  --reference <image-1> --reference <image-2> --reference <image-3>
node scripts/export_pdf.js <case>/5.release/release-package.html \
  --output <case>/5.release/release-package.pdf
```

After FIT, do not route directly to TUNE. Ask UX to decide for every Fxx whether the diagnosed failure should be retained, merged, or removed, and to provide any missing suggestions. For every resulting Rule proposal, require UX to state MUST or PREFERRED. Clarify that Fxx identifies a Failure Diagnosis, not a frozen Rule ID.

Do not copy UX wording mechanically into the Rule Set. For v0.4, organize feedback against independent R Rules and their categories; for historical v0.3 retain T/V IDs: create a new Fxx plus Candidate Rule only when the issue is independently observable, generalizable, valuable, measurable, and not covered; otherwise merge the feedback into the relevant existing Rule and rewrite its rubric and Prompt mapping. First report the organized Fxx list and exact before/after Rule changes to UX. Wait for explicit final confirmation before writing the confirmed final spec, freezing Rules, or entering TUNE.

After confirmation, save `2.fit/ux-rule-review.json` against [schemas/ux-rule-review.schema.json](schemas/ux-rule-review.schema.json), write the updated complete spec to `1.define/final-template-spec.json`, and build the complete Final Define Report:

```bash
python3 scripts/build_report.py <case>/1.define/final-template-spec.json \
  --output-dir <case>/1.define --final-define \
  --reference <image-1> --reference <image-2> --reference <image-3>
node scripts/export_pdf.js <case>/1.define/final-template-definition-report.html \
  --output <case>/1.define/final-template-definition-report.pdf
```

The confirmed review records the original DEFINE hash and updated final DEFINE hash. TUNE binds to `final-template-spec.json` and `prompt-final-define.txt`; the original `template-spec.json` remains the immutable FIT baseline.

Every functional Prompt revision must be tested on the identical formal set and record Prompt version, Target Rules, Revision Hypothesis, full Prompt, and rule-oriented change log. The tester may author the Prompt. Compare case IDs, tiers, input text/hashes, fixed-set ID, Prompt artifact/hash, and all Rule scores. Do not hide regressions behind an overall average. Do not tune after CALIBRATE begins.

Use stable output IDs when one input has multiple generations. Every batch must also carry the current DEFINE spec SHA-256; changing Target Visual or a Core constraint starts a new lineage and requires a new FIT.

## Final quality check

Before reporting a stage complete, verify:

- Structured JSON passes its schema and the relevant builder validation.
- `python3 scripts/test_define_v04.py` passes v0.4 coverage, references, readiness, rendering and routing regressions; `python3 scripts/test_rule_quality.py` preserves historical checks. These tests do not prove semantic independence.
- The detector reports the expected next action.
- Prompt text exactly matches its authoritative JSON and manifest hash.
- Test evidence is complete, user-confirmed, and never represented as scientific measurement.
- HTML opens standalone; embedded images render; every formal DEFINE/FIT/TUNE handoff PDF exists and was visually inspected.
- Gate A or B failure forces Release `FAIL`; P0/P1/P2 remain separate.
- Core constraints are never weakened merely to force release; every relaxed preference records Before, After, and Why.

Keep this a local UX decision skill. Do not add a web app, database, account system, API integration, image generator, reference search, evaluation dashboard, template library, or collaboration platform.

## Testing corpus maintenance

Read [references/testing-corpus.md](references/testing-corpus.md) only when the user explicitly asks to develop or evaluate this Skill, maintain its reusable test corpus, or add a calibration case. Ordinary template creation and optimization do not use the corpus.

Treat bundled `cases/` as immutable Skill-owned regression fixtures. For an explicit corpus task, keep reusable human testing cases outside the installable Skill at `../../skill-testing/seedream-template-spec-v2-1/`, relative to this Skill root.

Within an explicitly selected corpus, a case identifies one stable template direction and each independent attempt lives under `cases/<case-slug>/run-###/`. Preserve earlier runs and update corpus indexes only as part of that explicit corpus task.

Never modify the installed Skill while executing a template. Skill source changes, fixture changes, and installation updates require an explicit Skill-development request.
