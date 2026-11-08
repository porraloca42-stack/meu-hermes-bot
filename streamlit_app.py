import os
import streamlit as strl
import threading
import json
import urllib.request
import re
import telebot
from groq import Groq

# Interface visual básica do Streamlit
strl.set_page_config(page_title="Hermes Agente", page_icon="🤖")
strl.title("🤖 Agente Hermes Avançado")
strl.success("O Hermes está online e pronto no Telegram!")

TELEGRAM_TOKEN = strl.secrets["TELEGRAM_TOKEN"]
GROQ_API_KEY = strl.secrets["GROQ_API_KEY"]

# Inicializa as conexões de API de forma segura
bot = telebot.TeleBot(TELEGRAM_TOKEN)
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

# Comandos do Telegram
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Fala mestre! O Hermes está online, conectado à internet e pronto para criar seus roteiros!")

@bot.message_handler(func=lambda message: True)
def responder_hermes(message):
    user_message = message.text
    system_prompt = "Você é o Hermes, um agente de IA de altíssimo nível. Se o usuário pedir dados atuais ou notícias recentes, use a ferramenta 'pesquisar_internet'."

    mensagens = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=mensagens,
        tools=FERRAMENTAS,
        tool_choice="auto"
    )
    response_message = response.choices.message
    
    if response_message.tool_calls:
        bot.send_message(message.chat.id, "🔍 Pesquisando dados atualizados na internet...")
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
                
                segunda_resposta = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=mensagens
                )
                bot.reply_to(message, segunda_resposta.choices.message.content)
                return

    bot.reply_to(message, response_message.content)

# SOLUÇÃO COMPLETA CONTRA O ERRO 409
# Usa o singleton nativo do Streamlit para travar a execução e nunca duplicar o bot
@strl.cache_resource
def iniciar_servico_do_bot():
    try:
        bot.remove_webhook()
    except:
        pass
    
    # Inicia o bot em uma Thread isolada e única do sistema
    threading.Thread(
        target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True), 
        daemon=True
    ).start()
    return True

iniciar_servico_do_bot()
