# SET-MCP

SET-MCP is a Python package that provides tools for serving Model Context Protocol which can access the Securities Exchange of Thailand (SET). It allows AI agents to retrieve comprehensive financial statements including income statements, balance sheets, and cash flow statements for listed companies.

## Features

- Retrieve financial statements for SET-listed companies
- Support for multiple financial statement types:
  - Income Statement
  - Balance Sheet
  - Cash Flow Statement
- Historical data retrieval with customizable date ranges
- Command-line interface for easy integration
- FastMCP integration for enhanced functionality

## Installation

The package requires Python 3.11 or higher. You can install it using pip:

```bash
pip install set-mcp
```

## Usage

### Command Line Interface

The package provides a command-line interface for easy access to financial data:

```bash
set-mcp --transport stdio
```

### Using with `uvx`

Run

```
uvx set-mcp
```

### Using with `pipx`

```
pipx install set-mcp
pipx run set-mcp
```

### MCP.json example

```json
{
    "mcpServers": {
      "set_mcp": {
        "command": "/path/to/bin/uvx", // Edit to your uvx path
        "args": [
            "set-mcp"
        ],
      }
    }
}
```

Available options:
- `--port`: Port to listen on for SSE (default: 8000)
- `--host`: Host to listen on (default: 0.0.0.0)
- `--transport`: Transport type (choices: stdio, sse, default: stdio)

**Note: SSE is not yet implemented**

### Python API

You can also use the package programmatically in your Python code:

```python
from set_mcp import get_financial_statement

# Get financial statements for a specific company
result = await get_financial_statement(
    symbol="PTT",  # Company symbol
    from_year=2023,
    to_year=2024
)
```

## Development

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/set-mcp.git
cd set-mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
python test_client.py
```

The output should be no error

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

- Prem Chotipanit (prem.ch@ku.th | prem.chotepanit@gmail.com)