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
       chrome_options.add_argument("--remote-debugging-port=9222")
       
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
       time.sleep(20)
       
       page_source = driver.page_source
       
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
       
       fees_value = None
       fee_keywords = ["Fees earned", "Fees"]
       
       for keyword in fee_keywords:
           if keyword in page_source:
               sections = page_source.split(keyword)
               if len(sections) > 1:
                   fees_section = sections[1][:1000]
                   print(f"✅ Seção '{keyword}' encontrada!")
                   
                   patterns = [r'(\d+[,.]?\d*)\s*US\$', r'(\d+[,.]\d+)\s*US\$', r'\$(\d+[,.]?\d*)', r'(\d+[,.]\d+)\s*USD']
                   
                   for pattern in patterns:
                       matches = re.findall(pattern, fees_section)
                       if matches:
                           try:
                               value_str = str(matches[0]).replace(',', '.')
                               fees_value = float(value_str)
                               print(f"💰 Valor das Fees: ${fees_value:.2f}")
                               return fees_value, range_status
                           except:
                               continue
       
       print("❌ Seções de fees não encontradas!")
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
    
    driver.quit()
