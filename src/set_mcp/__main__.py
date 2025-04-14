from typing import Literal

import click
from fastmcp import FastMCP
from .settrade_scraper import (
    get_financial_statement_from_year,
    FinancialStatement,
)


mcp = FastMCP("Set Balance Sheet")


def construct_financial_statement(financial_statement: FinancialStatement) -> str:
    """Construct the financial statement from the financial statement dictionary.

    Args:
        financial_statement (FinancialStatement): The financial statement dictionary.

    Returns:
        str: The constructed financial statement.
    """
    return f"""
    Business Type: {financial_statement["business_type"]}

    UNIT: Million THB

    Income Statement:
    {financial_statement["income_statement"]}

    Balance Sheet:
    {financial_statement["balance_sheet"]}

    Cash Flow Statement:
    {financial_statement["cash_flow_statement"]}
    """


@mcp.tool()
async def get_financial_statement(symbol: str, from_year: int, to_year: int) -> str:  # noqa
    """Get the balance sheet of stock in The Securities Exchange of Thailand (SET).

    Args:
        symbol (str): Stock symbol in The Securities Exchange of Thailand (SET).
        from_year (int): The start YEAR of the financial statement for example 2024.
        to_year (int): The end YEAR of the financial statement for example 2024.

    Returns:
        str: The constructed financial statement.
        Include Income Statement, Balance Sheet, and Cash Flow Statement in CSV format with | as the delimiter.
    """  # noqa
    financial_statement = await get_financial_statement_from_year(
        symbol, from_year, to_year
    )
    context = construct_financial_statement(financial_statement)
    return context


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option("--host", default="0.0.0.0", help="Host to listen on")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(transport: Literal["stdio", "sse"], host: str, port: int):
    if transport == "stdio":
        mcp.run(transport=transport)
    elif transport == "sse":
        raise NotImplementedError("SSE transport is not implemented")
    else:
        raise ValueError(f"Invalid transport: {transport}")


if __name__ == "__main__":
    main()
