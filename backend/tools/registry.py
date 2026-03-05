from backend.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            registered = ", ".join(self._tools.keys()) or "<none>"
            raise KeyError(
                f"Tool '{name}' not found. Registered tools: {registered}"
            )
        return self._tools[name]

    def all_schemas(self) -> list[dict]:
        return [t.to_llm_schema() for t in self._tools.values()]
