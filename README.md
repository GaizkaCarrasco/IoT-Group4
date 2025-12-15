# Sistema de Papelera Inteligente con API de Reciclaje

Sistema completo de papelera inteligente con RFID, base de datos SQLite, API REST y panel web integrado con información de puntos de reciclaje.

## Características

- ✅ Lectura de tarjetas RFID para identificación de usuarios
- ✅ Medición de nivel de llenado con sensor ultrasónico
- ✅ Base de datos SQLite para usuarios, depósitos y estadísticas
- ✅ Integración con API de puntos de reciclaje de Madrid
- ✅ API REST con Flask para acceso a los datos
- ✅ Panel web interactivo con React
- ✅ Visualización de puntos de reciclaje más cercanos

## Estructura del Proyecto

- `PapeleraInteligente.py` - Sistema principal de la papelera (hardware + BD)
- `papelera_api.py` - Servidor Flask API REST
- `papeleraWeb.html` - Panel web con React
- `Boton2.py` - Código original con API de reciclaje (referencia)
- `requirements.txt` - Dependencias de Python

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

