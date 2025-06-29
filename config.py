import os
import csv
import time
from dataclasses import dataclass, field
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class ImprovedParserConfig:
    headless: bool = False
    window_size: str = "1920,1080"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    max_pages: int = 10
    delay_between_pages: tuple = (3, 7)
    delay_between_reviews: tuple = (0.5, 1.5)
    debug_mode: bool = True
    save_html: bool = True
    save_screenshots: bool = True
    output_dir: str = "output"
    screenshots_dir: str = "screenshots"
    debug_dir: str = "debug"
    page_load_timeout: int = 30
    element_wait_timeout: int = 15

    def __post_init__(self):
        for directory in [self.output_dir, self.screenshots_dir, self.debug_dir]:
            os.makedirs(directory, exist_ok=True)

@dataclass
class ParserConfig:
    headless: bool = False
    window_size: str = "1920,1080"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    max_pages: int = 50
    delay_between_pages: tuple = (2, 5)
    delay_between_reviews: tuple = (0.5, 1.5)
    output_dir: str = "output"
    screenshots_dir: str = "screenshots"
    review_selectors: List[str] = field(default=None)
    author_selectors: List[str] = field(default=None)
    rating_selectors: List[str] = field(default=None)
    text_selectors: List[str] = field(default=None)

    def __post_init__(self):
        self.post_init()

    def post_init(self):
        if self.review_selectors is None:
            self.review_selectors = [
                '[data-widget="webReviews"]',
                '[data-widget="webListReviews"]',
                '[data-widget="webReviewCard"]',
                '.review-item',
                '.review-card',
                '[data-testid="review"]'
            ]
        if self.author_selectors is None:
            self.author_selectors = [
                '[data-widget="webReviewAuthor"]',
                '.review-author',
                '.author-name',
                '.user-name',
                '.reviewer-name'
            ]
        if self.rating_selectors is None:
            self.rating_selectors = [
                '[data-widget="webRating"]',
                '.review-rating',
                '.rating-stars',
                '.stars'
            ]
        if self.text_selectors is None:
            self.text_selectors = [
                '[data-widget="webReviewText"]',
                '.review-text',
                '.review-content',
                '.comment-text'
            ]
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

def parse_multiple_products(product_urls: List[str], config: ParserConfig = None, max_workers: int = 1):
    if config is None:
        config = ParserConfig()
    
    results = []

    if max_workers == 1:
        for i, url in enumerate(product_urls, 1):
            print(f"\n--- Парсинг товара {i}/{len(product_urls)} ---")
            from simple_runner import parse_ozon_reviews
            result = parse_ozon_reviews(url, config)
            results.append(result)
            if i < len(product_urls):
                print("Пауза между товарами...")
                time.sleep(30)
    else:
        from simple_runner import parse_ozon_reviews
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(parse_ozon_reviews, url, config): url 
                for url in product_urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"Завершен парсинг: {url}")
                except Exception as e:
                    print(f"Ошибка для {url}: {e}")
                    results.append({'error': str(e), 'product_url': url, 'reviews': []})
    return results

def load_urls_from_csv(csv_file: str) -> List[str]:
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith('http'):
                urls.append(row[0])
    return urls
