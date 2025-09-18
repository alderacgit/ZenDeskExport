"""
Module for extracting email addresses from Zendesk tickets
"""

import logging
import re
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict
import validators
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


class EmailExtractor:
    """Class for extracting email addresses from Zendesk tickets"""
    
    def __init__(self):
        """Initialize email extractor"""
        # Email regex pattern for finding emails in text
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
    
    def extract_from_tickets(
        self, 
        tickets: List[Dict[str, Any]],
        include_ccs: bool = True,
        include_comments: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract email addresses from a list of tickets
        
        Args:
            tickets: List of ticket dictionaries
            include_ccs: Whether to include CC email addresses
            include_comments: Whether to extract emails from comments
            
        Returns:
            Dictionary with email as key and metadata as value
        """
        email_data = defaultdict(lambda: {
            'ticket_ids': [],
            'ticket_count': 0,
            'first_seen': None,
            'last_seen': None,
            'is_requester': False,
            'is_cc': False,
            'is_from_comment': False
        })
        
        for ticket in tickets:
            # Extract requester email
            requester_email = self._extract_requester_email(ticket)
            if requester_email:
                self._add_email(email_data, requester_email, ticket, 'requester')
            
            # Extract CC emails
            if include_ccs:
                cc_emails = self._extract_cc_emails(ticket)
                for cc_email in cc_emails:
                    self._add_email(email_data, cc_email, ticket, 'cc')
            
            # Extract emails from custom fields
            custom_emails = self._extract_custom_field_emails(ticket)
            for custom_email in custom_emails:
                self._add_email(email_data, custom_email, ticket, 'custom_field')
            
            # Extract emails from comments if requested
            if include_comments:
                comment_emails = self._extract_comment_emails(ticket)
                for comment_email in comment_emails:
                    self._add_email(email_data, comment_email, ticket, 'comment')
        
        return dict(email_data)
    
    def get_unique_emails(
        self, 
        tickets: List[Dict[str, Any]],
        include_ccs: bool = True,
        include_comments: bool = False
    ) -> Set[str]:
        """
        Get unique set of email addresses from tickets
        
        Args:
            tickets: List of ticket dictionaries
            include_ccs: Whether to include CC email addresses
            include_comments: Whether to extract emails from comments
            
        Returns:
            Set of unique email addresses
        """
        email_data = self.extract_from_tickets(tickets, include_ccs, include_comments)
        return set(email_data.keys())
    
    def get_email_statistics(
        self,
        email_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate statistics about extracted emails
        
        Args:
            email_data: Dictionary of email data
            
        Returns:
            Dictionary with statistics
        """
        if not email_data:
            return {
                'total_unique_emails': 0,
                'total_tickets': 0,
                'requester_emails': 0,
                'cc_emails': 0,
                'comment_emails': 0
            }
        
        requester_count = sum(1 for data in email_data.values() if data['is_requester'])
        cc_count = sum(1 for data in email_data.values() if data['is_cc'])
        comment_count = sum(1 for data in email_data.values() if data['is_from_comment'])
        total_tickets = len(set(
            ticket_id 
            for data in email_data.values() 
            for ticket_id in data['ticket_ids']
        ))
        
        return {
            'total_unique_emails': len(email_data),
            'total_tickets': total_tickets,
            'requester_emails': requester_count,
            'cc_emails': cc_count,
            'comment_emails': comment_count,
            'avg_tickets_per_email': round(
                sum(data['ticket_count'] for data in email_data.values()) / len(email_data), 2
            ) if email_data else 0
        }
    
    def display_email_summary(self, email_data: Dict[str, Dict[str, Any]]):
        """Display summary of extracted emails"""
        if not email_data:
            console.print("[yellow]No emails found[/yellow]")
            return
        
        # Create table
        table = Table(title="Extracted Emails Summary")
        table.add_column("Email", style="cyan")
        table.add_column("Tickets", style="green", justify="right")
        table.add_column("Type", style="yellow")
        table.add_column("First Seen", style="magenta")
        
        # Sort emails by ticket count
        sorted_emails = sorted(
            email_data.items(),
            key=lambda x: x[1]['ticket_count'],
            reverse=True
        )
        
        # Display top 20 emails
        for email, data in sorted_emails[:20]:
            email_type = []
            if data['is_requester']:
                email_type.append("Requester")
            if data['is_cc']:
                email_type.append("CC")
            if data['is_from_comment']:
                email_type.append("Comment")
            
            first_seen = data['first_seen']
            if first_seen:
                first_seen = first_seen.split('T')[0]  # Extract date part
            
            table.add_row(
                email,
                str(data['ticket_count']),
                ", ".join(email_type),
                first_seen or "N/A"
            )
        
        console.print(table)
        
        # Display statistics
        stats = self.get_email_statistics(email_data)
        console.print("\n[bold cyan]Statistics:[/bold cyan]")
        console.print(f"Total unique emails: [green]{stats['total_unique_emails']}[/green]")
        console.print(f"Total tickets: [green]{stats['total_tickets']}[/green]")
        console.print(f"Requester emails: [yellow]{stats['requester_emails']}[/yellow]")
        console.print(f"CC emails: [yellow]{stats['cc_emails']}[/yellow]")
        console.print(f"Comment emails: [yellow]{stats['comment_emails']}[/yellow]")
        console.print(f"Avg tickets per email: [magenta]{stats['avg_tickets_per_email']}[/magenta]")
    
    def _extract_requester_email(self, ticket: Dict[str, Any]) -> Optional[str]:
        """Extract requester email from ticket"""
        # Try different possible locations for requester email
        requester_email = None
        
        # Check via field
        via = ticket.get('via', {})
        source = via.get('source', {})
        from_address = source.get('from', {})
        if isinstance(from_address, dict):
            requester_email = from_address.get('address')
        
        # Check requester_id and look up in users if available
        if not requester_email and 'requester' in ticket:
            requester = ticket['requester']
            if isinstance(requester, dict):
                requester_email = requester.get('email')
        
        # Validate and return
        if requester_email and self._validate_email(requester_email):
            return requester_email.lower()
        
        return None
    
    def _extract_cc_emails(self, ticket: Dict[str, Any]) -> Set[str]:
        """Extract CC email addresses from ticket"""
        cc_emails = set()
        
        # Check email_cc field
        email_ccs = ticket.get('email_ccs', [])
        if email_ccs:
            for cc_entry in email_ccs:
                if isinstance(cc_entry, dict):
                    email = cc_entry.get('email')
                elif isinstance(cc_entry, str):
                    email = cc_entry
                else:
                    continue
                
                if email and self._validate_email(email):
                    cc_emails.add(email.lower())
        
        # Check collaborator_ids if present
        collaborators = ticket.get('collaborators', [])
        for collaborator in collaborators:
            if isinstance(collaborator, dict):
                email = collaborator.get('email')
                if email and self._validate_email(email):
                    cc_emails.add(email.lower())
        
        return cc_emails
    
    def _extract_custom_field_emails(self, ticket: Dict[str, Any]) -> Set[str]:
        """Extract email addresses from custom fields"""
        emails = set()
        
        # Check custom fields
        custom_fields = ticket.get('custom_fields', [])
        for field in custom_fields:
            value = field.get('value')
            if value and isinstance(value, str):
                # Look for emails in the value
                found_emails = self.email_pattern.findall(value)
                for email in found_emails:
                    if self._validate_email(email):
                        emails.add(email.lower())
        
        # Check fields object
        fields = ticket.get('fields', [])
        for field in fields:
            value = field.get('value')
            if value and isinstance(value, str):
                found_emails = self.email_pattern.findall(value)
                for email in found_emails:
                    if self._validate_email(email):
                        emails.add(email.lower())
        
        return emails
    
    def _extract_comment_emails(self, ticket: Dict[str, Any]) -> Set[str]:
        """Extract email addresses from ticket comments"""
        emails = set()
        
        # Note: Comments might not be included in the basic ticket data
        # They would need to be fetched separately via get_ticket_comments
        comments = ticket.get('comments', [])
        for comment in comments:
            body = comment.get('body', '')
            if body:
                found_emails = self.email_pattern.findall(body)
                for email in found_emails:
                    if self._validate_email(email):
                        emails.add(email.lower())
        
        return emails
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        if not email:
            return False
        
        # Use validators library for validation
        validation = validators.email(email)
        return validation is True
    
    def _add_email(
        self,
        email_data: Dict[str, Dict[str, Any]],
        email: str,
        ticket: Dict[str, Any],
        source_type: str
    ):
        """Add email to the email data dictionary"""
        ticket_id = ticket.get('id')
        created_at = ticket.get('created_at')
        
        data = email_data[email]
        
        # Add ticket ID if not already present
        if ticket_id and ticket_id not in data['ticket_ids']:
            data['ticket_ids'].append(ticket_id)
            data['ticket_count'] = len(data['ticket_ids'])
        
        # Update timestamps
        if created_at:
            if not data['first_seen'] or created_at < data['first_seen']:
                data['first_seen'] = created_at
            if not data['last_seen'] or created_at > data['last_seen']:
                data['last_seen'] = created_at
        
        # Mark source type
        if source_type == 'requester':
            data['is_requester'] = True
        elif source_type == 'cc':
            data['is_cc'] = True
        elif source_type == 'comment':
            data['is_from_comment'] = True