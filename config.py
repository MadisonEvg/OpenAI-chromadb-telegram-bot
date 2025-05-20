import os

IN_DOCKER = os.environ.get("IN_DOCKER", False)

# Если НЕ в Docker — загружаем переменные из `.env`
if not IN_DOCKER:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.getcwd(), ".env", ".env")
    load_dotenv(dotenv_path)

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    PROMPT_FILE_PATH = os.getenv('PROMPT_FILE_PATH')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    WELCOME_PHRASE = os.getenv('WELCOME_PHRASE')
    MAX_MESSAGES = os.getenv('MAX_MESSAGES', None)
    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.5))
    ASSISTANT_DELAY = int(os.getenv('ASSISTANT_DELAY', 1))
    PROXY_URL = os.getenv('PROXY_URL', 1)
    MODEL_GPT4O = "gpt-4o"
    MODEL_GPT4OMINI = "gpt-4o-mini"
    MAX_TOKENS = 10500