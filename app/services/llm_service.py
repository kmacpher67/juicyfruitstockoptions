
import logging
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        """Initialize the Gemini Service with API key and model config."""
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set. Gemini Service will not function correctly.")
            self.model = None
            return

        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            logger.info(f"Gemini Service initialized with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Service: {e}", exc_info=True)
            self.model = None

    def generate_reasoning(self, context: str) -> str:
        """
        Generate generic reasoning or analysis based on the provided context.
        
        Args:
            context (str): The prompt or context provided by the user/system.
            
        Returns:
            str: The generated text response from Gemini.
        """
        if not self.model:
            return "Error: Gemini Service is not available (check API Key)."

        try:
            response = self.model.generate_content(context)
            if response.text:
                return response.text
            else:
                logger.warning("Gemini returned empty response.")
                return "Analysis unavailable."
        except Exception as e:
            logger.error(f"Error generating reasoning: {e}", exc_info=True)
            return f"Error generation reasoning: {str(e)}"

    def get_trade_analysis(self, ticker: str, ecosystem_context: dict) -> str:
        """
        Construct a specific trading agent prompt and get analysis.
        
        Args:
            ticker (str): The symbol being analyzed.
            ecosystem_context (dict): Dictionary containing relevant data like:
                - cost_basis (float)
                - current_price (float)
                - risk_profile (str)
                - strategies (list)
        
        Returns:
            str: Structured analysis from the Agent.
        """
        if not self.model:
             return "Error: Gemini Service is not available."

        # Construct the Prompt
        prompt = f"""
        You are a specialized Options Trading Agent for the 'Juicy Fruit' portfolio.
        
        Analyze the following scenario for Ticker: {ticker}
        
        Context Data:
        - Current Price: {ecosystem_context.get('current_price', 'N/A')}
        - Cost Basis: {ecosystem_context.get('cost_basis', 'N/A')}
        - Account Risk Profile: {ecosystem_context.get('risk_profile', 'Moderate')}
        - Available Strategies: {', '.join(ecosystem_context.get('strategies', []))}
        
        Please evaluate the best course of action. 
        Focus on:
        1. Risk/Reward ratio.
        2. Alignment with 'Bad Trade Heuristics' (No impulsive trades).
        3. Potential for Annualized Yield (using 365/DTE logic).
        
        Provide your reasoning in a clear, concise manner.
        """
        
        return self.generate_reasoning(prompt)

# Singleton instance for easy import
llm_service = GeminiService()
