import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
import os, json, sys, shutil, traceback

# === CONFIG PADRÃO ===
CONFIG_FILE = "config_fundo.json"
BOT_TOKEN = '8341816244:AAE6GOR8-GZ2wDtt_MU1Fcq7bfo5TQNvLjg'
CHAT_ID = '18037748'

class TelegramBot:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
    def send_message(self, text):
        try:
            r=requests.post(self.url,data={"chat_id":self.chat_id,"text":text},timeout=10)
            return r.status_code==200
        except: return False

# === LOAD TICKERS (ATIVO;LD) ===
def load_tickers(file_path):
    ativos=[]
    if not os.path.exists(file_path): return ativos
    with open(file_path,'r',encoding='utf-8') as f:
        for raw in f:
            line=raw.strip()
            if not line or line.startswith('#'): continue
            parts=line.split(';')
            symbol=parts[0].strip().upper()
            if not symbol.endswith('.SA'): symbol+=".SA"
            ld_val=float(parts[1].replace(',','.')) if len(parts)>1 else None
            ativos.append((symbol,ld_val))
    return ativos

def analyze_fundo(symbol, ld_val=None, ema_fast=8, ema_slow=80, usar_filtro=True, hist_period="120d"):
    try:
        df=yf.Ticker(symbol).history(period=hist_period,interval="1d")
        if df.empty or len(df)<6: return None
        lows,highs,closes=df["Low"],df["High"],df["Close"]
        min_aa,min_a,min_c=float(lows.iloc[-3]),float(lows.iloc[-2]),float(lows.iloc[-1])
        if not(min_c>min_a and min_a<min_aa): return None
        entrada=float(highs.iloc[-1]); stop=min_a; amp=entrada-stop
        if amp<=0: return None
        alvo=entrada+2*amp
        if usar_filtro:
            if len(closes)<ema_slow+2: return None
            emaf=closes.ewm(span=ema_fast).mean(); emas=closes.ewm(span=ema_slow).mean()
            if not(emaf.iloc[-1]>emas.iloc[-1] and emaf.iloc[-1]>emaf.iloc[-2] and emas.iloc[-1]>emas.iloc[-2]): return None
        return {"symbol":symbol.replace(".SA",""),"entrada":round(entrada,2),"stop":round(stop,2),
                "alvo":round(alvo,2),"amplitude":round(amp,2),"ld":ld_val}
    except: return None

def moeda(valor):
    """Formata um número como moeda brasileira."""
    return f"R${valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def run_bot(config):
    ativos = load_tickers(config["ranking_file"])
    resultados = [analyze_fundo(s, ld, config["ema_fast"], config["ema_slow"], 
                                config["usar_filtro"], config["hist_period"])
                  for s, ld in ativos]
    resultados = [r for r in resultados if r]
    
    msg = (
        f"📈 Setup 123 Compra\n"
        f"Filtro EMAs: {'Ativado' if config['usar_filtro'] else 'Desativado'}\n"
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    )
    
    if not resultados:
        return msg + "Nenhum ativo."
    
    for r in resultados:
        msg += (
            f"{r['symbol']} | LD={r['ld'] if r['ld'] else 'N/A'}\n"
            f"Entrada={moeda(r['entrada'])}\n"
            f"Stop={moeda(r['stop'])}\n"
            f"Alvo={moeda(r['alvo'])} (2x ampl={moeda(2*r['amplitude'])})\n"
            "─────────────\n"
        )
    
    return msg

