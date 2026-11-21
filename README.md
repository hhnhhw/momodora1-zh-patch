# Momodora 1 汉化补丁

**Momodora 1.51 简体中文非官方补丁 · v0.1 测试版**

本仓库只提供汉化补丁、翻译表和制作工具，**不含原版游戏、整合版 EXE、游戏音频、存档或反编译工程**。请自行从[原作者页面](https://rdein.itch.io/momodora-i)取得游戏。

> 测试版，不代表完成全流程通关回归。游戏及原素材版权属于原作者；本项目并非官方发布，也不表示已取得官方授权。

## 汉化范围

共 **91 条翻译/显示映射**：

- 开始提示、主菜单、最佳时间、计时 HUD 与保存提示；
- 新游戏序章的三段叙述；
- 已识别的普通 NPC、武器教程、首领及结局母亲对白；
- 暂停界面 15 项物品的名称和说明（30 条）；
- 片尾职务、部分鸣谢说明与出品文字。

保留原作者和参与者姓名、署名与版权文字。图片内烘焙文字、Logo、引擎错误弹窗及开发测试房间文字不在本版承诺范围内。

## 安装

### 方法一：复制补丁到游戏目录

1. 从 GitHub 下载本仓库 ZIP 并解压。
2. 将 `Momo1_151_Chinese_Patch` 文件夹和 `启动中文测试版.cmd` 复制到原版 `momo1_v151.exe` 所在目录。
3. 安装 [Python 3](https://www.python.org/downloads/)（3.9 或更高；安装器只用标准库）。
4. 双击 `Momo1_151_Chinese_Patch/安装汉化.cmd`。
5. 双击游戏目录中的 `启动中文测试版.cmd`，或运行生成的 `momo1_v151_zh.exe`。

**运行已生成的汉化游戏不需要 Python，也不需要安装字体。** 请保留游戏全部原资源，以及新增的 `data/graphic/momo1_zh_text.png`；不要单独移动汉化 EXE。

### 方法二：从克隆目录指定游戏位置

```powershell
git clone https://github.com/hhnhhw/momodora1-zh-patch.git
cd momodora1-zh-patch
py -3 Momo1_151_Chinese_Patch/apply_patch.py --game-dir "D:\你的游戏目录"
```

只检查，不写文件：

```powershell
py -3 Momo1_151_Chinese_Patch/apply_patch.py --game-dir "D:\你的游戏目录" --check
```

## 支持版本

仅支持经以下 SHA-256 确认的 Windows **Momodora 1.51** 原版：

```text
momo1_v151.exe
3,013,668 字节
97b6419b3def0f9133a6b1322d113f3ed22b395fbf5d3eaa6dd8dc2dd406e84a
```

错误版本或已修改的原版会被拒绝。安装器不联网、不覆盖原版 EXE，不修改原配置与存档；再次安装相同版本可重复执行。

## 卸载

```powershell
py -3 Momo1_151_Chinese_Patch/apply_patch.py --game-dir "D:\你的游戏目录" --remove
```

也可运行游戏目录补丁文件夹里的 `卸载汉化.cmd`。卸载仅删除校验匹配的汉化 EXE、中文图集及安装记录。运行原版 `momo1_v151.exe` 即可回到英文。

中英文共用原存档路径 `data/saves/slot1`。尽管补丁不更改游戏 ID 与存档结构，**切换前仍建议自行备份**，因为尚未完成所有存读档回归。

## 已完成验证

- 原版解包与无改动回包；汉化 EXE 读回一致性；引擎前缀保持不变。
- 安装、重复安装、只读检查、卸载、错误版本拒绝、未知文件保护，共 6 项安装器测试。
- 在 Windows 实际启动原版与汉化版，进入第一游戏场景并打开物品栏。
- 中文开始提示、三项菜单、序章三段与“魔法叶”物品名/说明，共 7 项实际截图字形匹配检查通过；序章淡入透明度保留。

**未完成**全流程通关、全部首领/结局路线、全部道具、全部缩放与完整存读档回归。测试报告位于补丁目录的 `build_report.json`、`installer_test_report.json`、`runtime_test_report.json`。

## 实现方式

原版使用 Game Maker 7，逐字节绘制文字。为避免 UTF-8/GBK 乱码，本补丁：

1. 固定校验原版 EXE，解压/解混淆定版游戏资源；
2. 使用原本空闲的脚本槽加入文字绘制代理；
3. 根据原英文文本查找预渲染中文图集；
4. 保留原对话条件、分页、数值及英文回退逻辑；
5. 重新封装为独立 `_zh.exe`，原版不动。

图集采用旧引擎兼容的黑色色键透明。不安装 DLL，不改系统区域、打印机或安全软件设置。

## 修改译文

- `Momo1_151_Chinese_Patch/texts.json`：翻译表。
- `Momo1_151_Chinese_Patch/tools/build_patch.py`：渲染图集、生成补丁清单与本地汉化 EXE。
- `Momo1_151_Chinese_Patch/tools/gm7.py`：本定版专用的资源读取/重封装工具。
- `Momo1_151_Chinese_Patch/apply_patch.py`：仅用 Python 标准库的安装/卸载工具。

重新构建需要 Pillow，以及构建器当前指定的 Windows 黑体字形。仓库没有分发字体文件；若更换构建字体，请自行确认字形使用与分发权限。构建器默认要求补丁目录的上级有原版游戏，并拒绝覆盖已存在的汉化 EXE。直接编辑 JSON 不会即时改变已经生成的游戏，必须同步重建图集和清单。

完整操作说明见 [使用说明](Momo1_151_Chinese_Patch/使用说明.md)。

## 权利与发布边界

请阅读 [NOTICE.md](NOTICE.md)。本仓库不授权重新发布或出售原游戏、整合 EXE、原始素材、反编译工程或字体文件。原文、游戏名称与第三方字形等权利仍归各自权利人。公开可访问不等于获得游戏、翻译或字形的再分发授权；如有权利问题，请通过 Issue 联系维护者。
