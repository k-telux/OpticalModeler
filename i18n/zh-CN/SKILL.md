---
name: thorlabs-blender-optical-path-zh
description: 从二维光路示意图与厂家 CAD 通过一个端到端运行、writer、场景谱系和 fail-closed 证据账本构建、审核和修订完整且具有物理可信度的 Blender 光学平台。适用于 Thorlabs 兼容器件、完整光路拓扑、整机 workflow 验证和 Nature 风格光子学渲染。
---

# Thorlabs Blender 光路

把二维示意图转换成可解释、可独立审计的 Blender 光学平台。

英文版是技术权威源。涉及几何时读取 `../../skills/thorlabs-blender-optical-path/references/physical-gates.md`；验收前读取 `evidence-contract.md`；修订旧场景时读取 `history-derived-rules.md`；完整案例见 `project-case-study.md`；整机运行前读取 `end-to-end-workflow.md`。

## 权威与版本

1. 系统约束优先；随后是用户最新文字或标注截图、项目 active rules、本 skill，最后才是旧产物和旧 PASS。
2. 冻结已验收版本；每次纠正新建 revision，不覆盖旧证据。
3. 整机保持一个 run ID、writer、revision、生成器/Blend 谱系和 workflow 账本；副 agent 默认只读，禁止拼接独立写入模块冒充整机完成。
4. 把每个截图问题转换为对象族、世界坐标几何、数值门槛和必需证据。
5. 无法证明时使用 `UNVERIFIED` 或 `BLOCKED`。文件存在、CAD 导入、进程成功、AABB 接触和自报文本都不是证据。

## 核心流程

1. 用 `scripts/workflow_ledger.py` 初始化一个整机 run spec、状态账本和 append-only 事件哈希链。
2. 建立 `schematic node -> 实验角色 -> 真实资产 -> 光/光纤/电端口 -> 支撑路径`。
3. 列出全部分支、器件、光束高度、孔径和探测终点。
4. 只从 manifest 锁定的厂家 URL 把官方 CAD 下载到私有缓存；原子落盘前复核 bytes 与 SHA-256，并记录型号、来源、尺度、bbox、局部光轴、法向、孔径、provenance 和再分发边界。替代件必须明示；没有明确授权时禁止公开厂家几何。
5. 先解光心、镜面、分束面、反射和分支连续性。
6. 再从真实桌孔向上按 post-first 构建紧固件、夹具、holder、post、mount 和器件。
7. 修共享根因，在同一运行内先验一个代表件再传播；保存后重开并逐件复核。
8. 先做明亮的机械/轴向/剖切审计图，再做 beauty render。
9. 发布脚本必须能重算同一语义锁，README/GATE 计数必须来自机器证据；随后在同一账本完成重开、整机 ray/BVH、OpenCV、GLB 回导、二进制/PNG 元数据脱敏、manifest、hash 和全 active-rule 合规矩阵。

光束、柔性光纤和电缆必须是不同对象族。孔径必须真实开放。删除重复 surrogate 和无角色 placeholder。Nature 风格只能在物理门槛通过后修改材质、灯光、相机和排版，不能替代装配证据。

状态：`PASS` 表示所有适用规则有新鲜证据；`PARTIAL/SCOPED` 只代表局部，必须列出 blocker 且 final/release 保持 false；`UNVERIFIED` 表示证据不足；`BLOCKED` 表示已知失败。禁止把脱敏通过、局部通过或 CAD 导入成功写成整机最终通过。
