#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Papelera Inteligente
- Botn debe estar presionado para que funcione
- Tarjeta debe mantenerse 5 segundos para registrar
"""

import time
from smbus2 import SMBus
from grove.gpio import GPIO
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger
from grove.display.jhd1802 import JHD1802

# ============== CONFIGURACIN ==============
DISTANCIA_VACIA = 12  # cm cuando est vaca
DISTANCIA_LLENA = 0   # cm cuando est llena
TIEMPO_CONFIRMACION = 5  # segundos que debe estar la tarjeta

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
            self.rfid.close()
            print("\n? Sistema cerrado correctamente\n")

# ============== EJECUCIN ==============
if __name__ == "__main__":
    sistema = SistemaPapelera()
    sistema.ejecutar()
    
