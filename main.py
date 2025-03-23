from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from utils.openai_client import OpenAIClient
from models.conversation_manager import ConversationManager
from config import Config

load_dotenv()
# Инициализация клиента OpenAI
openai_client = OpenAIClient()
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

    await update.message.reply_text(Config.WELCOME_PHRASE)

async def respond(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_input = update.message.text

    if chat_id not in user_message_count:
        user_message_count[chat_id] = 0

    if Config.MAX_MESSAGES and user_message_count[chat_id] >= int(Config.MAX_MESSAGES):
        update.message.reply_text(
            "Вы превысили количество сообщений для демо-версии ИИ Менеджера, по вопросам сотрудничества обращайтесь по номеру +79146738418")
        return

    # Запрашиваем ответ от GPT-4, передавая результат поиска из векторной базы данных
    final_response, input_tokens_o, output_tokens_o = openai_client.create_gpt4o_response(
        user_input, chat_id
    )
        
    user_message_count[chat_id] += 1
    await update.message.reply_text(final_response)


def main():
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    application.run_polling()


if __name__ == "__main__":
    main()
