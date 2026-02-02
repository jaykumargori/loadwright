#!/usr/bin/env python3
"""
Example usage of JMeter Automation Tool
"""
from agent import JMeterAgent
import json

def main():
    # Initialize the agent
    print("Initializing JMeter Agent...")
    agent = JMeterAgent()
    
    # Example 1: Start container
    print("\n1. Starting JMeter container...")
    result = agent.execute_command("start container", {})
    print(json.dumps(result, indent=2))
    
    # Example 2: Check status
    print("\n2. Checking container status...")
    result = agent.execute_command("status", {})
    print(json.dumps(result, indent=2))
    
    # Example 3: Create an API test plan
    print("\n3. Creating API test plan...")
    result = agent.execute_command("create test", {
        "test_name": "example_api_test",
        "type": "api",
        "endpoints": [
            {
                "name": "Get Request",
                "domain": "httpbin.org",
                "path": "/get",
                "method": "GET",
                "protocol": "https"
            },
            {
                "name": "Post Request",
                "domain": "httpbin.org",
                "path": "/post",
                "method": "POST",
                "protocol": "https"
            }
        ],
        "threads": 5,
        "ramp_up": 2,
        "loops": 10
    })
    print(json.dumps(result, indent=2))
    
    # Example 4: Validate test plan
    if result.get("success"):
        print("\n4. Validating test plan...")
        result = agent.execute_command("validate test", {
            "test_plan": "example_api_test.jmx"
        })
        print(json.dumps(result, indent=2))
    
    # Example 5: Run test (commented out to avoid long execution)
    # print("\n5. Running test...")
    # result = agent.execute_command("run test", {
    #     "test_plan": "example_api_test.jmx",
    #     "generate_report": True
    # })
    # print(json.dumps(result, indent=2))
    
    # Example 6: List plugins
    print("\n6. Listing installed plugins...")
    result = agent.execute_command("list plugins", {})
    print(json.dumps(result, indent=2))
    
    print("\nExamples completed!")

if __name__ == "__main__":
    main()

