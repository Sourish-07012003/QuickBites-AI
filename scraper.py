import time
import logging
import random
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_driver():
    try:
        # Set up Chrome options with anti-detection measures
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-browser-side-navigation")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        
        # Add more sophisticated anti-detection measures
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_argument("--disable-features=BlockInsecurePrivateNetworkRequests")
        chrome_options.add_argument("--disable-features=CrossSiteDocumentBlockingIfIsolating")
        chrome_options.add_argument("--disable-features=CrossSiteDocumentBlockingAlways")
        chrome_options.add_argument("--disable-features=CrossSiteDocumentBlockingIfIsolating")
        
        # Add random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Initialize the Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set page load timeout and window size
        driver.set_page_load_timeout(30)
        driver.set_window_size(1920, 1080)
        
        # Execute JavaScript to modify navigator properties
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        return driver
    except Exception as e:
        logger.error(f"Error initializing driver: {str(e)}")
        raise

def check_driver_session(driver):
    """Check if the driver session is still valid"""
    try:
        driver.current_url
        return True
    except WebDriverException:
        return False

def wait_for_element(driver, by, value, timeout=15):
    """Wait for an element to be present and visible"""
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        # First wait for the element to be present
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        
        # Then wait for it to be visible
        WebDriverWait(driver, timeout).until(
            EC.visibility_of(element)
        )
        
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)  # Small delay after scrolling
        
        return element
    except TimeoutException:
        logger.error(f"Timeout waiting for element {value}")
        return None
    except WebDriverException as e:
        logger.error(f"Driver session error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error waiting for element {value}: {str(e)}")
        return None

def wait_for_elements(driver, by, value, timeout=15):
    """Wait for multiple elements to be present and visible"""
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        # First wait for at least one element to be present
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )
        
        # Then wait for at least one element to be visible
        WebDriverWait(driver, timeout).until(
            lambda driver: any(element.is_displayed() for element in elements)
        )
        
        return elements
    except TimeoutException:
        logger.error(f"Timeout waiting for elements {value}")
        return []
    except WebDriverException as e:
        logger.error(f"Driver session error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error waiting for elements {value}: {str(e)}")
        return []

def simulate_human_behavior(driver):
    """Simulate human-like behavior with safe scrolling"""
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        # Get page height
        page_height = driver.execute_script("return document.body.scrollHeight")
        
        # Random scrolling with smooth behavior
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(200, 500)
            driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, left: 0, behavior: 'smooth'}});")
            time.sleep(random.uniform(0.5, 1.5))
        
        # Scroll back to top smoothly
        driver.execute_script("window.scrollTo({top: 0, left: 0, behavior: 'smooth'});")
        time.sleep(random.uniform(0.5, 1))
    except WebDriverException as e:
        logger.error(f"Driver session error in human behavior simulation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in human behavior simulation: {str(e)}")

def scrape_burger_items(driver, url):
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        driver.get(url)
        time.sleep(random.uniform(3, 5))  # Random wait time
        
        # Simulate human behavior
        simulate_human_behavior(driver)
        
        # Wait for restaurant cards to load and be visible
        restaurant_selector = "div[class*='sc-1mo3ldo-0']"
        wait_for_element(driver, By.CSS_SELECTOR, restaurant_selector)
        
        # Get page source after JavaScript execution
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find restaurant cards with multiple possible selectors
        restaurant_selectors = [
            "div[class*='sc-1mo3ldo-0']",
            "div[class*='sc-1mo3ldo-1']",
            "div[class*='sc-1mo3ldo-2']"
        ]
        
        restaurants = []
        for selector in restaurant_selectors:
            restaurants.extend(soup.select(selector))
            if restaurants:
                break
        
        if restaurants:
            logger.info(f"Found {len(restaurants)} restaurants:")
            for restaurant in restaurants[:5]:  # Limit to top 5 restaurants
                try:
                    # Try multiple selectors for each piece of information
                    name = restaurant.select_one('h4[class*="sc-1hp8d8a-0"], h4[class*="sc-1hp8d8a-1"]')
                    location = restaurant.select_one('p[class*="sc-1hez2tp-0"], p[class*="sc-1hez2tp-1"]')
                    rating = restaurant.select_one('div[class*="sc-1q7bklc-5"], div[class*="sc-1q7bklc-6"]')
                    price = restaurant.select_one('div[class*="sc-1hez2tp-0"]:-soup-contains("₹"), div[class*="sc-1hez2tp-1"]:-soup-contains("₹")')
                    
                    if name and location:
                        logger.info(f"Restaurant: {name.text.strip()}")
                        logger.info(f"Location: {location.text.strip()}")
                        if rating:
                            logger.info(f"Rating: {rating.text.strip()}")
                        if price:
                            logger.info(f"Price Range: {price.text.strip()}")
                        logger.info("---")
                    
                except Exception as e:
                    logger.error(f"Error processing restaurant: {e}")
                    continue
        else:
            logger.error("No restaurants found. This might be due to:")
            logger.error("1. Zomato's anti-scraping measures")
            logger.error("2. The city or food item not being available")
            logger.error("3. Network issues")
            
    except WebDriverException as e:
        logger.error(f"Driver session error in burger scraping: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error scraping burger items: {str(e)}")

