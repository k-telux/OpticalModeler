# OpticalModeler

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) &nbsp; / &nbsp; [v2.0.0](https://github.com/k-telux/OpticalModeler/releases/tag/v2.0.0)

[Skill →](skills/thorlabs-blender-optical-path/SKILL.md) &nbsp; [完全対話 →](examples/v2.0/README.md) &nbsp; [Evidence →](skills/thorlabs-blender-optical-path/references/evidence-contract.md)

<img src="assets/readme/wordmark.svg" width="100%" align="top" alt="OpticalModeler — 光路、構造、証拠。">
<img src="assets/readme/formal-optics-detail.jpg" width="100%" align="top" alt="正式な保存モデルから新しいカメラで描画した relay optics、mount、support と既存光路の詳細。">

<sub>正式モデルの新しい camera view。装置配置と beam geometry を保持し、重要 instrument identity と private scene を公開しません。</sub>

**光路を設計し、その根拠を残す。**

OpticalModeler は測定要件、図、装置写真を編集可能な Blender 光学システムへ変える Agent Skill です。光線を実 aperture、mount interface、support path に結び、保存シーン、検査、最終画像を同じ結果へ接続します。

---

## 01 / 意図から始める

対応する Agent Skills installer で:

```bash
npx skills add k-telux/OpticalModeler
```

入力、変更可能範囲、必要な成果物を Agent に伝えます。

```text
Use $thorlabs-blender-optical-path
to reconstruct these annotated photos
on the accepted baseline.
Keep originals and fixed endpoints.
Deliver an editable optics-only model,
clear views and a short checklist.
Separate installed, candidate and
proposed parts.
```

手動では [skill folder](skills/thorlabs-blender-optical-path) を Agent の skills directory にコピーします。

## 02 / 操作を選び、境界を保つ

| 目的 | 出発点 |
|---|---|
| 新しい測定を **Design** | 空のシーン、source-backed topology、許可された component assets。 |
| 図や写真を **Reconstruct** | 権威 input と明示的に保持する baseline。 |
| 受け入れ済みモデルを **Correct** | 凍結 originals、protected families、編集自由度。 |
| シーンを **Audit** | Read-only evidence、実保存 geometry、具体的 findings。 |
| 結果を **Present** | Camera/light copy、保持された geometry と image provenance。 |

固定上段 endpoint は固定します。Optic と mount/support は一体で動かします。Proposed camera は proposed のままです。読みやすい render は presentation の証拠で、未知 physical interface の合格ではありません。

## 03 / 依頼から最終納品まで

- **A — 図からシーン。** 公開 input、final previews、歴史的 evidence を持つ再構築。
- **B — 不完全な仕様の写真。** Installed identity と推定を分けて review model を納品。
- **C — 再設計しない compact layout。** 拒否後に相対 vectors と固定 endpoints を保持して修正。
- **D — より良い照明、同じ装置。** Presentation copy、geometry preservation、新しい affected images。
- **E — 一つの入口、選択出力。** Proposed detector と shutter states、未知内部 transfer の明示。
- **F — 終了コードと不足 evidence。** Valid record または再現可能な blocker/checkpoint。

[英語の完全対話 →](examples/v2.0/WALKTHROUGHS.md) · [中国語対話 →](examples/v2.0/WALKTHROUGHS.zh-CN.md)

実験室由来対話は編集・匿名化された教材です。Private photos、実座標、重要 SKU、full scene は配布しません。

## 04 / 光路、構造、証拠をつなぐ

**光路。** Directed branches、working faces、apertures、detector endpoints。Free-space light と fiber の役割を区別します。

**構造。** 実 mounting interfaces、table holes、fasteners、continuous supports。反復配置前に代表件を検査し、保存後に affected neighbors を再検査します。

**証拠。** 一つの scene lineage、fresh reopen measurements、actual image producers、consistent manifest。Process success、source CAD、clear image はそれぞれの claim を支えます。

[End-to-end workflow](skills/thorlabs-blender-optical-path/references/end-to-end-workflow.md) · [写真再構築](skills/thorlabs-blender-optical-path/references/photo-reconstruction-and-revisions.md) · [Presentation と納品](skills/thorlabs-blender-optical-path/references/presentation-and-delivery.md)

## 05 / 結果の意味を理解する

| Status | 結論 |
|---|---|
| **PASS** | 宣言した適用 gate に current evidence がある。 |
| **PARTIAL / SCOPED** | 明示 subset を検査し、残る blocker と限界を保持。 |
| **UNVERIFIED** | 必要 evidence が不足または不確定。 |
| **BLOCKED** | 既知 requirement に失敗。 |

`READY_FOR_USER_REVIEW` は inspection 用 handoff です。Installed hardware、thread preload、alignment、performance、laser safety の認証ではありません。新 cover は既存モデルの presentation detail で、元の physical limits を保持します。[画像 provenance](assets/readme/MANIFEST.json) · [Publication privacy](skills/thorlabs-blender-optical-path/references/publication-privacy.md)

<details>
<summary><strong>歴史的モデルと qualification results</strong></summary>

- [G1/G2: public input、final previews、sanitized historical acceptance](examples/g1g2/README.md)。Private Blend と vendor CAD は含みません。
- [N04 single-run workflow/replay](examples/end-to-end-workflow/n04-v1.0.1-replay/README.md)。Private assets が必要な static gate は `UNVERIFIED`。
- [Multi-run qualification](examples/end-to-end-workflow/qualification-v1.1.0/README.md)。Scoped、blocked、unverified は別 verdict; whole-system physical PASS はありません。
- [MZI preview limitations](examples/fresh-design/mzi-preview/README.md)。Fixed-zero error、family hit、小 preview は完全 acceptance を証明しません。
- [4 public-only forward tests](examples/forward-tests/README.md)。歴史的 discovery evidence であり、全系 module として結合できません。

</details>

<details>
<summary><strong>Validation、contribution、source boundaries</strong></summary>

```text
python scripts/validate_repository.py
```

Skill editions、resources、manifests、historical verdicts、PNG metadata、software checks を検査します。Private identifier policy は repository 外に置き、pixels/container を別に確認します。[Privacy guide](skills/thorlabs-blender-optical-path/references/publication-privacy.md)

[Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Security](SECURITY.md) · [Project-memory template](rules/OPTICAL_PATH_PROJECT_MEMORY_TEMPLATE.md)

</details>

---

独立 community workflow で、Thorlabs との提携・承認関係はありません。英語が技術的正本です。[中国語](i18n/zh-CN/SKILL.md)と[日本語](i18n/ja/SKILL.md)も同じ evidence rules を保持します。

Maintainer: [telux](https://github.com/k-telux) · [MIT License](LICENSE)
