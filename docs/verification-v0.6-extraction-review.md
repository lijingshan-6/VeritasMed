# 原子拆分的开发复核记录

这是实施者 AI 对已保存输出的诊断，**不是独立人工标签或医学核查器的准确率**。
复核集合沿用消融协议在观察输出前按 seed 选定的 3 个来源组、全部 4 个变体，共 12 条。
未按错误、漂亮案例或最终测试成绩选样。原始记录见
[`ablations/manifest.json`](../data/verification/v06/ablations/manifest.json)，
输入及构造事实见 [`medical.json`](../data/verification/v06/medical.json)。

复核只比较原回答与提取表：事实是否遗漏，原文限定词是否保留，代词展开是否有依据，
是否新增原文没有的含义。来源判断分开讨论；这里不重新打分或修订构造标签。

| 来源 / 变体 | 原回答与规范化事实的对照 | 发现及处置 |
|---|---|---|
| medical-04 / original_meaning | 67.4% 对应 most deprived fifth；75.5% 对应 least deprived fifth；that procedure 展开为 anterior resection for rectal cancer | 两个人群、比例、手术均可回到原回答。此样本未发现新增含义；不推断总体无损 |
| medical-04 / paraphrase | 同样保留最贫困/最不贫困五分位与各自比例 | 对应关系仍在规范化文本中；槽位并非每项都填满，不能把空槽位当成原回答无该信息 |
| medical-04 / single_error | 保留两个 75.5%，没有把第一个数自动改回来源的 67.4% | 保留待审错误，第一项 contradicted，第二项 supported；不把“修正后正确”记作审计成功 |
| medical-04 / evidence_removed | 仍拆出两项原有事实，不根据剩余无关来源删除它们 | 两项 insufficient；这只是明确删证据的构造控制 |
| medical-06 / original_meaning | 两项均保留 per 100,000 per quarter 及 period 1 / 3 | 第二项 comparator 标成 period 1 是对并列关系的模型解释，原句并未独立声明统计比较；不能直接转成比较效果结论 |
| medical-06 / paraphrase | 第一项保留 quarterly average；第二项规范化为 “In period 3, the corresponding colonoscopy rate was 1,919 per 100,000.” | **第二项未显式保留 quarterly average**。原回答中的 corresponding 回指带有该时间分母的 rate；独立目标若只读取规范化文本，会丢失限定。保留这一失败，不调整提示后覆盖结果 |
| medical-06 / single_error | 第一项 1919、period 1 保留，第二项 1919、period 3 保留 | 没有悄悄修正第一个时期；两个目标均保留季度分母 |
| medical-06 / evidence_removed | 两个数字、时期和季度分母均保留 | 核查两项 insufficient；不是自然缺证据发生率 |
| medical-15 / original_meaning | 4828 同意提供样本；4550 有结果且在排除 278 后；另列 278 被排除 | 产生重复覆盖；含 after 限定的复合事实仍自报 atomic。不能相信模型的 atomic 字段足以证明真正原子化 |
| medical-15 / paraphrase | 4828、278、4550 出现在规范化文本里，value_unit 槽位多处仅写 participants / samples | **槽位未完整复制数字**，但不能误报为规范化文本也漏数字。第一项被判 insufficient；初看人数存在曾归为判断失败，但 09-27 复看发现 Natsal-3 波次并未由给定来源建立，因此不能据数字正确断定完整命名事实应为 supported |
| medical-15 / single_error | 8047 错误保留；后半句拆成 4550、278、after 278 三项 | 重复与复合项并存，但时间关系有单独保留。第一项 contradicted，不把其余重复支持计成多个独立成功 |
| medical-15 / evidence_removed | 同样保留 4828、4550、278 及 after 关系 | 最后一项在此变体被标 still_compound → needs_review；相近原句的原子状态不一致，提示自报拆分状态不稳定 |

这 12 条显示了三种不同问题：规范化文本丢限定词、显式槽位信息不足、拆分重复/复合状态不一致。
原文绑定和高亮让它们可以被发现，**不会自动使规范化事实可信**。
当前保留原回答、原片段、模型解释和槽位供审阅；默认策略仍为 Direct。

医学全量表使用字符位置关联构造事实，只能衡量位置覆盖与关联判断，不能替代此处的语义复核。
未对余下全部样本宣称完成独立提取保真度标注，也不将这次 AI 开发复核合并为发布主准确率。

下一阶段应针对限定词继承建立独立、可复查的目标，并以冻结新来源检验；不要在本次已曝光集合
反复修提示后把成绩当新测试。临床适用范围和跨文献可比性仍不由这些槽位自动判定。

**2026-09-27 补充勘误：** medical-15 的构造标签自身有给定来源范围问题。见
[标签复看记录](../data/verification/v06/medical-label-review.json)与统一去掉该组的
[事后敏感性分析](../data/verification/v06/medical-label-sensitivity.json)。这是对上述 AI 诊断的
修正，不修改原始模型结果，也说明 AI 复核不能被当成独立专家裁决。

**同目标 E2 的引用问题：** medical-06 的 original_meaning 第二项与 paraphrase 两项均返回
`supported`，但使用 `sentence_ids=[1]`。E2 将给定源视图合成一个证据单元，实际仅有编号 0，
因此保留为 `SentenceOutOfRange`。这体现了多句文字包装与引用编号的契约问题，不能仅凭这个
状态断言三条内容判断都错了。原结果不改写，最终固定目标报告另列标签层诊断。
