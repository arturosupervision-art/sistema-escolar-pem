import os
import base64
import io
import smtplib
import sqlite3
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Definir la ruta exacta de la imagen para Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo 172.png")

# ==============================================================================
# CONFIGURACIÓN DE SERVICIOS Y PÁGINA
# ==============================================================================
CORREO_EMISOR = "notificaciones@pem.edu.mx"
PASSWORD_CORREO = "mqtxcnxwycqflxip"

# Función helper para obtener siempre la hora exacta de CDMX / Edo. Méx.
def obtener_fecha_hora_mexico():
    return datetime.now(ZoneInfo("America/Mexico_City"))

st.set_page_config(page_title="Sistema Control Escolar - Prep. Edo. de México", layout="wide")
CREDITOS = "Sistema diseñado por: LEM Arturo Javier Diaz Salazar, Subdirector Académico de la Preparatoria Estado de México."

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

MATERIAS_POR_SEMESTRE = {
    1: ["MATEMATICAS", "ESPAÑOL"],
    2: ["MATEMATICAS II", "ESPAÑOL II"],
    3: ["MATEMATICAS III", "ESPAÑOL III"],
    4: ["MATEMATICAS IV", "ESPAÑOL IV"],
    5: ["MATEMATICAS V", "ESPAÑOL V"],
    6: ["MATEMATICAS VI", "ESPAÑOL VI"]
}

# ----------------- FUNCIONES DE NOTIFICACIÓN & EVIDENCIA GLOBAL -----------------
def generar_link_whatsapp(telefono, nombre_alumno, tipo_evento, detalle):
    if not telefono or str(telefono).strip() in ["", "None", "0"]:
        return None
    tel_limpio = "".join(filter(str.isdigit, str(telefono)))
    if len(tel_limpio) == 10:
        tel_limpio = "521" + tel_limpio
    
    fecha_mx = obtener_fecha_hora_mexico().strftime('%d/%m/%Y %H:%M')
    
    # Texto con diseño Ejecutivo y Elegante con emojis 100% compatibles
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
    # Codificación UTF-8 para evitar los caracteres raros en la URL
    texto_enc = urllib.parse.quote(texto, encoding='utf-8')
    return f"https://wa.me/{tel_limpio}?text={texto_enc}"

def renderizar_lista_enlaces_whatsapp(lista_links):
    """Muestra una tarjeta por cada registro para enviar WhatsApp individualmente"""
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
                st.markdown(f'<a href="{item["Link"]}" target="_blank" style="background-color:#25D366; color:white; padding:6px 12px; text-decoration:none; border-radius:5px; font-size:13px; font-weight:bold; display:inline-block;">💬 Enviar WhatsApp</a>', unsafe_allow_html=True)
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

