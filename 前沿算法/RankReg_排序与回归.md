# RankReg：排序与回归目标的候选连接

## 身份、版本与状态

- 原始论文：[Rank-guided learning accelerates automated enzyme engineering](https://doi.org/10.1038/s41467-026-76264-2)，Nature Communications，2026 年；精确发表日期待补核。Nature Portfolio 身份与 Nature 主刊分别登记，中科院一区身份待官方分区核验。
- 仓库：[zyan-y/REAP](https://github.com/zyan-y/REAP)，固定 commit `96c69e94b3b39c33ffb70ac394bd06022b4f035f`；2026-10-28 检查，非归档、非禁用。
- README 明确 AGPL-3.0-only，根 LICENSE 与 GitHub AGPL-3.0 标签已核对；依赖分别授权。
- 状态：固定 README、LICENSE、requirements.txt 和 src/reap/losses.py 已静态阅读；论文原始页面的机制描述与仓库方向一致。完整论文、补充材料、代码双向关联和结果复现未完成。来源 `source:FRONTIER-RANKREG-PAPER-2026`、`source:FRONTIER-RANKREG-CODE-2026`。

## 基线缺口与可迁移问题

只降低数值预测误差，可能不能充分满足“优先筛选最有价值对象”的决策目标。原研究在酶工程中结合数值回归和成对排序，并迭代接收实验反馈。本库提炼的是“让损失与实际筛选目标对齐”的候选问题；不把生物实验效果推广到交通、能源或一般表格回归。

任务契约候选：输入为对象特征及可比较的连续标签；输出为数值预测和候选排序。只有实际存在筛选成本或 top-k 决策时，才考虑增加排序项；纯数值预测先做简单回归。

## 固定实现的静态发现

src/reap/losses.py 中 rank_reg_loss 将均方误差与成对损失加权。成对部分依标签差决定顺序、间隔与权重，并对接近的标签使用预测差平方。批量小于 2 时退回均方误差。这些只是该固定模块的代码行为，尚未完成公式独立推导和运行核对。

一个值得提前防范的成本点：可选 pair sampling 发生在 torch.combinations 已构造所有配对之后，不能把该选项宣传为消除了全部成对枚举的内存成本。标签量纲、标准化与近似相同标签的阈值会影响权重和间隔；源码默认值不是推荐参数。

仓库还涉及模型权重获取、训练、结果写入及实验辅助工具。本次未安装依赖、未执行训练或湿实验相关入口；单模块静态阅读不是全仓安全认证。

## 最低验证计划（未执行）

- 在相同特征、模型头、训练预算和划分下，比较 MSE、Huber 与排序—回归组合；再加入岭回归、随机森林等结构匹配基线。
- 同时报数值误差、Spearman 排序相关和预先固定 k 的筛选收益；不能只挑有利指标。k 与选择规则须在测试前确定。
- 主体、来源或实验轮次关联按结构划分；主动选样只能用当轮已观测标签，不把未来反馈倒灌训练。
- 检验标签并列、单样本、顺序反转、尺度变换，以及全配对和抽样差异；训练外多种子比较后再谈性能。
- 删除排序项，观察实际筛选收益是否下降；若收益不足以覆盖解释、调参和计算成本，保留简单回归。

英文计划表述：

> The prediction task also requires selecting a small set of candidates. We will therefore compare a ranking-aware loss with pointwise regression under the same validation protocol. Better ranking alone will not be treated as evidence of better numerical prediction.

目前没有本地性能、跨领域泛化或新颖性验证；未制作图像。

## 2026-10-30：先验证评价目标是否一致

新增[可运行评价反例](评价目标反例/README.md)：固定三个对象和两个人为预测向量，数值误差与top-1真实收益给出相反偏好。8项精确算术、置换/尺度和边界检查通过，并有可复算结果及英文解释。反例限定在设计输入，不是RankReg复现或训练外性能证据；本轮所检查的Conda环境无PyTorch，未安装依赖或执行上游代码。

方法库据此先把评价目标写清，再做模型选择；审查库要求并列报告误差、筛选收益及比较边界，不能用某一指标的改善替代全部题目要求。原最低验证计划仍未执行。
