# How to Use the FastMCP Server

This guide walks through getting the FastMCP-based MCP server running locally, validating the setup, and exploring tools with the included Playground UI and SSE transport for LangChain integration.

## 1. Prerequisites

- Python 3.10 or newer (`python --version`)
- `pip` package manager
- Recommended: virtual environment support (`python -m venv venv`)
- Optional: API keys for external services used by specific tools

## 2. Project Setup

1. **Clone and enter the repository**
   ```bash
   git clone <repository-url>
   cd langchain-mcp-server
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with values appropriate for your environment. Key entries include:
   - `MCP_SERVER_NAME`, `MCP_LOG_LEVEL` – core server settings
   - `MCP_ENABLED_TOOLS_CONFIG` – comma-separated list of enabled tools (defaults to `calculator,web_search,web_fetch,pdf_generate`)
   - `MCP_MAX_TOOL_EXECUTION_TIME` – per-tool timeout in seconds
   - Optional API keys (`OPENAI_API_KEY`, `SERPER_API_KEY`, etc.) for tools that call external services

## 3. Running the MCP Server

### 3.1 Standard MCP Server (stdio transport)

From the project root with your virtual environment active:

```bash
python -m src.server
# or
fastmcp run src/server.py
```

You should see log entries confirming the server name, version, and registered tools. The server listens over stdio and is ready for MCP-compatible clients.

### 3.2 SSE MCP Server (for LangChain integration)

For LangChain integration with SSE transport, the server supports flexible port configuration:

#### Method 1: Default Port (8080)
```bash
# Set authentication token
export MCP_BEARER_TOKEN="your-secret-token"

# Start SSE server on default port 8080
python simple_sse_server.py
```

#### Method 2: Custom Port via Command Line
```bash
# Set authentication token
export MCP_BEARER_TOKEN="your-secret-token"

# Start on custom port (e.g., 9000)
python simple_sse_server.py --port 9000

# Start on custom port with custom host
python simple_sse_server.py --port 9000 --host 127.0.0.1

# Start with custom token
python simple_sse_server.py --port 9000 --token "your-custom-token"
```

#### Method 3: Custom Port via Environment Variables
```bash
# Set configuration
export MCP_BEARER_TOKEN="your-secret-token"
export MCP_SSE_PORT=9000
export MCP_SSE_HOST=127.0.0.1

# Start server (will use environment variables)
python simple_sse_server.py
```

#### Command Line Options
```bash
python simple_sse_server.py --help
```
Available options:
- `--port, -p`: Port to listen on (default: 8080)
- `--host, -H`: Host to bind to (default: 0.0.0.0)
- `--token, -t`: Bearer token for authentication (default: from MCP_BEARER_TOKEN env)

#### Environment Variables
- `MCP_BEARER_TOKEN`: Bearer token for authentication (default: "test-token-123")
- `MCP_SSE_PORT`: Port to listen on (default: 8080)
- `MCP_SSE_HOST`: Host to bind to (default: "0.0.0.0")

The server will start with the configured port and host, providing these endpoints:
- **SSE Endpoint**: `GET /mcp/sse` (for LangChain SSE transport)
- **MCP Request**: `POST /mcp/request` (JSON-RPC 2.0)
- **Tools List**: `GET /tools`
- **Tool Call**: `POST /tools/{tool_name}/call`
- **Health**: `GET /health`

**Example startup output:**
```
============================================================
🚀 MCP SSE Server Starting
============================================================
📍 Server URL: http://localhost:9000
🔌 Port: 9000
🌐 Host: 0.0.0.0
🔐 Auth Token: your-secret...
🛠️  Available Tools: calculator, web_search, web_fetch, pdf_generate
============================================================
📡 Available Endpoints:
   • SSE:      http://localhost:9000/mcp/sse
   • Tools:    http://localhost:9000/tools
   • Health:   http://localhost:9000/health
   • MCP Req:  http://localhost:9000/mcp/request
   • Docs:     http://localhost:9000/docs
