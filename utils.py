import json
import os
from datetime import datetime
import uuid
import logging # For potential logging if issues arise

# --- Configuration (can be moved to a config.py if it grows) ---
RATINGS_FILE_PATH = 'data/ratings.json'
SMART_CART_RULES_FILE_PATH = 'data/smart_cart_rules.json'
# Example for calculate_order_totals (if used)
# TAX_RATE_CONFIG = 0.05 # 5% tax rate

# --- Logging (optional, but good practice) ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)


# --- Core Utility Functions needed by main.py ---

def generate_order_id():
    """Generate a unique order ID (8 characters)."""
    return str(uuid.uuid4())[:8]


def load_json_file(file_path, default_data=None):
    """Helper function to load a JSON file."""
    if default_data is None:
        default_data = [] if 'ratings' in file_path else {} # Default for ratings is list, for rules is dict
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Try to open and load
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file not found or empty/corrupt, save default data and return it
        # print(f"File {file_path} not found or invalid. Creating with default data.")
        with open(file_path, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data


def save_json_file(file_path, data_to_save):
    """Helper function to save data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        return True
    except Exception as e:
        # print(f"Error saving to {file_path}: {e}")
        return False


def load_ratings():
    """Load all user ratings from the ratings JSON file."""
    return load_json_file(RATINGS_FILE_PATH, default_data=[])


def save_ratings(all_ratings_data):
    """Save all user ratings data to the ratings JSON file."""
    return save_json_file(RATINGS_FILE_PATH, all_ratings_data)


def add_or_update_rating(user_id, item_name, restaurant_name, rating_value):
    """Add a new rating or update an existing one for a specific user and item."""
    if not all([user_id, item_name, restaurant_name]): # Basic validation
        # print("Error: Missing user_id, item_name, or restaurant_name for rating.")
        return False
        
    current_ratings_list = load_ratings()
    rating_updated = False

    for rating_entry in current_ratings_list:
        if rating_entry.get('user_id') == user_id and \
           rating_entry.get('item_name') == item_name and \
           rating_entry.get('restaurant_name') == restaurant_name:
            # Update existing rating
            rating_entry['rating'] = rating_value
            rating_entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rating_updated = True
            break
    
    if not rating_updated:
        # Add new rating entry
        new_rating = {
            'user_id': user_id,
            'item_name': item_name,
            'restaurant_name': restaurant_name,
            'rating': rating_value,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        current_ratings_list.append(new_rating)
    
    return save_ratings(current_ratings_list)


def get_user_ratings(user_id_to_find):
    """Get all ratings for a specific user, returned as a dictionary for easy lookup."""
    all_ratings = load_ratings()
    user_specific_ratings_dict = {}
    for rating_entry in all_ratings:
        if rating_entry.get('user_id') == user_id_to_find:
            # Key for the dictionary: (item_name, restaurant_name) tuple
            item_restaurant_key = (rating_entry.get('item_name'), rating_entry.get('restaurant_name'))
            user_specific_ratings_dict[item_restaurant_key] = rating_entry.get('rating')
    return user_specific_ratings_dict


def load_smart_cart_rules():
    """Load smart cart suggestion rules from the JSON file."""
    default_rules = {
        "Biryani": ["Raita", "Coca-Cola (300ml)", "Gulab Jamun (2 pcs)"],
        "Pizza": ["Garlic Naan", "Pepsi (300ml)", "Chocolate Ice Cream (2 scoops)"], # Example update
        "Burger": ["French Fries", "Coca-Cola (300ml)"],
        "Paneer Butter Masala": ["Butter Naan", "Jeera Rice"]
    }
    return load_json_file(SMART_CART_RULES_FILE_PATH, default_data=default_rules)


# --- Optional/Advanced Utility Functions (not directly called by current main.py) ---

def get_current_formatted_timestamp():
    """Get current timestamp in a standard format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate_detailed_order_totals(order_items_list, tax_rate=0.05, global_discount_percentage=0):
    """
    Calculate detailed order totals including subtotal, tax, item discounts, and overall total.
    Assumes each item in order_items_list is a dictionary with 'Price', 'quantity', and optionally 'Discount' (item-specific discount percentage).
    """
    subtotal = 0
    total_item_discount_amount = 0

    for item in order_items_list:
        item_price = float(item.get('Price', 0))
        item_quantity = int(item.get('quantity', 1))
        item_total_price = item_price * item_quantity
        subtotal += item_total_price

        # Item-specific discount (percentage)
        item_discount_percent = float(item.get('Discount', 0)) # e.g., 10 for 10%
        if item_discount_percent > 0:
            total_item_discount_amount += item_total_price * (item_discount_percent / 100.0)

    # Subtotal after item discounts
    subtotal_after_item_discounts = subtotal - total_item_discount_amount

    # Global discount (e.g., promo code) applied on subtotal_after_item_discounts
    global_discount_amount = 0
    if global_discount_percentage > 0:
        global_discount_amount = subtotal_after_item_discounts * (global_discount_percentage / 100.0)
    
    price_before_tax = subtotal_after_item_discounts - global_discount_amount
    tax_amount = price_before_tax * tax_rate
    final_total_amount = price_before_tax + tax_amount

    return {
        "subtotal_gross": subtotal, # Sum of (price*qty) before any discounts
        "total_item_discount": total_item_discount_amount,
        "subtotal_net_after_item_discounts": subtotal_after_item_discounts,
        "global_order_discount": global_discount_amount,
        "amount_taxable": price_before_tax,
        "tax_amount": tax_amount,
        "final_total": final_total_amount
    }