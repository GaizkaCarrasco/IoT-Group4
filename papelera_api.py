#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para el Sistema de Papelera Inteligente
Expone endpoints para acceder a datos de usuarios, depositos, estadisticas y puntos de reciclaje
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permitir CORS para que la web pueda acceder

# Configuracion
DB_FILE = "papelera_inteligente.db"
RECICLAJE_DB_FILE = "reciclaje.db"

# Coordenadas de la papelera
LAT_PAPELERA = 40.4168
LON_PAPELERA = -3.7038

def get_db_connection(db_file):
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

def distancia_km(lat1, lon1, lat2, lon2):
    """Calcula la distancia en km entre dos puntos usando la fórmula de Haversine."""
    import math
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

# ============== ENDPOINTS DE USUARIOS Y DEPOSITOS ==============

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    """Obtener lista de todos los usuarios"""
    try:
        conn = get_db_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT uid, nombre, fecha_registro FROM usuarios ORDER BY nombre')
        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'uid': row[0],
                'nombre': row[1],
                'fecha_registro': row[2]
            })
        conn.close()
        return jsonify({'usuarios': usuarios, 'total': len(usuarios)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/depositos', methods=['GET'])
def get_depositos():
    """Obtener lista de depositos"""
    try:
        limit = request.args.get('limit', 10, type=int)
        uid = request.args.get('uid', None)
        
        conn = get_db_connection(DB_FILE)
        cursor = conn.cursor()
        
        if uid:
            cursor.execute('''
                SELECT d.id, d.uid, u.nombre, d.porcentaje_depositado, d.kg_estimado, 
                       d.nivel_final, d.fecha
                FROM depositos d
                JOIN usuarios u ON d.uid = u.uid
                WHERE d.uid = ?
                ORDER BY d.fecha DESC
                LIMIT ?
            ''', (uid, limit))
        else:
            cursor.execute('''
                SELECT d.id, d.uid, u.nombre, d.porcentaje_depositado, d.kg_estimado, 
                       d.nivel_final, d.fecha
                FROM depositos d
                JOIN usuarios u ON d.uid = u.uid
                ORDER BY d.fecha DESC
                LIMIT ?
            ''', (limit,))
        
        depositos = []
        for row in cursor.fetchall():
            depositos.append({
                'id': row[0],
                'uid': row[1],
                'nombre': row[2],
                'porcentaje': row[3],
                'kg': row[4],
                'nivel': row[5],
                'fecha': row[6]
            })
        conn.close()
        return jsonify({'depositos': depositos, 'total': len(depositos)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def get_estadisticas():
    """Obtener estadisticas de todos los usuarios"""
    try:
        conn = get_db_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.uid, u.nombre, e.total_depositos, e.kg_total, e.ultima_actualizacion
            FROM usuarios u
            JOIN estadisticas e ON u.uid = e.uid
            ORDER BY e.kg_total DESC
        ''')
        
        estadisticas = []
        for row in cursor.fetchall():
            estadisticas.append({
                'uid': row[0],
                'nombre': row[1],
                'total_depositos': row[2],
                'kg_total': row[3],
                'ultima_actualizacion': row[4]
            })
        
        # Calcular totales
        total_kg = sum(s['kg_total'] for s in estadisticas)
        total_depositos = sum(s['total_depositos'] for s in estadisticas)
        
        # Obtener nivel actual de la papelera (ultimo depósito)
        cursor.execute('SELECT nivel_final FROM depositos ORDER BY fecha DESC LIMIT 1')
        nivel_actual = cursor.fetchone()
        nivel_actual = nivel_actual[0] if nivel_actual else 0
        
        conn.close()
        
        return jsonify({
            'estadisticas': estadisticas,
            'totales': {
                'kg_total': total_kg,
                'total_depositos': total_depositos,
                'nivel_actual': nivel_actual
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nivel-actual', methods=['GET'])
def get_nivel_actual():
    """Obtener el nivel actual de la papelera"""
    try:
        conn = get_db_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nivel_final FROM depositos ORDER BY fecha DESC LIMIT 1')
        nivel = cursor.fetchone()
        conn.close()
        
        if nivel:
            return jsonify({'nivel': nivel[0]})
        else:
            return jsonify({'nivel': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== ENDPOINTS DE PUNTOS DE RECICLAJE ==============

@app.route('/api/puntos-reciclaje', methods=['GET'])
def get_puntos_reciclaje():
    """Obtener lista de puntos de reciclaje ordenados por distancia"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        if not os.path.exists(RECICLAJE_DB_FILE):
            return jsonify({'puntos': [], 'total': 0, 'mensaje': 'Base de datos de reciclaje no encontrada'})
        
        conn = get_db_connection(RECICLAJE_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje')
        filas = cursor.fetchall()
        conn.close()
        
        puntos_con_distancia = []
        for row in filas:
            nombre, direccion, municipio, lat, lon = row
            d = distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
            if d is not None:
                puntos_con_distancia.append({
                    'nombre': nombre,
                    'direccion': direccion,
                    'municipio': municipio,
                    'lat': lat,
                    'lon': lon,
                    'distancia_km': round(d, 2)
                })
        
        # Ordenar por distancia
        puntos_con_distancia.sort(key=lambda x: x['distancia_km'])
        
        return jsonify({
            'puntos': puntos_con_distancia[:limit],
            'total': len(puntos_con_distancia)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/punto-reciclaje-cercano', methods=['GET'])
def get_punto_reciclaje_cercano():
    """Obtener el punto de reciclaje mas cercano"""
    try:
        if not os.path.exists(RECICLAJE_DB_FILE):
            return jsonify({'error': 'Base de datos de reciclaje no encontrada'}), 404
        
        conn = get_db_connection(RECICLAJE_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje')
        filas = cursor.fetchall()
        conn.close()
        
        if not filas:
            return jsonify({'mensaje': 'No hay puntos de reciclaje disponibles'})
        
        mejor = None
        mejor_dist = None
        
        for nombre, direccion, municipio, lat, lon in filas:
            d = distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
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
                    'distancia_km': round(d, 2)
                }
        
        if mejor:
            return jsonify(mejor)
        else:
            return jsonify({'mensaje': 'No se pudo calcular la distancia a ningún punto'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resumen', methods=['GET'])
def get_resumen():
    """Obtener resumen completo del sistema"""
    try:
        # Estadisticas
        conn = get_db_connection(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        num_usuarios = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM depositos')
        num_depositos = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(kg_total) FROM estadisticas')
        total_kg = cursor.fetchone()[0] or 0.0
        
        cursor.execute('SELECT nivel_final FROM depositos ORDER BY fecha DESC LIMIT 1')
        nivel_row = cursor.fetchone()
        nivel_actual = nivel_row[0] if nivel_row else 0
        
        conn.close()
        
        # Punto mas cercano
        punto_cercano = None
        if os.path.exists(RECICLAJE_DB_FILE):
            try:
                conn_rec = get_db_connection(RECICLAJE_DB_FILE)
                cursor_rec = conn_rec.cursor()
                cursor_rec.execute('SELECT nombre, direccion, municipio, lat, lon FROM puntos_reciclaje')
                filas = cursor_rec.fetchall()
                conn_rec.close()
                
                mejor_dist = None
                for nombre, direccion, municipio, lat, lon in filas:
                    d = distancia_km(LAT_PAPELERA, LON_PAPELERA, lat, lon)
                    if d is not None and (mejor_dist is None or d < mejor_dist):
                        mejor_dist = d
                        punto_cercano = {
                            'nombre': nombre,
                            'direccion': direccion,
                            'municipio': municipio,
                            'distancia_km': round(d, 2)
                        }
            except:
                pass
        
        return jsonify({
            'usuarios': num_usuarios,
            'depositos': num_depositos,
            'kg_total': round(total_kg, 2),
            'nivel_actual': nivel_actual,
            'punto_reciclaje_cercano': punto_cercano
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de salud para verificar que la API está funcionando"""
    db_exists = os.path.exists(DB_FILE)
    reciclaje_db_exists = os.path.exists(RECICLAJE_DB_FILE)
    
    return jsonify({
        'status': 'ok',
        'db_papelera': db_exists,
        'db_reciclaje': reciclaje_db_exists
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  API REST - Sistema de Papelera Inteligente")
    print("="*60)
    print("\nEndpoints disponibles:")
    print("  GET /api/usuarios - Lista de usuarios")
    print("  GET /api/depositos - Lista de depósitos")
    print("  GET /api/estadisticas - Estadísticas de usuarios")
    print("  GET /api/nivel-actual - Nivel actual de la papelera")
    print("  GET /api/puntos-reciclaje - Lista de puntos de reciclaje")
    print("  GET /api/punto-reciclaje-cercano - Punto más cercano")
    print("  GET /api/resumen - Resumen completo del sistema")
    print("  GET /api/health - Estado de la API")
    print("\nIniciando servidor en http://localhost:5000\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

