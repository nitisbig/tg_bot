import os
import requests
from telebot import TeleBot, types
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
from agent import agent_run

load_dotenv()

BOT_TOKEN = os.getenv('telegram_api')
SERVER_URL = os.getenv("SERVER_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs on startup
    webhook_url_base = SERVER_URL
    
    if not webhook_url_base:
        print("WARNING: Neither SERVER_URL nor DEV_URL is set. Webhook will not be configured.")
    else:
        webhook_url = f"{webhook_url_base}/{BOT_TOKEN}"
        print(f"Setting webhook on startup to: {webhook_url}")
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            print("Webhook set successfully!")
            info = bot.get_webhook_info()
            print(f"Current webhook info: {info.url}")
        except Exception as e:
            print(f"Error setting webhook: {e}")
    
    yield
    # This block would run on shutdown (if you had any cleanup logic)
    print("Shutting down. Removing webhook.")
    bot.remove_webhook()

app = FastAPI(lifespan=lifespan)
bot = TeleBot(BOT_TOKEN)

class Answer(BaseModel):
    answer: str
class Question(BaseModel):
    question: str

@bot.message_handler(commands=['start'])
def welcome(message):
    first_name = message.from_user.first_name
    bot.reply_to(message,f"{first_name}!, Welcome. Use /ask for asking question.", parse_mode='Markdown')

@bot.message_handler(commands=['ask'])
def handle_ask(message):
    try:
        question = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        bot.reply_to(message, 'please provide quesion after /ask command')
        return
    
    print(f'Question received from {message.from_user.first_name} with quesiton: {question}')
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        init_state = {'user_query': question}
        result = agent_run.invoke(init_state)
        answer = result.get('llm_response', 'Sorry, i could not process that in this time')
        bot.reply_to(message, answer)
    except Exception as e:
        print(f"❌ Error during agent invocation: {e}")
        bot.reply_to(message, "Sorry, I ran into an error while thinking.")

@app.get('/')
def root():
    return "Everything working fine"

@app.post(f'/{BOT_TOKEN}')
async def process_webhook(req: Request):
    try:
        # Decode the request body once and reuse it
        json_string = (await req.body()).decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response(status_code=200)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return Response(status_code=400)


@app.post('/ask', response_model=Answer)
def ask(req: Question):
    print(f"--- Received API request for question: {req.question} ---")
    init_state = {'user_query': req.question}
    result_state = agent_run.invoke(init_state)
    llm_answer = result_state['llm_response']
    # Explicitly create an instance of the Res model for the response
    return Answer(answer=llm_answer)