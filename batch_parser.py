import csv
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_multiple_products(product_urls: List[str], config: ParserConfig = None, max_workers: int = 1):
    if config is None:
        config = ParserConfig()
    
    results = []
    
    if max_workers == 1:
        for i, url in enumerate(product_urls, 1):
            print(f"\nПарсинг товара {i}/{len(product_urls)} ---")
            result = parse_ozon_reviews(url, config)
            results.append(result)
            
            if i < len(product_urls):
                print("Пауза между товарами...")
                time.sleep(30)
    else:
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