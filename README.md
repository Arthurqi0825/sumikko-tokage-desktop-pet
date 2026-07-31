# Tokage Desktop Pet

一个以《角落生物（Sumikko Gurashi）》中的 Tokage（とかげ）为角色参考制作的桌面宠物资源包。

仓库同时提供两种使用方式：

- 原生 macOS 独立桌宠（推荐）：安装 `dist/Tokage-Desktop-Pet-Swift-macOS-universal.dmg`，或用 Xcode 打开 `macos-swift/TokageDesktopPet.xcodeproj`。
- Codex 宠物：把 `assets/codex/tokage/` 导入或复制到 `~/.codex/pets/tokage/`。

## 原生 Swift 独立桌宠

原生版使用 Swift + AppKit，最低支持 macOS 13，同时包含 Apple Silicon 与 Intel 架构。应用包不包含 Python、PySide、Qt 或 Python runtime，当前 Release 应用约 3.5 MB。

安装：打开以下 DMG，把 `Tokage Desktop Pet.app` 拖入 `Applications`：

```text
dist/Tokage-Desktop-Pet-Swift-macOS-universal.dmg
```

由于当前没有 Apple Developer ID，DMG 内应用采用 adhoc 签名。它可以上传到 GitHub Releases；其他设备首次启动时可能需要右键应用选择“打开”，或在“系统设置 → 隐私与安全性”中允许。消除 Gatekeeper 提示需要 Developer ID 签名和 Apple notarization。

### Xcode 测试

1. 打开 `macos-swift/TokageDesktopPet.xcodeproj`。
2. 选择 `TokageDesktopPet` scheme 和 `My Mac`。
3. 按 `Command + R`。

工程最低部署目标为 macOS 13，可在 Xcode 中直接 Debug/Release；无第三方包管理器和 Python 环境依赖。

操作：

- 单击：循环触发挥手、检查、等待动作，同时触发约 22 pt 的回应弹跳、18 个彩色粒子与扩散圆环。
- 双击：触发约 96 pt 的明显抛物线起跳、28 个彩色粒子与三层扩散圆环。
- 拖动：移动桌宠；根据方向切换向左/向右跑动动画。
- 移动鼠标：Tokage 会使用 16 个方向姿态注视指针。
- 闲置休息：Tokage 会自动从站立过渡到完整躺下，安静呼吸一段时间后再起身。
- 静态默认姿态：可选择随机动作、静态站立、静态跳跃、静态躺下、静态挥手或静态等待；选择会跨重启保存。
- 选择静态姿态后，idle 阶段固定显示代表帧；点击、跳跃或拖动动画结束后自动回到该姿态。
- 右键：可直接选择“躺下休息”等互动，以及暂停、自动随机动作、置顶、大小和复位。
- 始终置顶：使用原生高窗口层级，不抢占键盘焦点；默认保持在普通窗口之上，设置会跨重启保存。
- 多桌面与全屏：透明 `NSPanel` 使用 `canJoinAllSpaces + fullScreenAuxiliary + stationary`，可加入所有 macOS Spaces，并显示在全屏应用空间中。
- 图标统一：Finder、应用包与顶部菜单栏控制均使用同一个 `assets/app-icon.icns` 彩色 Tokage 图标。
- 透明区域穿透：鼠标位于角色透明像素时，点击会传递给下方应用，不阻挡正常 macOS 操作。
- 单实例启动：重复点击应用或再次执行启动命令不会生成第二只宠物，而会显示并提升已经运行的 Tokage。
- 左右拖动：连续播放对应方向的 8 帧跑动动画，改变方向时即时切换。
- 动画速度：全部动作已采用更舒适的默认节奏；右键菜单和菜单栏均可用滑动条在 50%–200% 间连续调整，设置会跨重启保存。
- 自定义大小：右键菜单和菜单栏均提供 10%–200% 滑动条，并保留常用快捷档位；设置会跨重启保存。

### macOS 菜单栏控制

应用运行后，macOS 顶部菜单栏会显示 Tokage 图标。单击图标可显示或隐藏桌宠，右键或打开菜单可控制：

- 挥手、明显跳跃、躺下休息、等待、工作、检查、难过、环顾与随机动作
- 静态默认姿态选择（与右键菜单实时同步）
- 暂停/继续及启用自动动作
- 始终置顶（与右键菜单同步并跨重启保存）
- 50%–200% 动画速度、10%–200% 桌宠大小滑动条
- 回到右下角、显示/隐藏与退出

应用设置了 `LSUIElement=true`，不会占用 Dock；即使隐藏桌宠，也可通过菜单栏图标或再次点击应用恢复。程序使用本机单实例锁，重复启动不会生成多个桌宠。

原生独立桌宠从 App Bundle 读取 `spritesheet.webp`，使用全部 9 个动作行和 16 个方向姿态。

### 编辑动画基准速度

日常使用直接调整“动画速度”滑动条即可。如果要修改程序的出厂节奏，可编辑 `macos-swift/Sources/PetConstants.swift` 中各动作的 `intervalMilliseconds`：数值越大动作越慢。运行时实际间隔为 `intervalMilliseconds ÷ 动画速度倍率`，因此 50% 会播放为两倍时长，200% 会播放为一半时长。

### 打包 macOS 应用与 DMG

需要 macOS 和完整 Xcode：

```bash
./macos-swift/scripts/build_dmg.sh
```

输出：

```text
dist/swift/Tokage Desktop Pet.app
dist/Tokage-Desktop-Pet-Swift-macOS-universal.dmg
```

构建脚本完成 Universal 2 Release 编译、隐藏 Dock 图标、adhoc codesign、原生运行时自测、Python/Qt 缺失检查、DMG 创建和 `hdiutil verify`。可继续执行 `./macos-swift/scripts/validate_dmg.sh`，验证从 DMG 挂载、复制到新位置后仍能正常启动。

旧 Python/PySide 实现仍保留为迁移参考，可运行 `python app.py` 或执行 `scripts/build_macos.sh` 构建旧版；GitHub Release 应优先使用新的 Swift Universal 2 DMG。

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
macos-swift/           # Swift/AppKit 源码、Xcode 工程、自测与 DMG 脚本
src/                   # 独立桌宠窗口实现
tests/                 # Qt 状态机与交互自动化测试
scripts/build_macos.sh # .app 与 .dmg 构建/验证
```

## 权利说明

Tokage、Sumikko Gurashi 及相关角色形象归 San-X Co., Ltd. 所有。本仓库中的角色素材仅用于个人、非商业桌面宠物实验；请勿将第三方角色素材视为本仓库代码许可的一部分。
