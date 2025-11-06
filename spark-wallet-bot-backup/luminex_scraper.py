"""
LUMINEX (luminex.io) SCRAPER
Получает данные токенов с нового launchpad Luminex
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from typing import Dict, List, Optional


class LuminexScraper:
    """Scraper для Luminex launchpad"""
    
    BASE_URL = "https://luminex.io"  # ПРАВИЛЬНЫЙ URL!
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Инициализация Chrome driver"""
        if self.driver:
            return
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Автоматическая установка ChromeDriver через webdriver-manager
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def get_token_by_address(self, token_address: str) -> Optional[Dict]:
        """Получить данные токена по address"""
        self._init_driver()
        
        try:
            # ПРАВИЛЬНЫЙ URL для Luminex
            url = f"{self.BASE_URL}/spark/token/{token_address}"
            print(f"📡 Loading token page: {url}")
            
            self.driver.get(url)
            
            # Увеличиваем timeout и ждем загрузки контента
            wait = WebDriverWait(self.driver, 30)  # Увеличено с 15 до 30 секунд
            
            # Ждем либо h1 (название токена), либо body (любая страница)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            except:
                # Если h1 не нашлось за 30 сек - все равно продолжаем
                print("  ⚠️ Timeout waiting for h1, continuing anyway...")
            
            time.sleep(2)  # Доп время для полной загрузки JS (уменьшено с 3 до 2)
            
            # Парсим данные токена
            token_data = {}
            
            # Поиск названия (h1 тег с классом font-bold text-white)
            try:
                name_elem = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'font-bold') and contains(@class, 'text-white')]")
                token_data['name'] = name_elem.get_attribute('textContent').strip() or name_elem.text.strip()
                print(f"  ✓ Name: {token_data['name']}")
            except Exception as e:
                print(f"  ✗ Name not found: {e}")
            
            # Поиск символа (span с эмодзи рядом с h1)
            try:
                symbol_elem = self.driver.find_element(By.XPATH, "//h1/../span[contains(@class, 'text-slate-500')]")
                token_data['symbol'] = symbol_elem.get_attribute('textContent').strip() or symbol_elem.text.strip()
                print(f"  ✓ Symbol: {token_data['symbol']}")
            except Exception as e:
                print(f"  ✗ Symbol not found: {e}")
            
            # Поиск цены (div с классами text-*xl font-bold text-white и содержащий $)
            try:
                price_elem = self.driver.find_element(By.XPATH, "//div[contains(@class, 'font-bold') and contains(@class, 'text-white') and (contains(@class, 'text-2xl') or contains(@class, 'text-3xl') or contains(@class, 'text-4xl'))][contains(text(), '$')]")
                token_data['price_text'] = price_elem.get_attribute('textContent').strip() or price_elem.text.strip()
                print(f"  ✓ Price: {token_data['price_text']}")
            except Exception as e:
                print(f"  ✗ Price not found: {e}")
            
            # Поиск Market Cap
            try:
                mc_elem = self.driver.find_element(By.XPATH, "//div[text()='Market Cap']/..//div[contains(@class, 'font-bold')]")
                token_data['market_cap_text'] = mc_elem.text.strip()
                print(f"  ✓ Market Cap: {token_data['market_cap_text']}")
            except Exception as e:
                print(f"  ✗ Market Cap not found: {e}")
            
            # Поиск 24h Volume
            try:
                vol_elem = self.driver.find_element(By.XPATH, "//div[text()='24h Volume']/..//div[contains(@class, 'font-bold')]")
                token_data['volume_24h_text'] = vol_elem.text.strip()
                print(f"  ✓ 24h Volume: {token_data['volume_24h_text']}")
            except Exception as e:
                print(f"  ✗ 24h Volume not found: {e}")
            
            # Поиск Holders
            try:
                holders_elem = self.driver.find_element(By.XPATH, "//div[text()='Holders']/..//div[contains(@class, 'font-bold')]")
                token_data['holders_text'] = holders_elem.text.strip()
                print(f"  ✓ Holders: {token_data['holders_text']}")
            except Exception as e:
                print(f"  ✗ Holders not found: {e}")
            
            print(f"\n📊 Raw Data: {token_data}")
            
            if token_data:
                # Парсим числа
                price = self._parse_price(token_data.get('price_text', ''))
                market_cap = self._parse_number(token_data.get('market_cap_text', ''))
                volume = self._parse_number(token_data.get('volume_24h_text', ''))
                holders = self._parse_number(token_data.get('holders_text', ''))
                
                return {
                    'symbol': token_data.get('symbol', 'UNKNOWN'),
                    'name': token_data.get('name', 'Unknown Token'),
                    'token_address': token_address,
                    'price_usd': price,
                    'market_cap': market_cap,
                    'volume_24h': volume,
                    'holders': holders,
                    'source': 'luminex.io',
                    '_raw_data': token_data
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        """Закрыть browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _parse_price(self, price_str: str) -> float:
        """Парсит цену из строки вида $0.0000 или $93.8K"""
        try:
            # Убираем $, пробелы, запятые
            clean = price_str.replace('$', '').replace(',', '').replace(' ', '').strip()
            
            # Обработка специальных случаев (< 0.00000001)
            if clean.startswith('<') or '0.0000' in clean and len(clean) <= 6:
                return 0.00000001  # Минимальное значение
            
            # Если есть K, M, B
            if 'K' in clean.upper():
                return float(clean.upper().replace('K', '')) * 1000
            elif 'M' in clean.upper():
                return float(clean.upper().replace('M', '')) * 1_000_000
            elif 'B' in clean.upper():
                return float(clean.upper().replace('B', '')) * 1_000_000_000
            else:
                return float(clean)
        except:
            return 0.0
    
    def _parse_number(self, num_str: str) -> float:
        """Парсит число из строки вида 75 или $93.8K"""
        try:
            # Убираем $, пробелы, запятые
            clean = num_str.replace('$', '').replace(',', '').replace(' ', '').strip()
            
            # Если есть K, M, B
            if 'K' in clean.upper():
                return float(clean.upper().replace('K', '')) * 1000
            elif 'M' in clean.upper():
                return float(clean.upper().replace('M', '')) * 1_000_000
            elif 'B' in clean.upper():
                return float(clean.upper().replace('B', '')) * 1_000_000_000
            else:
                return float(clean)
        except:
            return 0.0


def test_luminex_scraper():
    """Тест scraper"""
    print("="*70)
    print("LUMINEX SCRAPER TEST")
    print("="*70 + "\n")
    
    scraper = LuminexScraper(headless=False)  # С окном чтобы видеть
    
    try:
        # Пробуем загрузить конкретный токен
        test_address = "btkn1fa6l5xk6kwd9hdenvjy2atcrcrh0du5g3yq0c4znnrzmrlvgpkasnkh0dl"
        token = scraper.get_token_by_address(test_address)
        
        if token:
            print(f"✅ Token found!")
            for key, value in token.items():
                print(f"  {key}: {value}")
        else:
            print("⚠️ Token not found or couldn't parse")
        
        input("\n\nPress ENTER to close browser...")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    test_luminex_scraper()
