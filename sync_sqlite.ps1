# Configuración
$RASPBERRY_IP = "192.168.1.84"
$RASPBERRY_USER = "group2"
$RASPBERRY_DB_PATH = "/home/group2/Desktop/Laboratorios/papelera_inteligente.db"
$LOCAL_DB_PATH = "C:\Users\Adrian\papelera_inteligente.db"  # Cambia esta ruta si quieres
$LOG_FILE = "C:\Users\Adrian\sync.log"

# Crear directorio local si no existe
$localDir = Split-Path $LOCAL_DB_PATH -Parent
if (-not (Test-Path $localDir)) {
    New-Item -ItemType Directory -Path $localDir -Force | Out-Null
}

# Registrar inicio de sincronización
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LOG_FILE -Value "[$timestamp] Iniciando sincronización..."

# Transferir la base de datos usando SCP
$scpCommand = "${RASPBERRY_USER}@${RASPBERRY_IP}:${RASPBERRY_DB_PATH}"
scp $scpCommand $LOCAL_DB_PATH

# Verificar si la transferencia fue exitosa
if ($LASTEXITCODE -eq 0) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOG_FILE -Value "[$timestamp] Sincronización completada exitosamente"
    Write-Host "Sincronización completada con éxito" -ForegroundColor Green
} else {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOG_FILE -Value "[$timestamp] ERROR: Falló la sincronización"
    Write-Host "Error en la sincronización" -ForegroundColor Red
}