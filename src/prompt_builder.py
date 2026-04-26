from pathlib import Path
from typing import Optional


class PromptBuilder:
    def __init__(self, prompt_template_path: Optional[str] = None):
        if prompt_template_path is None:
            prompt_template_path = Path(__file__).parent.parent / "prompts" / "requirement_analysis_prompt.md"
        
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            self.template = f.read()

    def build_prompt(self, requirement_text: str) -> str:
        return self.template.replace("{{REQUIREMENT_TEXT}}", requirement_text)
