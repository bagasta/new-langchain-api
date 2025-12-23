import random
import string
import os
from locust import HttpUser, task, between, SequentialTaskSet

# Global list to share registered users between tasks if needed, 
# though SequentialTaskSet keeps state per user instance.
# We'll stick to per-user state for the full workflow.

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class UserWorkflow(SequentialTaskSet):
    def on_start(self):
        self.email = f"user_{random_string()}@example.com"
        self.password = "securepassword123"
        self.jwt_token = None
        self.api_key = None
        self.agent_id = None
        self.headers = {"Content-Type": "application/json"}

    @task
    def register(self):
        """
        Test Register Endpoint.
        """
        payload = {
            "email": self.email,
            "password": self.password
        }
        with self.client.post(
            "/api/v1/auth/register", 
            params=payload, 
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Registration failed: {response.text}")
                self.interrupt()

    @task
    def activate_account(self):
        """
        Step 2: Activate the account.
        This is required before Login.
        """
        with self.client.post(
            f"/api/v1/auth/activate",
            params={"email": self.email},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Activation failed: {response.text}")
                self.interrupt()

    @task
    def login(self):
        """
        Step 3: Login to get JWT Token.
        """
        payload = {
            "email": self.email,
            "password": self.password
        }
        with self.client.post(
            "/api/v1/auth/login", 
            params=payload, 
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("jwt_token")
                # Set Authorization header for the next step (Generate API Key)
                self.headers["Authorization"] = f"Bearer {self.jwt_token}"
                response.success()
            else:
                response.failure(f"Login failed: {response.text}")
                self.interrupt()

    @task
    def generate_api_key(self):
        """
        Step 4: Generate API Key.
        Requires JWT Token (set in headers during login).
        """
        if not self.jwt_token:
            self.interrupt()
            return

        payload = {
            "username": self.email,
            "password": self.password,
            "plan_code": "PRO_M"
        }
        
        # Note: The endpoint might expect the JWT token in the header, 
        # which we set in the login task.
        with self.client.post(
            "/api/v1/auth/api-key",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.api_key = data.get("access_token")
                # Update headers to use API Key for Agent operations
                self.headers["Authorization"] = f"Bearer {self.api_key}"
                response.success()
            else:
                response.failure(f"API Key Generation failed: {response.text}")
                self.interrupt()

    @task
    def create_agent(self):
        """
        Step 5: Create Agent.
        Requires API Key.
        """
        if not self.api_key:
            self.interrupt()
            return

        payload = {
            "name": f"LoadTest Agent {random_string(5)}",
            "config": {
                "llm_model": "gpt-4o-mini",
                "system_prompt": "You are a helpful assistant for load testing.",
                "temperature": 0.7
            },
            "allowed_tools": ["calculator"]
        }
        
        with self.client.post(
            "/api/v1/agents/", 
            json=payload, 
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.agent_id = data.get("id")
                response.success()
            else:
                response.failure(f"Create Agent failed: {response.text}")
                self.interrupt()

    @task
    def upload_document(self):
        """
        Step 6: Upload Document (RAG).
        Requires API Key and Agent ID.
        """
        if not self.agent_id or not self.api_key:
            return

        file_path = os.path.join(os.path.dirname(__file__), "test_doc.txt")
        # Use API Key for auth
        auth_header = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": ("test_doc.txt", f, "text/plain")}
                with self.client.post(
                    f"/api/v1/agents/{self.agent_id}/documents",
                    headers=auth_header,
                    files=files,
                    catch_response=True
                ) as response:
                    if response.status_code == 200:
                        response.success()
                    else:
                        response.failure(f"Document Upload failed: {response.text}")
                        self.interrupt()
        except FileNotFoundError:
            print(f"Test file not found at {file_path}")
            self.interrupt()

    @task
    def execute_agent(self):
        """
        Step 7: Execute Agent.
        Requires API Key and Agent ID.
        """
        if not self.agent_id or not self.api_key:
            return

        payload = {
            "input": "Summarize the document I just uploaded.",
            "session_id": f"session_{random_string()}"
        }

        with self.client.post(
            f"/api/v1/agents/{self.agent_id}/execute",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Execute Agent failed: {response.text}")

    @task
    def stop(self):
        """End the workflow for this user"""
        self.interrupt()

class WebsiteUser(HttpUser):
    tasks = [UserWorkflow]
    wait_time = between(1, 5)
