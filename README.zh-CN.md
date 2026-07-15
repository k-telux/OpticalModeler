# Thorlabs Blender 光路 Skill

[English](README.md) · [日本語](README.ja.md)

这是一个把二维光路示意图转换为可物理审计 Blender 光学平台的 Agent Skill。它把光路拓扑、真实孔径、厂家 CAD、紧固件、承载链、光纤曲率和证据血缘作为硬门槛，而不是装饰细节。

> 非官方社区项目，与 Thorlabs, Inc. 无隶属或背书关系。产品名称仅用于识别兼容硬件。渲染模型不构成机械、光谱、激光安全或实验认证。

## 示例

| 二维原始输入 | Nature 风格三维输出 |
|---|---|
| ![二维 G1/G2 光路](examples/g1g2/input/fig_s17_componentlibrary_g1g2.png) | ![三维光学平台](examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg) |

安装：

```bash
npx skills add k-telux/thorlabs-blender-optical-path
```

典型调用：

```text
使用 $thorlabs-blender-optical-path 把这张 pump-probe 示意图重建为 Blender 光学平台，并生成 fail-closed 物理审计。
```

仓库包含英文权威 skill、简体中文和日文版本、项目规则模板、脱敏的 G1/G2 案例，以及不依赖第三方包的发布验证器。厂家 STEP/CAD 和大型实验 Blend 不进入 Git。

详细使用方法见 [英文主页](README.md)，中文 Skill 见 [i18n/zh-CN/SKILL.md](i18n/zh-CN/SKILL.md)。
