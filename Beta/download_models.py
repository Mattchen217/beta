from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    base_dir = Path(r"D:\TTLLAMA\Beta")
    models_dir = base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    models = {
        "google/gemma-3-1b-it": models_dir / "gemma-3-1b-it",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": models_dir / "paraphrase-multilingual-MiniLM-L12-v2",
    }

    for repo_id, local_dir in models.items():
        print(f"Downloading {repo_id} to {local_dir} ...", flush=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )

    print("All models downloaded.")


if __name__ == "__main__":
    main()

