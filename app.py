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

# CONFIGURACIÓN DE RUTAS Y SERVICIOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo_172.png")
CORREO_EMISOR = "notificaciones@pem.edu.mx"
PASSWORD_CORREO = "mqtxcnxwycqflxip"

st.set_page_config(page_title="Sistema Control Escolar Prep. Edo. de México", layout="wide")
CREDITOS = "Sistema diseñado por: LEM Arturo Javier Diaz Salazar, Subdirector Académico de la Preparatoria Estado de México."

conn = st.connection("supabase", type="sql")

def obtener_fecha_hora_mexico():
    return datetime.now(ZoneInfo("America/Mexico_City"))

def obtener_siguiente_dia_habil(fecha_actual):
    dia = fecha_actual + timedelta(days=1)
    while dia.weekday() > 4: 
        dia += timedelta(days=1)
    return dia

def obtener_dia_habil_anterior(fecha_actual):
    dia = fecha_actual - timedelta(days=1)
    while dia.weekday() > 4: 
        dia -= timedelta(days=1)
    return dia

def get_cookie_manager():
    return stx.CookieManager(key="cookie_manager_pem")

cookie_manager = get_cookie_manager()

PWA_PUSH_SCRIPT = """
<script>
if ('serviceWorker' in navigator && 'PushManager' in window) {
    navigator.serviceWorker.register('/sw.js').then(function(reg) {
        console.log('Service Worker Registrado.', reg);
    });
}
function solicitarPermisoPush() {
    if ('Notification' in window) {
        Notification.requestPermission().then(function(permission) {
            if (permission === 'granted') {
                new Notification("Prep. Estado de México", {
                    body: "Notificaciones Push activadas",
                    icon: "/logo.png"
                });
            }
        });
    }
}
</script>
<div style="background-color: #f0f7ff; border: 1px solid #b6d4fe; border-radius: 8px; padding: 10px; text-align: center;">
    <span style="font-size: 13px; color: #084298; font-weight: bold;">Instalación y Notificaciones Celular:</span>
    <button onclick="solicitarPermisoPush()" style="background-color: #0d6efd; color: white; border: none; padding: 6px 12px; margin-left: 10px; border-radius: 4px;">Activar Push</button>
</div>
"""

MOTIVOS_ACADEMICOS = [
    "I Inasistencia", "II Sin material", "III Retardo", "IV Vocabulario Inapropiado", 
    "V Indisciplina", "VI No trabajo en clase", "VII Incumplimiento de tareas", 
    "VIII Tarea incompleta", "Otro motivo (especificar)"
]

OPCIONES_NOTIFICACION_DISCIPLINARIO = [
    "Mensaje de WhatsApp", "Llamada Telefónica", "Visita a la Institución", 
    "Correo Electrónico", "Citatorio Firmado en Físico", "Multicanal / Portal Web"
]

MATERIAS_POR_SEMESTRE = {
    1: ['LENGUA Y COMUNICACION I', 'INGLES I', 'CULTURA DIGITAL', 'PENSAMIENTO MATEMATICO I', 'QUIMICA I', 'HUMANIDADES I', 'CIENCIAS SOCIALES I'],
    2: ['LENGUA Y COMUNICACION II', 'INGLES II', 'PENSAMIENTO MATEMATICO II', 'FISICA I', 'HUMANIDADES II', 'CIENCIAS SOCIALES II', 'DESARROLLO PERSONAL'],
    3: ['LENGUA Y COMUNICACION III', 'INGLES III', 'PENSAMIENTO MATEMATICO III', 'BIOLOGIA I', 'HUMANIDADES III', 'METODOLOGIA Y TALLER DE INVESTIGACION'],
    4: ['LITERATURA', 'INGLES IV', 'TEMAS SELECTOS DE MATEMATICAS I', 'CONCIENCIA HISTORICA I', 'QUIMICA II', 'CULTURA AMBIENTAL Y DESARROLLO SOSTENIBLE'],
    5: ['TEMAS SELECTOS DE MATEMATICAS II', 'CONCIENCIA HISTORICA II', 'FISICA II', 'GEOGRAFIA', 'APRECIACION Y EXPRESION DEL ARTE I', 'CULTURA DE PAZ'],
    6: ['TEMAS SELECTOS DE MATEMATICAS III', 'CONCIENCIA HISTORICA III', 'BIOLOGIA II', 'APRECIACION Y EXPRESION DEL ARTE II', 'PSICOLOGIA']
}

