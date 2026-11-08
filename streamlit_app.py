import os
import streamlit as strl

# Garante a injeção correta das chaves no sistema operacional
if "TELEGRAM_TOKEN" not in os.environ:
    os.environ["TELEGRAM_TOKEN"] = strl.secrets["TELEGRAM_TOKEN"]
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = strl.secrets["GROQ_API_KEY"]

import threading
import json
import urllib.request
import re
import telebot
from groq import Groq

# Interface visual do Streamlit
strl.set_page_config(page_title="Hermes Agente", page_icon="🤖")
strl.title("🤖 Agente Hermes Avançado")
strl.success("O Hermes está ativo e rodando de forma estável no Telegram!")

# Inicializa o bot usando a variável de ambiente limpa
bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

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

# FUNÇÃO QUE RESOLVE O CONFLITO 401 DE SESSÃO
def rodar_polling_limpo():
    try:
        # Força o Telegram a derrubar qualquer outra conexão fantasma aberta com esse token
        bot.remove_webhook()
    except:
        pass
    
    # Inicia a escuta de mensagens limpando erros anteriores
    bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)

def iniciar_bot_com_trava():
    for thread in threading.enumerate():
        if thread.name == "HermesTelegramThread":
            return
            
    nova_thread = threading.Thread(target=rodar_polling_limpo, daemon=True)
    nova_thread.name = "HermesTelegramThread"
    nova_thread.start()

iniciar_bot_com_trava()
