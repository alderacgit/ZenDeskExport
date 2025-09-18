"""
Zendesk API client for making authenticated requests
"""

import logging
import time
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
logger = logging.getLogger(__name__)


class ZendeskAPIError(Exception):
    """Custom exception for Zendesk API errors"""
    pass


class RateLimitExceeded(ZendeskAPIError):
    """Exception raised when rate limit is exceeded"""
    pass


class ZendeskClient:
    """Client for interacting with Zendesk API"""
    
    def __init__(self, config):
        """
        Initialize Zendesk client
        
        Args:
            config: ZendeskConfig instance with API settings
        """
        self.config = config
        self.session = self._create_session()
        self.request_count = 0
        self.last_request_time = time.time()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication and headers
        session.auth = self.config.auth
        session.headers.update(self.config.headers)
        
        return session
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.config.rate_limit_window:
            if self.request_count >= self.config.rate_limit_requests:
                sleep_time = self.config.rate_limit_window - time_since_last_request
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            self.request_count = 0
            self.last_request_time = current_time
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request to Zendesk API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
            
        Raises:
            ZendeskAPIError: If API returns an error
            RateLimitExceeded: If rate limit is exceeded
        """
        self._check_rate_limit()
        
        # Set timeout if not provided
        kwargs.setdefault('timeout', self.config.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            self.request_count += 1
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds")
                time.sleep(retry_after)
                raise RateLimitExceeded(f"Rate limit exceeded. Retry after {retry_after} seconds")
            
            # Check for other errors
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error occurred: {e}"
            if response.text:
                error_msg += f" Response: {response.text}"
            logger.error(error_msg)
            raise ZendeskAPIError(error_msg) from e
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error occurred: {e}"
            logger.error(error_msg)
            raise ZendeskAPIError(error_msg) from e
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout: {e}"
            logger.error(error_msg)
            raise ZendeskAPIError(error_msg) from e
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            raise ZendeskAPIError(error_msg) from e
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request to Zendesk API
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            JSON response as dictionary
        """
        response = self._make_request('GET', url, params=params)
        return response.json()
    
    def post(self, url: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a POST request to Zendesk API
        
        Args:
            url: URL to request
            json_data: JSON data to send
            
        Returns:
            JSON response as dictionary
        """
        response = self._make_request('POST', url, json=json_data)
        return response.json()
    
    def get_paginated(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all pages of results from a paginated endpoint
        
        Args:
            url: URL to request
            params: Query parameters
            max_pages: Maximum number of pages to fetch (None for all)
            
        Returns:
            List of all results across all pages
        """
        if params is None:
            params = {}
        
        params['per_page'] = self.config.page_size
        all_results = []
        page = 1
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Fetching data from Zendesk...", total=None)
            
            while True:
                if max_pages and page > max_pages:
                    break
                
                params['page'] = page
                response = self.get(url, params)
                
                # Handle different response formats
                if 'results' in response:
                    results = response['results']
                elif 'tickets' in response:
                    results = response['tickets']
                elif 'users' in response:
                    results = response['users']
                elif 'groups' in response:
                    results = response['groups']
                else:
                    results = response
                
                if not results:
                    break
                
                all_results.extend(results)
                progress.update(task, description=f"[cyan]Fetched {len(all_results)} items...")
                
                # Check for next page
                if 'next_page' in response and response['next_page']:
                    page += 1
                else:
                    break
        
        logger.info(f"Fetched {len(all_results)} total items across {page} pages")
        return all_results
    
    def test_connection(self) -> bool:
        """
        Test connection to Zendesk API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with console.status("[bold cyan]Testing Zendesk connection..."):
                # Try to fetch the current user to test auth
                url = f"{self.config.base_url}/users/me.json"
                response = self.get(url)
                
                if response and 'user' in response:
                    user = response['user']
                    console.print(
                        f"[green]✓[/green] Connected to Zendesk as: "
                        f"[bold]{user.get('name', 'Unknown')}[/bold] "
                        f"({user.get('email', 'Unknown')})"
                    )
                    return True
                    
        except Exception as e:
            console.print(f"[red]✗[/red] Connection failed: {e}")
            logger.error(f"Connection test failed: {e}")
            
        return False
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get all groups from Zendesk
        
        Returns:
            List of group dictionaries
        """
        url = self.config.get_endpoint('groups')
        return self.get_paginated(url)
    
    def search_tickets(
        self, 
        query: str,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Search for tickets using Zendesk Search API
        
        Args:
            query: Search query string
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            List of ticket dictionaries
        """
        url = self.config.get_endpoint('search')
        params = {
            'query': f"type:ticket {query}",
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        return self.get_paginated(url, params)