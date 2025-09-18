# Zendesk Email Extractor

🎯 A powerful Python tool to extract and export email addresses from Zendesk tickets by group, with advanced filtering and multiple export formats.

## 🌟 Features

- **Extract emails from multiple sources**:
  - Ticket requesters
  - CC recipients
  - Ticket comments (optional)
  - Custom fields

- **Flexible filtering**:
  - Filter by group ID or all groups
  - Filter by ticket status (open, pending, solved, closed)
  - Filter by date range

- **Multiple export formats**:
  - CSV - Simple spreadsheet format
  - JSON - Structured data with metadata
  - TXT - Plain text list
  - Excel - Multi-sheet workbook with statistics

- **Smart features**:
  - Automatic pagination handling
  - Rate limiting and retry logic
  - Response caching to reduce API calls
  - Progress indicators
  - Email validation and deduplication
  - Comprehensive error handling

## 📋 Prerequisites

- Python 3.8 or higher
- Zendesk account with API access
- API token (generate at https://alderac.zendesk.com/admin/api/settings/tokens)

## 🚀 Installation

1. **Clone the repository**:
```bash
git clone https://github.com/alderacgit/ZenDeskExport.git
cd ZenDeskExport
```

2. **Create and activate virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure credentials**:
```bash
cp .env.example .env
```

Edit `.env` file with your Zendesk credentials:
```env
ZENDESK_EMAIL=your-email@example.com
ZENDESK_API_TOKEN=your-api-token-here
ZENDESK_SUBDOMAIN=alderac
```

## 💻 Usage

### Basic Commands

**Test connection and list available groups**:
```bash
python src/main.py --list-groups
```

**Extract emails from a specific group**:
```bash
python src/main.py -g GROUP_ID -f csv
```

**Extract emails from all groups**:
```bash
python src/main.py --all-groups -f excel
```

### Advanced Options

**Filter by ticket status**:
```bash
python src/main.py -g GROUP_ID --status open -f csv
```

**Filter by date range (last 30 days)**:
```bash
python src/main.py -g GROUP_ID --days-back 30 -f json
```

**Include emails from comments**:
```bash
python src/main.py -g GROUP_ID --include-comments -f excel
```

**Use cached data (faster for testing)**:
```bash
python src/main.py -g GROUP_ID --use-cache -f csv
```

**Specify custom output directory**:
```bash
python src/main.py -g GROUP_ID -o /path/to/output -f csv
```

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--group-id` | `-g` | Zendesk group ID to fetch tickets from |
| `--all-groups` | | Fetch tickets from all groups |
| `--status` | | Filter by status: open, pending, solved, closed, all |
| `--days-back` | | Only fetch tickets created in the last N days |
| `--include-ccs` | | Include CC email addresses (default: true) |
| `--include-comments` | | Extract emails from ticket comments |
| `--format` | `-f` | Output format: csv, json, txt, excel |
| `--output` | `-o` | Output directory path |
| `--dry-run` | | Test connection without fetching data |
| `--use-cache` | | Use cached ticket data if available |
| `--clear-cache` | | Clear all cached data before running |
| `--verbose` | `-v` | Enable verbose output |
| `--list-groups` | | List all available groups and exit |
| `--help` | | Show help message |

## 📊 Output Formats

### CSV Format
Simple spreadsheet with columns:
- Email address
- Ticket count
- Type (Requester/CC/Comment)
- First seen date
- Last seen date
- Sample ticket IDs

### JSON Format
Structured data including:
- Complete email metadata
- Ticket associations
- Statistics
- Export timestamp

### Excel Format
Multi-sheet workbook:
- **Emails**: All extracted emails with metadata
- **Statistics**: Summary statistics
- **Top Requesters**: Top 50 most active requesters

### TXT Format
Simple list of unique email addresses, one per line.

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Required
ZENDESK_EMAIL=your-email@example.com
ZENDESK_API_TOKEN=your-api-token
ZENDESK_SUBDOMAIN=alderac

# Optional
ZENDESK_DEFAULT_GROUP_ID=123456
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### API Rate Limits

- Zendesk allows 700 requests per minute for Essential plans
- The tool automatically handles rate limiting and retries
- Use `--use-cache` to reduce API calls during testing

## 🐛 Troubleshooting

### Common Issues

**Authentication Error**:
- Verify your email and API token in `.env`
- Ensure API token has appropriate permissions
- Check subdomain spelling

**No Tickets Found**:
- Verify group ID exists
- Check date range filters
- Try removing status filters

**Rate Limit Errors**:
- Use `--use-cache` for repeated runs
- Reduce concurrent requests
- Wait and retry

**Memory Issues with Large Datasets**:
- Process one group at a time
- Use date filters to limit scope
- Export in smaller batches

### Debug Mode

Enable verbose logging for debugging:
```bash
python src/main.py -g GROUP_ID -v
```

Logs are saved to `logs/zendesk_export_YYYYMMDD.log`

## 📁 Project Structure

```
ZenDeskExport/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI interface
│   ├── zendesk_client.py    # API client
│   ├── ticket_fetcher.py    # Ticket retrieval
│   ├── email_extractor.py   # Email extraction
│   └── output_formatter.py  # Export formatting
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration
├── tests/                   # Unit tests
├── logs/                    # Log files
├── output/                  # Export files
├── .cache/                  # Cache directory
├── .env.example            # Environment template
├── .gitignore              # Git ignore file
├── requirements.txt        # Python dependencies
└── README.md              # Documentation
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Submit a pull request

## 📜 License

MIT License - feel free to use this tool for your needs.

## 🆘 Support

For issues or questions:
- Create an issue on GitHub
- Contact the development team

## 🎉 Acknowledgments

- Zendesk API documentation
- Python Requests library
- Rich console library for beautiful CLI output
