# Tokage Desktop Pet

一个以《角落生物（Sumikko Gurashi）》中的 Tokage（とかげ）为角色参考制作的桌面宠物资源包。

仓库同时提供两种使用方式：

- 独立桌宠：运行 `python app.py`，或安装 `dist/Tokage-Desktop-Pet-macOS-arm64.dmg`。
- Codex 宠物：把 `assets/codex/tokage/` 导入或复制到 `~/.codex/pets/tokage/`。

## 独立桌宠

需要 Python 3.10+：

```bash
python -m pip install -r requirements.txt
python app.py
```

操作：

- 单击：循环触发挥手、检查、等待动作，同时触发约 22 pt 的回应弹跳、18 个彩色粒子与扩散圆环。
- 双击：触发约 96 pt 的明显抛物线起跳、28 个彩色粒子与三层扩散圆环。
- 拖动：移动桌宠；根据方向切换向左/向右跑动动画。
- 移动鼠标：Tokage 会使用 16 个方向姿态注视指针。
- 闲置休息：Tokage 会自动从站立过渡到完整躺下，安静呼吸一段时间后再起身。
- 静态默认姿态：可选择随机动作、静态站立、静态跳跃、静态躺下、静态挥手或静态等待；选择会跨重启保存。
- 选择静态姿态后，idle 阶段固定显示代表帧；点击、跳跃或拖动动画结束后自动回到该姿态。
- 右键：可直接选择“躺下休息”等互动，以及暂停、自动随机动作、置顶、大小和复位。
- 始终置顶：使用标准 macOS 浮动层级，不再抢占应用焦点或覆盖系统交互；设置会跨重启保存。
- 透明区域穿透：鼠标位于角色透明像素时，点击会传递给下方应用，不阻挡正常 macOS 操作。
- 单实例启动：重复点击应用或再次执行启动命令不会生成第二只宠物，而会显示并提升已经运行的 Tokage。
- 左右拖动：连续播放对应方向的 8 帧跑动动画，改变方向时即时切换。

### macOS 菜单栏控制

应用运行后，macOS 顶部菜单栏会显示 Tokage 图标。单击图标可显示或隐藏桌宠，右键或打开菜单可控制：

- 挥手、明显跳跃、躺下休息、等待、工作、检查、难过、环顾与随机动作
- 静态默认姿态选择（与右键菜单实时同步）
- 暂停/继续及启用自动动作
- 始终置顶（与右键菜单同步并跨重启保存）、75%–150% 显示大小
- 回到右下角、显示/隐藏与退出

应用设置了 `LSUIElement=true`，不会占用 Dock；即使隐藏桌宠，也可通过菜单栏图标或再次点击应用恢复。程序使用本机单实例锁，重复启动不会生成多个桌宠。

独立桌宠直接读取 `assets/codex/tokage/spritesheet.webp`，使用全部 9 个动作行和 16 个方向姿态。

### 打包 macOS 应用与 DMG

需要 macOS、Python 3.10+、Xcode Command Line Tools：

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

输出：

```text
dist/macos/Tokage Desktop Pet.app
dist/Tokage-Desktop-Pet-macOS-arm64.dmg
```

构建脚本完成 PyInstaller 打包、隐藏 Dock 图标、adhoc codesign、`.app` 严格校验、DMG 创建与 `hdiutil verify`。公开分发仍需使用 Apple Developer ID 签名并完成 notarization；adhoc 签名版本适合本机测试和个人使用。

## 导入 Codex

Codex v2 包位于：

```text
assets/codex/tokage/
├── pet.json
└── spritesheet.webp
```

可以手动复制，也可以运行：

```bash
./scripts/install_codex.sh
```

`pet.json` 使用 `spriteVersionNumber: 2`；精灵表为 8×11、单元格 192×208、总尺寸 1536×2288。

## 目录

```text
assets/
├── references/        # 搜索保存的原生 GIF、官方角色图与来源说明
├── standalone/        # 独立桌宠 GIF 与清单
└── codex/tokage/      # 可导入 Codex 的 v2 宠物包
qa/                    # 联系表、方向检查表、动画预览和验证结果
src/                   # 独立桌宠窗口实现
tests/                 # Qt 状态机与交互自动化测试
scripts/build_macos.sh # .app 与 .dmg 构建/验证
```

## 权利说明

Tokage、Sumikko Gurashi 及相关角色形象归 San-X Co., Ltd. 所有。本仓库中的角色素材仅用于个人、非商业桌面宠物实验；请勿将第三方角色素材视为本仓库代码许可的一部分。
