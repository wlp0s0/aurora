import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not TOKEN or not OPENAI_KEY:
    raise ValueError("анлука, ключе нет")

client = OpenAI(api_key=OPENAI_KEY)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с инструкциями."""
    await update.message.reply_text(
        "✨ **DataHub AI.** ✨\n\n"
        "Я AI-консультант. **Отправь мне ОДНО СООБЩЕНИЕ**, где будет:\n"
        "1. **Твои интересы.**\n"
        "2. **Балл ЕНТ/GPA.**\n"
        "3. **Описание проектов (портфолио).**\n"
        "4. **Города, которые интересны, и уни, которые не хочешь.**\n\n"
        "Пример: *«Интересы: дизайн, англ. ЕНТ 105. Я делал постеры для КВН. Хочу Алматы/Астану, но не хочу КазНУ.»*\n\n"
        "Жду твой мега-текст!"
        , parse_mode='Markdown')

async def analyze_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Анализирует текст пользователя с помощью OpenAI, 
    структурирует данные и отправляет их на FastAPI бэкенд.
    """
    
    text = update.message.text
    tg_id = update.effective_user.id
    name = update.effective_user.username or update.effective_user.first_name
    
    await update.message.reply_text("⏳ **Ща проанализирую, 30 сек...**")

    try:
        completion = client.chat.completions.create(
         
            model="gpt-3.5-turbo-1106", 
            messages=[
                {"role": "system", "content": "Ты эксперт по профориентации. Извлеки структурированные данные из текста абитуриента для системы подбора ВУЗов. Ты ДОЛЖЕН ответить только JSON-объектом, используя ключи: main_interests (список), user_score (число), portfolio_summary (строка), portfolio_strength (число от 1 до 5), desired_cities (список), undesired_universities (список)."},
                {"role": "user", "content": text}
            ],
      
            response_format={"type": "json_object"} 
        )
        
        llm_json = completion.choices[0].message.content
        data = json.loads(llm_json)
        
        
        data['telegram_id'] = tg_id 
        data['username'] = name
      
        if 'portfolio_summary' not in data:
            raise ValueError("LLM не смог извлечь 'portfolio_summary'.")
        
    except Exception as e:
        logging.error(f"LLM/JSON Error: {e}")
        await update.message.reply_text(
            f" **AI-сервис тупит.** Проверь ключ или запрос. Детали: {e}"
        )
        return


    logging.info(f"Отправка данных на API: {API_URL}")
    try:
        response = requests.post(API_URL, json=data)
        
        if response.status_code == 200:
            msg = " **Профиль готов!** \n\n" \
                  f"Твое резюме: ({data.get('portfolio_summary', 'Резюме не найдено')[:50]}...)\n" \
                  "Теперь иди на сайт и **введи свой Telegram ID**, чтобы увидеть подборку уни!"
        else:
        
            msg = f" Ошибка сервера FastAPI (код: {response.status_code})."
            logging.error(f"FastAPI returned error {response.status_code}: {response.text}")

    except requests.exceptions.ConnectionError:
      
        msg = "Сервер (main.py) не запущен! Сначала запусти его командой `uvicorn main:app --reload`."
    except Exception as e:
         msg = f" Непредвиденная ошибка при отправке на API: {e}"

    await update.message.reply_text(msg, parse_mode='Markdown')



def main() -> None:
    """Инициализирует и запускает Telegram бота."""

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_and_send))

    logging.info("Telegram Bot запущен! Ожидание сообщений...")
    app.run_polling(poll_interval=1.0)

if __name__ == "__main__":
    main()