# -*- coding: utf-8 -*-
import time
from grove.gpio import GPIO
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger
from grove.display.jhd1802 import JHD1802

# === Configuracin de pines ===
button = GPIO(5, GPIO.IN)            # Botn en D5 ? GPIO5
ultrasonic = GroveUltrasonicRanger(18)  # Sensor ultrasnico en D18 ? GPIO24
lcd = JHD1802()                        # LCD 16x2 White on Blue

# Funcin para calcular porcentaje de llenado
def calcular_porcentaje(distancia):
    if 0 < distancia <= 3:
        return 100
    elif 3 < distancia <= 20:
        return 70
    elif 22 < distancia <= 25:
        return 30
    else:
        return 0

# Limpia pantalla al inicio
lcd.clear()
lcd.setCursor(0,0)
lcd.write("Sistema iniciado")

print("Sistema iniciado. Mantn presionado el botn para medir...")

while True:
    try:
        if button.read():  # Solo medir si el botn est presionado
            distancia = ultrasonic.get_distance()
            porcentaje = calcular_porcentaje(distancia)

            # Consola
            if porcentaje == 100:
                print(f"??? Basura llena ({porcentaje}%) | Distancia: {distancia:.1f} cm", end="\r")
            else:
                print(f"Distancia: {distancia:.1f} cm | Llenado: {porcentaje}%", end="\r")

            # LCD
            lcd.setCursor(0,0)
            lcd.write("Llenado: {:>3}%".format(porcentaje))
            lcd.setCursor(1,0)
            lcd.write("Dist: {:>5.1f}cm".format(distancia))

        else:
            lcd.setCursor(0,0)
            lcd.write("Esperando boton  ")
            lcd.setCursor(1,0)
            lcd.write("                  ")
            print("Botn no presionado. Esperando...", end="\r")

        time.sleep(0.2)

    except KeyboardInterrupt:
        lcd.clear()
        lcd.setCursor(0,0)
        lcd.write("Sistema detenido")
        print("\nPrograma detenido.")
        break
