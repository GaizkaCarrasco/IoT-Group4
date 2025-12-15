#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Papelera Inteligente
- Botn debe estar presionado para que funcione
- Tarjeta debe mantenerse 5 segundos para registrar
"""

import math
import time
import sqlite3

import requests
from smbus2 import SMBus
from grove.gpio import GPIO
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger
from grove.display.jhd1802 import JHD1802

# ============== CONFIGURACION ==============
DISTANCIA_VACIA = 12  # cm cuando esta vacia
DISTANCIA_LLENA = 0   # cm cuando esta llena
TIEMPO_CONFIRMACION = 5  # segundos que debe estar la tarjeta

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
        
        # Estado
        self.tarjeta_actual = None
        self.tiempo_tarjeta = 0
        self.porcentaje_inicial = 0
        self.ultima_lectura_exitosa = 0  # Timestamp ltima lectura RFID
        self.timeout_perdida = 1.5  # Segundos sin lectura para considerar retirada
        self.usuarios = {}  # {uid: {'nombre': str, 'depositos': int, 'kg_total': float}}

        # Base de datos local para información de reciclaje
        self.conn = None
        self.cur = None
        self.init_db()
        self.actualizar_puntos_reciclaje()
        self.mostrar_punto_reciclaje_mas_cercano()
        
        # Inicializar
        self.rfid.init()
        self.lcd.clear()
        self.mostrar_lcd("Sistema listo", "Presiona boton")

    # ============== BASE DE DATOS + API RECICLAJE ==============
    def init_db(self):
        """
        Crea (si no existe) una BD SQLite local con puntos de reciclaje.

        Para el ejemplo, se usa la API abierta de Puntos Limpios del
        Ayuntamiento de Madrid (servicio de reciclaje):
        https://datos.madrid.es/egob/catalogo/212625-0-puntos-limpios.json
        """
        try:
            self.conn = sqlite3.connect("reciclaje.db")
            self.cur = self.conn.cursor()
            self.cur.execute(
                """
                CREATE TABLE IF NOT EXISTS puntos_reciclaje (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    direccion TEXT,
                    municipio TEXT,
                    lat REAL,
                    lon REAL
                )
                """
            )
            self.conn.commit()
            print("\n? BD 'reciclaje.db' lista.")
        except Exception as e:
            print(f"\n!! Error inicializando BD de reciclaje: {e}")

    def actualizar_puntos_reciclaje(self):
        """
        Descarga puntos de reciclaje desde una API pública y los guarda en la BD.

        API usada (reciclaje / puntos limpios):
        https://datos.madrid.es/egob/catalogo/212625-0-puntos-limpios.json
        """
        if self.conn is None or self.cur is None:
            return

        url = "https://datos.madrid.es/egob/catalogo/212625-0-puntos-limpios.json"
        print("\n? Actualizando puntos de reciclaje desde API publica...")

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            puntos = data.get("@graph", [])
            if not puntos:
                print("!! La API no devolvio puntos de reciclaje (@graph vacio).")
                return

            # Limpiamos la tabla antes de insertar
            self.cur.execute("DELETE FROM puntos_reciclaje")

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

                self.cur.execute(
                    insert_sql,
                    (nombre, direccion, municipio, lat, lon),
                )

            self.conn.commit()
            total = self.cur.execute("SELECT COUNT(*) FROM puntos_reciclaje").fetchone()[0]
            print(f"? Puntos de reciclaje guardados en BD: {total}")
        except Exception as e:
            print(f"!! Error actualizando puntos de reciclaje desde API: {e}")

    def _distancia_km(self, lat1, lon1, lat2, lon2):
        """Calcula la distancia en km entre dos puntos usando la fórmula de Haversine."""
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

    def mostrar_punto_reciclaje_mas_cercano(self):
        """
        Busca en la BD el punto de reciclaje más cercano a la papelera
        y lo muestra por consola.
        """
        if self.conn is None or self.cur is None:
            print("!! BD de reciclaje no inicializada.")
            return

        try:
            self.cur.execute(
                "SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje"
            )
            filas = self.cur.fetchall()
            if not filas:
                print("!! No hay puntos de reciclaje en la BD.")
                return

            mejor = None
            mejor_dist = None

            for nombre, direccion, municipio, lat, lon in filas:
                d = self._distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
                if d is None:
                    continue
                if mejor_dist is None or d < mejor_dist:
                    mejor_dist = d
                    mejor = (nombre, direccion, municipio, lat, lon)

            if mejor is None:
                print("!! No se pudo calcular la distancia a ningún punto de reciclaje.")
                return

            nombre, direccion, municipio, lat, lon = mejor
            print("\n" + "=" * 50)
            print("PUNTO DE RECICLAJE MÁS CERCANO")
            print("=" * 50)
            print(f"Nombre    : {nombre}")
            print(f"Dirección : {direccion}")
            print(f"Municipio : {municipio}")
            print(f"Lat, Lon  : {lat}, {lon}")
            print(f"Distancia : {mejor_dist:.2f} km desde la papelera aprox.")
            print("=" * 50 + "\n")
        except Exception as e:
            print(f"!! Error calculando punto de reciclaje más cercano: {e}")

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
        if uid not in self.usuarios:
            self.usuarios[uid] = {
                'nombre': f"User-{uid[-4:]}",
                'depositos': 0,
                'kg_total': 0.0
            }
        
        # Estimar kg (aproximado: 1% = 0.05 kg)
        kg = porcentaje_depositado * 0.05
        
        self.usuarios[uid]['depositos'] += 1
        self.usuarios[uid]['kg_total'] += kg
        
        nombre = self.usuarios[uid]['nombre']
        
        print(f"\n? REGISTRADO - {nombre}:")
        print(f"  Depositado: +{porcentaje_depositado}% (~{kg:.2f}kg)")
        print(f"  Total usuario: {self.usuarios[uid]['kg_total']:.2f}kg en {self.usuarios[uid]['depositos']} depositos")
        print(f"  Nivel papelera: {porcentaje_final}%")
        
        self.mostrar_lcd(f"Registrado!", f"{nombre[:12]}")
        time.sleep(2)
    def mostrar_estadisticas(self):
        """Muestra estadsticas de todos los usuarios"""
        print("\n" + "="*50)
        print("ESTADISTICAS DE USO DE LA PAPELERA")
        print("="*50)
        
        if not self.usuarios:
            print("No hay registros todavia")
            return
        
        for uid, datos in sorted(self.usuarios.items(), key=lambda x: x[1]['kg_total'], reverse=True):
            print(f"\n{datos['nombre']}")
            print(f"  UID: {uid}")
            print(f"  Depositos: {datos['depositos']}")
            print(f"  Total: {datos['kg_total']:.2f}kg")
        
        total_kg = sum(u['kg_total'] for u in self.usuarios.values())
        total_depositos = sum(u['depositos'] for u in self.usuarios.values())
        print("\n" + "-"*50)
        print(f"TOTAL GENERAL: {total_kg:.2f}kg en {total_depositos} depositos")
        print("="*50)
    
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
        print("\nPresiona Ctrl+C para ver estadisticas y salir\n")
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
            if self.conn:
                self.conn.close()
            self.rfid.close()
            print("\n? Sistema cerrado correctamente\n")

# ============== EJECUCIN ==============
if __name__ == "__main__":
    sistema = SistemaPapelera()
    sistema.ejecutar()
    
