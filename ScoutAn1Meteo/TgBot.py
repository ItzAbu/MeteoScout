import logging
import aiohttp
import mysql.connector
import asyncio
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

#bot token

token = ""


# Configura il logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurazione del database
db_config = {
    'user': '',
    'password': '',
    'host': '',
    'database': '',
    'port': 
}

# Set di admin (sostituisci con gli ID degli admin reali)
admins = {"C3 3c a9 13", "93 6e a6 13"}  # Esempio di ID degli admin



# Funzione per ottenere l'ultima lettura di temperatura e umidità
def get_last_sensor_data():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Ottieni l'ultimo record della tabella sensor_data
        cursor.execute("SELECT temperature, humidity, recorded_at FROM sensor_data ORDER BY id DESC LIMIT 1")
        last_data = cursor.fetchone()

        cursor.close()
        connection.close()

        return last_data if last_data else (None, None, None)  # Restituisce tre valori
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return None, None, None



# Funzione per ottenere la media degli ultimi 20 valori
def get_average_sensor_data():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Calcola la media degli ultimi 20 record
        cursor.execute("SELECT AVG(temperature), AVG(humidity) FROM (SELECT temperature, humidity FROM sensor_data ORDER BY id DESC LIMIT 20) AS subquery")
        avg_data = cursor.fetchone()

        cursor.close()
        connection.close()

        return avg_data if avg_data else (None, None)
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return None, None

# Funzione per ottenere gli ultimi 20 valori di temperatura e umidità
# Funzione per ottenere gli ultimi 20 valori di temperatura e umidità
def get_last_20_sensor_data():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Ottieni gli ultimi 20 record della tabella sensor_data
        cursor.execute("SELECT temperature, humidity, recorded_at FROM sensor_data ORDER BY id DESC LIMIT 20")
        last_20_data = cursor.fetchall()

        cursor.close()
        connection.close()

        return last_20_data if last_20_data else []
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return []
    
    
# Funzione per salvare la richiesta nel database
def save_access_request():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Inserisce una richiesta
        cursor.execute("INSERT INTO richieste (lettura) VALUES (TRUE)")
        connection.commit()

        request_id = cursor.lastrowid  # Ottieni l'ID dell'ultima richiesta
        cursor.close()
        connection.close()

        return request_id
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return None

# Funzione per controllare se ci sono richieste attive
def check_active_requests():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Controlla se ci sono richieste attive
        cursor.execute("SELECT * FROM richieste WHERE lettura = TRUE LIMIT 1")
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return result is not None
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return False

# Funzione per rimuovere la richiesta
def remove_request():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Rimuovi la richiesta
        cursor.execute("DELETE FROM richieste WHERE lettura = TRUE LIMIT 1")
        connection.commit()
        
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")

# Funzione per ottenere l'ultima risposta
def get_last_response():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Ottieni l'ultimo codice dalla tabella risposte
        cursor.execute("SELECT codice FROM risposte ORDER BY id DESC LIMIT 1")
        response = cursor.fetchone()

        cursor.close()
        connection.close()

        return response[0] if response else None
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")
        return None

# Funzione per rimuovere l'ultima risposta
def remove_last_response():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Rimuovi l'ultima risposta in base all'id
        cursor.execute("DELETE FROM risposte ORDER BY id DESC LIMIT 1")
        connection.commit()

        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        logger.error(f"Errore nella connessione al database: {err}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia un messaggio quando il comando /start viene emesso."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Accedi", callback_data="access_request")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
    f"Ciao {user.first_name}!\n"
    "Con questo bot avrai accesso al meteo in tempo reale e ai dati del sensore.\n"
    "Seleziona 'Accedi' per iniziare.\n"
    "L'accesso richiede che l'arduino sia acceso e che l'utente abbia la chiave RFID.",
    reply_markup=reply_markup,
    parse_mode='Markdown'  # Usa Markdown per il formato del messaggio
)


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


async def get_rain_status() -> str:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 43.6158,  # Coordinate di Ancona
            "longitude": 13.5186,
            "current": ["rain"],
            "timezone": "auto",
        }
        responses = openmeteo.weather_api(url, params=params)

        response = responses[0]
        current = response.Current()
        current_rain = current.Variables(0).Value()

        # Classificazione della pioggia
        if current_rain > 0:
            if current_rain < 2.5:
                rain_type = "Pioggia leggera"
            elif current_rain < 7.6:
                rain_type = "Pioggia moderata"
            else:
                rain_type = "Acquazzone"
        else:
            rain_type = "Nessuna pioggia attuale"

        return f"Quantità di pioggia: {current_rain} mm\nTipo di pioggia: {rain_type}"
    except Exception as e:
        logger.error(f"Errore durante il recupero delle informazioni sulla pioggia: {e}")
        return "Errore nel recupero delle informazioni sulla pioggia."
    
