import httpx
import pandas as pd
import re
import asyncio
from typing import TypedDict, Optional


class FinancialStatement(TypedDict):
    """A dictionary containing all financial statements."""

    business_type: Optional[str]
    income_statement: str
    balance_sheet: str
    cash_flow_statement: str


pd.options.display.float_format = "{:.2f}".format


headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-TH,en;q=0.9,th-TH;q=0.8,th;q=0.7,en-GB;q=0.6,en-US;q=0.5",
    "if-none-match": '"342c523b"',
    "priority": "u=1, i",
    "referer": "https://www.settrade.com/th/equities/quote/OR/financial-statement/full",
    "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",  # noqa
}


def scale(sheet: pd.DataFrame) -> pd.DataFrame:
    """Scale the sheet by 1000000.

    Args:
        sheet (pd.DataFrame): The sheet to scale.

    Returns:
        pd.DataFrame: The scaled sheet.
    """
    sheet["amount"] = sheet["amount"] * sheet["divider"] / 1000000
    return sheet


async def get_session(symbol: str) -> httpx.AsyncClient:
    """Get a session for the SET trade website.

    Args:
        symbol (str): The symbol of the stock to get the session for.

    Returns:
        httpx.AsyncClient: A client for the SET trade website.
    """
    client = httpx.AsyncClient()
    await client.get(
        f"https://www.settrade.com/th/equities/quote/{symbol}/financial-statement/full"
    )

    return client


async def get_business_type(session: httpx.AsyncClient, symbol: str) -> Optional[str]:
    """Get the business type of a stock.

    Args:
        session (httpx.AsyncClient): The client to use.
        symbol (str): The symbol of the stock to get the business type for.

    Returns:
        Optional[str]: The business type of the stock, or None if not found.
    """
    response = await session.get(
        f"https://www.settrade.com/th/equities/quote/{symbol}/overview"
    )

    response.raise_for_status()
    text = response.text
    pattern = r'businessType:\s*"([^"]+)"'
    found = re.search(pattern, text)

    if found:
        target_data = found.group(1)
        return target_data
    else:
        print("No match found.")
        return None


async def get_balance_sheet(
    session: httpx.AsyncClient, symbol: str, period: str
) -> pd.DataFrame:
    """Get the balance sheet of a stock."""
    params = {
        "accountType": "balance_sheet",
        "fsType": "company",
        "period": period,
        "language": "en",
    }
    response = await session.get(
        f"https://www.settrade.com/api/set/stock/{symbol}/financialstatement",
        params=params,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return scale(pd.DataFrame(data["accounts"]))


async def get_income_statement(
    session: httpx.AsyncClient, symbol: str, period: str
) -> pd.DataFrame:
    params = {
        "accountType": "income_statement",
        "fsType": "company",
        "period": period,
        "language": "en",
    }
    response = await session.get(
        f"https://www.settrade.com/api/set/stock/{symbol}/financialstatement",
        params=params,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return scale(pd.DataFrame(data["accounts"]))


async def get_cash_flow_statement(
    session: httpx.AsyncClient, symbol: str, period: str
) -> pd.DataFrame:
    """Get the cash flow statement of a stock."""
    params = {
        "accountType": "cash_flow",
        "fsType": "company",
        "period": period,
        "language": "en",
    }
    response = await session.get(
        f"https://www.settrade.com/api/set/stock/{symbol}/financialstatement",
        params=params,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return scale(pd.DataFrame(data["accounts"]))


def transform_statements_to_df(
    statement_list: list[pd.DataFrame], year_range: range
) -> pd.DataFrame:
    """Transform a list of statement DataFrames into a single DataFrame with years as columns.

    Args:
        statement_list: List of DataFrames containing financial statements
        year_range: Range of years to include

    Returns:
        DataFrame with account codes, names, and yearly amounts as columns
    """  # noqa
    if not statement_list:
        return pd.DataFrame()

    df, *remaining_statements = statement_list
    df[year_range[0]] = df["amount"]
    df = df[["accountCode", "accountName", year_range[0]]]
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    for period, statement in zip(year_range[1:], remaining_statements):
        statement = statement.copy()  # Create a copy to avoid modifying the original
        statement[period] = statement["amount"].astype(float)
        statement = statement[["accountCode", "accountName", period]]
        df = pd.merge(
            df,
            statement,
            on="accountCode",
            how="outer",
            suffixes=("", "_drop"),
        )
        # Convert Index to list before dropping columns
        drop_columns = list(df.filter(like="_drop").columns)
        df.drop(columns=drop_columns, inplace=True)

    return df


async def get_financial_statement_from_year(
    symbol: str, from_year: int, to_year: int
) -> FinancialStatement:
    """Get the financial statement of a stock from a specific year to another year."""
    session = await get_session(symbol)
    business_type = await get_business_type(session, symbol)
    year_range = range(from_year, to_year + 1)
    balance_sheet_coroutine_list = []
    income_statement_coroutine_list = []
    cash_flow_statement_coroutine_list = []
    for year in year_range:
        query_year = f"YE_{year}"
        balance_sheet_coroutine_list.append(
            get_balance_sheet(session, symbol, query_year)
        )
        income_statement_coroutine_list.append(
            get_income_statement(session, symbol, query_year)
        )
        cash_flow_statement_coroutine_list.append(
            get_cash_flow_statement(session, symbol, query_year)
        )

    # Gather all coroutines at once
    all_results: list[pd.DataFrame] = await asyncio.gather(
        *balance_sheet_coroutine_list,
        *income_statement_coroutine_list,
        *cash_flow_statement_coroutine_list,
    )

    # Split the results back into their respective lists
    total_years = len(year_range)
    balance_sheet_list = all_results[:total_years]
    income_statement_list = all_results[total_years : total_years * 2]  # noqa
    cash_flow_statement_list = all_results[total_years * 2 :]  # noqa

    balance_sheet_df = transform_statements_to_df(balance_sheet_list, year_range)
    income_statement_df = transform_statements_to_df(income_statement_list, year_range)
    cash_flow_statement_df = transform_statements_to_df(
        cash_flow_statement_list, year_range
    )

    return {
        "business_type": business_type,
        "balance_sheet": balance_sheet_df.to_csv(index=False, sep="|"),
        "income_statement": income_statement_df.to_csv(index=False, sep="|"),
        "cash_flow_statement": cash_flow_statement_df.to_csv(index=False, sep="|"),
    }


if __name__ == "__main__":

    async def main():
        financial_statement = await get_financial_statement_from_year("BH", 2022, 2024)
        print(financial_statement)

    asyncio.run(main())
