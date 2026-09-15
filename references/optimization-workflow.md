> 新 reviewReport.version=2 案例优先遵循 review-output-v2.md。旧数字FIT/TUNE自动化不适用于二元MUST，不作隐式换算；规则确认后收集测试材料与判断。

# Seedream Template Optimization Workflow

Use this guide after DEFINE or for an existing template project the user has selected. Structured JSON is authoritative; HTML, PDF, and Prompt text are rebuildable. Follow python3 scripts/detect_stage.py <case-directory> and its earliest unmet dependency.

Default invocation starts a new template DEFINE and must not trigger workspace discovery. Only search for existing template projects when the user explicitly asks to find or continue one. Discovery is not selection: it may return candidate names or paths only; do not inspect candidate contents or run detect_stage.py, even when exactly one is found. Once the user selects a project, keep using it for the current workflow without repeatedly asking. In user-facing Chinese say “模板” or “模板项目,” not “case”; case directory remains an internal filesystem term.

## Prompt guidance across stages

Use the bundled structured knowledge offline. Select task modules and S01–S12 techniques; a web visit is not a stage prerequisite. Unknown version-specific capabilities remain unverified unless the user requests a knowledge update.

Read and apply [seedream-prompt-guide.md](seedream-prompt-guide.md) when proposing or reviewing Rules and before creating, revising, or reviewing any Prompt, including FIT suggestions, Final DEFINE, TUNE, and final patches. An unchanged guide already loaded in the current context need not be reread; resumed work must load it when absent from context. Include its link and relevant guidance in tester handoffs. Testers may independently tune Prompts; AI review applies the guide without silently changing tester-authored text. The guide informs expression, not template intent, priority, or acceptance thresholds. Preserve the prohibition on tuning after CALIBRATE begins.

## Preserved case structure and evidence

Use ordered stage directories for new or explicitly migrated runs: `0.reference/`, `1.define/`, `2.fit/`, `3.tune/`, `4.calibrate/`, and `5.release/`. Continue reading legacy `references/`, `define/`, `fit/`, `tune/`, `calibrate/`, and `release/` names when encountered. Existing Revision A/B and Final Patch folders remain valid; tester-authored Prompt versions are metadata and do not require a directory migration.

Each test batch preserves lineage ID, DEFINE spec SHA-256, model, fixed-set ID, Prompt artifact/hash, case IDs, applicability tiers, input text/hashes, and stable output IDs/hashes. Mark a batch ready only after user confirmation. Every functional Prompt revision uses the identical formal set. A changed Template Description or MUST Rule starts a new lineage and returns to FIT.

New DEFINE artifacts use `prompt-0.0.txt`; accept legacy `prompt-v01.txt`, `prompt-1.0.txt`, and `prompt.txt` when reading older projects. Formal UX/tester handoffs are PDFs generated from JSON through the existing builders.

## DEFINE version routing

For new specVersion 0.4, follow [define-rules-v2.md](define-rules-v2.md) and the fixed traversal catalog. Five groups contain independent R Rules; there are no mandatory six V Rules or six-dimension numeric alignment gates. Actual target confirmation and resolved questions gate the formal handoff. Apply the unchanged test budgets and tester-led later stages below. For v0.4, every mention of T/V Rules below means the existing independent R Rules; add R IDs, never manufacture new T/V Rules. Use the v0.4 schema when rebuilding Final DEFINE. Structural validation cannot prove visual or semantic correctness.

The following DEFINE v0.3 subsection is historical compatibility guidance only. Its six-Rule count, category names and 80-point alignment thresholds do not apply to v0.4.

## Historical DEFINE v0.3

Require Usage Scenario and prefer an explicit runtime input. Alignment remains one object with two gates:

- Visual Alignment: anchored 0–4 scoring for V01 Subject Treatment, V02 Composition & Layout, V03 Material & Visual Texture, V04 Color & Lighting, V05 Graphics & Typography, and V06 Realism. Total is their average after conversion to 0/25/50/75/100.
- Intent Alignment: anchored 0–4 internal checks for Input Match, Transformation Match, and Output Match. The PDF shows its total and concise reason; failures also show original UX text, runtime input, and conflicting references/patterns.

Both totals must be at least 80 and neither may have a severe conflict. Otherwise stop before Template Definition and Prompt.

On pass, define a minimal Template Description, one Hero Reference, an audited Candidate T Rule search, 0–N retained T Rules, fixed V01–V06 Visual Quality Rules, MUST/PREFERRED, concise 2/1/0 rubrics, Initial Applicability, separate FIT and TUNE Test Plans, Prompt v0.0, and sentence-to-Rule mapping. The Rule Quality Gate rejects both over-definition and under-definition; the target is minimum but complete. Rebuild Prompt/mapping after every Rule change. Do not create a separate registry.