# ----------------- BASE DE DATOS -----------------
def inicializar_bd():
    conn = sqlite3.connect("sistema_escolar.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, contrasena TEXT, rol TEXT)")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        matricula TEXT PRIMARY KEY, 
        nombre TEXT, 
        semestre INT, 
        grupo TEXT,
        correo_tutor TEXT,
        whatsapp_tutor TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calificaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        matricula TEXT, 
        semestre INT, 
        materia TEXT, 
        parcial1 REAL, 
        parcial2 REAL, 
        final REAL
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reportes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        matricula TEXT, 
        semestre INT, 
        fecha TEXT, 
        motivo TEXT,
        metodo_notificacion TEXT,
        tipo_reporte TEXT DEFAULT 'Disciplinario'
    )""")

    cursor.execute("CREATE TABLE IF NOT EXISTS ayuda (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula TEXT, semestre INT, tipo_ayuda TEXT, observaciones TEXT)")
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO usuarios VALUES (?, ?, ?)", [
            ("arturo.subdirector", "admin123", "Subdirector"),
            ("coordinacion.prepa", "coord123", "Coordinación"),
            ("2026001", "alumno123", "Alumno/Padre")
        ])
        cursor.execute("INSERT INTO alumnos VALUES ('2026001', 'Juan Pérez Gómez', 3, 'A', 'tutor.juan@gmail.com', '7221234567')")
        cursor.execute("INSERT INTO alumnos VALUES ('2026002', 'María Luisa Hernández', 1, 'B', 'tutor.maria@gmail.com', '7229876543')")
    conn.commit()
    conn.close()

inicializar_bd()

def obtener_lista_alumnos():
    conn = sqlite3.connect("sistema_escolar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT matricula, nombre, semestre, grupo, correo_tutor, whatsapp_tutor FROM alumnos")
    lista = cursor.fetchall()
    conn.close()
    return lista

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
            conn = sqlite3.connect("sistema_escolar.db")
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE usuario=? AND contrasena=?", (usuario, contrasena))
            res = cursor.fetchone()
            conn.close()
            if res:
                rol_db = res[0]
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
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario = None
    st.session_state.links_masivos_wa = []
    
    cookie_manager.delete("pem_usuario", key="del_usr")
    cookie_manager.delete("pem_rol", key="del_rol")
    st.rerun()

def calcular_reglas_boleta(p1, p2, ef_guardado):
    p1_v = p1 if p1 is not None else 0.0
    p2_v = p2 if p2 is not None else 0.0
    prom_parcial = (p1_v + p2_v) / 2
    
    if prom_parcial >= 8.0:
        ex_final_str = "N/A"
        prom_ordinario = prom_parcial
    elif 6.0 <= prom_parcial <= 7.9:
        ef_v = ef_guardado if ef_guardado is not None else 0.0
        ex_final_str = f"{ef_v:.1f}"
        prom_ordinario = (prom_parcial + ef_v) / 2 if ef_v > 0.0 else prom_parcial
    else:
        ex_final_str = "SD"
        ef_v = ef_guardado if ef_guardado is not None else 0.0
        prom_ordinario = (prom_parcial + ef_v) / 2 if ef_v > 0.0 else prom_parcial
        
    return prom_parcial, ex_final_str, prom_ordinario

def mostrar_boleta(matricula, nombre, grupo, semestre_selec):
    conn = sqlite3.connect("sistema_escolar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT materia, parcial1, parcial2, final FROM calificaciones WHERE matricula=? AND semestre=?", (matricula, semestre_selec))
    materias = cursor.fetchall()
    conn.close()
    
    if materias:
        datos_lista_pantalla, pdf_rows, suma_ordinarios = [], "", 0.0
        for m in materias:
            nom_mat, p1, p2, ef = m
            prom_p, ef_str, prom_o = calcular_reglas_boleta(p1, p2, ef)
            suma_ordinarios += prom_o
            p1_f = f"{p1:.1f}" if p1 is not None else "0.0"
            p2_f = f"{p2:.1f}" if p2 is not None else "0.0"
            
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
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
        
        <div style="position: absolute; left: -9999px; top: 0; width: 850px;">
            {html_completo_pdf}
        </div>

        <button onclick="descargarPDFHorizontal()" style="background-color: #198754; color: white; border: none; padding: 12px 24px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer;">➡️ DESCARGAR BOLETA EN FORMATO HORIZONTAL (PDF)</button>
        
        <script>
        function descargarPDFHorizontal() {{
            const elemento = document.getElementById('boleta-imprimir');
            const opciones = {{ 
                margin: [0.5, 0.5, 0.5, 0.5], 
                filename: 'Boleta_{matricula}_Semestre_{semestre_selec}.pdf', 
                image: {{ type: 'jpeg', quality: 0.98 }}, 
                html2canvas: {{ scale: 2, useCORS: true, allowTaint: true }}, 
                jsPDF: {{ unit: 'in', format: 'letter', orientation: 'landscape' }} 
            }};
            html2pdf().set(opciones).from(elemento).save();
        }}
        </script>""", height=80)
    else: 
        st.warning("No se encontraron calificaciones registradas para este semestre.")

