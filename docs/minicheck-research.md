# MiniCheck 可选研究环境

[English](en/minicheck-research.md) | **简体中文**

轻量界面和实时 Flash 审计不会导入或下载 MiniCheck。本地模型实验使用独立 Python 3.12 环境。

```sh
uv venv .research-venv --python 3.12
uv pip install --python .research-venv -r requirements-research-minicheck.txt --torch-backend auto
uv pip install --python .research-venv --no-deps -e .
```

运行 `--method minicheck` 或校准命令时激活该环境；Flash 实验使用安装了
`requirements-audit.txt` 的轻量环境。GPU 需要合适的 CUDA PyTorch，程序记录实际设备，也支持 CPU。
权重约 3.1 GB，保存在本地缓存；Windows 不支持符号链接时，临时文件和缓存副本会额外占空间。

模型：[lytang/MiniCheck-Flan-T5-Large](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large)，
revision `96eafd01cee2d16cf81aaa2fb226b14f422a37b3`，模型卡标注 MIT。
参考实现：[MiniCheck](https://github.com/Liyan06/MiniCheck)，
revision `b58b9fa69acbd1015ec970fa65dd752413a053d2`，Apache-2.0，作者 Liyan Tang、
Philippe Laban、Greg Durrett；见 [EMNLP 论文](https://arxiv.org/abs/2404.10774)。

适配器沿用官方 `predict: document</s>claim` 输入及首 token logits 3/209，二分类阈值为 0.5。
它明确改用了完整输入与 2048-token 超限报错，不采用上游分块或截断。因此这是有记录的适配配置，
不是对作者已发表 benchmark 分数的复现。

`raw_support_score` 是分类器分数，不是事实、医学或临床正确概率。非支持合并反驳与信息不足；
适配器不为该模型编造三分类结果或依据原句。

同原子事实比较时，Flash 和 MiniCheck 得到同一冻结的独立规范化事实与来源视图，不把原回答
附加到来源里，避免答案充当自己的证据。因此结果依赖忠实拆解；整段回答保真是另一个任务。
