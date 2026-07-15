---
name: thorlabs-blender-optical-path-ja
description: 2D 光学回路図とメーカー CAD から、物理的に妥当な Blender 光学テーブルを構築・監査・改訂します。Thorlabs 互換ミラーマウント、レンズマウント、ビームスプリッター、ポスト、ファイバー結合、開口、検出器、光学トポロジー、fail-closed 証拠、Nature スタイル描画に使用します。
---

# Thorlabs Blender Optical Path

2D 回路図を、説明可能で独立監査可能な Blender 光学テーブルへ変換します。

英語版を技術的な正本とします。形状作業の前に `../../skills/thorlabs-blender-optical-path/references/physical-gates.md`、合否判定の前に `evidence-contract.md`、既存シーンの改訂では `history-derived-rules.md`、実例では `project-case-study.md` を読みます。

## 権限と改訂

1. システム制約、最新のユーザー指示・注釈画像、active なプロジェクト規則、本 Skill、旧成果物・旧 PASS の順に優先します。
2. 合格済み成果物を凍結し、修正ごとに新しい revision を作ります。
3. 共有 Blender generator は single-writer とし、補助 agent は既定で read-only です。
4. 画像指摘を object family、world-space geometry、数値ゲート、必要証拠へ変換します。
5. 実形状で証明できない場合は `UNVERIFIED` または `BLOCKED` とします。CAD の存在、process success、AABB 接触、自己申告は証拠ではありません。

## コア手順

1. `schematic node -> experimental role -> real asset -> optical/fiber/electrical ports -> support path` を作成します。
2. 全 branch、部品、光線高さ、開口、検出端点を列挙します。
3. 公式 CAD の型番、URL、SHA-256、scale、bbox、local axis/normal、aperture、provenance を記録します。
4. 光学中心、鏡面、分割面、反射、branch continuity を先に解きます。
5. 実テーブル穴から fastener、clamp、holder、post、mount、device を post-first で組みます。
6. 共通の配置原因を修正し、代表 1 台を証明してから展開し、保存後に全コピーを再監査します。
7. beauty render より先に明るい mechanical/axial/cutaway 監査画像を作ります。
8. reopen、ray/BVH、OpenCV、GLB reimport、report、manifest、hash、active-rule matrix を完了します。

自由空間光、ガイドファイバー、電気ケーブルは別 family とします。開口は実際に開いていなければなりません。物理 PASS 後にのみ Nature スタイルの材質、照明、カメラ、注釈を変更できます。

`PASS` は全適用ゲートの新しい証拠、`PARTIAL/SCOPED` は限定範囲、`UNVERIFIED` は証拠不足、`BLOCKED` は既知の失敗を表します。
