from pocketflow import Node, Flow
from utils import call_llm, get_tools, call_tool
import yaml
from mcp.types import Tool
from typing import Any


class GetToolsNode(Node):
    server_paths: list[str]

    def prep(self, shared):
        """Initialize and get tools"""
        # The question is now passed from main via shared
        print("🔍 Getting available tools...")
        return self.server_paths

    def exec(self, server_paths: list[str]):
        """Retrieve tools from the MCP server"""
        tools: list[Tool] = []
        for server_path in server_paths:
            print(f"Server path: {server_path}")
            tools += get_tools(server_path)
        return tools

    def post(self, shared: dict[str, Any], prep_res: list[str], exec_res: list[Tool]):
        """Store tools and process to decision node"""
        tools = exec_res
        shared["tools"] = tools

        # Format tool information for later use
        tool_info = []
        for i, tool in enumerate(tools, 1):
            properties = tool.inputSchema.get("properties", {})
            required = tool.inputSchema.get("required", [])

            params = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "unknown")
                req_status = "(Required)" if param_name in required else "(Optional)"
                params.append(f"    - {param_name} ({param_type}): {req_status}")

            tool_info.append(
                f"[{i}] {tool.name}\n  Description: {tool.description}\n  Parameters:\n"
                + "\n".join(params)
            )

        shared["tool_info"] = "\n".join(tool_info)
        return "decide"

    def __init__(self, server_paths: list[str]):
        super().__init__()
        self.server_paths = server_paths


class DecideToolNode(Node):
    def prep(self, shared):
        """Prepare the prompt for LLM to process the question"""
        tool_info = shared["tool_info"]
        question = shared["question"]

        prompt = f"""
### CONTEXT
You are an assistant that can use tools via Model Context Protocol (MCP).

### ACTION SPACE
{tool_info}

### TASK
Answer this question: "{question}"

## NEXT ACTION
Analyze the question, extract parameters, and decide which tool to use.
Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning about what the question is asking and what parameters to extract>
tool: <name of the tool to use>
reason: <why you chose this tool>
parameters:
    <parameter_name>: <parameter_value>
    <parameter_name>: <parameter_value>
```
IMPORTANT:
1. Extract parameters from the question properly
2. Use proper indentation (4 spaces) for multi-line fields
3. Use the | character for multi-line text fields
"""  # noqa: E501
        return prompt

    def exec(self, prompt):
        """Call LLM to process the question and decide which tool to use"""
        print("🤔 Analyzing question and deciding which tool to use...")
        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        """Extract decision from YAML and save to shared context"""
        try:
            print(exec_res)
            yaml_str = exec_res.split("```yaml")[1].split("```")[0].strip()
            decision = yaml.safe_load(yaml_str)

            shared["tool_name"] = decision["tool"]
            shared["parameters"] = decision["parameters"]
            shared["thinking"] = decision.get("thinking", "")

            print(f"💡 Selected tool: {decision['tool']}")
            print(f"🔢 Extracted parameters: {decision['parameters']}")

            return "execute"
        except Exception as e:
            print(f"❌ Error parsing LLM response: {e}")
            print("Raw response:", exec_res)
            return None


class ExecuteToolNode(Node):
    def prep(self, shared):
        """Prepare tool execution parameters"""
        return shared["tool_name"], shared["parameters"]

    def exec(self, inputs):
        """Execute the chosen tool"""
        tool_name, parameters = inputs
        print(f"🔧 Executing tool '{tool_name}' with parameters: {parameters}")
        result = call_tool(self.server_path, tool_name, parameters)
        return tool_name, parameters, result

    def post(self, shared, prep_res, exec_res):
        tool_name, parameters, result = exec_res
        if result.isError:
            shared["call_result"] = f"Error: {result.error}"
            return "handle_error"
        call_result = f"""
From calling the tool '{tool_name}' with parameters '{parameters}', we got the following result:

{result}
"""  # noqa: E501
        shared["call_result"] = call_result
        return "write_answer"

    def __init__(self, server_path: str):
        super().__init__()
        self.server_path = server_path


class WriteAnswerNode(Node):
    def prep(self, shared):
        """Write the answer to the question"""
        prompt = f"""
### CONTEXT
You are an assistant that can use tools via Model Context Protocol (MCP).

### TASK
Answer this question: "{shared["question"]}"

### TOOL CALL RESULT
{shared["call_result"]}

### ANSWER
Write the answer to the question based on the tool call result in Markdown format.
"""
        return prompt

    def exec(self, prompt):
        print("💬 Writing answer...")
        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        with open("answer.md", "w") as f:
            f.write(exec_res)
        return "done"


class HandleErrorNode(Node):
    def prep(self, shared):
        return shared["call_result"]

    def exec(self, call_result):
        print(f"❌ Error: {call_result}")
        return "done"


if __name__ == "__main__":
    shared = {
        "question": "Analyze the financial statements of AOT stock from 2022 to 2024",
    }
    # Initialize nodes
    get_tools_node = GetToolsNode(server_paths=["uvx set-mcp"])
    decide_node = DecideToolNode()
    execute_node = ExecuteToolNode(server_path="uvx set-mcp")
    write_answer_node = WriteAnswerNode()
    handle_error_node = HandleErrorNode()

    # Connect nodes
    get_tools_node - "decide" >> decide_node
    decide_node - "execute" >> execute_node
    execute_node - "write_answer" >> write_answer_node
    execute_node - "handle_error" >> handle_error_node

    # Create flow
    flow = Flow(start=get_tools_node)
    flow.run(shared)
