<div align="center">

# OpticalModeler

**从二维光路示意图到可物理审计的 Blender 光学平台。**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Validation](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml/badge.svg)](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)

<img src="examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg" width="100%" alt="经过物理审计的 G1/G2 光学平台 Nature 风格渲染">

</div>

OpticalModeler 是一个证据优先的 Agent Skill，用于在 Blender 中重建实验室光路。它把光路拓扑、真实孔径、厂家 CAD、紧固件、承载链、光纤布线和证据血缘作为硬性验收门槛，而不是装饰细节。

> **独立社区项目。** 与 Thorlabs, Inc. 无隶属或背书关系。产品名称仅用于识别兼容硬件。渲染的 CAD 装配不构成机械、光谱、激光安全或实验性能认证。

## 核心能力

| 物理装配 | 光学真实性 | Fail-closed 证据 |
|---|---|---|
| 立柱优先、真实台孔、紧固件、承载链与受支撑硬件。 | 孔径居中、分束平面、支路连续、内部细束与光纤弯曲约束。 | 重开场景审计、光线/BVH 检查、哈希、清单、标注渲染与明确状态。 |

## 二维输入 → 已验证三维输出

| 原始光路图 | 标注后的三维重建 |
|---|---|
| <img src="examples/g1g2/input/fig_s17_componentlibrary_g1g2.png" width="100%" alt="原始 G1/G2 光路图"> | <img src="examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg" width="100%" alt="三维光学平台标注俯视图"> |

脱敏的 [G1/G2 案例](examples/g1g2/README.md)包含二维原始输入、编辑级三维渲染和机器可读验收记录。厂家 STEP/CAD 与大型实验 `.blend` 不进入 Git。

## 公开前向测试

[四轨公开测试矩阵](examples/forward-tests/README.md)记录了仅使用发布版 `v1.0.0` Skill 的 light-sheet/N04、自由空间干涉仪、OCT 与 Thorlabs CAD 转换测试。它公开净化后的 evidence package、完整标记 workflow、生成日志和可重放脚本，同时保持最弱 verdict：N04 仅传播门 `PASS`/整体 `PARTIAL_SCOPED`，干涉仪为 `PARTIAL_SCOPED`，OCT 为 `UNVERIFIED`，CAD 转换为 `BLOCKED`。

这些测试新增三项 release gate：公共脚本必须重算出相同语义锁；README/GATE 数值必须来自 reopen evidence；二进制与 PNG 元数据必须逐文件解析，不能把解码失败当成零命中。脱敏 `PASS` 不会覆盖几何或转换 `BLOCKED`。

## 安装

```bash
npx skills add k-telux/OpticalModeler
```

也可以把 `skills/thorlabs-blender-optical-path` 复制到 Agent 的 skills 目录。

## 调用示例

```text
使用 $thorlabs-blender-optical-path 把这张 pump-probe 示意图重建为 Blender 光学平台，并生成 fail-closed 物理审计。
```

英文 Skill 是技术权威源；[简体中文 Skill](i18n/zh-CN/SKILL.md)提供中文入口，并明确继承英文版的几何与证据合同。仓库还包含[项目规则模板](rules/OPTICAL_PATH_PROJECT_MEMORY_TEMPLATE.md)、无第三方依赖的发布验证器与像素数据保持不变的 PNG metadata 清理器。

维护者：[telux](https://github.com/k-telux) · [MIT License](LICENSE)
