#include <WiFiNINA.h>
#include <DHT.h>
#include <SPI.h>
#include <MFRC522.h> // Libreria per il lettore RFID

// Dati del sensore DHT
#define DHTPIN 6      // Pin a cui è collegato il DHT
#define DHTTYPE DHT11 // Cambia a DHT22 se usi un DHT22
DHT dht(DHTPIN, DHTTYPE);

const char* ssid = "";        // Sostituisci con il tuo SSID
const char* password = ""; // Sostituisci con la tua password Wi-Fi

// Dati del server MySQL
const char* server = ""; // URL del tuo script PHP

// Pin LED
#define LED_PIN 2 // Pin a cui è collegato il LED
bool ledState = false; // Stato del LED

// Definizione dei pin per il lettore RFID
#define RST_PIN 7   // Pin di reset
#define SS_PIN 11   // Pin di selezione dello slave
MFRC522 rfid(SS_PIN, RST_PIN); // Crea un'istanza dell'oggetto MFRC522

// Timer per il salvataggio dei dati
unsigned long previousMillis = 0; // Salva il tempo dell'ultima lettura
const long interval = 100000; // 100 secondi in millisecondi

// Funzione per inviare una risposta al server
void sendResponse(String response, String requestId) {
    WiFiClient client;
    if (client.connect(server, 80)) {
        String postData = "response=" + response + "&id_richiesta=" + requestId;

        client.println("POST /arduino_project/response.php HTTP/1.1");
        client.println("Host: " + String(server));
        client.println("Content-Type: application/x-www-form-urlencoded");
        client.print("Content-Length: ");
        client.println(postData.length());
        client.println();
        client.print(postData);

        // Aspetta una risposta dal server
        while (client.connected() || client.available()) {
            if (client.available()) {
                String line = client.readStringUntil('\n');
                Serial.println(line); // Stampa la risposta del server
            }
        }
        client.stop(); // Ferma la connessione
    } else {
        Serial.println("Connessione al server fallita");
    }
}

// Funzione per controllare le richieste
void checkRequests() {
    WiFiClient client;
    if (client.connect(server, 80)) {
        client.println("GET /arduino_project/check_requests.php HTTP/1.1");
        client.println("Host: " + String(server));
        client.println("Connection: close");
        client.println();

        unsigned long startMillis = millis(); // Inizio del timer
        while (client.connected() || client.available()) {
            if (client.available()) {
                String line = client.readStringUntil('\n');
                Serial.println(line); // Stampa la risposta del server
                if (line.startsWith("REQUEST")) { // Modifica la condizione secondo il formato della tua risposta
                    String requestId = line.substring(8); // Supponendo che l'ID sia dopo "REQUEST "
                    ledState = true; // Accendi il LED
                    digitalWrite(LED_PIN, HIGH);
                    Serial.println("Richiesta ricevuta. LED acceso.");

                    // Aspetta la lettura dall'RFID
                    String rfidData = waitForRFID(); // Funzione per ottenere la lettura dall'RFID
                    digitalWrite(3, HIGH);

                    Serial.print("Dati RFID letti: ");
                    Serial.println(rfidData); // Mostra i dati letti dall'RFID
                    sendResponse(rfidData, requestId); // Manda la risposta con l'ID della richiesta

                    // Aspetta 60 secondi prima di spegnere il LED e rimuovere la richiesta
                    delay(25000);
                    ledState = false; // Spegni il LED
                    digitalWrite(2, LOW);
                    digitalWrite(3, LOW);
                    Serial.println("Risposta completata. LED spento.");

                    // Rimuovi la richiesta dal database
                    removeRequest(requestId);
                    return; // Esci dalla funzione
                }
            }

            // Controlla se sono passati 60 secondi
            if (millis() - startMillis >= 60000) {
                Serial.println("Accesso negato: timeout di 60 secondi.");
                return; // Esci dalla funzione
            }
        }
        client.stop(); // Ferma la connessione
    } else {
        Serial.println("Connessione al server fallita");
    }
}

