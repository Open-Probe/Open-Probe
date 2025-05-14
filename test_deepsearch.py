#!/usr/bin/env python3
"""
DeepSearch Test - Simple test for the DeepSearch system
"""

import asyncio
import argparse
import sys

from src.deepsearch.cli import run_query, print_result


async def solve(question, verbose=False, max_iterations=None):
    """Run a DeepSearch query and print the result.
    
    Args:
        question: The question to search for
        verbose: Whether to print verbose output
        max_iterations: Maximum number of search iterations
    """
    result = await run_query(question, max_iterations, verbose)
    print_result(result, verbose)
    
    return result


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Test the DeepSearch system')
    parser.add_argument('query', nargs='?', help='Query to search for')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('-m', '--max-iterations', type=int, help='Maximum number of iterations')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Default example queries
    examples = [
        "Which country launched the first satellite into space, and what was the name of the satellite?",
        "A farmer wants to cross a river and take with him a wolf, a goat and a cabbage. He has a boat with three secure separate compartments. If the wolf and the goat are alone on one shore, the wolf will eat the goat. If the goat and the cabbage are alone on the shore, the goat will eat the cabbage. How can the farmer efficiently bring the wolf, the goat and the cabbage across the river without anything being eaten?"
    ]
    
    if args.query:
        # Use provided query
        query = args.query
    else:
        # Use default query
        print("No query provided. Using example query:")
        query = examples[0]
        print(f"Query: {query}")
    
    try:
        asyncio.run(solve(query, args.verbose, args.max_iterations))
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
