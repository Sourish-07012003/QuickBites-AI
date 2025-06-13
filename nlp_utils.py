import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize # Not directly used in revised functions but kept if other parts need it
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
# from textblob import TextBlob # Not used in the current functions
import spacy
from collections import defaultdict

# --- NLTK Downloads (run once) ---
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('sentiment/vader_lexicon.zip')
    nltk.data.find('taggers/averaged_perceptron_tagger') # For POS tagging if needed by spaCy or other features
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet') # For lemmatization if spaCy model fails
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)

# --- Load spaCy model ---
NLP_SPACY = None
try:
    NLP_SPACY = spacy.load('en_core_web_sm')
except OSError:
    print("Downloading spaCy 'en_core_web_sm' model...")
    import subprocess
    try:
        subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
        NLP_SPACY = spacy.load('en_core_web_sm')
    except Exception as e:
        print(f"Failed to download or load spaCy model: {e}. Some NLP features might be limited.")

# --- Initialize NLP components ---
SIA = SentimentIntensityAnalyzer()
STOP_WORDS_SET = set(stopwords.words('english'))

# --- Food-related terms for preference matching (used by extract_food_preferences) ---
FOOD_TERMS = {
    'spicy': ['spicy', 'hot', 'chilli', 'chili', 'pepper', 'spice', 'fiery', 'zesty', 'tangy', 'piquant'],
    'sweet': ['sweet', 'sugar', 'honey', 'caramel', 'dessert', 'candy', 'chocolate', 'sugary', 'syrup'],
    'healthy': ['healthy', 'nutritious', 'organic', 'fresh', 'light', 'low-calorie', 'diet', 'balanced', 'wholesome', 'lean'],
    'vegetarian': ['vegetarian', 'veg', 'plant-based', 'meatless', 'veggie'], # 'vegan' handled by dietary_restrictions
    'non_vegetarian': ['non-vegetarian', 'non-veg', 'meat', 'chicken', 'mutton', 'fish', 'seafood', 'pork', 'beef', 'lamb'],
    'meal_type': ['breakfast', 'lunch', 'dinner', 'snack', 'brunch', 'supper', 'appetizer', 'starter', 'main course', 'side dish'],
    'taste': ['sweet', 'sour', 'bitter', 'spicy', 'savory', 'umami', 'tangy', 'mild', 'rich', 'creamy', 'smoky', 'herby'],
    'cooking_style': ['grilled', 'fried', 'baked', 'steamed', 'roasted', 'stir-fried', 'curried', 'poached', 'smoked', 'bbq']
}


def analyze_sentiment_text(text):
    """Analyze sentiment of a given text string."""
    if not isinstance(text, str):
        return 0.0 # Neutral for non-string input
    sentiment = SIA.polarity_scores(text)
    return sentiment['compound']  # Returns a score between -1 (negative) and 1 (positive)


