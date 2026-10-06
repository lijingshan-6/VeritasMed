# VeritasMed · Navy citation badge

2026-10-06，第 2 版。保留作者参考图中的圆角方块与白色引用 V；根据最新反馈统一字标字体，回到深色 / 青蓝两种品牌色，并恢复原标语。

![VeritasMed](reference/veritasmed-reference-header-light.png)

## 字体与字标

VeritasMed 全部使用 **DM Serif Display Regular**，统一字号 240、统一字重与缩放，不再单独放大 V、压窄后续字母或为 Med 另选字体。只在 s 与 M 的词界增加 7 个设计像素。标语使用 **Inter 400**，文案恢复为 **Medical answers. Evidence you can inspect.**。

这是依据参考图风格重新制作的可编辑矢量字标，并非对图片原字体的确定鉴定。字标与标语全部转为路径，GitHub 展示无需加载字体。

字标保持深色 `#17323B` / 青蓝 `#246F80`，暖白固定背景为 `#FAF9F5`。深色版字标保持浅色 `#F4F5F1` / 提亮青蓝 `#8CC5D0`，固定背景为 `#101C26`。

最终一轮仅按作者红框截图替换图标填色：浅色版的方块 / 括号 / V 分别为 `#17262F` / `#1F6F7A` / `#F4F2EE`；深色版分别为 `#E9EEF0` / `#5FB3BF` / `#0D1117`。单色版保持原样。`reference/badge-color-verification.json` 记录了颜色以外的 SVG 内容与图标外 PNG 像素均未改变的核对结果。

括号笔画从 5/120 加粗到 8/120，V 左侧粗笔与右侧细笔分别加粗，保留对比与衬线起笔。方块按全部文字的实际轮廓计算高度，文字上缘与方块上缘之间、文字下缘与方块下缘之间，均留 12 个设计像素；窄栏版本按没有标语的文字块重新计算。头像与 favicon 继续只用方块。

## 交付

| 使用场景 | 文件 |
|---|---|
| GitHub 浅色与深色主题 | `reference/veritasmed-reference-logo-light.svg` / `logo-dark.svg` |
| 手机与窄栏 | `reference/veritasmed-reference-compact-light.svg` / `compact-dark.svg` |
| 独立图标 | `reference/veritasmed-reference-mark-light.svg` / `mark-dark.svg` |
| favicon 与小图标 | `reference/veritasmed-reference-small-light.svg` / `small-dark.svg` |
| 头像 | `reference/veritasmed-reference-avatar-light.png` / `avatar-dark.png` |
| 固定底色展示 | `reference/veritasmed-reference-header-light.png` / `header-dark.png` |
| 单色 | `reference/veritasmed-reference-logo-mono.svg` / `mark-mono.svg` |

横版 SVG 为 2160 × 720，PNG 为 4320 × 1440。头像 SVG 为 512 × 512，PNG 为 1024 × 1024；PNG 的圆角外保留透明背景。清单 `reference/asset-manifest.json` 记录尺寸、字节数与 SHA-256。

预览页为 `preview.html`：在本目录运行 `python -m http.server`，再打开 `/preview.html`。早期草稿版本没有收入本仓库。网页应用使用的贴边横标与 favicon 位于 `frontend/public/brand/`，由本目录的 compact 与 small 文件直接派生（只改显示范围，图形不变）。

## 字体来源与生成源

字体来自 Google Fonts 官方仓库，使用 SIL Open Font License。完整许可保存在 `source/dmserifdisplay-OFL.txt` 与 `source/inter-OFL.txt`。Montserrat 仍保留，供旧版重建使用。

- [DM Serif Display](https://github.com/google/fonts/tree/main/ofl/dmserifdisplay)
- [Inter](https://github.com/google/fonts/tree/main/ofl/inter)

生成源：`source/build_reference.py`；栅格导出：`source/render_reference.cjs`；校验：`source/verify_reference.py`。项目图形与组合遵循仓库 Apache-2.0 许可，字体仍遵循各自 OFL 许可。
