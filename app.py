import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
import uuid

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO (DB independiente) ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# --- Limpieza diferida ---
if "limpiar_form" in st.session_state and st.session_state["limpiar_form"]:
    for key in [
        "lugar", "ctx1", "ctx2", "ctx3", "ctx4", "ctx5", "ctx6",
        "inv1", "inv2", "inv3",
        "int1", "int2", "int3", "int4", "int5"
    ]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["foto_key"] = str(uuid.uuid4())  # reiniciar uploader
    st.session_state["limpiar_form"] = False

# Clave dinámica para reiniciar file_uploader
if "foto_key" not in st.session_state:
    st.session_state["foto_key"] = str(uuid.uuid4())

# === FORMULARIO ===
st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

st.header("🆕 Nueva entrada")
lugar = st.text_input("📍 Lugar o punto del recorrido", key="lugar", placeholder="Ej: Centro Cultural de Moravia")

# --- Preguntas orientadoras ---
st.subheader("A. Elementos de Contexto")
ctx1 = st.text_area("1. Principales hitos en la transformación territorial", key="ctx1")
ctx2 = st.text_area("2. Actores individuales y colectivos claves en la configuración del territorio", key="ctx2")
ctx3 = st.text_area("3. Principales transformaciones urbanas y su impacto social", key="ctx3")
ctx4 = st.text_area("4. Relaciones intergeneracionales e interculturales", key="ctx4")
ctx5 = st.text_area("5. Tensiones/conflictos en la concepción del territorio", key="ctx5")
ctx6 = st.text_area("6. Matrices de opresión identificadas en el territorio", key="ctx6")

st.subheader("B. Elementos asociados a la investigación")
inv1 = st.text_area("1. Particularidades de la investigación en Moravia (técnicas, relación con grupos sociales, lugar del sujeto, alcances, quién investiga)", key="inv1")
inv2 = st.text_area("2. Intereses que movilizan las investigaciones", key="inv2")
inv3 = st.text_area("3. Nexos entre investigación – acción – transformación", key="inv3")

st.subheader("C. Elementos de la intervención")
int1 = st.text_area("1. Actores que movilizan procesos de intervención barrial", key="int1")
int2 = st.text_area("2. Propuestas de intervención comunitarias (tipo, características)", key="int2")
int3 = st.text_area("3. Propuestas de intervención institucionales (tipo, características)", key="int3")
int4 = st.text_area("4. Papel de la memoria en los procesos de transformación territorial", key="int4")
int5 = st.text_area("5. Contradicciones en los procesos de intervención", key="int5")

# --- Foto opcional ---
foto = st.file_uploader("📷 Subir foto (opcional)", type=["jpg", "jpeg", "png"], key=st.session_state["foto_key"])

# === GUARDAR ===
if st.button("💾 Guardar entrada"):
    fecha_hora = datetime.now(colombia)

    # Guardar imagen si existe
    foto_base64 = None
    if foto is not None:
        foto_bytes = foto.read()
        if foto_bytes:
            foto_base64 = base64.b64encode(foto_bytes).decode("utf-8")

    registro = {
        "fecha_hora": fecha_hora,
        "lugar": lugar.strip(),
        "contexto": [ctx1, ctx2, ctx3, ctx4, ctx5, ctx6],
        "investigacion": [inv1, inv2, inv3],
        "intervencion": [int1, int2, int3, int4, int5],
        "foto": foto_base64
    }
    coleccion_moravia.insert_one(registro)

    st.success("✅ Entrada guardada correctamente.")

    # Activar limpieza diferida
    st.session_state["limpiar_form"] = True
    st.rerun()

# === HISTORIAL ===
st.header("📜 Historial")
registros = list(coleccion_moravia.find().sort("fecha_hora", -1))

for reg in registros:
    fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
    with st.expander(f"📅 {fecha_str} — {reg.get('lugar', 'Sin lugar')}"):
        st.markdown("**Elementos de Contexto**")
        for i, resp in enumerate(reg["contexto"], start=1):
            st.write(f"{i}. {resp}")
        st.markdown("**Elementos de la Investigación**")
        for i, resp in enumerate(reg["investigacion"], start=1):
            st.write(f"{i}. {resp}")
        st.markdown("**Elementos de la Intervención**")
        for i, resp in enumerate(reg["intervencion"], start=1):
            st.write(f"{i}. {resp}")
        if reg.get("foto"):
            img_bytes = base64.b64decode(reg["foto"])
            st.image(img_bytes, use_container_width=True)