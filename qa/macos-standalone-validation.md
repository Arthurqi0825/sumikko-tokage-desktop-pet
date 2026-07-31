# macOS 独立桌宠验证报告

验证日期：2026-07-31

## 结论

- 本机独立运行：通过
- `.app` 打包与启动：通过
- DMG 创建、挂载与只读校验：通过
- 单击、双击、拖动、右键菜单与多动作状态机：通过
- 明显起跳与落地复位：通过（默认尺寸峰值 96 pt）
- 自动躺卧休息、呼吸循环与起身复位：通过
- 明显点击反馈：通过（22 pt 回应弹跳、18/28 粒子、2/3 层扩散圆环）
- 静态默认姿态、持久化及右键/菜单栏同步：通过
- 左右拖动连续跑动动画：通过
- macOS 菜单栏图标与控制菜单：通过
- 透明、无边框、始终置顶、Tool Window：通过
- 公开互联网分发的 Gatekeeper/Notarization：未完成（当前为 adhoc 签名）

## 验证环境

- macOS 26.5（Build 25F71）
- Apple Silicon arm64
- Python 3.12.5
- PySide6 6.11.1
- PyInstaller 6.21.0

## 自动化验证

`python -m unittest discover -s tests -v`：13/13 通过。

覆盖：

- 1536×2288 v2 图集加载
- 9 个标准动作状态与帧推进
- 16 个方向姿态映射
- 单击互动与粒子效果
- 双击触发约 96 pt 抛物线起跳并准确落回原位
- 单击触发约 22 pt 回应弹跳、18 个粒子和两层扩散圆环
- 双击触发 28 个粒子和三层扩散圆环
- 闲置或菜单操作触发站立→躺下→呼吸休息→起身→待机完整状态机
- 拖动期间取消跳跃位移，避免窗口位置漂移
- 高频拖动事件不会重置帧计时器，左右 8 帧跑动动画持续推进
- 默认姿态支持随机、静态站立、静态跳跃、静态躺下、静态挥手与静态等待
- 静态 idle 使用固定代表帧并停止帧计时器，互动完成后恢复所选姿态
- 默认姿态使用 QSettings 跨重启保存，并在右键菜单和菜单栏组件同步勾选
- 暂停/继续、自动动作、置顶、75%–150% 缩放
- 右键菜单、互动动作和默认动作选择
- macOS 菜单栏图标及显示/隐藏、躺下休息、互动、暂停、随机动作、置顶、缩放、复位与退出控制

最终 DMG 内 `.app` 在真实 Cocoa 窗口运行 `--self-test-output`：`all_passed: true`。菜单栏组件在 Cocoa 环境中报告 `available: true`、`visible: true`，完整结果见 `macos-self-test.json`。

## 产物验证

- 版本：1.4.0（bundle 5）
- `.app`：100 MB
- DMG：42 MB
- 主可执行文件：Mach-O 64-bit arm64
- `LSUIElement=true`：不占用 Dock，由菜单栏组件承担常驻控制
- `codesign --verify --deep --strict`：通过
- `hdiutil verify`：VALID
- DMG SHA-256：`c22e8624a8f22fc9fd40121b9ec8b71882d96eb763bb8890539bb573b45a3348`
- DMG 挂载内容：`Tokage Desktop Pet.app` 与 `Applications` 快捷方式

## 签名说明

当前构建使用 adhoc codesign，保证包内完整性，但没有 Apple Developer ID 与 notarization。因此 `spctl` 拒绝属于预期结果；个人本机测试可右键选择“打开”。若要公开分发，需要配置 Developer ID Application 证书，对 `.app` 签名，提交 Apple notarization，再执行 stapling。
