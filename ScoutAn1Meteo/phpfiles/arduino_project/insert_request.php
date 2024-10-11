<?php
$servername = ""; // Cambia con il tuo server
$username = ""; // Cambia con il tuo username
$password = ""; // Cambia con la tua password
$dbname = ""; // Nome del tuo database

// Crea connessione
$conn = new mysqli($servername, $username, $password, $dbname);

// Controlla la connessione
if ($conn->connect_error) {
    die("Connessione fallita: " . $conn->connect_error);
}

// Inserisci una nuova richiesta
$sql = "INSERT INTO richieste (lettura) VALUES (TRUE)";
if ($conn->query($sql) === TRUE) {
    echo "Nuova richiesta inserita con successo";
} else {
    echo "Errore: " . $sql . "<br>" . $conn->error;
}

$conn->close();
?>
