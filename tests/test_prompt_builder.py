from pathlib import Path

from src.prompt_builder import PromptBuilder


def test_prompt_builder_inserts_requirement_text(tmp_path: Path):
    template = "Header\n{{REQUIREMENT_TEXT}}\nFooter\n"
    template_path = tmp_path / "template.md"
    template_path.write_text(template, encoding="utf-8")

    builder = PromptBuilder(prompt_template_path=str(template_path))

    requirement_text = "# Title\n\nSome requirement text."
    prompt = builder.build_prompt(requirement_text)

    assert "{{REQUIREMENT_TEXT}}" not in prompt
    assert requirement_text in prompt
    assert prompt.startswith("Header")
    assert prompt.rstrip().endswith("Footer")
