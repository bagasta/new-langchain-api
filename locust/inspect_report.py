import re
import os

file_path = os.path.join(os.path.dirname(__file__), "report", "load-testing(100 Users 30s).html")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Look for JSON data assignments
matches = re.findall(r'(?:var|const|let)\s+(\w+)\s*=\s*({.*?}|\[.*?\]);', content, re.DOTALL)

print(f"Found {len(matches)} data variables.")
for name, data in matches:
    print(f"Variable: {name}, Length: {len(data)}")
    if len(data) < 500:
        print(f"Data: {data}")
    else:
        print(f"Data (truncated): {data[:200]}...")
