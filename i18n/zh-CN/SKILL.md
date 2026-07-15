---
name: thorlabs-blender-optical-path-zh
description: 从二维光路示意图与厂家 CAD 构建、审核和修订具有物理可信度的 Blender 光学平台。适用于 Thorlabs 兼容镜架、透镜架、分束器、支柱、光纤耦合、孔径、探测器、完整光路拓扑、fail-closed 证据和 Nature 风格光子学渲染。
---

# Thorlabs Blender 光路

把二维示意图转换成可解释、可独立审计的 Blender 光学平台。

英文版是技术权威源。涉及几何时读取 `../../skills/thorlabs-blender-optical-path/references/physical-gates.md`；验收前读取 `evidence-contract.md`；修订旧场景时读取 `history-derived-rules.md`；完整案例见 `project-case-study.md`。

## 权威与版本

1. 系统约束优先；随后是用户最新文字或标注截图、项目 active rules、本 skill，最后才是旧产物和旧 PASS。
2. 冻结已验收版本；每次纠正新建 revision，不覆盖旧证据。
3. 共享 Blender 生成器保持单写入，副 agent 默认只读。
4. 把每个截图问题转换为对象族、世界坐标几何、数值门槛和必需证据。
5. 无法证明时使用 `UNVERIFIED` 或 `BLOCKED`。文件存在、CAD 导入、进程成功、AABB 接触和自报文本都不是证据。

## 核心流程

1. 建立 `schematic node -> 实验角色 -> 真实资产 -> 光/光纤/电端口 -> 支撑路径`。
2. 列出全部分支、器件、光束高度、孔径和探测终点。
3. 记录官方 CAD 的型号、来源、SHA-256、尺度、bbox、局部光轴、法向、孔径和 provenance；替代件必须明示。
4. 先解光心、镜面、分束面、反射和分支连续性。
5. 再从真实桌孔向上按 post-first 构建紧固件、夹具、holder、post、mount 和器件。
6. 修共享根因，先验一个代表件，再传播；保存后重开并逐件复核。
7. 先做明亮的机械/轴向/剖切审计图，再做 beauty render。
8. 完成重开、ray/BVH、OpenCV、GLB 回导、报告、manifest、hash 和全 active-rule 合规矩阵。

光束、柔性光纤和电缆必须是不同对象族。孔径必须真实开放。删除重复 surrogate 和无角色 placeholder。Nature 风格只能在物理门槛通过后修改材质、灯光、相机和排版，不能替代装配证据。

状态：`PASS` 表示所有适用规则有新鲜证据；`PARTIAL/SCOPED` 只代表局部；`UNVERIFIED` 表示证据不足；`BLOCKED` 表示已知失败。禁止把局部通过写成整机最终通过。