============================================================
```

### 3.3 Adjusting Logging and Tool Configuration

- Override the log level inline:
  ```bash
  MCP_LOG_LEVEL=DEBUG python -m src.server
  ```
- Edit `.env` to disable tools you do not need; changes take effect on the next run.

## 4. SSE API Documentation and Curl Examples

### 4.1 Authentication

All SSE endpoints require Bearer token authentication:

```bash
# Set your token
export MCP_BEARER_TOKEN="your-secret-token"

# Use in curl requests (replace PORT with your configured port)
curl -H "Authorization: Bearer your-secret-token" http://localhost:PORT/endpoint

# Example with port 9000
curl -H "Authorization: Bearer your-secret-token" http://localhost:9000/tools
```

### 4.2 Server Information

Get basic server information (replace PORT with your configured port):

```bash
curl -H "Authorization: Bearer your-secret-token" http://localhost:PORT/

# Example with port 9000
curl -H "Authorization: Bearer your-secret-token" http://localhost:9000/
```

**Response:**
```json
{
  "message": "MCP SSE Server for LangChain",
  "version": "1.0.0",
  "endpoints": {
    "mcp_sse": "/mcp/sse",
    "docs": "/docs",
    "health": "/health",
    "tools": "/tools"
  },
  "transport": "sse",
  "available_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]
}
```

### 4.3 Health Check

Check server health status (replace PORT with your configured port):

```bash
curl -H "Authorization: Bearer your-secret-token" http://localhost:PORT/health

# Example with port 9000
curl -H "Authorization: Bearer your-secret-token" http://localhost:9000/health
```

**Response:**
```json
{
  "status": "healthy",
  "transport": "sse",
  "server": "mcp"
}
```

### 4.4 List Available Tools

Get list of all available tools with their schemas:

```bash
curl -H "Authorization: Bearer your-secret-token" http://localhost:8080/tools
```

**Response:**
```json
{
  "tools": [
    {
      "name": "calculator",
      "description": "Evaluates mathematical expressions safely using a restricted evaluator.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "expression": {"type": "string"}
        },
        "required": ["expression"]
      }
    },
    {
      "name": "web_search",
      "description": "Perform a placeholder web search and return mock results for the given query.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
      }
    },
    {
      "name": "web_fetch",
      "description": "Fetch content from a URL and return a cleaned text snippet.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "url": {"type": "string"},
          "max_chars": {"type": "integer", "default": 2000}
        },
        "required": ["url"]
      }
    },
    {
      "name": "pdf_generate",
      "description": "Render PDF documents from HTML or Markdown templates using configurable engines.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "template": {"type": "string"},
          "content_type": {"type": "string", "default": "html"},
          "engine": {"type": "string", "default": "weasyprint"},
          "output_format": {"type": "string", "default": "base64"}
        },
        "required": ["template"]
      }
    }
  ]
}
```

### 4.5 Call Tools via REST API

Direct tool execution using REST API:

#### Calculator Tool
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"expression": "15*8+12"}}' \
  http://localhost:8080/tools/calculator/call
```

**Response:**
```json
{
  "tool": "calculator",
  "arguments": {"expression": "15*8+12"},
  "result": "132",
  "success": true
}
```

#### Web Search Tool
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "Python programming", "num_results": 3}}' \
  http://localhost:8080/tools/web_search/call
```

**Response:**
```json
{
  "tool": "web_search",
  "arguments": {"query": "Python programming", "num_results": 3},
  "result": "Mock search results for 'Python programming' (showing 3 results):\n1. Result about Python programming\n2. Another result about Python programming\n3. More information about Python programming",
  "success": true
}
```

#### Web Fetch Tool
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"url": "https://httpbin.org/html", "max_chars": 500}}' \
  http://localhost:8080/tools/web_fetch/call
```

**Response:**
```json
{
  "tool": "web_fetch",
  "arguments": {"url": "https://httpbin.org/html", "max_chars": 500},
  "result": "Mock content from https://httpbin.org/html (truncated to 500 characters): This is sample content that would normally be fetched from the actual URL.",
  "success": true
}
```

