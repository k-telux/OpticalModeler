<div align="center">

# OpticalModeler

**OpticalModeler 2.0: 図と写真から、編集可能で証拠範囲を明示した光学システムへ。**

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

## v2.0.0: 写真、制約付き改訂、最終成果物までの対話

2.0 は写真による再構築、固定上段端点を持つ局部移動、instrument port/shutter state、独立 presentation copy を区別します。Installed/candidate/proposed identity、意図の受け入れ、凍結 baseline、保存後の保持検査、実画像 producer を明確にします。

[6 事例と実公開 input/output](examples/v2.0/README.md)、[英語の完全対話](examples/v2.0/WALKTHROUGHS.md)、[中国語対話](examples/v2.0/WALKTHROUGHS.zh-CN.md)は、依頼、必要な確認、ユーザーの拒否/修正、検査、最終納品までを示します。図の再構築、写真、compact translation、材質/照明、proposed detector/shutter、audit failure/checkpoint を扱います。

- 写真と固定 constraint: [再構築/改訂](skills/thorlabs-blender-optical-path/references/photo-reconstruction-and-revisions.md)。
- 保存された presentation、画像 reuse、UI/納品: [Presentation と納品](skills/thorlabs-blender-optical-path/references/presentation-and-delivery.md)。
- 実験室 identity を除いた公開: [Publication privacy](skills/thorlabs-blender-optical-path/references/publication-privacy.md)。

実験室由来事例では重要 SKU、実座標/動作値、private photo/scene、対応表を除外します。対話は教育用編集であり raw transcript ではありません。既公開 independent example のメーカー出所は保持します。本版は guidance と ledger software の公開で、新 geometry run、blind test、physical qualification は実施せず、過去の verdict を変更しません。[CHANGELOG](CHANGELOG.md#200--2026-10-07)を参照してください。

```text
Use $thorlabs-blender-optical-path to reconstruct these photographs on the
accepted baseline. Preserve originals and fixed upper endpoints. Deliver an
editable optics-only review model, clear final views and a measurement list.
Separate installed/candidate/proposed parts and keep laboratory identities,
photos and the full scene private.
```

## v1.2.0：新しい測定設計とプレビューの検証範囲

「旧例と同等の精細さで別の測定光路」という依頼では、新しい topology と空のシーンから開始します。再利用できる部品 asset と旧装置全体を区別し、optics-only では光検出器と実支持を保ちながら回路・電気・データの可視化を除きます。

[新設計ガイド](skills/thorlabs-blender-optical-path/references/fresh-design-and-rendering.md)は部品 detail、可視光路、実 port 測定、preview/final render、runtime 分離、納品の終了条件を扱います。[MZI preview の制限事例](examples/fresh-design/mzi-preview/README.md)では、同じ部品 family への hit、固定ゼロ誤差、全画像スコア、2048 幅の preview が、完全な物理合格や 4K 納品を証明しないことを説明します。

本版は Skill と証拠規則の更新であり、新装置の物理認証ではありません。過去のモデル verdict は変更しません。全変更は[更新履歴](CHANGELOG.md#120--2026-09-04)を参照してください。

```text
Use $thorlabs-blender-optical-path to design a new optics-only measurement path.
Use the G1/G2 example for modeling/rendering quality only, start from an empty
scene with provenance-bound component assets, and deliver verified paths and
the requested final-resolution views.
```

## v1.1.0 multi-run qualification

[v1.1.0 qualification package](examples/end-to-end-workflow/qualification-v1.1.0/README.md) は 64/96/128-node N04 scale run と独立した 40-node multi-state interferometer test を比較します。権威 verdict は `PARTIAL_SCOPED`、strict-BVH `BLOCKED`、scale-only `PASS_SCOPED`、topology `UNVERIFIED` のままで、whole-system physical/release PASS はありません。

反復試験により atomic source bundle、live/pinned CAD identity、cache alias、ledger replay、execution/claim status、representative spacing/load、strict collision、stateful topology、public sanitization を強化しました。版ごとの変更は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## 公開 forward test

[4 トラックの公開テスト行列](examples/forward-tests/README.md)は、公開 `v1.0.0` Skill だけを使用した light-sheet/N04、自由空間干渉計、OCT、Thorlabs CAD conversion の分離テストです。Sanitized evidence package、完全な workflow、generation log、replay script を公開し、N04 は propagation `PASS` / model `PARTIAL_SCOPED`、interferometer は `PARTIAL_SCOPED`、OCT は `UNVERIFIED`、CAD conversion は `BLOCKED` のまま保持します。

公開 script の semantic replay、evidence 由来の README/GATE 数値、binary/PNG metadata の fail-closed scan が release gate に追加されました。Sanitization `PASS` は geometry/conversion `BLOCKED` を上書きしません。

4-track matrix は過去の defect-discovery record としてのみ残し、4 package を 1 つの whole-system verdict に結合してはなりません。

## インストール

公開前に `python scripts/validate_repository.py` を実行します。任意の `--private-terms-file /private/release-inputs/sensitive-terms.txt` は repository 外の policy を使い、候補 filename と uncompressed UTF-8/UTF-16 bytes を検査します。Pixel/OCR や archive/container inspection の代わりではありません。既存 manifest、PNG、software regression の検査は維持します。

```bash
npx skills add k-telux/OpticalModeler
```

または `skills/thorlabs-blender-optical-path` を Agent の skills ディレクトリへコピーします。

英語版 Skill が技術的な正本です。[日本語 Skill](i18n/ja/SKILL.md) は日本語の入口を提供し、形状・証拠ルールは英語版を継承します。

Maintainer: [telux](https://github.com/k-telux) · [MIT License](LICENSE)
