from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from utils.openai_client import OpenAIClient
from models.conversation_manager import ConversationManager, PromptType
from config import Config
from utils.db_parser import parse_json_files, parse_filter_text
from utils.chromadb_client import ChromaDbClient
from models.query import get_filtered_apartments
from logger_config import logger

load_dotenv()
# Инициализация клиента OpenAI
openai_client = OpenAIClient()
chromadb_client = ChromaDbClient(openai_client._client)
conversation_manager = ConversationManager()

conversation_histories = {}
user_message_count = {}


async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    conversation_manager.reset_conversation(chat_id)

    if chat_id in user_message_count:
        del user_message_count[chat_id]
        
    conversation_manager.initialize_conversation(chat_id)
    conversation_manager.add_user_message(chat_id, "Hello")
    conversation_manager.add_assistant_message(chat_id, Config.WELCOME_PHRASE)
    user_message_count[chat_id] = 0

    await update.message.reply_text(Config.WELCOME_PHRASE.replace("\\n", "\n"))
    
async def respond(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_input = update.message.text
    conversation_manager.initialize_conversation(chat_id)

    if chat_id not in user_message_count:
        user_message_count[chat_id] = 0

    if Config.MAX_MESSAGES and user_message_count[chat_id] >= int(Config.MAX_MESSAGES):
        update.message.reply_text(
            "Вы превысили количество сообщений для демо-версии ИИ Менеджера, по вопросам сотрудничества обращайтесь по номеру +79146738418")
        return
    logger.info('+ Пользователь ++++++++++++++++++++++')
    logger.info(user_input)
    logger.info('+++++++++++++++++++++++')
    conversation_manager.add_user_message(chat_id, user_input)
    
    # Запрашиваем анализ запроса клиента и получаем параметры поиска ЖК и квартир
    result = await openai_client.get_gpt4o_mini_response(chat_id, PromptType.MINI_DIALOG)
    filters = parse_filter_text(result)
    logger.info(filters)
    complex_names = None
    if filters["complex_search"] or filters["complex_search_phrase"] is not None:
        user_phase = filters.pop('complex_search_phrase', None)
        chromadb_result = await chromadb_client.search_in_vector_db(user_phase)
        conversation_manager.add_update_message(chat_id, chromadb_result, "Результат поиска в базе знаний запроса")
        logger.info('complex_names setted')
    # if complex_names:
        # filters['complex_names'] = complex_names
    logger.info(filters)
    filters.pop('complex_search_phrase', None)
    filters.pop('complex_search', None)
    results = get_filtered_apartments(**filters)
    logger.info('--- Результат промежуточного анализа запроса:')
    logger.info(results)
    logger.info("-----")
    
    conversation_manager.add_update_message(chat_id, results, "Результат промежуточного анализа запроса")
    
    # Запрашиваем ответ от GPT-4, передавая результат поиска из векторной базы данных
    final_response, _, _ = await openai_client.create_gpt4o_response(user_input, chat_id)
    logger.info('+ Ответ ++++++++++++++++++++++')
    logger.info(final_response)
    logger.info('+++++++++++++++++++++++')
    user_message_count[chat_id] += 1
    await update.message.reply_text(final_response)


def main():
    # parse_json_files()
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    application.run_polling()


if __name__ == "__main__":
    main()
