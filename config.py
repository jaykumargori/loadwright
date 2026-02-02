"""
Configuration file for JMeter Automation Tool
"""
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try loading from project root first
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        # Try loading from current working directory
        load_dotenv(override=True)
except ImportError:
    # python-dotenv not installed, skip .env loading
    # User can still set environment variables manually
    pass
except Exception as e:
    # Silently fail if .env loading has issues
    pass

# Base paths
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / "tests"
RESULTS_DIR = BASE_DIR / "results"
JMETER_PLUGINS_DIR = BASE_DIR / "jmeter_plugins"

# Docker configuration
JMETER_IMAGE = "justb4/jmeter:latest"
JMETER_CONTAINER_NAME = "jmeter-automation"
JMETER_VERSION = "5.6.3"

# JMeter configuration
JMETER_HEAP = os.getenv("JMETER_HEAP", "1g")
JMETER_OPTS = os.getenv("JMETER_OPTS", "")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, gemini
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")

# Docker volumes
DOCKER_VOLUMES = {
    str(TESTS_DIR): "/tests",
    str(RESULTS_DIR): "/results",
    str(JMETER_PLUGINS_DIR): "/plugins"
}

# Create directories if they don't exist
TESTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
JMETER_PLUGINS_DIR.mkdir(exist_ok=True)

