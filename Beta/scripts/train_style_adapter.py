from pathlib import Path

from src.b_style.adapter.config import LoraTrainConfig
from src.b_style.adapter.train import train_lora

# ===== 自动定位项目根目录 =====
BASE_DIR = Path(__file__).resolve().parents[1]   # scripts/ 的上一层 = project root
DATA_DIR = BASE_DIR / "data"

if __name__ == "__main__":
    cfg = LoraTrainConfig(
        base_model="google/gemma-3-1b-it",

        # ⭐ 用绝对路径（推荐）
        train_data_path=str(DATA_DIR / "style_pairs" / "zhao_shuang.approved.jsonl"),
        output_dir=str(DATA_DIR / "style_adapters" / "user_default" / "v1"),

        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        num_train_epochs=2,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
    )

    print("Training data:", cfg.train_data_path)
    print("Output dir:", cfg.output_dir)

    train_lora(cfg)