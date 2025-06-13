import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')  # Default to empty string if not found

# File paths
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
MENU_DATASET_PATH = os.path.join(DATA_DIR, 'corrected_menu_dataset.csv')

# App settings
APP_TITLE = "Guli - Food Recommendations"
APP_ICON = "🍽️"

# Food types mapping
FOOD_TYPES = {
    "peene": "Beverage", "drink": "Beverage", "drinks": "Beverage", "beverage": "Beverage",
    "juice": "Beverage", "coffee": "Beverage", "tea": "Beverage", "milkshake": "Milkshake",
    "khane": "Main Course", "food": "Main Course", "dinner": "Main Course", "lunch": "Main Course",
    "meal": "Main Course", "biriyani": "Main Course", "curry": "Main Course",
    "snack": "Snack", "snacks": "Snack", "fast food": "Snack", "pakoda": "Snack",
    "fries": "Snack", "chips": "Snack", "starter": "Snack", "appetizer": "Snack",
    "meethe": "Dessert", "dessert": "Dessert", "sweet": "Dessert", "sweets": "Dessert",
    "cake": "Dessert", "pastry": "Dessert", "ice cream": "Dessert", "chocolate": "Dessert",
    "brownie": "Dessert", "halwa": "Dessert", "mexican": "Mexican", "indian": "Indian",
    "american": "American", "italian": "Italian", "chinese": "Chinese"
}

# Dietary options
DIETARY_OPTIONS = ["Vegan", "Vegetarian", "Gluten-Free", "Keto", "Nut-Free"]

# Stopwords
STOPWORDS = {"bhi", "hai", "kya", "ka", "i", "want"}

# Tax and discount settings
TAX_RATE = 0.05
MIN_WALLET_BALANCE = 100 