from __future__ import annotations

import torch


class InferenceEngine:
    def __init__(self, model, tokenizer, device="cpu"):
        self.model, self.tokenizer, self.device = model.eval().to(device), tokenizer, device

    @torch.inference_mode()
    def stream(self, prompt: str, max_new_tokens: int = 32):
        tokens = self.tokenizer.encode(prompt)
        if not tokens: raise ValueError("Prompt cannot be empty")
        input_ids = torch.tensor([tokens], device=self.device)
        emitted = 0
        for _ in range(max_new_tokens):
            logits = self.model(input_ids)["logits"][:, -1]
            next_token = logits.argmax(dim=-1, keepdim=True)
            input_ids = torch.cat((input_ids, next_token), dim=1)
            text = self.tokenizer.decode([int(next_token.item())])
            emitted += 1
            yield text
        if emitted == 0: raise RuntimeError("Inference produced a silent empty response")

