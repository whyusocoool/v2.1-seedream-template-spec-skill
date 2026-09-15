# DEFINE 审阅输出协议（2026-09-10 修订2）

DEFINE 对外固定为两类 PDF：

1. `<模板名>_模板定义_to UX_vN.pdf`：根据 UX 输入和上一轮反馈生成的完整待修订稿。v1、v2、v3依次保留评审轮次；合并 Alignment 与 Definition，供 UX 确认、讨论和修改，REFERENCE 只供 UX 理解 Rules 的制定依据。
2. `<模板名>_测试指南_to 测试.pdf`：UX 明确确认后的最终测试交付。只保留三个章节：定义、Rules、Prompt及Rules-Prompt映射；MUST/PREFER评分卡；A/B/C测试材料建议。章节可按内容自动续页，不限制总页数。删除一致性检查、Criteria-Rules图、标准遍历表，以及Rules表中的「来自遍历项」列。

新 DEFINE 必须使用 specVersion 0.4 + reviewReport.version="2"。本协议覆盖旧文档关于报告布局、初版交付门槛、MUST评分和DEFINE测试材料计划的约定。旧案例按原协议读取，不自动迁移。

## 状态与一致性

三个状态独立：模板可定义性、目标确认、Rules确认。UX同意继续DEFINE不是逐条批准候选Rules。每轮反馈必须同步更新事实源、Rules、级别、Prompt、评分卡和材料覆盖，再输出下一个 vN；不得只改PDF表面。只有 UX 明确要求“输出给测试的版本”，且规则/级别、目标和所有黄色待定项均已确认，才可生成测试交付。reviewReport.ruleStatus=DRAFT时uxConfirmation为空；有明确待决取舍时记录pendingRuleIds，不把所有普通候选都标成黄色。

模板可定义性同时检查 Rule Set 成立度和 Criteria 收敛度。有效 Rule Set 需有4–12条获得足够图片支持且可独立评分的Rules，至少3条为MUST，并由合格MUST分别覆盖C2与C3。MUST至少有3张可观察参考图支持且支持率≥80%；PREFER至少有2张可观察参考图支持且支持率≥50%。支持率只使用该特征可观察的参考图作分母。相同底层属性、仅措辞不同或评分时必然同时成败的Rules必须合并，不得靠拆分凑数。

Criteria收敛度=`(MUST+PREFER)/(MUST+PREFER+待定+不规定)`；无关不进入分母，分色项按比例计数。≥60%为明确收敛，40%–<60%为基本收敛，<40%为方向分散。有效Rule Set成立且收敛度≥40%时，结论为“可定义”。待定会降低收敛度，但不单独表示风格不稳定。29项图、公式、当前百分比、有效Rule数和Rule Set结论必须同时可见，不使用另一套隐藏冲突Gate。

## PDF和HTML固定结构

排版层级固定：页级大标题、分区标题和表头使用粗体，字号和段前后间距明显区分。普通段落和列表使用统一正文字号；表格内容使用统一表格字号。图例、方法说明、指南声明和页脚使用独立小字号与正文拉开层级。不得为填满页面随意改变同类文字大小。

需要 UX 采取行动、注意限制或理解状态的提示，应紧邻对应内容；黄色仅用于表内的待定 Rule 行。测试版不显示黄色说明框。

模板可定义性是 UX 专用 REFERENCE 页。右侧结论显示“可定义”或“待补充”。页面直接显示上述判断规则、Criteria收敛度、收敛等级、有效Rule数量和Rule Set是否成立。图例显示 MUST、PREFER、待定、不规定、无关的加权数量；分色项按比例计入各状态。

