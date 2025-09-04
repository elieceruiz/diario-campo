import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO (DB independiente) ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# === TÍTULO ===
st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

# === FUNCIONES ===
def generar_pdf(registros):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Agregar fuente Liberation Mono con soporte Unicode
    pdf.add_font("LiberationMono", "", "LiberationMono-Regular.ttf", uni=True)
    pdf.set_font("LiberationMono", size=12)

    pdf.cell(0, 10, "Diario de Campo - Moravia 2025", ln=True, align="C")
    pdf.ln(10)

    for reg in registros:
        fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar", "Sin lugar")

        pdf.set_font("LiberationMono", "B", 14)
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
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# === FORMULARIO PLEGADO ===
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
            "foto": foto_base64
        }
        coleccion_moravia.insert_one(registro)
        st.success("✅ Entrada guardada correctamente.")

# === HISTORIAL PLEGADO ===
with st.expander("Historial", expanded=False):
    registros = list(coleccion_moravia.find().sort("fecha_hora", -1))

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

# === BOTÓN PARA EXPORTAR PDF ===
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
