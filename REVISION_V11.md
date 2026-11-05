# v11：算法分支、最终证书与统计口径一致性

2026-11-05。正文六页、五表两图、15引用；新增合并下界推论，补充材料四页。作者王治然（Zhiran Wang），中国海洋大学，2174560006@qq.com。未投稿。

## 代码与伪代码

- Algorithm 1容量检查失败明确返回CAPACITY_NOT_CERTIFIED并终止；Python容量接口对应CapacityNotCertified异常，失败不进入求解。
- CP-SAT超时无可行incumbent沿用已有旧方案兜底，显式记录incumbent_source=old_plan_fallback。局部上界是旧局部能量；吸收外部常数后与重构方案目标一致。
- 设v为新目标无预算最优值，L_K/U_K已包含外部常数。K=V时L_final=max(v,L_K)；严格缩区时L_final=max(v,L_K-epsilon)。返回x、U_K=E1(x)、[L_final,U_K]；按此区间是否闭合认证全局最优。
- barr/cpsat.py和标准库参考barr/core.py均同步。common_fastpath=False只关闭CP包装器的提前返回，仍计算并计入无预算下界。历史正式计时使用各阶段保存的原源码，不以新版本改写计时结果。
- 24项测试通过，新增120组小图/预算枚举对照两个后端；覆盖正epsilon、全/部分区域、负常数、下界合并、无incumbent兜底。现有容量反例和拒绝分支继续通过。

## 冻结数据的派生分析

目录results/certificate_analysis_v11，原始输入/解/界/计时及source快照全部保留。

- 32例epsilon：全部22零损失(68.75%)；全图6/6，真正缩区16/26(61.54%)。B=8为6/16，B=16为16/16，其中10例真正缩区。实际零损失由已证FullCP参考核实，不等于BARR自己认证最优。
- 对九个已完成阶段共6208次保存CP调用离线合并下界（包括加权HopCP，不含LR调用/早期休眠诊断）。18个下界增强，均来自epsilon组；全图6例新闭合，其余26个BARR区间仍开放，包含16个实际零损失例。derived_certificates.csv同时保存原状态/区间及派生状态/区间。不据此声称求解更快。
- 全图族/规模统一报告逐例三次耗时中位数之和及其比值。Grid128/512约1.095/1.664，Modular128/512约1.211/2.360，Small-world128/512约0.988/0.996。Modular512全80例为3.634/1.540秒；这是旧计时汇总，不是新串行工作负载测试。原配对速度中位数1.009(约1.01)仍保留。
- 补充表S2同时给出FullCP/BARRCP建模、求解、共同割、预处理及其他开销。按输入/重复配对，再先在输入内取分项均值，再按层汇总；相同重复数下等价于同批调用均值，分项可加总。other是同调用total扣去四分项的残差，包括设置/重构/记账/时钟差；不把分项中位数相加。
- 旧日志只能分离认证/区域/边界的合计预处理，不能分别识别每个步骤。各输入/调用/全体与非快捷层的完整CSV均提供。Modular512非快捷层平均建模/求解节省14.575/55.404ms、额外预处理1.744ms；小世界负收益保留。

## 版式与表述

- 正文保留并集一次epsilon、区域存在性、完整证明、边界常数、容量冗余及活跃容量反例；补充合并下界推论。区分结构回退所需条件与非负权图割实现条件，不扩展模型。
- N统一指queries not resolved by the shared cut shortcut，图表采用N/all；主表II短表注，定义移至邻近正文。正文保留3.17/1.01、66/72公开快捷、全部困难结果及400调用重复等关键事实。
- 正文两图都保留；CAD原始矩阵像素不变，仅顶部注释统一为N。补充图S1快捷查询移到独立灰色标记区，不放在真实全图区域100%处。
- S1几何与累计耗时，S2配对时间分解，S3损失/预算/缩区分层与派生证书，S4协议和历史。压缩重复叙述与结论，未缩字体或页边距，未重跑困难计时。

## 重现

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_certificates_v11.py --out results/certificate_analysis_recheck_new
.venv/bin/python scripts/build_analysis_assets_v11.py
python scripts/build_analysis_supplement_v11.py
.venv/bin/python scripts/check_paper.py
```

分析输出目录必须不存在。绘图使用项目matplotlib；PDF补充构建需要requirements-build.txt中的reportlab。原始结果不可覆盖；check_paper.py在完整工作目录检查编译日志，在公开材料无build目录时记录其不可用。不重做有效锚点/多轮实验，不作原创性、实际部署收益或录取概率保证。
