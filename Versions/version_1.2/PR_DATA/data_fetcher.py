# OLD: Synchronous blocking calls
import requests
import time

def fetch_data(url):
    """Fetch data from URL synchronously"""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def fetch_multiple_sources(urls):
    """Fetch from multiple sources (blocking)"""
    results = []
    for url in urls:
        results.append(fetch_data(url))
    return results

# NEW: Async implementation with aiohttp
import aiohttp
import asyncio

async def async_fetch_data(session, url):
    """Fetch data asynchronously"""
    async with session.get(url, timeout=10) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_multiple_sources_async(urls):
    """Fetch from multiple sources concurrently"""
    async with aiohttp.ClientSession() as session:
        tasks = [async_fetch_data(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# NEW: Added retry mechanism with exponential backoff
async def fetch_with_retry(session, url, max_retries=3):
    """Fetch with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            return await async_fetch_data(session, url)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)