def preprocess_text_for_preferences(text):
    """
    Preprocess text specifically for extracting food preferences.
    Keeps known food terms even if they are stopwords.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Simple tokenization using split is fine for preference keyword matching
    tokens = text.split()

    # Collect all terms from FOOD_TERMS for checking
    all_food_keywords = set()
    for term_list in FOOD_TERMS.values():
        all_food_keywords.update(term_list)

    # Remove general stopwords but keep specific food-related keywords
    # This logic might be too simple; spaCy based preference extraction is usually better for complex queries.
    processed_tokens = [token for token in tokens if token not in STOP_WORDS_SET or token in all_food_keywords]
    return ' '.join(processed_tokens)


def extract_food_preferences(text_query):
    """
    Extract food preferences from user input text using keyword matching.
    """
    preferences = {
        'spicy': False, 'sweet': False, 'healthy': False,
        'vegetarian': False, 'non_vegetarian': False,
        'meal_type': None, # Will store the first matched meal type string
        'taste': [],       # List of matched taste keywords
        'cooking_style': [] # List of matched cooking style keywords
    }
    if not isinstance(text_query, str) or not text_query.strip():
        return preferences

    processed_text = text_query.lower() # Work with lowercase text for matching

    # More robustly check for meal_type first as it's usually exclusive
    for meal in FOOD_TERMS['meal_type']:
        if meal in processed_text:
            preferences['meal_type'] = meal
            # Remove meal type from text to avoid it being matched as a taste/other keyword
            # This is a simple approach; more advanced NLP would handle overlapping terms better
            processed_text = processed_text.replace(meal, "", 1).strip()
            break # Found a meal type

    for category, terms_list in FOOD_TERMS.items():
        if category == 'meal_type': continue # Already handled

        for term in terms_list:
            if term in processed_text:
                if isinstance(preferences[category], list):
                    if term not in preferences[category]: # Avoid duplicates in lists
                        preferences[category].append(term)
                else: # For boolean flags
                    preferences[category] = True
                    # For veg/non-veg, if one is true, the other should be false (simplified assumption)
                    if category == 'vegetarian' and preferences['vegetarian']:
                        preferences['non_vegetarian'] = False
                    elif category == 'non_vegetarian' and preferences['non_vegetarian']:
                        preferences['vegetarian'] = False
    return preferences


def preprocess_text_for_semantic_search(text):
    """
    Preprocess text (like item descriptions or queries) for TF-IDF based semantic search.
    Uses spaCy for lemmatization and removal of stopwords/punctuation.
    """
    if not isinstance(text, str):
        return ""
    if NLP_SPACY is None: # Fallback if spaCy model failed to load
        tokens = text.lower().split()
        return " ".join([token for token in tokens if token.isalpha() and token not in STOP_WORDS_SET])

    doc = NLP_SPACY(text.lower())
    # Lemmatize, remove stopwords, punctuation, and non-alphabetic tokens
    processed_tokens = [
        token.lemma_ for token in doc
        if token.is_alpha and not token.is_stop and not token.is_punct
    ]
    return " ".join(processed_tokens)


def semantic_search(query, df_menu, top_n=5, description_col='Description'):
    """
    Perform semantic search on food items based on their descriptions.
    Returns a DataFrame of the top_n matching items from df_menu, with a 'similarity_score'.
    """
    if not query or df_menu.empty or description_col not in df_menu.columns:
        return pd.DataFrame() # Return empty DataFrame if inputs are invalid

    processed_query = preprocess_text_for_semantic_search(query)
    if not processed_query: # If query becomes empty after preprocessing
        return pd.DataFrame()

    # Preprocess all item descriptions
    item_descriptions = df_menu[description_col].apply(preprocess_text_for_semantic_search)

    # Create TF-IDF vectors
    vectorizer_tfidf = TfidfVectorizer() # Can use stop_words='english' here if not handled by preprocess
    
    try:
        # Combine query and descriptions for fitting the vectorizer
        all_texts_for_tfidf = [processed_query] + item_descriptions.tolist()
        tfidf_matrix = vectorizer_tfidf.fit_transform(all_texts_for_tfidf)
    except ValueError as e: # Handles case where vocabulary is empty after processing
        # print(f"TF-IDF Vectorization error: {e}. Likely due to empty vocabulary after preprocessing.")
        return pd.DataFrame()


    # Calculate cosine similarity between the query vector and all item description vectors
    # query_vector is tfidf_matrix[0:1]
    # item_vectors are tfidf_matrix[1:]
    similarity_scores_array = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

    if similarity_scores_array.size == 0:
        return pd.DataFrame()

    # Get top_n matching indices
    # argsort returns indices that would sort the array. We want the largest scores.
    # [::-1] reverses the sorted indices to get descending order.
    num_items_to_consider = min(top_n, len(similarity_scores_array[0]))
    top_indices = similarity_scores_array[0].argsort()[-num_items_to_consider:][::-1]

    # Filter out matches with zero similarity if we have more than top_n actual matches
    # Or if we simply want to ensure meaningful matches
    meaningful_indices = [idx for idx in top_indices if similarity_scores_array[0][idx] > 0.01] # Threshold
    if not meaningful_indices:
        return pd.DataFrame()
    
    top_meaningful_indices = meaningful_indices[:top_n]


    # Create results DataFrame
    results_df = df_menu.iloc[top_meaningful_indices].copy() # Use .copy() to avoid SettingWithCopyWarning
    results_df['semantic_score'] = similarity_scores_array[0][top_meaningful_indices] # Use 'semantic_score'

    # Sort by the new 'semantic_score' column in descending order
    results_df = results_df.sort_values('semantic_score', ascending=False)

    return results_df


# --- Advanced/Optional NLP Functions (kept for potential future use, not directly wired into main.py yet) ---

def analyze_user_feedback_text(feedback_text):
    """Analyze user feedback for sentiment and extract key noun phrases."""
    if not isinstance(feedback_text, str) or NLP_SPACY is None:
        return {'sentiment_score': 0.0, 'key_points': [], 'is_positive': False}

    sentiment_score = SIA.polarity_scores(feedback_text)['compound']
    doc = NLP_SPACY(feedback_text)
    key_points = list(set([chunk.text for chunk in doc.noun_chunks if chunk.root.pos_ in ['NOUN', 'PROPN']]))

    return {
        'sentiment_score': sentiment_score,
        'key_points': key_points,
        'is_positive': sentiment_score > 0.05 # Standard threshold for positive
    }


def extract_dietary_restrictions_from_text(text_query):
    """Extract common dietary restrictions from user input text using regex."""
    if not isinstance(text_query, str):
        return []
        
    restrictions_found = []
    text_lower = text_query.lower()

    # Patterns for common dietary restrictions
    restriction_patterns = {
        'gluten-free': r'\bgluten[-\s]?free\b|\bceliac\b',
        'dairy-free': r'\bdairy[-\s]?free\b|\blactose[-\s]?free\b|\bno dairy\b',
        'nut-free': r'\bnut[-\s]?free\b|\bpeanut[-\s]?free\b|\bno nuts\b',
        'halal': r'\bhalal\b',
        'kosher': r'\bkosher\b',
        'vegan': r'\bvegan\b',
        'vegetarian': r'\bvegetarian\b|\bveg\b(?!etable|\gies)' # Avoid matching 'vegetable'
    }

    for restriction_name, pattern_regex in restriction_patterns.items():
        if re.search(pattern_regex, text_lower):
            if restriction_name not in restrictions_found: # Avoid duplicates
                restrictions_found.append(restriction_name)
    return restrictions_found

# Example of a more complex recommendation function that might use order history
# This is NOT directly used by the main.py provided but shows a different approach
def generate_historical_recommendation_profile(user_order_history):
    """
    Generate a user profile based on their order history.
    (This is a conceptual function, not fully integrated with main.py's get_recommendations)
    """
    if not user_order_history:
        return {}

    # Example: Aggregate preferences for cuisine, price, time
    # Assumes 'Cuisine', 'Price' are in item details and order has 'timestamp'
    cuisine_preferences = defaultdict(int)
    # ... more complex aggregation logic ...

    # This would return a profile that could then be used by another recommendation engine
    return {"message": "Historical profile generation concept"}