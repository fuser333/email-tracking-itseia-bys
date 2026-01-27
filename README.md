# Sistema de Tracking de Emails - Alianza ITSEIA-BYS

Sistema completo para rastrear aperturas de emails de la campaña de alianza estratégica ITSEIA - Liceo BYS.

## Características

- ✅ Tracking de aperturas mediante pixel invisible
- ✅ Dashboard en tiempo real con estadísticas
- ✅ Registro de IP, User-Agent y timestamp
- ✅ Base de datos SQLite
- ✅ Listo para deploy en Render

## Deployment en Render

### 1. Subir a GitHub

```bash
cd email_tracking_system
git init
git add .
git commit -m "Sistema de tracking de emails ITSEIA-BYS"
git branch -M main
git remote add origin [TU_REPO_URL]
git push -u origin main
```

### 2. Conectar con Render

1. Ve a https://render.com
2. Click en "New" → "Web Service"
3. Conecta tu repositorio de GitHub
4. Render detectará automáticamente el `render.yaml`
5. Click en "Create Web Service"

### 3. Obtener la URL

Una vez deployado, Render te dará una URL como:
```
https://email-tracking-itseia-bys.onrender.com
```

### 4. Usar en los Emails

El pixel de tracking se inserta en el HTML del email así:

```html
<img src="https://email-tracking-itseia-bys.onrender.com/track/[EMAIL_ID].gif"
     width="1" height="1" style="display:none">
```

Donde `[EMAIL_ID]` es un identificador único por email (ej: `colegio-san-jose_1234567890`)

### 5. Ver el Dashboard

Accede a:
```
https://email-tracking-itseia-bys.onrender.com/
```

## Endpoints

- `GET /` - Dashboard de estadísticas
- `GET /track/<email_id>.gif` - Pixel de tracking
- `GET /stats` - API JSON con estadísticas

## Desarrollo Local

```bash
pip install -r requirements.txt
python app.py
```

El servidor correrá en `http://localhost:10000`

## Estructura de la Base de Datos

```sql
CREATE TABLE email_opens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL,
    institucion TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);
```

## Autor

Instituto Ecuatoriano de Inteligencia Artificial (ITSEIA) - 2026
