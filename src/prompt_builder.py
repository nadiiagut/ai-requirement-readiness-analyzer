from pathlib import Path
from typing import Optional

from .context_loader import DomainContext, load_context


class PromptBuilder:
    def __init__(self, prompt_template_path: Optional[str] = None):
        if prompt_template_path is None:
            prompt_template_path = Path(__file__).parent.parent / "prompts" / "requirement_analysis_prompt.md"
        
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            self.template = f.read()

    def build_prompt(
        self,
        requirement_text: str,
        domain_context: Optional[str] = None
    ) -> str:
        """
        Build the analysis prompt with optional domain context.
        
        Args:
            requirement_text: The requirement to analyze
            domain_context: Optional domain context name (e.g., 'control_panel')
        
        Returns:
            Complete prompt string with context injected
        """
        prompt = self.template.replace("{{REQUIREMENT_TEXT}}", requirement_text)
        
        # Load and inject domain context
        context = load_context(domain_context)
        context_section = context.to_prompt_section()
        
        if context_section.strip():
            # Insert context before the requirement
            prompt = prompt.replace(
                "{{REQUIREMENT_TEXT}}",
                requirement_text
            )
            # Add context section after system instructions but before requirement
            if "## Requirement to Analyze" in prompt:
                prompt = prompt.replace(
                    "## Requirement to Analyze",
                    f"{context_section}\n## Requirement to Analyze"
                )
            else:
                # Fallback: prepend context to requirement
                prompt = prompt.replace(
                    requirement_text,
                    f"{context_section}\n\n{requirement_text}"
                )
        
        return prompt
