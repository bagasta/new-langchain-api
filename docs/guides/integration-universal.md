# MCP Calculator Server Integration Guide

This document explains how external LangChain-based projects can connect to the MCP Calculator Server provided in this repository. The server exposes calculator tools and a web fetching utility over multiple transports (STDIO, SSE, Streamable HTTP, REST API). Choose the transport that best matches your deployment scenario, then follow the corresponding integration steps.

## Available Tools

The server registers the following tools via MCP:

- `add`, `subtract`, `multiply`, `divide`, `power`, `sqrt`, `factorial`, `percentage`
- `fetch_web_content` — retrieve a text snippet from an HTTP/HTTPS URL

All tools return structured responses compatible with LangChain’s tool schemas.

## Prerequisites

- Python 3.10+
- Install server dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- (Optional) For LangChain playground support:
  ```bash
  cd playground/backend
  pip install -r requirements.txt
  ```

## Starting the MCP Server

From the repository root, start one of the following transports.

### STDIO Transport (CLI integration)
```bash
python -m src.transports.stdio
```
Use this when the client spawns the server process and communicates via stdio (ideal for local LangChain agents or CLI tools).

### SSE Transport (Server-Sent Events)
```bash
python -m src.transports.sse
# Defaults to http://localhost:8000/sse
```
SSE is recommended for web-based agents or backends that need persistent, streaming connections. The playground backend uses this transport.

### Streamable HTTP Transport
```bash
python -m src.transports.streamable
# Defaults to http://localhost:8001/mcp
```
Provides HTTP streaming semantics without SSE. Useful for environments where SSE is restricted but streaming responses are required.

### REST API Transport
```bash
python -m src.transports.api
# Exposes endpoints at http://localhost:8002
```
Offers simple JSON endpoints for listing tools and executing a single tool call. Ideal for lightweight integrations or debugging.

## Integrating with LangChain

### Using `langchain-mcp` Adapter (Recommended)

The playground backend demonstrates how to consume the MCP server via SSE using `langchain-mcp`:

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_mcp import MCPToolkit
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SSE_URL = "http://localhost:8000/sse"

async with sse_client(MCP_SSE_URL) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        toolkit = MCPToolkit(session=session)
        await toolkit.initialize()
        tools = toolkit.get_tools()

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        prompt = ChatPromptTemplate.from_messages([...])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools)
        result = await executor.ainvoke({"input": "What is 2+2?"})
```

Replace `sse_client` with other client transports (`stdio`, `streamable_http`) from the `mcp.client` package if you prefer different protocols.

### Using REST API

For simpler clients that do not require full MCP semantics, call the REST transport:

```python
import httpx

BASE_URL = "http://localhost:8002"

# List tools
tools = httpx.get(f"{BASE_URL}/tools").json()["tools"]

# Execute a tool
payload = {"tool_name": "fetch_web_content", "arguments": {"url": "https://example.com"}}
result = httpx.post(f"{BASE_URL}/execute", json=payload).json()
```

#### Reusing the REST MCP Client Adapter

The repository includes a minimal async adapter at `playground/backend/mcp_client.py`. External projects can copy or adapt this file to interact with the REST transport:

1. Copy `playground/backend/mcp_client.py` into your project (keeping the `MCPClient` class).
2. Install dependencies from `playground/backend/requirements.txt` (notably `httpx`, `pydantic`, and `python-dotenv` if you want `.env` support).
3. Ensure the REST transport is running (e.g., `python -m src.transports.api`), and set `MCP_API_BASE_URL` or pass a base URL to the client constructor.

The adapter exposes `list_tools()` and `execute_tool()` coroutines, mirroring the REST API endpoints.

### Using Streamable HTTP

When running `python -m src.transports.streamable`, use `mcp.client.streamable_http`:

```python
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

STREAM_URL = "http://localhost:8001/mcp"

async with streamable_http_client(STREAM_URL) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        ...
```

### Using STDIO

If your LangChain agent runs the MCP server as a subprocess:

```python
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

server_params = StdioServerParameters(command=["python", "-m", "src.transports.stdio"])

async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        ...
```

## Configuration Tips

- **Web fetching responses** are truncated to 1,500 characters to stay within LLM context limits. Check the `note` field for truncation status.
- Setting environment variables:
  - `MCP_API_BASE_URL` to point the REST client elsewhere.
  - `MCP_SSE_URL` for the SSE-based integrations.
  - `OPENAI_API_KEY` when using OpenAI-powered LangChain agents.
- The playground backend (FastAPI) uses SSE + `langchain-mcp`. Run both REST (`python -m src.transports.api`) and SSE transports when testing the full stack.

## Troubleshooting

- **400 Bad Request from OpenAI**: Ensure responses sent back to the LLM are within token limits. The server already truncates web content; customize limits in `src/tools.py` if needed.
- **Connection Issues**: Verify the transport is running, ports are open, and URLs match (`http`, `https`, or proper local ports).
- **Agent loops**: The LangChain executor caps iterations and includes prompt instructions to avoid repeated tool calls.

## Extending the Server

1. Add new methods to `src/tools.py` (Calculator or new utility class).
2. Register the tool in `src/server.py` with `@mcp.tool()`.
3. Update documentation and tests if applicable.
4. Restart the server to expose new tools to clients.

## References

- `playground/backend/main.py` — Complete example of integrating LangChain with MCP over SSE.
- `src/transports/*` — Transport implementations.
- `src/server.py` — Tool registration and FastMCP setup.

Use this guide to plug the MCP Calculator Server into your LangChain projects across different transports, enabling consistent tool access in any environment.
