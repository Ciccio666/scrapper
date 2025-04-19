# Web Scraper API

A FastAPI-based web scraping application with advanced capabilities for content extraction, JavaScript rendering, and data retrieval.

## Key Features

- Extract content from websites using Selenium (handles JavaScript)
- Clean text extraction with Trafilatura
- Recursive crawling with domain restriction and depth control
- Special handling for chat.openai.com shared links
- Selector-based content extraction
- JavaScript rendering with Pyppeteer
- Comprehensive metadata extraction
- Link extraction and analysis
- Screenshot capture
- Proxy support for bypassing geo-restrictions

## API Endpoints

### Core Endpoints
- `/api/scrape` - Extract content using Selenium
- `/api/scrape/trafilatura` - Extract clean text using Trafilatura

### Advanced Endpoints
- `/api/extract` - Extract content using CSS selectors
- `/api/render` - Render page with JavaScript execution
- `/api/metadata` - Extract comprehensive metadata
- `/api/links` - Extract all links with additional information
- `/api/screenshot` - Capture screenshots of webpages

## Usage

1. Start the server:
   ```
   python main.py
   ```

2. Use the API endpoints with curl or any HTTP client:
   ```
   curl -X POST "http://localhost:5000/api/scrape" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "user_agent": "chrome-windows"}'
   ```

3. See [example_api_calls.md](example_api_calls.md) for detailed examples of all endpoints.

## Testing

Run the test script to verify all endpoints:
```
./run_tests.sh
```

This will start the server and run tests on all endpoints.

### Testing Proxy Support

To test proxy support specifically, use the proxy test script:
```
python test_proxy.py --host your-proxy-host --port your-proxy-port
```

You can also test authenticated proxies:
```
python test_proxy.py --host your-proxy-host --port your-proxy-port --username user --password pass
```

To test all endpoints with a proxy:
```
python test_proxy.py --host your-proxy-host --port your-proxy-port --test-all
```

## Web Interface

A web interface is also available at the root URL:
```
http://localhost:5000/
```

## Settings

Configure the scraper settings at:
```
http://localhost:5000/settings
```