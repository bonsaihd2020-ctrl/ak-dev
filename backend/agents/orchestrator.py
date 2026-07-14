from __future__ import annotations
import asyncio
import json
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from agents.planner import PlannerAgent
from agents.architect import ArchitectAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from agent_loop import AgentLoop
from memory import get_memory
from providers import LLMProvider


class Orchestrator:
    def __init__(self, provider: LLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model
        self.memory = get_memory()
        self._paused = False
        self._stopped = False
        self._on_event: Optional[Callable] = None
        self.agents = {
            "planner": PlannerAgent(),
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
            "reviewer": ReviewerAgent(),
            "tester": TesterAgent(),
        }
        self._agent_order = ["planner", "architect", "coder", "reviewer", "tester"]
        self._structured_data: Dict[str, Any] = {}

    def set_on_event(self, callback: Callable) -> None:
        self._on_event = callback

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True

    async def run(self, task: str, context: Optional[Dict] = None) -> AsyncGenerator[Dict[str, Any], None]:
        shared_state: Dict[str, Any] = {"task": task, "context": context or {}}
        tools_used: List[str] = []

        for agent_name in self._agent_order:
            if self._stopped:
                yield {"event": "stopped", "message": "Workflow stopped by user"}
                return

            while self._paused:
                await asyncio.sleep(0.5)
                if self._stopped:
                    yield {"event": "stopped", "message": "Workflow stopped by user"}
                    return

            agent = self.agents[agent_name]
            yield {"event": "agent_start", "agent": agent.name, "emoji": agent.emoji}

            agent_input = self._build_agent_input(agent_name, shared_state, task)
            self.memory.add_message("user", agent_input, agent=agent_name)

            monologue = f"Starting {agent.name} phase. Analyzing input..."
            self.memory.add_monologue(agent_name, monologue)
            yield {"event": "monologue", "agent": agent.name, "thought": monologue}

            messages_for_llm: List[Dict[str, str]] = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": agent_input},
            ]

            if self.memory.collected_keywords:
                keyword_msg = f"Relevant context keywords: {', '.join(self.memory.collected_keywords[:15])}"
                messages_for_llm.append({"role": "user", "content": keyword_msg})

            experiences = self.memory.get_relevant_experiences(task)
            if experiences:
                exp_text = "\n".join([f"- Task: {e['task'][:100]}, Success: {e['success']}" for e in experiences])
                messages_for_llm.append({"role": "user", "content": f"Past experiences:\n{exp_text}"})

            iteration = 0
            max_iter = 20
            agent_content = ""

            while iteration < max_iter and not self._stopped:
                while self._paused:
                    await asyncio.sleep(0.5)
                    if self._stopped:
                        break
                iteration += 1

                try:
                    full_response = {"role": "assistant", "content": "", "tool_calls": []}
                    content_parts = []

                    for chunk in self.provider.chat_stream(messages_for_llm, self.model):
                        if self._stopped:
                            break
                        if chunk["type"] == "content":
                            content_parts.append(chunk["content"])
                            agent_content += chunk["content"]
                            yield {"event": "content", "agent": agent.name, "content": chunk["content"]}
                        elif chunk["type"] == "tool_calls":
                            full_response["tool_calls"] = chunk["tool_calls"]

                    full_response["content"] = "".join(content_parts)
                    messages_for_llm.append(full_response)
                    self.memory.add_message("assistant", full_response["content"], agent=agent_name)

                    if not full_response["tool_calls"]:
                        shared_state[f"{agent_name}_output"] = full_response["content"]
                        self._parse_agent_output(agent_name, full_response["content"])
                        yield {"event": "agent_done", "agent": agent.name, "output": full_response["content"]}
                        self.memory.record_step(agent.name, f"Completed {agent_name} phase")
                        break

                    for tc in full_response["tool_calls"]:
                        from tools import dispatch_tool
                        func_name = tc["function"]["name"]
                        tools_used.append(func_name)
                        try:
                            func_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            func_args = {}

                        yield {"event": "tool_call", "agent": agent.name, "tool": func_name, "args": func_args}
                        result = dispatch_tool(func_name, func_args)
                        self.memory.record_tool_call(func_name, func_args, result)

                        if func_name in ("write_file", "edit_file") and result.get("success"):
                            self.memory.track_file_change(func_args.get("path", ""), created=(func_name == "write_file"))

                        result_content = json.dumps(result, indent=2) if not result.get("success") else f"Success: {json.dumps(result)}"
                        yield {"event": "tool_result", "agent": agent.name, "tool": func_name, "result": result}
                        messages_for_llm.append({"role": "tool", "content": result_content})

                except Exception as e:
                    yield {"event": "error", "agent": agent.name, "message": str(e)}
                    messages_for_llm.append({"role": "user", "content": f"Error: {str(e)}. Continue."})

        success = not self._stopped
        self.memory.add_experience(task, self.memory.get_summary(), tools_used, success)

        yield {"event": "workflow_done", "summary": self.memory.get_summary()}

    def _build_agent_input(self, agent_name: str, shared_state: Dict, task: str) -> str:
        if agent_name == "planner":
            return self.agents["planner"].get_prompt(task, shared_state.get("context"))
        elif agent_name == "architect":
            plan = shared_state.get("planner_output", "")
            plan_data = self._structured_data.get("planner")
            return self.agents["architect"].get_prompt(plan, task, plan_data)
        elif agent_name == "coder":
            plan = shared_state.get("planner_output", "")
            arch = shared_state.get("architect_output", "")
            arch_data = self._structured_data.get("architect")
            existing_code = ""
            ws = None
            try:
                from workspace import get_workspace
                ws = get_workspace()
                if ws.is_connected():
                    files = ws.list_files_recursive()
                    code_parts = []
                    for f in files[:20]:
                        result = ws.read_file(f)
                        if result.get("success"):
                            code_parts.append(f"### {f}\n{result.get('content', '')[:500]}")
                    existing_code = "\n\n".join(code_parts)
            except Exception:
                pass
            return self.agents["coder"].get_prompt(arch, plan, task, existing_code, arch_data)
        elif agent_name == "reviewer":
            files = self.memory.files_created + self.memory.files_modified
            arch = shared_state.get("architect_output", "")
            return self.agents["reviewer"].get_prompt(files, task, arch)
        elif agent_name == "tester":
            files = self.memory.files_created + self.memory.files_modified
            arch = shared_state.get("architect_output", "")
            return self.agents["tester"].get_prompt(files, task, arch)
        return task

    def _parse_agent_output(self, agent_name: str, content: str) -> None:
        if agent_name == "planner":
            plan = self.agents["planner"].parse_plan(content)
            if plan:
                self._structured_data["planner"] = plan
                self.memory.set_plan(plan)
        elif agent_name == "architect":
            arch = self.agents["architect"].parse_architecture(content)
            if arch:
                self._structured_data["architect"] = arch