#### PDF Generation Tool
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"template": "<h1>Hello {{name}}</h1><p>Today is {{date}}</p>", "content_type": "html", "variables": {"name": "World", "date": "2025-10-08"}}}' \
  http://localhost:8080/tools/pdf_generate/call
```

**Response:**
```json
{
  "tool": "pdf_generate",
  "arguments": {
    "template": "<h1>Hello {{name}}</h1><p>Today is {{date}}</p>",
    "content_type": "html",
    "variables": {"name": "World", "date": "2025-10-08"}
  },
  "result": "Mock PDF generated from template (length: 58 chars). Additional params: {}",
  "success": true
}
```

### 4.6 MCP Protocol via REST API

Execute MCP protocol commands (JSON-RPC 2.0):

#### Initialize MCP Session
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0"}
    }
  }' \
  http://localhost:8080/mcp/request
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "experimental": {},
      "prompts": {"listChanged": false},
      "resources": {"subscribe": false, "listChanged": false},
      "tools": {"listChanged": true}
    },
    "serverInfo": {
      "name": "langchain-mcp-server",
      "version": "1.0.0"
    },
    "instructions": "FastMCP server with SSE transport for LangChain integration"
  }
}
```

#### List Tools via MCP Protocol
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }' \
  http://localhost:8080/mcp/request
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "calculator",
        "description": "Evaluates mathematical expressions safely using a restricted evaluator.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
      // ... other tools
    ]
  }
}
```

#### Call Tool via MCP Protocol
```bash
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {"expression": "100*5+25"}
    }
  }' \
  http://localhost:8080/mcp/request
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "525"
      }
    ]
  }
}
```

### 4.7 SSE Connection (Server-Sent Events)

For actual SSE connections (used by LangChain):

```bash
# Establish SSE connection
curl -H "Authorization: Bearer your-secret-token" \
  -N http://localhost:8080/mcp/sse
