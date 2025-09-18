"""
Module for formatting and exporting extracted email data
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
import pandas as pd
from rich.console import Console

console = Console()


class OutputFormatter:
    """Class for formatting and exporting email data"""
    
    def __init__(self, output_dir: Path):
        """
        Initialize output formatter
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export_emails(
        self,
        email_data: Dict[str, Dict[str, Any]],
        format: str = "csv",
        filename_prefix: str = "emails",
        include_stats: bool = True
    ) -> Path:
        """
        Export email data to file
        
        Args:
            email_data: Dictionary of email data
            format: Output format (csv, json, txt)
            filename_prefix: Prefix for output filename
            include_stats: Whether to include statistics
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filepath = self._export_to_csv(email_data, f"{filename_prefix}_{timestamp}")
        elif format == "json":
            filepath = self._export_to_json(email_data, f"{filename_prefix}_{timestamp}", include_stats)
        elif format == "txt":
            filepath = self._export_to_txt(email_data, f"{filename_prefix}_{timestamp}")
        elif format == "excel":
            filepath = self._export_to_excel(email_data, f"{filename_prefix}_{timestamp}", include_stats)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        console.print(f"[green]✓[/green] Exported to: [cyan]{filepath}[/cyan]")
        return filepath
    
    def _export_to_csv(self, email_data: Dict[str, Dict[str, Any]], filename: str) -> Path:
        """Export email data to CSV file"""
        filepath = self.output_dir / f"{filename}.csv"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'email', 
                'ticket_count', 
                'is_requester', 
                'is_cc',
                'is_from_comment',
                'first_seen', 
                'last_seen',
                'ticket_ids'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for email, data in sorted(email_data.items()):
                row = {
                    'email': email,
                    'ticket_count': data['ticket_count'],
                    'is_requester': 'Yes' if data['is_requester'] else 'No',
                    'is_cc': 'Yes' if data['is_cc'] else 'No',
                    'is_from_comment': 'Yes' if data['is_from_comment'] else 'No',
                    'first_seen': data['first_seen'] or '',
                    'last_seen': data['last_seen'] or '',
                    'ticket_ids': ','.join(str(tid) for tid in data['ticket_ids'][:10])  # First 10 IDs
                }
                writer.writerow(row)
        
        return filepath
    
    def _export_to_json(
        self, 
        email_data: Dict[str, Dict[str, Any]], 
        filename: str,
        include_stats: bool
    ) -> Path:
        """Export email data to JSON file"""
        filepath = self.output_dir / f"{filename}.json"
        
        output = {
            'export_date': datetime.now().isoformat(),
            'total_emails': len(email_data),
            'emails': email_data
        }
        
        if include_stats:
            from .email_extractor import EmailExtractor
            extractor = EmailExtractor()
            output['statistics'] = extractor.get_email_statistics(email_data)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(output, jsonfile, indent=2, default=str)
        
        return filepath
    
    def _export_to_txt(self, email_data: Dict[str, Dict[str, Any]], filename: str) -> Path:
        """Export email list to plain text file"""
        filepath = self.output_dir / f"{filename}.txt"
        
        with open(filepath, 'w', encoding='utf-8') as txtfile:
            # Write header
            txtfile.write(f"# Email Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            txtfile.write(f"# Total unique emails: {len(email_data)}\n")
            txtfile.write("#" + "=" * 50 + "\n\n")
            
            # Write emails (one per line)
            for email in sorted(email_data.keys()):
                txtfile.write(f"{email}\n")
        
        return filepath
    
    def _export_to_excel(
        self,
        email_data: Dict[str, Dict[str, Any]],
        filename: str,
        include_stats: bool
    ) -> Path:
        """Export email data to Excel file with multiple sheets"""
        filepath = self.output_dir / f"{filename}.xlsx"
        
        # Prepare main data
        records = []
        for email, data in email_data.items():
            records.append({
                'Email': email,
                'Ticket Count': data['ticket_count'],
                'Type': self._get_email_type(data),
                'First Seen': data['first_seen'],
                'Last Seen': data['last_seen'],
                'Is Requester': data['is_requester'],
                'Is CC': data['is_cc'],
                'From Comment': data['is_from_comment']
            })
        
        # Create Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main email data sheet
            df_emails = pd.DataFrame(records)
            df_emails = df_emails.sort_values('Ticket Count', ascending=False)
            df_emails.to_excel(writer, sheet_name='Emails', index=False)
            
            # Statistics sheet
            if include_stats:
                from .email_extractor import EmailExtractor
                extractor = EmailExtractor()
                stats = extractor.get_email_statistics(email_data)
                
                stats_data = [
                    {'Metric': 'Total Unique Emails', 'Value': stats['total_unique_emails']},
                    {'Metric': 'Total Tickets', 'Value': stats['total_tickets']},
                    {'Metric': 'Requester Emails', 'Value': stats['requester_emails']},
                    {'Metric': 'CC Emails', 'Value': stats['cc_emails']},
                    {'Metric': 'Comment Emails', 'Value': stats['comment_emails']},
                    {'Metric': 'Avg Tickets per Email', 'Value': stats['avg_tickets_per_email']}
                ]
                
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            # Top requesters sheet
            requester_emails = [
                (email, data) for email, data in email_data.items() 
                if data['is_requester']
            ]
            requester_emails.sort(key=lambda x: x[1]['ticket_count'], reverse=True)
            
            top_requesters = []
            for email, data in requester_emails[:50]:  # Top 50
                top_requesters.append({
                    'Email': email,
                    'Ticket Count': data['ticket_count'],
                    'First Seen': data['first_seen'],
                    'Last Seen': data['last_seen']
                })
            
            if top_requesters:
                df_requesters = pd.DataFrame(top_requesters)
                df_requesters.to_excel(writer, sheet_name='Top Requesters', index=False)
        
        return filepath
    
    def _get_email_type(self, data: Dict[str, Any]) -> str:
        """Get email type string"""
        types = []
        if data['is_requester']:
            types.append("Requester")
        if data['is_cc']:
            types.append("CC")
        if data['is_from_comment']:
            types.append("Comment")
        return ", ".join(types) if types else "Unknown"
    
    def print_summary(self, email_data: Dict[str, Dict[str, Any]]):
        """Print summary to console"""
        if not email_data:
            console.print("[yellow]No emails to display[/yellow]")
            return
        
        console.print("\n[bold cyan]Email Export Summary[/bold cyan]")
        console.print("=" * 50)
        
        # Basic stats
        total_emails = len(email_data)
        requester_count = sum(1 for d in email_data.values() if d['is_requester'])
        cc_count = sum(1 for d in email_data.values() if d['is_cc'])
        
        console.print(f"Total unique emails: [green]{total_emails}[/green]")
        console.print(f"Requester emails: [yellow]{requester_count}[/yellow]")
        console.print(f"CC emails: [yellow]{cc_count}[/yellow]")
        
        # Top 5 emails by ticket count
        sorted_emails = sorted(
            email_data.items(),
            key=lambda x: x[1]['ticket_count'],
            reverse=True
        )
        
        console.print("\n[bold]Top 5 emails by ticket count:[/bold]")
        for email, data in sorted_emails[:5]:
            console.print(f"  • {email}: {data['ticket_count']} tickets")
        
        console.print("=" * 50)