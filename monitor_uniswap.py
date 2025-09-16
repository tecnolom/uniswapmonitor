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
UNISWAP_URL = "https://app.uniswap.org/positions/v3/ethereum/1085465"

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
       time.sleep(30)
       
       page_source = driver.page_source
       print(f"Página carregada: {len(page_source)} caracteres")
       
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
       
       # PROCURAR ESPECIFICAMENTE "Fees earned"
       fees_value = None
       
       if "Fees earned" in page_source:
           print("✅ 'Fees earned' encontrado!")
           sections = page_source.split('Fees earned')
           if len(sections) > 1:
               fees_section = sections[1][:1000]
               print("Procurando valor na seção Fees earned...")
               
               patterns = [r'(\d+[,.]?\d*)\s*US\$', r'(\d+[,.]\d+)\s*US\$', r'\$(\d+[,.]?\d*)', r'(\d+[,.]\d+)\s*USD']
               
               for pattern in patterns:
                   matches = re.findall(pattern, fees_section)
                   if matches:
                       try:
                           value_str = str(matches[0]).replace(',', '.')
                           fees_value = float(value_str)
                           print(f"💰 Fees earned: ${fees_value:.2f}")
                           break
                       except:
                           continue
       
       # Se não encontrou "Fees earned", tentar outras variações
       if fees_value is None:
           print("❌ 'Fees earned' não encontrado, tentando outras variações...")
           
           # Salvar página em arquivo para debug
           with open('/tmp/debug_page.html', 'w') as f:
               f.write(page_source)
           
           # Procurar por contexto próximo a valores em dólar
           all_fees_contexts = []
           for match in re.finditer(r'(\d+[,.]?\d*)\s*US\$', page_source):
               start = max(0, match.start() - 200)
               end = min(len(page_source), match.end() + 200)
               context = page_source[start:end]
               value = float(match.group(1).replace(',', '.'))
               all_fees_contexts.append((value, context))
           
           print(f"Encontrados {len(all_fees_contexts)} valores com contexto")
           
           # Procurar o contexto que contém "fees" ou "earned"
           for value, context in all_fees_contexts:
               if any(word in context.lower() for word in ['fees', 'earned', 'fee']):
                   print(f"🎯 Valor com contexto de fees: ${value:.2f}")
                   fees_value = value
                   break
       
       if fees_value is None:
           print("❌ FALHA CRÍTICA: Não encontrou Fees earned!")
           # Enviar debug
           debug_msg = f"🚨 <b>ERRO GitHub Actions</b>\n\nNão conseguiu encontrar 'Fees earned'\nPágina tem {len(page_source)} chars\nStatus: {range_status}"
           send_telegram_message(debug_msg)
       
       return fees_value, range_status
           
   except Exception as e:
       print(f"Erro: {e}")
       return None, "Status desconhecido"

# Executar verificação
driver = setup_driver()
if driver:
    fees_value, range_status = get_fees_and_range_status(driver)
    
    if fees_value:
        message = f"🦄 <b>Alerta de Ganhos...</b>\n\n"
        message += f"💵 Total disponível para coleta: <b>${fees_value:.2f}</b>\n\n"
        
        if "🟢" in range_status:
            message += f"🟢 Pool Status: Dentro do Range"
        elif "🔴" in range_status:
            message += f"🔴 Pool Status: Fora do Range"
        else:
            message += f"Pool Status: {range_status}"
        
        send_telegram_message(message)
        print(f"✅ Fees earned enviado: ${fees_value:.2f}")
    
    driver.quit()
