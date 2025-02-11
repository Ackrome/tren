import git
import requests
import time

api_token = "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"
Model = 'EleutherAI/gpt-neo-125M'
#Model = 'distilgpt2'
#Model = 'google-t5/t5-small'
#Model = 'EleutherAI/gpt-neo-2.7B'
#Model = 'EleutherAI/gpt-neo-1.3B'


    
def preload_model(api_token):
    """
    Предварительно загружает модель, чтобы она была готова к использованию.
    
    :param api_token: Ваш API-токен Hugging Face.
    """
    API_URL = f"https://api-inference.huggingface.co/models/{Model}"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {
        "inputs": "Test input to preload the model.",
        "parameters": {"max_length": 10}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            print("Model preloaded successfully.")
        else:
            print(f"Preloading failed: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error during preloading: {e}")


def generate_commit_message_with_retries(diff, api_token, retries=5, delay=5):
    global model
    """
    Генерирует сообщение коммита с повторными попытками в случае ошибки.
    
    :param diff: Текстовый дифф изменений.
    :param api_token: Ваш API-токен Hugging Face.
    :param retries: Количество попыток.
    :param delay: Задержка между попытками (в секундах).
    :return: Сгенерированное сообщение коммита.
    """
    API_URL = f"https://api-inference.huggingface.co/models/{Model}"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    #prompt = f"Generate a concise commit message for the following changes:\n\n{diff}"
    prompt = f"Generate a concise Git commit message for the following code changes:\n\n{diff}\n\nCommit message:"
    
    payload = {
    "inputs": prompt,
    "parameters": {
        "max_length": min(2048, len(prompt.split()) + 50),  # Ограничиваем длину ответа
        "num_return_sequences": 1,
        "temperature": 0.7,  # Контролирует случайность генерации
        "top_p": 0.9         # Фильтрует менее вероятные токены
    }
}
    
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                print('Response:')
                return response.json()[0]['generated_text']
            elif response.status_code == 503:
                error_data = response.json()
                estimated_time = error_data.get("estimated_time", delay)
                print(f"Model is loading. Retrying in {estimated_time} seconds...")
                time.sleep(estimated_time)
            else:
                raise Exception(f"Error: {response.status_code}, {response.text}")
        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise Exception("All attempts failed.")
            

def get_git_diff(repo_path):
    """
    Получает дифф между текущим состоянием рабочего каталога и последним коммитом.
    
    :param repo_path: Путь к локальному репозиторию.
    :return: Строка с диффом.
    """
    try:
        # Открываем репозиторий
        repo = git.Repo(repo_path)
        
        # Проверяем, есть ли изменения
        if not repo.is_dirty():
            return "No changes detected in the repository."
        
        # Получаем дифф относительно HEAD
        diff = repo.git.diff('HEAD')
        return diff
    
    except Exception as e:
        return f"Error: {str(e)}"
    


def filter_diff(diff):
    """
    Фильтрует дифф, оставляя только добавленные и удаленные строки.
    
    :param diff: Текстовый дифф.
    :return: Отфильтрованный дифф.
    """
    filtered_lines = []
    for line in diff.split('\n'):
        if line.startswith('+') or line.startswith('-'):
            # Исключаем строки, которые содержат только пробелы или закомментированный код
            if not line.strip().startswith('#') and len(line.strip()) > 1:
                filtered_lines.append(line)
    return '\n'.join(filtered_lines)


def shorten_diff(diff, max_lines=20):
    """
    Сокращает дифф до указанного количества строк.
    
    :param diff: Текстовый дифф.
    :param max_lines: Максимальное количество строк.
    :return: Сокращенный дифф.
    """
    lines = diff.split('\n')
    if len(lines) > max_lines:
        return '\n'.join(lines[:max_lines]) + "\n[...]"
    return diff




preload_model(api_token)

repo_path = r'C:\Users\ivant\Desktop\tren'
diff = get_git_diff(repo_path)
diff = filter_diff(diff)
diff = shorten_diff(diff)
#print('\n'+diff)

commit_message = generate_commit_message_with_retries(diff, api_token)
print(commit_message)