import requests
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime

# === CONFIGURACIÓN ===
token = '7776844365:AAFCUe2IqqkGjqwKlFRxFz5Ij2_DkK9QCQk'
chat_id = '-1002587355674'
chrome_driver_path = 'chromedriver.exe'  # o usa la ruta completa si hace falta
url_grafico = 'https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=5&theme=light'

# === GUARDAR PRECIO DE REFERENCIA ===
precio_referencia = None
ultima_actualizacion_referencia = None

# === UMBRALES ===
def calcular_umbral(precio_actual, precio_ref):
    margen = 0.05  # 5%
    umbral_compra = precio_ref * (1 - margen)
    umbral_venta = precio_ref * (1 + margen)
    return umbral_compra, umbral_venta

# === OBTENER PRECIO DE BTC ===
def obtener_precio_btc():
    api_key = '5ed10f2f2dad2ace60796e94a0d6c7fe87e21daa29bcc21b2d933c1a12c43c83'
    url = f'https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD&api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['USD']
    else:
        print("Error al obtener precio:", response.status_code, response.text)
        return None

# === CAPTURAR GRÁFICO TRADINGVIEW ===
def capturar_grafico():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,720')
    options.add_argument('--no-sandbox')

    if not os.path.exists(chrome_driver_path):
        raise FileNotFoundError(f"No se encontró chromedriver en: {chrome_driver_path}")

    driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
    driver.get(url_grafico)
    time.sleep(7)  # Espera a que cargue el gráfico

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_archivo = f'btc_chart_{timestamp}.png'
    driver.save_screenshot(nombre_archivo)
    driver.quit()
    return nombre_archivo

# === ENVIAR MENSAJE CON IMAGEN ===
def enviar_senal(mensaje, imagen_path):
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    with open(imagen_path, 'rb') as photo:
        files = {'photo': photo}
        data = {'chat_id': chat_id, 'caption': mensaje}
        response = requests.post(url, files=files, data=data)
    if response.status_code == 200:
        print("✅ Señal enviada al grupo.")
    else:
        print("❌ Error al enviar la señal:", response.text)

# === LÓGICA PRINCIPAL ===
def evaluar_y_enviar_senal():
    global precio_referencia, ultima_actualizacion_referencia
    
    precio_actual = obtener_precio_btc()
    if not precio_actual:
        return
    
    # Si es la primera ejecución o han pasado más de 24 horas, actualiza el precio de referencia
    ahora = datetime.now()
    if precio_referencia is None or ultima_actualizacion_referencia is None or \
       (ahora - ultima_actualizacion_referencia).total_seconds() > 86400:  # 24 horas
        precio_referencia = precio_actual
        ultima_actualizacion_referencia = ahora
        print(f"Precio de referencia actualizado: {precio_referencia} USD - {ahora}")
        return  # Esperamos a la siguiente iteración para evaluar
    
    umbral_compra, umbral_venta = calcular_umbral(precio_actual, precio_referencia)
    
    print(f"Precio actual: {precio_actual} USD")
    print(f"Precio referencia: {precio_referencia} USD")
    print(f"Umbral de compra: {umbral_compra} USD")
    print(f"Umbral de venta: {umbral_venta} USD")

    # Lógica de decisión
    if precio_actual < umbral_compra:
        decision = "🟢 Señal de trading: ¡Compra BTC ahora!"
    elif precio_actual > umbral_venta:
        decision = "🔴 Señal de trading: ¡Vende BTC ahora!"
    else:
        decision = "🟡 Señal de trading: Mantente en espera."

    # Captura de gráfico y envío de señal
    try:
        imagen = capturar_grafico()
        mensaje = f"{decision}\nPrecio actual: {precio_actual:.2f} USD\nPrecio referencia: {precio_referencia:.2f} USD"
        enviar_senal(mensaje, imagen)
        os.remove(imagen)  # Borra la imagen luego de enviarla
        
        # Si se ha generado una señal de compra o venta, actualizamos la referencia
        if decision.startswith("🟢") or decision.startswith("🔴"):
            precio_referencia = precio_actual
            ultima_actualizacion_referencia = ahora
            print(f"Precio de referencia actualizado tras señal: {precio_referencia} USD")
    except Exception as e:
        print("⚠️ Error al capturar o enviar imagen:", e)

# === EJECUCIÓN CADA 10 SEGUNDOS ===
if __name__ == '__main__':
    print("🤖 Bot de señales de trading iniciado")
    while True:
        evaluar_y_enviar_senal()
        time.sleep(10)  # Espera 10 segundos antes de ejecutar nuevamente