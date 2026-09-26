# MiniCheck optional research environment

The lightweight UI and live Flash audit do not import or download MiniCheck. Keep local
model experiments in a separate Python 3.12 environment.

```sh
uv venv .research-venv --python 3.12
uv pip install --python .research-venv -r requirements-research-minicheck.txt --torch-backend auto
uv pip install --python .research-venv --no-deps -e .
```

Activate that environment when running `--method minicheck` or calibration commands; use
the lightweight environment plus `requirements-audit.txt` for Flash experiments. A suitable
CUDA-enabled PyTorch wheel is needed for GPU use. The implementation records the actual device;
it also supports CPU. Model weights are approximately 3.1 GB and cached locally. On Windows
without symlink support temporary/cache duplication can require additional disk space.

Model: [lytang/MiniCheck-Flan-T5-Large](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large),
revision `96eafd01cee2d16cf81aaa2fb226b14f422a37b3`; model card specifies MIT.
Reference implementation: [MiniCheck](https://github.com/Liyan06/MiniCheck),
revision `b58b9fa69acbd1015ec970fa65dd752413a053d2`, Apache-2.0, by Liyan Tang,
Philippe Laban and Greg Durrett. See their [EMNLP paper](https://arxiv.org/abs/2404.10774).

Our small adapter uses the official `predict: document</s>claim` format and first-token logits
3/209, with a binary threshold of 0.5. It deliberately replaces upstream's chunking/truncation
with full-input processing and an explicit 2048-token overflow. This is a documented adapter
configuration, not a reproduction of the authors' published benchmark scores.

The returned `raw_support_score` is a classifier score. It is not a probability of factual,
medical or clinical correctness. Non-support combines contradiction and insufficient evidence;
the adapter does not invent a three-class decision or rationale sentences for this model.

For the same-atom comparison, both Flash and MiniCheck receive the same frozen standalone
normalized fact and source view. The original answer is not appended to the source, since doing
that would let answer text serve as its own evidence. Results therefore depend on faithful
parsing; whole-answer fidelity is a separate task.
