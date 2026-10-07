---
name: thorlabs-blender-optical-path-zh
description: 从测量需求、二维光路图和有来源记录的 CAD 设计新测量光路，或重建、审核、修订 Blender 光学平台。适用于高精度 optics-only 模型、Thorlabs 兼容光机件、光路拓扑、整机验证及具有明确物理证据范围的发表级渲染。
metadata:
  version: "2.0.0"
---

# OpticalModeler 2.0 — Thorlabs Blender 光路

把测量需求或二维示意图转换成可解释、可独立审计的 Blender 光学平台。

## 2.0 新增任务与交付边界

英文版为技术权威源。照片重建、固定端点/局部移动、端口与快门状态时读取[照片重建与修订](../../skills/thorlabs-blender-optical-path/references/photo-reconstruction-and-revisions.md)；材质、灯光、图片复用、交互打开状态与最终回复时读取[展示与交付](../../skills/thorlabs-blender-optical-path/references/presentation-and-delivery.md)；实验室经验公开时读取[发布隐私](../../skills/thorlabs-blender-optical-path/references/publication-privacy.md)。[六组完整中文交互](../../examples/v2.0/WALKTHROUGHS.zh-CN.md)展示需求、必要确认、用户否决/纠正、检查及最终产出；对话为教学改写，不是原始聊天或新增盲测。

- 区分新测量设计、照片/图纸重建、受约束修订、展示副本和只读审核。新测量从空场景/新拓扑开始；用户明确要求保留的重建基线可在新 revision 只读复用。局部修订延续原谱系、输入锁和真实 pending 门，不伪造整机账本完成。
- 分开实装/用户确认身份、厂家候选、拟装器件、geometry 来源、图纸/模型/现场尺寸与物理资格。真实 holder 不能证明未知 insert 的处方。
- 几何前锁定完整 protected set、rigid 内部向量、固定上层完整位姿、镜数/顺序、水平段方向及可动自由度。“紧凑”不授权重排光路；用户意图独立于几何诊断验收。
- 使用实际工作面中心/法线，整族移动包括其他 node 的脚/螺钉，并检查 changed-to-fixed/changed-to-changed。平台覆盖比较完整器件/支撑 footprint 与真实 plate projection，不只中心点。检查源板真实范围、孔相位、材料槽/多边形索引、宽承面与盲孔底；null 不当零 gap，有限接触不当 retention/preload/load 资格。
- 未知内部传输保持功能黑箱；真实端口需要开孔，按准确配置区分选择输出和同时分光。每态刷新 evaluated transform/visibility，关闭时轴止于声明包络，拟装身份在图像/说明保持。
- 展示在独立副本进行。保存后比较完整相关网格/拓扑、属性/法线、modifier、语义、槽位、可见性和状态；先查真实 shader 归属，必要时仅目标 object/slot 独立材质，保护光学/感光面。看实际成图和逐支路；在框内不等于无遮挡。实际 decode 核尺寸/位深。
- 旧图复用保留原 producer 并有完整依赖保持桥接，不改 hash 冒充新渲染。Relight/recolor 的受影响视角需要新图。
- 先用已有照片/证据，再问影响执行的关键问题。用户选择先交完整审阅候选时，完成 editable model、实际全路径图、观看指南与现场清单，明确未知。`READY_FOR_USER_REVIEW` 不等于物理 PASS。
- 获授权并行时共享 writer 仍唯一。普通反馈合并到自然检查点/idle 队列，不反复打断进行中的 render。尊重明确资源停止点并保存可恢复状态；完成指定交付后停止可选修改。
- 公开用稳定功能别名；关键型号、真实坐标/参数、实验室照片、私有模型、邮箱/session 信息和映射不入 Git。旧公开独立案例的厂家来源保持。私有词表留仓库外，配合可选 scanner 及实际视觉/容器检查验证最终候选。

最终可打开文件使用绝对路径 Markdown 可点击链接，必要时显示实际结果图。UI 验证需要完成任务后的截图、视觉识别与对应真实交互；不能捕获渲染后的回复窗口时报告 `reply_visual_confirmation=incomplete`。文档/软件发布可以总结有限结果，不增加新模型、实机性能或跨 run 资格信用。

英文版是技术权威源。涉及几何时读取 `../../skills/thorlabs-blender-optical-path/references/physical-gates.md`；验收前读取 `evidence-contract.md`；修订旧场景时读取 `history-derived-rules.md`；完整案例见 `project-case-study.md`；整机运行前读取 `end-to-end-workflow.md`；多轮规模/发布资格测试读取 `multi-run-qualification.md`。

