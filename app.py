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
        dia +=Tienes toda la razón, perdí el enfoque; este sistema lo diseñamos exclusivamente para el control central de Subdirección, Coordinación y Alumnos, sin accesos ni asignaciones para docentes. Revisando tu base de datos en `image_411914.png`, confirmo que la estructura de grupos utiliza la nomenclatura exacta de 1, 2, 3, 4 y 1V.

He ajustado los valores de ejemplo y los campos de captura en el código para que reflejen esta realidad, manteniendo intacta toda la lógica y la arquitectura que ya construimos[cite: 1].

**Código Completo del Sistema (Actualizado)**

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

def obtener_dia_habil_anterior(fecha_actual):
    dia = fecha_actual - timedelta(days=1)
    while dia.weekday() > 4: # 5 es Sábado, 6 es Domingo
        dia -= timedelta(days=1)
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
        return False, str(e)

# ----------------- BASE DE DATOS SUPABASE -----------------
def inicializar_bd():
    with conn.session as session:
        session.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, contrasena TEXT, rol TEXT)"))
        
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS alumnos (
            matricula TEXT PRIMARY KEY, 
            nombre TEXT, 
            semestre INT, 
            grupo TEXT,
            correo_tutor TEXT,
            whatsapp_tutor TEXT
        )"""))

        session.execute(text("""
        CREATE TABLE IF NOT EXISTS calificaciones (
            id SERIAL PRIMARY KEY, 
            matricula TEXT, 
            semestre INT, 
            materia TEXT, 
            parcial1 REAL, 
            parcial2 REAL, 
            final REAL
        )"""))
        
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS reportes (
            id SERIAL PRIMARY KEY, 
            matricula TEXT, 
            semestre INT, 
            fecha TEXT, 
            motivo TEXT,
            metodo_notificacion TEXT,
            tipo_reporte TEXT DEFAULT 'Disciplinario'
        )"""))

        session.execute(text("CREATE TABLE IF NOT EXISTS ayuda (id SERIAL PRIMARY KEY, matricula TEXT, semestre INT, tipo_ayuda TEXT, observaciones TEXT)"))
        
        # AGREGAR COLUMNA DE AUDITORÍA (CAPTURISTA) SI NO EXISTE
        try:
            session.execute(text("ALTER TABLE reportes ADD COLUMN capturista TEXT DEFAULT 'Sistema'"))
        except:
            pass
            
        session.commit()
    
    df_count = conn.query("SELECT COUNT(*) AS total FROM usuarios", ttl=0)
    if df_count.iloc[0]['total'] == 0:
        with conn.session as session:
            session.execute(text("INSERT INTO usuarios VALUES ('arturo.subdirector', 'admin123', 'Subdirector') ON CONFLICT (usuario) DO NOTHING"))
            session.execute(text("INSERT INTO usuarios VALUES ('coordinacion.prepa', 'coord123', 'Coordinación') ON CONFLICT (usuario) DO NOTHING"))
            session.execute(text("INSERT INTO usuarios VALUES ('2026001', 'alumno123', 'Alumno/Padre') ON CONFLICT (usuario) DO NOTHING"))
            session.execute(text("INSERT INTO alumnos VALUES ('2026001', 'Juan Pérez Gómez', 3, '3', 'tutor.juan@gmail.com', '7221234567') ON CONFLICT (matricula) DO NOTHING"))
            session.execute(text("INSERT INTO alumnos VALUES ('2026002', 'María Luisa Hernández', 1, '1V', 'tutor.maria@gmail.com', '7229876543') ON CONFLICT (matricula) DO NOTHING"))
            session.commit()

inicializar_bd()

def obtener_lista_alumnos():
    df = conn.query("SELECT matricula, nombre, semestre, grupo, correo_tutor, whatsapp_tutor FROM alumnos ORDER BY nombre", ttl=0)
    return df.values.tolist()

# ----------------- AUTENTICACIÓN PERSISTENTE VÍA COOKIES -----------------
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario = None

cookie_user = cookie_manager.get(cookie="pem_usuario")
cookie_role = cookie_manager.get(cookie="pem_rol")

if cookie_user and cookie_role and not st.session_state.autenticado:
    st.session_state.autenticado = True
    st.session_state.usuario = cookie_user
    st.session_state.rol = cookie_role