Definition首页分别显示一句话定义、Input和使用情景；右为一张典型参考图，并显示初版Rule表「Rule｜要求｜建议级别｜来自遍历项」。最后一列只显示C子项编号，不显示名称；MUST用绿色文字，PREFER用蓝色文字。UX确认/调整提示在表格之前。完整Prompt及Rules-Prompt映射从独立页面开始，并按映射段落自动续页。Prompt与Rules必须绘制为两个独立的PDF文本区域：先完整写入左侧Prompt，再写入右侧Rules；复制左栏时应得到连续且不夹杂Rule编号的Prompt正文，同时保持两栏逐行对齐。Prompt文本文件仍作为无格式复制的标准交付。
2. `Criteria-Rules映射`作为REFERENCE紧邻Prompt章节之前；其下绘制29项状态图，左侧每行为C1-C5，标记数5/7/7/5/5，图表顶部按列统一显示数字1–7。图例直接放在该图下方。Prompt映射不再与29项矩阵竞争同一页。顶部数字和左侧行名使用粗体。标记使用由指定SVG路径形成的圆润方形，内部不显示文字，尺寸为旧标记的70%。五种用户可见状态为：MUST #97C657、PREFER #84AEF9、待定 #EDD154、不重要 #C9CBD0、无关为白底灰色 #9AA0A6 虚线描边。前三种与不重要标记不描边。同子项多个去向用形状内部左右分色，禁止使用无法独立解读的外附小点。
   黄色只表示需要UX取舍的规则提议。每个黄色项必须作为Rule表内的一行，使用与普通Rule完全一致的列、字号、行高与分隔线，仅整行增加浅黄色底色。该行提出具体候选Rule，或明确提出“不保留为Rule”的处理方案，并标明来源Criteria。不得另做黄色说明块，也不得把模型生成能力、缺少输入输出对照或待生图验证标成DEFINE待定。
3. 全部Rule的简明评分卡，优先一页，先显示黑色MUST Rules标题和MUST表，再显示黑色PREFER Rules标题和PREFER表；UX审核稿和测试指南格式一致，不显示黄色提示框。Rule总数不得超过12条。两表均固定三列「Rule｜结果｜判断标准」。MUST结果列只写“通过/不通过”；PREFER结果列只写“2分/1分/0分”。每个结果及其对应标准必须独占同一水平行；结果列收窄。不通过和0分的结果与标准均为红色，1分均为橙色。FIT首页的单项Rules表现也拆成MUST Rules和PREFER Rules两表，Rule名称为黑色、表体白底；只将失败诊断中有对应测试图片的低分数字标红。失败诊断以小标题和表格放在首页底部。计算规则页使用较大表格字号；Gate表头已经说明统计对象后，单元格只写阈值或必要的人工作决策，不重复类别、MUST/PREFER名称，也不写“不作要求”。
4. 测试材料：在「测试材料建议」大标题右侧显示灰色小字`以下为测试材料建议，供测试人员参考，不必严格执行`。面向用户统一显示`A 核心场景`、`B 拓展场景`、`C 边缘场景`，每组固定显示一行「输入范围」和一张「序号｜建议素材｜输入特征」表，再给6/6/4个具体内容方向。先用输入覆盖矩阵定义三类，至少覆盖输入类型、主体数量、主体类别、背景简杂、构图、遮挡、分辨率和轮廓清晰度，再由这些维度组合材料建议。材料项只描述要找什么素材及其输入特征，不得包含Rule编号、评分检查、Prompt修改、UX决策、「不臆造」等生成约束或执行说明；这些信息分别归入评分卡、Rules或Prompt。底层P0/P1/P2仅作旧数据兼容，不在报告显示。UX版和测试版均不显示材料提示框或页尾操作说明。生成器读取旧数据时应剥离这类尾注。
5. 标准遍历表 Criteria Check List：与Alignment使用相同的四列29项表。

## 数据、脚本和评分接口

所有内容以template-spec.json为唯一事实源。traversal记录Criteria去向、来源和Rule链接；reviewReport.ruleEvidence只记录Rules的逐图可观察性与支持分；结论、计数、支持率和Criteria来源均由脚本计算。新数据不写rules[].evidence或reviewReport.referenceConsistency；这两个字段只兼容旧案例。报告内子项ID统一显示为C1-1形式，JSON保留C1.01作为内部键。promptRuleMap生成映射。不要另写仅适用于一个模板的报告生成器。

`scripts/run_compact_report.sh` 负责选择可用 Python、检查 PDF 依赖和中文字体，再调用 `compact_report.py` 生成紧凑PDF、Prompt、本地指南及遍历审计。新reviewReport案例不先运行build_report.py。先做一次完整预检，再生成：

```bash
scripts/run_compact_report.sh <run>/1.define/template-spec.json --check-only
scripts/run_compact_report.sh <run>/1.define/template-spec.json --revision 1
```

