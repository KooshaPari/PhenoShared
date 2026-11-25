"""Quickstart: pheno-llms-txt

Run with::

    python examples/quickstart.py

Writes ``./out/llms.txt`` next to this file using an inline LlmConfig.
"""

from pathlib import Path

from phenotype_py_extras.llms_txt.core import LlmConfig, init_llms, render, write_llms_txt


def render_inline_config() -> str:
    """Build an LlmConfig in-memory and return the rendered llms.txt string."""
    cfg = LlmConfig(
        repo_name="pheno-llms-txt-demo",
        tagline="Quickstart demo for pheno-llms-txt.",
        install=["pip install pheno-llms-txt"],
        usage=["pheno-llms-txt", "pheno-llms-txt --out docs/llms.txt"],
        public_api=["pheno_llms_txt.LlmConfig", "pheno_llms_txt.render"],
        common_errors=[
            ["No such file: pheno-llms-txt.yaml", "file is optional; create one"],
            ["parse YAML error", "check YAML syntax; all fields are optional"],
        ],
        references=["https://llmstxt.org"],
    )
    return render(cfg)


def write_to_disk(out_dir: Path) -> Path:
    """Materialize llms.txt in out_dir via the scaffold-kit entrypoint."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = LlmConfig(
        repo_name=out_dir.name,
        tagline="Quickstart scaffold.",
        install=[f"pip install {out_dir.name}"],
        usage=[f"{out_dir.name} --help"],
        public_api=[],
        common_errors=[],
        references=["https://llmstxt.org"],
    )
    dest = out_dir / "llms.txt"
    write_llms_txt(cfg, dest)
    return dest


def main() -> None:
    text = render_inline_config()
    print(text)
    print("---")
    dest = write_to_disk(Path(__file__).parent / "out")
    print(f"wrote {dest}")
    # Scaffold-kit entrypoint: idempotent, returns {"ok": bool, ...}.
    print(init_llms(Path(__file__).parent / "out"))


if __name__ == "__main__":
    main()