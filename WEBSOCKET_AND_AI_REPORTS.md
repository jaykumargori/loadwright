# WebSocket Testing & AI-Powered Reports

## WebSocket Testing

The tool now supports WebSocket testing with proper test plan generation.

### Creating WebSocket Tests

```bash
python main.py -c "create test" -p '{
  "test_name": "websocket_test",
  "type": "websocket",
  "ws_url": "wss://echo.websocket.events",
  "messages": ["Hello", "World", "Test Message"],
  "threads": 5,
  "ramp_up": 2,
  "loops": 10
}'
```

### Parameters:
- `ws_url`: WebSocket URL (ws:// or wss://). If not provided, defaults to `wss://echo.websocket.events`
- `messages`: List of messages to send. If not provided, defaults to `["Hello", "World"]`
- `threads`: Number of concurrent threads
- `ramp_up`: Ramp-up time in seconds
- `loops`: Number of loops per thread

**Important Notes**: 
- WebSocket testing requires the WebSocket plugin to be installed in JMeter.
- **⚠️ Deprecated Service**: `wss://echo.websocket.org` is deprecated and no longer available. 
- **Recommended Alternatives**:
  - `wss://echo.websocket.events` (public echo server - default)
  - `ws://localhost:8080` (for local testing)
  - Your own WebSocket server endpoint

## AI-Powered HTML Reports

The tool now generates dynamic, AI-powered HTML reports that analyze test results and provide insights.

### Features:
- **AI Analysis**: Uses OpenAI, Anthropic, or Gemini to analyze test results
- **Dynamic Charts**: Interactive charts for response codes, endpoint performance, and success rates
- **Actionable Insights**: Recommendations and findings based on test results
- **Beautiful UI**: Modern, responsive design with gradient themes

### Generating AI Reports

```bash
# Using OpenAI (default)
python main.py -c "run test" -p '{
  "test_plan": "api_test2.jmx",
  "generate_report": true,
  "use_ai": true,
  "llm_provider": "openai"
}'

# Using Anthropic
python main.py -c "run test" -p '{
  "test_plan": "api_test2.jmx",
  "generate_report": true,
  "use_ai": true,
  "llm_provider": "anthropic"
}'

# Using Google Gemini
python main.py -c "run test" -p '{
  "test_plan": "api_test2.jmx",
  "generate_report": true,
  "use_ai": true,
  "llm_provider": "gemini"
}'
```

### Report Contents:
1. **Executive Summary**: High-level overview of test results
2. **Key Findings**: Important insights from the test
3. **Performance Insights**: Analysis of response times and throughput
4. **Error Analysis**: Detailed breakdown of any errors
5. **Recommendations**: Actionable items for improvement
6. **Interactive Charts**: Visual representation of data
7. **Endpoint Details**: Comprehensive endpoint performance table

### Configuration

Set your API keys in environment variables:

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GEMINI_API_KEY="your-gemini-key"
```

Or in `.env` file:
```
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
LLM_PROVIDER=openai  # or anthropic, gemini
```

### Report Location

AI-powered reports are saved in:
```
results/report_<timestamp>/index.html
```

Open the HTML file in your browser to view the interactive report.

## Example: Complete Workflow

```bash
# 1. Create a WebSocket test
python main.py -c "create test" -p '{
  "test_name": "ws_test",
  "type": "websocket",
  "ws_url": "wss://echo.websocket.events",
  "messages": ["ping", "pong"],
  "threads": 3,
  "ramp_up": 1,
  "loops": 5
}'

# 2. Run the test with AI-powered report
python main.py -c "run test" -p '{
  "test_plan": "ws_test.jmx",
  "generate_report": true,
  "use_ai": true,
  "llm_provider": "gemini"
}'
```

## Standard Reports

If you prefer the standard JMeter HTML report:

```bash
python main.py -c "run test" -p '{
  "test_plan": "api_test2.jmx",
  "generate_report": true,
  "use_ai": false
}'
```

