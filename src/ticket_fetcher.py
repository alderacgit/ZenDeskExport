"""
Module for fetching tickets from Zendesk groups
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
import json
from pathlib import Path

logger = logging.getLogger(__name__)
console = Console()


class TicketFetcher:
    """Class for fetching tickets from Zendesk"""
    
    def __init__(self, client, config):
        """
        Initialize ticket fetcher
        
        Args:
            client: ZendeskClient instance
            config: ZendeskConfig instance
        """
        self.client = client
        self.config = config
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def fetch_tickets_by_group(
        self, 
        group_id: str,
        status: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        use_cache: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch all tickets from a specific group
        
        Args:
            group_id: Group ID to fetch tickets from
            status: Ticket status filter (open, pending, solved, closed)
            created_after: Only fetch tickets created after this date
            created_before: Only fetch tickets created before this date
            use_cache: Whether to use cached results if available
            
        Returns:
            List of ticket dictionaries
        """
        # Check cache first if requested
        cache_key = self._get_cache_key(group_id, status, created_after, created_before)
        if use_cache:
            cached_tickets = self._load_from_cache(cache_key)
            if cached_tickets:
                console.print(f"[green]Loaded {len(cached_tickets)} tickets from cache[/green]")
                return cached_tickets
        
        # Build search query
        query_parts = [f"group_id:{group_id}"]
        
        if status:
            query_parts.append(f"status:{status}")
        
        if created_after:
            date_str = created_after.strftime("%Y-%m-%d")
            query_parts.append(f"created>={date_str}")
        
        if created_before:
            date_str = created_before.strftime("%Y-%m-%d")
            query_parts.append(f"created<={date_str}")
        
        query = " ".join(query_parts)
        
        console.print(f"[cyan]Searching for tickets with query: {query}[/cyan]")
        
        # Fetch tickets
        tickets = self.client.search_tickets(query)
        
        console.print(f"[green]Found {len(tickets)} tickets in group {group_id}[/green]")
        
        # Save to cache
        if tickets:
            self._save_to_cache(cache_key, tickets)
        
        return tickets
    
    def fetch_all_group_tickets(
        self,
        status: Optional[str] = None,
        use_cache: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch tickets from all groups
        
        Args:
            status: Ticket status filter
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary mapping group ID to list of tickets
        """
        # First get all groups
        console.print("[cyan]Fetching all groups...[/cyan]")
        groups = self.client.get_groups()
        
        if not groups:
            console.print("[yellow]No groups found[/yellow]")
            return {}
        
        # Display groups
        self._display_groups(groups)
        
        # Fetch tickets for each group
        all_tickets = {}
        for group in groups:
            group_id = str(group['id'])
            group_name = group.get('name', 'Unknown')
            
            console.print(f"\n[cyan]Fetching tickets for group: {group_name} (ID: {group_id})[/cyan]")
            
            tickets = self.fetch_tickets_by_group(group_id, status=status, use_cache=use_cache)
            if tickets:
                all_tickets[group_id] = tickets
        
        return all_tickets
    
    def get_ticket_details(self, ticket_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a specific ticket
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Ticket dictionary with full details
        """
        url = f"{self.config.base_url}/tickets/{ticket_id}.json"
        params = {"include": "users,groups"}
        
        response = self.client.get(url, params)
        return response.get('ticket', {})
    
    def get_ticket_comments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """
        Get all comments for a ticket
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            List of comment dictionaries
        """
        url = self.config.get_endpoint('ticket_comments', ticket_id=ticket_id)
        response = self.client.get(url)
        return response.get('comments', [])
    
    def _display_groups(self, groups: List[Dict[str, Any]]):
        """Display groups in a table"""
        table = Table(title="Available Groups")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Created", style="yellow")
        
        for group in groups:
            created_at = group.get('created_at', 'Unknown')
            if created_at != 'Unknown':
                # Parse and format the date
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = dt.strftime("%Y-%m-%d")
                except:
                    pass
            
            table.add_row(
                str(group['id']),
                group.get('name', 'Unknown'),
                created_at
            )
        
        console.print(table)
    
    def _get_cache_key(
        self,
        group_id: str,
        status: Optional[str],
        created_after: Optional[datetime],
        created_before: Optional[datetime]
    ) -> str:
        """Generate cache key for ticket search"""
        parts = [f"group_{group_id}"]
        
        if status:
            parts.append(f"status_{status}")
        
        if created_after:
            parts.append(f"after_{created_after.strftime('%Y%m%d')}")
        
        if created_before:
            parts.append(f"before_{created_before.strftime('%Y%m%d')}")
        
        return "_".join(parts) + ".json"
    
    def _save_to_cache(self, cache_key: str, data: List[Dict[str, Any]]):
        """Save data to cache file"""
        cache_file = self.cache_dir / cache_key
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Saved {len(data)} items to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Load data from cache file"""
        cache_file = self.cache_dir / cache_key
        
        if not cache_file.exists():
            return None
        
        # Check if cache is fresh (less than 1 hour old)
        cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if cache_age > timedelta(hours=1):
            logger.debug(f"Cache expired: {cache_key}")
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            logger.debug(f"Loaded {len(data)} items from cache: {cache_key}")
            return data
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached data"""
        cache_files = list(self.cache_dir.glob("*.json"))
        for file in cache_files:
            file.unlink()
        
        console.print(f"[green]Cleared {len(cache_files)} cache files[/green]")