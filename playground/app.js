(function () {
  const STORAGE_KEY = "langchain-playground-config";
  const baseUrlInput = document.getElementById("base-url");
  const tokenInput = document.getElementById("auth-token");
  const responseStatus = document.getElementById("response-status");
  const responseOutput = document.getElementById("response-output");
  const clearResponseBtn = document.getElementById("clear-response");
  const clearTokenBtn = document.getElementById("clear-token");

  initConfig();
  bindGlobalActions();
  bindAuthForms();
  bindAgentForms();
  bindToolForms();
  bindTestingFlow();

  function initConfig() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.baseUrl) {
          baseUrlInput.value = parsed.baseUrl;
        }
        if (parsed.token) {
          tokenInput.value = parsed.token;
        }
      }
    } catch (err) {
      console.warn("Failed to restore playground config", err);
    }

    const persist = () => {
      const payload = {
        baseUrl: baseUrlInput.value.trim(),
        token: tokenInput.value.trim()
      };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      } catch (err) {
        console.warn("Failed to persist playground config", err);
      }
    };

    baseUrlInput.addEventListener("change", persist);
    baseUrlInput.addEventListener("blur", persist);
    tokenInput.addEventListener("change", persist);
    tokenInput.addEventListener("blur", persist);
    clearTokenBtn.addEventListener("click", () => {
      tokenInput.value = "";
      persist();
    });
  }

  function bindGlobalActions() {
    clearResponseBtn.addEventListener("click", () => {
      responseStatus.textContent = "Waiting for request…";
      responseOutput.textContent = "";
    });
  }

  function bindAuthForms() {
    handleSubmit("form-login", async () => {
      const email = valueOf("login-email");
      const password = valueOf("login-password");
      const result = await apiRequest({
        method: "POST",
        path: "/auth/login",
        query: { email, password }
      });
      if (result.ok && result.data && result.data.access_token) {
        tokenInput.value = result.data.access_token;
        persistToken();
      }
    });

    handleSubmit("form-register", async () => {
      const email = valueOf("register-email");
      const password = valueOf("register-password");
      const result = await apiRequest({
        method: "POST",
        path: "/auth/register",
        query: { email, password }
      });
      if (result.ok && result.data && result.data.access_token) {
        tokenInput.value = result.data.access_token;
        persistToken();
      }
    });

    document.getElementById("btn-auth-me").addEventListener("click", async () => {
      await apiRequest({ method: "GET", path: "/auth/me", auth: true });
    });

    document.getElementById("btn-auth-tokens").addEventListener("click", async () => {
      await apiRequest({ method: "GET", path: "/auth/tokens", auth: true });
    });

    handleSubmit("form-google-auth", async () => {
      const email = valueOf("google-email");
      await apiRequest({
        method: "POST",
        path: "/auth/google/auth",
        body: { email },
        auth: true
      });
    });

    handleSubmit("form-google-callback", async () => {
      const code = valueOf("google-code");
      const state = valueOf("google-state");
      await apiRequest({
        method: "GET",
        path: "/auth/google/callback",
        query: { code, state }
      });
    });
  }

  function bindAgentForms() {
    handleSubmit("form-agent-create", async () => {
      const name = valueOf("agent-name");
      const toolsRaw = document.getElementById("agent-tools").value;
      const tools = toolsRaw
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      const config = {
        llm_model: valueOf("agent-model") || "gpt-3.5-turbo",
        temperature: parseFloat(valueOf("agent-temperature") || "0.7"),
        max_tokens: parseInt(valueOf("agent-max-tokens") || "1000", 10),
        memory_type: valueOf("agent-memory") || "buffer",
        reasoning_strategy: valueOf("agent-strategy") || "react"
      };

      await apiRequest({
        method: "POST",
        path: "/agents/",
        body: { name, tools, config },
        auth: true
      });
    });

    document.getElementById("btn-agents-list").addEventListener("click", async () => {
      await apiRequest({ method: "GET", path: "/agents/", auth: true });
    });

    document.getElementById("btn-agent-fetch").addEventListener("click", async () => {
      const agentId = valueOf("agent-id");
      await apiRequest({ method: "GET", path: `/agents/${agentId}`, auth: true });
    });

    document.getElementById("btn-agent-delete").addEventListener("click", async () => {
      const agentId = valueOf("agent-id");
      await apiRequest({ method: "DELETE", path: `/agents/${agentId}`, auth: true });
    });

    handleSubmit("form-agent-update", async () => {
      const agentId = valueOf("agent-id");
      const name = document.getElementById("agent-update-name").value.trim();
      const status = document.getElementById("agent-update-status").value;

      const payload = {};
      if (name) {
        payload.name = name;
      }
      if (status) {
        payload.status = status;
      }

      if (!Object.keys(payload).length) {
        renderError(new Error("Provide name or status to update."), "Update skipped");
        return;
      }

      await apiRequest({
        method: "PUT",
        path: `/agents/${agentId}`,
        body: payload,
        auth: true
      });
    });

    handleSubmit("form-agent-execute", async () => {
      const agentId = valueOf("execute-agent-id");
      const input = valueOf("execute-input");
      const paramsRaw = document.getElementById("execute-params").value.trim();
      const parameters = paramsRaw ? parseJson(paramsRaw, "Execution parameters") : {};

      await apiRequest({
        method: "POST",
        path: `/agents/${agentId}/execute`,
        body: { input, parameters },
        auth: true
      });
    });

    document.getElementById("btn-agent-executions").addEventListener("click", async () => {
      const agentId = valueOf("execute-agent-id");
      await apiRequest({
        method: "GET",
        path: `/agents/${agentId}/executions`,
        auth: true
      });
    });

    document.getElementById("btn-agent-stats").addEventListener("click", async () => {
      await apiRequest({
        method: "GET",
        path: "/agents/executions/stats",
        auth: true
      });
    });
  }

  function bindToolForms() {
    handleSubmit("form-tools-list", async () => {
      const toolType = document.getElementById("tools-type").value.trim();
      const query = toolType ? { tool_type: toolType } : undefined;
      await apiRequest({ method: "GET", path: "/tools", query, auth: true });
    });

    handleSubmit("form-tool-create", async () => {
      const name = valueOf("tool-name");
      const description = document.getElementById("tool-description").value.trim();
      const schemaRaw = document.getElementById("tool-schema").value.trim();
      const schema = parseJson(schemaRaw, "Tool schema");
      const type = document.getElementById("tool-type").value;

      await apiRequest({
        method: "POST",
        path: "/tools",
        body: {
          name,
          description: description || null,
          schema,
          type
        },
        auth: true
      });
    });

    document.getElementById("btn-tool-fetch").addEventListener("click", async () => {
      const toolId = valueOf("tool-id");
      await apiRequest({ method: "GET", path: `/tools/${toolId}`, auth: true });
    });

    document.getElementById("btn-tool-delete").addEventListener("click", async () => {
      const toolId = valueOf("tool-id");
      await apiRequest({ method: "DELETE", path: `/tools/${toolId}`, auth: true });
    });

    handleSubmit("form-tool-update", async () => {
      const toolId = valueOf("tool-id");
      const description = document.getElementById("tool-update-description").value.trim();
      const schemaRaw = document.getElementById("tool-update-schema").value.trim();

      const payload = {};
      if (description) {
        payload.description = description;
      }
      if (schemaRaw) {
        payload.schema = parseJson(schemaRaw, "Tool schema");
      }

      if (!Object.keys(payload).length) {
        renderError(new Error("Provide a description or schema to update."), "Update skipped");
        return;
      }

      await apiRequest({
        method: "PUT",
        path: `/tools/${toolId}`,
        body: payload,
        auth: true
      });
    });

    handleSubmit("form-tool-execute", async () => {
      const toolId = valueOf("execute-tool-id");
      const paramsRaw = document.getElementById("execute-tool-params").value.trim();
      const parameters = parseJson(paramsRaw, "Execution parameters");

      await apiRequest({
        method: "POST",
        path: "/tools/execute",
        body: {
          tool_id: toolId,
          parameters
        },
        auth: true
      });
    });

    handleSubmit("form-tool-schema", async () => {
      const toolName = valueOf("schema-tool-name");
      await apiRequest({
        method: "GET",
        path: `/tools/schemas/${toolName}`,
        auth: true
      });
    });

    handleSubmit("form-tool-scopes", async () => {
      const toolsRaw = valueOf("scope-tools");
      await apiRequest({
        method: "GET",
        path: "/tools/scopes/required",
        query: { tools: toolsRaw },
        auth: true
      });
    });
  }

  async function apiRequest({ method = "GET", path, query, body, auth = false }) {
    const baseUrl = sanitizeBaseUrl(baseUrlInput.value);
    if (!baseUrl) {
      throw new Error("Base URL is required.");
    }

    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    let url = `${baseUrl}${cleanPath}`;

    if (query && Object.keys(query).length) {
      const params = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => {
        if (value !== undefined && value !== null && String(value).length) {
          params.append(key, value);
        }
      });
      const qs = params.toString();
      if (qs) {
        url += `?${qs}`;
      }
    }

    const headers = { Accept: "application/json" };
    let payload;

    if (body !== undefined && body !== null) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }

    if (auth) {
      const token = tokenInput.value.trim();
      if (!token) {
        throw new Error("Authorization token is required for this request.");
      }
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method,
      headers,
      body: payload
    });

    const contentType = response.headers.get("content-type") || "";
    let data;
    if (contentType.includes("application/json")) {
      try {
        data = await response.json();
      } catch (err) {
        data = null;
      }
    } else {
      data = await response.text();
    }

    renderResponse({ method, url, query, body }, response, data);

    return {
      ok: response.ok,
      status: response.status,
      data
    };
  }

  function renderResponse(request, response, data) {
    const statusLine = `${request.method.toUpperCase()} ${request.url} → ${response.status} ${response.statusText}`;
    responseStatus.textContent = statusLine;

    const headers = {};
    response.headers.forEach((value, key) => {
      headers[key] = value;
    });

    const payload = {
      request: {
        method: request.method,
        url: request.url,
        query: request.query && Object.keys(request.query).length ? request.query : undefined,
        body: request.body
      },
      response: {
        status: response.status,
        statusText: response.statusText,
        headers,
        data
      }
    };

    responseOutput.textContent = JSON.stringify(payload, null, 2);
  }

  function handleSubmit(formId, handler) {
    const form = document.getElementById(formId);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await handler(event);
      } catch (err) {
        renderError(err, "Request failed");
      }
    });
  }

  function valueOf(elementId) {
    return document.getElementById(elementId).value.trim();
  }

  function parseJson(text, label) {
    try {
      return JSON.parse(text);
    } catch (err) {
      throw new Error(`${label} is not valid JSON.`);
    }
  }

  function renderError(error, context) {
    const message = error instanceof Error ? error.message : String(error);
    responseStatus.textContent = `${context}: ${message}`;
    responseOutput.textContent = message;
  }

  function sanitizeBaseUrl(value) {
    if (!value) {
      return "";
    }
    return value.replace(/\/$/, "");
  }

  function persistToken() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const baseUrl = sanitizeBaseUrl(baseUrlInput.value);
      const payload = stored ? JSON.parse(stored) : {};
      payload.baseUrl = baseUrl;
      payload.token = tokenInput.value.trim();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (err) {
      console.warn("Failed to save token", err);
    }
  }

  // Testing Flow Functions
  function bindTestingFlow() {
    document.getElementById("btn-run-flow").addEventListener("click", runTestingFlow);
    document.getElementById("btn-reset-flow").addEventListener("click", resetTestingFlow);
    document.getElementById("copy-response").addEventListener("click", copyResponse);
  }

  async function runTestingFlow() {
    resetTestingFlow();

    const flowSteps = [
      { step: 'register', name: 'Register User', execute: executeRegisterStep },
      { step: 'login', name: 'Login', execute: executeLoginStep },
      { step: 'agent', name: 'Create Agent', execute: executeAgentStep },
      { step: 'execute', name: 'Execute Agent', execute: executeExecuteStep }
    ];

    for (const flowStep of flowSteps) {
      try {
        await updateStepStatus(flowStep.step, 'pending', `Running ${flowStep.name}...`);
        await flowStep.execute();
        await updateStepStatus(flowStep.step, 'success', `${flowStep.name} completed successfully`);

        // Add a small delay between steps for better UX
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (error) {
        await updateStepStatus(flowStep.step, 'error', `${flowStep.name} failed: ${error.message}`);
        break;
      }
    }
  }

  function resetTestingFlow() {
    const steps = ['register', 'login', 'agent', 'execute'];
    steps.forEach(step => {
      updateStepStatus(step, 'pending', 'Pending');
    });
  }

  async function updateStepStatus(step, status, message) {
    const stepElement = document.querySelector(`[data-step="${step}"]`);
    if (!stepElement) return;

    const statusElement = stepElement.querySelector('.step-status');
    statusElement.className = `step-status ${status}`;
    statusElement.textContent = message;

    // Add animation
    stepElement.classList.add('fade-in');
    setTimeout(() => stepElement.classList.remove('fade-in'), 300);
  }

  async function executeRegisterStep() {
    const testEmail = `testuser${Date.now()}@example.com`;
    const testPassword = 'TestPassword123!';

    const result = await apiRequest({
      method: "POST",
      path: "/auth/register",
      query: { email: testEmail, password: testPassword }
    });

    if (result.ok && result.data && result.data.access_token) {
      tokenInput.value = result.data.access_token;
      persistToken();

      // Store test credentials for login step
      localStorage.setItem('test-email', testEmail);
      localStorage.setItem('test-password', testPassword);

      // Update form fields with test credentials
      document.getElementById('login-email').value = testEmail;
      document.getElementById('login-password').value = testPassword;

      return result.data;
    } else {
      throw new Error('Registration failed');
    }
  }

  async function executeLoginStep() {
    const testEmail = localStorage.getItem('test-email');
    const testPassword = localStorage.getItem('test-password');

    if (!testEmail || !testPassword) {
      throw new Error('Test credentials not found. Please run the register step first.');
    }

    const result = await apiRequest({
      method: "POST",
      path: "/auth/login",
      query: { email: testEmail, password: testPassword }
    });

    if (result.ok && result.data && result.data.access_token) {
      tokenInput.value = result.data.access_token;
      persistToken();
      return result.data;
    } else {
      throw new Error('Login failed');
    }
  }

  async function executeAgentStep() {
    const agentName = `TestAgent${Date.now()}`;
    const tools = ['gmail']; // Using Gmail tool as it's commonly available

    const config = {
      llm_model: "gpt-3.5-turbo",
      temperature: 0.7,
      max_tokens: 1000,
      memory_type: "buffer",
      reasoning_strategy: "react"
    };

    const result = await apiRequest({
      method: "POST",
      path: "/agents/",
      body: { name: agentName, tools, config },
      auth: true
    });

    if (result.ok && result.data) {
      // Store agent ID for execution step
      localStorage.setItem('test-agent-id', result.data.id);

      // Update form fields with agent data
      document.getElementById('agent-name').value = agentName;
      document.getElementById('agent-tools').value = tools.join(',');
      document.getElementById('agent-model').value = config.llm_model;
      document.getElementById('agent-temperature').value = config.temperature;
      document.getElementById('agent-max-tokens').value = config.max_tokens;
      document.getElementById('agent-memory').value = config.memory_type;
      document.getElementById('agent-strategy').value = config.reasoning_strategy;
      document.getElementById('execute-agent-id').value = result.data.id;

      return result.data;
    } else {
      throw new Error('Agent creation failed');
    }
  }

  async function executeExecuteStep() {
    const agentId = localStorage.getItem('test-agent-id');

    if (!agentId) {
      throw new Error('Test agent ID not found. Please run the create agent step first.');
    }

    const result = await apiRequest({
      method: "POST",
      path: `/agents/${agentId}/execute`,
      body: {
        input: "List my recent emails and summarize them briefly.",
        parameters: {},
        session_id: "test-session-flow"
      },
      auth: true
    });

    if (result.ok) {
      return result.data;
    } else {
      throw new Error('Agent execution failed');
    }
  }

  async function copyResponse() {
    const responseText = responseOutput.textContent;
    if (!responseText) {
      showNotification('No response to copy', 'warning');
      return;
    }

    try {
      await navigator.clipboard.writeText(responseText);
      showNotification('Response copied to clipboard!', 'success');
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = responseText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      showNotification('Response copied to clipboard!', 'success');
    }
  }

  function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());

    // Create new notification
    const notification = document.createElement('div');
    notification.className = `notification status-indicator ${type}`;
    notification.innerHTML = `
      <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
      <span>${message}</span>
    `;

    // Position the notification
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '10000';
    notification.style.maxWidth = '300px';

    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Enhanced response rendering with better formatting
  function renderResponse(request, response, data) {
    const statusLine = `${request.method.toUpperCase()} ${request.url} → ${response.status} ${response.statusText}`;

    // Update status indicator
    const statusIndicator = document.getElementById('response-status');
    statusIndicator.className = `status-indicator ${response.ok ? 'success' : 'error'}`;
    statusIndicator.innerHTML = `
      <span>${response.ok ? '✅' : '❌'}</span>
      <span>${statusLine}</span>
    `;

    const headers = {};
    response.headers.forEach((value, key) => {
      headers[key] = value;
    });

    const payload = {
      timestamp: new Date().toISOString(),
      request: {
        method: request.method,
        url: request.url,
        query: request.query && Object.keys(request.query).length ? request.query : undefined,
        body: request.body
      },
      response: {
        status: response.status,
        statusText: response.statusText,
        headers,
        data
      }
    };

    responseOutput.textContent = JSON.stringify(payload, null, 2);

    // Add syntax highlighting for JSON
    if (response.ok) {
      responseOutput.style.color = '#10b981';
    } else {
      responseOutput.style.color = '#ef4444';
    }
  }

  // Override the original renderResponse function
  window.renderResponse = renderResponse;
})();
