from __future__ import annotations
from typing import Any, Dict, Optional

PLANNER_PROMPT = """You are the PLANNER agent in a multi-agent coding system. Your job is to analyze the user's task and create a structured implementation plan.

## Your Role
- Analyze the task thoroughly
- Break it down into clear, actionable steps
- Identify files that need to be created or modified
- Identify potential risks and edge cases
- Create a structured plan with priorities

## Output Format (STRICT - follow exactly)
You MUST respond with a JSON object inside a ```json code block. Example:

```json
{
  "project_name": "short-project-name",
  "reply": "Brief human-like response about what you'll do",
  "focus": "Main objective",
  "steps": [
    {"id": 1, "description": "Step description", "priority": "high", "files": ["file1.py"], "estimated_effort": "5min"},
    {"id": 2, "description": "Step description", "priority": "medium", "files": ["file2.py"], "estimated_effort": "10min"}
  ],
  "files_to_modify": [
    {"path": "path/to/file", "action": "create", "description": "What changes"}
  ],
  "risks": [
    {"risk": "Risk description", "mitigation": "How to handle it", "severity": "high"}
  ],
  "dependencies": ["any external deps needed"],
  "summary": "Brief summary of the approach"
}
```

## Rules
- project_name: max 5 words, lowercase, hyphenated
- reply: short, human-like, 1-2 sentences
- steps: ordered by priority (high first), each with id, description, priority, files, estimated_effort
- files_to_modify: action can be "create", "modify", or "delete"
- risks: severity can be "high", "medium", or "low"
- If the task is simple, just give 1-2 steps
- Be specific about file paths
- Consider edge cases and error handling

## Internal Monologue
Before outputting the plan, think through:
1. What is the user really asking for?
2. What's the simplest approach that works?
3. What could go wrong?
4. What's the order of operations?

Show your thinking process, then output the plan."""


class PlannerAgent:
    def __init__(self) -> None:
        self.name = "Planner"
        self.system_prompt = PLANNER_PROMPT
        self.emoji = "\U0001f4cb"

    def get_prompt(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        msg = f"## Task\n{task}"
        if context:
            if context.get("additional_context"):
                msg += f"\n\n## Additional Context\n{context['additional_context']}"
            if context.get("keywords"):
                msg += f"\n\n## Relevant Keywords\n{', '.join(context['keywords'][:20])}"
            if context.get("previous_plan"):
                msg += f"\n\n## Previous Plan (improve upon this)\n{context['previous_plan']}"
        msg += "\n\nThink through the task, then output your structured plan in JSON format."
        return msg

    def parse_plan(self, response: str) -> Optional[Dict[str, Any]]:
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

            plan = json.loads(json_str)
            required_keys = ["project_name", "steps"]
            if all(k in plan for k in required_keys):
                return plan
        except (json.JSONDecodeError, ValueError):
            pass
        return None
