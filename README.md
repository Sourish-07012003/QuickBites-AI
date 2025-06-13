# QuickBites AI - Personalized Food Discovery & Ordering System

QuickBites AI is an intelligent food recommendation and ordering system built with Streamlit. It offers a personalized experience, helping users discover food based on a variety of preferences, including natural language queries, occasion, mood, and even user-inputted weather conditions.

## Features

*   **Natural Language Search:** Describe what you're craving (e.g., "spicy vegetarian lunch"), and the system understands.
*   **Personalized Recommendations:**
    *   Learns from your **past order ratings** to suggest items you'll love.
    *   Considers your selected **dietary preferences** (vegetarian, non-vegetarian, any).
    *   Adapts to the **occasion** (e.g., Quick Lunch, Family Dinner, Party).
    *   Suggests food based on your current **mood** (e.g., Happy, Stressed, Cozy).
    *   Tailors recommendations based on user-inputted **weather conditions**.
*   **Smart Cart:** Dynamically suggests complementary items as you add food to your cart.
*   **Interactive Food Cards:** Easy "Add to Cart" and quantity management directly on item cards.
*   **Shopping Cart Functionality:** View, modify, and manage items in your cart.
*   **Order History & Rating:**
    *   Track all your past orders.
    *   Rate individual items from past orders (1-5 stars) to improve future recommendations.
*   **Simulated Wallet Management:**
    *   Virtual wallet with a starting balance.
    *   Option to "add money" to the wallet via a simulated secure card payment form (with validation).
*   **Simulated Order Placement & Delivery:**
    *   Place orders using Cash on Delivery or Wallet balance.
    *   View simulated order confirmation and delivery details (partner, ETA).
*   **User-Friendly Interface:** Intuitive and responsive design built with Streamlit.
*   **Modular Codebase:** Separated utilities (`utils.py`) and NLP logic (`nlp_utils.py`).

## Demo / Screenshots

*(Optional: Consider adding a GIF or a few screenshots here to showcase the app's UI and key features.)*
*   *Main recommendation page with NLP input.*
*   *Sidebar showing preference filters (diet, occasion, mood, weather).*
*   *Cart with smart suggestions.*
*   *Order history with rating option.*
*   *Payment page with "Add to Wallet" and card form.*

## Tech Stack

*   **Python:** Core programming language.
*   **Streamlit:** For building the interactive web application.
*   **Pandas:** For data manipulation (menu data).
*   **NLTK & spaCy:** For Natural Language Processing (sentiment analysis, preference extraction, text preprocessing).
*   **Scikit-learn:** For TF-IDF and cosine similarity (semantic search).
*   **FuzzyWuzzy:** For fuzzy string matching (smart cart rules).
*   **JSON:** For storing user ratings and smart cart rules.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd QuickBites-AI # Or your project directory name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The `requirements.txt` file should be updated to include all necessary libraries: streamlit, pandas, nltk, spacy, scikit-learn, fuzzywuzzy, python-Levenshtein)*
    You may also need to download spaCy's English model if it's your first time:
    ```bash
    python -m spacy download en_core_web_sm
    ```

4.  **Prepare Data Files:**
    *   Ensure you have a `data/` directory in the project root.
    *   **`dummy_menu_dataset.csv`**: Place your menu dataset here. **Crucially, this CSV must include a `Tags` column**, populated with comma-separated keywords for each food item (e.g., `"veg,main_course,spicy,indian,comfort_food"`). Other essential columns include `Item`, `Description`, `Price`, `Category`, `Restaurant`, `Is_Vegetarian`.
    *   **`ratings.json`**: Create an empty JSON file in the `data/` directory:
        ```json
        []
        ```
    *   **`smart_cart_rules.json`**: Create this file in `data/` with rules for complementary item suggestions, e.g.:
        ```json
        {
            "Biryani": ["Raita", "Coca-Cola (300ml)"],
            "Pizza": ["Garlic Naan", "Pepsi (300ml)"]
        }
        ```

5.  **Run the application:**
    ```bash
    streamlit run app.py
    ```
    (Assuming your main Streamlit script is named `app.py`)

## Project Structure

QuickBites-AI/
├── app.py # Main Streamlit application script
├── utils.py # Utility functions (ratings, smart cart, IDs)
├── nlp_utils.py # NLP functions (preference extraction, semantic search)
├── requirements.txt # Python package dependencies
├── data/ # Data directory
│ ├── dummy_menu_dataset.csv # Menu data with a 'Tags' column
│ ├── ratings.json # Stores user ratings (initially empty: [])
│ └── smart_cart_rules.json # Rules for smart cart suggestions
└── README.md # This file

*(Note: `config.py` might not be strictly needed if API keys like Groq's are not currently in use. If you re-add external APIs, reinstate `config.py` for keys.)*

## How to Use

1.  The app will generate a unique User ID for your session.
2.  **Set Preferences (Sidebar):**
    *   Select your dietary preference.
    *   Choose the current occasion and your mood.
    *   Input the current weather conditions (temperature and condition).
3.  **Discover Food (Main Page):**
    *   Type what you're looking for in the "What are you craving?" search box (e.g., "I want something healthy and vegetarian for lunch").
    *   Alternatively, browse by food category.
    *   Click "Find Food!" to get personalized recommendations.
4.  **Interact with Food Cards:**
    *   View item details and price.
    *   Click "Add to Cart" or use "➕" / "➖" to manage quantity if already in cart.
5.  **Manage Cart (Sidebar):**
    *   View items, total price.
    *   Remove items.
    *   See "You might also like" suggestions based on your cart.
    *   Click "Place Order" to proceed to payment.
6.  **Payment:**
    *   Choose "Cash on Delivery" or "Wallet Payment".
    *   If wallet balance is insufficient, an option to "Add Money to Wallet" will appear.
    *   Use the simulated card payment form to add funds (validation is performed).
7.  **Order Confirmation:** View simulated order details and delivery information.
8.  **Order History (Sidebar):**
    *   Click "View Order History".
    *   See details of past orders.
    *   Rate individual items (1-5 stars) from your past orders. These ratings will enhance future recommendations.

## Future Enhancements / To-Do

*   Implement collaborative filtering for "users who liked X also liked Y" recommendations.
*   Real-time order tracking simulation on a map.
*   More detailed restaurant profile pages.
*   User accounts and persistent data storage (e.g., using a database like SQLite).
*   Integration with actual payment gateways (beyond simulation).
*   PDF bill generation.
*   Admin panel for menu management.

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeatureName`).
3.  Make your changes and commit them (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeatureName`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License. See the `LICENSE` file (if you create one) for details.