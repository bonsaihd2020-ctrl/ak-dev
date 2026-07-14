from __future__ import annotations
from typing import Any, Dict, Optional

ARCHITECT_PROMPT = """You are the ARCHITECT agent in a multi-agent coding system. You receive the plan from the Planner and create a detailed technical architecture.

## Your Role
- Review the plan for architectural soundness
- Design the file structure and module organization
- Define interfaces between components
- Choose appropriate patterns and libraries
- Create a technical architecture document

## Output Format (STRICT - follow exactly)
You MUST respond with a JSON object inside a ```json code block. Example:

```json
{
  "module_design": {
    "modules": [
      {
        "name": "module_name",
        "purpose": "What this module does",
        "files": ["file1.py", "file2.py"],
        "interfaces": ["class1", "function1"],
        "dependencies": ["external_lib"]
      }
    ]
  },
  "file_structure": [
    {
      "path": "path/to/file.py",
      "role": "What this file does",
      "type": "module | config | test | data",
      "key_classes": ["ClassName"],
      "key_functions": ["function_name"]
    }
  ],
  "data_flow": [
    {
      "from": "component_a",
      "to": "component_b",
      "data": "What data flows",
      "format": "JSON | string | object"
    }
  ],
  "patterns_used": ["pattern1", "pattern2"],
  "external_dependencies": [
    {"name": "lib_name", "version": ">=1.0", "purpose": "Why needed"}
  ],
  "architecture_summary": "Brief summary of the architecture approach"
}
```

## Rules
- Be specific about file paths and class names
- Choose patterns that fit the task complexity
- Consider scalability and maintainability
- List all external dependencies with purposes
- Define clear interfaces between modules

## Internal Monologue
Before outputting the architecture, think through:
1. What's the best project structure for this task?
2. What design patterns are appropriate?
3. How will components communicate?
4. What are the key abstractions?

Show your thinking process, then output the architecture."""


class ArchitectAgent:
    def __init__(self) -> None:
        self.name = "Architect"
        self.system_prompt = ARCHITECT_PROMPT
        self.emoji = "\U0001f3d7\ufe0f"

    def get_prompt(self, plan: str, task: str, plan_data: Optional[Dict] = None) -> str:
        msg = f"## Original Task\n{task}\n\n## Plan from Planner\n{plan}"
        if plan_data:
            if plan_data.get("risks"):
                msg += f"\n\n## Identified Risks\n{plan_data['risks']}"
            if plan_data.get("files_to_modify"):
                msg += f"\n\n## Files to Consider\n{plan_data['files_to_modify']}"
        msg += "\n\nReview the plan and create a solid architecture. Output your architecture in JSON format."
        return msg

    def parse_architecture(self, response: str) -> Optional[Dict[str, Any]]:
        import json
        try:
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return None
