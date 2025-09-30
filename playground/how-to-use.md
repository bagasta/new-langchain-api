# LangChain API Playground - How to Use

## Overview
The LangChain API Playground is an interactive testing environment that allows you to test all endpoints of the LangChain Agent API. This guide will help you understand how to use the playground effectively.

## Prerequisites

Before using the playground, ensure you have:

1. **FastAPI Server Running**:
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Environment Variables Configured**:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `GOOGLE_CLIENT_ID` - Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
   - `DATABASE_URL` - PostgreSQL connection string
   - `SECRET_KEY` - JWT secret key

3. **Browser Compatibility**:
   - Modern browser with JavaScript ES6+ support
   - LocalStorage enabled for token persistence

## Getting Started

### 1. Configuration
- **Base URL**: Set to your API endpoint (default: `http://localhost:8000/api/v1`)
- **Bearer Token**: Automatically populated after login or enter manually

### 2. Guided Testing Flow
The playground provides a 4-step automated testing flow:

#### Step 1: Register User
- Creates a new user account
- Automatically logs in after successful registration
- Returns access token for subsequent operations

#### Step 2: Login
- Authenticates with email and password
- Stores access token automatically
- Validates user credentials

#### Step 3: Create Agent
- Creates an AI agent with configurable parameters
- Assigns tools to the agent
- Sets up execution environment

#### Step 4: Execute Agent
- Tests the agent with sample input
- Executes assigned tools
- Returns results and execution logs

### Running the Flow
1. Click **🚀 Run Full Flow** to execute all steps automatically
2. Each step will update its status (Pending → Running → Success/Error)
3. View detailed results in the Response Log
4. Use **🔄 Reset Flow** to start over

## Manual Testing

### Authentication
- **Login**: Use existing credentials
- **Register**: Create new account
- **Profile**: Get current user info
- **Google OAuth**: Test Google authentication flow

### Agents
- **Create Agent**: Configure AI agent with tools and parameters
- **Manage Agent**: Update, fetch, or delete agents
- **Execute Agent**: Run agent with custom input
- **List Agents**: View all your agents

### Tools
- **List Tools**: Browse available tools (BUILTIN/CUSTOM)
- **Create Tool**: Register custom tools with JSON schema
- **Manage Tool**: Update or delete tools
- **Execute Tool**: Test individual tools
- **Metadata**: Get tool schemas and required scopes

## Response Log

The Response Log shows detailed information about each API call:
- **Status**: Success/Error indicators
- **Request**: Method, URL, and payload
- **Response**: JSON response data
- **Timing**: Execution duration
- **Copy**: Copy response to clipboard

## Features

### Testing Flow Controls
- **🚀 Run Full Flow**: Execute complete workflow
- **🔄 Reset Flow**: Clear all progress and start over
- **Step-by-Step**: Individual step status tracking

### Configuration Management
- **Base URL**: Easy API endpoint configuration
- **Token Management**: Automatic token handling
- **Clear Token**: Manual token clearing

### Response Features
- **Syntax Highlighting**: JSON response formatting
- **Copy to Clipboard**: Easy result sharing
- **Clear Log**: Reset response display
- **Status Indicators**: Visual success/error feedback

## Common Use Cases

### 1. First-Time Setup
1. Start with the guided testing flow
2. Complete registration and login
3. Create your first agent
4. Test agent execution

### 2. Agent Development
1. Create custom tools
2. Configure agents with specific tools
3. Test agent execution with various inputs
4. Monitor execution performance

### 3. Integration Testing
1. Test authentication flows
2. Verify tool registration
3. Validate agent execution
4. Check error handling

### 4. Google OAuth Testing
1. Create auth URL with Google email
2. Process OAuth callback
3. Verify token storage
4. Test Google tool execution

## Troubleshooting

### Common Issues

**Server Not Running**
- Ensure FastAPI server is started with `uvicorn app.main:app --reload`
- Check server logs for errors

**Authentication Errors**
- Verify environment variables are set
- Check database connection
- Clear browser cache and tokens

**Agent Execution Failures**
- Verify OpenAI API key is valid
- Check tool configurations
- Review execution logs

**Google OAuth Issues**
- Verify Google OAuth credentials
- Check redirect URL configuration
- Ensure proper scope permissions

### Debug Tips

1. **Check Response Log**: Detailed error messages and stack traces
2. **Browser Console**: JavaScript errors and network requests
3. **Server Logs**: Backend errors and database queries
4. **Environment Variables**: Verify all required variables are set

## Best Practices

### Testing Workflow
1. Always start with the guided flow for new setups
2. Test individual components before full integration
3. Use the reset flow feature between test runs
4. Monitor response times and error rates

### Security
1. Never commit API keys to version control
2. Use environment variables for sensitive data
3. Clear tokens after testing sessions
4. Verify OAuth scope requirements

### Performance
1. Monitor execution times for agent runs
2. Test with various input sizes
3. Check database query performance
4. Verify API response times

## Advanced Features

### Custom Tool Development
1. Create tools with JSON schema validation
2. Test tool execution independently
3. Integrate with agent workflows
4. Monitor tool performance metrics

### Agent Configuration
1. Experiment with different LLM models
2. Adjust temperature and token limits
3. Test various memory types
4. Compare reasoning strategies

### Authentication Testing
1. Test JWT token expiration
2. Verify refresh token functionality
3. Test OAuth with different providers
4. Validate permission scopes

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review server and browser logs
3. Verify configuration settings
4. Test with minimal configurations

## Next Steps

After mastering the playground:
1. Integrate with your applications
2. Develop custom tools
3. Build agent workflows
4. Scale to production environments

---

*The LangChain API Playground is designed to make API testing intuitive and efficient. Start with the guided flow, then explore individual components as needed.*