# v12：定稿收尾与冻结说明

2026-11-05。正文六页、五表两图、15项参考文献；补充材料四页。署名与v11一致，尚未投稿。

本轮按完整收尾核查意见进行有限报告修订。四个证明环境、Algorithm 1及表II—V全部数值行逐字一致；生产代码、测试、输入、原始/派生实验记录均未改动，未重跑计时求解。

## 已完成

1. V-A及补充S4明确95% percentile bootstrap confidence intervals；2000次(n,family,seed)簇重采样，因素与重复保持同簇。2.5%/97.5%端点与summarize_gate.py一致，原区间数字不变。
2. V-A及补充S4明确整次查询软目标：主实验1秒、加权消融1秒、旧差距2秒。补充注明主/消融每方法每例三次计时，旧差距一次。原配置不变。
3. Section III在定义固定图G、连通分量和路径区域前删除零权边，与区域实现的w>0传播一致；这不改变能量。
4. IV-F容量反例显式给出r=(1,1)，与单位负载区分。
5. 参考文献[4]和编辑用references.bib补文章号e28。核对来源：[Bath出版记录](https://researchportal.bath.ac.uk/en/publications/the-emergent-structures-in-digital-engineering-work-what-can-we-l/)。[15]的作者顺序保持正式PDF所列顺序。
6. 正文及当前补充统一使用speedup；摘要首次写3.17×和1.01×。统计口径和3.17/1.01/2.36数值均不变。
7. 式(7)分两行，编号不变；CAD矩阵浮动源位置提前，保留为第5页图2。两个原始图像均不变，未缩小字号或边距。表I、IV、V没有排版故障，未进行低收益的行距/长表注重排。

## 核查与重建

正文及补充逐页渲染查看，通过字体嵌入、页数、引用解析、数值行一致性及四项说明检查。没有把已有24项算法测试或6420次保存调用的独立核查描述成本轮新增实验。当前代码与冻结记录哈希对照v11保持一致。

```sh
# 使用IEEEtran兼容环境编译main.tex（如tectonic）。
python scripts/build_analysis_supplement_v12.py
.venv/bin/python scripts/check_paper.py
```

补充构建依赖requirements-build.txt中的reportlab，继续读取certificate_analysis_v11的冻结派生统计。v11构建脚本作为历史记录保留。可用[会议投稿要求](https://cscwd2027.dailyeliteevents.com.au/submission.html)核对六页上限；本轮未执行PDF eXpress认证或提交论文。

## 停止标准

主体内容现已冻结，建议进入投稿准备。除非发现实质正确性、事实/统计矛盾或格式阻断，或作者明确改变研究范围，不再主动扩展实验、改模型或反复润色小细节。创新增量、受限双团队假设及实际应用收益的剩余风险需要另一轮研究，已在现稿披露；这次收尾不声称消除了这些风险。
