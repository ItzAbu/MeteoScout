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

// Ricevi i dati dalla richiesta POST
$temperature = $_POST['temperature'];
$humidity = $_POST['humidity'];

// Inserisci i dati nel database
$sql = "INSERT INTO sensor_data (temperature, humidity) VALUES ('$temperature', '$humidity')";
if ($conn->query($sql) === TRUE) {
    echo "Nuovo record inserito con successo";
} else {
    echo "Errore: " . $sql . "<br>" . $conn->error;
}

$conn->close();
?>