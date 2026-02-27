# HetaiAI Beta (ABC)

本项目是你拍板的 Beta 最小闭环：

**A（取证据） → B（基于证据生成回答） → C（adapter 风格润色）**

- A：本地记忆检索（向量 + BM25 融合），输出 evidence（conv_id / time_range / msg_ids / snippet / score）
- B：`Qwen/Qwen2.5-3B-Instruct`（base，不带 LoRA）严格基于 evidence 生成“像助手”的回答，并输出“依据”
- C：风格层（规则 + 可选 LoRA adapter），只改表达，不改事实；QA 场景默认关闭 sign_off，避免乱加尾巴

## 1) 运行（交互测试）

```bash
python scripts/test_agent_abc.py
```

示例问题：
- 客户A之前问过报价包含什么吗？
- 合同v2是在哪个会话发的？
- 我三天前跟谁说过报价20万？

## 2) 索引构建（A）

如果你更换/新增语料，需要先 rebuild：

```bash
python -m src.a_memory.index_build
```

或直接运行你原来的 ingest/build 脚本流程。

## 3) 训练风格 adapter（可选）

准备 `data/style_pairs/<user>.jsonl` 后：

```bash
python scripts/train_style_adapter.py
```

训练产物默认写到 `data/style_adapters/user_default/v1`

## 4) 重要说明（Beta 的“可控性”）

- B 的 LLM 生成 **必须**受 evidence 约束（prompt 已强制）
- C 的 adapter **只做表达润色**，并有 invariant check；失败会回滚到 rule-only/original
