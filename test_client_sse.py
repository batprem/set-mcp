import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client(
        url="http://localhost:8000/sse",
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available resources
            resources = await session.list_tools()
            print("Listing tools...")
            for tool in resources.tools:
                print(f"Tool: {tool.name}")
                print(f"Description: {tool.description}")
                print(f"Input Schema: {tool.inputSchema}")
                print("-" * 100)

            result = await session.call_tool(
                "get_financial_statement",
                dict(
                    symbol="AOT",
                    from_year=2022,
                    to_year=2024,
                ),
            )
            print(result)
            assert not result.isError


asyncio.run(main())
