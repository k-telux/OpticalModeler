# Thorlabs Blender Optical Path Skill

[English](README.md) · [简体中文](README.zh-CN.md)

2D フォトニクス回路図を、物理的に監査可能な Blender 光学テーブルへ変換する Agent Skill です。光学トポロジー、実開口、メーカー CAD、締結部、荷重経路、ファイバー曲率、証拠の系譜を必須ゲートとして扱います。

> 非公式コミュニティプロジェクトです。Thorlabs, Inc. とは提携しておらず、同社の承認も受けていません。レンダリングされた CAD は、機械・分光・レーザー安全・実験性能の認証ではありません。

## 例

| 2D 入力 | Nature スタイル 3D 出力 |
|---|---|
| ![2D G1/G2 schematic](examples/g1g2/input/fig_s17_componentlibrary_g1g2.png) | ![3D optical table](examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg) |

```bash
npx skills add k-telux/thorlabs-blender-optical-path
```

英語版が技術的な正本です。日本語 Skill は [i18n/ja/SKILL.md](i18n/ja/SKILL.md)、詳細は [English README](README.md) を参照してください。メーカー STEP/CAD と大容量の実験用 Blend は Git に含めません。
