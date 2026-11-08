import os
import streamlit as strl
import telebot
from groq import Groq

# Interface visual básica do Streamlit
strl.set_page_config(page_title="Hermes Agente", page_icon="🤖")
strl.title("🤖 Agente Hermes Oficial")
strl.success("O Hermes está conectado e escutando seus comandos no Telegram!")

# Injeta as chaves direto do sistema
TELEGRAM_TOKEN = strl.secrets["TELEGRAM_TOKEN"]
GROQ_API_KEY = strl.secrets["GROQ_API_KEY"]

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Fala mestre! O Hermes está online e pronto para os roteiros!")

@bot.message_handler(func=lambda message: True)
def responder_hermes(message):
    user_message = message.text
    system_prompt = "Você é o Hermes, um agente de IA de altíssimo nível. Responda com foco em roteiros e produtividade."

    chat_completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    bot.reply_to(message, chat_completion.choices.message.content)

# Executa o polling direto no fluxo principal do Streamlit (Sem dar conflito de Thread)
if "bot_started" not in strl.session_state:
    strl.session_state["bot_started"] = True
    try:
        bot.remove_webhook()
        # Roda o bot de forma leve
        bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        strl.error(f"Erro ao iniciar conexão: {e}")
