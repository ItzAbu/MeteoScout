#include <WiFiNINA.h>
#include <DHT.h>

// Dati del sensore DHT
#define DHTPIN 6      // Pin a cui è collegato il DHT
#define DHTTYPE DHT11 // Cambia a DHT11 se usi un DHT11
DHT dht(DHTPIN, DHTTYPE);

// Dati Wi-Fi
const char* ssid = "Wind3 HUB-37306C";        // Sostituisci con il tuo SSID
const char* password = "6a6o9prbnbe9gho7"; // Sostituisci con la tua password Wi-Fi

// Dati del server MySQL
const char* server = "192.168.1.251"; // URL del tuo script PHP

// Pin LED
#define LED_PIN 2 // Pin a cui è collegato il LED
bool ledState = false; // Stato del LED

// Funzione per inviare una risposta al server
void sendResponse(String response) {
    WiFiClient client;
    if (client.connect(server, 80)) {
        String postData = "response=" + response;
        
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

        // Aspetta una risposta dal server
        while (client.connected() || client.available()) {
            if (client.available()) {
                String line = client.readStringUntil('\n');
                Serial.println(line); // Stampa la risposta del server
                if (line.startsWith("REQUEST")) { // Modifica la condizione secondo il formato della tua risposta
                    ledState = true; // Accendi il LED
                    digitalWrite(LED_PIN, HIGH);
                    Serial.println("Richiesta ricevuta. LED acceso.");
                    
                    // Aspetta la lettura dall'RFID
                    String rfidData = waitForRFID(); // Funzione da implementare per ottenere la lettura dall'RFID
                    sendResponse(rfidData); // Manda la risposta

                    // Aspetta 60 secondi prima di spegnere il LED e rimuovere la richiesta
                    delay(60000);
                    ledState = false; // Spegni il LED
                    digitalWrite(LED_PIN, LOW);
                    Serial.println("Richiesta completata. LED spento.");

                    // Rimuovi la richiesta dal database
                    removeRequest();
                }
            }
        }
        client.stop(); // Ferma la connessione
    } else {
        Serial.println("Connessione al server fallita");
    }
}

// Funzione per rimuovere la richiesta
void removeRequest() {
    WiFiClient client;
    if (client.connect(server, 80)) {
        client.println("GET /arduino_project/remove_request.php HTTP/1.1");
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
    // Qui dovresti implementare il codice per attendere la lettura dall'RFID
    // Ad esempio, restituisce una stringa di dati RFID letti
    // Per il momento restituiamo un valore fittizio
    delay(5000); // Simula attesa
    return "DATA_RFID"; // Sostituisci con i dati letti dall'RFID
}

void setup() {
    Serial.begin(115200);
    delay(10);
    
    // Inizializzazione del DHT
    dht.begin();

    // Imposta il pin del LED come OUTPUT
    pinMode(LED_PIN, OUTPUT);

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
    // Leggi i dati dal sensore
    float temperature = dht.readTemperature(); // In gradi Celsius
    float humidity = dht.readHumidity();       // In percentuale

    // Controlla se la lettura è valida
    if (isnan(temperature) || isnan(humidity)) {
        Serial.println("Errore nella lettura del DHT");
        return;
    }

    // Crea la richiesta HTTP POST
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

    // Controlla le richieste dal database
    checkRequests();
}