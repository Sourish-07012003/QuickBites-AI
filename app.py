import streamlit as st
import pandas as pd
import os
# from config import * # No longer needed if OPENWEATHERMAP_API_KEY was the only thing
from utils import *  # For load_ratings, save_ratings, add_or_update_rating, get_user_ratings, load_smart_cart_rules
from nlp_utils import analyze_sentiment_text, semantic_search, extract_food_preferences # Ensure these functions are well-defined
import json
from datetime import datetime, timedelta
import uuid
# import geocoder # Not used in this version
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
import logging
import random
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- NLTK Downloads (run once) ---
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('sentiment/vader_lexicon.zip')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('taggers/averaged_perceptron_tagger')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('wordnet', quiet=True)

# --- Initialize NLP components ---
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))
# vectorizer = TfidfVectorizer(stop_words='english') # Defined in nlp_utils or used directly there

# --- Global variable for menu data (cached in session_state) ---
if 'menu_df' not in st.session_state:
    st.session_state.menu_df = None

def load_menu_data():
    """Load menu data from CSV file and cache it in session_state."""
    if st.session_state.menu_df is None:
        try:
            df = pd.read_csv('data/dummy_menu_dataset.csv')
            # Ensure essential columns exist
            required_cols = ['Item', 'Price', 'Category', 'Restaurant', 'Is_Vegetarian', 'Tags']
            for col in required_cols:
                if col not in df.columns:
                    st.error(f"Dataset missing essential column: '{col}'. Please add it to 'data/dummy_menu_dataset.csv'.")
                    # Add placeholder column if missing to prevent immediate crash, but functionality will be limited
                    if col == 'Tags':
                         df[col] = "" # Empty string for tags
                    elif col == 'Price':
                        df[col] = 0.0
                    else:
                        df[col] = "Unknown"
            st.session_state.menu_df = df
            return df
        except FileNotFoundError:
            st.error("Error: 'data/dummy_menu_dataset.csv' not found. Please create it.")
            st.session_state.menu_df = pd.DataFrame() # Empty DataFrame
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading menu data: {str(e)}")
            st.session_state.menu_df = pd.DataFrame() # Empty DataFrame
            return pd.DataFrame()
    return st.session_state.menu_df

def generate_order_id():
    """Generate a unique order ID"""
    return str(uuid.uuid4())[:8]

def generate_delivery_partner():
    """Generate a realistic delivery partner name"""
    first_names = ['Rahul', 'Amit', 'Suresh', 'Rajesh', 'Kumar', 'Vikram', 'Deepak', 'Sunil', 'Manoj', 'Prakash']
    last_names = ['Singh', 'Kumar', 'Sharma', 'Verma', 'Gupta', 'Yadav', 'Patel', 'Mishra', 'Chauhan', 'Reddy']
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_restaurant_info_for_order(): # Renamed to avoid conflict
    """Generate restaurant information FOR A PLACED ORDER (can be different from item's restaurant)"""
    restaurant_names = [
        "Kolkata Biryani House", "The Royal Platter", "Taste of Bengal", "Mughlai Dastarkhwan",
        "Quick Bites", "Dragon's Wok", "Chai & Chaat Corner", "Snack Attack", "Roll Raja", "Cafe Central"
    ]
    return random.choice(restaurant_names)

def calculate_delivery_time():
    """Calculate estimated delivery time (30-45 mins from now)"""
    current_time = datetime.now()
    delivery_time = current_time + timedelta(minutes=random.randint(30, 45))
    return delivery_time.strftime("%I:%M %p")

