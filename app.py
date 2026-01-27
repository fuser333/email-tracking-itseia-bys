#!/usr/bin/env python3
"""
Sistema de Tracking de Emails - Alianza ITSEIA-BYS
Backend Flask para registrar aperturas de emails y mostrar dashboard
"""

from flask import Flask, request, send_file, render_template, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import io
import os

app = Flask(__name__)
CORS(app)

# Base de datos
DATABASE = 'email_tracking.db'

def init_db():
    """Inicializa la base de datos"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT NOT NULL,
            institucion TEXT,
            autoridad TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/track/<email_id>.gif')
def track_email(email_id):
    """
    Pixel de tracking - registra cuando se abre el email
    """
    # Registrar la apertura
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')

    # Extraer datos del email_id (formato: email_institucion_timestamp)
    parts = email_id.split('_')
    institucion = parts[1] if len(parts) > 1 else 'Desconocido'

    c.execute('''
        INSERT INTO email_opens (email_id, institucion, ip_address, user_agent)
        VALUES (?, ?, ?, ?)
    ''', (email_id, institucion, ip_address, user_agent))

    conn.commit()
    conn.close()

    # Crear pixel transparente 1x1
    pixel = io.BytesIO()
    pixel.write(b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    pixel.seek(0)

    return send_file(pixel, mimetype='image/gif')

@app.route('/stats')
def get_stats():
    """
    API para obtener estadísticas de aperturas
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Total de aperturas
    c.execute('SELECT COUNT(*) FROM email_opens')
    total_aperturas = c.fetchone()[0]

    # Emails únicos
    c.execute('SELECT COUNT(DISTINCT email_id) FROM email_opens')
    emails_unicos = c.fetchone()[0]

    # Promedio de aperturas
    promedio = total_aperturas / emails_unicos if emails_unicos > 0 else 0

    # Detalles de aperturas
    c.execute('''
        SELECT email_id, institucion, timestamp, ip_address, user_agent
        FROM email_opens
        ORDER BY timestamp DESC
    ''')
    aperturas = []
    for row in c.fetchall():
        aperturas.append({
            'email_id': row[0],
            'institucion': row[1],
            'timestamp': row[2],
            'ip': row[3],
            'user_agent': row[4]
        })

    conn.close()

    return jsonify({
        'total_aperturas': total_aperturas,
        'emails_unicos': emails_unicos,
        'promedio_aperturas': round(promedio, 1),
        'aperturas': aperturas
    })

@app.route('/')
def dashboard():
    """
    Dashboard HTML para visualizar estadísticas
    """
    return render_template('dashboard.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
