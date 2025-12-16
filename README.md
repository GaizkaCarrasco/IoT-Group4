# Sistema de Papelera Inteligente con API de Reciclaje

Sistema completo de papelera inteligente con RFID, base de datos SQLite, API REST y panel web integrado con información de puntos de reciclaje.

## Características

- Lectura de tarjetas RFID para identificación de usuarios
- Medición de nivel de llenado con sensor ultrasónico
- Base de datos SQLite para usuarios, depósitos y estadísticas
- Integración con API de puntos de reciclaje de Madrid
- API REST con Flask para acceso a los datos
- Panel web interactivo con React
- Visualización de puntos de reciclaje más cercanos

## Hardware y Sensores

### Sensores Incorporados

1. **Lector RFID/NFC WS1850S**
   - Protocolo: I2C (dirección 0x28)
   - Función: Identificación de usuarios mediante tarjetas RFID
   - Conexión: Bus I2C (SDA/SCL)

2. **Sensor Ultrasónico Grove Ultrasonic Ranger**
   - Tipo: Sensor de distancia por ultrasonidos
   - Rango: 0-12 cm (configurable)
   - Función: Medición del nivel de llenado de la papelera
   - Conexión: Pin digital GPIO 18 (D18)

3. **Botón GPIO**
   - Tipo: Botón digital
   - Función: Activación del sistema (debe estar presionado para funcionar)
   - Conexión: Pin digital GPIO 5 (D5)

4. **Pantalla LCD JHD1802**
   - Tipo: Display LCD 16x2 caracteres
   - Función: Visualización de información al usuario
   - Conexión: I2C (mismo bus que RFID)

### Conexiones del Hardware

```
Raspberry Pi / Grove Base Hat
├── I2C Bus
│   ├── WS1850S RFID Reader (0x28)
│   └── JHD1802 LCD Display
├── GPIO 5 (D5) → Botón
└── GPIO 18 (D18) → Sensor Ultrasónico
```

### Especificaciones Técnicas

- **Plataforma**: Raspberry Pi con Grove Base Hat
- **Comunicación**: I2C para RFID y LCD, GPIO para botón y sensor ultrasónico
- **Base de datos**: SQLite (archivos locales)
- **API Externa**: API de puntos limpios de Madrid (requiere internet)

## Estructura del Código

### Arquitectura del Sistema

El proyecto está estructurado en tres componentes principales:

1. **Sistema Principal (`PapeleraInteligente.py`)**
   - Clase `WS1850S`: Manejo del lector RFID/NFC
   - Clase `DatabaseManager`: Gestión de base de datos SQLite
   - Clase `SistemaPapelera`: Lógica principal del sistema
     - Inicialización de hardware
     - Bucle principal de lectura de sensores
     - Registro de depósitos
     - Cálculo de estadísticas

2. **API REST (`papelera_api.py`)**
   - Servidor Flask con endpoints para:
     - Consulta de usuarios y depósitos
     - Estadísticas en tiempo real
     - Información de puntos de reciclaje
   - CORS habilitado para acceso web

3. **Panel Web (`papeleraWeb.html`)**
   - Interfaz React con Tailwind CSS
   - Visualización de datos en tiempo real
   - Carga de datos desde API o archivos SQLite locales

### Archivos del Proyecto

- `PapeleraInteligente.py` - Sistema principal de la papelera (hardware + BD)
- `papelera_api.py` - Servidor Flask API REST
- `papeleraWeb.html` - Panel web con React
- `LectorNFC.py` - Código de referencia para lectura RFID
- `Boton2.py` - Código original con API de reciclaje (referencia)
- `requirements.txt` - Dependencias de Python
- `sync_sqlite.ps1` - Script de sincronización (PowerShell)

## Instalación

### 1. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 2. Ejecutar el sistema de papelera

```bash
python PapeleraInteligente.py
```

Este script:
- Inicializa la base de datos SQLite (`papelera_inteligente.db`)
- Descarga puntos de reciclaje desde la API de Madrid
- Guarda los puntos en `reciclaje.db`
- Muestra el punto de reciclaje más cercano al inicio

### 3. Iniciar el servidor API

En otra terminal:

```bash
python papelera_api.py
```

El servidor se iniciará en `http://localhost:5000`

### 4. Abrir el panel web

Abre `papeleraWeb.html` en tu navegador. El panel:
- Se conecta automáticamente a la API en `http://localhost:5000`
- Muestra usuarios, depósitos, estadísticas y puntos de reciclaje
- Permite actualizar datos desde la API
- También permite cargar archivos de BD locales como respaldo

## Endpoints de la API

- `GET /api/usuarios` - Lista de usuarios
- `GET /api/depositos?limit=10` - Lista de depósitos
- `GET /api/estadisticas` - Estadísticas de usuarios
- `GET /api/nivel-actual` - Nivel actual de la papelera
- `GET /api/puntos-reciclaje?limit=10` - Lista de puntos de reciclaje
- `GET /api/punto-reciclaje-cercano` - Punto más cercano
- `GET /api/resumen` - Resumen completo del sistema
- `GET /api/health` - Estado de la API

## Funcionamiento del Sistema

1. **Registro de depósitos:**
   - Mantén presionado el botón
   - Acerca tu tarjeta RFID
   - Mantén la tarjeta 5 segundos para confirmar
   - El depósito se registra automáticamente

2. **Base de datos:**
   - Usuarios se registran automáticamente al primer uso
   - Cada depósito se guarda con porcentaje, kg estimado y nivel final
   - Las estadísticas se actualizan automáticamente

3. **Puntos de reciclaje:**
   - Se descargan desde la API de Madrid al iniciar
   - Se calcula la distancia desde la papelera usando coordenadas GPS
   - Se muestra el punto más cercano en consola y web

## Configuración

### Coordenadas de la papelera

Edita en `PapeleraInteligente.py` y `papelera_api.py`:

```python
LAT_PAPELERA = 40.4168  # Latitud
LON_PAPELERA = -3.7038  # Longitud
```

### URL de la API en la web

El panel web permite cambiar la URL de la API. Por defecto es `http://localhost:5000`

## Notas

- La API de puntos de reciclaje requiere conexión a internet
- Los datos se guardan localmente en archivos SQLite
- El sistema funciona sin conexión a internet (excepto para actualizar puntos de reciclaje)