// Funzione per rimuovere la richiesta
void removeRequest(String requestId) {
    WiFiClient client;
    if (client.connect(server, 80)) {
        client.println("GET /arduino_project/remove_request.php?id_richiesta=" + requestId + " HTTP/1.1");
        client.println("Host: " + String(server));
        client.println("Connection: close");
        client.println();

        // Aspetta una risposta dal server
        while (client.connected() || client.available()) {
            if (client.available()) {
                String line = client.readStringUntil('\n');
                Serial.println(line); // Stampa la risposta del server
            }
        }
        client.stop(); // Ferma la connessione
    } else {
        Serial.println("Connessione al server fallita");
    }
}

// Funzione per attendere la lettura dall'RFID
String waitForRFID() {
    // Aspetta fino a che un tag RFID è presente
    while (!rfid.PICC_IsNewCardPresent()) {
        // Non fare nulla, attendi la lettura del tag
    }

    // Se un tag è presente, prova a leggere
    if (rfid.PICC_ReadCardSerial()) {
        String rfidData = ""; // Inizializza la stringa per memorizzare i dati RFID

        // Leggi i byte del tag RFID e converti in esadecimale
        for (byte i = 0; i < rfid.uid.size; i++) {
            rfidData += String(rfid.uid.uidByte[i], HEX);
            // Aggiungi uno spazio per chiarezza (opzionale)
            if (i < rfid.uid.size - 1) {
                rfidData += " ";
            }
        }

        // Disattiva il tag RFID
        rfid.PICC_HaltA();

        // Restituisci i dati RFID come stringa esadecimale
        return rfidData;
    }

    return "ERROR"; // Se non riesci a leggere il tag, restituisci un errore
}

void setup() {
    Serial.begin(115200);
    delay(10);

    // Inizializzazione del DHT
    dht.begin();
    
    // Inizializzazione del lettore RFID
    SPI.begin(); // Inizializza il bus SPI
    rfid.PCD_Init(); // Inizializza il lettore RFID
    Serial.println("In attesa di un tag RFID...");

    // Imposta il pin del LED come OUTPUT
    pinMode(LED_PIN, OUTPUT);
    pinMode(3, OUTPUT);

    // Connessione al Wi-Fi
    Serial.print("Connessione a ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("Connesso al Wi-Fi");
}

void loop() {
    unsigned long currentMillis = millis(); // Ottieni il tempo attuale

    // Salva i dati ogni 100 secondi
    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis; // Aggiorna il tempo dell'ultima lettura

        // Leggi i dati dal sensore DHT
        float temperature = dht.readTemperature(); // In gradi Celsius
        float humidity = dht.readHumidity();       // In percentuale

        // Controlla se la lettura è valida
        if (isnan(temperature) || isnan(humidity)) {
            Serial.println("Errore nella lettura del DHT");
            return;
        }

        // Crea la richiesta HTTP POST per inviare i dati al server
        WiFiClient client;
        if (client.connect(server, 80)) {
            String postData = "temperature=" + String(temperature) + "&humidity=" + String(humidity);
            Serial.print("Dati inviati: "); // Debug: mostra i dati inviati
            Serial.println(postData);

            client.println("POST /arduino_project/insert.php HTTP/1.1");
            client.println("Host: " + String(server));
            client.println("Content-Type: application/x-www-form-urlencoded");
            client.print("Content-Length: ");
            client.println(postData.length());
            client.println();
            client.print(postData);

            // Aspetta una risposta dal server
            while (client.connected() || client.available()) {
                if (client.available()) {
                    String line = client.readStringUntil('\n');
                    Serial.println(line); // Stampa la risposta del server
                }
            }
            client.stop(); // Ferma la connessione
        } else {
            Serial.println("Connessione al server fallita");
        }
    }

    // Controlla le richieste dal database
    checkRequests();
}
