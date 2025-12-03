#!/usr/bin/env python3
"""Lector RFID WS1850S - Versión minimalista para solo leer UIDs"""

from smbus2 import SMBus
import time

class WS1850S:
    def __init__(self, bus=1, addr=0x28):
        self.bus = SMBus(bus)
        self.addr = addr
    
    def _wr(self, reg, val):
        self.bus.write_byte_data(self.addr, reg, val)
    
    def _rd(self, reg):
        return self.bus.read_byte_data(self.addr, reg)
    
    def init(self):
        """Inicializar chip"""
        self._wr(0x01, 0x0F)  # Reset
        time.sleep(0.05)
        self._wr(0x2A, 0x8D)  # Timer
        self._wr(0x2B, 0x3E)
        self._wr(0x2D, 30)
        self._wr(0x2C, 0)
        self._wr(0x15, 0x40)  # TX
        self._wr(0x11, 0x3D)  # Mode
        
        # Antena ON
        val = self._rd(0x14)
        if not (val & 0x03):
            self._wr(0x14, val | 0x03)
    
    def _transceive(self, data):
        """Enviar/recibir datos"""
        self._wr(0x02, 0xF7)
        self._wr(0x04, self._rd(0x04) & ~0x80)
        self._wr(0x0A, self._rd(0x0A) | 0x80)
        self._wr(0x01, 0x00)
        
        for d in data:
            self._wr(0x09, d)
        
        self._wr(0x01, 0x0C)
        self._wr(0x0D, self._rd(0x0D) | 0x80)
        
        # Esperar
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
        """Leer UID de tarjeta"""
        # Request
        self._wr(0x0D, 0x07)
        resp = self._transceive([0x26])
        if not resp:
            return None
        
        # Anticoll
        self._wr(0x0D, 0x00)
        uid = self._transceive([0x93, 0x20])
        
        if uid and len(uid) == 5:
            # Verificar checksum
            if (uid[0] ^ uid[1] ^ uid[2] ^ uid[3]) == uid[4]:
                return ''.join(f'{b:02X}' for b in uid[:4])
        
        return None
    
    def close(self):
        self.bus.close()


# Uso simple
if __name__ == "__main__":
    reader = WS1850S()
    reader.init()
    print("Lector listo. Ctrl+C para salir\n")
    
    last = None
    try:
        while True:
            uid = reader.read_uid()
            if uid and uid != last:
                print(f"UID: {uid}")
                last = uid
            elif not uid:
                last = None
            time.sleep(0.2)
    except KeyboardInterrupt:
        reader.close()
        print("\nCerrado")