<div align="center">

# OpticalModeler

**2D 光学回路図から、物理的に監査可能な Blender 光学テーブルへ。**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Validation](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml/badge.svg)](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)

<img src="examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg" width="100%" alt="物理監査済み G1/G2 光学テーブルの Nature スタイルレンダー">

</div>

OpticalModeler は、実験室の光路を Blender で再構築する証拠優先の Agent Skill です。光学トポロジー、実開口、メーカー CAD、締結部、荷重経路、ファイバー配線、証拠の系譜を必須の受け入れゲートとして扱います。

> **独立したコミュニティプロジェクトです。** Thorlabs, Inc. との提携・承認関係はありません。製品名は互換ハードウェアの識別にのみ使用します。レンダリングされた CAD は、機械・分光・レーザー安全・実験性能の認証ではありません。

## 主な特徴

| 物理アセンブリ | 光学的整合性 | Fail-closed 証拠 |
|---|---|---|
| ポスト優先配置、実テーブル穴、締結部、荷重経路。 | 開口中心、ビームスプリッター面、分岐連続性、内部細線ビーム、ファイバー曲率。 | 再オープン監査、レイ/BVH 検査、ハッシュ、マニフェスト、注釈付きレンダー、明示的な状態。 |

## 2D 入力 → 検証済み 3D 出力

| 元の光学回路図 | 注釈付き 3D 再構築 |
|---|---|
| <img src="examples/g1g2/input/fig_s17_componentlibrary_g1g2.png" width="100%" alt="元の G1/G2 回路図"> | <img src="examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg" width="100%" alt="3D 光学テーブルの注釈付き上面図"> |

匿名化済みの [G1/G2 ケーススタディ](examples/g1g2/README.md)には、2D 入力、3D レンダー、機械可読の受け入れ記録が含まれます。メーカー STEP/CAD と大容量の実験用 `.blend` は Git に含めません。

## 統合 whole-system workflow

現在の主要 workflow は、1 つの run ID、1 つの revision、1 人の writer、1 本の generator lineage、1 本の Blender scene lineage、1 冊の append-only evidence ledger を持つ順序付き単一 run です。Source lock、topology、CAD provenance、representative smoke、full-scene propagation、saved-scene reopen、optomechanical audit、render、sanitization は同じ run の gate であり、独立 module を後から結合する方式ではありません。

[End-to-end workflow contract](skills/thorlabs-blender-optical-path/references/end-to-end-workflow.md)、[single-run N04 deterministic replay](examples/end-to-end-workflow/n04-v1.0.1-replay/README.md)、[fresh whole-system runbook](examples/end-to-end-workflow/n04-v1.0.1-replay/RUNBOOK.md) から開始してください。Static replay は vendor CAD と代表 `.blend` を repository から除外するため `UNVERIFIED` で停止し、下流 gate は pending のままです。新しい private revision では公開済み fetch/build/reopen/audit/sanitization script を連続実行できます。

## 公開 forward test

[4 トラックの公開テスト行列](examples/forward-tests/README.md)は、公開 `v1.0.0` Skill だけを使用した light-sheet/N04、自由空間干渉計、OCT、Thorlabs CAD conversion の分離テストです。Sanitized evidence package、完全な workflow、generation log、replay script を公開し、N04 は propagation `PASS` / model `PARTIAL_SCOPED`、interferometer は `PARTIAL_SCOPED`、OCT は `UNVERIFIED`、CAD conversion は `BLOCKED` のまま保持します。

公開 script の semantic replay、evidence 由来の README/GATE 数値、binary/PNG metadata の fail-closed scan が release gate に追加されました。Sanitization `PASS` は geometry/conversion `BLOCKED` を上書きしません。

4-track matrix は過去の defect-discovery record としてのみ残し、4 package を 1 つの whole-system verdict に結合してはなりません。

## インストール

```bash
npx skills add k-telux/OpticalModeler
```

または `skills/thorlabs-blender-optical-path` を Agent の skills ディレクトリへコピーします。

英語版 Skill が技術的な正本です。[日本語 Skill](i18n/ja/SKILL.md) は日本語の入口を提供し、形状・証拠ルールは英語版を継承します。

Maintainer: [telux](https://github.com/k-telux) · [MIT License](LICENSE)