```

**Expected SSE Stream:**
```
event: connected
data: {"message": "MCP SSE connection established", "server": "langchain-mcp-server", "available_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]}

event: ping
data: {"timestamp": 1728391234.567, "status": "alive"}
```

## 5. LangChain Integration

### 5.1 Configuration for LangChain

Create or update your LangChain agent configuration (replace PORT with your configured port):

```json
{
  "name": "Agent dengan External MCP",
  "mcp_servers": {
    "my_mcp_server": {
      "transport": "sse",
      "url": "http://localhost:PORT/mcp/sse",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  },
  "allowed_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]
}
```

**Example configurations:**

```json
{
  "name": "Agent with Port 9000",
  "mcp_servers": {
    "my_mcp_server": {
      "transport": "sse",
      "url": "http://localhost:9000/mcp/sse",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  },
  "allowed_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]
}
```

```json
{
  "name": "Agent with Port 7000",
  "mcp_servers": {
    "my_mcp_server": {
      "transport": "sse",
      "url": "http://localhost:7000/mcp/sse",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  },
  "allowed_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]
}
```

### 5.2 Production Deployment

For production deployment using Docker with configurable ports:

```bash
# Method 1: Default port (8080)
export MCP_BEARER_TOKEN="your-production-token"
docker-compose -f docker-compose.sse.yml up -d

# Method 2: Custom port (e.g., 9000)
export MCP_BEARER_TOKEN="your-production-token"
export MCP_SSE_PORT=9000
docker-compose -f docker-compose.sse.yml up -d

# Method 3: Custom port and host
export MCP_BEARER_TOKEN="your-production-token"
export MCP_SSE_PORT=9000
export MCP_SSE_HOST=127.0.0.1
docker-compose -f docker-compose.sse.yml up -d
```

#### Docker Environment Variables
- `MCP_BEARER_TOKEN`: Bearer token for authentication (required)
- `MCP_SSE_PORT`: Port to expose (default: 8080)
- `MCP_SSE_HOST`: Host to bind to (default: 0.0.0.0)
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `SERPER_API_KEY`: Serper API key for web search (optional)

#### Docker Configuration Files
The Docker setup includes:
- **MCP SSE Server** on configurable port (default: 8080)
- **Nginx Load Balancer** on ports 80/443
- **Dynamic port mapping** based on `MCP_SSE_PORT` environment variable
- **Health checks** with configurable port
- **SSL support** (configure certificates in `./ssl/`)
- **Automatic restarts** and monitoring

#### Docker Compose Override
Create a `.env` file for persistent configuration:

```bash
# .env file for Docker
MCP_BEARER_TOKEN=your-production-token
MCP_SSE_PORT=9000
MCP_SSE_HOST=0.0.0.0
OPENAI_API_KEY=your-openai-key
SERPER_API_KEY=your-serper-key
```

Then deploy with:
```bash
docker-compose -f docker-compose.sse.yml up -d
```

#### Scaling and Load Balancing
```bash
# Scale multiple instances
docker-compose -f docker-compose.sse.yml up -d --scale mcp-sse-server=3

# The Nginx load balancer will distribute traffic across instances
```

## 6. Running the Test Suite

Execute the project's automated tests to verify the installation:

```bash
pytest tests/ -v
```

For coverage details:

```bash
pytest tests/ --cov=src --cov-report=term
```

## 7. Using the Playground UI

The Playground is a FastAPI-powered web interface that surfaces the available tools and lets you run them without writing client code.

### 7.1 Start the Playground Server

```bash
python start_playground.py
```

On startup you will see terminal output similar to:
```
🚀 Starting MCP Playground Server...
📍 UI: http://0.0.0.0:8080
🔧 API: http://0.0.0.0:8080/api
```

Leave this process running while you interact with the UI.

### 7.2 Access the UI

Open a browser to `http://localhost:8080`. The interface is split into:
- **Tool list (left panel)** – available tools grouped by category with descriptions.
- **Execution workspace (center)** – dynamic input form generated from the tool's parameters and a result panel.
- **API preview (bottom)** – live JSON payload representing the request made to the server, ready to copy for use in clients or tests.

### 7.3 Executing a Tool

1. Select a tool from the left panel. The form updates to match its parameters.
2. Enter parameter values. Required fields are marked; optional fields can be left blank.
3. Click **Execute Tool**. The result panel shows formatted output, execution time, and any errors.
4. Copy the API payload or result using the provided buttons if you want to replay the request elsewhere.

### 7.4 Playground API Endpoints

The Playground exposes a REST API under `/api` that mirrors the UI operations:

- `GET /api/tools` – discover available tools and their parameter schema.
- `POST /api/execute` – execute a tool; body must include `tool` and `parameters`.
- `GET /api/health` – health and uptime information.
- `GET /api/server/info` – server metadata and enabled features.

## 8. Troubleshooting Tips

### 8.1 SSE Connection Issues
- **401 Unauthorized**: Check your `MCP_BEARER_TOKEN` environment variable and ensure it matches the token used in API calls
- **Connection timeouts**: Ensure the SSE server is running on port 8080 and accessible from your LangChain application
- **CORS errors**: The SSE server includes CORS headers, but ensure your client supports SSE connections

### 8.2 Standard MCP Issues
- **Missing tools:** Ensure `MCP_ENABLED_TOOLS_CONFIG` lists the tool names (`calculator`, `web_search`, `web_fetch`, `pdf_generate`); restart the server after changes.
- **Timeouts:** Increase `MCP_MAX_TOOL_EXECUTION_TIME` in `.env` for long-running operations.
- **Third-party requests fail:** Verify network access and confirm any required API keys are set.

### 8.3 General Issues
- **Playground not loading assets:** Run `start_playground.py` from the repository root so static files resolve correctly.
- **Docker deployment fails:** Check logs with `docker-compose logs mcp-sse-server` and ensure all environment variables are set.

## 9. Additional Resources

- `README.md` – high-level overview and quick start.
- `docs/` directory – deep dives into configuration, testing strategy, deployment, and advanced usage.
- `playground/web_server.py` – reference implementation of the Playground API and tool integrations.
- `langchain_sse_config.json` – Example LangChain configuration for SSE integration.

With these steps you can run the MCP server in both stdio and SSE modes, verify its behavior, experiment interactively using the Playground UI, and integrate with LangChain applications using SSE transport.