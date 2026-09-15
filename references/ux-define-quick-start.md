# 快速上手 Seedream template spec skill v2


## 一、使用流程

### 1. UX 提供参考图文
输入必要信息：
> 模板名称
> 3–6 张黄金参考图
> Input：单图/照片/涂鸦/文字/图文/...
> Scenario：描述用户通常通过什么入口，为什么使用这个模板，希望得到什么。
> （可选）其他已明确的模板表现要求

Agent 分析后，输出第一版「模板定义.pdf」。

### 2. UX审核回应

UX仔细检查整份「模板定义.pdf」。优先回应黄色行，即Agent无法代替 UX 决定的内容；其余定义、Rules、级别、Prompt 和材料建议等，UX也尽量逐项确认。

给出修改反馈，例如：
> R03 的级别改为 PREFER
> R05 的不通过标准改成 ……
> 增加一条关于……的规则
> A类测试材料增加……

Agent 据此同步调整定义，输出下一版「模板定义.pdf」。
重复此过程，直到定义内容确认无误。

### 3. UX确认无误

明确告诉 Agent：
> 已确认，请输出测试指南。

Agent 输出「测试指南.pdf」，可直接交给测试。




## 二、两个交付物：「模板定义」与「测试指南」

「模板定义」只比「测试指南」多两页REFERENCE。

REFERENCE页是为了将模型定义Rules的过程透明化，帮助UX了解skill内部机制，与Agent更顺畅地合作。例如，UX可以通过查看Reference，大致了解ai对参考图分析了哪些方面，在哪些方面达成了一致，哪些方面未达到稳定等。



## 三、定义机制

目前的skill的模板定义逻辑分为三层，Criteria-Rules-Prompt。

### Criteria to Rules
Criteria是skill要求Agent遍历分析的方面，Agent会基于Criteria，对UX提供的图文进行逐项分析，如果某项Criteria表现较为一致和稳定，则可以归纳为Rules。
- Must Rules是该模板必须实现的核心原则，如果未达成，会导致失败的用户体验；
- Prefer Rules是不会影响核心表现，达成后效果会更好的原则。

### Rules to Prompt
基于Rules，Agent会再依据Seedance的Prompt书写指南书写Prompt。