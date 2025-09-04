import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io
import openai

# Config y conexión
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

openai.api_key = st.secrets["openai_api_key"]

LUGARES_FIJOS = [
    "Centro Cultural / La Casa de Todos",
    "La Barbería",
    "Los Viveros",
    "Lugar de Almuerzo"
]

preguntas_contexto = [
    "Principales hitos en la transformación territorial",
    "Actores individuales y colectivos claves en la configuración del territorio",
    "Principales transformaciones urbanas y su impacto social",
    "Relaciones intergeneracionales e interculturales",
    "Tensiones/conflictos en la concepción del territorio",
    "Matrices de opresión identificadas en el territorio"
]

preguntas_investigacion = [
    "Particularidades de la investigación en Moravia (técnicas, relación con grupos sociales, lugar del sujeto, alcances, quién investiga)",
    "Intereses que movilizan las investigaciones",
    "Nexos entre investigación – acción – transformación"
]

preguntas_intervencion = [
    "Actores que movilizan procesos de intervención barrial",
    "Propuestas de intervención comunitarias (tipo, características)",
    "Propuestas de intervención institucionales (tipo, características)",
    "Papel de la memoria en los procesos de transformación territorial",
    "Contradicciones en los procesos de intervención"
]

# Funcs

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

def cargar_registros_por_lugar(lugar):
    # Busca registros con lugar exacto, case insensitive
    return list(coleccion_moravia.find({"lugar": {"$regex": f"^{lugar}$", "$options":"i"}}).sort("fecha_hora", 1))

def concatenar_por_pregunta(registros, campo, indice):
    textos = [r[campo][indice].strip() for r in registros if len(r.get(campo, [])) > indice and r[campo][indice].strip()]
    return "\n\n".join(textos) if textos else ""

# Guardar edición conjunto
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

# UI

st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

tabs = st.tabs(["Base/Formulario"] + LUGARES_FIJOS)

# Pestaña 1: Formulario base + historial
with tabs[0]:
    st.header("Formulario Base y Registros")
    with st.expander("Nueva entrada", expanded=False):
        with st.form("entrada_moravia", clear_on_submit=True):
            lugar = st.text_input("📍 Lugar o punto del recorrido", placeholder="Ej: Centro Cultural de Moravia", key="input_lugar")
            st.subheader("A. Elementos de Contexto")
            ctx = [st.text_area(f"{i+1}. {preguntas_contexto[i]}", key=f"ctx_{i}") for i in range(len(preguntas_contexto))]
            st.subheader("B. Elementos asociados a la investigación")
            inv = [st.text_area(f"{i+1}. {preguntas_investigacion[i]}", key=f"inv_{i}") for i in range(len(preguntas_investigacion))]
            st.subheader("C. Elementos de la intervención")
            intval = [st.text_area(f"{i+1}. {preguntas_intervencion[i]}", key=f"int_{i}") for i in range(len(preguntas_intervencion))]
            foto = st.file_uploader("📷 Subir foto (opcional)", type=["jpg", "jpeg", "png"], key="foto_uploader")
            guardar = st.form_submit_button("💾 Guardar entrada", key="guardar_btn")
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
                "contexto": ctx,
                "investigacion": inv,
                "intervencion": intval,
                "foto": foto_base64,
            }
            coleccion_moravia.insert_one(registro)
            st.success("✅ Entrada guardada correctamente.")

    # Historial expandible con todo
    with st.expander("Historial — revisa lo que hay:", expanded=False):
        registros = list(coleccion_moravia.find().sort("fecha_hora", -1))
        if not registros:
            st.info("No hay registros aún.")
        for reg in registros:
            fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
            with st.expander(f"{fecha_str} — {reg.get('lugar', 'Sin lugar')}"):
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

    if st.button("📄 Exportar todo a PDF", key="exportar_pdf"):
        registros_pdf = list(coleccion_moravia.find().sort("fecha_hora", -1))
        if registros_pdf:
            pdf_data = generar_pdf(registros_pdf)
            st.download_button(
                "Descargar PDF",
                data=pdf_data,
                file_name="diario_campo_moravia.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No hay registros para exportar.")

# Pestañas por lugar con todas las preguntas
for i, lugar in enumerate(LUGARES_FIJOS, start=1):
    with tabs[i]:
        st.header(lugar)

        registros_lugar = cargar_registros_por_lugar(lugar)

        st.subheader("A. Elementos de Contexto")
        respuestas_ctx = []
        for idx, pregunta in enumerate(preguntas_contexto):
            st.markdown(f"**{idx+1}. {pregunta}**")
            texto = concatenar_por_pregunta(registros_lugar, "contexto", idx)
            texto_edit = st.text_area(f"Respuesta {idx+1} Contexto", value=texto, height=100, key=f"contexto_{i}_{idx}")
            respuestas_ctx.append(texto_edit)

        st.subheader("B. Elementos asociados a la investigación")
        respuestas_inv = []
        for idx, pregunta in enumerate(preguntas_investigacion):
            st.markdown(f"**{idx+1}. {pregunta}**")
            texto = concatenar_por_pregunta(registros_lugar, "investigacion", idx)
            texto_edit = st.text_area(f"Respuesta {idx+1} Investigación", value=texto, height=100, key=f"investigacion_{i}_{idx}")
            respuestas_inv.append(texto_edit)

        st.subheader("C. Elementos de la intervención")
        respuestas_int = []
        for idx, pregunta in enumerate(preguntas_intervencion):
            st.markdown(f"**{idx+1}. {pregunta}**")
            texto = concatenar_por_pregunta(registros_lugar, "intervencion", idx)
            texto_edit = st.text_area(f"Respuesta {idx+1} Intervención", value=texto, height=100, key=f"intervencion_{i}_{idx}")
            respuestas_int.append(texto_edit)

        if st.button(f"Generar sugerencias GPT para {lugar}", key=f"gpt_{i}"):
            sug_ctx = obtener_sugerencia_gpt("\n\n".join(respuestas_ctx), "Contexto")
            sug_inv = obtener_sugerencia_gpt("\n\n".join(respuestas_inv), "Investigación")
            sug_int = obtener_sugerencia_gpt("\n\n".join(respuestas_int), "Intervención")
            st.text_area(f"Sugerencia Contexto {lugar}", value=sug_ctx, height=100, key=f"sug_ctx_{i}")
            st.text_area(f"Sugerencia Investigación {lugar}", value=sug_inv, height=100, key=f"sug_inv_{i}")
            st.text_area(f"Sugerencia Intervención {lugar}", value=sug_int, height=100, key=f"sug_int_{i}")

        if st.button(f"Guardar cambios en Mongo para {lugar}", key=f"save_{i}"):
            guardar_lugar(lugar, "\n".join(respuestas_ctx), "\n".join(respuestas_inv), "\n".join(respuestas_int))
            st.success(f"Datos guardados para {lugar}")
