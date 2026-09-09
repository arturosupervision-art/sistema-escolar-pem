import os
import time
import base64
import io
import smtplib
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

# Definir la ruta exacta de la imagen para Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo 172.png")

# ==============================================================================
# CONFIGURACIÓN DE SERVICIOS Y PÁGINA
# ==============================================================================
CORREO_EMISOR = "notificaciones@pem.edu.mx"
PASSWORD_CORREO = "mqtxcnxwycqflxip"

st.set_page_config(page_title="Sistema Control Escolar - Prep. Edo. de México", layout="wide")
CREDITOS = "Sistema diseñado por: LEM Arturo Javier Diaz Salazar, Subdirector Académico de la Preparatoria Estado de México."

# Inicializar conexión a Supabase
conn = st.connection("supabase", type="sql")

# Función helper para obtener siempre la hora exacta de CDMX / Edo. Méx.
def obtener_fecha_hora_mexico():
    return datetime.now(ZoneInfo("America/Mexico_City"))

def obtener_siguiente_dia_habil(fecha_actual):
    dia = fecha_actual + timedelta(days=1)
    while dia.weekday() > 4: # 5 es Sábado, 6 es Domingo
        dia += timedelta(days=1)
    return dia

# ----------------- ADMINISTRADOR DE COOKIES -----------------
def get_cookie_manager():
    return stx.CookieManager(key="cookie_manager_pem")

cookie_manager = get_cookie_manager()

# ----------------- SCRIPT PWA & NOTIFICACIONES PUSH -----------------
PWA_PUSH_SCRIPT = """
<script>
  if ('serviceWorker' in navigator && 'PushManager' in window) {
    navigator.serviceWorker.register('/sw.js').then(function(reg) {
      console.log('Service Worker Registrado Exitosamente.', reg);
    }).catch(function(err) {
      console.log('Error registrando Service Worker:', err);
    });
  }

  function solicitarPermisoPush() {
    if ('Notification' in window) {
      Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') {
          new Notification("🏛️ Prep. Estado de México", {
            body: "¡Notificaciones Push activadas en tu dispositivo!",
            icon: "/logo.png"
          });
        }
      });
    }
  }
</script>
<div style="background-color: #f0f7ff; border: 1px solid #b6d4fe; border-radius: 8px; padding: 10px; margin-bottom: 15px; text-align: center;">
    <span style="font-size: 13px; color: #084298; font-weight: bold;">📱 Instalación y Notificaciones Celular:</span>
    <button onclick="solicitarPermisoPush()" style="background-color: #0d6efd; color: white; border: none; padding: 6px 12px; margin-left: 10px; border-radius: 4px; font-size: 12px; cursor: pointer; font-weight: bold;">
        🔔 Activar Notificaciones Push en este Celular
    </button>
</div>
"""

MOTIVOS_ACADEMICOS = [
    "I Inasistencia",
    "II Sin material",
    "III Retardo",
    "IV Vocabulario Inapropiado",
    "V Indisciplina",
    "VI No trabajo en clase",
    "VII Incumplimiento de tareas",
    "VIII Tarea incompleta",
    "Otro motivo (especificar)"
]

OPCIONES_NOTIFICACION_DISCIPLINARIO = [
    "Mensaje de WhatsApp",
    "Llamada Telefónica",
    "Visita a la Institución",
    "Correo Electrónico",
    "Citatorio Firmado en Físico",
    "Multicanal / Portal Web"
]

def obtener_base64_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    return ""