def display_cart_icon():
    """Display floating cart icon with item count"""
    cart_count = len(st.session_state.cart)
    st.markdown(
        f"""
        <div style="position: fixed; top: 20px; right: 20px; z-index: 1000;">
            <div style="background-color: #FF4B4B; color: white; padding: 10px 20px; border-radius: 20px; display: flex; align-items: center; gap: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
                <span style="font-size: 20px;">🛒</span>
                <span>{cart_count} items</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_cart():
    """Display cart contents in sidebar, including Smart Cart Suggestions"""
    st.markdown("### 🛒 Your Cart")

    if not st.session_state.cart:
        st.info("Your cart is empty.")
        return

    total = 0.0
    cart_item_details = [] # To store (name, restaurant) for smart cart check

    for item in st.session_state.cart:
        cart_item_details.append((item['Item'], item.get('Restaurant')))

    for idx, item in enumerate(st.session_state.cart):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{item['Item']}** ({item.get('Restaurant', 'N/A')})") # Show restaurant
            quantity = item.get('quantity', 1)
            price = float(item.get('Price', 0)) # Ensure price is float
            item_total = price * quantity
            st.write(f"₹{price:.2f} × {quantity} = ₹{item_total:.2f}")
        with col2:
            # More robust key for removal
            remove_key = f"remove_{item.get('Restaurant','')}_{item['Item']}_{idx}".replace(" ","_")
            if st.button("❌", key=remove_key):
                st.session_state.cart.pop(idx)
                st.rerun()
        total += item_total

    st.markdown("---")
    st.markdown(f"**Total: ₹{total:.2f}**")

    if st.button("Place Order", key="place_order_button_sidebar_main"):
        st.session_state.show_payment = True
        # Clear other views
        st.session_state.view_order_history = False
        st.session_state.show_order_details = False
        st.rerun()

    # --- Smart Cart Suggestions ---
    st.markdown("---")
    st.markdown("#### 🤔 You might also like:")
    smart_cart_rules = load_smart_cart_rules()
    menu_df = load_menu_data() # Already loaded, but get the DataFrame
    suggestions_made = 0

    if menu_df.empty:
        st.caption("Menu data not available for suggestions.")
        return

    # Create a set of items already in cart for quick lookup (Item Name, Restaurant Name)
    cart_item_identifiers = set((ci_name, ci_rest) for ci_name, ci_rest in cart_item_details)

    for cart_item_name_in_cart, _ in cart_item_details: # Iterate over items in cart
        if suggestions_made >= 3: break

        matched_rule_key = None
        # Fuzzy match against rule keys
        for rule_key in smart_cart_rules.keys():
            if fuzz.partial_ratio(cart_item_name_in_cart.lower(), rule_key.lower()) > 85:
                matched_rule_key = rule_key
                break
        
        if matched_rule_key:
            for suggested_item_name in smart_cart_rules[matched_rule_key]:
                if suggestions_made >= 3: break

                # Find the suggested item in the menu (any restaurant offering it)
                # Check if any variant of this suggested_item_name is already in cart
                is_suggested_item_name_in_cart_already = any(
                    s_item_name == suggested_item_name for s_item_name, _ in cart_item_identifiers
                )
                if is_suggested_item_name_in_cart_already:
                    continue

                # Find actual item from menu
                suggested_item_df_matches = menu_df[menu_df['Item'].str.contains(suggested_item_name, case=False, na=False)]
                if not suggested_item_df_matches.empty:
                    item_to_suggest = suggested_item_df_matches.iloc[0].to_dict() # Pick first match

                    # Final check: ensure this specific (Item, Restaurant) combo is not in cart
                    suggested_item_key_for_cart_check = (item_to_suggest['Item'], item_to_suggest.get('Restaurant'))
                    if suggested_item_key_for_cart_check not in cart_item_identifiers:
                        col_sugg_name, col_sugg_add = st.columns([3,1])
                        with col_sugg_name:
                            sugg_price = float(item_to_suggest.get('Price', 0))
                            st.write(f"<small>{item_to_suggest['Item']} (₹{sugg_price:.2f})</small>", unsafe_allow_html=True)
                        with col_sugg_add:
                            smart_add_key = f"smart_add_{item_to_suggest.get('Restaurant','')}_{item_to_suggest['Item']}_{suggestions_made}".replace(" ","_")
                            if st.button("➕ Add", key=smart_add_key):
                                item_copy = item_to_suggest.copy()
                                item_copy['quantity'] = 1
                                st.session_state.cart.append(item_copy)
                                st.rerun()
                        suggestions_made += 1
    if suggestions_made == 0 and st.session_state.cart: # Only show if cart not empty
        st.caption("No specific suggestions right now.")


# This function should be part of your main app.py script

def display_payment_options(total):
    """Display payment options and handle payment processing, including adding money to wallet."""

    # Ensure necessary session state variables for the form are initialized
    if 'card_errors' not in st.session_state:
        st.session_state.card_errors = []
    if 'show_card_form' not in st.session_state:
        st.session_state.show_card_form = False # Controls visibility of card form
    if 'amount_to_add_input' not in st.session_state: # To store the input value
        st.session_state.amount_to_add_input = 0.0
    if 'card_data' not in st.session_state:
        st.session_state.card_data = {
            'card_number': '',
            'expiry': '',
            'cvv': '',
            'card_name': ''
        }

    st.markdown("### 💳 Select Payment Method")

    payment_method = st.radio(
        "Choose how you want to pay:",
        ["Cash on Delivery", "Wallet Payment"],
        key="payment_method_radio_main_display" # Unique key
    )

    if payment_method == "Wallet Payment":
        st.markdown(f"**Current Wallet Balance:** ₹{st.session_state.wallet_balance:.2f}")
        st.markdown(f"**Order Total:** ₹{total:.2f}")

        if st.session_state.wallet_balance < total:
            deficit = total - st.session_state.wallet_balance
            st.warning(f"⚠️ Insufficient wallet balance! You need ₹{deficit:.2f} more.")

            st.markdown("---")
            st.markdown("### 💰 Add Money to Wallet")
            
            # Use a number input that persists its value via session_state for amount_to_add
            # Initialize if not present or reset if form was successful
            if not st.session_state.show_card_form: # Reset if card form not shown (e.g. after successful add)
                 st.session_state.amount_to_add_input = deficit


            amount_to_add = st.number_input(
                "Enter amount to add:",
                min_value=float(deficit), # Ensure float for min_value
                value=float(st.session_state.amount_to_add_input), # Ensure float for value
                step=50.0,
                key="amount_to_add_wallet_input"
            )
            st.session_state.amount_to_add_input = amount_to_add # Store current input

            if st.button("Proceed to Add Money", key="proceed_add_money_button"):
                st.session_state.show_card_form = True
                st.session_state.card_errors = [] # Clear previous errors when showing form
                st.rerun() # Rerun to show the card form

            if st.session_state.show_card_form:
                st.markdown("#### 💳 Enter Card Details to Add Money")
                
                # Secure payment visual cue
                st.markdown("""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                    <p style='color: #1f77b4; font-weight: bold;'>🔒 Secure Payment Simulation</p>
                    <p style='font-size: 0.9em;'>Your card details are for simulation purposes and are not stored.</p>
                </div>
                """, unsafe_allow_html=True)

                # Display validation errors if any
                if st.session_state.card_errors:
                    error_html = "<div style='background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 10px; margin: 10px 0;'><p style='font-weight: bold;'>⚠️ Please correct the following errors:</p><ul>"
                    for error in st.session_state.card_errors:
                        error_html += f"<li>{error}</li>"
                    error_html += "</ul></div>"
                    st.markdown(error_html, unsafe_allow_html=True)

                # Card details form
                # Persist input values using st.session_state.card_data
                card_number = st.text_input("Card Number",
                                          value=st.session_state.card_data['card_number'],
                                          placeholder="1234 5678 9012 3456",
                                          max_chars=19, key="card_num_input")
                st.session_state.card_data['card_number'] = card_number

                col1_expiry, col2_cvv = st.columns(2)
                with col1_expiry:
                    expiry = st.text_input("Expiry (MM/YY)",
                                         value=st.session_state.card_data['expiry'],
                                         placeholder="MM/YY",
                                         max_chars=5, key="card_expiry_input")
                    st.session_state.card_data['expiry'] = expiry
                with col2_cvv:
                    cvv = st.text_input("CVV",
                                      value=st.session_state.card_data['cvv'],
                                      placeholder="123",
                                      max_chars=3, type="password", key="card_cvv_input")
                    st.session_state.card_data['cvv'] = cvv
                
                card_name = st.text_input("Name on Card",
                                        value=st.session_state.card_data['card_name'],
                                        placeholder="John Doe", key="card_name_input")
                st.session_state.card_data['card_name'] = card_name

                if st.button(f"Pay ₹{amount_to_add:.2f} to Wallet", key="pay_add_to_wallet_button"):
                    st.session_state.card_errors = [] # Clear previous errors

                    # --- Card Validation Logic (same as your original) ---
                    # Card Number
                    if not card_number: st.session_state.card_errors.append("Card number is required")
                    elif not card_number.replace(" ", "").isdigit(): st.session_state.card_errors.append("Card number must contain only digits")
                    elif len(card_number.replace(" ", "")) != 16: st.session_state.card_errors.append("Card number must be 16 digits")
                    # Expiry
                    if not expiry: st.session_state.card_errors.append("Expiry date is required")
                    elif not expiry.replace("/", "").isdigit() or len(expiry.replace("/", "")) != 4:
                        st.session_state.card_errors.append("Expiry date must be 4 digits in MM/YY format")
                    else:
                        try:
                            month, year_short = expiry.split("/")
                            month = int(month)
                            year = int(f"20{year_short}") # Assuming 21st century
                            current_year_short = int(datetime.now().strftime("%y"))
                            current_month = datetime.now().month
                            if not (1 <= month <= 12): st.session_state.card_errors.append("Invalid month in expiry date")
                            elif int(year_short) < current_year_short or (int(year_short) == current_year_short and month < current_month):
                                st.session_state.card_errors.append("Card has expired")
                        except ValueError: st.session_state.card_errors.append("Invalid expiry date format. Use MM/YY.")
                    # CVV
                    if not cvv: st.session_state.card_errors.append("CVV is required")
                    elif not cvv.isdigit() or len(cvv) != 3: st.session_state.card_errors.append("CVV must be 3 digits")
                    # Name
                    if not card_name: st.session_state.card_errors.append("Name on card is required")
                    elif len(card_name.split()) < 2: st.session_state.card_errors.append("Please enter your full name")
                    # --- End of Card Validation ---

                    if not st.session_state.card_errors:
                        # Simulate successful payment
                        st.session_state.wallet_balance += amount_to_add
                        st.success(f"✅ ₹{amount_to_add:.2f} successfully added to your wallet!")
                        st.balloons()
                        
                        # Reset card form state and data
                        st.session_state.show_card_form = False
                        st.session_state.card_data = {'card_number': '', 'expiry': '', 'cvv': '', 'card_name': ''}
                        st.session_state.amount_to_add_input = 0.0 # Reset amount to add too
                        st.rerun() # Rerun to reflect updated balance and hide form
                    else:
                        st.rerun() # Rerun to display errors

        elif st.session_state.wallet_balance >= total: # Sufficient balance
            if st.button("Pay with Wallet", key="pay_with_wallet_sufficient_button"):
                st.session_state.wallet_balance -= total
                process_order(total, "Wallet") # Ensure process_order exists and works
        else: # Should not happen if logic is correct, but a fallback
            st.error("An unexpected error occurred with wallet balance calculation.")


    else:  # Cash on Delivery
        if st.button("Confirm Cash on Delivery", key="confirm_cod_button_main"):
            process_order(total, "Cash on Delivery") # Ensure process_order exists and works
            
def process_order(total, payment_method):
    """Process the order and create order details"""
    order_id = generate_order_id()
    delivery_partner = generate_delivery_partner()
    delivery_phone = f"{random.choice(['9', '8', '7', '6'])}{random.randint(100000000, 999999999)}"
    # The 'restaurant' for the order summary can be a general one,
    # as an order might contain items from multiple if your logic allowed that.
    # For simplicity, let's pick one from the cart or a default.
    order_restaurant = st.session_state.cart[0].get('Restaurant') if st.session_state.cart else generate_restaurant_info_for_order()

    estimated_delivery = calculate_delivery_time()

    order = {
        'order_id': order_id,
        'items': st.session_state.cart.copy(), # Critical: copy the cart
        'total': total,
        'delivery_partner': delivery_partner,
        'delivery_phone': delivery_phone,
        'payment_method': payment_method,
        'restaurant': order_restaurant, # Restaurant for the overall order
        'order_time': datetime.now().strftime("%I:%M %p"),
        'estimated_delivery': estimated_delivery,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    st.session_state.order_history.append(order)
    st.session_state.cart = [] # Clear the cart
    st.session_state.show_payment = False
    st.session_state.show_order_details = True
    st.session_state.current_order = order
    st.rerun()


def display_order_details():
    """Display order details after successful placement"""
    if not st.session_state.current_order:
        st.warning("No current order to display.")
        st.session_state.show_order_details = False # Reset flag
        st.rerun()
        return

    order = st.session_state.current_order
    st.success("🎉 Order placed successfully!")

    st.markdown(f"""
    <div style='background-color: #e6f3ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #b3d9ff;'>
        <h3 style='color: #0056b3;'>Order Status</h3>
        <p>🕒 Order placed at: {order['order_time']}</p>
        <p>⏰ Estimated delivery: {order['estimated_delivery']}</p>
        <p>🏪 Restaurant (Processing From): {order.get('restaurant', 'Central Kitchen')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Order Details")
    st.markdown(f"**Order ID:** {order['order_id']}")
    st.markdown(f"**Total Amount:** ₹{order['total']:.2f}")
    st.markdown(f"**Payment Method:** {order['payment_method']}")

    st.markdown("### 🚚 Delivery Information")
    st.markdown(f"**Delivery Partner:** {order['delivery_partner']}")
    st.markdown(f"**Contact:** {order['delivery_phone']}")

    st.markdown("### 🍽️ Ordered Items")
    for item in order['items']:
        item_price = float(item.get('Price',0))
        item_qty = item.get('quantity',1)
        st.markdown(f"- {item['Item']} ({item.get('Restaurant', 'N/A')}) - {item_qty} x ₹{item_price:.2f}") # Show restaurant for each item

    if st.button("Back to Menu", key="back_to_menu_from_order_details"):
        st.session_state.show_order_details = False
        st.session_state.current_order = None
        st.rerun()

def display_swipe_card(item_dict, index_key_suffix):
    """Display a food item card with quantity controls. item_dict is a dictionary."""
    if not isinstance(item_dict, dict):
        st.error(f"Invalid item format: {item_dict}")
        return

    item_name = item_dict.get('Item', 'Unknown Item')
    item_restaurant = item_dict.get('Restaurant', 'Unknown Restaurant')
    item_description = item_dict.get('Description', '')
    item_price = float(item_dict.get('Price', 0.0))
    item_discount = item_dict.get('Discount')

    item_identifier_key = f"{item_restaurant.replace(' ','_')}_{item_name.replace(' ','_')}_{index_key_suffix}"

    with st.container(border=True):
        st.markdown(f"#### {item_name}")
        st.caption(f"From: {item_restaurant}")
        if item_description and isinstance(item_description, str):
            st.markdown(f"<small>*{item_description}*</small>", unsafe_allow_html=True)

        # Main columns for price and controls
        col_price_info, col_cart_controls = st.columns([0.6, 0.4]) # Adjust ratio as needed: 60% for price, 40% for controls

        with col_price_info:
            st.markdown(f"**Price:** ₹{item_price:.2f}")
            if item_discount and float(item_discount) > 0:
                st.markdown(f"**Discount:** {item_discount}%")

        with col_cart_controls: # This is now our primary column for all cart actions
            if 'cart' not in st.session_state: st.session_state.cart = []

            cart_item_index = -1
            found_cart_item = None
            for idx, cart_item_loop in enumerate(st.session_state.cart):
                if cart_item_loop['Item'] == item_name and cart_item_loop.get('Restaurant') == item_restaurant:
                    cart_item_index = idx
                    found_cart_item = cart_item_loop
                    break

            if cart_item_index == -1: # Item not in cart
                if st.button("Add to Cart", key=f"add_{item_identifier_key}", type="primary", use_container_width=True):
                    item_copy = item_dict.copy()
                    item_copy['quantity'] = 1
                    st.session_state.cart.append(item_copy)
                    st.rerun()
            else: # Item is in cart, show quantity controls
                # --- MODIFIED PART: Use st.columns HERE for the +/- buttons and quantity display ---
                # This is the first level of nesting within col_cart_controls, which is allowed.
                # We removed the col1_price, col2_controls structure that was causing the double nesting.
                # Now, the structure is:
                # main_page_columns (rec_cols)
                #  -> col_cart_controls (within display_swipe_card)
                #     -> (button_minus, qty_display, button_plus) using st.columns - THIS IS FINE.

                # The issue was likely:
                # main_page_columns (rec_cols)
                #  -> one_of_rec_cols (e.g. rec_cols[0])
                #     -> col1_price, col2_controls (from display_swipe_card's first st.columns)
                #        -> col2_controls (which IS a column)
                #           -> col_minus, col_qty, col_plus (SECOND st.columns INSIDE a column) - THIS WAS THE PROBLEM.

                # Let's re-evaluate the structure. The original structure was:
                # rec_cols[i % num_cols_rec] (This is a column)
                #   WITHIN THIS: display_swipe_card is called.
                #   display_swipe_card:
                #     st.container(border=True)
                #       col1_price, col2_controls = st.columns([2, 1.5]) # First level of columns *inside the container*, NOT directly inside rec_cols[i]
                #       with col2_controls: # This is a column from the above line
                #         col_minus, col_qty, col_plus = st.columns([1, 1, 1]) # This is nested.

                # The key is that `with col2_controls:` makes the current context a column.
                # So, `st.columns` inside it is a nested column.

                # --- Corrected approach for quantity controls ---
                # We are ALREADY inside `col_cart_controls`. We can lay out elements horizontally
                # using Streamlit's natural flow or with a bit of HTML for precise control if needed.
                # For simplicity, let's use three separate elements that will flow.
                # If `col_cart_controls` is narrow, they might stack. If wider, they might go side-by-side.
                # To force side-by-side, we might need a sub-column here IF col_cart_controls itself wasn't already a column
                # generated from the main page.

                # The error occurs because the `with rec_cols[i % num_cols_rec]:` in main()
                # establishes a column context. Then `display_swipe_card` is called.
                # Inside `display_swipe_card`, `col1_price, col2_controls = st.columns(...)`
                # is the *first level of nesting*.
                # Then, `with col2_controls:` you are inside one of *those* columns.
                # So, `st.columns([1,1,1])` inside `col2_controls` is the *second level of nesting*.

                # Let's simplify `display_swipe_card` to have only ONE `st.columns` call AT ITS TOP LEVEL.
                # All subsequent layout will happen within those top-level columns.

                # Simplification: Assume col_cart_controls is where all controls go.
                # We can't use st.columns again directly here for the +/-/qty.
                # We can use st.button and st.markdown in sequence. They will flow based on col_cart_controls width.
                # To get them on one line if space allows, we can try putting them in a container
                # or just let them flow.

                # Let's try placing them sequentially inside col_cart_controls.
                # If you need them strictly horizontal and compact, this might not be perfect.
                
                # --- Attempt 1: Sequential elements in col_cart_controls ---
                # This will likely stack them vertically if col_cart_controls is narrow.

                # --- Attempt 2: Use a sub-column structure if absolutely needed,
                # but this requires the parent (col_cart_controls) to NOT be a column itself,
                # or for this to be the *only* level of column nesting from its parent.

                # The core issue:
                # main.py: `rec_cols = st.columns(num_cols_rec)`
                # `with rec_cols[i % num_cols_rec]:` (CONTEXT A = COLUMN)
                #    `display_swipe_card(...)`
                #       `display_swipe_card`: `col1, col2 = st.columns(...)` (CONTEXT B = COLUMN, NESTED IN A)
                #          `with col2:` (CONTEXT C = STILL WITHIN COLUMN B)
                #             `st.columns(...)` (TRYING TO NEST COLUMNS AGAIN WITHIN C - ERROR)

                #Revised display_swipe_card to avoid the double nesting of st.columns
                #We will have one st.columns call at the top of the card for price and controls.
                #The quantity controls will be laid out within the 'controls' column without a further st.columns call.

                # If we want the +/- buttons and quantity to be horizontal *within* col_cart_controls,
                # we must ensure col_cart_controls itself isn't already a column that's nested.
                #
                # The structure in main.py:
                # `rec_cols = st.columns(num_cols_rec)`
                # `with rec_cols[i % num_cols_rec]:` -> This makes the current DeltaGenerator a column.
                #    `display_swipe_card(...)` is called.
                #
                # Inside `display_swipe_card(item_dict, index_key_suffix)`:
                # `with st.container(border=True):` -> Good, containers don't count as column nesting level for st.columns
                #    `col_price_info, col_cart_controls = st.columns([0.6, 0.4])` -> This is fine, 1st level of columns INSIDE the container.
                #    `with col_cart_controls:` -> Now we are inside a column.
                #       `if cart_item_index == -1: ... else: ...`
                #          IF WE DO `st.columns` here for +/-/qty, IT'S A NESTED COLUMN.
                #
                # Solution: Place buttons and text for quantity sequentially in `col_cart_controls`
                # or use HTML/Markdown for layout if precise horizontal alignment is critical.

                # Let's use a more manual horizontal layout with st.columns, but carefully.
                # The problem is that the `col_cart_controls` is ALREADY a column.
                # The simplest way to get horizontal layout for a few small elements is often
                # to use multiple `st.button` calls within a single, wider column, and they will
                # try to fit side-by-side if space allows, or wrap.
                # For explicit control, we can use Markdown with HTML, but let's try to avoid that.

                # If we want the "Add to Cart" button OR the "+/-/qty" controls:
                # `col_cart_controls` is the column where these should live.

                # Let's make the quantity controls directly within `col_cart_controls`
                # We can have one row for the buttons, and the quantity above/below or let them flow.

                # Alternative structure for quantity controls inside `col_cart_controls`
                # This places them sequentially. They will flow based on the width of `col_cart_controls`.
                # If col_cart_controls is wide enough, they might appear somewhat horizontal.
                
                # To make them appear more like a single control unit:
                # We can use st.columns for the +/- buttons and quantity display *if*
                # the PARENT of these columns (i.e., the context where we call st.columns for them)
                # is NOT itself a column that has already been nested.
                #
                # The issue is that `rec_cols[i % num_cols_rec]` IS A COLUMN.
                # And then `col_cart_controls` IS A COLUMN NESTED INSIDE IT.
                # So, we cannot use `st.columns` again for the quantity controls inside `col_cart_controls`.

                # **Revised Logic for Quantity Controls (No further `st.columns`)**
                # We are inside `col_cart_controls`. Let's lay out elements.
                # This might not look perfectly like [ - QTY + ] horizontally if col_cart_controls is too narrow.
                
                # One approach: use a sub-container if that helps Streamlit's layout engine,
                # but containers don't directly solve the column nesting.

                # The most robust way if you need fine-grained horizontal layout for the quantity
                # controls *inside* an already nested column (`col_cart_controls`) is often
                # to use `st.markdown` with custom HTML and CSS (e.g., using flexbox).
                #
                # However, let's try a simpler approach first by just placing them.
                # Streamlit's layout might be good enough.

                # Let's try placing button, then quantity, then button.
                # This will likely stack them if col_cart_controls is narrow.
                # For a horizontal layout, they ideally need to be in their own columns,
                # but that's what's causing the error.

                # --- Final Attempt at a clean structure for quantity controls ---
                # We are inside `col_cart_controls`.
                # Let's try to use HTML for the quantity controls to ensure they are on one line.
                
                # Build HTML for the quantity controls
                button_style = "padding: 0.25rem 0.5rem; margin: 0 2px; border-radius: 5px; border: 1px solid #ccc; background-color: #f0f0f0; cursor: pointer;"
                qty_style = "padding: 0.25rem 0.5rem; font-weight: bold; margin: 0 5px;"

                # We need to trigger Streamlit buttons for the actions.
                # So, we still need st.button. HTML is only for visual grouping if st.columns fails.

                # The error is quite specific. `st.columns` cannot be nested that deep.
                # The problem is that `rec_cols[i % num_cols_rec]` is a column.
                # `col_cart_controls` is a column *within* that.
                # Calling `st.columns` again for `col_minus, col_qty, col_plus` is the forbidden second level of nesting.

                # **Corrected structure for display_swipe_card:**
                # The `st.columns` for `col_price_info` and `col_cart_controls` is the *only* `st.columns` call
                # directly within the `st.container` of the card.
                # The quantity controls (+/-/qty) must be laid out *within* `col_cart_controls`
                # *without* using another `st.columns` call.

                # Simple sequential layout within col_cart_controls:
                if st.button("➖", key=f"minus_{item_identifier_key}"):
                    if found_cart_item['quantity'] > 1:
                        found_cart_item['quantity'] -= 1
                    else:
                        st.session_state.cart.pop(cart_item_index)
                    st.rerun()

                # Display quantity next to the minus button
                # Use st.markdown for better control over display if needed, or just st.write
                st.markdown(f"<div style='display: inline-block; padding: 0.3rem 0.5rem; text-align: center; font-weight: bold;'>{found_cart_item['quantity']}</div>", unsafe_allow_html=True)
                # st.write(f"{found_cart_item['quantity']}") # Simpler alternative

                if st.button("➕", key=f"plus_{item_identifier_key}"):
                    found_cart_item['quantity'] += 1
                    st.rerun()
                
                # This sequential layout might not be perfectly horizontal.
                # If col_cart_controls is narrow, they will stack.
                # If you absolutely need them horizontal in a compact way,
                # you'd typically use st.columns for them, but that's what's failing.
                # The alternative is custom HTML/CSS with st.markdown.
def display_order_history():
    st.markdown("## 📜 Your Order History")
    if not st.session_state.order_history:
        st.info("You have no past orders yet.")
        return

    user_ratings = get_user_ratings(st.session_state.user_id) # Load user's ratings

    for i, order in enumerate(reversed(st.session_state.order_history)): # Show newest first
        order_total = float(order.get('total', 0))
        expander_title = f"Order ID: {order['order_id']} - {order['timestamp']} - ₹{order_total:.2f}"
        with st.expander(expander_title):
            st.markdown(f"**Restaurant (Processed by):** {order.get('restaurant', 'N/A')}")
            st.markdown(f"**Items:**")
            for item_in_order in order['items']:
                item_name = item_in_order['Item']
                # Restaurant for this item (important for rating uniqueness)
                item_restaurant = item_in_order.get('Restaurant', order.get('restaurant', 'Unknown Restaurant'))
                item_key_for_rating = (item_name, item_restaurant) # Composite key for rating
                item_price_ordered = float(item_in_order.get('Price',0))
                item_qty_ordered = item_in_order.get('quantity',1)

                st.markdown(f"- {item_name} ({item_restaurant}) - {item_qty_ordered} x ₹{item_price_ordered:.2f}")

                # Rating Section
                st.write(f"Rate '{item_name}' from '{item_restaurant}':")
                current_rating_for_item = user_ratings.get(item_key_for_rating)
                rating_options = [1, 2, 3, 4, 5]
                cols_rating = st.columns(len(rating_options) + 1) # +1 for clear button

                for r_idx, r_val in enumerate(rating_options):
                    with cols_rating[r_idx]:
                        button_char = "⭐" if current_rating_for_item and r_val <= current_rating_for_item else "☆"
                        rate_key = f"rate_{order['order_id']}_{item_restaurant}_{item_name}_{r_val}_{i}".replace(" ","_")
                        if st.button(button_char, key=rate_key):
                            add_or_update_rating(st.session_state.user_id, item_name, item_restaurant, r_val)
                            st.success(f"You rated '{item_name}' ({item_restaurant}) {r_val} stars!")
                            st.rerun()
                if current_rating_for_item: # Show clear button only if rated
                    with cols_rating[len(rating_options)]:
                        clear_key = f"clear_rate_{order['order_id']}_{item_restaurant}_{item_name}_{i}".replace(" ","_")
                        if st.button("Clear", key=clear_key):
                            add_or_update_rating(st.session_state.user_id, item_name, item_restaurant, 0) # 0 or None to clear
                            st.info(f"Rating for '{item_name}' ({item_restaurant}) cleared.")
                            st.rerun()
            st.markdown("---")


def get_recommendations(category=None, dietary_preferences=None, limit=10, user_query=None,
                        occasion=None, mood=None, current_weather_input=None):
    df = load_menu_data()
    if df.empty:
        return []

    results_df = df.copy()
    results_df['recommendation_score'] = 0.0 # Initialize score

    # 0. User Ratings Boost
    if 'user_id' in st.session_state:
        user_ratings = get_user_ratings(st.session_state.user_id)
        if user_ratings:
            def rating_boost(row):
                item_key = (row['Item'], row.get('Restaurant'))
                rating = user_ratings.get(item_key, 0) # Default to 0 if not rated
                if rating >= 4: return rating * 2.0
                if rating == 3: return rating * 0.5
                return 0.0
            results_df['recommendation_score'] += results_df.apply(rating_boost, axis=1)

    # 1. Dietary Preferences
    if dietary_preferences: # dietary_preferences is a list e.g. ['vegetarian']
        if 'vegetarian' in dietary_preferences:
            results_df = results_df[results_df['Is_Vegetarian'].str.lower() == 'veg']
        elif 'non-vegetarian' in dietary_preferences:
            results_df = results_df[results_df['Is_Vegetarian'].str.lower() == 'non-veg']
        # If empty (i.e., 'any'), no filter applied here.

    # 2. Category Filter
    if category and category != 'All':
        results_df = results_df[results_df['Category'] == category]

    # Ensure 'Tags' column is string type for safe operations
    if 'Tags' in results_df.columns:
        results_df['Tags'] = results_df['Tags'].astype(str)

    # 3. Occasion-Based Boosting
    if occasion and occasion != "Any Occasion" and 'Tags' in results_df.columns:
        occasion_tags_map = {
            "Quick Lunch": ["quick_lunch", "snack", "light_meal", "roll", "fast_food"],
            "Family Dinner": ["family_meal", "main_course", "shareable", "combo", "biryani", "curry"],
            "Party": ["party_pack", "bulk", "snack_platter", "pizza", "finger_food", "appetizer"],
            "Healthy Meal": ["healthy", "salad", "low_calorie", "grilled", "soup", "steamed", "fruit"]
        }
        if occasion in occasion_tags_map:
            for tag in occasion_tags_map[occasion]:
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 5 if tag in x.lower() else 0)

    # 4. Mood-Based Boosting
    if mood and mood != "Any Mood" and 'Tags' in results_df.columns:
        mood_tags_map = {
            "Happy": ["dessert", "celebration", "treat", "sweet", "ice_cream", "cake", "chocolate"],
            "Stressed": ["comfort_food", "chocolate", "sweet", "rich", "creamy", "pasta", "pizza"],
            "Cozy": ["soup", "warm", "tea", "coffee", "comfort_food", "hot_drink", "stew", "pasta"],
            "Adventurous": ["exotic", "new_flavor", "spicy_high", "unique", "fusion", "sushi", "thai"] # Assuming some tags
        }
        if mood in mood_tags_map:
            for tag in mood_tags_map[mood]:
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 3 if tag in x.lower() else 0)

    # 5. Weather-Based Boosting (User Input)
    if current_weather_input and 'Tags' in results_df.columns:
        temp = current_weather_input.get('temperature') # Float
        condition = current_weather_input.get('condition', '').lower() # String

        if temp is not None:
            if temp > 28: # Hot
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 4 if any(t in x.lower() for t in ["cold", "refreshing", "juice", "lassi", "ice_cream", "salad"]) else 0)
            elif temp < 15: # Cold
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 4 if any(t in x.lower() for t in ["hot", "warm", "soup", "tea", "coffee", "hearty", "stew", "spicy"]) else 0)

        if condition:
            if condition == 'rainy':
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 5 if any(t in x.lower() for t in ["hot", "soup", "comfort_food", "pakora", "chai", "fried", "warm"]) else 0)
            elif condition == 'sunny' and (temp is None or temp > 20):
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 3 if any(t in x.lower() for t in ["refreshing", "light_meal", "salad", "juice", "fruit", "cold_drink", "ice_cream"]) else 0)
            elif condition == 'cloudy':
                results_df['recommendation_score'] += results_df['Tags'].apply(lambda x: 1 if "comfort_food" in x.lower() else 0)

    # 6. User Query (Semantic Search) - Needs robust integration
    if user_query:
        # semantic_search should return a DataFrame with original columns + 'semantic_score' or similar
        # Or it returns a list of items with scores.
        # For this example, assume it returns a DataFrame of the same structure but re-ordered or with a score.
        # This is a critical part that depends on your nlp_utils.semantic_search implementation.
        
        # Option A: Semantic search filters and returns a new DataFrame
        # query_filtered_df = semantic_search(user_query, results_df.copy(), top_n=len(results_df)) # or a smaller top_n
        # if not query_filtered_df.empty:
        #     results_df = query_filtered_df # Overwrite results_df if semantic search is the primary filter

        # Option B: Semantic search adds a score to existing items
        # For example, if semantic_search can add a 'semantic_score' column to results_df:
        # results_df = semantic_search(user_query, results_df, add_score_column='semantic_score')
        # results_df['recommendation_score'] += results_df.get('semantic_score', 0) * 10 # High weight
        
        # Placeholder: Assuming semantic_search returns a list of item names that match
        # This is a simplified integration.
        try:
            matched_items_df_from_query = semantic_search(user_query, results_df.copy(), top_n=20) # semantic_search returns df
            if not matched_items_df_from_query.empty:
                # Give a high score boost to items found by semantic search
                # We need to merge this boost back to the main results_df
                # Create a dictionary of boosts: {(Item, Restaurant): boost_value}
                query_boosts = {}
                for _, row in matched_items_df_from_query.iterrows():
                    # Assuming semantic_search might provide its own score, or we assign a flat boost
                    boost_val = row.get('semantic_score', 20) # Use semantic_score if available, else 20
                    query_boosts[(row['Item'], row.get('Restaurant'))] = boost_val
                
                def apply_query_boost(row):
                    return query_boosts.get((row['Item'], row.get('Restaurant')), 0)

                results_df['recommendation_score'] += results_df.apply(apply_query_boost, axis=1)

        except Exception as e:
            # st.warning(f"Semantic search integration issue: {e}") # For debugging
            pass # Continue without semantic search if it fails


    # Sort by final recommendation score, then by original Rating (if available)
    sort_by_cols = ['recommendation_score']
    ascending_order = [False]
    if 'Rating' in results_df.columns: # Assuming 'Rating' is numerical
        results_df['Rating'] = pd.to_numeric(results_df['Rating'], errors='coerce').fillna(0)
        sort_by_cols.append('Rating')
        ascending_order.append(False)

    results_df = results_df.sort_values(by=sort_by_cols, ascending=ascending_order)
    
    # Remove duplicates keeping the one with highest recommendation_score
    # Considering 'Item' and 'Restaurant' as unique identifier for a dish
    results_df = results_df.drop_duplicates(subset=['Item', 'Restaurant'], keep='first')

    return results_df.head(limit).to_dict('records')


# --- Main Application ---
def main():
    st.set_page_config(page_title="QuickBites AI", layout="wide", initial_sidebar_state="expanded")

    # --- Initialize session state variables (Robustly) ---
    default_session_state = {
        'menu_df': None, 'cart': [], 'order_history': [], 'wallet_balance': 1000.0,
        'user_id': generate_order_id(), 'dietary_preferences': [], # Empty list for 'any'
        'show_payment': False, 'show_order_details': False, 'current_order': None,
        'show_recommendations': False, 'current_recommendations': [],
        'user_query': "", 'selected_category': 'All',
        'selected_occasion': "Any Occasion", 'selected_mood': "Any Mood",
        'view_order_history': False,
        'user_weather_input': {'condition': 'Clear', 'temperature': 25.0},
        'card_errors': [], 'show_card_form': False, # For payment form
        'card_data': {'card_number': '', 'expiry': '', 'cvv': '', 'card_name': ''} # For payment form
    }
    for key, value in default_session_state.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Ensure user_id is persistent for the session
    if 'user_id' not in st.session_state or not st.session_state.user_id:
        st.session_state.user_id = generate_order_id()


    # --- Load menu data once at the start ---
    load_menu_data()

    st.title("🍽️ QuickBites AI")
    st.markdown("### Your Personalized Food Discovery Engine!")
    display_cart_icon() # Floating cart icon

    # --- Sidebar ---
    with st.sidebar:
        st.header("👤 User Preferences")
        dietary_pref_options = ["any", "vegetarian", "non-vegetarian"]
        current_diet_pref = st.session_state.dietary_preferences[0] if st.session_state.dietary_preferences else "any"
        selected_diet_pref_val = st.radio(
            "Dietary preference:", dietary_pref_options,
            index=dietary_pref_options.index(current_diet_pref),
            key="dietary_radio_sidebar"
        )
        st.session_state.dietary_preferences = [] if selected_diet_pref_val == "any" else [selected_diet_pref_val]

        st.markdown("---")
        st.header("🎉 Occasion & Mood")
        occasions = ["Any Occasion", "Quick Lunch", "Family Dinner", "Party", "Healthy Meal"]
        st.session_state.selected_occasion = st.selectbox("What's the occasion?", occasions,
            index=occasions.index(st.session_state.selected_occasion), key="occasion_select_sidebar")

        moods = ["Any Mood", "Happy", "Stressed", "Cozy", "Adventurous"]
        st.session_state.selected_mood = st.selectbox("How are you feeling?", moods,
            index=moods.index(st.session_state.selected_mood), key="mood_select_sidebar")

        st.markdown("---")
        st.header("☀️ Current Weather")
        weather_conditions_options = ["Clear", "Sunny", "Cloudy", "Rainy", "Windy", "Snowy", "Foggy"]
        user_weather_cond_val = st.session_state.user_weather_input.get('condition', 'Clear')
        user_weather_temp_val = float(st.session_state.user_weather_input.get('temperature', 25.0))

        selected_weather_condition = st.selectbox("Condition:", weather_conditions_options,
            index=weather_conditions_options.index(user_weather_cond_val if user_weather_cond_val in weather_conditions_options else 'Clear'),
            key="weather_condition_sidebar")
        selected_weather_temp = st.number_input("Temperature (°C):", value=user_weather_temp_val, step=1.0, key="weather_temp_sidebar")
        st.session_state.user_weather_input = {'condition': selected_weather_condition, 'temperature': selected_weather_temp}

        st.markdown("---")
        if st.button("📜 View Order History", key="view_history_btn_main_sidebar", use_container_width=True):
            st.session_state.view_order_history = True
            st.session_state.show_payment = False
            st.session_state.show_order_details = False
            st.rerun()

        st.markdown("---")
        st.markdown(f"### 💰 Wallet: ₹{st.session_state.wallet_balance:.2f}")
        display_cart() # Cart display and smart suggestions

    # --- Main Page Content Routing ---
    if st.session_state.view_order_history:
        display_order_history()
        if st.button("Back to Menu", key="back_to_menu_from_history_main_page", use_container_width=True):
            st.session_state.view_order_history = False
            st.rerun()
    elif st.session_state.show_order_details:
        display_order_details() # Contains its own "Back to Menu" button
    elif st.session_state.show_payment:
        current_total = sum(float(item.get('Price',0)) * item.get('quantity', 1) for item in st.session_state.cart)
        display_payment_options(current_total) # Ensure this function exists and is robust
    else: # Main browsing and recommendation view
        st.markdown("### 🔍 What are you craving?")
        st.session_state.user_query = st.text_input(
            "Describe what you're looking for (e.g., 'spicy chicken for dinner')...",
            value=st.session_state.user_query,
            key="user_query_input_main_page"
        )

        menu_df_for_categories = load_menu_data()
        if not menu_df_for_categories.empty and 'Category' in menu_df_for_categories.columns:
             available_categories = ['All'] + sorted(list(menu_df_for_categories['Category'].astype(str).unique()))
        else:
            available_categories = ['All']
        
        cat_idx = available_categories.index(st.session_state.selected_category) if st.session_state.selected_category in available_categories else 0
        st.session_state.selected_category = st.selectbox(
            "🍽️ Or browse by category:", available_categories, index=cat_idx,
            key="category_select_main_page"
        )

        if st.button("😋 Find Food!", key="find_food_button_main_page", type="primary", use_container_width=True):
            st.session_state.show_recommendations = True # Trigger display of recommendation section
            recommendations_list = get_recommendations(
                category=st.session_state.selected_category if st.session_state.selected_category != 'All' else None,
                dietary_preferences=st.session_state.dietary_preferences,
                user_query=st.session_state.user_query,
                occasion=st.session_state.selected_occasion,
                mood=st.session_state.selected_mood,
                current_weather_input=st.session_state.user_weather_input,
                limit=10 # Number of recommendations to show
            )
            st.session_state.current_recommendations = recommendations_list
            # No rerun here, allow flow to display section

        # Display NLP feedback if a query is active
        if st.session_state.user_query:
            # Assuming extract_food_preferences is robust and returns a dict
            preferences = extract_food_preferences(st.session_state.user_query)
            if preferences: # Check if preferences were extracted
                st.info("🎯 Based on your query, I understand:")
                pref_text_parts = []
                if preferences.get('spicy'): pref_text_parts.append("spicy")
                if preferences.get('healthy'): pref_text_parts.append("healthy")
                if preferences.get('vegetarian') and 'vegetarian' not in pref_text_parts: pref_text_parts.append("vegetarian")
                if preferences.get('non_vegetarian') and 'non-vegetarian' not in pref_text_parts: pref_text_parts.append("non-vegetarian")
                
                meal_val = preferences.get('meal_type')
                if meal_val and isinstance(meal_val, str) and meal_val.lower() not in ['unknown', 'true', '']:
                    pref_text_parts.append(f"for {meal_val}")
                
                taste_list = preferences.get('taste') # taste should be a list of strings
                if taste_list and isinstance(taste_list, list) and len(taste_list) > 0:
                    pref_text_parts.append(f"that's {', '.join(taste_list)}")
                
                if pref_text_parts:
                    st.markdown(f"**Looking for:** {', '.join(pref_text_parts)} food.")
                else:
                    st.markdown("Processing your query...")


        # Display recommendations if available
        if st.session_state.show_recommendations:
            if st.session_state.current_recommendations:
                st.markdown("---")
                st.subheader("🌟 Here are your personalized recommendations:")
                num_cols_rec = 2 # Or 3 if cards are narrow
                rec_cols = st.columns(num_cols_rec)
                for i, rec_item in enumerate(st.session_state.current_recommendations):
                    with rec_cols[i % num_cols_rec]:
                        display_swipe_card(rec_item, index_key_suffix=f"rec_item_{i}")
            # Only show "no items" if a search was actually attempted and yielded nothing
            elif st.session_state.user_query or st.session_state.selected_category != 'All' or \
                 st.session_state.selected_occasion != "Any Occasion" or \
                 st.session_state.selected_mood != "Any Mood":
                st.info("🤔 No items found matching your current criteria. Try adjusting your search or filters.")

        # Complementary items logic (optional, if you have a specific use case beyond smart cart)
        # if 'show_complementary' in st.session_state and st.session_state.show_complementary:
        #     display_complementary_items(st.session_state.show_complementary)
        #     st.session_state.show_complementary = None


if __name__ == "__main__":
    main()