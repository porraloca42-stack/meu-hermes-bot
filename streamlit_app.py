import os
import streamlit as strl
import threading
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Interface simples do Streamlit
strl.set_page_config(page_title="Hermes Bot", page_icon="🤖")
strl.title("🤖 Status do Agente Hermes")
strl.success("O seu bot do Telegram está ativo e rodando em segundo plano!")
strl.write("Pode mandar mensagens e comandos direto no Telegram que o Hermes vai responder.")

# Pegar as chaves salvas no painel do Streamlit
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fala mestre! O Hermes está online e pronto para os roteiros!")

async def responder_hermes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    system_prompt = (
        "Você é o Hermes, um agente de IA altamente inteligente e focado em produtividade. "
        "Sua especialidade é criar roteiros fantásticos, estruturar ideias e executar comandos com precisão lógica."
    )

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        model="llama-3.1-8b-instant", 
    )
    await update.message.reply_text(chat_completion.choices.message.content)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_hermes))
    
    application.run_polling()

# Garante que o bot só inicia uma vez por inicialização do servidor
if "bot_started" not in strl.session_state:
    strl.session_state["bot_started"] = True
    threading.Thread(target=run_bot, daemon=True).start()
