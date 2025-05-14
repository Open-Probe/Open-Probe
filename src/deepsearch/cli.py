import argparse
import asyncio
import sys
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich import print as rich_print
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from langchain_core.messages import HumanMessage

from .graph import create_graph
from .utils import extract_answer
from .config import config

# Initialize rich console if available
console = Console() if RICH_AVAILABLE else None


def print_result(result, verbose=False):
    """Print the result of a DeepSearch query.
    
    Args:
        result: The result dictionary from the graph
        verbose: Whether to print detailed output
    """
    if RICH_AVAILABLE:
        if verbose:
            # Print all messages in the conversation
            console.print("\n[bold cyan]Full Conversation[/bold cyan]\n")
            for i, m in enumerate(result["messages"]):
                message_type = type(m).__name__.replace("Message", "")
                content = m.content
                
                console.print(f"[bold]{message_type} Message {i+1}:[/bold]")
                console.print(Panel(content, border_style="dim"))
        
        # Print the final answer
        if result.get("answer"):
            console.print("\n[bold green]Answer[/bold green]\n")
            console.print(Panel(Markdown(result["answer"]), border_style="green"))
        else:
            # Try to extract the answer from the last message
            last_msg_content = result["messages"][-1].content
            answer = extract_answer(last_msg_content)
            
            if answer:
                console.print("\n[bold green]Answer[/bold green]\n")
                console.print(Panel(Markdown(answer), border_style="green"))
            else:
                console.print("\n[bold yellow]No definitive answer found[/bold yellow]\n")
                console.print("Last message content:")
                console.print(Panel(last_msg_content, border_style="yellow"))
    else:
        # Fallback to standard print if rich is not available
        if verbose:
            # Print all messages in the conversation
            print("\n=== Full Conversation ===\n")
            for i, m in enumerate(result["messages"]):
                print(f"Message {i+1}:")
                m.pretty_print()
                print()
        
        # Print the final answer
        if result.get("answer"):
            print("\n=== Answer ===\n")
            print(result["answer"])
        else:
            # Try to extract the answer from the last message
            last_msg_content = result["messages"][-1].content
            answer = extract_answer(last_msg_content)
            
            if answer:
                print("\n=== Answer ===\n")
                print(answer)
            else:
                print("\n=== No definitive answer found ===\n")
                print("Last message content:")
                print(last_msg_content)


async def run_query(query: str, max_iterations: Optional[int] = None, verbose: bool = False):
    """Run a query through the DeepSearch system.
    
    Args:
        query: The query to search for
        max_iterations: Maximum number of iterations
        verbose: Whether to print verbose output
        
    Returns:
        The result from the graph
    """
    # Update verbose setting
    if verbose:
        config.set("verbose", True)
    
    # Use configured max_iterations if not provided
    if max_iterations is None:
        max_iterations = config.get("max_iterations")
    
    # Create a new graph instance
    graph = create_graph()
    
    # Show progress if rich is available
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            console=console
        ) as progress:
            task = progress.add_task("Running DeepSearch query...", total=None)
            
            # Run the query
            result = await graph.ainvoke({
                "messages": [HumanMessage(f"<question>{query}</question>")],
                "current_iter": 0,
                "max_iter": max_iterations,
                "search_query": None,
                "search_summary": None,
                "answer": None
            })
            
            progress.update(task, completed=True)
    else:
        # Run without progress indicator
        print("Running DeepSearch query...")
        start_time = time.time()
        
        result = await graph.ainvoke({
            "messages": [HumanMessage(f"<question>{query}</question>")],
            "current_iter": 0,
            "max_iter": max_iterations,
            "search_query": None,
            "search_summary": None,
            "answer": None
        })
        
        elapsed = time.time() - start_time
        print(f"Query completed in {elapsed:.2f} seconds")
    
    return result


