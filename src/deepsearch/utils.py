import re
import os
import json
import time
import hashlib
import asyncio
import inspect
from pathlib import Path
from typing import Optional, Dict, Any, Union, Callable, TypeVar, cast

T = TypeVar('T')


def extract_search_query(input_str):
    """Extract search query from ReAct format string.
    
    Args:
        input_str: String containing the web_search action
        
    Returns:
        The search query string
        
    Raises:
        ValueError: If web_search action cannot be extracted
    """
    match = re.search(r"web_search\[(.*?)\]", input_str.strip())
    if not match:
        raise ValueError("Cannot extract 'web_search'!")
    return match.group(1)


def extract_answer(input_str):
    """Extract answer from ReAct format string.
    
    Args:
        input_str: String containing the answer tag
        
    Returns:
        The answer string or None if not found
    """
    match = re.search(r"<answer>(.*?)</answer>", input_str.strip(), re.DOTALL)
    if not match:
        return None
    return match.group(1)


def extract_content(input_str, target_tag):
    """Extract content from a specific tag in ReAct format string.
    
    Args:
        input_str: String containing the tagged content
        target_tag: Tag name to extract content from
        
    Returns:
        The content within the specified tag or None if extraction fails
    """
    lines = input_str.strip().split("\n")
    match = re.match(r"<(\w+)>(.*?)</\1>", lines[-1])
    try:
        if not match:
            raise RuntimeError(f"Cannot extract '{target_tag}'!")
        tag, content = match.groups()
        if tag != target_tag:
            raise RuntimeError(
                f"Found different tag '{tag}' instead of '{target_tag}'!")
        return content
    except Exception as e:
        print(f"Error extracting content: {e}")
        return None


class SearchCache:
    """Cache for storing and retrieving search results."""
    
    def __init__(self, cache_dir: Optional[str] = None, max_age_days: int = 7):
        """Initialize the search cache.
        
        Args:
            cache_dir: Directory to store cache files. Defaults to ~/.openprobe/cache
            max_age_days: Maximum age of cache entries in days
        """
        if cache_dir is None:
            home_dir = Path.home()
            cache_dir = os.path.join(home_dir, ".openprobe", "cache")
        
        self.cache_dir = cache_dir
        self.max_age_seconds = max_age_days * 24 * 60 * 60
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_key(self, query: str) -> str:
        """Generate a cache key from the search query.
        
        Args:
            query: The search query
            
        Returns:
            A hash-based cache key
        """
        # Create a hash of the query to use as the filename
        hash_obj = hashlib.md5(query.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def get_cache_path(self, key: str) -> str:
        """Get the file path for a cache key.
        
        Args:
            key: The cache key
            
        Returns:
            The full path to the cache file
        """
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached search results for a query.
        
        Args:
            query: The search query
            
        Returns:
            The cached results or None if not found or expired
        """
        key = self.get_cache_key(query)
        cache_path = self.get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            # Check if cache is expired
            file_time = os.path.getmtime(cache_path)
            if time.time() - file_time > self.max_age_seconds:
                print(f"Cache for '{query}' has expired")
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    
    def set(self, query: str, data: Dict[str, Any]) -> None:
        """Store search results in cache.
        
        Args:
            query: The search query
            data: The search results to cache
        """
        key = self.get_cache_key(query)
        cache_path = self.get_cache_path(key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing to cache: {e}")


def retry_with_exponential_backoff(
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3
):
    """Retry a function with exponential backoff.
    
    Supports both synchronous and asynchronous functions.
    
    Args:
        initial_delay: Initial delay between retries in seconds
        exponential_base: Base of the exponential to use for delay calculation
        jitter: Add random jitter to delay
        max_retries: Maximum number of retries
        
    Returns:
        The decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            # Async version
            async def async_wrapper(*args, **kwargs):
                num_retries = 0
                delay = initial_delay
                
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        num_retries += 1
                        if num_retries > max_retries:
                            raise Exception(f"Maximum number of retries ({max_retries}) exceeded: {str(e)}")
                        
                        delay_with_jitter = delay * (1 + jitter * 0.1 * (2 * (time.time() % 1) - 1))
                        print(f"Retrying in {delay_with_jitter:.2f} seconds... (attempt {num_retries}/{max_retries})")
                        await asyncio.sleep(delay_with_jitter)
                        delay *= exponential_base
            
            return cast(Callable[..., T], async_wrapper)
        else:
            # Sync version
            def sync_wrapper(*args, **kwargs):
                num_retries = 0
                delay = initial_delay
                
                while True:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        num_retries += 1
                        if num_retries > max_retries:
                            raise Exception(f"Maximum number of retries ({max_retries}) exceeded: {str(e)}")
                        
                        delay_with_jitter = delay * (1 + jitter * 0.1 * (2 * (time.time() % 1) - 1))
                        print(f"Retrying in {delay_with_jitter:.2f} seconds... (attempt {num_retries}/{max_retries})")
                        time.sleep(delay_with_jitter)
                        delay *= exponential_base
            
            return cast(Callable[..., T], sync_wrapper)
    
    return decorator
