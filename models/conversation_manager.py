import pytz
# from utils.helpers import trim_conversation_history
# from config import Config
from docx import Document
from enum import Enum
from datetime import datetime
from logger_config import logger


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    
class PromptType(Enum):
    MINI_DIALOG = "mini_dialog"
    MINI_PING = "mini_ping"
    
weekdays = {
    0: 'Понедельник',
    1: 'Вторник',
    2: 'Среда',
    3: 'Четверг',
    4: 'Пятница',
    5: 'Суббота',
    6: 'Воскресенье',
}    
    
def get_vladivostok_time():
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    vladivostok_time = datetime.now(vladivostok_tz)
    weekday = weekdays[vladivostok_time.weekday()]
    return f"{weekday}, {vladivostok_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    
class ConversationManager:
    
    _instance = None  
    
    DEFAULT_PROMPT_PATH = "promts/promt.docx"  # Дефолтный путь
    MINI_PROMPT_PATH = "promts/promt_dialog.docx"  # Путь для решения успешности диалога

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.conversation_histories = {} 
        return cls._instance
    
    def __init__(self):
        self.promt = self._read_prompt_from_word(self.DEFAULT_PROMPT_PATH)
        self.mini_promt_dialog = self._read_prompt_from_word(self.MINI_PROMPT_PATH)

    def _read_prompt_from_word(self, file_path: str) -> str:
        try:
            document = Document(file_path)
            return "\n".join([para.text for para in document.paragraphs])
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {e}")
            return "Произошла ошибка при загрузке промпта."

    def initialize_conversation(self, chat_id):
        if chat_id not in self.conversation_histories:
            self.conversation_histories[chat_id]=[{"role": Role.SYSTEM.value, "content": self.promt}]

    def reset_conversation(self, chat_id):
        if chat_id in self.conversation_histories:
            del self.conversation_histories[chat_id]
                    
    def add_update_message(self, chat_id, content, rep_text):
        # удаляем старую запись и вставляем новую, чтобы она не была где-то позади
        self.conversation_histories[chat_id] = [
            msg for msg in self.conversation_histories[chat_id]
            if not (msg['role'] == Role.SYSTEM.value and rep_text in msg['content'])
        ]
        self.add_message(chat_id, Role.SYSTEM, content)
            
    def add_user_message(self, chat_id, content):
        self.add_message(chat_id, Role.USER, content)
        
    def add_assistant_message(self, chat_id, content):
        self.add_message(chat_id, Role.ASSISTANT, content)

    def add_message(self, chat_id, role, content):
        self.conversation_histories[chat_id].append({"role": role.value, "content": content})

    def get_history(self, chat_id):
        vladivostok_time = get_vladivostok_time()
        time_promt  = list()
        time_promt.append({"role": Role.SYSTEM.value, "content": f"Текущее время во Владивостоке: {vladivostok_time}"})
        b = self.conversation_histories.get(chat_id, [])
        # print(b)
        return self.conversation_histories.get(chat_id, []) + time_promt
    
    def get_history_for_mini(self, chat_id, prompt_type: PromptType = PromptType.MINI_DIALOG):
        prompt_map = {
            PromptType.MINI_DIALOG: self.mini_promt_dialog,
        }
        prompt = prompt_map.get(prompt_type)
        result = list()
        result.append({"role": Role.SYSTEM.value, "content": prompt})
        for message in self.get_history(chat_id)[1:]:
            if message['role'] in (Role.USER.value, Role.ASSISTANT.value):
                result.append(message)
        return result
    
    def trim_history(self, chat_id, max_tokens=3500):
        history = self.conversation_histories.get(chat_id, [])
        # trim_conversation_history(history, max_tokens)
        self.conversation_histories[chat_id] = history