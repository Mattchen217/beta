from __future__ import annotations
from dataclasses import dataclass
import torch

@dataclass
class LoraTrainConfig:
    base_model: str = "google/gemma-3-1b-it"
    output_dir: str = "data/style_adapters/user_default/v1"
    train_data_path: str = "data/style_pairs/user_default.jsonl"  # 你自己准备的 approved pairs
    max_length: int = 768

    # LoRA
    r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05

    # Training
    num_train_epochs: int = 2
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.03
    weight_decay: float = 0.0
    logging_steps: int = 10
    save_steps: int = 200
    save_total_limit: int = 2

    bf16: bool = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
    fp16: bool = torch.cuda.is_available() and not bf16

    seed: int = 42