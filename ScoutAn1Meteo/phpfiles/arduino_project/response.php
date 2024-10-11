<?php
// Modifica queste variabili con i tuoi dati di connessione
$servername = ""; // o l'indirizzo IP del server MySQL
$username = "";            // Nome utente predefinito
$password = "";       // Lascia vuoto se non hai una password
$database = "";         // Sostituisci con il tuo database

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    if (isset($_POST["response"])) { // Rimuovi l'isset per 'id_richiesta'
        $response = $_POST["response"];
        
        // Crea connessione
        $conn = new mysqli($servername, $username, $password, $database);

        // Controlla la connessione
        if ($conn->connect_error) {
            die("Connessione fallita: " . $conn->connect_error);
        }
        
        // Usa una prepared statement per l'inserimento
        $stmt = $conn->prepare("INSERT INTO risposte (codice) VALUES (?)"); // Rimuovi 'id_richiesta'
        $stmt->bind_param("s", $response); // "s" per string
        
        if ($stmt->execute()) {
            echo "Nuova risposta salvata.";
        } else {
            echo "Errore: " . $stmt->error;
        }
        
        $stmt->close();
        $conn->close();
    } else {
        echo "Dati non validi.";
    }
} else {
    echo "Richiesta non valida.";
}
?>
