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

- 单击：循环触发挥手、检查、等待动作，并显示轻量彩色粒子。
- 双击：触发跳跃和加强版互动粒子。
- 拖动：移动桌宠；根据方向切换向左/向右跑动动画。
- 移动鼠标：Tokage 会使用 16 个方向姿态注视指针。
- 右键：选择 8 种互动、暂停、自动随机动作、置顶、大小和复位。

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
