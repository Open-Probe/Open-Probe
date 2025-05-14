import asyncio
import argparse
from .graph import run_deep_search
from .config import config

def parse_args():
    parser = argparse.ArgumentParser(description="Run DeepSearch with reasoning-first approach")
    parser.add_argument("query", nargs="?", help="The query to search for")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--max-iter", type=int, default=5, help="Maximum number of iterations")
    return parser.parse_args()

async def main():
    args = parse_args()
    
    if args.verbose:
        config.set("verbose", True)
        
    if not args.query:
        # Interactive mode
        print("DeepSearch (reasoning-first approach)")
        print("Type 'exit' to quit")
        print("-" * 50)
        
        while True:
            query = input("\nEnter your query: ")
            if query.lower() in ("exit", "quit", "q"):
                break
                
            result = await run_deep_search(query, max_iterations=args.max_iter)
            
            if result.get("answer"):
                print(f"\nAnswer: {result['answer']}")
            else:
                print("\nNo answer found.")
    else:
        # Single query mode
        result = await run_deep_search(args.query, max_iterations=args.max_iter)
        
        if result.get("answer"):
            print(result["answer"])
        else:
            print("No answer found.")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 