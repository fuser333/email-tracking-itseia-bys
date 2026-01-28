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
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# Configuración SMTP para enviar emails desde el formulario
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "vicerrectorado@liceobys.edu.ec"
APP_PASSWORD = "kppm abst dddy wago"
RECIPIENT_EMAIL = "administracion@itseia.ai"

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
        c.execute('''
            CREATE TABLE IF NOT EXISTS formulario_contacto (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                institucion TEXT,
                telefono TEXT,
                dia TEXT,
                horario TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS formulario_contacto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                institucion TEXT,
                telefono TEXT,
                dia TEXT,
                horario TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ SQLite inicializado")


def enviar_email_formulario(data):
    """
    Envía un email con los datos del formulario a administracion@itseia.ai
    """
    try:
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎯 Nueva solicitud de reunión - {data.get('institucion', 'Sin institución')}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL

        # Cuerpo del email en HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9; }}
                .header {{ background: linear-gradient(135deg, #1F2F58 0%, #22D3EE 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
                .field {{ margin: 15px 0; padding: 12px; background: #f0f7ff; border-left: 4px solid #22D3EE; }}
                .field strong {{ color: #1F2F58; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📩 Nueva Solicitud de Reunión</h1>
                    <p>Alianza ITSEIA - Liceo BYS</p>
                </div>
                <div class="content">
                    <h2 style="color: #1F2F58;">Datos del Contacto:</h2>

                    <div class="field">
                        <strong>👤 Nombre:</strong> {data.get('nombre', 'No proporcionado')}
                    </div>

                    <div class="field">
                        <strong>📧 Email:</strong> {data.get('email', 'No proporcionado')}
                    </div>

                    <div class="field">
                        <strong>🏫 Institución:</strong> {data.get('institucion', 'No proporcionado')}
                    </div>

                    <div class="field">
                        <strong>📱 Teléfono:</strong> {data.get('telefono', 'No proporcionado')}
                    </div>

                    <div class="field">
                        <strong>📅 Día preferido:</strong> {data.get('dia', 'No proporcionado')}
                    </div>

                    <div class="field">
                        <strong>🕐 Horario preferido:</strong> {data.get('horario', 'No proporcionado')}
                    </div>

                    <p style="margin-top: 25px; padding: 15px; background: #e8f5e9; border-radius: 8px; color: #2e7d32;">
                        <strong>✓ Acción requerida:</strong> Contactar a esta institución para coordinar la reunión.
                    </p>
                </div>
                <div class="footer">
                    <p>Este email fue enviado automáticamente desde el formulario de contacto</p>
                    <p>Alianza Estratégica ITSEIA - Liceo Brigham Young School</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Adjuntar HTML
        msg.attach(MIMEText(html_content, 'html'))

        # Enviar usando SSL
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email enviado a {RECIPIENT_EMAIL} - Institución: {data.get('institucion')}")
        return True

    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False


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


@app.route('/formulario', methods=['POST'])
def formulario():
    """
    Endpoint para recibir datos del formulario de contacto
    Acepta tanto JSON (para APIs) como form-data (para formularios HTML)
    """
    try:
        # Detectar si es JSON o form-data
        if request.is_json:
            data = request.json
        else:
            # Formulario HTML normal (form-data)
            data = {
                'nombre': request.form.get('nombre'),
                'email': request.form.get('email'),
                'institucion': request.form.get('institucion'),
                'telefono': request.form.get('telefono'),
                'dia': request.form.get('dia'),
                'horario': request.form.get('horario')
            }

        # Asegurar que las tablas existen antes de insertar
        try:
            init_db()
        except:
            pass  # Si ya existen, continuar

        # Guardar en base de datos
        conn = get_db_connection()

        if USE_POSTGRES:
            c = conn.cursor()
            c.execute('''
                INSERT INTO formulario_contacto (nombre, email, institucion, telefono, dia, horario, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (data.get('nombre'), data.get('email'), data.get('institucion'),
                  data.get('telefono'), data.get('dia'), data.get('horario')))
        else:
            c = conn.cursor()
            c.execute('''
                INSERT INTO formulario_contacto (nombre, email, institucion, telefono, dia, horario, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (data.get('nombre'), data.get('email'), data.get('institucion'),
                  data.get('telefono'), data.get('dia'), data.get('horario')))

        conn.commit()
        conn.close()

        # Enviar email a administracion@itseia.ai
        email_enviado = enviar_email_formulario(data)

        # Retornar respuesta según el tipo de request
        if request.is_json:
            # Request JSON - retornar JSON
            if email_enviado:
                return jsonify({'success': True, 'message': 'Solicitud recibida. Nos contactaremos pronto.'})
            else:
                return jsonify({'success': True, 'message': 'Solicitud guardada, pero hubo un problema enviando la notificación.'})
        else:
            # Formulario HTML - retornar página de éxito
            return '''
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Solicitud Recibida - ITSEIA</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                        background: linear-gradient(135deg, #1F2F58 0%, #22D3EE 100%);
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                    }
                    .container {
                        background: white;
                        max-width: 500px;
                        padding: 50px 40px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                    }
                    .checkmark {
                        width: 80px;
                        height: 80px;
                        border-radius: 50%;
                        background: linear-gradient(135deg, #0BDD0F 0%, #22D3EE 100%);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0 auto 30px;
                        font-size: 48px;
                        color: white;
                        box-shadow: 0 8px 24px rgba(11, 221, 15, 0.4);
                    }
                    h1 {
                        color: #1F2F58;
                        font-size: 28px;
                        margin: 0 0 15px 0;
                        font-weight: 800;
                    }
                    p {
                        color: #334155;
                        font-size: 16px;
                        line-height: 1.6;
                        margin: 15px 0;
                    }
                    .highlight {
                        background: #E8F5E9;
                        padding: 20px;
                        border-radius: 12px;
                        margin: 25px 0;
                        border-left: 4px solid #0BDD0F;
                    }
                    .highlight strong {
                        color: #1F2F58;
                        font-size: 18px;
                    }
                    .contact {
                        margin-top: 30px;
                        padding-top: 25px;
                        border-top: 2px solid #E0E7FF;
                        font-size: 14px;
                        color: #64748b;
                    }
                    .contact a {
                        color: #22D3EE;
                        text-decoration: none;
                        font-weight: 600;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="checkmark">✓</div>
                    <h1>¡Solicitud Recibida Exitosamente!</h1>
                    <p>Gracias por su interés en la <strong>Alianza Estratégica ITSEIA - Liceo BYS</strong>.</p>

                    <div class="highlight">
                        <strong>📞 Nos contactaremos con usted</strong><br>
                        dentro de las próximas <strong>24 horas</strong> para confirmar su reunión.
                    </div>

                    <p>Hemos registrado su solicitud y enviado una notificación a nuestro equipo.</p>

                    <div class="contact">
                        <p><strong>Información de Contacto:</strong></p>
                        <p>📧 <a href="mailto:administracion@itseia.ai">administracion@itseia.ai</a></p>
                        <p>📱 WhatsApp: <a href="https://wa.me/593959892034">+593 95 989 2034</a></p>
                        <p>🌐 <a href="https://itseia.ai" target="_blank">www.itseia.ai</a></p>
                    </div>

                    <p style="margin-top: 30px; font-size: 12px; color: #94a3b8;">
                        Puede cerrar esta ventana
                    </p>
                </div>
            </body>
            </html>
            '''
    except Exception as e:
        print(f"Error en formulario: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/setup-db')
def setup_db():
    """
    Endpoint para forzar la creación de tablas (ejecutar una sola vez)
    """
    try:
        init_db()
        return jsonify({'success': True, 'message': 'Database initialized successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
