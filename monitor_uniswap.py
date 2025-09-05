#!/usr/bin/env python3
import requests
import time
from datetime import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_IDS = [os.environ.get('CHAT_ID1'), os.environ.get('CHAT_ID2')]
UNISWAP_URL = "https://app.uniswap.org/positions/v3/ethereum/1071249"

def send_telegram_message(message):
   try:
       url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
       for chat_id in CHAT_IDS:
           data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
           requests.post(url, json=data, timeout=10)
       return True
   except:
       return False

def setup_driver():
   try:
       chrome_options = Options()
       chrome_options.add_argument("--headless")
       chrome_options.add_argument("--no-sandbox")
       chrome_options.add_argument("--disable-dev-shm-usage")
       chrome_options.add_argument("--disable-gpu")
       chrome_options.add_argument("--window-size=1920,1080")
       chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
       
       service = Service(ChromeDriverManager().install())
       driver = webdriver.Chrome(service=service, options=chrome_options)
       return driver
   except Exception as e:
       print(f"Erro: {e}")
       return None

def get_fees_and_range_status(driver):
   try:
       print("Acessando Uniswap...")
       driver.get(UNISWAP_URL)
       time.sleep(30)  # Mais tempo para carregar
       
       page_source = driver.page_source
       print(f"Página carregada: {len(page_source)} caracteres")
       
       # Debug: procurar por "fees" em geral
       fees_count = page_source.lower().count('fees')
       print(f"Palavra 'fees' encontrada {fees_count} vezes")
       
       range_status = "Status desconhecido"
       page_lower = page_source.lower()
       
       if "out of range" in page_lower:
           range_status = "🔴 Fora do Range"
       elif "in range" in page_lower:
           range_status = "🟢 Dentro do Range"
       elif "earning" in page_lower and "not earning" not in page_lower:
           range_status = "🟢 Dentro do Range"
       elif "not earning" in page_lower:
           range_status = "🔴 Fora do Range"
       
       print(f"Status do Range: {range_status}")
       
       # BUSCA MAIS AGRESSIVA - procurar TODOS os valores em dólar
       print("🔍 Procurando TODOS os valores em dólar...")
       patterns = [r'(\d+[,.]?\d*)\s*US\$', r'(\d+[,.]\d+)\s*US\$', r'\$(\d+[,.]?\d*)', r'(\d+[,.]\d+)\s*USD']
       found_values = []
       
       for pattern in patterns:
           matches = re.findall(pattern, page_source)
           for match in matches:
               try:
                   value = float(str(match).replace(',', '.'))
                   if 10 <= value <= 1000:  # Range para fees típicas
                       found_values.append(value)
               except:
                   continue
       
       if found_values:
           unique_values = sorted(list(set(found_values)), reverse=True)
           print(f"💰 Valores encontrados: {[f'${v:.2f}' for v in unique_values[:10]]}")
           
           # Estratégia: pegar o valor que mais faz sentido para fees
           # Procurar valor próximo ao range esperado (30-60)
           best_candidate = None
           for value in unique_values:
               if 25 <= value <= 100:  # Range típico de fees
                   best_candidate = value
                   break
           
           if not best_candidate and unique_values:
               best_candidate = unique_values[0]  # Fallback
           
           if best_candidate:
               print(f"✅ Valor selecionado: ${best_candidate:.2f}")
               return best_candidate, range_status
       
       print("❌ Nenhum valor válido encontrado")
       return None, range_status
           
   except Exception as e:
       print(f"Erro: {e}")
       return None, "Status desconhecido"

# Executar verificação
driver = setup_driver()
if driver:
    fees_value, range_status = get_fees_and_range_status(driver)
    
    if fees_value:
        message = f"🦄 <b>Monitor Uniswap - GitHub Actions</b>\n\n"
        message += f"💵 Total disponível: <b>${fees_value:.2f}</b>\n"
        
        if "🟢" in range_status:
            message += f"🟢 Pool Status: Dentro do Range"
        elif "🔴" in range_status:
            message += f"🔴 Pool Status: Fora do Range"
        else:
            message += f"Pool Status: {range_status}"
        
        send_telegram_message(message)
        print(f"✅ Verificação enviada: ${fees_value:.2f}")
    else:
        # Se não encontrou, enviar debug
        debug_msg = f"🔧 <b>Debug GitHub Actions</b>\n\nNão conseguiu encontrar valores de fees.\nStatus: {range_status}"
        send_telegram_message(debug_msg)
        print("❌ Enviado debug para Telegram")
    
    driver.quit()