def generar_link_whatsapp(telefono, nombre_alumno, tipo_evento, detalle):
    if not telefono or str(telefono).strip() in ["", "None", "0"]:
        return None
    tel_limpio = "".join(filter(str.isdigit, str(telefono)))
    if len(tel_limpio) == 10: tel_limpio = "521" + tel_limpio
    fecha_mx = obtener_fecha_hora_mexico().strftime('%d/%m/%Y %H:%M')
    texto = (f"*PREPARATORIA ESTADO DE MÉXICO*\n_Subdirección Académica_\n\n"
             f"Estimado tutor, aviso importante sobre:\n*{nombre_alumno}*\n\n"
             f"*Tipo:* {tipo_evento}\n*Detalle:* {detalle}\n*Fecha/Hora:* {fecha_mx}\n\n"
             f"_Favor de acudir a la institución para aclaraciones._")
    return f"https://api.whatsapp.com/send?phone={tel_limpio}&text={urllib.parse.quote(texto)}"

def renderizar_lista_enlaces_whatsapp(lista_links):
    if not lista_links: return
    st.markdown("---")
    st.markdown("### Opciones para Enviar por WhatsApp")
    for item in lista_links:
        col_a, col_b = st.columns([3, 1])
        with col_a: st.write(f"**{item['Alumno']}** ({item['Matrícula']}) - *{item['Detalle']}*")
        with col_b:
            if item.get('Link'): st.link_button("Enviar WhatsApp", item["Link"], type="primary")
            else: st.caption("Sin teléfono")

