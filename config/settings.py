"""
Configuration settings for Zendesk Email Exporter
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Logger configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ZendeskConfig:
    """Configuration class for Zendesk API settings"""
    
    def __init__(self):
        # API Credentials
        self.email = os.getenv('ZENDESK_EMAIL')
        self.api_token = os.getenv('ZENDESK_API_TOKEN')
        self.subdomain = os.getenv('ZENDESK_SUBDOMAIN', 'alderac')
        
        # Validate required credentials
        if not self.email or not self.api_token:
            raise ValueError(
                "Missing required credentials. Please set ZENDESK_EMAIL and "
                "ZENDESK_API_TOKEN in your .env file"
            )
        
        # API URLs
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
        
        # API Endpoints
        self.endpoints = {
            'tickets': f"{self.base_url}/tickets.json",
            'search': f"{self.base_url}/search.json",
            'groups': f"{self.base_url}/groups.json",
            'users': f"{self.base_url}/users",
            'ticket_comments': f"{self.base_url}/tickets/{{ticket_id}}/comments.json"
        }
        
        # Request settings
        self.timeout = 30  # seconds
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        # Pagination settings
        self.page_size = 100  # Maximum allowed by Zendesk
        
        # Rate limiting (Zendesk allows 700 requests per minute for Essential plans)
        self.rate_limit_requests = 700
        self.rate_limit_window = 60  # seconds
        
        # Default group ID (optional)
        self.default_group_id = os.getenv('ZENDESK_DEFAULT_GROUP_ID')
        
        # Output settings
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './output'))
        self.output_dir.mkdir(exist_ok=True)
    
    @property
    def auth(self) -> tuple:
        """Return authentication tuple for requests"""
        return (f"{self.email}/token", self.api_token)
    
    @property
    def headers(self) -> dict:
        """Return default headers for API requests"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_endpoint(self, endpoint_name: str, **kwargs) -> str:
        """Get formatted endpoint URL"""
        endpoint = self.endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        return endpoint.format(**kwargs)
    
    def __str__(self) -> str:
        """String representation of config"""
        return (
            f"ZendeskConfig(subdomain={self.subdomain}, "
            f"email={self.email}, authenticated=True)"
        )


# Create a singleton config instance
config = ZendeskConfig()