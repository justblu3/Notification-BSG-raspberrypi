#!/usr/bin/env python3
"""
BSG Magazine Product Tracker with Telegram Notifications
Continuously monitors products and sends alerts via Telegram bot
"""


import json
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


class Config:
    """Configuration settings for the scraper and bot"""
    BASE_URL = "https://bsgmag.ro/catalog/produse-recente"
    STORAGE_FILE = "bsg_products.json"
    CONFIG_FILE = "bot_config.json"
    TIMEOUT = 10  # Request timeout in seconds
    CHECK_INTERVAL = 300  # Check every 5 minutes (300 seconds)
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Telegram settings (loaded from config file)
    TELEGRAM_BOT_TOKEN = None
    TELEGRAM_CHAT_ID = None


class BotConfig:
    """Handles bot configuration"""
    
    @staticmethod
    def create_config_file():
        """Create a template config file"""
        config = {
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "check_interval_seconds": 300,
            "notifications_enabled": True
        }
        
        with open(Config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Created config file: {Config.CONFIG_FILE}")
        print("\n📝 Please edit the config file and add your Telegram credentials:")
        print("   1. Get bot token from @BotFather on Telegram")
        print("   2. Get your chat ID from @userinfobot on Telegram")
        print("   3. Run this script again after updating the config\n")
    
    @staticmethod
    def load_config():
        """Load configuration from file"""
        if not os.path.exists(Config.CONFIG_FILE):
            BotConfig.create_config_file()
            sys.exit(0)
        
        try:
            with open(Config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            Config.TELEGRAM_BOT_TOKEN = config.get('telegram_bot_token')
            Config.TELEGRAM_CHAT_ID = config.get('telegram_chat_id')
            Config.CHECK_INTERVAL = config.get('check_interval_seconds', 300)
            
            # Validate required fields
            if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
                print("❌ Error: Please set your telegram_bot_token in bot_config.json")
                sys.exit(1)
            
            if not Config.TELEGRAM_CHAT_ID or Config.TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
                print("❌ Error: Please set your telegram_chat_id in bot_config.json")
                sys.exit(1)
            
            return config
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"❌ Error loading config file: {e}")
            sys.exit(1)


class TelegramNotifier:
    """Handles Telegram notifications"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a text message via Telegram"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return True
        
        except requests.RequestException as e:
            print(f"⚠️  Warning: Failed to send Telegram message: {e}")
            return False
    
    def send_product_notification(self, products: List[Dict]) -> bool:
        """Send notification about new products"""
        if not products:
            return True
        
        # Create formatted message
        if len(products) == 1:
            message = "🎉 <b>Produs nou pe BSG Magazine!</b>\n\n"
        else:
            message = f"🎉 <b>{len(products)} Produse noi pe BSG Magazine!</b>\n\n"
        
        for i, product in enumerate(products, 1):
            message += f"<b>{i}. {product['name']}</b>\n"
            message += f"💰 Preț: {product['price']}\n"
            message += f"🔗 <a href='{product['url']}'>Vezi produsul</a>\n\n"
        
        # Split message if too long (Telegram has 4096 char limit)
        if len(message) > 4000:
            # Send multiple messages
            for i in range(0, len(products), 5):
                batch = products[i:i+5]
                batch_message = self._format_batch_message(batch)
                self.send_message(batch_message)
                time.sleep(0.5)  # Avoid rate limiting
            return True
        else:
            return self.send_message(message)
    
    def _format_batch_message(self, products: List[Dict]) -> str:
        """Format a batch of products for notification"""
        message = "🎉 <b>Produse noi pe BSG Magazine!</b>\n\n"
        for i, product in enumerate(products, 1):
            message += f"<b>{i}. {product['name']}</b>\n"
            message += f"💰 Preț: {product['price']}\n"
            message += f"🔗 <a href='{product['url']}'>Vezi produsul</a>\n\n"
        return message
    
    def send_status_update(self, status: str) -> bool:
        """Send a status update message"""
        return self.send_message(f"ℹ️ {status}")
    
    def test_connection(self) -> bool:
        """Test the Telegram bot connection"""
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            bot_info = response.json()
            
            if bot_info.get('ok'):
                bot_name = bot_info['result']['username']
                print(f"✅ Telegram bot connected: @{bot_name}")
                return True
            return False
        
        except requests.RequestException as e:
            print(f"❌ Error: Could not connect to Telegram bot: {e}")
            return False


class ProductStorage:
    """Handles persistent storage of product data"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.products = self._load()
    
    def _load(self) -> Dict[str, Dict]:
        """Load products from JSON file"""
        if not os.path.exists(self.filepath):
            return {}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Could not load storage file: {e}")
            return {}
    
    def save(self) -> None:
        """Save products to JSON file"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"❌ Error: Could not save to storage file: {e}")
    
    def get_known_ids(self) -> Set[str]:
        """Get set of all known product IDs"""
        return set(self.products.keys())
    
    def add_products(self, products: List[Dict]) -> None:
        """Add new products to storage"""
        for product in products:
            product_id = product['id']
            if product_id not in self.products:
                self.products[product_id] = {
                    **product,
                    'first_seen': datetime.now().isoformat()
                }


class BSGScraper:
    """Scraper for BSG Magazine product pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(Config.HEADERS)
    
    def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a single page"""
        try:
            response = self.session.get(url, timeout=Config.TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            print(f"⚠️  Warning: Error fetching {url}: {e}")
            raise
    
    def extract_product_id(self, product_url: str) -> str:
        """Extract unique product ID from URL"""
        parsed = urlparse(product_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if path_parts and path_parts[-1].isdigit():
            return path_parts[-1]
        
        query_params = parse_qs(parsed.query)
        if 'id' in query_params:
            return query_params['id'][0]
        
        return product_url
    
    def extract_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract product information from page"""
        products = []
        
        product_elements = soup.select('.product-item, .product, article.product, .item-product')
        
        if not product_elements:
            product_elements = soup.select('[class*="product"]')
        
        for element in product_elements:
            try:
                link_elem = element.select_one('a[href*="/product"], a[href*="/produs"], a.product-link')
                if not link_elem:
                    link_elem = element.find('a', href=True)
                
                if not link_elem:
                    continue
                
                product_url = urljoin(base_url, link_elem['href'])
                product_id = self.extract_product_id(product_url)
                
                name_elem = element.select_one('.product-name, .product-title, h2, h3, .title')
                if not name_elem:
                    name_elem = link_elem
                product_name = name_elem.get_text(strip=True)
                
                price_elem = element.select_one('.price, .product-price, [class*="price"]')
                product_price = price_elem.get_text(strip=True) if price_elem else "N/A"
                
                img_elem = element.select_one('img')
                image_url = urljoin(base_url, img_elem['src']) if img_elem and img_elem.get('src') else None
                
                products.append({
                    'id': product_id,
                    'name': product_name,
                    'price': product_price,
                    'url': product_url,
                    'image_url': image_url
                })
            
            except Exception as e:
                continue
        
        return products
    
    def get_current_page_number(self, url: str) -> int:
        """Extract current page number from URL"""
        match = re.search(r'/p(\d+)/?$', url)
        if match:
            return int(match.group(1))
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'page' in params:
            return int(params['page'][0])
        if 'pag' in params:
            return int(params['pag'][0])
        
        return 1
    
    def find_next_page(self, soup: BeautifulSoup, current_url: str) -> str:
        """Find URL of next pagination page"""
        current_page = self.get_current_page_number(current_url)
        
        next_link = soup.select_one('a.next, a[rel="next"]')
        
        if not next_link:
            pagination_links = soup.select('.pagination a, .pager a, nav a, ul.page-numbers a')
            for link in pagination_links:
                link_text = link.get_text(strip=True).lower()
                if link_text in ['next', 'următorul', '›', '»', 'urmatorul', 'următor']:
                    next_link = link
                    break
        
        if not next_link:
            page_links = soup.select('.pagination a[href], .pager a[href], nav a[href], ul.page-numbers a[href]')
            for link in page_links:
                link_url = link.get('href', '')
                if not link_url:
                    continue
                
                full_url = urljoin(current_url, link_url)
                link_page_num = self.get_current_page_number(full_url)
                
                if link_page_num == current_page + 1:
                    return full_url
        
        if next_link and next_link.get('href'):
            return urljoin(current_url, next_link['href'])
        
        if re.search(r'/p\d+/?$', current_url):
            next_url = re.sub(r'/p\d+/?$', f'/p{current_page + 1}', current_url)
            return next_url
        elif current_page == 1 and '/produse-recente' in current_url:
            base = current_url.rstrip('/')
            return f"{base}/p2"
        
        return None
    
    def scrape_all_pages(self, silent: bool = False) -> List[Dict]:
        """Scrape all pages with pagination"""
        all_products = []
        current_url = Config.BASE_URL
        page_count = 0
        
        if not silent:
            print(f"🔍 Starting scrape from: {current_url}")
        
        while current_url and page_count < 3:
            page_count += 1
            if not silent:
                print(f"📄 Scraping page {page_count}...")
            
            try:
                soup = self.fetch_page(current_url)
                products = self.extract_products(soup, current_url)
                
                if not products:
                    if not silent:
                        print(f"⚠️  No products found on page {page_count}")
                    break
                
                all_products.extend(products)
                if not silent:
                    print(f"   Found {len(products)} products on this page")
                
                next_url = self.find_next_page(soup, current_url)
                if not next_url or next_url == current_url:
                    break
                
                current_url = next_url
            
            except Exception as e:
                if not silent:
                    print(f"⚠️  Error on page {page_count}: {e}")
                break
        
        if not silent:
            print(f"✅ Scraping complete. Total products found: {len(all_products)}")
        
        return all_products


def run_continuous_monitoring():
    """Run the bot in continuous monitoring mode"""
    print("🤖 BSG Magazine Product Tracker Bot")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load configuration
    config = BotConfig.load_config()
    
    # Initialize components
    storage = ProductStorage(Config.STORAGE_FILE)
    scraper = BSGScraper()
    notifier = TelegramNotifier(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID)
    
    # Test Telegram connection
    if not notifier.test_connection():
        print("❌ Could not connect to Telegram. Please check your bot token.")
        sys.exit(1)
    
    # Send startup notification
    notifier.send_status_update("🚀 Bot pornit! Monitorizez produse noi pe BSG Magazine...")
    
    print(f"📦 Known products in database: {len(storage.get_known_ids())}")
    print(f"⏰ Check interval: {Config.CHECK_INTERVAL} seconds")
    print(f"🔄 Monitoring started. Press Ctrl+C to stop.\n")
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] 🔍 Check #{check_count}: Scanning for new products...")
            
            try:
                # Scrape current products
                current_products = scraper.scrape_all_pages(silent=True)
                
                if not current_products:
                    print("   ⚠️  No products found (possible site issue)")
                    time.sleep(Config.CHECK_INTERVAL)
                    continue
                
                # Find new products
                known_ids = storage.get_known_ids()
                new_products = [p for p in current_products if p['id'] not in known_ids]
                
                if new_products:
                    print(f"   🎉 Found {len(new_products)} new product(s)!")
                    
                    # Send notification
                    notifier.send_product_notification(new_products)
                    
                    # Update storage
                    storage.add_products(new_products)
                    storage.save()
                    
                    # Display to console
                    for product in new_products:
                        print(f"      - {product['name']} ({product['price']})")
                else:
                    print(f"   ✅ No new products. Total tracked: {len(current_products)}")
            
            except Exception as e:
                print(f"   ❌ Error during check: {e}")
            
            # Wait before next check
            print(f"   ⏳ Next check in {Config.CHECK_INTERVAL} seconds...\n")
            time.sleep(Config.CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot stopped by user")
        notifier.send_status_update("⏸️ Bot oprit.")
        sys.exit(0)


def run_single_check():
    """Run a single check (original behavior)"""
    print("🚀 BSG Magazine Product Tracker")
    print(f"📅 Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    storage = ProductStorage(Config.STORAGE_FILE)
    known_ids = storage.get_known_ids()
    
    print(f"📦 Known products in database: {len(known_ids)}")
    
    scraper = BSGScraper()
    current_products = scraper.scrape_all_pages()
    
    if not current_products:
        print("\n⚠️  No products could be scraped. Please check the website or selectors.")
        return
    
    new_products = [p for p in current_products if p['id'] not in known_ids]
    
    # Display results
    if not new_products:
        print("\n✨ No new products found.")
    else:
        print(f"\n🎉 Found {len(new_products)} new product(s):\n")
        print("=" * 80)
        
        for i, product in enumerate(new_products, 1):
            print(f"\n{i}. {product['name']}")
            print(f"   💰 Price: {product['price']}")
            print(f"   🔗 URL: {product['url']}")
        
        print("\n" + "=" * 80)
    
    # Update storage
    if new_products:
        storage.add_products(new_products)
        storage.save()
        print(f"\n💾 Saved {len(new_products)} new product(s) to {Config.STORAGE_FILE}")
    else:
        print(f"\n💾 No updates to {Config.STORAGE_FILE}")


def main():
    """Main execution function"""
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--bot" or sys.argv[1] == "-b":
            run_continuous_monitoring()
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("BSG Magazine Product Tracker\n")
            print("Usage:")
            print("  python bsg.py           Run a single check")
            print("  python bsg.py --bot     Run in continuous bot mode")
            print("  python bsg.py --help    Show this help message")
            sys.exit(0)
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # Default: single check mode
        run_single_check()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