FIT and TUNE plans have different jobs. FIT normally uses eight distinct inputs (P0/P1/P2 = 4/2/2) with one run each to test breadth. After Rule Freeze, TUNE normally uses a fixed twelve-input set (6/4/2) with three runs per input to compare Prompt versions, test repeat stability, and detect regression. Adapt counts when the template genuinely requires it and explain the deviation; never silently reuse one plan for both stages. The Definition handoff contains one blank FIT score sheet and one blank TUNE score sheet only, each with a writable `Prompt v____` title field; it never repeats a sheet for each group of Test IDs.

## FIT: Rule scoring first

Judge every `Test Output × Rule` with the frozen rubric. MUST is pass/fail. PREFERRED is 2/1/0 for met, partly met, and not met. Rules are universal across the supported inputs; input conditions and difficulty belong to the A/B/C material definition. Obtain additional evidence before finalizing any judgment that cannot be seen reliably.

For each PREFERRED Rule:

`Rule Score = actual points / (applicable outputs × 2) × 100`

Keep the legacy weighted Overall Score for continuity, with weights MUST = 3 and PREFERRED = 1. Do not use that average to decide whether a MUST result passed.

`Overall Score = weighted actual points / weighted maximum points × 100`

For MUST, every applicable `Test Output × Rule` score is a binary pass decision: `0 = 未通过`; `1 or 2 = 通过`. Report each MUST Rule as the counts of 0/1/2 and its pass count over applicable outputs. Report the top-level MUST metric as total passed MUST judgments / total applicable MUST judgments, not an average point score. Builder validation recomputes all values and enforces:

- Overall Score ≥ 80
- MUST overall pass rate ≥ 60%
- Every individual MUST Rule pass rate ≥ 70%

`GO` means every hard gate passes. `CONDITIONAL` may enter one concentrated tuning cycle only when evidence is promising but not all thresholds pass. `STOP` means failures undermine template validity or have low Prompt fixability. Status and recommended actions must agree with computed gates.

Keep capability signals and Failure Diagnosis as supporting evidence. Every Failure Diagnosis must retain affected Test IDs and Output IDs in authoritative JSON, but the PDF shows only `问题图片：<Test IDs>`; do not repeat input/output labels or expose Output IDs in the diagnosis card. Render severity as `影响程度：高/中/低` and Prompt fixability as `Prompt 可修复性：高/中/低`; never show unlabeled `High/Medium/Low` pills. The FIT PDF starts with the summary, then adds an Input/Output evidence appendix ordered P0 → P1 → P2 and Test ID ascending. Make appendix comparison frames approximately twice the former compact height and paginate at exactly three Input/Output pairs per full appendix page. The final appendix page may contain fewer pairs only when the total is not divisible by three. A failure either explains a low T/V Rule or proposes Candidate Rule `N01…` when stable, generalizable, valuable, measurable, and uncovered. Candidate Rules require UX decision Accept, Merge, or Reject. Accepted candidates receive a T ID or merge into an existing Rule; N IDs never become truth automatically.

In the FIT summary header only, use the eyebrow `规则评分 RULE SCORING` without naming FIT or TUNE. Show the Prompt version as a prominent pill immediately beside the template title, formatted `Prompt <version>`, and show the image-generation model as a parallel neighboring pill. Keep only the test count in the smaller subtitle. Do not apply this FIT-specific title treatment to DEFINE, TUNE, CALIBRATE, or RELEASE reports.

The FIT evidence appendix adds a `RULE 评分` column to the right of Input and Output. For each output, list every Rule as `<Rule ID> <MUST 通过/不通过>` or `<Rule ID> <PREFER 0/1/2分>`. Highlight the entire line red only when a MUST Rule fails. Preserve three Input/Output/Rule-score groups per full appendix page.

The FIT handoff must explicitly ask UX to review every Fxx as retain, merge, or remove and to add any missing observations. Require MUST or PREFERRED for every resulting Rule proposal. Explain that Fxx is a Failure Diagnosis identifier, not a frozen Rule identifier. The handoff ends with exactly three displayed lines: `UX 最终确认后，所有 Rule 才会被冻结并交付给测试人员，` / `并重新输出完整的 Final Define Report，` / `作为TUNE阶段的优化依据。` Preserve these explicit line breaks. When no Candidate Rule exists, use this handoff as the table's only body row. When candidates exist, place it below the candidate table.

Generate Suggested Tune Priority from impact, frequency, Prompt fixability, and MUST/PREFERRED. Mark at most about ten Rules with 🔥 without reordering the Rule list. Show marks on the Rule sheet and Prompt mapping.

## FIT UX Rule Review and Final DEFINE

FIT never freezes Rules automatically. After the report is delivered:

1. Ask UX to judge every Fxx and provide new suggestions; every resulting Rule proposal must say MUST or PREFERRED.
2. Record the feedback in `2.fit/ux-rule-review.json` as DRAFT. Do not treat UX wording as final Rule text.
3. Compare each item against all existing T/V Rules. A standalone issue becomes a new sequential Fxx and a Candidate T Rule only when it passes independence, generality, value, measurability, and overlap checks. If an existing T/V Rule already owns the judgment, merge and rewrite that Rule instead. Never add an F Rule to the frozen Rule Set: Fxx remains evidence.
4. Report to UX the organized Fxx list, rejected/merged suggestions, each resulting MUST/PREFERRED choice, and exact before/after changes to existing or new T/V Rules. Rebuild provisional Prompt and Prompt–Rule mapping, but do not freeze or produce the Final Define Report yet.
5. Wait for explicit UX confirmation. If UX revises the proposal, update the DRAFT and repeat the report.
6. Only after confirmation set the review to CONFIRMED, resolve all Candidate Rule decisions, write the complete updated spec to `1.define/final-template-spec.json`, rebuild Prompt/mapping and Rule Quality Gate, and generate `final-template-definition-report.html/.pdf` plus `prompt-final-define.txt`.

The review binds both the immutable pre-FIT `template-spec.json` hash and the confirmed `final-template-spec.json` hash. TUNE uses the final hash and `prompt-final-define.txt`. `detect_stage.py` must return `WAIT_UX_RULE_REVIEW`, `WAIT_UX_FINAL_CONFIRMATION`, or a Final DEFINE rebuild action until these gates are satisfied; it may return `WAIT_TUNE_BASELINE` only afterward.

Before TUNE, UX resolves every Candidate Rule and confirms priorities. Final DEFINE hash, lineage, fixed set, input/Prompt hashes freeze Template Definition, T/V Rules and rubrics, Supported Inputs, the TUNE Test Plan, scoring formula, Prompt mapping, and Tune Priority for the round.

## TUNE: tester-driven, evidence-bound

Before testing, generate the tester-facing PDF containing Template Definition, Rule scoring sheet, Test Plan, current Prompt/mapping, real FIT baseline, Tune Priority, and a blank Tune score sheet.

The tester may write every Prompt revision. Each revision records:

- Prompt version (`1.1`, `1.2`, `2.0`, and so on)
- Target Rules
- one-sentence Revision Hypothesis
- full Prompt text
- optional concrete change notes

The rule-oriented Change Log maps changes to T/V Rule IDs. Preserve the existing 2 + 1 functional revision budget as the default safety envelope: two consolidated revisions and one optional near-release patch. Legacy Revision A/B labels remain compatible storage aliases.

Each version uses the same fixed set and rubrics. Compare all Rules and retain complete score sheets. Mark each tracked Rule `SOLVED`, `IMPROVED`, `UNCHANGED`, `REGRESSED`, or `MODEL-LIMITED`; an improved average never hides a regression.

The final Tune Review PDF contains:

1. Tune Summary with initial/final Prompt; Overall, MUST, PREFERRED, and Tune Priority before→after; gate; solved issues, remaining issues, and regressions.
2. Complete Score Comparison for every frozen Rule plus all version score sheets.
3. Prompt Change Review for every 🔥 Rule, including explicit “未发现针对该 Rule 的 Prompt 调整” when applicable.
4. Complete evidence appendix: inputs and baseline, major revision, and final outputs keyed by stable case/output IDs. Body images focus on severe lows, regression, and MODEL-LIMITED evidence.

After tester handoff, agent review checks Prompt-to-Rule traceability, suspicious score jumps without relevant Prompt changes, cross-Rule regressions, unreported failures, and unsupported new Prompt constraints. New findings remain evidence or Candidate Rules; never silently rewrite the frozen benchmark.

## CALIBRATE and RELEASE

Do not tune after CALIBRATE begins. Reconcile the initial hypothesis with observed capability:

- `KEEP`: retain a MUST Rule.
- `RELAX`: only a PREFERRED Rule, with Before, After, and Why.
- `NARROW APPLICABILITY`: replace Initial with evidence-backed Validated Applicability.
- `STOP`: a MUST Rule with low controllability prevents the intended experience.

Preserve P0/P1/P2 separately. Release status remains PASS, CONDITIONAL PASS, or FAIL; Template Identity or MUST gate failure forces FAIL. Keep legacy final-spec fields readable during migration and do not unrelatedly redesign CALIBRATE/RELEASE.

## Stopping and deliverable rules

- A report alone never proves its JSON exists.
- Rebuild missing HTML/PDF/TXT from valid JSON rather than rerunning analysis.
- Prompt text must exactly match authoritative JSON and manifest hash.
- Required PDF content must be directly visible; do not rely on hover, expansion, clicks, or copy buttons.
- User-visible labels are Chinese-first. Keep useful terms such as DEFINE, FIT, TUNE, MUST, PREFERRED, Prompt, Rule, P0/P1/P2, and MODEL-LIMITED.
- Separate observed evidence, inference, and UX judgment; do not claim scientific measurement.
- At each Seedream-generation pause, request only the current materials and destination.