def enviar_notificacion_correo(correo_tutor, nombre_alumno, matricula, tipo_evento, detalle_texto):
    if not correo_tutor or "@" not in str(correo_tutor): return False, "Sin correo."
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Preparatoria Estado de México <{CORREO_EMISOR}>"
        msg['To'] = correo_tutor
        msg['Subject'] = f"[Notificación Escolar] Actualización para {nombre_alumno}"
        cuerpo_html = f"<p><b>Notificación para:</b> {nombre_alumno} ({matricula})</p><p><b>Tipo:</b> {tipo_evento}</p><p><b>Detalle:</b> {detalle_texto}</p>"
        msg.attach(MIMEText(cuerpo_html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(CORREO_EMISOR, PASSWORD_CORREO)
        server.sendmail(CORREO_EMISOR, correo_tutor, msg.as_string())
        server.quit()
        return True, "Enviado."
    except Exception as e:
        return False, str(e)

def inicializar_bd():
    with conn.session as session:
        session.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, contrasena TEXT, rol TEXT)"))
        session.execute(text("CREATE TABLE IF NOT EXISTS alumnos (matricula TEXT PRIMARY KEY, nombre TEXT, semestre INT, grupo TEXT, correo_tutor TEXT, whatsapp_tutor TEXT)"))
        session.execute(text("CREATE TABLE IF NOT EXISTS calificaciones (id SERIAL PRIMARY KEY, matricula TEXT, semestre INT, materia TEXT, parcial1 REAL, parcial2 REAL, final REAL)"))
        session.execute(text("CREATE TABLE IF NOT EXISTS reportes (id SERIAL PRIMARY KEY, matricula TEXT, semestre INT, fecha TEXT, motivo TEXT, metodo_notificacion TEXT, tipo_reporte TEXT DEFAULT 'Disciplinario')"))
        session.execute(text("CREATE TABLE IF NOT EXISTS ayuda (id SERIAL PRIMARY KEY, matricula TEXT, semestre INT, tipo_ayuda TEXT, observaciones TEXT)"))
        try: session.execute(text("ALTER TABLE reportes ADD COLUMN capturista TEXT DEFAULT 'Sistema'"))
        except: pass
        session.commit()

inicializar_bd()

def obtener_lista_alumnos():
    df = conn.query("SELECT matricula, nombre, semestre, grupo, correo_tutor, whatsapp_tutor FROM alumnos ORDER BY nombre", ttl=0)
    return df.values.tolist()

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
    st.session_state.usuario = None
if "links_masivos_wa" not in st.session_state:
    st.session_state.links_masivos_wa = []

if not st.session_state.autenticado:
    st.title("Preparatoria Estado de México - Acceso")
    with st.form("Login"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            res = conn.query("SELECT rol FROM usuarios WHERE usuario=:u AND contrasena=:p", params={"u": usuario, "p": contrasena}, ttl=0)
            if not res.empty:
                st.session_state.autenticado = True
                st.session_state.rol = res.iloc[0]['rol']
                st.session_state.usuario = usuario
                st.rerun()
            else: st.error("Credenciales incorrectas.")
    st.stop()

components.html(PWA_PUSH_SCRIPT, height=75)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    components.html("<script>window.parent.location.reload();</script>", height=0)

def mostrar_expediente_completo(matricula):
    df_al = conn.query("SELECT * FROM alumnos WHERE matricula=:m", params={"m": matricula}, ttl=0)
    if not df_al.empty:
        al = df_al.values.tolist()[0]
        st.markdown(f"### Expediente: {al[1]} (Grupo: {al[3]})")
        calif = conn.query("SELECT semestre, materia, parcial1, parcial2, final FROM calificaciones WHERE matricula=:m", params={"m": matricula}, ttl=0).values.tolist()
        reps = conn.query("SELECT semestre, fecha, motivo, metodo_notificacion, tipo_reporte, capturista FROM reportes WHERE matricula=:m", params={"m": matricula}, ttl=0).values.tolist()
        ayudas = conn.query("SELECT semestre, tipo_ayuda, observaciones FROM ayuda WHERE matricula=:m", params={"m": matricula}, ttl=0).values.tolist()
        
        semestres_brutos = [c[0] for c in calif] + [r[0] for r in reps] + [a[0] for a in ayudas] + [al[2]]
        semestres_disp = sorted(list(set([int(s) for s in semestres_brutos if pd.notnull(s) and str(s).strip().isdigit()])))
        
        for sem in semestres_disp:
            with st.expander(f"Semestre {sem}", expanded=True):
                st.write(f"Registros del semestre {sem}...")
        return al
    return None

def modulo_carga_datos(key_prefix=""):
    opciones = ["Nuevo Reporte Académico", "Nuevo Reporte Disciplinario", "Registrar Nuevo Alumno"]
    opcion = st.selectbox("Acción:", opciones, key=f"{key_prefix}_op")
    alumnos_disponibles = obtener_lista_alumnos()
    usr_actual = st.session_state.usuario
    estampa_fecha_hora = obtener_fecha_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")

    if opcion == "Nuevo Reporte Académico":
        st.markdown("### Registro Académico (Lote)")
        sem_rep = st.number_input("1. Semestre:", min_value=1, max_value=6, value=1)
        grupos_disp = sorted(list(set([a[3] for a in alumnos_disponibles if a[3] and a[2] == sem_rep])))
        gpo_sel = st.selectbox("2. Grupo:", grupos_disp if grupos_disp else ["SIN GRUPOS"])
        mat_rep = st.selectbox("3. Materia:", MATERIAS_POR_SEMESTRE.get(sem_rep, ["OTRA"]))
        
        al_fil = [a for a in alumnos_disponibles if a[2] == sem_rep and a[3] == gpo_sel]
        opciones_al = [f"{a[0]} - {a[1]}" for a in al_fil]
        al_sel_str = st.multiselect("4. Alumnos:", opciones_al)
        
        if al_sel_str:
            datos_lote = {}
            for al_s in al_sel_str:
                mat_a = al_s.split(" - ")[0]
                motivo = st.selectbox(f"Motivo para {mat_a}:", MOTIVOS_ACADEMICOS, key=f"m_{mat_a}")
                obs = st.text_input(f"Observaciones ({mat_a}):", key=f"o_{mat_a}")
                datos_lote[mat_a] = {"nombre": al_s.split(" - ")[1], "motivo": motivo, "obs": obs}
            
            if st.button("Guardar y Notificar Lote"):
                temp_links, c_ok, c_correos = [], 0, 0
                fecha_obj = obtener_dia_habil_anterior(obtener_fecha_hora_mexico())
                f_db, f_msg = fecha_obj.strftime("%Y-%m-%d"), fecha_obj.strftime("%d/%m/%Y")
                
                with conn.session as session:
                    for mat_a, val in datos_lote.items():
                        txt = f"[{mat_rep}] {val['motivo']} | Obs: {val['obs']} (Corresponde al: {f_msg})"
                        session.execute(text("INSERT INTO reportes (matricula, semestre, fecha, motivo, metodo_notificacion, tipo_reporte, capturista) VALUES (:m, :s, :f, :mot, 'Multicanal', 'Académico', :cap)"), {"m": mat_a, "s": sem_rep, "f": f_db, "mot": txt, "cap": usr_actual})
                        c_ok += 1
                        
                        datos_al = [a for a in al_fil if a[0] == mat_a][0]
                        ok_c, _ = enviar_notificacion_correo(datos_al[4], val['nombre'], mat_a, "Reporte Académico", txt)
                        if ok_c: c_correos += 1
                        
                        link = generar_link_whatsapp(datos_al[5], val['nombre'], "Reporte Académico", txt)
                        temp_links.append({"Matrícula": mat_a, "Alumno": val['nombre'], "Detalle": txt, "Link": link})
                    session.commit()
                st.session_state.links_masivos_wa = temp_links
                st.success(f"Guardado. Reportes: {c_ok}, Correos: {c_correos}")
                renderizar_lista_enlaces_whatsapp(temp_links)

p_tabs = st.tabs(["Buscador Central", "Captura de Datos"])
with p_tabs[0]:
    alumnos_bd = obtener_lista_alumnos()
    if alumnos_bd:
        a_sel = st.selectbox("Alumno:", [f"{a[0]} - {a[1]}" for a in alumnos_bd])
        mostrar_expediente_completo(a_sel.split(" - ")[0])
with p_tabs[1]:
    modulo_carga_datos("cap_main")
