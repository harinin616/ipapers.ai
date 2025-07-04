# Daily Feed System - No Backend API Required

This document explains how the Daily Feed system now works without requiring backend API communication.

## How It Works

The Daily Feed now operates as a **static system** where:

1. **Data Generation**: The pipeline generates summaries and word clouds from arXiv papers
2. **Static File Generation**: A script copies all data to the frontend's public folder as static files
3. **Frontend Access**: The frontend reads data directly from static JSON files

## Key Files

### Backend Scripts
- `copy_to_frontend.py` - Copies generated data to frontend public folder
- `run_full_pipeline.py` - Generates daily feed data (word clouds, summaries)
- `summary_generator.py` - Generates topic summaries from papers

### Frontend
- `frontend/src/views/DailyFeedView.vue` - Displays daily feed (reads from static files)
- `frontend/public/daily_feed/` - Contains all static daily feed data

## Usage

### 1. Generate Daily Feed Data

```bash
# From backend/scripts/daily_feed/
python run_full_pipeline.py --date 2025-07-03
python summary_generator.py --date 2025-07-03
```

### 2. Copy Data to Frontend

```bash
# From backend/scripts/daily_feed/
python copy_to_frontend.py --date 2025-07-03
```

### 3. Frontend Access

The frontend automatically reads from `/daily_feed/daily_feed.json` and displays:
- Word cloud images for each category
- Topic summaries for each category
- "There is no new paper for today" for empty categories

## Data Structure

The generated `daily_feed.json` contains:

```json
{
  "categories": [
    {
      "category": "computer_science_cs",
      "display_name": "Computer Science (cs.)",
      "word_cloud_url": "/daily_feed/Computer_Science_cs_wordcloud.png",
      "summaries": ["markdown content..."]
    }
  ],
  "last_updated": "2025-07-03T...",
  "date": "2025-07-03",
  "total_categories": 7,
  "generated_at": "2025-07-03 10:30:00"
}
```

## Benefits

1. **No Backend Dependency**: Frontend works independently
2. **Better Performance**: Static files load faster than API calls
3. **Simplified Architecture**: No need for backend API routes
4. **Easier Deployment**: Just copy static files to any web server

## Automation

To automate daily updates, add to your cron job:

```bash
# Daily at 6 AM
0 6 * * * cd /path/to/backend/scripts/daily_feed && python run_full_pipeline.py && python summary_generator.py && python copy_to_frontend.py
```

## Troubleshooting

### Empty Categories
If a category shows "There is no new paper for today":
- Check if the pipeline generated data for that category
- Verify the date parameter matches generated data
- Run the copy script to ensure data is in frontend/public/daily_feed/

### Missing Images
If word clouds don't display:
- Check that `*_wordcloud.png` files exist in `frontend/public/daily_feed/`
- Verify image paths in `daily_feed.json`
- Ensure proper file permissions

### Frontend Errors
If the frontend shows loading errors:
- Ensure `daily_feed.json` exists in `frontend/public/daily_feed/`
- Check browser console for specific error messages
- Verify JSON file is valid (not corrupted) 