## 权威与版本

1. 系统约束优先；随后是用户最新文字或标注截图、项目 active rules、本 skill，最后才是旧产物和旧 PASS。
2. 冻结已提交或验收的包；在活动 revision 中集中处理相关纠正，不覆盖冻结证据，不为每张预览发布新版本。
3. 整机保持一个 run ID、writer、revision、生成器/Blend 谱系和 workflow 账本；副 agent 默认只读，禁止拼接独立写入模块冒充整机完成。
4. 把每个截图问题转换为对象族、世界坐标几何、数值门槛和必需证据。
5. 无法证明时使用 `UNVERIFIED` 或 `BLOCKED`。文件存在、CAD 导入、进程成功、AABB 接触和自报文本都不是证据。

## 核心流程

先区分新测量设计、原图重建、既有场景修正与纯渲染。用户要求“参考旧示例的精度生成另一种光路”时，旧示例只作画质比较，需从空场景建立新拓扑、生成器与资产映射。optics-only 包含光学探测器和机械支撑，排除电路及电气/数据信号可视化。详细要求见[新设计与渲染](../../skills/thorlabs-blender-optical-path/references/fresh-design-and-rendering.md)。

1. 新整机 build 用 `scripts/workflow_ledger.py` 初始化 run spec、状态账本和事件哈希链；局部修订保留原谱系及未完成门的真实状态。
2. 建立 `schematic node -> 实验角色 -> 真实资产 -> 光/光纤/电端口 -> 支撑路径`。
3. 列出全部分支、器件、光束高度、孔径和探测终点。
4. 只从 manifest 锁定的厂家 URL 把官方 CAD 下载到私有缓存；原子落盘前复核 bytes 与 SHA-256，并记录型号、来源、尺度、bbox、局部光轴、法向、孔径、provenance 和再分发边界。替代件必须明示；没有明确授权时禁止公开厂家几何。
5. 把 source lock 与其全部哈希文件当作一个原子输入包；几何前运行 producer-to-consumer artifact preflight，确认 source bytes、CAD canonical/型号别名 key、官方图纸和 runtime 均位于下一脚本实际消费的路径。查找前先按强类型 exact-set 合同验证结构化 authority 输入；missing、duplicate、extra、legacy、malformed 或身份不一致必须生成可持久化的结构化 `BLOCKED`，不得异常退出或静默折叠重复项。
6. 发布脚本必须重算同一语义锁且 difference paths 为零。多状态系统的每条 edge 必须有精确 `active_states` 或哈希化确定型展开，每个 state 都要有明确 ray template。
7. 先解光心、镜面、分束面、反射和分支连续性。设计坐标与保存后重开的真实 mesh/port 测量必须分开；常量零误差和命中同名器件族不足以证明孔径及首碰撞。
8. 再从真实桌孔向上按 post-first 构建紧固件、夹具、holder、post、mount 和器件。
9. 修共享根因，在同一运行内先验一个代表件再传播；保存后重开并逐件复核。
10. 先做明亮的机械/轴向/剖切审计图，再做 beauty render。
11. README/GATE 计数必须来自机器证据；随后在同一账本完成重开、整机 ray/BVH、OpenCV、GLB 回导、二进制/PNG 元数据脱敏、manifest、hash 和全 active-rule 合规矩阵。

光束、柔性光纤和电缆必须是不同对象族，仅生成请求范围内的类别。孔径必须真实开放。删除重复 surrogate 和无角色 placeholder。低成本诊断预览可用于检查器件精度、可见光路与构图，注明尚未闭合的物理证据。物理合格声明须先过物理门；已授权的人工审阅/展示包可在未知明确、physical=false 时完成。保留材质槽与多边形索引语义，逐器件近景和逐分支检查；全图清晰度、边缘密度、颜色像素数不能单独证明建模精度或光束连续。实际 2K 图不能满足 4K 交付要求。

达到用户要求与硬门槛后冻结一次交付；只公开另行授权的范围，只在输入、依赖、runtime 变化或检查失败时复验受影响部分。Skill 文档更新可以记录未通过模型的经验，不能转移模型发布信用。案例数值阈值不得直接成为通用标准。

状态：`PASS` 表示所有适用规则有新鲜证据；`PARTIAL/SCOPED` 只代表局部，必须列出 blocker 且 final/release 保持 false；`UNVERIFIED` 表示证据不足；`BLOCKED` 表示已知失败。禁止把脱敏通过、局部通过或 CAD 导入成功写成整机最终通过。
