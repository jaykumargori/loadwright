# Quick Start Guide

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables (optional for LLM features):**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Ensure Docker is running:**
```bash
docker ps
```

## Basic Usage

### Start the Tool

```bash
# Interactive mode
python main.py --interactive

# Or use command line
python main.py -c "start container"
```

### Common Commands

1. **Start JMeter container:**
```bash
python main.py -c "start container"
```

2. **Create a simple API test:**
```bash
python main.py -c "create test" -p '{
  "test_name": "my_test",
  "type": "api",
  "endpoints": [{
    "name": "Test API",
    "domain": "httpbin.org",
    "path": "/get",
    "method": "GET"
  }],
  "threads": 5,
  "ramp_up": 1,
  "loops": 10
}'
```

3. **Run the test:**
```bash
python main.py -c "run test" -p '{
  "test_plan": "my_test.jmx",
  "generate_report": true
}'
```

4. **Check container status:**
```bash
python main.py -c "status"
```

## Python API Usage

```python
from agent import JMeterAgent

# Initialize agent
agent = JMeterAgent()

# Start container
agent.execute_command("start container", {})

# Create test
agent.execute_command("create test", {
    "test_name": "api_test",
    "type": "api",
    "endpoints": [{
        "domain": "api.example.com",
        "path": "/users",
        "method": "GET"
    }]
})

# Run test
agent.execute_command("run test", {
    "test_plan": "api_test.jmx"
})
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [example.py](example.py) for more examples
- Explore interactive mode for easier command execution

