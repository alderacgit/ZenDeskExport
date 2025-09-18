#!/usr/bin/env python3
"""
Zendesk Email Extractor - Main CLI Interface

Extract email addresses from Zendesk tickets in specific groups.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import click
from rich.console import Console
from rich.logging import RichHandler

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from src.zendesk_client import ZendeskClient, ZendeskAPIError
from src.ticket_fetcher import TicketFetcher
from src.email_extractor import EmailExtractor
from src.output_formatter import OutputFormatter

console = Console()

# Configure logging
def setup_logging(verbose: bool, log_file: Path = None):
    """Set up logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [RichHandler(console=console, rich_tracebacks=True)]
    
    if log_file:
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=handlers
    )


@click.command()
@click.option(
    '--group-id',
    '-g',
    help='Zendesk group ID to fetch tickets from'
)
@click.option(
    '--all-groups',
    is_flag=True,
    help='Fetch tickets from all groups'
)
@click.option(
    '--status',
    type=click.Choice(['open', 'pending', 'solved', 'closed', 'all']),
    default='all',
    help='Ticket status filter'
)
@click.option(
    '--days-back',
    type=int,
    help='Only fetch tickets created in the last N days'
)
@click.option(
    '--include-ccs',
    is_flag=True,
    default=True,
    help='Include CC email addresses'
)
@click.option(
    '--include-comments',
    is_flag=True,
    help='Extract emails from ticket comments (slower)'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['csv', 'json', 'txt', 'excel']),
    default='csv',
    help='Output format'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Output directory (default: ./output)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Test connection and show available groups without fetching tickets'
)
@click.option(
    '--use-cache',
    is_flag=True,
    help='Use cached ticket data if available'
)
@click.option(
    '--clear-cache',
    is_flag=True,
    help='Clear all cached data before running'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--list-groups',
    is_flag=True,
    help='List all available groups and exit'
)
def main(
    group_id,
    all_groups,
    status,
    days_back,
    include_ccs,
    include_comments,
    format,
    output,
    dry_run,
    use_cache,
    clear_cache,
    verbose,
    list_groups
):
    """
    Extract email addresses from Zendesk tickets.
    
    Examples:
    
    \b
    # Extract emails from a specific group
    python main.py -g 123456 -f csv
    
    \b
    # Extract emails from all groups
    python main.py --all-groups -f excel
    
    \b
    # List available groups
    python main.py --list-groups
    
    \b
    # Extract only recent tickets (last 30 days)
    python main.py -g 123456 --days-back 30
    
    \b
    # Test connection without fetching data
    python main.py --dry-run
    """
    
    # Setup logging
    log_file = Path("logs") / f"zendesk_export_{datetime.now().strftime('%Y%m%d')}.log"
    setup_logging(verbose, log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Print banner
        console.print("\n[bold cyan]Zendesk Email Extractor[/bold cyan]")
        console.print("=" * 50)
        
        # Initialize client
        console.print("[cyan]Initializing Zendesk client...[/cyan]")
        client = ZendeskClient(config)
        
        # Test connection
        if not client.test_connection():
            console.print("[red]Failed to connect to Zendesk. Please check your credentials.[/red]")
            sys.exit(1)
        
        # Initialize components
        fetcher = TicketFetcher(client, config)
        extractor = EmailExtractor()
        
        # Clear cache if requested
        if clear_cache:
            console.print("[yellow]Clearing cache...[/yellow]")
            fetcher.clear_cache()
        
        # List groups if requested
        if list_groups or dry_run:
            console.print("\n[cyan]Fetching available groups...[/cyan]")
            groups = client.get_groups()
            fetcher._display_groups(groups)
            
            if list_groups:
                sys.exit(0)
            
            if dry_run:
                console.print("\n[green]Dry run complete. Connection successful![/green]")
                sys.exit(0)
        
        # Validate input
        if not group_id and not all_groups:
            console.print("[red]Error: Please specify either --group-id or --all-groups[/red]")
            console.print("Use --list-groups to see available groups")
            sys.exit(1)
        
        # Prepare date filters
        created_after = None
        if days_back:
            created_after = datetime.now() - timedelta(days=days_back)
            console.print(f"[cyan]Filtering tickets created after {created_after.strftime('%Y-%m-%d')}[/cyan]")
        
        # Prepare status filter
        ticket_status = None if status == 'all' else status
        
        # Fetch tickets
        console.print("\n[bold cyan]Fetching tickets...[/bold cyan]")
        
        if all_groups:
            all_tickets_dict = fetcher.fetch_all_group_tickets(
                status=ticket_status,
                use_cache=use_cache
            )
            # Flatten all tickets into single list
            tickets = []
            for group_tickets in all_tickets_dict.values():
                tickets.extend(group_tickets)
        else:
            tickets = fetcher.fetch_tickets_by_group(
                group_id=group_id,
                status=ticket_status,
                created_after=created_after,
                use_cache=use_cache
            )
        
        if not tickets:
            console.print("[yellow]No tickets found with the specified criteria[/yellow]")
            sys.exit(0)
        
        console.print(f"[green]Found {len(tickets)} tickets[/green]")
        
        # Extract emails
        console.print("\n[bold cyan]Extracting email addresses...[/bold cyan]")
        email_data = extractor.extract_from_tickets(
            tickets,
            include_ccs=include_ccs,
            include_comments=include_comments
        )
        
        if not email_data:
            console.print("[yellow]No email addresses found in tickets[/yellow]")
            sys.exit(0)
        
        # Display summary
        extractor.display_email_summary(email_data)
        
        # Export data
        output_dir = Path(output) if output else config.output_dir
        formatter = OutputFormatter(output_dir)
        
        console.print(f"\n[cyan]Exporting to {format.upper()} format...[/cyan]")
        output_file = formatter.export_emails(
            email_data,
            format=format,
            filename_prefix=f"zendesk_emails_{group_id or 'all'}"
        )
        
        # Print final summary
        formatter.print_summary(email_data)
        
        console.print("\n[bold green]✓ Export complete![/bold green]")
        console.print(f"Output saved to: [cyan]{output_file}[/cyan]")
        
    except ZendeskAPIError as e:
        logger.error(f"Zendesk API error: {e}")
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()