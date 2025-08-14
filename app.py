import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from PIL import Image, ImageDraw, ImageFont
import io

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO (DB independiente) ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# === Función para crear emoji-calendario en español ===
def generar_calendario(fecha, size=80):
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    mes = meses_es[fecha.month - 1]
    dia = f"{fecha.day:02d}"

    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    # Franja roja
    draw.rectangle([0, 0, size, size * 0.25], fill=(220, 0, 0))

    try:
        font_mes = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.3))
        font_dia = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.65))
    except:
        font_mes = ImageFont.load_default()
        font_dia = ImageFont.load_default()

    # Mes
    w_mes, _ = draw.textsize(mes, font=font_mes)
    draw.text(((size - w_mes) / 2, size * 0.02), mes, fill="white", font=font_mes)

    # Día
    w_dia, _ = draw.textsize(dia, font=font_dia)
    draw.text(((size - w_dia) / 2, size * 0.3), dia, fill="black", font=font_dia)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# === FORMULARIO ===
st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

st.header("🆕 Nueva entrada")

with st.form("entrada_moravia", clear_on_submit=True):
    lugar = st.text_input("📍 Lugar o punto del recorrido", placeholder="Ej: Centro Cultural de Moravia")

    st.subheader("A. Elementos de Contexto")
    ctx1 = st.text_area("1. Principales hitos en la transformación territorial")
    ctx2 = st.text_area("2. Actores individuales y colectivos claves en la configuración del territorio")
    ctx3 = st.text_area("3. Principales transformaciones urbanas y su impacto social")
    ctx4 = st.text_area("4. Relaciones intergeneracionales e interculturales")
    ctx5 = st.text_area("5. Tensiones/conflictos en la concepción del territorio")
    ctx6 = st.text_area("6. Matrices de opresión identificadas en el territorio")

    st.subheader("B. Elementos asociados a la investigación")
    inv1 = st.text_area("1. Particularidades de la investigación en Moravia (técnicas, relación con grupos sociales, lugar del sujeto, alcances, quién investiga)")
    inv2 = st.text_area("2. Intereses que movilizan las investigaciones")
    inv3 = st.text_area("3. Nexos entre investigación – acción – transformación")

    st.subheader("C. Elementos de la intervención")
    int1 = st.text_area("1. Actores que movilizan procesos de intervención barrial")
    int2 = st.text_area("2. Propuestas de intervención comunitarias (tipo, características)")
    int3 = st.text_area("3. Propuestas de intervención institucionales (tipo, características)")
    int4 = st.text_area("4. Papel de la memoria en los procesos de transformación territorial")
    int5 = st.text_area("5. Contradicciones en los procesos de intervención")

    foto = st.file_uploader("📷 Subir foto (opcional)", type=["jpg", "jpeg", "png"])

    guardar = st.form_submit_button("💾 Guardar entrada")

if guardar:
    fecha_hora = datetime.now(colombia)

    foto_base64 = None
    if foto:
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

# === HISTORIAL ===
st.header("📜 Historial")
registros = list(coleccion_moravia.find().sort("fecha_hora", -1))

for reg in registros:
    fecha = reg["fecha_hora"].astimezone(colombia)
    fecha_str = fecha.strftime("%Y-%m-%d %H:%M")

    with st.expander(f"{reg.get('lugar', 'Sin lugar')} — {fecha_str}", expanded=False):
        # Mostrar emoji-calendario dentro del expander
        st.image(generar_calendario(fecha, size=60), width=60)
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