def mostrar_expediente_completo(matricula):
    conn = sqlite3.connect("sistema_escolar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alumnos WHERE matricula=?", (matricula,))
    alumno = cursor.fetchall()
    
    if alumno:
        al_mat, al_nom, al_sem, al_gpo = alumno[0][0], alumno[0][1], alumno[0][2], alumno[0][3]
        al_correo = alumno[0][4] if len(alumno[0]) > 4 else "Sin correo"
        al_wa = alumno[0][5] if len(alumno[0]) > 5 else "Sin número"
        
        st.markdown(f"""
        <div style='background-color:#fff; border:1px solid #ddd; border-radius:8px; padding:15px; margin-bottom:15px;'>
            <span style='color:#777; font-size:12px; font-weight:bold;'>EXPEDIENTE ACADÉMICO</span><br>
            <span style='font-size:18px; color:#4B1C24; font-weight:bold;'>{al_nom}</span> &nbsp;|&nbsp; <span><b>Grupo:</b> {al_gpo}</span> &nbsp;|&nbsp; <span><b>Semestre:</b> {al_sem}°</span><br>
            <span style='font-size:12px; color:#555;'>📧 Correo: <b>{al_correo or 'N/A'}</b> | 📱 WhatsApp: <b>{al_wa or 'N/A'}</b></span>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("SELECT semestre, materia, parcial1, parcial2, final FROM calificaciones WHERE matricula=?", (al_mat,))
        calif = cursor.fetchall()
        cursor.execute("SELECT semestre, fecha, motivo, metodo_notificacion, tipo_reporte FROM reportes WHERE matricula=?", (al_mat,))
        reps = cursor.fetchall()
        cursor.execute("SELECT semestre, tipo_ayuda, observaciones FROM ayuda WHERE matricula=?", (al_mat,))
        ayudas = cursor.fetchall()
        
        st.markdown("### 📚 Trayectoria de Historial Desglosado")
        semestres_disponibles = sorted(list(set([c[0] for c in calif] + [r[0] for r in reps] + [a[0] for a in ayudas] + [al_sem])))
        
        for sem in semestres_disponibles:
            with st.expander(f"➔ Ver Historial Completo del {sem}° Semestre", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**📊 Calificaciones**")
                    c_sem = [x for x in calif if x[0] == sem]
                    if c_sem:
                        for c in c_sem:
                            _, ef_str, prom_o = calcular_reglas_boleta(c[2], c[3], c[4])
                            st.info(f"**{c[1]}**\n1P: {c[2] or 0.0} | 2P: {c[3] or 0.0}\nFinal: {ef_str} | Ord: {prom_o:.1f}")
                    else: 
                        st.caption("*Sin asignaturas*")
                        
                with col2:
                    st.markdown("**⚠️ Reportes Escolares y Bitácora**")
                    r_sem = [x for x in reps if x[0] == sem]
                    if r_sem:
                        for r in r_sem:
                            tipo_tit = r[4] or "Disciplinario"
                            notif_info = f"\n📜 *Evidencia:* {r[3]}" if len(r) > 3 and r[3] else ""
                            st.error(f"📌 **{tipo_tit}** ({r[1]})\n{r[2]}{notif_info}")
                    else: 
                        st.success("✓ Conducta / Expediente Limpio")
                        
                with col3:
                    st.markdown("**📍 Apoyos y Tutorías**")
                    a_sem = [x for x in ayudas if x[0] == sem]
                    if a_sem:
                        for a in a_sem: 
                            st.warning(f"🌟 {a[1]}\n{a[2]}")
                    else: 
                        st.caption("*Sin requerimientos*")
        conn.close()
        return al_mat, al_nom, al_sem, al_gpo, al_correo, al_wa
    else:
        st.error("No se encontró ningún alumno.")
        conn.close()
        return None

# GENERADORES EXCEL
def generar_excel_muestra():
    df = pd.DataFrame({"matricula": ["2026003"], "nombre": ["Pedro Lopez"], "semestre": [1], "grupo": ["A"], "correo_tutor": ["padre@gmail.com"], "whatsapp_tutor": ["7221112233"]})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
    return out.getvalue()

def generar_excel_muestra_rep_academicos():
    df = pd.DataFrame({"matricula": ["2026001"], "semestre": [3], "fecha": [obtener_fecha_hora_mexico().strftime("%Y-%m-%d")], "motivo": ["I Inasistencia"]})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
    return out.getvalue()

# ----------------- MÓDULO DE CARGA Y CAPTURA GENERAL -----------------
def modulo_carga_datos(key_prefix=""):
    opcion = st.selectbox(
        "¿Qué deseas capturar?", 
        ["Nuevo Reporte Académico", "Nuevo Reporte Disciplinario", "Nueva Calificación", "Cargar Ayuda Académica", "Registrar Nuevo Alumno"], 
        key=f"{key_prefix}_opcion"
    )
    alumnos_disponibles = obtener_lista_alumnos()
    
    if not alumnos_disponibles and opcion != "Registrar Nuevo Alumno":
        st.warning("⚠️ Primero debes dar de alta al menos a un alumno.")
        return

    # REGISTRAR NUEVO ALUMNO
    if opcion == "Registrar Nuevo Alumno":
        st.markdown("### 👤 Registro Individual de Alumno")
        with st.form(f"{key_prefix}_form_alumno"):
            mat = st.text_input("Matrícula del Alumno")
            nombre_al = st.text_input("Nombre completo")
            sem = st.number_input("Semestre Inicial", min_value=1, max_value=6, value=1)
            grupo_al = st.text_input("Grupo (Ej. A)")
            correo_t = st.text_input("Correo del Tutor/Padre de Familia")
            wa_t = st.text_input("Número de WhatsApp del Tutor (10 dígitos)")
            
            if st.form_submit_button("Dar de Alta Alumno"):
                if mat.strip() and nombre_al.strip():
                    conn = sqlite3.connect("sistema_escolar.db")
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO alumnos VALUES (?, ?, ?, ?, ?, ?)", (mat.strip(), nombre_al.strip(), sem, grupo_al.strip().upper(), correo_t.strip(), wa_t.strip()))
                        cursor.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, 'Alumno/Padre')", (mat.strip(), mat.strip()))
                        conn.commit()
                        st.success(f"¡Alumno {nombre_al} registrado con éxito!")
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Error: {e}")
                    finally: 
                        conn.close()

        st.write("---")
        st.markdown("### 📊 Carga Masiva desde Excel")
        st.download_button("📥 Plantilla Alumnos", data=generar_excel_muestra(), file_name="plantilla_alumnos.xlsx")
        archivo = st.file_uploader("Sube Excel de Alumnos:", type=["xlsx"], key=f"{key_prefix}_up_al")
        if archivo and st.button("🚀 Procesar e Importar Alumnos", key=f"{key_prefix}_btn_proc_al"):
            df = pd.read_excel(archivo)
            conn = sqlite3.connect("sistema_escolar.db")
            cursor = conn.cursor()
            ex, err = 0, 0
            for _, f in df.iterrows():
                try:
                    mat_item = str(f['matricula']).strip()
                    wa = str(f['whatsapp_tutor']).strip() if 'whatsapp_tutor' in df.columns and pd.notnull(f['whatsapp_tutor']) else ""
                    ct = str(f['correo_tutor']).strip() if 'correo_tutor' in df.columns and pd.notnull(f['correo_tutor']) else ""
                    cursor.execute("INSERT INTO alumnos VALUES (?, ?, ?, ?, ?, ?)", (mat_item, str(f['nombre']).strip(), int(f['semestre']), str(f['grupo']).strip().upper(), ct, wa))
                    cursor.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, 'Alumno/Padre')", (mat_item, mat_item))
                    ex += 1
                except: 
                    err += 1
            conn.commit()
            conn.close()
            st.success(f"Éxito: {ex} añadidos, {err} omitidos.")
            st.rerun()
        return

    # CAMPOS GENERALES DE SELECCIÓN DE ALUMNO
    filtro_mat = st.text_input("🔍 Buscar por Matrícula:", key=f"{key_prefix}_filt_txt_gen")
    alumnos_filtrados = [a for a in alumnos_disponibles if filtro_mat.strip() in a[0]] if filtro_mat else alumnos_disponibles
    if not alumnos_filtrados:
        st.error("Ningún alumno coincide.")
        return

    opciones_alumnos = [f"{a[0]} - {a[1]} (Semestre {a[2]}°)" for a in alumnos_filtrados]
    alumno_selec = st.selectbox("Selecciona al Alumno:", opciones_alumnos, key=f"{key_prefix}_al_sel_gen")
    mat_limpia = alumno_selec.split(" - ")[0]
    datos_al = [a for a in alumnos_disponibles if a[0] == mat_limpia][0]
    nom_alumno, semestre_def, correo_tutor, wa_tutor = datos_al[1], datos_al[2], datos_al[4], datos_al[5]

    # ESTAMPILLA UNIFICADA DE FECHA Y HORA (HORARIO LOCAL MÉXICO)
    estampa_fecha_hora = obtener_fecha_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")

    # 1. REPORTE ACADÉMICO (INDIVIDUAL Y MASIVO CON WHATSAPP OPTATIVO)
    if opcion == "Nuevo Reporte Académico":
        st.markdown("### 📋 Registro de Reporte Académico")
        tab_ind, tab_mas = st.tabs(["✍️ Captura Individual", "📊 Carga Masiva (Excel / CSV)"])
        
        with tab_ind:
            sem_rep = st.number_input("Semestre", min_value=1, max_value=6, value=int(semestre_def), key=f"{key_prefix}_sem_ac")
            motivo_ac_sel = st.selectbox("Motivo del Reporte Académico:", MOTIVOS_ACADEMICOS, key=f"{key_prefix}_mot_ac_sel")
            
            motivo_final = motivo_ac_sel
            if motivo_ac_sel == "Otro motivo (especificar)":
                motivo_final = st.text_input("Especificar motivo:", key=f"{key_prefix}_mot_ac_esp")

            st.info(f"📧 **Correo Tutor:** {correo_tutor or 'Sin correo'} | 📱 **WhatsApp Tutor:** {wa_tutor or 'Sin teléfono'}")
            
            if st.button("Registrar Reporte Académico", key=f"{key_prefix}_btn_ac"):
                if motivo_final.strip():
                    evidencia_auto = f"Registro Sistema [{estampa_fecha_hora}]"
                    conn = sqlite3.connect("sistema_escolar.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO reportes VALUES (NULL, ?, ?, ?, ?, ?, 'Académico')", (mat_limpia, sem_rep, obtener_fecha_hora_mexico().strftime("%Y-%m-%d"), motivo_final.strip(), evidencia_auto))
                    conn.commit()
                    conn.close()
                    
                    enviar_notificacion_correo(correo_tutor, nom_alumno, mat_limpia, "Reporte Académico", f"Motivo: {motivo_final}")
                    
                    st.success(f"✅ ¡Reporte guardado! Registrado con estampilla: {estampa_fecha_hora}")
                    
                    # Generar opción opcional de WhatsApp
                    link_wa = generar_link_whatsapp(wa_tutor, nom_alumno, "Reporte Académico", motivo_final)
                    renderizar_lista_enlaces_whatsapp([{"Matrícula": mat_limpia, "Alumno": nom_alumno, "Detalle": motivo_final, "Link": link_wa}])

        with tab_mas:
            st.markdown("#### 🚀 Carga Masiva de Reportes Académicos")
            st.download_button("📥 Descargar Plantilla Excel Reportes Académicos", data=generar_excel_muestra_rep_academicos(), file_name="plantilla_reportes_academicos.xlsx")
            file_ac = st.file_uploader("Sube archivo Excel/CSV para Reportes Académicos:", type=["xlsx", "csv"], key=f"{key_prefix}_file_ac_mas")
            
            if file_ac and st.button("🚀 Procesar Carga Masiva", key=f"{key_prefix}_btn_proc_mas"):
                df_rep = pd.read_csv(file_ac) if file_ac.name.endswith(".csv") else pd.read_excel(file_ac)
                conn = sqlite3.connect("sistema_escolar.db")
                cursor = conn.cursor()
                
                c_ok, c_correos = 0, 0
                temp_links = []
                
                for _, f in df_rep.iterrows():
                    mat_item = str(f['matricula']).strip()
                    sem_item = int(f['semestre'])
                    fecha_item = str(f['fecha']).strip()
                    motivo_item = str(f['motivo']).strip()
                    evidencia_auto = f"Registro Carga Masiva [{estampa_fecha_hora}]"

                    cursor.execute("INSERT INTO reportes VALUES (NULL, ?, ?, ?, ?, ?, 'Académico')", (mat_item, sem_item, fecha_item, motivo_item, evidencia_auto))
                    c_ok += 1
                    
                    cursor.execute("SELECT nombre, correo_tutor, whatsapp_tutor FROM alumnos WHERE matricula=?", (mat_item,))
                    al_data = cursor.fetchone()
                    if al_data:
                        nom_a, corr_t, wa_t = al_data
                        ok_c, _ = enviar_notificacion_correo(corr_t, nom_a, mat_item, "Reporte Académico", f"Motivo: {motivo_item}")
                        if ok_c: c_correos += 1
                        link = generar_link_whatsapp(wa_t, nom_a, "Reporte Académico", motivo_item)
                        temp_links.append({"Matrícula": mat_item, "Alumno": nom_a, "Detalle": motivo_item, "Link": link})
                
                conn.commit()
                conn.close()
                st.session_state.links_masivos_wa = temp_links
                st.success(f"🎉 ¡Proceso masivo completado!\n- 📋 {c_ok} Reportes e evidencias registrados automáticamente.\n- 📧 {c_correos} Correos enviados.")

            if st.session_state.links_masivos_wa:
                renderizar_lista_enlaces_whatsapp(st.session_state.links_masivos_wa)

    # 2. REPORTE DISCIPLINARIO
    elif opcion == "Nuevo Reporte Disciplinario":
        st.markdown("### 📋 Registro de Reporte Disciplinario")
        sem_rep = st.number_input("Semestre", min_value=1, max_value=6, value=int(semestre_def))
        motivo_disc = st.text_area("Descripción Detallada de la Falta Disciplinaria:")
        metodo_notif = st.selectbox("¿Medio por el que se le notificó al Padre de Familia / Tutor?", OPCIONES_NOTIFICACION_DISCIPLINARIO, index=0)
        fecha_rep = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")

        st.info(f"📧 **Correo Tutor:** {correo_tutor or 'Sin correo'} | 📱 **WhatsApp Tutor:** {wa_tutor or 'Sin teléfono'}")

        if st.button("Registrar Reporte Disciplinario"):
            if motivo_disc.strip():
                evidencia_auto = f"{metodo_notif} [{estampa_fecha_hora}]"
                conn = sqlite3.connect("sistema_escolar.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO reportes VALUES (NULL, ?, ?, ?, ?, ?, 'Disciplinario')", (mat_limpia, sem_rep, fecha_rep, motivo_disc.strip(), evidencia_auto))
                conn.commit()
                conn.close()
                
                enviar_notificacion_correo(correo_tutor, nom_alumno, mat_limpia, "Reporte Disciplinario", f"Detalle: {motivo_disc}")
                st.success(f"✅ ¡Reporte Disciplinario guardado! Evidencia registrada: {evidencia_auto}")
                
                # Opción opcional de WhatsApp para el usuario
                link_wa = generar_link_whatsapp(wa_tutor, nom_alumno, "Reporte Disciplinario", motivo_disc)
                renderizar_lista_enlaces_whatsapp([{"Matrícula": mat_limpia, "Alumno": nom_alumno, "Detalle": motivo_disc, "Link": link_wa}])

    # 3. NUEVA CALIFICACIÓN
    elif opcion == "Nueva Calificación":
        st.markdown("### 📊 Captura de Calificación")
        sem_calif = st.number_input("Semestre", min_value=1, max_value=6, value=int(semestre_def))
        materia_selec = st.selectbox("Asignatura:", MATERIAS_POR_SEMESTRE.get(sem_calif, ["OTRA"]))
        tipo_parcial = st.selectbox("Parcial:", ["Examen 1º Parcial", "Examen 2º Parcial", "Examen Final"])
        calif_nota = st.number_input("Nota", min_value=0.0, max_value=10.0, step=0.1)
        
        if st.button("Guardar Calificación"):
            conn = sqlite3.connect("sistema_escolar.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM calificaciones WHERE matricula=? AND semestre=? AND materia=?", (mat_limpia, sem_calif, materia_selec))
            existe = cursor.fetchone()
            col = "parcial1" if tipo_parcial == "Examen 1º Parcial" else "parcial2" if tipo_parcial == "Examen 2º Parcial" else "final"
            
            if existe: cursor.execute(f"UPDATE calificaciones SET {col}=? WHERE id=?", (calif_nota, existe[0]))
            else: cursor.execute(f"INSERT INTO calificaciones (matricula, semestre, materia, {col}) VALUES (?, ?, ?, ?)", (mat_limpia, sem_calif, materia_selec, calif_nota))
            
            evidencia_auto = f"Registro Sistema [{estampa_fecha_hora}]"
            cursor.execute("INSERT INTO reportes VALUES (NULL, ?, ?, ?, ?, ?, 'Aviso Calificación')", (mat_limpia, sem_calif, obtener_fecha_hora_mexico().strftime("%Y-%m-%d"), f"{materia_selec} ({tipo_parcial}): {calif_nota}", evidencia_auto))
            
            conn.commit()
            conn.close()
            
            enviar_notificacion_correo(correo_tutor, nom_alumno, mat_limpia, "Calificación", f"Materia: {materia_selec}<br>Nota: {calif_nota}")
            st.success(f"✅ ¡Calificación guardada y certificada en la bitácora ({estampa_fecha_hora})!")
            
            # Opción opcional de WhatsApp
            detalle_cal = f"{materia_selec} ({tipo_parcial}): {calif_nota}"
            link_wa = generar_link_whatsapp(wa_tutor, nom_alumno, "Aviso de Calificación", detalle_cal)
            renderizar_lista_enlaces_whatsapp([{"Matrícula": mat_limpia, "Alumno": nom_alumno, "Detalle": detalle_cal, "Link": link_wa}])

    # 4. AYUDA ACADÉMICA
    elif opcion == "Cargar Ayuda Académica":
        st.markdown("### 🌟 Registro de Apoyo o Tutoría Especial")
        sem_a = st.number_input("Semestre", min_value=1, max_value=6, value=int(semestre_def))
        tipo_a = st.selectbox("Tipo de Ayuda", ["Asesorías Académicas", "Tutoría Psicoeducativa", "Plan de Regularización"])
        obs_a = st.text_area("Observaciones")
        
        if st.button("Guardar Ayuda y Certificar"):
            conn = sqlite3.connect("sistema_escolar.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ayuda VALUES (NULL, ?, ?, ?, ?)", (mat_limpia, sem_a, tipo_a, obs_a))
            
            evidencia_auto = f"Registro Sistema [{estampa_fecha_hora}]"
            cursor.execute("INSERT INTO reportes VALUES (NULL, ?, ?, ?, ?, ?, 'Apoyo/Tutoría')", (mat_limpia, sem_a, obtener_fecha_hora_mexico().strftime("%Y-%m-%d"), f"{tipo_a}: {obs_a}", evidencia_auto))
            
            conn.commit()
            conn.close()
            st.success(f"✅ ¡Apoyo registrado y certificado automáticamente ({estampa_fecha_hora})!")
            
            # Opción opcional de WhatsApp
            detalle_ayuda = f"{tipo_a}: {obs_a}"
            link_wa = generar_link_whatsapp(wa_tutor, nom_alumno, "Apoyo/Tutoría", detalle_ayuda)
            renderizar_lista_enlaces_whatsapp([{"Matrícula": mat_limpia, "Alumno": nom_alumno, "Detalle": detalle_ayuda, "Link": link_wa}])

# ----------------- VISTA DE TUTORÍAS Y BITÁCORA DE EVIDENCIAS -----------------
def modulo_tutorias():
    st.title("🎯 Módulo de Bitácora y Tutorías - Evidencias Oficiales")
    st.info("Consulta y descarga en tiempo real la bitácora oficial. Cada registro contiene la fecha y hora exacta de captura/envío.")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: fecha_sel = st.date_input("Filtrar por Fecha/Día:", obtener_fecha_hora_mexico())
    with col_f2: sem_sel = st.selectbox("Filtrar por Semestre:", ["Todos", 1, 2, 3, 4, 5, 6])
    with col_f3: gpo_sel = st.text_input("Filtrar por Grupo (Dejar vacío para todos):")

    fecha_str = fecha_sel.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("sistema_escolar.db")
    query = """
    SELECT r.id, r.fecha, a.matricula, a.nombre, a.semestre, a.grupo, r.tipo_reporte, r.motivo, r.metodo_notificacion, a.whatsapp_tutor 
    FROM reportes r 
    JOIN alumnos a ON r.matricula = a.matricula 
    WHERE r.fecha = ?
    """
    params = [fecha_str]
    
    if sem_sel != "Todos":
        query += " AND a.semestre = ?"
        params.append(sem_sel)
    if gpo_sel.strip():
        query += " AND UPPER(a.grupo) = ?"
        params.append(gpo_sel.strip().upper())

    df_tutoria = pd.read_sql_query(query, conn, params=params)
    conn.close()

    st.subheader(f"📊 Registros del Día: {fecha_sel.strftime('%d/%m/%Y')}")
    
    if not df_tutoria.empty:
        df_tutoria.columns = ["ID", "Fecha Captura", "Matrícula", "Nombre Alumno", "Semestre", "Grupo", "Tipo Evento", "Motivo / Detalle", "Evidencia (Fecha y Hora de Registro/Envío)", "WhatsApp Tutor"]
        st.dataframe(df_tutoria, use_container_width=True, hide_index=True)
        
        out_tut = io.BytesIO()
        with pd.ExcelWriter(out_tut, engine='openpyxl') as writer:
            df_tutoria.to_excel(writer, index=False, sheet_name='Bitacora_Evidencias')
            
        st.download_button(
            label="📥 Descargar Reporte Completo de Evidencias (Excel)",
            data=out_tut.getvalue(),
            file_name=f"Evidencias_Oficiales_{fecha_str}_Sem_{sem_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else: 
        st.warning("No hay registros o evidencias guardadas para la fecha y filtros seleccionados.")

# ----------------- MÓDULO DE GESTIÓN DE USUARIOS -----------------
def modulo_gestion_usuarios():
    st.header("⚙️ Administración de Usuarios del Sistema")
    
    col_u1, col_u2 = st.columns([1, 1])
    
    with col_u1:
        st.markdown("### ➕ Registrar Nuevo Usuario")
        with st.form("form_alta_usuario"):
            nuevo_usr = st.text_input("Usuario (Ej. Matrícula o Nombre):")
            nuevo_pass = st.text_input("Contraseña:", type="password")
            nuevo_rol = st.selectbox("Rol del Usuario:", ["Alumno/Padre", "Coordinación", "Subdirector"])
            
            if st.form_submit_button("Crear Usuario", type="primary"):
                if nuevo_usr.strip() and nuevo_pass.strip():
                    conn = sqlite3.connect("sistema_escolar.db")
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO usuarios VALUES (?, ?, ?)", (nuevo_usr.strip(), nuevo_pass.strip(), nuevo_rol))
                        conn.commit()
                        st.success(f"¡Usuario **{nuevo_usr}** creado correctamente con el rol **{nuevo_rol}**!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear usuario (quizá ya existe): {e}")
                    finally:
                        conn.close()
                else:
                    st.warning("Completa todos los campos.")

    with col_u2:
        st.markdown("### 👥 Usuarios Registrados Actuales")
        conn = sqlite3.connect("sistema_escolar.db")
        df_usuarios = pd.read_sql_query("SELECT usuario AS 'Usuario', rol AS 'Rol' FROM usuarios", conn)
        conn.close()
        
        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Eliminar Usuario")
        usr_eliminar = st.selectbox("Selecciona un usuario para eliminar:", df_usuarios["Usuario"].tolist())
        if st.button("Eliminar Usuario Seleccionado"):
            if usr_eliminar == st.session_state.usuario:
                st.error("No puedes eliminar tu propio usuario activo.")
            else:
                conn = sqlite3.connect("sistema_escolar.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE usuario=?", (usr_eliminar,))
                conn.commit()
                conn.close()
                st.success(f"Usuario {usr_eliminar} eliminado.")
                st.rerun()

# --- INTERFAZ POR ROL ---
if st.session_state.rol in ["Subdirector", "Coordinación"]:
    p_tabs = ["🔍 Buscador Central", "📋 Administración de Alumnos", "📝 Captura de Datos", "🎯 Bitácora y Tutorías", "⚙️ Usuarios"] if st.session_state.rol == "Subdirector" else ["📝 Captura de Datos", "🎯 Bitácora y Tutorías", "🔍 Expedientes"]
    pestanas = st.tabs(p_tabs)

    if st.session_state.rol == "Subdirector":
        # 1. BUSCADOR CENTRAL
        with pestanas[0]:
            alumnos_bd = obtener_lista_alumnos()
            if alumnos_bd:
                f_txt = st.text_input("🔍 Buscar Matrícula:")
                a_fil = [a for a in alumnos_bd if f_txt.strip() in a[0]] if f_txt else alumnos_bd
                if a_fil:
                    al_sel = st.selectbox("Selecciona alumno:", [f"{a[0]} - {a[1]}" for a in a_fil])
                    m_b = al_sel.split(" - ")[0]
                    d_al = mostrar_expediente_completo(m_b)
                    if d_al:
                        sem_b = st.number_input("Semestre Boleta:", min_value=1, max_value=6, value=int(d_al[2]))
                        mostrar_boleta(d_al[0], d_al[1], d_al[3], sem_b)

        # 2. ADMINISTRACIÓN GLOBAL DE ALUMNOS
        with pestanas[1]:
            st.header("📋 Administración Global y Modificación de Alumnos")
            alumnos_lista = obtener_lista_alumnos()
            
            if alumnos_lista:
                df_admin = pd.DataFrame(alumnos_lista, columns=["Matrícula", "Nombre Completo", "Semestre", "Grupo", "Correo Tutor", "WhatsApp Tutor"])
                
                st.markdown("### ⚡ Acciones Masivas / En Lote")
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1: 
                    alumnos_seleccionados = st.multiselect("Selecciona los alumnos:", df_admin["Matrícula"].tolist())
                with col_m2: 
                    accion_masiva = st.selectbox("¿Qué acción masiva aplicar?", ["---", "Cambiar de Semestre Masivo", "Cambiar de Grupo Masivo", "Eliminar Alumnos Seleccionados"])
                with col_m3:
                    if accion_masiva == "Cambiar de Semestre Masivo":
                        nuevo_sem_m = st.number_input("Nuevo semestre:", min_value=1, max_value=6, value=1)
                        if st.button("Aplicar Semestre Masivo", type="primary"):
                            if alumnos_seleccionados:
                                conn = sqlite3.connect("sistema_escolar.db")
                                cursor = conn.cursor()
                                cursor.executemany("UPDATE alumnos SET semestre=? WHERE matricula=?", [(nuevo_sem_m, mat) for mat in alumnos_seleccionados])
                                conn.commit()
                                conn.close()
                                st.success("¡Semestres actualizados correctamente!")
                                st.rerun()
                                
                    elif accion_masiva == "Cambiar de Grupo Masivo":
                        nuevo_gpo_m = st.text_input("Nuevo grupo:")
                        if st.button("Aplicar Grupo Masivo", type="primary"):
                            if alumnos_seleccionados and nuevo_gpo_m.strip():
                                conn = sqlite3.connect("sistema_escolar.db")
                                cursor = conn.cursor()
                                cursor.executemany("UPDATE alumnos SET grupo=? WHERE matricula=?", [(nuevo_gpo_m.strip().upper(), mat) for mat in alumnos_seleccionados])
                                conn.commit()
                                conn.close()
                                st.success("¡Grupos actualizados correctamente!")
                                st.rerun()
                                
                    elif accion_masiva == "Eliminar Alumnos Seleccionados":
                        if st.button("🚨 ELIMINAR SELECCIONADOS", type="primary"):
                            if alumnos_seleccionados:
                                conn = sqlite3.connect("sistema_escolar.db")
                                cursor = conn.cursor()
                                for mat in alumnos_seleccionados:
                                    cursor.execute("DELETE FROM alumnos WHERE matricula=?", (mat,))
                                    cursor.execute("DELETE FROM calificaciones WHERE matricula=?", (mat,))
                                    cursor.execute("DELETE FROM reportes WHERE matricula=?", (mat,))
                                    cursor.execute("DELETE FROM ayuda WHERE matricula=?", (mat,))
                                conn.commit()
                                conn.close()
                                st.success("Alumnos eliminados exitosamente.")
                                st.rerun()
                                
                st.write("---")
                st.markdown("### 🔍 Lista de Alumnos Registrados")
                st.dataframe(df_admin, use_container_width=True, hide_index=True)
                
                st.write("---")
                col_ind1, col_ind2 = st.columns(2)
                
                with col_ind1:
                    st.markdown("### ✏️ Modificar Alumno Individual")
                    mat_mod = st.selectbox("Selecciona la matrícula a editar:", df_admin["Matrícula"].tolist(), key="sel_mod_ind")
                    datos_act = [a for a in alumnos_lista if a[0] == mat_mod][0]
                    
                    nom_new = st.text_input("Modificar Nombre:", value=datos_act[1])
                    sem_new = st.number_input("Modificar Semestre:", min_value=1, max_value=6, value=int(datos_act[2]))
                    gpo_new = st.text_input("Modificar Grupo:", value=datos_act[3])
                    correo_new = st.text_input("Modificar Correo Tutor:", value=datos_act[4] or "")
                    wa_new = st.text_input("Modificar WhatsApp Tutor:", value=datos_act[5] or "")
                    
                    if st.button("💾 Guardar Cambios Individuales", type="primary"):
                        conn = sqlite3.connect("sistema_escolar.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE alumnos SET nombre=?, semestre=?, grupo=?, correo_tutor=?, whatsapp_tutor=? WHERE matricula=?", 
                            (nom_new.strip(), sem_new, gpo_new.strip().upper(), correo_new.strip(), wa_new.strip(), mat_mod)
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"¡Datos de {nom_new} modificados con éxito!")
                        st.rerun()
                        
                with col_ind2:
                    st.markdown("### 🗑️ Borrar Alumno Individual")
                    mat_del = st.selectbox("Selecciona matrícula a borrar:", df_admin["Matrícula"].tolist(), key="sel_del_ind")
                    
                    if st.button("❌ Confirmar Eliminación Individual"):
                        conn = sqlite3.connect("sistema_escolar.db")
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM alumnos WHERE matricula=?", (mat_del,))
                        cursor.execute("DELETE FROM calificaciones WHERE matricula=?", (mat_del,))
                        cursor.execute("DELETE FROM reportes WHERE matricula=?", (mat_del,))
                        cursor.execute("DELETE FROM ayuda WHERE matricula=?", (mat_del,))
                        conn.commit()
                        conn.close()
                        st.success("Alumno y registros asociados eliminados correctamente.")
                        st.rerun()
            else: 
                st.info("No hay alumnos registrados actualmente.")

        with pestanas[2]: modulo_carga_datos(key_prefix="sub_c")
        with pestanas[3]: modulo_tutorias()
        with pestanas[4]: modulo_gestion_usuarios()
    else:
        with pestanas[0]: modulo_carga_datos(key_prefix="coor_c")
        with pestanas[1]: modulo_tutorias()
        with pestanas[2]:
            al = obtener_lista_alumnos()
            if al:
                a_sel = st.selectbox("Buscar Alumno:", [f"{a[0]} - {a[1]}" for a in al])
                mostrar_expediente_completo(a_sel.split(" - ")[0])

elif st.session_state.rol == "Alumno/Padre":
    mat = st.session_state.usuario
    datos = mostrar_expediente_completo(mat)
    if datos:
        sem_b = st.number_input("Ver semestre:", min_value=1, max_value=6, value=int(datos[2]))
        mostrar_boleta(datos[0], datos[1], datos[3], sem_b)

st.markdown("---")
st.caption(CREDITOS)