from __future__ import annotations

import os
import random
import torch
from typing import List, Dict, Any

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    set_seed,
)
from peft import LoraConfig, get_peft_model, TaskType

from .config import LoraTrainConfig
from .dataset import load_pairs_jsonl, tokenize_supervised


def _guess_target_modules(_: str) -> list[str]:
    # Qwen2.5 常见投影层名
    return ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


class _TorchDataset(torch.utils.data.Dataset):
    def __init__(self, rows: List[Dict[str, Any]]):
        self.rows = rows
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, idx):
        return self.rows[idx]


def _collate(features: List[Dict[str, Any]], pad_token_id: int):
    """
    手写 collate，保证：
    - input_ids pad 到同长度
    - attention_mask pad 0
    - labels pad -100
    """
    max_len = max(len(x["input_ids"]) for x in features)

    input_ids = []
    attention_mask = []
    labels = []

    for x in features:
        ids = x["input_ids"]
        mask = x["attention_mask"]
        lab = x["labels"]

        pad_len = max_len - len(ids)

        input_ids.append(ids + [pad_token_id] * pad_len)
        attention_mask.append(mask + [0] * pad_len)
        labels.append(lab + [-100] * pad_len)

    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def train_lora(cfg: LoraTrainConfig):
    os.makedirs(cfg.output_dir, exist_ok=True)
    set_seed(cfg.seed)

    tokenizer = AutoTokenizer.from_pretrained(cfg.base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    pad_token_id = tokenizer.pad_token_id

    dtype = torch.bfloat16 if cfg.bf16 else (torch.float16 if cfg.fp16 else torch.float32)

    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model,
        torch_dtype=dtype,                # ✅ 正确使用 torch_dtype 指定精度
        device_map="auto",
    )
    model.gradient_checkpointing_enable()

    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=cfg.r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=_guess_target_modules(cfg.base_model),
        bias="none",
    )
    model = get_peft_model(model, lora)

    # 读取 approved pairs
    pairs = load_pairs_jsonl(cfg.train_data_path)
    if len(pairs) < 10:
        raise ValueError(
            f"Not enough approved training pairs: {len(pairs)}. "
            f"Please set approved=true for enough samples in {cfg.train_data_path}."
        )

    random.shuffle(pairs)
    rows = [tokenize_supervised(tokenizer, p.prompt, p.answer, cfg.max_length) for p in pairs]
    train_ds = _TorchDataset(rows)

    # ✅ 用 warmup_steps 替代 warmup_ratio（避免 deprecated warning）
    total_steps = max(1, (len(train_ds) // max(1, cfg.per_device_train_batch_size)) * cfg.num_train_epochs)
    warmup_steps = int(total_steps * 0.03)  # 等价于 warmup_ratio=0.03

    args = TrainingArguments(
        output_dir=cfg.output_dir,
        num_train_epochs=cfg.num_train_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        learning_rate=cfg.learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=cfg.weight_decay,
        logging_steps=cfg.logging_steps,
        save_steps=cfg.save_steps,
        save_total_limit=cfg.save_total_limit,
        bf16=cfg.bf16,
        fp16=cfg.fp16,
        report_to=[],
        optim="adamw_torch",
        lr_scheduler_type="cosine",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        data_collator=lambda feats: _collate(feats, pad_token_id),
    )

    trainer.train()

    # 保存 adapter（只保存 LoRA 权重）
    model.save_pretrained(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)

    print(f"[OK] LoRA adapter saved to: {os.path.abspath(cfg.output_dir)}")


if __name__ == "__main__":
    cfg = LoraTrainConfig()
    train_lora(cfg)