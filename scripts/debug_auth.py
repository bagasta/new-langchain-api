#!/usr/bin/env python3

import requests
import json

# Test with login JWT (should fail)
login_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjE5MDQ1NjUsInN1YiI6IjgwZWI3OGNlLTYxYTAtNGQzOS1iMWUwLTgwNTA0NTY3MThjNSJ9.ONo5Yk76ECa2o6DvyCJuku9pLhuUlXRQxoP0U4Nhqmo"
api_key_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjE5MDQ1ODgsInN1YiI6IjgwZWI3OGNlLTYxYTAtNGQzOS1iMWUwLTgwNTA0NTY3MThjNSJ9.KkJuHo-3rHfLQm__qlbijplQAXy70sIaSVIYbkBu748"

print("Testing with login JWT:")
response = requests.get(
    "http://localhost:8000/api/v1/agents/",
    headers={"Authorization": f"Bearer {login_token}"}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
print()

print("Testing with API key:")
response = requests.get(
    "http://localhost:8000/api/v1/agents/",
    headers={"Authorization": f"Bearer {api_key_token}"}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")