参考图可命名为`REF01.png`或`golden-reference-01.png`（也支持 jpg/jpeg/webp）。普通运行不要求复制成两套文件。若预检同时报告多个版面风险，应一次调整全部问题后再生成，避免逐页串行试错。

生成后渲染并检查每页，尤其参考图比例、圆点、Prompt续页顺序和评分卡是否溢出。对话输出用同一JSON生成，不人工重编另一套结论。报告生成前后校验Prompt文本完全一致；若内容放不下，只能续页或移动章节，禁止为版面缩写Prompt或合并独立Rules。

score0/1/2分别承载不满足、部分满足、满足描述；MUST在报告中使用score1作为通过描述、score0作为不通过描述，score2只作兼容。旧fitTestPlan/tuneTestPlan字段暂为兼容字段，新输出只用reviewReport.testMaterials，不再把旧计划作为用户任务。detect_stage在确认后返回COLLECT_TEMPLATE_TESTS，收集真实输出和证据。采用稀疏减分记录：MUST通过率按`1－不通过数/已完成MUST判断总数`计算；PREFER表现率按`1－(1分数+2×0分数)/(2×已完成PREFER判断总数)`计算。通过和2分无需逐项记录；条件未出现时不评分且不进分母；0分、1分或不通过必须保留证据图ID。真正未检查的项同样不进分母。

## 对话固定输出

DEFINE初版交付：
- 模板概览：名称、一句定义、使用情景。
- 一致性：状态、一句证据结论；覆盖数和一致性是不同指标。
- 初版Rule表：编号、简短要求、MUST/PREFER/待确认。
- UX提示：请确认或按Rule编号调整要求与级别；仅在规则尚未确认时出现。用户已确认的目标不重复询问。
- 初版Prompt：全文或可直接读取的文本文件；注明本地指南版本、未实测。
- 当前阶段只交付一份PDF：审核阶段为「模板定义」，明确确认后为「测试指南」。完整遍历与映射放报告，不在对话重复29行。

若用户仍在修改Skill，则先简报修改和验证，再展示同一结构的试跑结果。不能因为有报告就自动触发Seedream生成。
## Template summary

Write the DEFINE summary as three short, non-overlapping lines:

- `一句话定义` describes only the intended output look and its essential visual traits.
- `Input` states only the accepted input type and quantity.
- `使用情景` states when or why a user would use the template.

Keep each line independently understandable. Do not repeat the input in the output definition or restate the visual style in the usage scenario.

## Page header

Give every generated page a small gray uppercase English eyebrow above the Chinese title, such as `DEFINE`, `TEST`, `REFERENCE`, or `DEFINE REVIEW`. In every UX template-definition PDF, append `请 UX 逐项查对、修正或补充` after each `DEFINE` eyebrow. On the consistency review page, place the overall pass/fail conclusion at the upper right using the same divider, label, type scale, and status colors as the FIT report header.

Place the `一致性检查` reference page immediately before `标准遍历表 Criteria Check List`. Show the evidence-based pass/fail conclusion at upper right. Derive legend counts from the current traversal data; split-state Criteria contribute equal fractional weights to each displayed state. Do not show an `x/29` alignment statement. Present one `Rules依据` table with columns `Rules`, `效果描述`, `图片依据`, and `Criteria依据`. Use `不规定` for intentionally unconstrained items and `待定` when UX still needs to decide a Rule.

Build `Rules依据` from the complete proposed Rule Set, not only from summarized effects, so no Rule can disappear when evidence is sparse. Show a missing image or Criteria source explicitly and route that Rule to `待定`; use PREFER only when the direction has affirmative evidence but is optional. Put the counted legend directly below the page title, above the `x/29` statement and matrix.

The UX review title is always `<模板名> · 模板定义`; express revision state through the file version and pending rows. Its Rule table has only `Rule`, `要求`, and `建议级别`; do not show a general yellow instruction box or the traversal-ID column. Yellow remains reserved for pending rows. On all UX `REFERENCE` pages, append `附录仅供 UX 参考` to the small English eyebrow.

Render UX and tester material suggestions with identical heading breaks and typography. Split every A/B/C definition after its first colon; render the definition on the second line at the same font size as the A/B/C heading above it, using normal weight. Do not place yellow explanatory callouts anywhere in the tester PDF. Directly below every `初始 Prompt v1.0` mapping table, add the small note `本 Prompt 依据 Seedream 官方提示词指南编写。`
