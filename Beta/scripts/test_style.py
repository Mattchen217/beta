from src.b_style.style_profile import StyleProfile
from src.b_style.api import style_rewrite
from src.b_style.adapter.apply import StyleAdapter, LoraAdapterConfig

if __name__ == "__main__":
    profile = StyleProfile()

    # 训练好之后再打开 adapter；没训练好可以先注释掉 adapter 相关
    adapter = StyleAdapter(LoraAdapterConfig(
        base_model_name_or_path="google/gemma-3-1b-it",
        adapter_path="../data/style_adapters/user_default/v1",
        dtype="bfloat16",
    ))

    draft = "我忙忘了"
    res = style_rewrite(
        draft_reply=draft,
        profile=profile,
        intent="customer_support_reply",
        adapter=adapter,
        force=False,
    )

    print("APPLIED:", res.applied, "OK:", res.ok_invariants, "META:", res.meta)
    print("\n--- original ---\n", draft)
    print("\n--- styled ---\n", res.styled_reply)
    print("\n--- diff ---\n", res.diff.to_dict())