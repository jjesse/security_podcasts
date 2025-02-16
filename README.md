# Security Podcasts Tracking System

This repository maintains a list of security-focused podcasts and tracks their activity status.

## Files

- `List_of_podcast.md`: Contains the comprehensive list of security podcasts with their descriptions and links
- `check_active_podcasts.py`: Python script that checks podcast activity status
- `podcast_status.csv`: Contains the current status of active podcasts
- `podcast_update.csv`: Contains the full status report of all podcasts
- `changelog.txt`: Tracks all changes and updates to the system

## Requirements

To run the scripts in this repository, you need Python 3.6+ and the following packages:

```bash
pip install requests
pip install beautifulsoup4
pip install pandas
```

## How It Works

The system uses a Python script (`check_active_podcasts.py`) to:

1. Read podcast URLs from the markdown file
2. Check each podcast's last update time
3. Generate two CSV files:
   - `podcast_status.csv`: Shows only active podcasts (updated within 30 days)
   - `podcast_update.csv`: Shows all podcasts with their current status

## Usage

To check podcast status:

```bash
python check_active_podcasts.py
```

## Updates

See `changelog.txt` for a detailed history of updates and changes to the podcast list and system.