def get_restaurant_links(driver, url):
    """Extract restaurant links from the search page"""
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Simulate human behavior
        simulate_human_behavior(driver)
        
        # Wait for restaurant cards to load
        restaurant_selector = "div[class*='sc-1mo3ldo-0']"
        wait_for_element(driver, By.CSS_SELECTOR, restaurant_selector)
        
        # Get all restaurant links
        restaurant_links = []
        link_selectors = [
            "a[class*='sc-1mo3ldo-0']",
            "a[class*='sc-1mo3ldo-1']",
            "a[class*='sc-1mo3ldo-2']",
            "a[href*='/order']"
        ]
        
        for selector in link_selectors:
            try:
                elements = wait_for_elements(driver, By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and '/order' in href and href not in restaurant_links:
                        restaurant_links.append(href)
            except Exception:
                continue
        
        if not restaurant_links:
            # Try alternative approach using BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            links = soup.find_all('a', href=lambda x: x and '/order' in x)
            restaurant_links = [link['href'] for link in links if link['href'] not in restaurant_links]
        
        logger.info(f"Found {len(restaurant_links)} restaurant links")
        return restaurant_links
        
    except WebDriverException as e:
        logger.error(f"Driver session error in getting restaurant links: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error getting restaurant links: {str(e)}")
        return []

def scrape_restaurant_data(driver, url):
    restaurant_data = {
        "name": None,
        "location": None,
        "rating": None,
        "menu": []
    }
    try:
        if not check_driver_session(driver):
            raise WebDriverException("Driver session is invalid")
            
        driver.get(url)
        time.sleep(random.uniform(3, 5))  # Random wait time
        
        # Simulate human behavior
        simulate_human_behavior(driver)
        
        # Wait for the page to load completely
        time.sleep(5)  # Give more time for dynamic content to load
        
        # Try to find menu items using multiple approaches
        menu_items = []
        
        # Approach 1: Try to find menu items by class
        menu_selectors = [
            "div[class*='sc-1s0saks-']",  # Generic menu item class
            "div[class*='sc-1s0saks']",   # Alternative class pattern
            "div[class*='sc-1s0saks'] div",  # Nested divs
            "div[class*='sc-1s0saks'] h4",   # Menu item titles
            "div[class*='sc-1s0saks'] p",    # Menu item descriptions
            "div[class*='sc-1s0saks'] span", # Menu item prices
            "div[class*='sc-1s0saks'] a",    # Menu item links
            "div[class*='sc-1s0saks'] button" # Menu item buttons
        ]
        
        for selector in menu_selectors:
            try:
                elements = wait_for_elements(driver, By.CSS_SELECTOR, selector)
                if elements:
                    menu_items.extend(elements)
            except Exception:
                continue
        
        # Approach 2: Try to find menu items by data attributes
        data_selectors = [
            "div[data-testid*='menu-item']",
            "div[data-testid*='dish']",
            "div[data-testid*='item']",
            "div[data-testid*='food']"
        ]
        
        for selector in data_selectors:
            try:
                elements = wait_for_elements(driver, By.CSS_SELECTOR, selector)
                if elements:
                    menu_items.extend(elements)
            except Exception:
                continue
        
        # Approach 3: Try to find menu items by text content
        text_selectors = [
            "div:contains('₹')",  # Price indicator
            "div:contains('Rs.')", # Alternative price indicator
            "div:contains('INR')", # Currency indicator
            "div:contains('Menu')", # Menu section
            "div:contains('Items')" # Items section
        ]
        
        for selector in text_selectors:
            try:
                elements = wait_for_elements(driver, By.CSS_SELECTOR, selector)
                if elements:
                    menu_items.extend(elements)
            except Exception:
                continue
        
        # Approach 4: Try to find menu items by role or aria attributes
        role_selectors = [
            "div[role='menuitem']",
            "div[role='listitem']",
            "div[aria-label*='menu']",
            "div[aria-label*='dish']",
            "div[aria-label*='item']"
        ]
        
        for selector in role_selectors:
            try:
                elements = wait_for_elements(driver, By.CSS_SELECTOR, selector)
                if elements:
                    menu_items.extend(elements)
            except Exception:
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_menu_texts = []
        for item in menu_items:
            item_text = item.text.strip()
            if item_text and item_text not in seen:
                seen.add(item_text)
                unique_menu_texts.append(item_text)
        
        # If no menu items found, try fallback
        if not unique_menu_texts:
            try:
                all_divs = driver.find_elements(By.TAG_NAME, "div")
                for div in all_divs:
                    try:
                        text = div.text.strip()
                        if text and ('₹' in text or 'Rs.' in text or 'INR' in text) and text not in seen:
                            seen.add(text)
                            unique_menu_texts.append(text)
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error in final menu scraping attempt: {e}")
            if not unique_menu_texts:
                logger.error("No menu items found. This might be due to:")
                logger.error("1. Zomato's anti-scraping measures")
                logger.error("2. The menu items not being available")
                logger.error("3. Network issues")
        restaurant_data["menu"] = unique_menu_texts

        # Extract name, location, rating (try multiple selectors for robustness)
        try:
            # Name
            name_elem = None
            for sel in [
                'h1',
                'h4[class*="sc-1hp8d8a-0"]',
                'h4[class*="sc-1hp8d8a-1"]'
            ]:
                try:
                    name_elem = driver.find_element(By.CSS_SELECTOR, sel)
                    if name_elem and name_elem.text.strip():
                        restaurant_data["name"] = name_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        try:
            # Location
            location_elem = None
            for sel in [
                'p[class*="sc-1hez2tp-0"]',
                'p[class*="sc-1hez2tp-1"]',
                'address',
                'div[class*="sc-1yq6ixn-0"]'
            ]:
                try:
                    location_elem = driver.find_element(By.CSS_SELECTOR, sel)
                    if location_elem and location_elem.text.strip():
                        restaurant_data["location"] = location_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        try:
            # Rating
            rating_elem = None
            for sel in [
                'div[class*="sc-1q7bklc-5"]',
                'div[class*="sc-1q7bklc-6"]',
                'span[class*="sc-1q7bklc-1"]',
                'span[class*="sc-1q7bklc-3"]'
            ]:
                try:
                    rating_elem = driver.find_element(By.CSS_SELECTOR, sel)
                    if rating_elem and rating_elem.text.strip():
                        restaurant_data["rating"] = rating_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        return restaurant_data
    except WebDriverException as e:
        logger.error(f"Driver session error in restaurant scraping: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error scraping restaurant data: {str(e)}")
        return restaurant_data

def main():
    # List of food items to scrape
    food_items = [
        'burger',
        'pizza',
        'biryani',
        'paneer',
        'chicken',
        'naan'
    ]
    
    driver = None
    try:
        driver = initialize_driver()
        
        for food_item in food_items:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Starting to scrape {food_item.upper()} items...")
                logger.info(f"{'='*50}\n")
                
                # Construct the URL for the current food item
                url = f'https://www.zomato.com/kolkata/delivery/dish-{food_item}'
                
                # First get all restaurant links
                logger.info(f"Getting restaurant links for {food_item}...")
                restaurant_links = get_restaurant_links(driver, url)
                
                if restaurant_links:
                    # Scrape each restaurant's menu
                    all_restaurants = []
                    for i, restaurant_url in enumerate(restaurant_links[:5]):  # Limit to top 5 restaurants
                        try:
                            logger.info(f"\nScraping restaurant {i+1}/{min(5, len(restaurant_links))} for {food_item}: {restaurant_url}")
                            data = scrape_restaurant_data(driver, restaurant_url)
                            all_restaurants.append(data)
                            time.sleep(random.uniform(2, 4))  # Add delay between restaurants
                        except Exception as e:
                            logger.error(f"Error scraping restaurant {restaurant_url} for {food_item}: {str(e)}")
                            continue
                    # After all restaurants for this item:
                    with open(f"{food_item}.json", "w", encoding="utf-8") as f:
                        json.dump(all_restaurants, f, ensure_ascii=False, indent=2)
                else:
                    logger.error(f"No restaurant links found for {food_item}. Moving to next item.")
                
                # Add delay between different food items
                time.sleep(random.uniform(5, 8))
                
            except Exception as e:
                logger.error(f"Error processing {food_item}: {str(e)}")
                continue
        
    except WebDriverException as e:
        logger.error(f"Driver session error: {str(e)}")
        if driver:
            try:
                driver.quit()
            except:
                pass
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == '__main__':
    main()
