import json
import logging
import asyncio
import httpx
from datetime import datetime
from config import Config
from utils.helpers import count_tokens
from models.conversation_manager import ConversationManager, PromptType
from openai import AsyncOpenAI
from logger_config import logger

AUDIO_PHOTO_RESPOSE = "Напишите пожалуйста текстом🙏 \nНаш софт позволяет видеть только текстовое сообщение."

class OpenAIClient:
    
    _instance = None  
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        transport = httpx.AsyncHTTPTransport(proxy=Config.PROXY_URL)
        http_async_client = httpx.AsyncClient(transport=transport)
        self._client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY, http_client=http_async_client)
        self._conversation_manager = ConversationManager()
        self.model_gpt4omini = Config.MODEL_GPT4OMINI

    async def _ask_openai(self, messages, model):
        try:
            response = await self._client.chat.completions.create(
                temperature=Config.TEMPERATURE,
                model=model,
                messages=messages
            )
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI: {e}")
            return "Произошла ошибка при обработке запроса.", 0, 0
        response_text = response.choices[0].message.content.strip()
        input_tokens, output_tokens = count_tokens(messages, response_text)
        # logger.info(f"Ответ от {model}: {response_text}")
        # logger.info(f"Входных токенов: {input_tokens}, Выходных токенов: {output_tokens}")
        return response_text, input_tokens, output_tokens
    
    async def create_gpt4o_response(self, question, chat_id):
        # Добавляем новое сообщение пользователя
        # self._conversation_manager.add_user_message(chat_id, question)
        
        # Ограничиваем историю, чтобы не превышать лимит токенов
        self._conversation_manager.trim_history(chat_id, max_tokens=Config.MAX_TOKENS)
        
        # Отправляем всю историю вместе с новым сообщением для GPT
        task_response = asyncio.create_task(self._ask_openai(
            self._conversation_manager.get_history(chat_id),
            model=Config.MODEL_GPT4O
        ))
        task_delay = asyncio.create_task(asyncio.sleep(Config.ASSISTANT_DELAY))
        gpt4_response, input_tokens, output_tokens = await task_response
        await task_delay
        self._conversation_manager.add_assistant_message(chat_id, gpt4_response)
        
        return gpt4_response, input_tokens, output_tokens
    
    async def get_gpt4o_mini_response(self, chat_id, prompt_type: PromptType):
        # Ограничиваем историю, чтобы не превышать лимит токенов
        self._conversation_manager.trim_history(chat_id, max_tokens=Config.MAX_TOKENS)
        
        history_for_mini = self._conversation_manager.get_history_for_mini(chat_id, prompt_type)
        logger.info("-------------------------")
        # Отправляем всю историю вместе с новым сообщением для GPT
        task_response = asyncio.create_task(self._ask_openai(
            history_for_mini,
            model=Config.MODEL_GPT4OMINI
        ))
        gpt4_response, _, _ = await task_response
        logger.info("--get_gpt4o_mini response:")
        logger.info(gpt4_response)
        logger.info("-------------------------")
        
        return gpt4_response
