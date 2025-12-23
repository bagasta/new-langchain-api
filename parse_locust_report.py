import re
import json

file_path = "locust/report/load-testing(100 Users 30s).html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the script tag containing window.templateArgs
# We know it starts with "window.templateArgs ="
pattern = r'window\.templateArgs\s*=\s*(\{.*?\})\s*;'
match = re.search(pattern, content, re.DOTALL)

if not match:
    # Try without semicolon
    pattern = r'window\.templateArgs\s*=\s*(\{.*?\})\s*$'
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)

if match:
    data_str = match.group(1)
    try:
        data = json.loads(data_str)
        
        print("=== Locust Test Report Analysis ===")
        print(f"Duration: {data.get('duration')}")
        print(f"End Time: {data.get('end_time')}")
        
        print("\n--- Request Statistics ---")
        req_stats = data.get('requests_statistics', [])
        total_requests = 0
        total_failures = 0
        
        # Print header
        print(f"{'Method':<10} {'Name':<50} {'Reqs':<10} {'Fails':<10} {'Avg (ms)':<10} {'Min':<10} {'Max':<10} {'RPS':<10}")
        print("-" * 120)
        
        for stat in req_stats:
            method = stat.get('method', '')
            name = stat.get('name', '')
            num_reqs = stat.get('num_requests', 0)
            num_failures = stat.get('num_failures', 0)
            avg_response_time = stat.get('avg_response_time', 0)
            min_response_time = stat.get('min_response_time', 0)
            max_response_time = stat.get('max_response_time', 0)
            rps = stat.get('total_rps', 0)
            
            total_requests += num_reqs
            total_failures += num_failures
            
            print(f"{method:<10} {name[:47]:<50} {num_reqs:<10} {num_failures:<10} {avg_response_time:<10.2f} {min_response_time:<10} {max_response_time:<10} {rps:<10.2f}")
            
        print("-" * 120)
        print(f"Total Requests: {total_requests}")
        print(f"Total Failures: {total_failures}")
        if total_requests > 0:
            print(f"Failure Rate: {(total_failures/total_requests)*100:.2f}%")
        
        print("\n--- Failures Statistics ---")
        fail_stats = data.get('failures_statistics', [])
        if not fail_stats:
            print("No failures recorded.")
        else:
            for fail in fail_stats:
                print(f"Method: {fail.get('method')} Name: {fail.get('name')} Error: {fail.get('error')} Count: {fail.get('occurrences')}")

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        # Print a snippet of what we tried to parse
        print(f"Snippet: {data_str[:100]}...")
else:
    print("Could not find window.templateArgs")
    # Debug: print where it might be
    idx = content.find("window.templateArgs")
    if idx != -1:
        print(f"Found 'window.templateArgs' at index {idx}")
        print(f"Context: {content[idx:idx+200]}")
