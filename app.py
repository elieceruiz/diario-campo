import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io
import openai

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# === CLAVE OPENAI ===
openai.api_key = st.secrets["openai_api_key"]

# === CONSTANTES ===
LUGARES_FIJOS = [
    "Centro Cultural / La Casa de Todos",
    "La Barbería",
    "Los Viveros",
    "Lugar de Almuerzo"
]

# === FUNCIONES ===
def generar_pdf(registros):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("LiberationMono", "", "LiberationMono-Regular.ttf", uni=True)
    pdf.set_font("LiberationMono", size=12)
    pdf.cell(0, 10, "Diario de Campo - Moravia 2025", ln=True, align="C")
    pdf.ln(10)
    for reg in registros:
        fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar", "Sin lugar")
        pdf.set_font("LiberationMono", "", 14)
        pdf.cell(0, 10, f"{fecha_str} — {lugar}", ln=True)
        pdf.set_font("LiberationMono", "", 12)
        pdf.cell(0, 8, "Elementos de Contexto:", ln=True)
        for i, resp in enumerate(reg["contexto"], start=1):
            if resp.strip():
                pdf.multi_cell(0, 8, f"{i}. {resp}")
        pdf.cell(0, 8, "Elementos de la Investigación:", ln=True)
        for i, resp in enumerate(reg["investigacion"], start=1):
            if resp.strip():
                pdf.multi_cell(0, 8, f"{i}. {resp}")
        pdf.cell(0, 8, "Elementos de la Intervención:", ln=True)
        for i, resp in enumerate(reg["intervencion"], start=1):
            if resp.strip():
                pdf.multi_cell(0, 8, f"{i}. {resp}")
        pdf.ln(5)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer = io.BytesIO(pdf_bytes)
    pdf_buffer.seek(0)
    return pdf_buffer

def obtener_sugerencia_gpt(texto, tipo_bloque):
    if not texto.strip():
        return "No hay texto para generar sugerencia."
    prompt = f"Como asistente para un diario de campo, analiza este texto del bloque {tipo_bloque} y propone un resumen/complemento para mejorar la coherencia y aportar detalles:\n\n{texto}\n\nRespuesta:"
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7,
            n=1
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error en API: {str(e)}"

def concatenar_textos(registros, campo):
    textos = sum([r.get(campo, []) for r in registros], [])
    return "\n\n".join([t for t in textos if t.strip()])

def cargar_registros_por_lugar(lugar):
    return list(coleccion_moravia.find({"lugar": {"$regex": lugar, "$options":"i"}}).sort("fecha_hora", 1))

def cargar_todo_texto_consolidado():
    registros = list(coleccion_moravia.find().sort("fecha_hora", 1))
    textos = []
    for r in registros:
        fecha_str = r["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = r.get("lugar", "Sin lugar")
        textos.append(f"{fecha_str} — {lugar}\nContexto:\n" + "\n".join(r["contexto"]) + "\nInvestigación:\n" + "\n".join(r["investigacion"]) + "\nIntervención:\n" + "\n".join(r["intervencion"]) + "\n\n---\n")
    return "\n".join(textos)

def guardar_lugar(lugar,texto_ctx,texto_inv,texto_int):
    doc = {
        "fecha_hora": datetime.now(colombia),
        "lugar": lugar,
        "contexto": [s.strip() for s in texto_ctx.split("\n") if s.strip()],
        "investigacion": [s.strip() for s in texto_inv.split("\n") if s.strip()],
        "intervencion": [s.strip() for s in texto_int.split("\n") if s.strip()],
        "foto": None,
    }
    coleccion_moravia.insert_one(doc)

# === TÍTULO ===
st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

tabs = st.tabs(["Base/Formulario"] + LUGARES_FIJOS)

# --- Pestaña 1: Formulario Base + Texto Consolidado ---
with tabs[0]:
    st.header("Formulario Base y Registros")
    with st.expander("Nueva entrada", expanded=False):
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
                "foto": foto_base64,
            }
            coleccion_moravia.insert_one(registro)
            st.success("✅ Entrada guardada correctamente.")
    if st.button("Mostrar texto consolidado registrado"):
        contenido_mierdero = cargar_todo_texto_consolidado()
        st.text_area("Texto Consolidado", contenido_mierdero, height=400)

    if st.button("📄 Exportar todo a PDF"):
        registros = list(coleccion_moravia.find().sort("fecha_hora", -1))
        if registros:
            pdf_data = generar_pdf(registros)
            st.download_button(
                "Descargar PDF",
                data=pdf_data,
                file_name="diario_campo_moravia.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No hay registros para exportar.")

# --- Pestañas por lugar ---
for i, lugar in enumerate(LUGARES_FIJOS, start=1):
    with tabs[i]:
        st.header(lugar)

        registros_lugar = cargar_registros_por_lugar(lugar)
        contexto = concatenar_textos(registros_lugar, "contexto")
        investigacion = concatenar_textos(registros_lugar, "investigacion")
        intervencion = concatenar_textos(registros_lugar, "intervencion")

        contexto_edit = st.text_area("Elementos de Contexto", contexto, height=150)
        investigacion_edit = st.text_area("Elementos de la Investigación", investigacion, height=150)
        intervencion_edit = st.text_area("Elementos de la Intervención", intervencion, height=150)

        if st.button(f"Generar sugerencias GPT para {lugar}", key=f"gpt_{lugar}"):
            sug_ctx = obtener_sugerencia_gpt(contexto_edit, "Contexto")
            sug_inv = obtener_sugerencia_gpt(investigacion_edit, "Investigación")
            sug_int = obtener_sugerencia_gpt(intervencion_edit, "Intervención")
            st.text_area(f"Sugerencia Contexto {lugar}", value=sug_ctx, height=100)
            st.text_area(f"Sugerencia Investigación {lugar}", value=sug_inv, height=100)
            st.text_area(f"Sugerencia Intervención {lugar}", value=sug_int, height=100)

        if st.button(f"Guardar cambios en Mongo para {lugar}", key=f"save_{lugar}"):
            guardar_lugar(lugar, contexto_edit, investigacion_edit, intervencion_edit)
            st.success(f"Datos guardados para {lugar}")
