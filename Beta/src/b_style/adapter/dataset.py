from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import json

from transformers import PreTrainedTokenizerBase


REWRITE_SYSTEM = (
    "你是“风格改写器”。你只允许改变表达方式，不允许改变事实信息。\n"
    "硬约束：\n"
    "1) 不得改动任何数字、金额、比例、日期、时间、姓名、公司名、地点。\n"
    "2) 不得新增未在原文出现的事实。\n"
    "3) 不得删除原文中的承诺、要求、交付物、付款节点等关键信息。\n"
    "4) 输出更像用户风格：短段落、适度分点、少 emoji、避免禁用词。\n"
)

def build_prompt(neutral: str) -> str:
    return f"{REWRITE_SYSTEM}\n原文：\n{neutral}\n\n请输出改写后的最终回复（只输出正文，不要解释）："

@dataclass
class PairSample:
    prompt: str
    answer: str


def load_pairs_jsonl(path: str) -> List[PairSample]:
    samples: List[PairSample] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if not obj.get("approved", True):
                continue
            neutral = (obj.get("neutral") or "").strip()
            styled = (obj.get("styled") or "").strip()
            if not neutral or not styled:
                continue
            samples.append(PairSample(prompt=build_prompt(neutral), answer=styled))
    return samples


def tokenize_supervised(
    tokenizer: PreTrainedTokenizerBase,
    prompt: str,
    answer: str,
    max_length: int,
) -> Dict[str, List[int]]:
    """
    SFT：prompt + answer 拼接，labels 只对 answer 部分生效（prompt 部分 = -100）
    """
    # Qwen chat 模型一般 eos_token 可用；pad_token 若缺，用 eos 代替
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    answer_ids = tokenizer.encode(answer + tokenizer.eos_token, add_special_tokens=False)

    input_ids = prompt_ids + answer_ids
    if len(input_ids) > max_length:
        # 保守截断：保留 prompt 尾部 + 全量 answer（尽量不截 answer）
        keep_answer = min(len(answer_ids), max_length // 2)
        answer_ids = answer_ids[-keep_answer:]
        keep_prompt = max_length - len(answer_ids)
        prompt_ids = prompt_ids[-keep_prompt:]
        input_ids = prompt_ids + answer_ids

    labels = [-100] * len(prompt_ids) + answer_ids[:]
    attention_mask = [1] * len(input_ids)

    return {
        "input_ids": input_ids,
        "labels": labels,
        "attention_mask": attention_mask,
    }