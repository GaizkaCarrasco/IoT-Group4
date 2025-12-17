# ============== CLASE BASE DE DATOS ==============
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.inicializar_db()
    
    def inicializar_db(self):
        """Crear tablas si no existen"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                uid TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS depositos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL,
                porcentaje_depositado INTEGER NOT NULL,
                kg_estimado REAL NOT NULL,
                nivel_final INTEGER NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uid) REFERENCES usuarios(uid)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estadisticas (
                uid TEXT PRIMARY KEY,
                total_depositos INTEGER DEFAULT 0,
                kg_total REAL DEFAULT 0.0,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uid) REFERENCES usuarios(uid)
            )
        ''')
        self.conn.commit()
        print(f"? Base de datos iniciada: {self.db_file}")
    
    def registrar_usuario(self, uid, nombre):
        """Agregar usuario nuevo si no existe"""
        cursor = self.conn.cursor()
        
        # Verificar si ya existe
        cursor.execute('SELECT uid FROM usuarios WHERE uid = ?', (uid,))
        existe = cursor.fetchone()
        
        if existe:
            print(f"??  Usuario {uid} ya existe en BD")
            return False
        
        # Insertar nuevo usuario
        cursor.execute('''
            INSERT INTO usuarios (uid, nombre) 
            VALUES (?, ?)
        ''', (uid, nombre))
        
        cursor.execute('''
            INSERT INTO estadisticas (uid, total_depositos, kg_total) 
            VALUES (?, 0, 0.0)
        ''', (uid,))
        
        self.conn.commit()
        print(f"? Usuario {nombre} ({uid}) registrado en BD")
        return True
    
    def guardar_deposito(self, uid, porcentaje, kg, nivel_final):
        cursor = self.conn.cursor()
        
        # VERIFICAR que el usuario existe ANTES de guardar
        cursor.execute('SELECT uid FROM usuarios WHERE uid = ?', (uid,))
        if not cursor.fetchone():
            print(f"? ERROR: Usuario {uid} no existe en BD. No se puede guardar depisito.")
            return False
        
        cursor.execute('''
            INSERT INTO depositos (uid, porcentaje_depositado, kg_estimado, nivel_final)
            VALUES (?, ?, ?, ?)
        ''', (uid, porcentaje, kg, nivel_final))
        
        deposito_id = cursor.lastrowid
        print(f"? Deposito #{deposito_id} guardado: {porcentaje}% ({kg:.2f}kg)")
        
        cursor.execute('''
            UPDATE estadisticas 
            SET total_depositos = total_depositos + 1,
                kg_total = kg_total + ?,
                ultima_actualizacion = CURRENT_TIMESTAMP
            WHERE uid = ?
        ''', (kg, uid))
        
        print(f"? Estadisticas actualizadas para {uid}")
        
        self.conn.commit()
        return True
    
    def obtener_estadisticas(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.uid, u.nombre, e.total_depositos, e.kg_total
            FROM usuarios u
            JOIN estadisticas e ON u.uid = e.uid
            ORDER BY e.kg_total DESC
        ''')
        resultados = cursor.fetchall()
        print(f"?? {len(resultados)} usuarios con estadisticas")
        return resultados
    
    def obtener_historial(self, uid=None, limit=10):
        cursor = self.conn.cursor()
        if uid:
            cursor.execute('''
                SELECT d.fecha, u.nombre, d.porcentaje_depositado, d.kg_estimado, d.nivel_final
                FROM depositos d
                JOIN usuarios u ON d.uid = u.uid
                WHERE d.uid = ?
                ORDER BY d.fecha DESC
                LIMIT ?
            ''', (uid, limit))
        else:
            cursor.execute('''
                SELECT d.fecha, u.nombre, d.porcentaje_depositado, d.kg_estimado, d.nivel_final
                FROM depositos d
                JOIN usuarios u ON d.uid = u.uid
                ORDER BY d.fecha DESC
                LIMIT ?
            ''', (limit,))
        resultados = cursor.fetchall()
        print(f"?? {len(resultados)} depositos en historial")
        return resultados
    
    def verificar_integridad(self):
        """Verificar que la BD tiene datos"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        num_usuarios = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM depositos')
        num_depositos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM estadisticas')
        num_stats = cursor.fetchone()[0]
        
        print(f"\n?? VERIFICACION DE BASE DE DATOS:")
        print(f"   Usuarios: {num_usuarios}")
        print(f"   Depositos: {num_depositos}")
        print(f"   Estadisticas: {num_stats}")
        
        return num_usuarios > 0 or num_depositos > 0
    
    def cerrar(self):
        if self.conn:
            self.verificar_integridad()
            self.conn.close()
            print("? Base de datos cerrada")
    
    # ============== PUNTOS DE RECICLAJE ==============
    def inicializar_reciclaje_db(self):
        """Crear tabla de puntos de reciclaje si no existe"""
        try:
            conn_reciclaje = sqlite3.connect(RECICLAJE_DB_FILE)
            cursor = conn_reciclaje.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS puntos_reciclaje (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    direccion TEXT,
                    municipio TEXT,
                    lat REAL,
                    lon REAL
                )
            ''')
            conn_reciclaje.commit()
            conn_reciclaje.close()
            print(f"? Base de datos de reciclaje iniciada: {RECICLAJE_DB_FILE}")
        except Exception as e:
            print(f"!! Error inicializando BD de reciclaje: {e}")
    
    def actualizar_puntos_reciclaje(self):
        """
        Descarga puntos de reciclaje desde una API pública y los guarda en la BD.
        API usada (reciclaje / puntos limpios):
        https://datos.madrid.es/egob/catalogo/200284-0-puntos-limpios-fijos.json
        """
        try:
            conn_reciclaje = sqlite3.connect(RECICLAJE_DB_FILE)
            cursor = conn_reciclaje.cursor()
            
            url = "https://datos.madrid.es/egob/catalogo/200284-0-puntos-limpios-fijos.json"
            print("\n? Actualizando puntos de reciclaje desde API publica...")
            
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            puntos = data.get("@graph", [])
            if not puntos:
                print("!! La API no devolvio puntos de reciclaje (@graph vacio).")
                conn_reciclaje.close()
                return
            
            # Limpiamos la tabla antes de insertar
            cursor.execute("DELETE FROM puntos_reciclaje")
            
            insert_sql = """
                INSERT INTO puntos_reciclaje (nombre, direccion, municipio, lat, lon)
                VALUES (?, ?, ?, ?, ?)
            """
            
            for p in puntos:
                nombre = p.get("title", "Punto reciclaje")
                address = p.get("address", {}) or {}
                direccion = address.get("street-address", "")
                municipio = address.get("locality", "")
                
                coord = p.get("location", {}) or {}
                lat = None
                lon = None
                try:
                    lat = float(coord.get("latitude")) if coord.get("latitude") is not None else None
                    lon = float(coord.get("longitude")) if coord.get("longitude") is not None else None
                except (TypeError, ValueError):
                    lat, lon = None, None
                
                cursor.execute(insert_sql, (nombre, direccion, municipio, lat, lon))
            
            conn_reciclaje.commit()
            total = cursor.execute("SELECT COUNT(*) FROM puntos_reciclaje").fetchone()[0]
            print(f"? Puntos de reciclaje guardados en BD: {total}")
            conn_reciclaje.close()
        except Exception as e:
            print(f"!! Error actualizando puntos de reciclaje desde API: {e}")
    
    def _distancia_km(self, lat1, lon1, lat2, lon2):
        """Calcula la distancia en km entre dos puntos usando la formula de Haversine."""
        if None in (lat1, lon1, lat2, lon2):
            return None
        
        R = 6371.0  # Radio medio de la Tierra en km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def obtener_punto_reciclaje_mas_cercano(self):
        """
        Busca en la BD el punto de reciclaje mas cercano a la papelera.
        Retorna un diccionario con la información o None.
        """
        try:
            conn_reciclaje = sqlite3.connect(RECICLAJE_DB_FILE)
            cursor = conn_reciclaje.cursor()
            
            cursor.execute("SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje")
            filas = cursor.fetchall()
            conn_reciclaje.close()
            
            if not filas:
                return None
            
            mejor = None
            mejor_dist = None
            
            for nombre, direccion, municipio, lat, lon in filas:
                d = self._distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
                if d is None:
                    continue
                if mejor_dist is None or d < mejor_dist:
                    mejor_dist = d
                    mejor = {
                        'nombre': nombre,
                        'direccion': direccion,
                        'municipio': municipio,
                        'lat': lat,
                        'lon': lon,
                        'distancia_km': mejor_dist
                    }
            
            return mejor
        except Exception as e:
            print(f"!! Error obteniendo punto de reciclaje mas cercano: {e}")
            return None
    
    def obtener_todos_puntos_reciclaje(self, limit=10):
        """Obtiene todos los puntos de reciclaje ordenados por distancia"""
        try:
            conn_reciclaje = sqlite3.connect(RECICLAJE_DB_FILE)
            cursor = conn_reciclaje.cursor()
            
            cursor.execute("SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje")
            filas = cursor.fetchall()
            conn_reciclaje.close()
            
            puntos_con_distancia = []
            for nombre, direccion, municipio, lat, lon in filas:
                d = self._distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
                if d is not None:
                    puntos_con_distancia.append({
                        'nombre': nombre,
                        'direccion': direccion,
                        'municipio': municipio,
                        'lat': lat,
                        'lon': lon,
                        'distancia_km': d
                    })
            
            # Ordenar por distancia
            puntos_con_distancia.sort(key=lambda x: x['distancia_km'])
            return puntos_con_distancia[:limit]
        except Exception as e:
            print(f"!! Error obteniendo puntos de reciclaje: {e}")
            return []
    
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Papelera Inteligente
- Boton debe estar presionado para que funcione
- Tarjeta debe mantenerse 5 segundos para registrar
"""

import time
import math
import sqlite3
import requests
from datetime import datetime
from smbus2 import SMBus
from grove.gpio import GPIO
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger
from grove.display.jhd1802 import JHD1802

# ============== CONFIGURACIN =============
DISTANCIA_VACIA = 12  # cm cuando est vaca
DISTANCIA_LLENA = 0   # cm cuando est llena
TIEMPO_CONFIRMACION = 5  # segundos que debe estar la tarjeta
DB_FILE = "papelera_inteligente.db"  # Base de datos SQLite
RECICLAJE_DB_FILE = "reciclaje.db"  # Base de datos para puntos de reciclaje

# Coordenadas aproximadas de la papelera
# Ejemplo: centro de Madrid
LAT_PAPELERA = 40.4168
LON_PAPELERA = -3.7038

# ============== CLASE RFID ==============
class WS1850S:
    def __init__(self, bus=1, addr=0x28):
        self.bus = SMBus(bus)
        self.addr = addr
    
    def _wr(self, reg, val):
        self.bus.write_byte_data(self.addr, reg, val)
    
    def _rd(self, reg):
        return self.bus.read_byte_data(self.addr, reg)
    
    def init(self):
        self._wr(0x01, 0x0F)
        time.sleep(0.05)
        self._wr(0x2A, 0x8D)
        self._wr(0x2B, 0x3E)
        self._wr(0x2D, 30)
        self._wr(0x2C, 0)
        self._wr(0x15, 0x40)
        self._wr(0x11, 0x3D)
        val = self._rd(0x14)
        if not (val & 0x03):
            self._wr(0x14, val | 0x03)
    
    def _transceive(self, data):
        self._wr(0x02, 0xF7)
        self._wr(0x04, self._rd(0x04) & ~0x80)
        self._wr(0x0A, self._rd(0x0A) | 0x80)
        self._wr(0x01, 0x00)
        for d in data:
            self._wr(0x09, d)
        self._wr(0x01, 0x0C)
        self._wr(0x0D, self._rd(0x0D) | 0x80)
        for _ in range(2000):
            n = self._rd(0x04)
            if n & 0x31:
                break
            time.sleep(0.001)
        self._wr(0x0D, self._rd(0x0D) & ~0x80)
        if self._rd(0x06) & 0x1B:
            return None
        n = self._rd(0x0A)
        return [self._rd(0x09) for _ in range(min(n, 16))]
    
    def read_uid(self):
        self._wr(0x0D, 0x07)
        resp = self._transceive([0x26])
        if not resp:
            return None
        self._wr(0x0D, 0x00)
        uid = self._transceive([0x93, 0x20])
        if uid and len(uid) == 5:
            if (uid[0] ^ uid[1] ^ uid[2] ^ uid[3]) == uid[4]:
                return ''.join(f'{b:02X}' for b in uid[:4])
        return None
    
    def close(self):
        self.bus.close()
# ============== CLASE SISTEMA ==============
class SistemaPapelera:
    def __init__(self):
        # Hardware
        self.rfid = WS1850S()
        self.boton = GPIO(5, GPIO.IN)
        self.ultrasonic = GroveUltrasonicRanger(18)
        self.lcd = JHD1802()
        
        # Base de datos
        self.db = DatabaseManager(DB_FILE)
        
        # Inicializar base de datos de reciclaje
        self.db.inicializar_reciclaje_db()
        self.db.actualizar_puntos_reciclaje()
        
        # Mostrar punto mas cercano al inicio
        punto_cercano = self.db.obtener_punto_reciclaje_mas_cercano()
        if punto_cercano:
            print("\n" + "=" * 50)
            print("PUNTO DE RECICLAJE MAS CERCANO")
            print("=" * 50)
            print(f"Nombre    : {punto_cercano['nombre']}")
            print(f"Dirección : {punto_cercano['direccion']}")
            print(f"Municipio : {punto_cercano['municipio']}")
            print(f"Distancia : {punto_cercano['distancia_km']:.2f} km")
            print("=" * 50 + "\n")
        
        # Estado
        self.tarjeta_actual = None
        self.tiempo_tarjeta = 0
        self.porcentaje_inicial = 0
        self.ultima_lectura_exitosa = 0  # Timestamp ltima lectura RFID
        self.timeout_perdida = 1.5  # Segundos sin lectura para considerar retirada
        self.usuarios = {}  # Cache local: {uid: {'nombre': str}}
        
        # Inicializar
        self.rfid.init()
        self.lcd.clear()
        self.mostrar_lcd("Sistema listo", "Presiona boton")
    
    def calcular_porcentaje(self, distancia):
        """Calcula % de llenado (0cm=100%, 12cm=0%)"""
        porcentaje = 100 - (distancia / DISTANCIA_VACIA) * 100
        return max(0, min(100, int(porcentaje)))
    
    def mostrar_lcd(self, linea1, linea2=""):
        """Muestra texto en LCD"""
        self.lcd.setCursor(0, 0)
        self.lcd.write(f"{linea1:<16}")
        self.lcd.setCursor(1, 0)
        self.lcd.write(f"{linea2:<16}")
    
    def registrar_deposito(self, uid, porcentaje_depositado, porcentaje_final):
        """Registra depsito del usuario despus de 5 segundos"""
        # Obtener o crear usuario
        if uid not in self.usuarios:
            nombre = f"User-{uid[-4:]}"
            self.usuarios[uid] = {'nombre': nombre}
            self.db.registrar_usuario(uid, nombre)
        else:
            nombre = self.usuarios[uid]['nombre']
        
        # Estimar kg (aproximado: 1% = 0.05 kg)
        kg = porcentaje_depositado * 0.05
        
        # Guardar en base de datos
        self.db.guardar_deposito(uid, porcentaje_depositado, kg, porcentaje_final)
        
        # Obtener estadsticas actualizadas
        stats = self.db.obtener_estadisticas()
        usuario_stats = next((s for s in stats if s[0] == uid), None)
        if usuario_stats:
            _, _, total_depositos, kg_total = usuario_stats
            
            print(f"\n? REGISTRADO - {nombre}:")
            print(f"  Depositado ahora: +{porcentaje_depositado}% (~{kg:.2f}kg)")
            print(f"  Total usuario: {kg_total:.2f}kg en {total_depositos} depositos")
            print(f"  Nivel papelera: {porcentaje_final}%")
            print(f"  ?? Guardado en base de datos")
        
        self.mostrar_lcd(f"Registrado!", f"{nombre[:12]}")
        time.sleep(2)
    def mostrar_estadisticas(self):
        """Muestra estadsticas desde la base de datos"""
        print("\n" + "="*60)
        print("       ESTADISTICAS DE USO - BASE DE DATOS")
        print("="*60)
        
        stats = self.db.obtener_estadisticas()
        
        if not stats:
            print("No hay registros todavia")
            return
        
        for uid, nombre, total_depositos, kg_total in stats:
            print(f"\n{nombre}")
            print(f"  UID: {uid}")
            print(f"  Depositos: {total_depositos}")
            print(f"  Total: {kg_total:.2f}kg")
        
        total_kg = sum(s[3] for s in stats)
        total_depositos = sum(s[2] for s in stats)
        print("\n" + "-"*60)
        print(f"TOTAL GENERAL: {total_kg:.2f}kg en {total_depositos} depositos")
        print("="*60)
        # Mostrar ltimos 5 depsitos
        print("\n" + "="*60)
        print("       ULTIMOS 5 DEPOSITOS")
        print("="*60)
        historial = self.db.obtener_historial(limit=5)
        
        for fecha, nombre, porcentaje, kg, nivel in historial:
            fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
            print(f"{fecha_formateada} - {nombre}: +{porcentaje}% (~{kg:.2f}kg) ? Nivel: {nivel}%")
        
        print("="*60)
        
    def ejecutar(self):
        """Bucle principal del sistema"""
        print("\n" + "="*50)
        print("    PAPELERA INTELIGENTE CON RFID")
        print("="*50)
        print("\nFUNCIONAMIENTO:")
        print("  1. Manten PRESIONADO el boton")
        print("  2. Acerca tu tarjeta RFID")
        print("  3. Manten la tarjeta 5 segundos para confirmar")
        print("  4. Deposito quedo registrado")
        print("\nPresiona Ctrl+C para ver estadasticas y salir\n")
        
        try:
            while True:
                boton_presionado = self.boton.read()
                
                # SISTEMA SOLO FUNCIONA SI BOTN EST PRESIONADO
                if boton_presionado:
                    # Medir nivel
                    distancia = self.ultrasonic.get_distance()
                    porcentaje_actual = self.calcular_porcentaje(distancia)
                    
                    # Leer tarjeta
                    uid = self.rfid.read_uid()
                    
                    if uid:
                        # Actualizar timestamp de ltima lectura exitosa
                        self.ultima_lectura_exitosa = time.time()
                        
                        # Si es nueva tarjeta
                        if uid != self.tarjeta_actual:
                            # Nueva tarjeta detectada
                            self.tarjeta_actual = uid
                            self.tiempo_tarjeta = time.time()
                            self.porcentaje_inicial = porcentaje_actual
                            
                            nombre = self.usuarios.get(uid, {}).get('nombre', f"User-{uid[-4:]}")
                            print(f"\n? Tarjeta detectada: {nombre}")
                            print(f"   Manten la tarjeta para confirmar...")
                            
                            self.mostrar_lcd(f"Hola {nombre[:12]}", "Mantenla 5 seg")
                        
                        # Calcular tiempo transcurrido
                        tiempo_transcurrido = time.time() - self.tiempo_tarjeta
                        tiempo_restante = TIEMPO_CONFIRMACION - tiempo_transcurrido
                        
                        if tiempo_restante > 0:
                            # An no han pasado 5 segundos
                            porcentaje_depositado = porcentaje_actual - self.porcentaje_inicial
                            
                            self.mostrar_lcd(
                                f"Confirma: {int(tiempo_restante)}s",
                                f"Nivel: {porcentaje_actual}% (+{porcentaje_depositado}%)"
                            )
                            
                            print(f"\r??  Confirmando... {int(tiempo_restante)}s | Nivel: {porcentaje_actual}% (+{porcentaje_depositado}%)    ", end="")
                        else:
                            # 5 segundos cumplidos! Registrar
                            porcentaje_depositado = porcentaje_actual - self.porcentaje_inicial
                            self.registrar_deposito(uid, porcentaje_depositado, porcentaje_actual)
                            
                            # Resetear para permitir nuevo registro
                            self.porcentaje_inicial = porcentaje_actual
                            self.tiempo_tarjeta = time.time()
                    
                    else:
                        # No se ley tarjeta en este ciclo
                        # Solo considerar retirada si ha pasado el timeout SIN lecturas
                        if self.tarjeta_actual:
                            tiempo_sin_lectura = time.time() - self.ultima_lectura_exitosa
                            
                            if tiempo_sin_lectura > self.timeout_perdida:
                                # Realmente se retir la tarjeta
                                print(f"\n? Tarjeta retirada (no confirmado)")
                                self.tarjeta_actual = None
                            else:
                                # Fallo temporal de lectura, seguir mostrando progreso
                                tiempo_transcurrido = time.time() - self.tiempo_tarjeta
                                tiempo_restante = TIEMPO_CONFIRMACION - tiempo_transcurrido
                                
                                if tiempo_restante > 0:
                                    porcentaje_depositado = porcentaje_actual - self.porcentaje_inicial
                                    
                                    self.mostrar_lcd(
                                        f"Confirma: {int(tiempo_restante)}s",
                                        f"Nivel: {porcentaje_actual}% (+{porcentaje_depositado}%)"
                                    )
                                    
                                    print(f"\r??  Confirmando... {int(tiempo_restante)}s | Nivel: {porcentaje_actual}% (+{porcentaje_depositado}%)    ", end="")
                        else:
                            # No hay tarjeta y no haba ninguna antes
                            self.mostrar_lcd(
                                "Boton presionado",
                                f"Nivel: {porcentaje_actual}%"
                            )
                            print(f"\r?? Nivel: {porcentaje_actual}% | Esperando tarjeta...    ", end="")
                
                else:
                    # BOTN NO PRESIONADO - Sistema inactivo
                    if self.tarjeta_actual:
                        print(f"\n??  Boton soltado - Registro cancelado")
                        self.tarjeta_actual = None
                    
                    self.mostrar_lcd("Sistema listo", "Presiona boton")
                    print("\r?? Sistema inactivo - Presiona el boton para usar    ", end="")
                
                time.sleep(0.2) 
                        
        
        except KeyboardInterrupt:
            print("\n\n?? Deteniendo sistema...")
            self.mostrar_estadisticas()
            self.lcd.clear()
            self.mostrar_lcd("Sistema", "detenido")
            self.rfid.close()
            self.db.cerrar()
            print(f"\n? Datos guardados en: {DB_FILE}")
            print("? Sistema cerrado correctamente\n")

# ============== EJECUCIN ==============
if __name__ == "__main__":
    sistema = SistemaPapelera()
    sistema.ejecutar()
    
