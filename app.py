#!/usr/bin/env python3
"""
Sistema de Tracking de Emails - Alianza ITSEIA-BYS
Backend Flask para registrar aperturas de emails y mostrar dashboard
Soporta PostgreSQL (producción) y SQLite (desarrollo)
"""

from flask import Flask, request, send_file, render_template, jsonify
from flask_cors import CORS
from datetime import datetime
import io
import os

app = Flask(__name__)
CORS(app)

# Detectar si estamos en producción (Render) o desarrollo (local)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("🐘 Usando PostgreSQL")
else:
    import sqlite3
    DATABASE = 'email_tracking.db'
    print("📁 Usando SQLite (desarrollo)")


def get_db_connection():
    """Obtiene conexión a la base de datos (PostgreSQL o SQLite)"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        return sqlite3.connect(DATABASE)


def init_db():
    """Inicializa la base de datos"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS email_opens (
                id SERIAL PRIMARY KEY,
                email_id TEXT NOT NULL,
                institucion TEXT,
                autoridad TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ PostgreSQL inicializado")
    else:
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
        print("✅ SQLite inicializado")


@app.route('/track/<email_id>.gif')
def track_email(email_id):
    """
    Pixel de tracking - registra cuando se abre el email
    """
    conn = get_db_connection()

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')

    # Extraer institución del email_id (formato: institucion_timestamp)
    parts = email_id.split('_')
    institucion = ' '.join(parts[:-1]).replace('-', ' ').title() if len(parts) > 1 else 'Desconocido'

    if USE_POSTGRES:
        c = conn.cursor()
        c.execute('''
            INSERT INTO email_opens (email_id, institucion, ip_address, user_agent)
            VALUES (%s, %s, %s, %s)
        ''', (email_id, institucion, ip_address, user_agent))
    else:
        c = conn.cursor()
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
    conn = get_db_connection()

    if USE_POSTGRES:
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
        rows = c.fetchall()
        aperturas = []
        for row in rows:
            aperturas.append({
                'email_id': row[0],
                'institucion': row[1],
                'timestamp': str(row[2]),
                'ip': row[3],
                'user_agent': row[4]
            })
    else:
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


@app.route('/health')
def health():
    """
    Health check endpoint
    """
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    return jsonify({
        'status': 'ok',
        'database': db_type
    })


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
