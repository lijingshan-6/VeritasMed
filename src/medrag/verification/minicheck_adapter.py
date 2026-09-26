"""Pinned optional MiniCheck inference; no silent truncation or clinical probabilities.

Uses the official Flan-T5 predict/eos format and logits [3, 209].
Upstream reference: Liyan06/MiniCheck b58b9fa69acbd1015ec970fa65dd752413a053d2
(Apache-2.0). Model: lytang/MiniCheck-Flan-T5-Large (MIT).
This adapter deliberately scores full inputs up to 2048 tokens and fails explicitly beyond
that, rather than using upstream's whitespace chunking and silent tokenizer truncation.
"""

import time

MODEL = "lytang/MiniCheck-Flan-T5-Large"
REVISION = "96eafd01cee2d16cf81aaa2fb226b14f422a37b3"
MAX_LENGTH = 2048


class MiniCheckAdapter:
    def __init__(self, cache_dir=".benchmark-runtime/v06-models", device=None):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL, revision=REVISION, cache_dir=cache_dir
        )
        self.model = (
            AutoModelForSeq2SeqLM.from_pretrained(
                MODEL,
                revision=REVISION,
                cache_dir=cache_dir,
                torch_dtype=torch.float32,
            )
            .to(self.device)
            .eval()
        )
        self.settings = {
            "model": MODEL,
            "revision": REVISION,
            "device": self.device,
            "precision": "float32",
            "max_input_tokens": MAX_LENGTH,
            "overflow": "execution failure, no truncation or auto-chunking",
            "input": "title + newline + complete abstract; predict: doc</s>claim",
            "binary_threshold": 0.5,
            "score": "raw_support_score, not truth probability",
        }

    def score(self, document: str, claim: str):
        started = time.perf_counter()
        record = {
            "status": "execution_error",
            "raw_support_score": None,
            "binary_prediction": None,
            "usage": None,
            "error_type": None,
            "model": MODEL,
            "revision": REVISION,
        }
        try:
            inputs = self.tokenizer(
                "predict: " + document + self.tokenizer.eos_token + claim,
                return_tensors="pt",
                truncation=False,
            )
            n = inputs["input_ids"].shape[1]
            record["input_tokens"] = n
            if n > MAX_LENGTH:
                record.update(status="input_overflow", error_type="FullInputExceedsLimit")
            else:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                with self.torch.inference_mode():
                    output = self.model(
                        **inputs,
                        decoder_input_ids=self.torch.zeros(
                            (1, 1), dtype=self.torch.long, device=self.device
                        ),
                    )
                    score = self.torch.softmax(output.logits[0, 0, [3, 209]].float(), dim=-1)[
                        1
                    ].item()
                record.update(
                    status="ok", raw_support_score=score, binary_prediction=int(score > 0.5)
                )
        except Exception as exc:
            record["error_type"] = type(exc).__name__
        record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        return record

    def verify(self, item):
        return {
            "case_id": item.case_id,
            **self.score(item.document.title + "\n" + item.document.canonical_text, item.claim),
        }
