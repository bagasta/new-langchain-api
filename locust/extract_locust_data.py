import re
import json
import sys
import os

file_path = os.path.join(os.path.dirname(__file__), "report", "load-testing(100 Users 30s).html")

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try to find the data
    # Locust reports often use 'stats_history' or just embed data in a script
    # Look for "var stats_history =" or "window.stats_history ="
    
    # Pattern for stats_history
    pattern = r'(?:var|window\.)stats_history\s*=\s*(\{.*?\}|\[.*?\]);'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        print("Found stats_history")
        data_str = match.group(1)
        # It might be a large JSON, let's try to parse it
        try:
            data = json.loads(data_str)
            print("Successfully parsed JSON")
            # Print summary
            print(json.dumps(data, indent=2)[:1000]) # Print first 1000 chars
        except json.JSONDecodeError:
            print("Failed to parse JSON")
    else:
        print("stats_history not found. Searching for other variables...")
        # Try to find 'requests' or 'failures'
        # Sometimes it's passed to a React component
        
        # Let's just print the first few lines of any large script tag content
        script_pattern = r'<script>(.*?)</script>'
        scripts = re.findall(script_pattern, content, re.DOTALL)
        for i, script in enumerate(scripts):
            if "stats_history" in script or "requests" in script:
                print(f"Script {i} contains relevant keywords.")
                print(script[:500])

except Exception as e:
    print(f"Error: {e}")
