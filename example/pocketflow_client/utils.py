import os
import asyncio
import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Any
import google.generativeai as genai


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


def call_llm(
    prompt: str,
    stream: bool = False,
) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text


def get_tools(server_script_path=None):
    """Get available tools, either from MCP server or locally based on MCP global setting."""  # noqa: E501
    return mcp_get_tools(server_script_path)


def mcp_get_tools(server_script_path: str):
    """Get available tools from an MCP server."""
    command, *args = server_script_path.split(" ")

    async def _get_tools():
        server_params = StdioServerParameters(command=command, args=args)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                return tools_response.tools

    return asyncio.run(_get_tools())


def call_tool(
    server_script_path=None, tool_name=None, arguments=None
) -> mcp.types.CallToolResult:
    """Call a tool."""
    return mcp_call_tool(server_script_path, tool_name, arguments)


def mcp_call_tool(
    server_script_path: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> mcp.types.CallToolResult:
    """Call a tool on an MCP server."""

    async def _call_tool():
        command, *args = server_script_path.split(" ")
        server_params = StdioServerParameters(command=command, args=args)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result
    return asyncio.run(_call_tool())


if __name__ == "__main__":
    tools_prompt = "Available tools:\n"
    for tool in get_tools("uvx set-mcp"):
        tool_prompt = f"""Name: {tool.name}
Description: {tool.description}

Input Schema:
{tool.inputSchema}

"""
        tools_prompt += tool_prompt

    call_tool_response = call_tool(
        "uvx set-mcp",
        tool_name="get_financial_statement",
        arguments={"symbol": "AOT", "from_year": 2021, "to_year": 2024},
    )
    print(call_tool_response)
