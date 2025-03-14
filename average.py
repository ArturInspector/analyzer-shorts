import json

def calculate_average_coefficient(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_coefficient = 0
    niche_count = 0
    
    for niche, details in data.items():
        if 'coefficient' in details:
            total_coefficient += details['coefficient']
            niche_count += 1
    
    if niche_count > 0:
        average_coefficient = total_coefficient / niche_count
    else:
        average_coefficient = 0
    
    return round(average_coefficient, 2)

def calculate_view_ratio(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_horizontal_views = 0
    total_vertical_views = 0
    
    for niche, details in data.items():
        if 'horizontal_videos' in details:
            for video in details['horizontal_videos']:
                total_horizontal_views += video['views']
        
        if 'vertical_videos' in details:
            for video in details['vertical_videos']:
                total_vertical_views += video['views']

    if total_horizontal_views > 0:
        view_ratio = total_vertical_views / total_horizontal_views
        print(view_ratio)
    else:
        view_ratio = 0
    
    return round(view_ratio, 2)

# Пример использования
view_ratio = calculate_view_ratio('output.json')
print(f"Соотношение просмотров shorts к длинным видео: {view_ratio}")

# С коэффициентом возникли некие проблемы, далее буду докручивать, пока что сделал только соотношение просмотров.
#average_coefficient = calculate_average_coefficient('output.json')
#print(f"Средний коэффициент: {average_coefficient}")
