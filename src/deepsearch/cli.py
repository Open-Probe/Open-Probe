#!/usr/bin/env python3
import asyncio
import argparse
import sys
from typing import Optional
import os
import time
from pathlib import Path

from .utils import extract_content
from .rewoo_graph import graph


async def solve(question: str, max_replan_iter: int = 1):
    """
    Run the DeepSearch solver with the given question.
    
    Args:
        question: The query to answer
        max_replan_iter: Maximum number of replan iterations
    
    Returns:
        The result from the graph execution
    """
    print(f"\n🔍 Solving: {question}")
    print(f"Max replanning iterations: {max_replan_iter}\n")
    
    start_time = time.time()
    
    res = await graph.ainvoke({
        "task": question,
        "plan_string": None,
        "steps": [],
        "results": {},
        "result": None,
        "intermediate_result": None,
        "search_query": None,
        "needs_replan": False,
        "replan_iter": 0,
        "max_replan_iter": max_replan_iter
    }, {"recursion_limit": 30})
    
    elapsed_time = time.time() - start_time
    
    # Print results
    print("\n===== EXECUTION PLAN =====")
    print(res["plan_string"])
    
    print("\n===== INTERMEDIATE RESULTS =====")
    for step_name, result in res["results"].items():
        print(f"{step_name}: {result}")
    
    print("\n===== FINAL ANSWER =====")
    response = res["result"]
    answer = extract_content(response, "answer")
    if answer is None:
        print("⚠️ Failed without an answer!")
        print(f"Raw response: {response}")
    else:
        print(f"🎯 Answer: {answer}")
    
    print(f"\n✓ Process completed in {elapsed_time:.2f} seconds")
    
    return res


async def interactive_mode():
    """Run DeepSearch in interactive mode where users can enter queries continuously."""
    print("\n🤖 OpenProbe DeepSearch Interactive Mode")
    print("Enter your questions below (type 'exit' or 'quit' to end session)")
    
    while True:
        try:
            query = input("\n🔍 Enter your question: ")
            if query.lower() in ['exit', 'quit']:
                print("Exiting interactive mode. Goodbye!")
                break
                
            if not query.strip():
                continue
                
            await solve(query)
            # Add delay to allow transports to close properly
            await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting interactive mode.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def run_async_with_cleanup(coro):
    """Run async coroutine with proper cleanup to prevent transport errors."""
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        # Cancel all pending tasks and close loop properly
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


def check_environment():
    """Check if required environment variables are set."""
    required_vars = ["GOOGLE_API_KEY", "WEB_SEARCH_API_KEY"]
    missing_vars = [var for var in required_vars if os.getenv(var) is None]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your environment or .env file.")
        return False
    return True


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="OpenProbe DeepSearch CLI")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Execute a search query")
    search_parser.add_argument("query", nargs="?", help="The search query")
    search_parser.add_argument("--max-replan", type=int, default=1, 
                              help="Maximum number of replan iterations")
    search_parser.add_argument("--interactive", "-i", action="store_true", 
                              help="Run in interactive mode")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not args.command:
        parser.print_help()
        return
    
    # Check environment variables
    if not check_environment():
        return
    
    # Handle commands with proper asyncio cleanup
    if args.command == "search":
        if args.interactive:
            run_async_with_cleanup(interactive_mode())
        elif args.query:
            async def single_query():
                await solve(args.query, args.max_replan)
                await asyncio.sleep(0.1)  # Allow transports to close
            run_async_with_cleanup(single_query())
        else:
            search_parser.print_help()
    
    elif args.command == "version":
        print("OpenProbe DeepSearch v0.1.0")


if __name__ == "__main__":
    main() 