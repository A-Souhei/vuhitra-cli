# Kibana Setup Guide

Kibana is the official UI for viewing and analyzing data in ElasticSearch.

## Starting Kibana

Start all services including Kibana:
```bash
cd services
docker compose up -d
```

## Accessing Kibana

1. Open your browser and go to: **http://localhost:5601**
2. Wait for Kibana to fully start (can take 30-60 seconds)

## Viewing Feedback Data

### First Time Setup

1. **Go to Discover**:
   - Click the hamburger menu (☰) in the top left
   - Navigate to **Analytics** → **Discover**

2. **Create Data View**:
   - Click "Create a data view"
   - Name: `LLM Feedback`
   - Index pattern: `llm_feedback*`
   - Timestamp field: `timestamp`
   - Click "Save data view to Kibana"

### Viewing Data

Once your data view is created:

1. **View All Feedback**:
   - Go to **Discover**
   - Select "LLM Feedback" from the dropdown
   - You'll see all feedback entries with heuristics

2. **Useful Columns to Add**:
   - `rating` - User satisfaction rating
   - `prompt` - User's question/prompt
   - `response` - LLM's response
   - `prompt_keywords` - Keywords extracted from prompt
   - `prompt_sentiment_vader` - Sentiment score of prompt
   - `is_code_response` - Whether response contains code
   - `code_purpose` - Purpose of code if detected
   - `execution_time_ms` - Response time

3. **Filter and Search**:
   - Filter by rating: `rating:5` (only 5-star ratings)
   - Filter code responses: `is_code_response:true`
   - Search prompts: Enter text in the search bar
   - Filter by sentiment: `prompt_sentiment_vader > 0` (positive prompts)

### Creating Visualizations

1. **Go to Visualize Library**:
   - Click hamburger menu → **Analytics** → **Visualize Library**
   - Click "Create visualization"

2. **Example Visualizations**:
   - **Rating Distribution**: Pie chart showing rating counts
   - **Sentiment Over Time**: Line chart of average sentiment by timestamp
   - **Code vs Non-Code**: Bar chart comparing response types
   - **Top Keywords**: Word cloud of most common keywords
   - **Average Response Time**: Metric showing avg execution_time_ms

### Creating Dashboards

1. **Go to Dashboard**:
   - Click hamburger menu → **Analytics** → **Dashboard**
   - Click "Create dashboard"
   - Add your visualizations
   - Save the dashboard

## Quick Tips

- **Refresh Interval**: Set auto-refresh in the top right (e.g., every 30 seconds) to see new feedback in real-time
- **Time Range**: Adjust the time picker in the top right to filter by date
- **Export Data**: You can export any view to CSV for analysis
- **Dev Tools**: Use hamburger menu → **Management** → **Dev Tools** to run raw ElasticSearch queries

## Troubleshooting

- **Can't connect**: Make sure ElasticSearch is running: `docker ps | grep elasticsearch`
- **No data**: Check if feedback is being collected (config `feedback_enabled: true`)
- **Slow loading**: Kibana needs ~1GB RAM; check Docker resources
