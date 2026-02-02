import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import logging

# Configure logging
logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        try:
            self.sia = SentimentIntensityAnalyzer()
        except LookupError:
            nltk.download('vader_lexicon')
            self.sia = SentimentIntensityAnalyzer()

    def analyze_impact(self, text: str, context_data: dict = None) -> dict:
        """
        Analyzes the text and returns a dictionary with scores, logic, and impact window.
        """
        score = self.sia.polarity_scores(text)['compound']
        
        impact_window = self.categorize_impact_window(text)
        logic, reasoning = self.generate_heuristic_logic(text, score)
        
        # Calculate opportunity score (0-100)
        # Simple heuristic: strong sentiment + logic match = higher score
        opp_score = abs(score) * 100 
        
        return {
            "sentiment_score": score,
            "impact_window": impact_window,
            "logic": logic,
            "reasoning": reasoning,
            "opportunity_score": opp_score
        }

    def categorize_impact_window(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ['earnings', 'guidance', 'beat', 'miss', 'spike']):
            return "Short-term"
        elif any(w in text_lower for w in ['sec', 'regulation', 'lawsuit', 'macro']):
            return "Long-term"
        return "Medium-term"

    def generate_heuristic_logic(self, text: str, score: float) -> tuple[str, str]:
        """Returns (logic, reasoning) based on simple keywords."""
        text_lower = text.lower()
        
        if "revenue growth" in text_lower and score < 0:
             return (
                 "Conflict: Growth vs Price Action",
                 "Stock is down despite revenue growth, possibly due to profitability concerns or macro headwinds."
             )
        
        if "profit" in text_lower and score > 0:
            return (
                "Profitability Driver",
                "Positive sentiment driven by profitability metrics."
            )

        if score < -0.5:
             return ("Negative Sentiment", "Significant negative sentiment detected in headline.")
        
        if score > 0.5:
            return ("Positive Momentum", "Strong positive sentiment detected.")
            
        return ("Neutral/Mixed", "Mixed signals or neutral update.")
