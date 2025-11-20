# -*- coding: utf-8 -*-
import time
from grove.gpio import GPIO
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger
from grove.display.jhd1802 import JHD1802

# === Configuracin de pines ===
button = GPIO(5, GPIO.IN)              # Botn en D5
ultrasonic = GroveUltrasonicRanger(18) # Sensor ultrasnico en D18
lcd = JHD1802()                        # LCD 16x2 White on Blue

# === Funcin para calcular porcentaje ===
# 0 cm = 100%
# 25 cm = 0%
def calcular_porcentaje(distancia):
    distancia_max = 25
    porcentaje = 100 - (distancia / distancia_max) * 100

    # Limitar entre 0% y 100%
    porcentaje = max(0, min(100, porcentaje))

    return int(porcentaje)

# Limpia pantalla al inicio
lcd.clear()
lcd.setCursor(0,0)
lcd.write("Sistema iniciado")

print("Sistema iniciado. Manten presionado el boton para medir...")

while True:
    try:
        if button.read():  # Solo medir si el botn est presionado
            distancia = ultrasonic.get_distance()
            porcentaje = calcular_porcentaje(distancia)

            # Consola
            print(f"Distancia: {distancia:.1f} cm | Llenado: {porcentaje}%", end="\r")

            # LCD
            lcd.setCursor(0,0)
            lcd.write("Llenado: {:>3}%".format(porcentaje))
            lcd.setCursor(1,0)
            lcd.write("Dist: {:>5.1f}cm".format(distancia))

        else:
            lcd.setCursor(0,0)
            lcd.write("Esperando boton ")
            lcd.setCursor(1,0)
            lcd.write("                  ")
            print("Boton no presionado. Esperando...", end="\r")

        time.sleep(0.2)

    except KeyboardInterrupt:
        lcd.clear()
        lcd.setCursor(0,0)
        lcd.write("Sistema detenido")
        print("\nPrograma detenido.")
        break
