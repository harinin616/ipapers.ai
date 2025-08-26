# Search Summary Feature Usage

This document explains how to use the new search summary feature that generates engaging news-style summaries for search results, following the same format as the DailyFeed summary generator.

## Overview

The search summary feature provides two ways to generate summaries:

1. **Integrated with search**: Get search results and summary in one API call
2. **Standalone summary**: Generate summary for existing search results

## API Endpoints

### 1. Enhanced Search with Summary

**Endpoint**: `POST /api/search/`

**Request Body**:
```json
{
  "query": "machine learning neural networks",
  "limit": 30,
  "include_summary": true,
  "summary_type": "full"
}
```

**Parameters**:
- `query`: Search query string
- `limit`: Number of results (1-100)
- `categories`: Optional list of categories to filter
- `include_summary`: Boolean flag to generate summary
- `summary_type`: Either "full" or "quick"

**Response**:
```json
{
  "results": [...papers...],
  "count": 15,
  "summary": "# Research Insights: Machine Learning Neural Networks\n\nScientists have achieved remarkable breakthroughs in neural network architectures..."
}
```

### 2. Standalone Summary Generation

**Endpoint**: `POST /api/search-summary/`

**Request Body**:
```json
{
  "query": "machine learning neural networks",
  "papers": [...array of paper objects...],
  "summary_type": "full"
}
```

**Response**:
```json
{
  "query": "machine learning neural networks",
  "summary": "# Research Insights: Machine Learning Neural Networks\n\n...",
  "paper_count": 15
}
```

## Summary Types

### Full Summary
- Comprehensive news-style article (4-6 paragraphs)
- Includes opening hook, key findings, research landscape, and future implications
- Citations converted to hyperlinks
- Engaging, accessible tone for general audience

### Quick Summary
- Brief 2-3 sentence overview
- Highlights main research themes
- Concise but engaging
- Limited to first 10 papers

## Features

### Citation Handling
- Uses `[1], [2], [3]` format for citations
- Automatically converts to hyperlinks:
  - arXiv papers: Links to `https://arxiv.org/abs/{paper_id}`
  - Other platforms: Links to PDF URL
  - Fallback: Plain text title

### Writing Style
- Science journalist tone
- Focus on "breakthroughs," "advances," "innovations"
- Accessible to general audience
- Active voice and dynamic language

## Example Usage

### Python Client Example
```python
import requests

# Search with summary
response = requests.post("http://localhost:8000/api/search/", json={
    "query": "quantum computing algorithms",
    "limit": 20,
    "include_summary": True,
    "summary_type": "full"
})

search_results = response.json()
print(f"Found {search_results['count']} papers")
print(f"Summary:\n{search_results['summary']}")
```

### JavaScript/Frontend Example
```javascript
const searchWithSummary = async (query) => {
  const response = await fetch('/api/search/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      limit: 25,
      include_summary: true,
      summary_type: 'full'
    })
  });
  
  const data = await response.json();
  return {
    papers: data.results,
    summary: data.summary,
    count: data.count
  };
};
```

## Configuration

### Environment Variables
The summary service requires the following environment variable:
- `GEMINI_API_KEY`: API key for Google's Gemini model

### Error Handling
- Invalid API key: Returns error message in summary field
- Empty results: Returns appropriate "no results" message
- API failures: Graceful degradation with error message

## Integration with DailyFeed

The search summary service uses the same underlying approach as the DailyFeed summary generator:

1. **Same LLM Service**: Uses Gemini API via OpenAI client
2. **Same Writing Style**: News journalist tone with engaging language
3. **Same Citation Format**: `[1], [2]` with hyperlink conversion
4. **Same Structure**: Hook → Key Points → Future Impact

This ensures consistency across the platform and leverages the proven effectiveness of the DailyFeed approach.

## Testing

Run the test script to verify functionality:
```bash
cd backend
python test_search_summary.py
```

The test script will verify:
- Full summary generation
- Quick summary generation
- Error handling for empty results
- Citation link conversion
