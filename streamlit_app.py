import os
import streamlit as strl
import threading
import asyncio
import json
import urllib.request
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Interface visual do Streamlit (obrigatória para o servidor grátis)
strl.set_page_config(page_title="Hermes Agente", page_icon="🤖")
strl.title("🤖 Agente Hermes")
strl.success("O Hermes está online e pronto no Telegram!")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# FUNÇÃO NATIVA DE PESQUISA NA WEB
def pesquisar_internet(query: str) -> str:
    try:
        query_formata = urllib.parse.quote_plus(query)
        url = f"https://duckduckgo.com{query_formata}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
        links = re.findall(r'<a class="result__url"[^>]*>([^<]+)</a>', html)[:3]
        snippets = re.findall(r'<td class="result__snippet">([^<]+)</td>', html)[:3]
        if not snippets:
            return "Nenhum resultado recente encontrado."
        texto_resultado = ""
        for i in range(len(snippets)):
            link_txt = links[i].strip() if i < len(links) else "Link indisponível"
            texto_resultado += f"Fonte {i+1}: {link_txt}\nResumo: {snippets[i].strip()}\n\n"
        return texto_resultado
    except Exception as e:
        return f"Erro ao acessar os dados da internet: {str(e)}"

FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_internet",
            "description": "Use esta ferramenta para buscar informações em tempo real na internet sobre notícias recentes ou dados atuais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "O termo de busca para pesquisar na internet."}
                },
                "required": ["query"],
            },
        },
    }
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fala mestre! Estou online, conectado à internet e pronto para seus roteiros!")

async def responder_hermes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    system_prompt = "Você é o Hermes, um agente de IA de altíssimo nível. Se o usuário pedir dados atuais ou notícias que você não sabe, use a ferramenta 'pesquisar_internet'."

    mensagens = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, 
        lambda: groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=mensagens,
            tools=FERRAMENTAS,
            tool_choice="auto"
        )
    )
    
    response_message = response.choices.message
    
    if response_message.tool_calls:
        await update.message.reply_text("🔍 Pesquisando dados atualizados na internet...")
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "pesquisar_internet":
                argumentos = json.loads(tool_call.function.arguments)
                resultado_busca = pesquisar_internet(argumentos.get("query"))
                
                mensagens.append(response_message)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": "pesquisar_internet",
                    "content": resultado_busca
                })
                
                segunda_resposta = await loop.run_in_executor(
                    None,
                    lambda: groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=mensagens
                    )
                )
                await update.message.reply_text(segunda_resposta.choices.message.content)
                return

    await update.message.reply_text(response_message.content)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_hermes))
    
    # Mantém o bot escutando os eventos sem dar erro de sinal do Linux
    application.run_polling(close_loop=False, close_loop_signum=None)

# Garante a inicialização única do bot em segundo plano
if "bot_started" not in strl.session_state:
    strl.session_state["bot_started"] = True
    threading.Thread(target=run_bot, daemon=True).start()
