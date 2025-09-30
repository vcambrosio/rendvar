import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
import os, json, sys, shutil, traceback

# === CONFIG PADRÃO ===
CONFIG_FILE = "config.json"
BOT_TOKEN = '8341816244:AAE6GOR8-GZ2wDtt_MU1Fcq7bfo5TQNvLjg'
CHAT_ID = '18037748'

# === TELEGRAM ===
class TelegramBot:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send_message(self, text):
        try:
            r = requests.post(self.url, data={"chat_id": self.chat_id, "text": text}, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print("Erro Telegram:", e)
            return False

# === RSI ===
def calculate_rsi(prices, period=2):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    rs = last_gain / last_loss
    return round(100 - (100 / (1 + rs)), 2)

# === LEITURA RANKING (ATIVO;RSI;LD) ===
def load_ranking(file_path):
    ativos = []
    if not os.path.exists(file_path):
        return ativos
    with open(file_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(';')
            if len(parts) < 3: continue
            symbol = parts[0].strip().upper()
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            try:
                rsi_ref = float(parts[1].replace(',', '.'))
                ld_val = float(parts[2].replace(',', '.'))
                ativos.append((symbol, rsi_ref, ld_val))
            except:
                continue
    return ativos

# === ANÁLISE ===
def analyze_asset(symbol, rsi_ref, ld_val, sma_period, ema_period, rsi_period, hist_period):
    try:
        df = yf.Ticker(symbol).history(period=hist_period, interval="1d")
        if df.empty: return None
        closes = df["Close"].dropna()
        if len(closes) < sma_period: return None
        price = float(closes.iloc[-1])
        sma = closes.rolling(window=sma_period).mean().iloc[-1]
        ema = closes.ewm(span=ema_period, adjust=False).mean().iloc[-1]
        rsi = calculate_rsi(closes, rsi_period)
        if price <= sma or rsi >= rsi_ref: return None
        dist_to_ema = ((price - ema) / ema) * 100 if ema != 0 else None
        return {
            "symbol": symbol.replace(".SA", ""),
            "price": round(price,2),
            "ld": ld_val,
            "rsi": rsi,
            "rsi_ref": rsi_ref,
            "sma": round(sma,2),
            "ema": round(ema,2),
            "dist_to_ema": round(dist_to_ema,2) if dist_to_ema else None
        }
    except: return None

def run_rsi_from_config(config):
    ativos = load_ranking(config["ranking_file"])
    resultados = []
    for symbol, rsi_ref, ld in ativos:
        r = analyze_asset(symbol, rsi_ref, ld,
                          config["sma_period"], config["ema_period"],
                          config["rsi_period"], config["hist_period"])
        if r: resultados.append(r)
    if not resultados:
        return (
            "SETUP IFR2 \n"
            "Nenhum ativo passou nos filtros."
        )   
    resultados.sort(key=lambda x: x["ld"], reverse=True)
    top = resultados[:config["max_to_send"]]
    msg = f"SETUP RSI - TOP {len(top)}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    for r in top:
        dist = f"{r['dist_to_ema']:+.2f}%" if r['dist_to_ema'] is not None else "N/A"
        msg += f"{r['symbol']} | LD={r['ld']:.2f}\n"
        msg += f"RSI={r['rsi']} (<{r['rsi_ref']})\n"
        msg += f"Preço=R${r['price']:.2f}\nEMA{config['ema_period']}=R${r['ema']} ({dist})\nSMA{config['sma_period']}=R${r['sma']}\n────────────\n"
    return msg

# === COPIAR PARA SERVIDOR (CORRIGIDO) ===
def copy_to_server(server_path_ui, server_path_real):
    logs = []
    try:
        os.makedirs(server_path_ui, exist_ok=True)

        # === Código que será gerado no servidor ===
        server_code = f'''import yfinance as yf
import requests, json, os
from datetime import datetime

BASE_PATH = r"{server_path_real}"
CONFIG_FILE = os.path.join(BASE_PATH, "config.json")
RANKING_FILE = os.path.join(BASE_PATH, "ranking_last.txt")

BOT_TOKEN = "{BOT_TOKEN}"
CHAT_ID = "{CHAT_ID}"

class TelegramBot:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{{token}}/sendMessage"
        self.chat_id = chat_id
    def send_message(self, text):
        try:
            r = requests.post(self.url, data={{"chat_id": self.chat_id, "text": text}}, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print("Erro Telegram:", e)
            return False

def calculate_rsi(prices, period=2):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    rs = last_gain / last_loss
    return round(100 - (100 / (1 + rs)), 2)

def load_ranking(file_path=RANKING_FILE):
    ativos = []
    if not os.path.exists(file_path):
        return ativos
    with open(file_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(';')
            if len(parts) < 3: continue
            symbol = parts[0].strip().upper()
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            try:
                rsi_ref = float(parts[1].replace(',', '.'))
                ld_val = float(parts[2].replace(',', '.'))
                ativos.append((symbol, rsi_ref, ld_val))
            except:
                continue
    return ativos

def analyze_asset(symbol, rsi_ref, ld_val, sma_period, ema_period, rsi_period, hist_period):
    try:
        df = yf.Ticker(symbol).history(period=hist_period, interval="1d")
        if df.empty: return None
        closes = df["Close"].dropna()
        if len(closes) < sma_period: return None
        price = float(closes.iloc[-1])
        sma = closes.rolling(window=sma_period).mean().iloc[-1]
        ema = closes.ewm(span=ema_period, adjust=False).mean().iloc[-1]
        rsi = calculate_rsi(closes, rsi_period)
        if price <= sma or rsi >= rsi_ref: return None
        dist_to_ema = ((price - ema) / ema) * 100 if ema != 0 else None
        return {{
            "symbol": symbol.replace(".SA", ""),
            "price": round(price,2),
            "ld": ld_val,
            "rsi": rsi,
            "rsi_ref": rsi_ref,
            "sma": round(sma,2),
            "ema": round(ema,2),
            "dist_to_ema": round(dist_to_ema,2) if dist_to_ema else None
        }}
    except:
        return None

def run_rsi_from_config(config):
    ativos = load_ranking()
    resultados = []
    for symbol, rsi_ref, ld in ativos:
        r = analyze_asset(symbol, rsi_ref, ld,
                          config["sma_period"], config["ema_period"],
                          config["rsi_period"], config["hist_period"])
        if r: resultados.append(r)
    if not resultados:
        return (
            "SETUP IFR2 \\n"
            "Nenhum ativo passou nos filtros."
        )   

    resultados.sort(key=lambda x: x["ld"], reverse=True)
    top = resultados[:config["max_to_send"]]
    msg = f"SETUP RSI - TOP {{len(top)}}\\nData: {{datetime.now().strftime('%d/%m/%Y %H:%M')}}\\n\\n"
    for r in top:
        dist = f"{{r['dist_to_ema']:+.2f}}%" if r['dist_to_ema'] is not None else "N/A"
        msg += f"{{r['symbol']}} | LD={{r['ld']:.2f}}\\n"
        msg += f"RSI={{r['rsi']}} (<{{r['rsi_ref']}})\\n"
        msg += f"Preço=R${{r['price']:.2f}}\\nEMA{{config['ema_period']}}=R${{r['ema']}} ({{dist}})\\nSMA{{config['sma_period']}}=R${{r['sma']}}\\n────────────\\n"
    return msg

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print("Configuração não encontrada!")
    else:
        with open(CONFIG_FILE,"r") as f: cfg=json.load(f)
        msg = run_rsi_from_config(cfg)
        print(msg)
        ok = TelegramBot(BOT_TOKEN,CHAT_ID).send_message(msg)
        print("Mensagem enviada!" if ok else "Falha ao enviar.")
'''

        # === Salvar app_rsi.py no servidor ===
        dest_main = os.path.join(server_path_ui, "app_rsi.py")
        with open(dest_main, "w", encoding="utf-8") as f:
            f.write(server_code)
        logs.append(f"Gerado app_rsi.py em {dest_main}")

        # === Copiar config.json e ranking_last.txt da raiz do projeto ===
        script_dir = os.path.dirname(os.path.abspath(__file__))  # ...\rendvar\pages
        base_dir = os.path.dirname(script_dir)  # sobe 1 nível -> ...\rendvar

        for extra in ["config.json", "ranking_last.txt"]:
            src = os.path.join(base_dir, extra)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(server_path_ui, extra))
                logs.append(f"{extra} copiado para {server_path_ui}")
            else:
                logs.append(f"⚠️ Arquivo {extra} não encontrado em {src}")

        logs.append("Conteúdo destino (Samba): " + ", ".join(os.listdir(server_path_ui)))
        return "\n".join(logs)

    except Exception as e:
        return f"Erro ao copiar: {e}\n" + traceback.format_exc()


# === STREAMLIT (MANTIDO ORIGINAL) ===
st.title("📊 RSI Bot - Configurações")

uploaded_file = st.file_uploader("Ranking (ATIVO;RSI;LD)", type="txt")
if uploaded_file:
    with open("ranking_last.txt", "wb") as f: f.write(uploaded_file.read())
    st.success("Arquivo salvo como ranking_last.txt")

sma_period = st.number_input("SMA", 50, 300, 200, 1)
ema_period = st.number_input("EMA", 5, 50, 21, 1)
rsi_period = st.number_input("RSI", 2, 20, 2, 1)
hist_period = st.selectbox("Histórico", ["120d","180d","360d"], index=2)
max_to_send = st.slider("Qtd máx ativos", 1, 10, 5)

if st.button("💾 Salvar Configuração RSI"):
    cfg = {
        "ranking_file":"ranking_last.txt",
        "sma_period":sma_period,
        "ema_period":ema_period,
        "rsi_period":rsi_period,
        "hist_period":hist_period,
        "max_to_send":max_to_send
    }
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f)
    st.success("Configuração salva.")

if st.button("▶️ Executar RSI Agora"):
    if not os.path.exists(CONFIG_FILE):
        st.warning("Salve a configuração primeiro.")
    else:
        with open(CONFIG_FILE,"r") as f: cfg=json.load(f)
        msg = run_rsi_from_config(cfg)
        st.text_area("Mensagem RSI", msg, height=300)
        ok = TelegramBot(BOT_TOKEN,CHAT_ID).send_message(msg)
        st.success("Mensagem enviada!" if ok else "Falha ao enviar.")

st.subheader("📂 Copiar para Servidor")

# Caminho que você enxerga pelo Samba (ex.: H:\codigos\telegram_bots)
server_path_ui = st.text_input("Pasta servidor mapeado no Samba", r"H:\codigos\telegram_bots")

# Caminho real no Linux onde o cron vai rodar (ex.: /mnt/dados/codigos/telegram_bots)
server_path_real = st.text_input("Pasta servidor (Linux)-usado para rodar o crond", "/mnt/dados/codigos/telegram_bots")

if st.button("📂 Copiar app_rsi.py para Servidor"):
    st.code(copy_to_server(server_path_ui, server_path_real))