if "links_masivos_wa" not in st.session_state:
    st.session_state.links_masivos_wa = []

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH): 
            st.image(LOGO_PATH, width=140)
    with col_titulo:
        st.title("Preparatoria Estado de México")
        st.subheader("Portal de Consulta y Control Escolar")
        
    with st.form("Login"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar al Sistema"):
            res = conn.query("SELECT rol FROM usuarios WHERE usuario = :u AND contrasena = :p", params={"u": usuario, "p": contrasena}, ttl=0)
            if not res.empty:
                rol_db = res.iloc[0]['rol']
                st.session_state.autenticado = True
                st.session_state.rol = rol_db
                st.session_state.usuario = usuario
                
                cookie_manager.set("pem_usuario", usuario, key="set_usr", expires_at=obtener_fecha_hora_mexico() + pd.Timedelta(days=7))
                cookie_manager.set("pem_rol", rol_db, key="set_rol", expires_at=obtener_fecha_hora_mexico() + pd.Timedelta(days=7))
                st.rerun()
            else: 
                st.error("Usuario o contraseña incorrectos.")
    st.caption(CREDITOS)
    st.stop()

# --- SIDEBAR & PUSH ---
if os.path.exists(LOGO_PATH): 
    st.sidebar.image(LOGO_PATH, width=150)
st.sidebar.markdown("<h3 style='text-align: center; color: #4B1C24;'>Prep. Estado de México</h3>", unsafe_allow_html=True)
st.sidebar.write(f"**Perfil:** {st.session_state.rol}")
st.sidebar.write(f"**Usuario:** {st.session_state.usuario}")

components.html(PWA_PUSH_SCRIPT, height=75)

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    # 1. Limpiar toda la memoria de la sesión actual
    st.session_state.clear()
    
    # 2. Forzar el borrado de cookies y recargar la página directamente desde el navegador
    js_cerrar_sesion = """
    <script>
        document.cookie = "pem_usuario=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "pem_rol=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.parent.location.reload();
    </script>
    """
    components.html(js_cerrar_sesion, height=0)

def calcular_reglas_boleta(p1, p2, ef_guardado):
    p1_v = float(p1) if p1 is not None and pd.notnull(p1) else 0.0
    p2_v = float(p2) if p2 is not None and pd.notnull(p2) else 0.0
    prom_parcial = (p1_v + p2_v) / 2
    
    if prom_parcial >= 8.0:
        ex_final_str = "N/A"
        prom_ordinario = prom_parcial
    elif 6.0 <= prom_parcial <= 7.9:
        ef_v = float(ef_guardado) if ef_guardado is not None and pd.notnull(ef_guardado) else 0.0
        ex_final_str = f"{ef_v:.1f}"
        prom_ordinario = (prom_parcial + ef_v) / 2 if ef_v > 0.0 else prom_parcial
    else:
        ex_final_str = "SD"
        ef_v = float(ef_guardado) if ef_guardado is not None and pd.notnull(ef_guardado) else 0.0
        prom_ordinario = (prom_parcial + ef_v) / 2 if ef_v > 0.0 else prom_parcial
        
    return prom_parcial, ex_final_str, prom_ordinario

def mostrar_boleta(matricula, nombre, grupo, semestre_selec):
    res = conn.query("SELECT materia, parcial1, parcial2, final FROM calificaciones WHERE matricula = :m AND semestre = :s", params={"m": matricula, "s": semestre_selec}, ttl=0)
    materias = res.values.tolist()
    
    if materias:
        datos_lista_pantalla, pdf_rows, suma_ordinarios = [], "", 0.0
        for m in materias:
            nom_mat, p1, p2, ef = m
            prom_p, ef_str, prom_o = calcular_reglas_boleta(p1, p2, ef)
            suma_ordinarios += prom_o
            p1_f = f"{float(p1):.1f}" if p1 is not None and pd.notnull(p1) else "0.0"
            p2_f = f"{float(p2):.1f}" if p2 is not None and pd.notnull(p2) else "0.0"
            
            datos_lista_pantalla.append({
                "Asignatura": nom_mat, "1º Parcial": p1_f, "2º Parcial": p2_f,
                "Prom. Parcial": f"{prom_p:.1f}", "Examen Final": ef_str, "Prom. Ordinario": f"{prom_o:.1f}"
            })
            
            pdf_rows += f"""
            <tr style='border-bottom: 1px solid #444;'>
                <td style='padding: 8px 10px; text-align: left; font-size: 11px;'><b>{nom_mat}</b></td>
                <td style='padding: 8px 10px; font-size: 11px;'>{p1_f}</td>
                <td style='padding: 8px 10px; font-size: 11px;'>{p2_f}</td>
                <td style='padding: 8px 10px; font-weight:bold; background-color:#f9f9f9; font-size: 11px;'>{prom_p:.1f}</td>
                <td style='padding: 8px 10px; font-size: 11px;'>{ef_str}</td>
                <td style='padding: 8px 10px; font-weight:bold; background-color:#e2f0d9; color:#1e4620; font-size: 11px;'>{prom_o:.1f}</td>
            </tr>"""
            
        promedio_general = suma_ordinarios / len(materias)
        st.subheader("📋 Boleta de Calificaciones en Pantalla")
        st.info(f"**Estudiante:** {nombre} | **Matrícula:** {matricula} | **Semestre:** {semestre_selec}° | **Grupo:** {grupo}")
        st.dataframe(pd.DataFrame(datos_lista_pantalla), use_container_width=True, hide_index=True)
        st.metric(label="🏆 Promedio General del Semestre", value=f"{promedio_general:.2f}")

        fecha_hoy = obtener_fecha_hora_mexico().strftime("%d/%m/%Y")
        logo_embed_html = obtener_base64_logo()
        
        img_tag = f'<img src="{logo_embed_html}" style="max-width: 100px; max-height: 100px; height: auto;">' if logo_embed_html else ''

        html_completo_pdf = f"""
        <div id="boleta-imprimir" style="padding: 20px; font-family: Arial, sans-serif; color: #000; width: 100%; max-width: 850px; margin: 0 auto; background: #fff;">
            <table style="width: 100%; border-bottom: 2px double #000; padding-bottom: 8px; margin-bottom: 15px;">
                <tr>
                    <td style="width: 20%; text-align: left; vertical-align: middle;">{img_tag}</td>
                    <td style="width: 80%; text-align: center; vertical-align: middle;">
                        <h2 style="margin: 0; font-size: 18px; font-weight: bold;">PREPARATORIA ESTADO DE MÉXICO</h2>
                        <h3 style="margin: 4px 0 0 0; font-size: 14px; font-weight: normal; color: #333;">BOLETA DE CALIFICACIONES OFICIAL</h3>
                        <p style="margin: 2px 0 0 0; font-size: 10px; color: #555;">Fecha de Emisión: {fecha_hoy}</p>
                    </td>
                </tr>
            </table>
            <table style="width: 100%; font-size: 11px; margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 8px;">
                <tr><td><b>Nombre del Alumno:</b> {nombre}</td><td><b>Matrícula Escolar:</b> {matricula}</td></tr>
                <tr><td><b>Semestre:</b> {semestre_selec}° Semestre</td><td><b>Grupo:</b> {grupo}</td></tr>
            </table>
            <table style="width: 100%; border-collapse: collapse; text-align: center; font-size: 11px;">
                <thead>
                    <tr style="background-color: #f2f2f2; border-top: 1.5px solid #000; border-bottom: 1.5px solid #000;">
                        <th style="padding: 10px 8px; text-align: left; width: 35%;">ASIGNATURA / MATERIA</th>
                        <th>1º PARCIAL</th><th>2º PARCIAL</th><th>PROM. PARCIAL</th><th>EXAMEN FINAL</th><th>PROMEDIO ORDINARIO</th>
                    </tr>
                </thead>
                <tbody>{pdf_rows}</tbody>
            </table>
            <div style="margin-top: 20px; text-align: right;">
                <span style="font-size: 13px; font-weight: bold; border: 1.5px solid #000; padding: 6px 14px; background-color: #fafafa;">
                    PROMEDIO GENERAL ACUMULADO: {promedio_general:.2f}
                </span>
            </div>
        </div>
        """
        st.write("---")
        components.html(f"""
        <script src="[https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js](https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js)"></script>
        
        <div style="position: absolute; left: -9999px; top: 0; width: 850px;">
            {html_completo_pdf}
        </div>

        <button onclick="descargarPDFHorizontal()" style="background-color: #198754; color: white; border: none; padding: 12px 24px; font-size: 14px; font-