def configure(args):
    """Configure the DeepSearch system.
    
    Args:
        args: Command-line arguments
    """
    if args.show:
        # Show current configuration
        if RICH_AVAILABLE:
            config_json = json.dumps(config.show(), indent=2)
            console.print("[bold cyan]Current Configuration[/bold cyan]")
            console.print(Syntax(config_json, "json", theme="monokai", line_numbers=True))
        else:
            print(json.dumps(config.show(), indent=2))
        return
    
    if args.reset:
        # Reset configuration to defaults
        config.reset()
        config.save()
        
        if RICH_AVAILABLE:
            console.print("[bold green]Configuration reset to defaults[/bold green]")
        else:
            print("Configuration reset to defaults")
        return
    
    if args.set:
        # Set configuration values
        for key_value in args.set:
            if "=" not in key_value:
                if RICH_AVAILABLE:
                    console.print(f"[bold red]Error:[/bold red] Invalid format for --set '{key_value}', use 'key=value'")
                else:
                    print(f"Error: Invalid format for --set '{key_value}', use 'key=value'")
                continue
                
            key, value = key_value.split("=", 1)
            
            # Try to convert value to appropriate type
            try:
                # Try as int
                converted_value = int(value)
            except ValueError:
                try:
                    # Try as float
                    converted_value = float(value)
                except ValueError:
                    # Try as boolean
                    if value.lower() in ("true", "yes", "1"):
                        converted_value = True
                    elif value.lower() in ("false", "no", "0"):
                        converted_value = False
                    else:
                        # Keep as string
                        converted_value = value
            
            config.set(key, converted_value)
            
            if RICH_AVAILABLE:
                console.print(f"Set [cyan]{key}[/cyan] = [yellow]{converted_value}[/yellow]")
            else:
                print(f"Set {key} = {converted_value}")
        
        # Save configuration
        config.save()
        
        if RICH_AVAILABLE:
            console.print("[bold green]Configuration saved[/bold green]")
        else:
            print("Configuration saved")


def parse_args():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="deepsearch",
        description="DeepSearch - Comprehensive web search and information extraction"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Run a DeepSearch query")
    search_parser.add_argument("query", nargs="?", help="Query to search for")
    search_parser.add_argument("-i", "--interactive", action="store_true", 
                               help="Run in interactive mode")
    search_parser.add_argument("-m", "--max-iterations", type=int,
                               help=f"Maximum number of iterations (default: {config.get('max_iterations')})")
    search_parser.add_argument("-v", "--verbose", action="store_true",
                               help="Print verbose output")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configure DeepSearch")
    config_parser.add_argument("--show", action="store_true", 
                               help="Show current configuration")
    config_parser.add_argument("--reset", action="store_true",
                               help="Reset configuration to defaults")
    config_parser.add_argument("--set", nargs="+", metavar="KEY=VALUE",
                               help="Set configuration key=value pairs")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    
    args = parser.parse_args()
    
    # If no command provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Handle version command
    if args.command == "version":
        if RICH_AVAILABLE:
            console.print("[bold cyan]DeepSearch[/bold cyan] version 0.2.0")
            console.print("Improved with caching, retries, and CLI enhancements")
        else:
            print("DeepSearch version 0.2.0")
            print("Improved with caching, retries, and CLI enhancements")
        sys.exit(0)
    
    return args


async def main_async():
    """Main async function to run the CLI."""
    args = parse_args()
    
    if args.command == "search":
        if args.interactive:
            # Interactive mode
            if RICH_AVAILABLE:
                console.print("[bold cyan]DeepSearch Interactive Mode[/bold cyan] (type 'exit' to quit)")
            else:
                print("DeepSearch Interactive Mode (type 'exit' to quit)")
                
            while True:
                try:
                    if RICH_AVAILABLE:
                        query = console.input("\n[bold]Enter your query:[/bold] ")
                    else:
                        query = input("\nEnter your query: ")
                        
                    if query.lower() in ("exit", "quit"):
                        break
                    
                    if not query.strip():
                        continue
                    
                    result = await run_query(query, args.max_iterations, args.verbose)
                    print_result(result, args.verbose)
                    
                except KeyboardInterrupt:
                    if RICH_AVAILABLE:
                        console.print("\n[bold red]Exiting...[/bold red]")
                    else:
                        print("\nExiting...")
                    break
                except Exception as e:
                    if RICH_AVAILABLE:
                        console.print(f"\n[bold red]Error:[/bold red] {e}")
                    else:
                        print(f"Error: {e}")
        elif args.query:
            # Single query mode
            result = await run_query(args.query, args.max_iterations, args.verbose)
            print_result(result, args.verbose)
        else:
            if RICH_AVAILABLE:
                console.print("[bold red]Error:[/bold red] Please provide a query or use --interactive mode")
            else:
                print("Error: Please provide a query or use --interactive mode")
    
    elif args.command == "config":
        configure(args)


def main():
    """Main entry point for the CLI."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print("\n[bold red]Exiting...[/bold red]")
        else:
            print("\nExiting...")
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 