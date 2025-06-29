import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from config import ParserConfig
from ozon_reviews_parser import OzonReviewsParserImproved

def parse_ozon_reviews(product_url: str, config: ParserConfig = None) -> Dict:
    if config is None:
        config = ParserConfig()

    Path(config.output_dir).mkdir(exist_ok=True)
    Path(config.screenshots_dir).mkdir(exist_ok=True)

    parser = OzonReviewsParserImproved(config=config)

    try:
        print(f"Начинаем парсинг отзывов для: {product_url}")
        start_time = datetime.now()

        reviews = parser.parse_product_reviews(product_url)

        end_time = datetime.now()
        duration = end_time - start_time

        result = {
            'product_url': product_url,
            'product_id': parser.product_id,
            'total_reviews': len(reviews),
            'reviews': reviews,
            'parsing_info': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'parser_version': '1.0'
            }
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        product_id = parser.product_id or "unknown"
        filename = f"{config.output_dir}/ozon_reviews_{product_id}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Парсинг завершен!")
        print(f"Найдено отзывов: {len(reviews)}")
        print(f"Время выполнения: {duration}")
        print(f"Результаты сохранены: {filename}")

        return result

    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"{config.screenshots_dir}/error_{timestamp}.png"
        try:
            parser.save_screenshot(screenshot_path)
            print(f"Скриншот ошибки сохранен: {screenshot_path}")
        except:
            pass

        return {'error': str(e), 'reviews': []}

def main():
    if len(sys.argv) < 2:
        print("Использование: python simple_runner.py <URL_товара_на_Ozon>")
        sys.exit(1)

    product_url = sys.argv[1]

    config = ParserConfig(
        headless=False,
        max_pages=10
    )
    config.post_init()

    result = parse_ozon_reviews(product_url, config)

    if result.get('reviews'):
        print("\nПримеры отзывов:")
        for i, review in enumerate(result['reviews'][:3]):
            print(f"\nОтзыв {i+1}:")
            print(f"Автор: {review.get('author', 'Не указан')}")
            print(f"Рейтинг: {review.get('rating', 'Не указан')}")
            print(f"Текст: {review.get('text', 'Не указан')[:100]}...")

if __name__ == "__main__":
    main()