# === COPIAR PARA SERVIDOR (VERSÃO MODIFICADA) ===
def copy_to_server(server_path_ui, server_path_real):
    logs = []
    try:
        os.makedirs(server_path_ui, exist_ok=True)

        # === Código que será gerado no servidor ===
        server_code = f'''import yfinance as yf
import requests, json, os
from datetime import datetime

# Caminho base no servidor (usado pelo cron no Linux)
BASE_PATH = r"{server_path_real}"
CONFIG_FILE = os.path.join(BASE_PATH, "config_fundo.json")
RANKING_FILE = os.path.join(BASE_PATH, "ranking_fundo.txt")

BOT_TOKEN = "{BOT_TOKEN}"
CHAT_ID = "{CHAT_ID}"

class TelegramBot:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{{token}}/sendMessage"
        self.chat_id = chat_id
    def send_message(self, text):
        try:
            r=requests.post(self.url,data={{"chat_id":self.chat_id,"text":text}},timeout=10)
            return r.status_code==200
        except: return False

def load_tickers(file_path=RANKING_FILE):
    ativos=[]
    if not os.path.exists(file_path): return ativos
    with open(file_path,'r',encoding='utf-8') as f:
        for raw in f:
            line=raw.strip()
            if not line or line.startswith('#'): continue
            parts=line.split(';')
            symbol=parts[0].strip().upper()
            if not symbol.endswith('.SA'): symbol+=".SA"
            ld_val=float(parts[1].replace(',','.')) if len(parts)>1 else None
            ativos.append((symbol,ld_val))
    return ativos

def analyze_fundo(symbol, ld_val=None, ema_fast=8, ema_slow=80, usar_filtro=True, hist_period="120d"):
    try:
        df=yf.Ticker(symbol).history(period=hist_period,interval="1d")
        if df.empty or len(df)<6: return None
        lows,highs,closes=df["Low"],df["High"],df["Close"]
        min_aa,min_a,min_c=float(lows.iloc[-3]),float(lows.iloc[-2]),float(lows.iloc[-1])
        if not(min_c>min_a and min_a<min_aa): return None
        entrada=float(highs.iloc[-1]); stop=min_a; amp=entrada-stop
        if amp<=0: return None
        alvo=entrada+2*amp
        if usar_filtro:
            if len(closes)<ema_slow+2: return None
            emaf=closes.ewm(span=ema_fast).mean(); emas=closes.ewm(span=ema_slow).mean()
            if not(emaf.iloc[-1]>emas.iloc[-1] and emaf.iloc[-1]>emaf.iloc[-2] and emas.iloc[-1]>emas.iloc[-2]): return None
        return {{"symbol":symbol.replace(".SA",""),"entrada":round(entrada,2),"stop":round(stop,2),
                "alvo":round(alvo,2),"amplitude":round(amp,2),"ld":ld_val}}
    except: return None

def moeda(valor):
    return f"R${{valor:,.2f}}".replace(',', 'X').replace('.', ',').replace('X', '.')

def run_bot(config):
    ativos = load_tickers()
    resultados = [analyze_fundo(s, ld, config["ema_fast"], config["ema_slow"], 
                                config["usar_filtro"], config["hist_period"])
                  for s, ld in ativos]
    resultados = [r for r in resultados if r]
    
    msg = (
        f"📈 Setup 123 Compra\\n"
        f"Filtro EMAs: {{'Ativado' if config['usar_filtro'] else 'Desativado'}}\\n"
        f"Data: {{datetime.now().strftime('%d/%m/%Y %H:%M')}}\\n\\n"
    )
    
    if not resultados:
        return msg + "Nenhum ativo."
    
    for r in resultados:
        msg += (
            f"{{r['symbol']}} | LD={{r['ld'] if r['ld'] else 'N/A'}}\\n"
            f"Entrada={{moeda(r['entrada'])}}\\n"
            f"Stop={{moeda(r['stop'])}}\\n"
            f"Alvo={{moeda(r['alvo'])}} (2x ampl={{moeda(2*r['amplitude'])}})\\n"
            "─────────────\\n"
        )
    
    return msg

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print("Configuração não encontrada!")
    else:
        with open(CONFIG_FILE,"r") as f: cfg=json.load(f)
        msg=run_bot(cfg)
        print(msg)
        ok=TelegramBot(BOT_TOKEN,CHAT_ID).send_message(msg)
        print("Mensagem enviada!" if ok else "Falha ao enviar.")
'''

        # === Salvar app_fundo.py no servidor (Samba) ===
        dest_main = os.path.join(server_path_ui, "app_fundo.py")
        with open(dest_main, "w", encoding="utf-8") as f:
            f.write(server_code)
        logs.append(f"Gerado app_fundo.py em {dest_main}")

        # Copiar também os arquivos auxiliares
        for extra in ["config_fundo.json", "ranking_fundo.txt"]:
            if os.path.exists(extra):
                shutil.copy2(extra, os.path.join(server_path_ui, extra))
                logs.append(f"{extra} copiado para {server_path_ui}")
            else:
                logs.append(f"⚠️ Arquivo {extra} não encontrado no diretório local.")

        logs.append("Conteúdo destino (Samba): " + ", ".join(os.listdir(server_path_ui)))
        return "\n".join(logs)

    except Exception as e:
        return f"Erro ao copiar: {e}\n" + traceback.format_exc()


# === STREAMLIT ===
st.title("📊 Setup 123 Compra - Configurações")

uploaded_file=st.file_uploader("Ranking (ATIVO;LD ou ATIVO)",type="txt")
if uploaded_file:
    with open("ranking_fundo.txt","wb") as f:f.write(uploaded_file.read())
    st.success("Arquivo salvo como ranking_fundo.txt")

ema_fast=st.number_input("EMA rápida",3,30,8,1)
ema_slow=st.number_input("EMA lenta",20,200,80,1)
usar_filtro=st.checkbox("Ativar filtro de EMAs",True)
hist_period=st.selectbox("Histórico",["360d","720d","1080d","1800d","3600d"],index=2)

if st.button("💾 Salvar Configuração 123 Compra"):
    cfg={"ranking_file":"ranking_fundo.txt","ema_fast":ema_fast,"ema_slow":ema_slow,"usar_filtro":usar_filtro,"hist_period":hist_period}
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f)
    st.success("Configuração salva.")

if st.button("▶️ Executar setup 123 Compra agora"):
    if not os.path.exists(CONFIG_FILE): st.warning("Salve config primeiro.")
    else:
        with open(CONFIG_FILE,"r") as f: cfg=json.load(f)
        msg=run_bot(cfg)
        st.text_area("Mensagem 123 Compra",msg,height=300)
        ok=TelegramBot(BOT_TOKEN,CHAT_ID).send_message(msg)
        st.success("Mensagem enviada!" if ok else "Falha ao enviar.")

st.subheader("📂 Copiar para Servidor")

# Caminho Samba (visível pela sua máquina)
server_path_ui = st.text_input("Pasta servidor (Samba)", r"H:\codigos\telegram_bots")

# Caminho real no Linux (usado no cron)
server_path_real = st.text_input("Pasta servidor (Linux)", "/mnt/dados/codigos/telegram_bots")

if st.button("📂 Copiar bot 123 Compra para Servidor"):
    st.code(copy_to_server(server_path_ui, server_path_real))
