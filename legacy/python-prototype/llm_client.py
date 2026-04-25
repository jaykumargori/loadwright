"""
LLM Client for AI-powered test generation
"""
import logging
import os
from typing import Optional
from config import LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """LLM Client wrapper for different providers"""
    
    def __init__(self, provider: str = LLM_PROVIDER, model: str = LLM_MODEL):
        self.provider = provider
        self.model = model
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client based on provider"""
        try:
            if self.provider == "openai":
                try:
                    import openai
                    if not OPENAI_API_KEY:
                        logger.warning("OpenAI API key not found. LLM features will be limited.")
                        return
                    self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
                    logger.info("OpenAI client initialized")
                except ImportError:
                    logger.warning("OpenAI package not installed. Install with: pip install openai")
            
            elif self.provider == "anthropic":
                try:
                    import anthropic
                    if not ANTHROPIC_API_KEY:
                        logger.warning("Anthropic API key not found. LLM features will be limited.")
                        return
                    self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    logger.info("Anthropic client initialized")
                except ImportError:
                    logger.warning("Anthropic package not installed. Install with: pip install anthropic")
            
            elif self.provider == "gemini":
                try:
                    # Try new google.genai first (newer API)
                    try:
                        import google.genai as genai
                        if not GEMINI_API_KEY:
                            logger.warning("Gemini API key not found. LLM features will be limited.")
                            return
                        # New API uses Client instead of configure
                        self.client = genai.Client(api_key=GEMINI_API_KEY)
                        # Store model name for later use
                        self.model_name = self.model
                        logger.info("Gemini client initialized (using google.genai)")
                    except (ImportError, AttributeError):
                        # Fallback to deprecated google.generativeai
                        try:
                            import google.generativeai as genai
                            if not GEMINI_API_KEY:
                                logger.warning("Gemini API key not found. LLM features will be limited.")
                                return
                            genai.configure(api_key=GEMINI_API_KEY)
                            self.client = genai.GenerativeModel(self.model)
                            logger.warning("Gemini client initialized (using deprecated google.generativeai - please upgrade to google-genai)")
                        except ImportError:
                            logger.warning("Google Generative AI package not installed. Install with: pip install google-genai (or google-generativeai for legacy)")
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini client: {e}")
            
            else:
                logger.warning(f"Unknown LLM provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
    
    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate response from LLM"""
        if not self.client:
            logger.warning("LLM client not initialized. Returning empty response.")
            return ""
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in JMeter test plan creation. Generate valid JMeter XML test plans."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
                return response.choices[0].message.content
            
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system="You are an expert in JMeter test plan creation. Generate valid JMeter XML test plans.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
            elif self.provider == "gemini":
                full_prompt = f"You are an expert in JMeter test plan creation. Generate valid JMeter XML test plans.\n\n{prompt}"
                try:
                    # Check if using new google.genai API (Client) or old google.generativeai (GenerativeModel)
                    if hasattr(self.client, 'models'):
                        # New API: google.genai.Client
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=full_prompt,
                            config={
                                "max_output_tokens": max_tokens,
                                "temperature": 0.3
                            }
                        )
                        # New API response format
                        if hasattr(response, 'text'):
                            return response.text
                        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                            return response.candidates[0].content.parts[0].text
                        else:
                            return str(response)
                    else:
                        # Old API: google.generativeai.GenerativeModel
                        response = self.client.generate_content(
                            full_prompt,
                            generation_config={
                                "max_output_tokens": max_tokens,
                                "temperature": 0.3
                            }
                        )
                        # Handle both new and old response formats
                        if hasattr(response, 'text'):
                            return response.text
                        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                            return response.candidates[0].content.parts[0].text
                        else:
                            return str(response)
                except Exception as e:
                    logger.error(f"Error generating Gemini response: {e}")
                    return ""
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if LLM client is available"""
        return self.client is not None

