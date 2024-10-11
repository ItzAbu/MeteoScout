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

// Controlla se ci sono richieste attive
$sql = "SELECT * FROM richieste WHERE lettura = TRUE LIMIT 1"; // Modifica se necessario
$result = $conn->query($sql);

if ($result->num_rows > 0) {
    echo "REQUEST"; // Indica che esiste almeno una richiesta attiva
} else {
    echo "NO REQUEST"; // Indica che non ci sono richieste attive
}

$conn->close();
?>
