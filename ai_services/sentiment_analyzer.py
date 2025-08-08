from textblob import TextBlob
from transformers import pipeline
import torch
import os
import json
import requests
# from config import Config


def analyze_sentiment_with_api(text):
    api_url = os.getenv("SENTIMENT_ANALYSIS_URL")
    api_key = os.getenv("SENTIMENT_ANALYSIS_API_KEY")
    
    payload = json.dumps({"text": text})
    headers = {'Content-Type': 'application/json'}
    
    if api_key:
        headers['x-api-key'] = api_key

    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=5)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API error {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

    # Fallback using TextBlob
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if polarity > 0.2:
        label = 'positive'
    elif polarity < -0.2:
        label = 'negative'
    else:
        label = 'neutral'

    return {
        'score': float(polarity),
        'label': label,
        'polarity': float(polarity),
        'transformer_score': None,
        'transformer_label': None,
        'fallback': True
    }

def analyze_sentiment(text):
    """
    Analyze the sentiment of the given text using TextBlob and Transformers.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Dictionary containing sentiment score and label
    """
    # Simple sentiment analysis with TextBlob
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to 1
    
    # Map polarity to sentiment label
    if polarity > 0.2:
        label = 'positive'
    elif polarity < -0.2:
        label = 'negative'
    else:
        label = 'neutral'
    
    # For more complex analysis, we can use a pre-trained transformer model
    try:
        # Check if we have a GPU
        device = 0 if torch.cuda.is_available() else -1
        
        # Initialize sentiment analysis pipeline
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            # model="distilbert-base-uncased-finetuned-sst-2-english",
            model="prajjwal1/bert-tiny",
            device=device
        )
        
        # Get transformer-based sentiment
        result = sentiment_pipeline(text[:512])[0]  # Limit to 512 tokens
        
        # Map transformer label to our format
        transformer_score = result['score']
        transformer_label = result['label'].lower()
        
        # Combine both results (simple average for now)
        combined_score = (polarity + (transformer_score if transformer_label == 'positive' else -transformer_score)) / 2
        
        # Update label based on combined score
        if combined_score > 0.2:
            label = 'positive'
        elif combined_score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
            
        return {
            'score': float(combined_score),
            'label': label,
            'polarity': float(polarity),
            'transformer_score': float(transformer_score),
            'transformer_label': transformer_label
        }
        
    except Exception as e:
        # Fallback to TextBlob if there's an error with transformers
        print(f"Error in sentiment analysis: {str(e)}")
        return {
            'score': float(polarity),
            'label': label,
            'polarity': float(polarity),
            'transformer_score': None,
            'transformer_label': None
        }

if __name__ == "__main__":
   print(analyze_sentiment_with_api("I absolutely love this product!"))
