from __future__ import annotations

from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from ..style_profile import StyleProfile


@dataclass
class LoraAdapterConfig:
    base_model_name_or_path: str = "google/gemma-3-1b-it"
    adapter_path: str = "data/style_adapters/user_default/v1"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    dtype: str = "bfloat16"  # "float16" / "bfloat16" / "float32"
    max_new_tokens: int = 220
    temperature: float = 0.2
    top_p: float = 0.9


class StyleAdapter:
    """
    LoRA rewrite-only adapter for B.
    Uses Qwen chat template + token-slice to avoid prompt-echo.
    """
    def __init__(self, cfg: LoraAdapterConfig):
        self.cfg = cfg
        self.enabled = True

        torch_dtype = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }[cfg.dtype]

        self.tokenizer = AutoTokenizer.from_pretrained(cfg.base_model_name_or_path, use_fast=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            cfg.base_model_name_or_path,
            torch_dtype=torch_dtype,  # ✅ 正确使用 torch_dtype 指定精度
            device_map="auto" if cfg.device != "cpu" else None,
        )
        self.model = PeftModel.from_pretrained(base, cfg.adapter_path)
        self.model.eval()

    def _build_messages(self, draft: str, profile: StyleProfile):
        forbidden = "、".join(profile.lexicon.forbidden_words[:20])
        closings = " / ".join(profile.sign_off.preferred_closings[:3])

        system = (
            "你是“风格改写器”。你只允许改变表达方式，不允许改变事实信息。\n"
            "硬约束：\n"
            "1) 不得改动任何数字、金额、比例、日期、时间、姓名、公司名、地点。\n"
            "2) 不得新增未在原文出现的事实。\n"
            "3) 不得删除原文中的承诺、要求、交付物、付款节点等关键信息。\n"
            f"4) 避免使用这些词：{forbidden}\n"
            "5) 结构偏好：短段落、适度分点、少 emoji。\n"
            f"6) 如需收尾，可用类似：{closings}\n\n"
            "输出要求：只输出改写后的正文；不要复述规则；不要复述原文；不要输出任何提示词。"
        )
        user = f"请把下面这段话改写成目标风格：\n\n{draft}"

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    @torch.inference_mode()
    def rewrite(self, text: str, profile: StyleProfile) -> str:
        messages = self._build_messages(text, profile)

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        out = self.model.generate(
            **inputs,
            max_new_tokens=self.cfg.max_new_tokens,
            do_sample=True,
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
        )

        # ✅ 关键：只取“新生成部分”，避免 prompt 回显
        gen_ids = out[0][inputs["input_ids"].shape[-1]:]
        answer = self.tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

        # ✅ 兜底清理：万一模型仍输出提示词
        for bad in ["原文：", "请输出", "不要解释", "提示词", "输出要求："]:
            if bad in answer:
                answer = answer.split(bad)[-1].strip()

        # 进一步避免出现“空输出”
        return answer if answer else text