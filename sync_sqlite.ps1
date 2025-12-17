# Configuración
$RASPBERRY_IP = "10.172.117.102"
$RASPBERRY_USER = "group2"
$RASPBERRY_DB_PATH = "/home/group2/Desktop/Laboratorios/papelera_inteligente.db"
$LOCAL_DB_PATH = "C:\Users\Adrian\papelera_inteligente.db"  # Cambia esta ruta si quieres
$LOG_FILE = "C:\Users\Adrian\sync.log"

# Segunda base de datos a sincronizar (misma carpeta remota, distinto nombre)
$RASPBERRY_DB_PATH_RECICLAJE = "/home/group2/Desktop/Laboratorios/reciclaje.db"
$LOCAL_DB_PATH_RECICLAJE = "C:\Users\Adrian\reciclaje.db"  # Cambia esta ruta si quieres

# Crear directorio local si no existe
$localDir = Split-Path $LOCAL_DB_PATH -Parent
if (-not (Test-Path $localDir)) {
    New-Item -ItemType Directory -Path $localDir -Force | Out-Null
}

# Registrar inicio de sincronización
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LOG_FILE -Value "[$timestamp] Iniciando sincronización..."

# Función para sincronizar una base de datos remota a local y registrar el resultado
function Sync-Db {
    param(
        [string]$RemotePath,
        [string]$LocalPath,
        [string]$Label
    )

    # Crear directorio local si no existe
    $localDir = Split-Path $LocalPath -Parent
    if (-not (Test-Path $localDir)) {
        New-Item -ItemType Directory -Path $localDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOG_FILE -Value "[$timestamp] Iniciando sincronización ($Label)..."

    $scpCommand = "${RASPBERRY_USER}@${RASPBERRY_IP}:${RemotePath}"
    scp $scpCommand $LocalPath

    if ($LASTEXITCODE -eq 0) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $LOG_FILE -Value "[$timestamp] Sincronización $Label completada exitosamente"
        Write-Host "Sincronización $Label completada con éxito" -ForegroundColor Green
    } else {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $LOG_FILE -Value "[$timestamp] ERROR: Falló la sincronización $Label"
        Write-Host "Error en la sincronización $Label" -ForegroundColor Red
    }
}

# Sincronizar ambas bases de datos
Sync-Db -RemotePath $RASPBERRY_DB_PATH -LocalPath $LOCAL_DB_PATH -Label "papelera_inteligente.db"
Sync-Db -RemotePath $RASPBERRY_DB_PATH_RECICLAJE -LocalPath $LOCAL_DB_PATH_RECICLAJE -Label "reciclaje.db"