# DICCIONARIO OFICIAL UAEMEX
MATERIAS_POR_SEMESTRE = {
    1: ['LENGUA Y COMUNICACION I', 'INGLES I', 'CULTURA DIGITAL', 'PENSAMIENTO MATEMATICO I', 'QUIMICA I', 'HUMANIDADES I', 'CIENCIAS SOCIALES I', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES I', 'ACTIVIDADES FISICAS Y DEPORTIVAS I'],
    2: ['LENGUA Y COMUNICACION II', 'INGLES II', 'PENSAMIENTO MATEMATICO II', 'FISICA I', 'HUMANIDADES II', 'CIENCIAS SOCIALES II', 'DESARROLLO PERSONAL Y EMOCIONAL', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES II', 'ACTIVIDADES FISICAS Y DEPORTIVAS II'],
    3: ['LENGUA Y COMUNICACION III', 'INGLES III', 'PENSAMIENTO MATEMATICO III', 'BIOLOGIA I', 'HUMANIDADES III', 'METODOLOGIA Y TALLER DE INVESTIGACION I', 'DESARROLLO SOCIAL', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES III', 'ACTIVIDADES FISICAS Y DEPORTIVAS III'],
    4: ['LITERATURA', 'INGLES IV', 'TEMAS SELECTOS DE MATEMATICAS I', 'CONCIENCIA HISTORICA I', 'QUIMICA II', 'CULTURA AMBIENTAL Y DESARROLLO SOSTENIBLE', 'METODOLOGIA Y TALLER DE INVESTIGACION II', 'ORIENTACION VOCACIONAL', 'ACTIVIDADES FISICAS Y DEPORTIVAS IV'],
    5: ['TEMAS SELECTOS DE MATEMATICAS II', 'CONCIENCIA HISTORICA II', 'FISICA II', 'GEOGRAFIA', 'APRECIACION Y EXPRESION DEL ARTE I', 'CULTURA DE PAZ', 'CALCULO INTEGRAL', 'TALLER DE LENGUA GRECOLATINA', 'ESTRATEGIAS PARA LA COMPRENSION LECTORA EN INGLES', 'BIOLOGIA Y SALUD', 'TOPICOS DE QUIMICA I', 'PROBLEMATICA SOCIAL Y SU REGULACION JURIDICA', 'ESTRATEGIAS PARA LA RESOLUCION DE PROBLEMAS Y TOMA DE DECISIONES', 'APLICACIONES PRACTICAS DEL DIBUJO', 'FILOSOFIA CONTEMPORANEA', 'ECONOMIA', 'ADMINISTRACION'],
    6: ['TEMAS SELECTOS DE MATEMATICAS III', 'CONCIENCIA HISTORICA III', 'BIOLOGIA II', 'APRECIACION Y EXPRESION DEL ARTE II', 'PSICOLOGIA', 'DESARROLLO EMPRENDEDOR', 'PRINCIPIOS DE ALGEBRA LINEAL', 'COMUNICACION Y DISCURSO', 'CERTIFICACION INTERNACIONAL DE INGLES', 'COMPUTACION APLICADA A LA PROGRAMACION', 'INFORMATICA Y APLICACIONES WEB', 'BIOLOGIA COMPARADA', 'TOPICOS DE QUIMICA II', 'FISICA ONDULATORIA Y ESTATICA', 'LIDERAZGO', 'DISEÑO', 'CONTABILIDAD Y FINANZAS']
}

# ----------------- FUNCIONES DE NOTIFICACIÓN & EVIDENCIA GLOBAL -----------------
def generar_link_whatsapp(telefono, nombre_alumno, tipo_evento, detalle):
    if not telefono or str(telefono).strip() in ["", "None", "0"]:
        return None
    tel_limpio = "".join(filter(str.isdigit, str(telefono)))
    if len(tel_limpio) == 10:
        tel_limpio = "521" + tel_limpio
    
    fecha_mx = obtener_fecha_hora_mexico().strftime('%d/%m/%Y %H:%M')
    
    texto = (
        f"🎓 *PREPARATORIA ESTADO DE MÉXICO*\n"
        f"_Subdirección Académica_\n\n"
        f"Estimado tutor, le enviamos un aviso importante sobre el alumno(a):\n"
        f"👤 *{nombre_alumno}*\n\n"
        f"📋 *Tipo de Registro:* {tipo_evento}\n"
        f"📝 *Detalle/Motivo:* {detalle}\n"
        f"🗓️ *Fecha y Hora:* {fecha_mx}\n\n"
        f"ℹ️ _Para cualquier duda o aclaración, favor de acudir a las instalaciones de la institución._"
    )
    
    texto_enc = urllib.parse.quote(texto)
    return f"https://api.whatsapp.com/send?phone={tel_limpio}&text={texto_enc}"

def renderizar_lista_enlaces_whatsapp(lista_links):
    if not lista_links:
        return
    st.markdown("---")
    st.markdown("### 💬 Opciones para Enviar por WhatsApp")
    for item in lista_links:
        col_a, col_b = st.columns([3, 1])
        with col_a: 
            st.write(f"👤 **{item['Alumno']}** ({item['Matrícula']}) — *{item['Detalle']}*")
        with col_b: 
            if item.get('Link'):
                st.link_button("💬 Enviar WhatsApp", item["Link"], type="primary")
            else:
                st.caption("⚠️ Sin teléfono válido")

def enviar_notificacion_correo(correo_tutor, nombre_alumno, matricula, tipo_evento, detalle_texto):
    if not correo_tutor or "@" not in str(correo_tutor):
        return False, "Sin correo registrado para el tutor."
        
    try:
        msg = MIMEMultipart() 

```python
import os
import time
import base64
import io
import smtplib
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

# Definir la ruta exacta de la imagen para Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo 172.png")

# ==============================================================================
# CONFIGURACIÓN DE SERVICIOS Y PÁGINA
# ==============================================================================
CORREO_EMISOR = "notificaciones@pem.edu.mx"
PASSWORD_CORREO = "mqtxcnxwycqflxip"

st.set_page_config(page_title="Sistema Control Escolar - Prep. Edo. de México", layout="wide")
CREDITOS = "Sistema diseñado por: LEM Arturo Javier Diaz Salazar, Subdirector Académico de la Preparatoria Estado de México."

# Inicializar conexión a Supabase
conn = st.connection("supabase", type="sql")

# Función helper para obtener siempre la hora exacta de CDMX / Edo. Méx.
def obtener_fecha_hora_mexico():
    return datetime.now(ZoneInfo("America/Mexico_City"))

def obtener_siguiente_dia_habil(fecha_actual):
    dia = fecha_actual + timedelta(days=1)
    while dia.weekday() > 4: # 5 es Sábado, 6 es Domingo
        dia += timedelta(days=1)
    return dia

# ----------------- ADMINISTRADOR DE COOKIES -----------------
def get_cookie_manager():
    return stx.CookieManager(key="cookie_manager_pem")

cookie_manager = get_cookie_manager()

# ----------------- SCRIPT PWA & NOTIFICACIONES PUSH -----------------
PWA_PUSH_SCRIPT = """
<script>
  if ('serviceWorker' in navigator && 'PushManager' in window) {
    navigator.serviceWorker.register('/sw.js').then(function(reg) {
      console.log('Service Worker Registrado Exitosamente.', reg);
    }).catch(function(err) {
      console.log('Error registrando Service Worker:', err);
    });
  }

  function solicitarPermisoPush() {
    if ('Notification' in window) {
      Notification.requestPermission().then(function(permission) {
        if (permission === 'granted') {
          new Notification("🏛️ Prep. Estado de México", {
            body: "¡Notificaciones Push activadas en tu dispositivo!",
            icon: "/logo.png"
          });
        }
      });
    }
  }
</script>
<div style="background-color: #f0f7ff; border: 1px solid #b6d4fe; border-radius: 8px; padding: 10px; margin-bottom: 15px; text-align: center;">
    <span style="font-size: 13px; color: #084298; font-weight: bold;">📱 Instalación y Notificaciones Celular:</span>
    <button onclick="solicitarPermisoPush()" style="background-color: #0d6efd; color: white; border: none; padding: 6px 12px; margin-left: 10px; border-radius: 4px; font-size: 12px; cursor: pointer; font-weight: bold;">
        🔔 Activar Notificaciones Push en este Celular
    </button>
</div>
"""

MOTIVOS_ACADEMICOS = [
    "I Inasistencia",
    "II Sin material",
    "III Retardo",
    "IV Vocabulario Inapropiado",
    "V Indisciplina",
    "VI No trabajo en clase",
    "VII Incumplimiento de tareas",
    "VIII Tarea incompleta",
    "Otro motivo (especificar)"
]

OPCIONES_NOTIFICACION_DISCIPLINARIO = [
    "Mensaje de WhatsApp",
    "Llamada Telefónica",
    "Visita a la Institución",
    "Correo Electrónico",
    "Citatorio Firmado en Físico",
    "Multicanal / Portal Web"
]

def obtener_base64_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    return ""

# DICCIONARIO OFICIAL UAEMEX
MATERIAS_POR_SEMESTRE = {
    1: ['LENGUA Y COMUNICACION I', 'INGLES I', 'CULTURA DIGITAL', 'PENSAMIENTO MATEMATICO I', 'QUIMICA I', 'HUMANIDADES I', 'CIENCIAS SOCIALES I', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES I', 'ACTIVIDADES FISICAS Y DEPORTIVAS I'],
    2: ['LENGUA Y COMUNICACION II', 'INGLES II', 'PENSAMIENTO MATEMATICO II', 'FISICA I', 'HUMANIDADES II', 'CIENCIAS SOCIALES II', 'DESARROLLO PERSONAL Y EMOCIONAL', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES II', 'ACTIVIDADES FISICAS Y DEPORTIVAS II'],
    3: ['LENGUA Y COMUNICACION III', 'INGLES III', 'PENSAMIENTO MATEMATICO III', 'BIOLOGIA I', 'HUMANIDADES III', 'METODOLOGIA Y TALLER DE INVESTIGACION I', 'DESARROLLO SOCIAL', 'RECURSOS Y AMBITOS SOCIOEMOCIONALES III', 'ACTIVIDADES FISICAS Y DEPORTIVAS III'],
    4: ['LITERATURA', 'INGLES IV', 'TEMAS SELECTOS DE MATEMATICAS I', 'CONCIENCIA HISTORICA I', 'QUIMICA II', 'CULTURA AMBIENTAL Y DESARROLLO SOSTENIBLE', 'METODOLOGIA Y TALLER DE INVESTIGACION II', 'ORIENTACION VOCACIONAL', 'ACTIVIDADES FISICAS Y DEPORTIVAS IV'],
    5: ['TEMAS SELECTOS DE MATEMATICAS II', 'CONCIENCIA HISTORICA II', 'FISICA II', 'GEOGRAFIA', 'APRECIACION Y EXPRESION DEL ARTE I', 'CULTURA DE PAZ', 'CALCULO INTEGRAL', 'TALLER DE LENGUA GRECOLATINA', 'ESTRATEGIAS PARA LA COMPRENSION LECTORA EN INGLES', 'BIOLOGIA Y SALUD', 'TOPICOS DE QUIMICA I', 'PROBLEMATICA SOCIAL Y SU REGULACION JURIDICA', 'ESTRATEGIAS PARA LA RESOLUCION DE PROBLEMAS Y TOMA DE DECISIONES', 'APLICACIONES PRACTICAS DEL DIBUJO', 'FILOSOFIA CONTEMPORANEA', 'ECONOMIA', 'ADMINISTRACION'],
    6: ['TEMAS SELECTOS DE MATEMATICAS III', 'CONCIENCIA HISTORICA III', 'BIOLOGIA II', 'APRECIACION Y EXPRESION DEL ARTE II', 'PSICOLOGIA', 'DESARROLLO EMPRENDEDOR', 'PRINCIPIOS DE ALGEBRA LINEAL', 'COMUNICACION Y DISCURSO', 'CERTIFICACION INTERNACIONAL DE INGLES', 'COMPUTACION APLICADA A LA PROGRAMACION', 'INFORMATICA Y APLICACIONES WEB', 'BIOLOGIA COMPARADA', 'TOPICOS DE QUIMICA II', 'FISICA ONDULATORIA Y ESTATICA', 'LIDERAZGO', 'DISEÑO', 'CONTABILIDAD Y FINANZAS']
}

# ----------------- FUNCIONES DE NOTIFICACIÓN & EVIDENCIA GLOBAL -----------------
def generar_link_whatsapp(telefono, nombre_alumno, tipo_evento, detalle):
    if not telefono or str(telefono).strip() in ["", "None", "0"]:
        return None
    tel_limpio = "".join(filter(str.isdigit, str(telefono)))
    if len(tel_limpio) == 10:
        tel_limpio = "521" + tel_limpio
    
    fecha_mx = obtener_fecha_hora_mexico().strftime('%d/%m/%Y %H:%M')
    
    texto = (
        f"🎓 *PREPARATORIA ESTADO DE MÉXICO*\n"
        f"_Subdirección Académica_\n\n"
        f"Estimado tutor, le enviamos un aviso importante sobre el alumno(a):\n"
        f"👤 *{nombre_alumno}*\n\n"
        f"📋 *Tipo de Registro:* {tipo_evento}\n"
        f"📝 *Detalle/Motivo:* {detalle}\n"
        f"🗓️ *Fecha y Hora:* {fecha_mx}\n\n"
        f"ℹ️ _Para cualquier duda o aclaración, favor de acudir a las instalaciones de la institución._"
    )
    
    texto_enc = urllib.parse.quote(texto)
    return f"[https://api.whatsapp.com/send?phone=](https://api.whatsapp.com/send?phone=){tel_limpio}&text={texto_enc}"

def renderizar_lista_enlaces_whatsapp(lista_links):
    if not lista_links:
        return
    st.markdown("---")
    st.markdown("### 💬 Opciones para Enviar por WhatsApp")
    for item in lista_links:
        col_a, col_b = st.columns([3, 1])
        with col_a: 
            st.write(f"👤 **{item['Alumno']}** ({item['Matrícula']}) — *{item['Detalle']}*")
        with col_b: 
            if item.get('Link'):
                st.link_button("💬 Enviar WhatsApp", item["Link"], type="primary")
            else:
                st.caption("⚠️ Sin teléfono válido")

def enviar_notificacion_correo(correo_tutor, nombre_alumno, matricula, tipo_evento, detalle_texto):
    if not correo_tutor or "@" not in str(correo_tutor):
        return False, "Sin correo registrado para el tutor."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Preparatoria Estado de México <{CORREO_EMISOR}>"
        msg['To'] = correo_tutor
        msg['Subject'] = f"[Notificación Escolar] Actualización para {nombre_alumno}"

        fecha_hoy = obtener_fecha_hora_mexico().strftime("%d/%m/%Y %H:%M")

        cuerpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px;">
                <h2 style="color: #4B1C24; border-bottom: 2px solid #4B1C24; padding-bottom: 8px; margin-top:0;">
                    Preparatoria Estado de México
                </h2>
                <p><b>Estimado(a) Padre, Madre de Familia o Tutor:</b></p>
                <p>Por medio del presente conducto, la Subdirección Académica le notifica un registro en el expediente de su hijo(a):</p>
                
                <div style="background-color: #f9f9f9; padding: 12px; border-left: 4px solid #4B1C24; margin: 15px 0;">
                    <p style="margin: 3px 0;"><b>Estudiante:</b> {nombre_alumno}</p>
                    <p style="margin: 3px 0;"><b>Matrícula:</b> {matricula}</p>
                    <p style="margin: 3px 0;"><b>Tipo de Registro:</b> <span style="color: #198754; font-weight:bold;">{tipo_evento}</span></p>
                    <p style="margin: 3px 0;"><b>Fecha y Hora:</b> {fecha_hoy}</p>
                </div>

                <p><b>Detalles de la actualización:</b></p>
                <p style="background: #fff; border: 1px solid #eee; padding: 10px; border-radius: 4px;">{detalle_texto}</p>

                <p style="font-size: 12px; color: #666; margin-top: 25px;">
                    Le recordamos que puede verificar el historial completo ingresando al portal escolar.
                </p>
                <hr style="border: 0; border-top: 1px solid #ccc;">
                <p style="font-size: 11px; color: #888; text-align: center;">
                    <b>LEM Arturo Javier Diaz Salazar</b><br>Subdirector Académico
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(cuerpo_html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(CORREO_EMISOR, PASSWORD_CORREO.replace(" ", ""))
        server.sendmail(CORREO_EMISOR, correo_tutor, msg.as_string())
        server.quit()
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, str(No te preocupes, es completamente normal querer ir a lo seguro. Aquí tienes el código completo de tu archivo **app (6)_3.py** listo para que lo copies y pegues sin que falte ningún detalle[cite: 1]:
