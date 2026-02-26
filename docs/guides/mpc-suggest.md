# LangChain MCP Integration Guide

This guide explains how to integrate your MCP server with LangChain applications.

## 📋 Table of Contents
1. [Understanding MCP Server Configuration](#understanding-mcp-server-configuration)
2. [Setting Up MCP Server](#setting-up-mcp-server)
3. [LangChain Configuration](#langchain-configuration)
4. [Multiple MCP Servers](#multiple-mcp-servers)
5. [Testing Integration](#testing-integration)
6. [Troubleshooting](#troubleshooting)

## 🔍 Understanding MCP Server Configuration

### What is `my_mcp_server`?

`my_mcp_server` is simply an **identifier/name** that you define in your LangChain configuration. It's not something that comes from the MCP server itself, but rather a name you give to your MCP server connection.

**Think of it like a variable name** - you can name it anything you want:

```json
{
  "mcp_servers": {
    "my_mcp_server": { ... },     // Your choice
    "math_tools": { ... },        // Also valid
    "web_scraper": { ... },       // Also valid
    "production_mcp": { ... }     // Also valid
  }
}
```

## 🚀 Setting Up MCP Server

### Step 1: Start Your MCP Server

```bash
# Generate a secure token (optional helper)
python generate_token.py

# Start server with your token using streamable HTTP transport
export MCP_BEARER_TOKEN="your-generated-token"
python streamable_http_server.py --port 8080
```

### Step 2: Verify Server is Running

```bash
# Test health endpoint
curl -H "Authorization: Bearer your-token" http://localhost:8080/health

# Optional: inspect manifest / tool list
curl -X POST http://localhost:8080/mcp/stream \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## 🔧 LangChain Configuration

### Basic Configuration

Create a configuration file for your LangChain agent:

```json
{
  "name": "Agent dengan External MCP",
  "mcp_servers": {
    "my_mcp_server": {
      "transport": "streamable_http",
      "url": "http://localhost:8001/mcp/",
      "headers": {
        "Authorization": "Bearer your-generated-token"
      }
    }
  },
  "allowed_tools": ["calculator", "web_search", "web_fetch", "pdf_generate"]
}
```

### Configuration Options

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Agent name | "Agent dengan External MCP" |
| `mcp_servers` | MCP server configurations | `{ "server_name": { ... } }` |
| `transport` | Transport type | "streamable_http" |
| `url` | MCP server endpoint | "http://localhost:8080/mcp/stream" |
| `headers` | Authentication headers | `{ "Authorization": "Bearer token" }` |
| `allowed_tools` | List of tools agent can use | `["calculator", "web_search"]` |

## 🎯 Naming Your MCP Server

Choose a meaningful name for your MCP server:

### Good Examples:
```json
{
  "mcp_servers": {
    "math_calculator": { ... },
    "web_research_tools": { ... },
    "pdf_generator": { ... },
    "production_mcp": { ... }
  }
}
```

### Naming Conventions:
- Use lowercase letters and underscores
- Be descriptive of the server's purpose
- Keep it short but meaningful
- Avoid spaces and special characters

## 🔗 Multiple MCP Servers

You can connect to multiple MCP servers:

```json
{
  "name": "Multi-Tool Agent",
  "mcp_servers": {
    "math_tools": {
      "transport": "streamable_http",
      "url": "http://localhost:8080/mcp/stream",
      "headers": {
        "Authorization": "Bearer math-token"
      }
    },
    "web_tools": {
      "transport": "streamable_http",
      "url": "http://localhost:9000/mcp/stream",
      "headers": {
        "Authorization": "Bearer web-token"
      }
    },
    "pdf_tools": {
      "transport": "streamable_http",
      "url": "http://localhost:7000/mcp/stream",
      "headers": {
        "Authorization": "Bearer pdf-token"
      }
    }
  },
  "allowed_tools": [
    "calculator", "web_search", "web_fetch", "pdf_generate"
  ]
}
```

### Setting Up Multiple Servers:

```bash
# Terminal 1: Math tools server
export MCP_BEARER_TOKEN="math-token-123"
python streamable_http_server.py --port 8080

# Terminal 2: Web tools server
export MCP_BEARER_TOKEN="web-token-456"
python streamable_http_server.py --port 9000

# Terminal 3: PDF tools server
export MCP_BEARER_TOKEN="pdf-token-789"
python streamable_http_server.py --port 7000
```

## 🧪 Testing Integration

### Test Individual MCP Servers

```bash
# Test math server
curl -H "Authorization: Bearer math-token-123" \
     http://localhost:8080/tools

# Test web server
curl -H "Authorization: Bearer web-token-456" \
     http://localhost:9000/tools

# Test PDF server
curl -H "Authorization: Bearer pdf-token-789" \
     http://localhost:7000/tools
```

### Test Tool Execution

```bash
# Test calculator
curl -X POST \
  -H "Authorization: Bearer math-token-123" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"expression": "2+2"}}' \
  http://localhost:8080/tools/calculator/call
```

### Test in LangChain

```python
# Example LangChain integration
from langchain.agents import create_openai_functions_agent
from langchain_openai import ChatOpenAI

# Your MCP configuration
mcp_config = {
    "name": "Test Agent",
    "mcp_servers": {
        "my_mcp_server": {
            "transport": "streamable_http",
            "url": "http://localhost:8080/mcp/stream",
            "headers": {
                "Authorization": "Bearer your-token"
            }
        }
    },
    "allowed_tools": ["calculator", "web_search"]
}

# Create agent with MCP tools
# (This depends on your LangChain setup)
```

## 🔍 Troubleshooting

### Common Issues:

#### 1. Connection Refused
```bash
# Error: Connection refused
# Solution: Make sure MCP server is running
curl -H "Authorization: Bearer your-token" http://localhost:8080/health
```

#### 2. Authentication Failed
```bash
# Error: 401 Unauthorized
# Solution: Check your Bearer token
export MCP_BEARER_TOKEN="correct-token"
python streamable_http_server.py
```

#### 3. Tools Not Found
```bash
# Error: Tool 'calculator' not found
# Solution: Check allowed_tools list
# Make sure tool names match exactly
```

#### 4. Stream Connection Issues
```bash
# Error: stream connection timeout
# Solution: Check firewall and network connectivity
# Verify port accessibility
telnet localhost 8080
```

### Debug Mode:

Enable debug logging:

```bash
export MCP_LOG_LEVEL=DEBUG
export MCP_BEARER_TOKEN="your-token"
python streamable_http_server.py --port 8080
```

## 📝 Best Practices

1. **Security**: Use strong, unique tokens for each environment
2. **Naming**: Use descriptive names for your MCP servers
3. **Ports**: Use different ports for multiple servers
4. **Monitoring**: Check server health regularly
5. **Documentation**: Keep track of your configurations

## 🎯 Quick Start Checklist

- [ ] Generate secure token: `python generate_token.py`
- [ ] Start MCP server: `python streamable_http_server.py --port 8080`
- [ ] Test server health: `curl -H "Authorization: Bearer token" http://localhost:8080/health`
- [ ] Create LangChain config with meaningful server name
- [ ] Test tool execution
- [ ] Verify LangChain integration

## 📚 Additional Resources

- [FastMCP Documentation](https://gofastmcp.com)
- [LangChain Documentation](https://python.langchain.com)
- [HTTP Streaming Overview](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#streaming_responses)

---

💡 **Pro Tip**: The `my_mcp_server` name is entirely up to you - choose something that makes sense for your application!