async def get_wind_info() -> str:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 43.6158,  # Coordinate di Ancona
            "longitude": 13.5186,
            "current": ["wind_speed_10m", "wind_direction_10m"],
            "timezone": "auto",
        }
        responses = openmeteo.weather_api(url, params=params)

        response = responses[0]
        current = response.Current()
        current_wind_speed_10m = current.Variables(0).Value()
        current_wind_direction_10m = current.Variables(1).Value()

        # Converti la velocità del vento in km/h
        wind_speed_kmh = current_wind_speed_10m * 3.6

        # Determina la direzione del vento
        if current_wind_direction_10m < 22.5 or current_wind_direction_10m >= 337.5:
            wind_direction = "Nord"
        elif 22.5 <= current_wind_direction_10m < 67.5:
            wind_direction = "Nord-Est"
        elif 67.5 <= current_wind_direction_10m < 112.5:
            wind_direction = "Est"
        elif 112.5 <= current_wind_direction_10m < 157.5:
            wind_direction = "Sud-Est"
        elif 157.5 <= current_wind_direction_10m < 202.5:
            wind_direction = "Sud"
        elif 202.5 <= current_wind_direction_10m < 247.5:
            wind_direction = "Sud-Ovest"
        elif 247.5 <= current_wind_direction_10m < 292.5:
            wind_direction = "Ovest"
        else:
            wind_direction = "Nord-Ovest"

        return f"Velocità del vento: {wind_speed_kmh:.2f} km/h\nDirezione del vento: {wind_direction}"
    except Exception as e:
        logger.error(f"Errore durante il recupero delle informazioni sul vento: {e}")
        return "Errore nel recupero delle informazioni sul vento."
    
    
async def rain_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    rain_status = await get_rain_status()  # Funzione per ottenere i dati sulla pioggia

    if rain_status:
        await query.message.reply_text(f"Informazioni sulla pioggia:\n{rain_status}")
    else:
        await query.message.reply_text("Nessuna informazione disponibile sulla pioggia.")

async def wind_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    wind_status = await get_wind_info()  # Funzione per ottenere i dati sul vento

    if wind_status:
        await query.message.reply_text(f"Informazioni sul vento:\n{wind_status}")
    else:
        await query.message.reply_text("Nessuna informazione disponibile sul vento.") 



