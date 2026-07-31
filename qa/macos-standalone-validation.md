# macOS 独立桌宠验证报告

验证日期：2026-07-31

## 结论

- 本机独立运行：通过
- `.app` 打包与启动：通过
- DMG 创建、挂载与只读校验：通过
- 单击、双击、拖动、右键菜单与多动作状态机：通过
- 透明、无边框、始终置顶、Tool Window：通过
- 公开互联网分发的 Gatekeeper/Notarization：未完成（当前为 adhoc 签名）

## 验证环境

- macOS 26.5（Build 25F71）
- Apple Silicon arm64
- Python 3.12.5
- PySide6 6.11.1
- PyInstaller 6.21.0

## 自动化验证

`python -m unittest discover -s tests -v`：7/7 通过。

覆盖：

- 1536×2288 v2 图集加载
- 9 个标准动作状态与帧推进
- 16 个方向姿态映射
- 单击互动与粒子效果
- 双击跳跃，以及双击不穿透为单击
- 暂停/继续、自动动作、置顶、75%–150% 缩放
- 右键菜单和 8 项互动动作

最终 DMG 内 `.app` 在真实 Cocoa 窗口运行 `--self-test-output`：`all_passed: true`。完整结果见 `macos-self-test.json`。

## 产物验证

- `.app`：100 MB
- DMG：42 MB
- 主可执行文件：Mach-O 64-bit arm64
- `LSUIElement=true`：不占用 Dock
- `codesign --verify --deep --strict`：通过
- `hdiutil verify`：VALID
- DMG SHA-256：`6417a6dbac759fe7dd6bdfbd35415b6563ca47a79b2c35d6427c76eb5eec3390`
- DMG 挂载内容：`Tokage Desktop Pet.app` 与 `Applications` 快捷方式

## 签名说明

当前构建使用 adhoc codesign，保证包内完整性，但没有 Apple Developer ID 与 notarization。因此 `spctl` 拒绝属于预期结果；个人本机测试可右键选择“打开”。若要公开分发，需要配置 Developer ID Application 证书，对 `.app` 签名，提交 Apple notarization，再执行 stapling。
