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
        print(f"📧 Preparando email para {RECIPIENT_EMAIL}...")

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

        # Enviar usando SSL con timeout más largo
        context = ssl.create_default_context()
        print(f"🔌 Conectando a {SMTP_SERVER}:{SMTP_PORT}...")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=30) as server:
            print(f"🔐 Autenticando con {SENDER_EMAIL}...")
            server.login(SENDER_EMAIL, APP_PASSWORD)

            print(f"📤 Enviando mensaje...")
            server.send_message(msg)
            print(f"✅ Email enviado exitosamente a {RECIPIENT_EMAIL}")

        return True

    except smtplib.SMTPException as e:
        print(f"❌ Error SMTP enviando email: {type(e).__name__} - {e}")
        return False
    except Exception as e:
        print(f"❌ Error general enviando email: {type(e).__name__} - {e}")
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


@app.route('/agendar-reunion')
def agendar_reunion():
    """
    Landing page con formulario para agendar reunión
    Esta página se abre cuando el usuario hace click en el email
    Usa EmailJS para envío de notificaciones
    """
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Agendar Reunión - Alianza ITSEIA-BYS</title>

        <!-- EmailJS SDK -->
        <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
        <script type="text/javascript">
            (function(){
                emailjs.init("A7cQPi8jRCDyLrHQr");
            })();
        </script>

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
                max-width: 600px;
                width: 100%;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            .header {
                text-align: center;
                margin-bottom: 35px;
            }
            .header h1 {
                color: #1F2F58;
                font-size: 28px;
                margin: 0 0 10px 0;
                font-weight: 800;
            }
            .header p {
                color: #64748b;
                font-size: 16px;
                margin: 0;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                color: #1F2F58;
                font-weight: 700;
                margin-bottom: 8px;
                font-size: 15px;
            }
            .form-group input,
            .form-group select {
                width: 100%;
                padding: 14px;
                border: 2px solid #22D3EE;
                border-radius: 8px;
                font-size: 15px;
                font-family: inherit;
                transition: all 0.3s ease;
                box-sizing: border-box;
            }
            .form-group input:focus,
            .form-group select:focus {
                outline: none;
                border-color: #0BDD0F;
                box-shadow: 0 0 0 3px rgba(11, 221, 15, 0.1);
            }
            .submit-button {
                background: linear-gradient(135deg, #0BDD0F 0%, #22D3EE 100%);
                color: white;
                padding: 18px 45px;
                border: none;
                font-weight: 800;
                font-size: 17px;
                border-radius: 12px;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s ease;
                box-shadow: 0 6px 20px rgba(11, 221, 15, 0.3);
            }
            .submit-button:hover {
                transform: translateY(-3px);
                box-shadow: 0 12px 32px rgba(11, 221, 15, 0.4);
            }
            .submit-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .info-box {
                background: #E8F5E9;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 25px;
                border-left: 4px solid #0BDD0F;
            }
            .info-box p {
                margin: 0;
                color: #1F2F58;
                font-size: 14px;
                line-height: 1.6;
            }
            @media only screen and (max-width: 600px) {
                .container { padding: 30px 20px; }
                body { padding: 10px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Agendar Reunión</h1>
                <p>Alianza Estratégica ITSEIA - Liceo BYS</p>
            </div>

            <div class="info-box">
                <p><strong>Complete este formulario</strong> y nos contactaremos con usted dentro de las próximas <strong>24 horas</strong> para confirmar la reunión.</p>
            </div>

            <form id="agendarForm" action="/formulario" method="POST">
                <div class="form-group">
                    <label for="nombre">Nombre de contacto *</label>
                    <input type="text" id="nombre" name="nombre" required placeholder="Ej: Juan Pérez">
                </div>

                <div class="form-group">
                    <label for="email">Email de contacto *</label>
                    <input type="email" id="email" name="email" required placeholder="Ej: juan.perez@colegio.edu.ec">
                </div>

                <div class="form-group">
                    <label for="institucion">Institución Educativa *</label>
                    <input type="text" id="institucion" name="institucion" required placeholder="Nombre del colegio">
                </div>

                <div class="form-group">
                    <label for="telefono">Teléfono de contacto *</label>
                    <input type="tel" id="telefono" name="telefono" required placeholder="Ej: 0987654321">
                </div>

                <div class="form-group">
                    <label for="dia">Día preferido para la visita *</label>
                    <select id="dia" name="dia" required>
                        <option value="">Seleccione un día</option>
                        <option value="Lunes">Lunes</option>
                        <option value="Martes">Martes</option>
                        <option value="Miércoles">Miércoles</option>
                        <option value="Jueves">Jueves</option>
                        <option value="Viernes">Viernes</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="horario">Horario preferido *</label>
                    <select id="horario" name="horario" required>
                        <option value="">Seleccione un horario</option>
                        <option value="08:00 - 10:00">08:00 - 10:00</option>
                        <option value="10:00 - 12:00">10:00 - 12:00</option>
                        <option value="14:00 - 16:00">14:00 - 16:00</option>
                        <option value="16:00 - 18:00">16:00 - 18:00</option>
                    </select>
                </div>

                <button type="submit" class="submit-button" id="submitBtn">
                    Agendar Reunión
                </button>
            </form>
        </div>

        <script>
            document.getElementById('agendarForm').addEventListener('submit', function(e) {
                e.preventDefault(); // Prevenir submit normal

                const btn = document.getElementById('submitBtn');
                btn.disabled = true;
                btn.textContent = 'Enviando...';

                // Obtener datos del formulario
                const formData = new FormData(this);
                const templateParams = {
                    nombre: formData.get('nombre'),
                    email: formData.get('email'),
                    institucion: formData.get('institucion'),
                    telefono: formData.get('telefono'),
                    dia: formData.get('dia'),
                    horario: formData.get('horario')
                };

                console.log('📧 Enviando con EmailJS...', templateParams);

                // Enviar con EmailJS
                emailjs.send('service_yqv4dts', 'template_alianza_itseia_', templateParams)
                    .then(function(response) {
                        console.log('✅ EmailJS SUCCESS!', response.status, response.text);

                        // Ahora guardar en nuestra base de datos
                        return fetch('/formulario', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(templateParams)
                        });
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('✅ Guardado en BD:', data);
                        // Redirigir a página de éxito
                        window.location.href = '/formulario-enviado';
                    })
                    .catch(function(error) {
                        console.error('❌ ERROR:', error);
                        alert('Hubo un error al enviar el formulario. Por favor intente nuevamente o contáctenos directamente.');
                        btn.disabled = false;
                        btn.textContent = 'Agendar Reunión';
                    });
            });
        </script>
    </body>
    </html>
    '''


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

        print(f"✅ Datos guardados en BD para: {data.get('institucion')}")

        # EmailJS se encarga del envío de notificaciones desde el frontend
        # Ya no necesitamos enviar SMTP desde el backend
        print("📧 Email de notificación enviado por EmailJS desde el cliente")

        # Retornar respuesta según el tipo de request
        if request.is_json:
            # Request JSON - retornar JSON
            return jsonify({'success': True, 'message': 'Solicitud recibida. Nos contactaremos pronto.'})
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


@app.route('/formulario-enviado')
def formulario_enviado():
    """
    Página de confirmación después de enviar el formulario
    """
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