# Funzione per gestire le callback dei pulsanti
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    

    if query.data == "access_request":
        request_id = save_access_request()  # Salva la richiesta nel database
        if request_id is not None:
            await query.edit_message_text(text=f"Richiesta inviata! ID: {request_id}. Posizionare la chiave sopra il lettore quando il led verde si accende. \n Il led Arancione indica che la chiave è stata letta correttamente.")
            await asyncio.sleep(30)

            response = get_last_response()
            remove_last_response()
            respone = response.replace(" ", "")

            if response is not None:
                if response in admins:
                    
                    
                    await query.message.reply_text(f"Risposta ricevuta: {response}")

                    # Mostra i pulsanti per temperatura e umidità
                    keyboard = [
                        [InlineKeyboardButton("Temperatura", callback_data="select_temperature")],
                        [InlineKeyboardButton("Umidità", callback_data="select_humidity")],
                        [InlineKeyboardButton("Pioggia", callback_data="get_rain")], 
                        [InlineKeyboardButton("Vento", callback_data="get_wind")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("Seleziona un'opzione:", reply_markup=reply_markup)
                    
                else:
                    await query.message.reply_text("Accesso negato, chiave sconosciuta. Chiave = " + response)
            else:
                await query.message.reply_text("Nessuna risposta disponibile.")
        else:
            await query.edit_message_text(text="Errore durante l'invio della richiesta.")

# Handler per la selezione della temperatura
async def select_temperature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    # Crea i nuovi pulsanti per le opzioni della temperatura
    keyboard = [
        [InlineKeyboardButton("Ultima Lettura", callback_data="temperature_last_value")],
        [InlineKeyboardButton("Media", callback_data="temperature_average")],
        [InlineKeyboardButton("Ultime 20 Letture", callback_data="temperature_last_20")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Temperatura - Seleziona un'opzione:", reply_markup=reply_markup)

# Handler per la selezione dell'umidità
async def select_humidity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    # Crea i nuovi pulsanti per le opzioni dell'umidità
    keyboard = [
        [InlineKeyboardButton("Ultima Lettura", callback_data="humidity_last_value")],
        [InlineKeyboardButton("Media", callback_data="humidity_average")],
        [InlineKeyboardButton("Ultime 20 Letture", callback_data="humidity_last_20")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Umidità - Seleziona un'opzione:", reply_markup=reply_markup)

# Funzione per tornare al menu principale (Temperatura/Umidità)
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    # Mostra i pulsanti per temperatura e umidità
    keyboard = [
        [InlineKeyboardButton("Temperatura", callback_data="select_temperature")],
        [InlineKeyboardButton("Umidità", callback_data="select_humidity")],
        [InlineKeyboardButton("Pioggia", callback_data="get_rain")], 
        [InlineKeyboardButton("Vento", callback_data="get_wind")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Seleziona un'opzione:", reply_markup=reply_markup)

# Handler per "Ultima Lettura" della temperatura
async def temperature_last_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_temp, last_hum, recorded_at = get_last_sensor_data()
    if last_temp is not None:
        await query.message.reply_text(f"L'ultimo valore della temperatura è: {last_temp} °C, registrato il {recorded_at}")
    else:
        await query.message.reply_text("Nessun dato disponibile per la temperatura.")

# Handler per "Media" della temperatura
async def temperature_average(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    avg_temp, _ = get_average_sensor_data()
    if avg_temp is not None:
        await query.message.reply_text(f"La media di tutti i valori della temperatura è: {avg_temp:.2f} °C")
    else:
        await query.message.reply_text("Nessun dato disponibile per la temperatura.")

# Handler per "Ultime 20 Letture" della temperatura
async def temperature_last_20(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_20_data = get_last_20_sensor_data()
    if last_20_data:
        # Correzione della chiamata a join
        last_20_temps = [f"{row[0]} °C - {row[2]}" for row in last_20_data]
        text = "Ultimi 20 valori di temperatura:\n" + "\n".join(last_20_temps)  # Corretta la sintassi di join
        await query.message.reply_text(text)
    else:
        await query.message.reply_text("Nessun dato disponibile per la temperatura.")


# Handler per "Ultima Lettura" dell'umidità
async def humidity_last_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_temp, last_hum, recorded_at = get_last_sensor_data()  # Modificato per aspettarsi solo due valori
    if last_hum is not None:
        # Qui devi ottenere 'recorded_at' dal database in un modo diverso
        await query.message.reply_text(f"L'ultimo valore dell'umidità è: {last_hum}% registrato il {recorded_at}")
    else:
        await query.message.reply_text("Nessun dato disponibile per l'umidità.")

# Handler per "Media" dell'umidità
async def humidity_average(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, avg_hum = get_average_sensor_data()
    if avg_hum is not None:
        await query.message.reply_text(f"La media di tutti i valori dell'umidità è: {avg_hum:.2f}%")
    else:
        await query.message.reply_text("Nessun dato disponibile per l'umidità.")

# Handler per "Ultime 20 Letture" dell'umidità
async def humidity_last_20(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_20_data = get_last_20_sensor_data()
    if last_20_data:
        # Corretta la chiamata a join per unire i dati in una stringa
        last_20_hums = [f"{row[1]}% - {row[2]}" for row in last_20_data]
        text = "Ultimi 20 valori di umidità:\n" + "\n".join(last_20_hums)  # Corretta la sintassi
        await query.message.reply_text(text)
    else:
        await query.message.reply_text("Nessun dato disponibile per l'umidità.")

# Funzione principale
def main() -> None:
    """Avvia il bot.""" 
    application = Application.builder().token(token).build()  # Sostituisci con il tuo token

    # Aggiungi gestori
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern="access_request"))
    # Aggiungi handler per selezione temperatura/umidità e loro opzioni
    application.add_handler(CallbackQueryHandler(select_temperature, pattern="select_temperature"))
    application.add_handler(CallbackQueryHandler(select_humidity, pattern="select_humidity"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="back_to_main"))

    # Aggiungi handler per i 6 bottoni (temperatura/umidità)
    application.add_handler(CallbackQueryHandler(temperature_last_value, pattern="temperature_last_value"))
    application.add_handler(CallbackQueryHandler(temperature_average, pattern="temperature_average"))
    application.add_handler(CallbackQueryHandler(temperature_last_20, pattern="temperature_last_20"))
    application.add_handler(CallbackQueryHandler(humidity_last_value, pattern="humidity_last_value"))
    application.add_handler(CallbackQueryHandler(humidity_average, pattern="humidity_average"))
    application.add_handler(CallbackQueryHandler(humidity_last_20, pattern="humidity_last_20"))
    
    application.add_handler(CallbackQueryHandler(rain_info, pattern='get_rain'))
    application.add_handler(CallbackQueryHandler(wind_info, pattern='get_wind'))
    



    # Esegui il bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()