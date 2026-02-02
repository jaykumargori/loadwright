#!/usr/bin/env python3
"""
Main entry point for JMeter Automation Tool
"""
import argparse
import json
import sys
from agent import JMeterAgent

def main():
    parser = argparse.ArgumentParser(description="JMeter Automation Tool - AI-Powered Test Management")
    parser.add_argument("--command", "-c", type=str, help="Command to execute")
    parser.add_argument("--params", "-p", type=str, help="JSON parameters for command")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--llm-provider", type=str, default="openai", help="LLM provider (openai, anthropic)")
    parser.add_argument("--llm-model", type=str, default="gpt-4", help="LLM model name")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = JMeterAgent(llm_provider=args.llm_provider, llm_model=args.llm_model)
    
    if args.interactive:
        agent.interactive_mode()
    elif args.command:
        # Parse parameters
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                print("Error: Invalid JSON parameters")
                sys.exit(1)
        
        # Execute command
        result = agent.execute_command(args.command, params)
        
        # Output result
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if result.get("success") else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

