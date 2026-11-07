# MFTabPFN：多保真回归候选

## 选用摘要

| 项目 | 本卡要点 |
|---|---|
| 问题 | 不同精度的数据能否改善高精度目标预测 |
| 验证链 | 高保真单独回归 → 同对象隔离验证 → 覆盖/成本检查 |
| 停止条件 | 低保真引入负迁移、层级错配或权重/许可不清时退出 |
| 证据状态 | 研究候选，未完成算法复现与目标任务验证 |

## 身份、版本与状态

- 原始论文：[A multi-fidelity tabular prior-data fitted network model for accurate prediction and uncertainty quantification](https://doi.org/10.1038/s41467-026-75163-w)，Nature Communications，2026-07-04。这是 Nature Portfolio 期刊，不是 Nature 主刊；中科院分区年份和大类/小类尚未核验。
- 仓库：[Rockou/MFTabPFN](https://github.com/Rockou/MFTabPFN)，固定 commit `34bee8546c804b727d01a5239b5db48796bbd8ea`；2026-10-28 检查，非归档、非禁用。
- 仓库根许可证 Apache-2.0；不能据此概括所有内嵌依赖、模型权重及外部数据的授权。
- 状态：仓库身份、固定 README、许可证及 requirements1.txt 已核验；论文题名/日期由 DOI 元数据核对。论文全文与官方代码双向关联仍需补核，算法结果未复现，适用性为研究候选。来源 `source:FRONTIER-MFTABPFN-PAPER-2026`、`source:FRONTIER-MFTABPFN-CODE-2026`。

## 为什么值得研究

当同一物理量存在大量低成本粗模拟及少量高成本精确观测时，单独使用高精度样本会舍弃已有信息，而简单混合可能把系统偏差当噪声。该论文研究多保真表格预测及不确定性；本卡仅记录这一方向，尚未独立核对内部构造、公式或性能排名。不要把多个精度标签直接当可互换样本。

任务契约候选：输入是特征、目标量、保真层级及观测成本；输出是高保真目标的预测及需校准的区间。先核验不同保真层级的变量定义、单位、配对关系、取得时点与偏差。无真实多保真来源、不能区分系统误差或只有一个精度层时，优先保留简单模型。

## 最低验证计划（未执行）

- 基线：高保真数据单独拟合的线性/岭回归、树回归；按任务需要加入简单多保真残差校正。与候选共用高保真评价样本、信息和预算。
- 划分：同一物理对象或同一设计点的不同保真记录不得跨训练/测试泄漏；未来预测按取得时序留出。
- 指标：MAE/RMSE、预测区间覆盖率与宽度、成本及失败率；区间输出不等于已校准。
- 消融：只用高保真与加入低保真、正确层级与错配层级比较；检查低保真偏差过大时是否反而恶化。
- 判退：无训练外收益、成本超出赛时资源、权重不可用或模型机制难以解释时，不进入主线。

## 实现审阅与英文解释

固定 README 声明 Python 3.11、基于 TabPFN v2.2.1，并提供 Test_example/Toy_S.py 等入口；这是作者说明，不是本机测试。requirements1.txt 含本地 editable 依赖、CUDA 源 PyTorch 2.7.1 和多个固定版本。运行前须检查嵌套软件、权重下载、CUDA 可用性与输出路径；本次未安装、未运行这些入口。

可用于候选方案的英文：

> We will test whether lower-cost observations improve prediction of the high-fidelity target. The comparison will hold the high-fidelity test set and information available at prediction time fixed. Any uncertainty intervals will require a separate calibration check.

这段是验证计划，不是已取得的实验结论。未生成性能图，不宣称视觉验收或论文复现。
