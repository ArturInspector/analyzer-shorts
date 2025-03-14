import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import isodate
import logging
from dotenv import load_dotenv
import time
import sys
import codecs

# Заменим настройку логирования:
# Настройка логирования
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_analyzer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YouTubeAnalyzer:
    def __init__(self, api_key: str):
        """
        Инициализация анализатора YouTube.
        
        Args:
            api_key (str): API ключ для доступа к YouTube Data API
        """
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.niches = [
            "котики",
            "смешные собаки",
            "реакции на фильмы",
            "новые песни",
            "челленджи",
            "пранки",
            "танцы",
            "пародии",
            "влоги",
            "анимации",
            "игры",
            "щенки и котята",
            "смешные моменты",
            "косплей",
            "скрытые камеры",
            "семейные игры",
            "вирусные танцы",
            "обзоры фильмов",
            "обзоры сериалов",
            "дети и еда",
            "путешествия",
            "обзоры гаджетов",
            "рецепты",
            "лучшие игры",
            "научные эксперименты"
        ]
        # Добавляем минимальное количество просмотров для анализа
        self.min_views = 1000
        # Добавляем задержку между запросами (в секундах)
        self.request_delay = 0.5

    def search_videos(self, query: str, is_shorts: bool = False, max_results: int = 3) -> List[Dict]:
        """
        Поиск видео по заданному запросу.
        
        Args:
            query (str): Поисковый запрос
            is_shorts (bool): Искать ли Shorts видео
            max_results (int): Максимальное количество результатов
            
        Returns:
            List[Dict]: Список найденных видео
        """
        try:
            logger.info(f"Начинаем поиск видео для запроса '{query}' (shorts={is_shorts})")
            
            search_params = {
                'q': query,
                'part': 'id,snippet',
                'type': 'video',
                'maxResults': 50,
                'regionCode': 'RU',
                'order': 'viewCount',
                'safeSearch': 'none'  # Отключаем безопасный поиск
            }
            
            logger.info(f"Отправляем поисковый запрос с параметрами: {search_params}")
            search_response = self.youtube.search().list(**search_params).execute()
            
            if 'items' not in search_response:
                logger.error(f"Ответ API не содержит элементов: {search_response}")
                return []
                
            logger.info(f"Получено {len(search_response['items'])} результатов поиска")
            
            videos = []
            for item in search_response.get('items', []):
                try:
                    video_id = item['id']['videoId']
                    logger.debug(f"Обработка видео {video_id}")
                    
                    time.sleep(self.request_delay)
                    
                    video_response = self.youtube.videos().list(
                        part='snippet,statistics,contentDetails',
                        id=video_id
                    ).execute()
                    
                    if not video_response['items']:
                        logger.warning(f"Нет данных для видео {video_id}")
                        continue
                        
                    video_info = video_response['items'][0]
                    
                    # Проверяем наличие необходимых полей
                    if 'contentDetails' not in video_info or 'duration' not in video_info['contentDetails']:
                        logger.warning(f"Отсутствует информация о длительности для видео {video_id}")
                        continue
                        
                    if 'statistics' not in video_info or 'viewCount' not in video_info['statistics']:
                        logger.warning(f"Отсутствует информация о просмотрах для видео {video_id}")
                        continue
                    
                    view_count = int(video_info['statistics']['viewCount'])
                    duration = isodate.parse_duration(video_info['contentDetails']['duration'])
                    duration_seconds = duration.total_seconds()
                    
                    # Определяем тип видео
                    is_video_shorts = any([
                        duration_seconds <= 60,
                        'shorts' in item['snippet'].get('description', '').lower(),
                        '#shorts' in item['snippet'].get('title', '').lower(),
                        'shorts' in item['snippet'].get('title', '').lower(),
                        '/shorts/' in video_info['snippet'].get('description', '').lower()
                    ])
                    
                    if is_shorts != is_video_shorts:
                        logger.debug(f"Пропуск видео {video_id} (несоответствие типа shorts/не shorts)")
                        continue
                    
                    video_data = {
                        'title': video_info['snippet']['title'],
                        'views': view_count,
                        'duration': f"{int(duration_seconds // 60)}:{str(int(duration_seconds % 60)).zfill(2)}",
                        'video_id': video_id,
                        'url': f"https://youtube.com/{'shorts' if is_shorts else 'watch'}/{video_id}"
                    }
                    
                    # Удаляем эмодзи из заголовка при логировании
                    clean_title = ''.join(char for char in video_data['title'] if ord(char) < 65536)
                    logger.info(f"Найдено подходящее видео: {clean_title} ({view_count:,} просмотров)")
                    videos.append(video_data)
                    
                    if len(videos) >= max_results:
                        logger.info(f"Достигнуто необходимое количество видео ({max_results})")
                        break
                        
                except Exception as e:
                    logger.exception(f"Ошибка при обработке видео {video_id}: {str(e)}")
                    continue
            
            logger.info(f"Поиск завершен. Найдено {len(videos)} подходящих видео")
            return videos[:max_results]
            
        except Exception as e:
            logger.exception(f"Критическая ошибка при поиске видео: {str(e)}")
            return []

    def analyze_niche(self, niche: str) -> Optional[Dict]:
        """
        Анализ отдельной ниши.
        
        Args:
            niche (str): Название ниши
            
        Returns:
            Optional[Dict]: Результаты анализа ниши
        """
        try:
            logger.info(f"Начинаем анализ ниши: {niche}")
            
            horizontal_videos = self.search_videos(niche, is_shorts=False)
            logger.info(f"Найдено {len(horizontal_videos)} обычных видео")
            
            vertical_videos = self.search_videos(niche, is_shorts=True)
            logger.info(f"Найдено {len(vertical_videos)} Shorts видео")

            if not horizontal_videos and not vertical_videos:
                logger.warning(f"Не найдено видео для ниши: {niche}")
                return None

            # Даже если одного типа видео нет, мы все равно можем проанализировать другой
            total_horizontal_views = sum(v['views'] for v in horizontal_videos) if horizontal_videos else 0
            total_vertical_views = sum(v['views'] for v in vertical_videos) if vertical_videos else 0

            # Рассчитываем коэффициент
            if horizontal_videos and vertical_videos:
                coefficient = total_vertical_views / total_horizontal_views
            else:
                coefficient = 0 if not vertical_videos else float('inf')

            result = {
                'horizontal_videos': horizontal_videos,
                'vertical_videos': vertical_videos,
                'coefficient': round(coefficient, 2),
                'avg_horizontal_views': int(total_horizontal_views / len(horizontal_videos)) if horizontal_videos else 0,
                'avg_vertical_views': int(total_vertical_views / len(vertical_videos)) if vertical_videos else 0
            }
            
            logger.info(f"Анализ ниши {niche} завершен успешно")
            return result
            
        except Exception as e:
            logger.exception(f"Ошибка при анализе ниши {niche}: {str(e)}")
            return None

    def analyze_all_niches(self) -> Dict:
        """
        Анализ всех ниш и сохранение результатов.
        
        Returns:
            Dict: Результаты анализа всех ниш
        """
        results = {}
        total_coefficient = 0
        niche_count = 0
        
        for niche in self.niches:
            logger.info(f"Анализ ниши: {niche}")
            niche_data = self.analyze_niche(niche)
            
            if niche_data:
                results[niche] = niche_data
                total_coefficient += niche_data['coefficient']
                niche_count += 1
                self.print_niche_results(niche, niche_data)
        
        # Вычисляем средний коэффициент
        if niche_count > 0:
            average_coefficient = total_coefficient / niche_count
        else:
            average_coefficient = 0
        
        # Добавляем средний коэффициент в результаты
        results['average_coefficient'] = round(average_coefficient, 2)
        
        return results

    def print_niche_results(self, niche: str, niche_data: Dict):
        """
        Улучшенный вывод результатов анализа ниши в консоль.
        """
        print(f"\nНиша: {niche}")
        print(f"Среднее количество просмотров (не Shorts): {niche_data['avg_horizontal_views']:,}")
        print(f"Среднее количество просмотров (Shorts): {niche_data['avg_vertical_views']:,}")
        print(f"Коэффициент (Shorts / не Shorts): {niche_data['coefficient']}")
        print(f"Преобладание: {'Shorts' if niche_data['coefficient'] > 1 else 'Не Shorts'}")

def main():
    """
    Основная функция для запуска анализа.
    """
    # Загрузка переменных окружения из файла .env
    load_dotenv()

    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        logger.error("API ключ не найден. Установите переменную окружения YOUTUBE_API_KEY")
        return

    analyzer = YouTubeAnalyzer(api_key)
    results = analyzer.analyze_all_niches()

    # Сохранение результатов в файл
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info("Анализ завершен. Результаты сохранены в output.json")

if __name__ == "__main__":
    main()
