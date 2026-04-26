from pathlib import Path
from typing import Dict, Any
import json
from .llm_client import OpenAIClient
from .prompt_builder import PromptBuilder
from .schemas import RequirementAnalysis


class RequirementAnalyzer:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or OpenAIClient()
        self.prompt_builder = PromptBuilder()

    async def analyze_markdown_file(self, file_path: str) -> RequirementAnalysis:
        with open(file_path, 'r', encoding='utf-8') as f:
            requirement_text = f.read()
        
        return await self.analyze_text(requirement_text)

    async def analyze_text(self, requirement_text: str) -> RequirementAnalysis:
        prompt = self.prompt_builder.build_prompt(requirement_text)
        analysis = await self.llm_client.analyze_requirement(prompt)
        return analysis

    def save_analysis_json(self, analysis: RequirementAnalysis, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis.model_dump(), f, indent=2, ensure_ascii=False)
