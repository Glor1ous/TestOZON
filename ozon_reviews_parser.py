import json
import time
import random
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class OzonReviewsParserImproved:
    
    def __init__(self, config=None):
        self.config = config
        self.driver = None
        self.reviews = []
        self.product_id = None
        self.debug = True
        
    def _setup_driver(self):
        chrome_options = Options()
        
        if self.config:
            if self.config.headless:
                chrome_options.add_argument('--headless')
            
            window_size = self.config.window_size.split(',')
            chrome_options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
            
            if self.config.user_agent:
                chrome_options.add_argument(f'--user-agent={self.config.user_agent}')
        else:
            chrome_options.add_argument('--window-size=1920,1080')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if not (self.config and self.config.headless):
            self.driver.maximize_window()
    
    def _debug_print(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def _save_debug_html(self, filename="debug.html"):
        if self.driver:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self._debug_print(f"HTML сохранен в {filename}")
    
    def parse_product_reviews(self, product_url: str) -> List[Dict]:
        try:
            self._setup_driver()
            self.reviews = []
            self.product_id = self._extract_product_id(product_url)
            
            self._debug_print(f"Открываем страницу: {product_url}")
            self.driver.get(product_url)
            self._handle_initial_page()
            
            self._save_debug_html("product_page.html")
            
            reviews_found = self._find_reviews_on_product_page()
            
            if not reviews_found:
                self._navigate_to_reviews()
                self._save_debug_html("reviews_page.html")
                self._parse_all_reviews()
            
            return self.reviews
            
        except Exception as e:
            self._debug_print(f"Ошибка при парсинге отзывов: {e}")
            self.save_screenshot("error_screenshot.png")
            self._save_debug_html("error_page.html")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_product_id(self, url: str) -> str:
        if '/product/' in url:
            parts = url.split('/product/')[1].split('-')
            return parts[-1].split('/')[0].split('?')[0]
        return ""
    
    def _handle_initial_page(self):
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        
        try:
            captcha_selectors = [
                '[data-widget="captcha"]',
                '.captcha',
                '#captcha'
            ]
            
            for selector in captcha_selectors:
                if self.driver.find_elements(By.CSS_SELECTOR, selector):
                    self._debug_print("Обнаружена капча")
                    if not (self.config and self.config.headless):
                        input("Решите капчу и нажмите Enter для продолжения...")
                    break
        except:
            pass
        
        try:
            cookie_selectors = [
                '[data-widget="cookieConsent"] button',
                'button[data-testid="cookie-accept"]',
                '.cookie-consent button'
            ]
            
            for selector in cookie_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    elements[0].click()
                    time.sleep(1)
                    break
        except:
            pass
        
        time.sleep(random.uniform(2, 4))
    
    def _find_reviews_on_product_page(self) -> bool:
        self._debug_print("Ищем отзывы на странице товара...")
        
        review_container_selectors = [
            '[data-widget="webReviews"]',
            '[data-widget="webListReviews"]',
            '[data-widget="reviews"]',
            '.reviews-section',
            '.product-reviews',
            '[data-testid="reviews"]',
            '.review-list',
            '.reviews-container'
        ]
        
        for selector in review_container_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self._debug_print(f"Найден контейнер отзывов: {selector}")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                    time.sleep(2)
                    
                    reviews = self._parse_reviews_in_container(elements[0])
                    if reviews:
                        self.reviews.extend(reviews)
                        self._debug_print(f"Найдено {len(reviews)} отзывов в контейнере")
                        return True
            except Exception as e:
                self._debug_print(f"Ошибка при поиске в {selector}: {e}")
                continue
        
        return False
    
    def _parse_reviews_in_container(self, container) -> List[Dict]:
        reviews = []
        
        review_item_selectors = [
            'div[data-widget="webReviewCard"]',
            '.review-item',
            '.review-card',
            '[data-testid="review"]',
            '.review',
            'div:has(.review-text)',
            'div:has([data-widget="webReviewText"])'
        ]
        
        review_elements = []
        for selector in review_item_selectors:
            try:
                elements = container.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self._debug_print(f"Найдены элементы отзывов: {selector} ({len(elements)} шт.)")
                    review_elements = elements
                    break
            except:
                continue
        
        if not review_elements:
            self._debug_print("Используем универсальный поиск отзывов...")
            all_divs = container.find_elements(By.TAG_NAME, "div")
            review_elements = [div for div in all_divs if len(div.text.strip()) > 50]
        
        for element in review_elements:
            try:
                review_data = self._extract_review_data_universal(element)
                if review_data and review_data.get('text'):
                    reviews.append(review_data)
            except Exception as e:
                self._debug_print(f"Ошибка при извлечении отзыва: {e}")
                continue
        
        return reviews
    
    def _extract_review_data_universal(self, element) -> Optional[Dict]:
        try:
            review_data = {}
            
            element_text = element.text.strip()
            if len(element_text) < 10:
                return None
            
            author_selectors = [
                '.review-author', '.author', '[data-widget="webReviewAuthor"]',
                '.user-name', '.reviewer-name', '.review-user',
                'span:contains("пользователь")', 'div:contains("@")'
            ]
            author = self._get_text_by_selectors_universal(element, author_selectors)
            
            rating = self._extract_rating_universal(element)
            
            text_selectors = [
                '.review-text', '[data-widget="webReviewText"]',
                '.review-content', '.comment-text', '.review-body'
            ]
            text = self._get_text_by_selectors_universal(element, text_selectors)
            
            if not text:
                text = element_text
            
            date_selectors = [
                '.review-date', '.date', '[data-widget="webReviewDate"]',
                'time', '.review-time'
            ]
            date = self._get_text_by_selectors_universal(element, date_selectors)
            
            review_data = {
                'author': author or 'Неизвестный автор',
                'rating': rating or 0,
                'text': text or element_text,
                'date': date or '',
                'raw_html': element.get_attribute('outerHTML')[:500]
            }
            
            return review_data if review_data['text'] else None
            
        except Exception as e:
            self._debug_print(f"Ошибка при извлечении данных отзыва: {e}")
            return None
    
    def _get_text_by_selectors_universal(self, parent_element, selectors: List[str]) -> str:
        for selector in selectors:
            try:
                elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements[0].text.strip()
            except:
                continue
        return ""
    
    def _extract_rating_universal(self, element) -> int:
        rating_selectors = [
            '[data-widget="webRating"]',
            '.rating', '.stars', '.review-rating'
        ]
        
        for selector in rating_selectors:
            try:
                rating_elements = element.find_elements(By.CSS_SELECTOR, selector)
                if rating_elements:
                    filled_stars = rating_elements[0].find_elements(By.CSS_SELECTOR, '[data-index]:not([data-state="empty"])')
                    if filled_stars:
                        return len(filled_stars)
                    
                    rating_text = rating_elements[0].text
                    for char in rating_text:
                        if char.isdigit() and int(char) <= 5:
                            return int(char)
            except:
                continue
        
        return 0
    
    def _navigate_to_reviews(self):
        try:
            self._debug_print("Ищем ссылку на отзывы...")
            
            reviews_link_selectors = [
                '[data-widget="webReviewProductScore"] a',
                'a[href*="reviews"]',
                '[data-widget="webProductRating"] a',
                '.product-review-summary a',
                'a:contains("отзыв")',
                'a:contains("Отзыв")',
                '[data-testid="reviews-link"]',
                '.reviews-link'
            ]
            
            reviews_link = None
            for selector in reviews_link_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        reviews_link = elements[0]
                        self._debug_print(f"Найдена ссылка на отзывы: {selector}")
                        break
                except:
                    continue
            
            if reviews_link:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", reviews_link)
                time.sleep(1)
                try:
                    reviews_link.click()
                except:
                    self.driver.execute_script("arguments[0].click();", reviews_link)
                
                time.sleep(3)
            else:
                self._debug_print("Пытаемся перейти по прямой ссылке на отзывы")
                base_url = self.driver.current_url.split('?')[0]
                reviews_url = f"{base_url}?tab=reviews"
                self.driver.get(reviews_url)
                time.sleep(3)
                
        except Exception as e:
            self._debug_print(f"Ошибка при навигации к отзывам: {e}")
    
    def _parse_all_reviews(self):
        self._debug_print("Начинаем парсинг всех отзывов...")
        
        found_reviews = self._find_reviews_on_current_page()
        
        if found_reviews:
            self._debug_print(f"Найдено {len(found_reviews)} отзывов")
            self.reviews.extend(found_reviews)
        else:
            self._debug_print("Отзывы не найдены на текущей странице")
    
    def _find_reviews_on_current_page(self) -> List[Dict]:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        all_elements = self.driver.find_elements(By.TAG_NAME, "div")
        potential_reviews = []
        
        for element in all_elements:
            try:
                text = element.text.strip()
                if (len(text) > 30 and 
                    len(text) < 2000 and 
                    not any(skip_word in text.lower() for skip_word in ['cookie', 'реклама', 'навигация', 'меню'])):
                    
                    review_data = {
                        'author': 'Неизвестный автор',
                        'rating': 0,
                        'text': text,
                        'date': '',
                        'element_tag': element.tag_name,
                        'element_class': element.get_attribute('class') or ''
                    }
                    potential_reviews.append(review_data)
                    
            except:
                continue
        
        return potential_reviews[:50] if potential_reviews else []
    
    def save_reviews_to_json(self, filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.reviews, f, ensure_ascii=False, indent=2)
        print(f"Отзывы сохранены в файл: {filename}")
    
    def save_screenshot(self, filename: str):
        if self.driver:
            self.driver.save_screenshot(filename)
            self._debug_print(f"Скриншот сохранен: {filename}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python improved_parser.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    parser = OzonReviewsParserImproved()
    reviews = parser.parse_product_reviews(url)
    
    print(f"Найдено отзывов: {len(reviews)}")
    for i, review in enumerate(reviews[:3]):
        print(f"\nОтзыв {i+1}:")
        print(f"Автор: {review.get('author', 'Не указан')}")
        print(f"Текст: {review.get('text', 'Не указан')[:100]}...")