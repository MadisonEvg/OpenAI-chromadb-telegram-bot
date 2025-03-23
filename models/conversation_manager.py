from utils.helpers import trim_conversation_history
from config import Config
from docx import Document
from enum import Enum


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationManager:
    
    _instance = None  

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.conversation_histories = {} 
        return cls._instance

    def __init__(self):
        if not hasattr(self, "promt"):  # Чтобы не перезаписывать при повторном вызове
            self.promt = self._read_prompt_from_word(Config.PROMPT_FILE_PATH)

    def _read_prompt_from_word(self, file_path: str) -> str:
        try:
            document = Document(file_path)
            return "\n".join([para.text for para in document.paragraphs])
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")
            return "Произошла ошибка при загрузке промпта."

    def initialize_conversation(self, chat_id):
        if chat_id not in self.conversation_histories:
            self.conversation_histories[chat_id]=[{"role": Role.SYSTEM.value, "content": self.promt}]
    
    def reset_conversation(self, chat_id):
        if chat_id in self.conversation_histories:
            del self.conversation_histories[chat_id]
            
    def add_user_message(self, chat_id, content):
        self.add_message(chat_id, Role.USER, content)
        
    def add_assistant_message(self, chat_id, content):
        self.add_message(chat_id, Role.ASSISTANT, content)

    def add_message(self, chat_id, role, content):
        self.conversation_histories[chat_id].append({"role": role.value, "content": content})

    def get_history(self, chat_id):
        return self.conversation_histories.get(chat_id, [])

    def trim_history(self, chat_id, max_tokens=3500):
        history = self.conversation_histories.get(chat_id, [])
        trim_conversation_history(history, max_tokens)
        self.conversation_histories[chat_id] = history