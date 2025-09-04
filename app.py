import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io
import re

st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

LUGARES_FIJOS = ["Centro Cultural", "Barbería", "Viveros", "Almuerzo"]

def generar_pdf(registros):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Aquí la fuente ya debe estar en el repo y cargarse
    pdf.add_font("LiberationMono", "", "LiberationMono-Regular.ttf", uni=True)
    pdf.set_font("LiberationMono", size=12)
    pdf.cell(0, 10, "Diario de Campo - Moravia 2025", ln=True, align="C")
    pdf.ln(10)
    for reg in registros:
        fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar","Sin lugar")
        pdf.set_font("LiberationMono", "", 14)
        pdf.cell(0,10,f"{fecha_str} — {lugar}", ln=True)
        pdf.set_font("LiberationMono", "", 12)
        for bloque, titulo in [("contexto","Elementos de Contexto"), ("investigacion","Elementos de la Investigación"), ("intervencion","Elementos de la Intervención")]:
            pdf.cell(0,8,f"{titulo}:", ln=True)
            for i, texto in enumerate(reg.get(bloque, []),1):
                if texto.strip():
                    pdf.multi_cell(0,8, f"{i}. {texto}")
        pdf.ln(5)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer = io.BytesIO(pdf_bytes)
    pdf_buffer.seek(0)
    return pdf_buffer

def cargar_todos_registros():
    return list(coleccion_moravia.find().sort("fecha_hora", -1))

def cargar_registros_por_lugar(lugar):
    filtro = {"lugar": {"$regex": re.escape(lugar), "$options": "i"}}
    return list(coleccion_moravia.find(filtro).sort("fecha_hora", -1))

st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado basado en las preguntas orientadoras.")

tabs = st.tabs(["Base / Nuevo Registro"] + LUGARES_FIJOS)

# Pestaña base: formulario + historial
with tabs[0]:
    st.header("Nuevo Registro")
    with st.form("form_nuevo", clear_on_submit=True):
        lugar = st.text_input("📍 Lugar o punto del recorrido", placeholder="Ej: Centro Cultural Moravia", key="input_lugar")
        st.markdown("### Elementos de Contexto (6 campos)")
        ctx = [st.text_area(f"{i+1}.", key=f"ctx_{i}") for i in range(6)]
        st.markdown("### Elementos de la Investigación (3 campos)")
        inv = [st.text_area(f"{i+1}.", key=f"inv_{i}") for i in range(3)]
        st.markdown("### Elementos de la Intervención (5 campos)")
        interv = [st.text_area(f"{i+1}.", key=f"int_{i}") for i in range(5)]
        foto = st.file_uploader("📷 Subir foto (opcional)", type=["jpg","jpeg","png"], key="foto_uploader")
        guardar = st.form_submit_button("💾 Guardar")
    if guardar:
        fecha = datetime.now(colombia)
        foto64 = None
        if foto:
            foto_bytes = foto.read()
            if foto_bytes:
                foto64 = base64.b64encode(foto_bytes).decode("utf-8")
        registro = {
            "fecha_hora": fecha,
            "lugar": lugar.strip(),
            "contexto": ctx,
            "investigacion": inv,
            "intervencion": interv,
            "foto": foto64,
        }
        coleccion_moravia.insert_one(registro)
        st.success("Registro guardado correctamente.")

    with st.expander("Historial completo (más reciente arriba)"):
        registros = cargar_todos_registros()
        if not registros:
            st.info("No hay registros aún.")
        for reg in registros:
            fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
            with st.expander(f"{fecha_str} — {reg.get('lugar','Sin lugar')}"):
                st.markdown("**Elementos de Contexto**")
                for i, t in enumerate(reg.get("contexto",[]),1):
                    st.write(f"{i}. {t}")
                st.markdown("**Elementos de la Investigación**")
                for i, t in enumerate(reg.get("investigacion",[]),1):
                    st.write(f"{i}. {t}")
                st.markdown("**Elementos de la Intervención**")
                for i, t in enumerate(reg.get("intervencion",[]),1):
                    st.write(f"{i}. {t}")
                if foto := reg.get("foto", None):
                    try:
                        img_bytes = base64.b64decode(foto)
                        st.image(img_bytes, use_container_width=True)
                    except:
                        st.write("Error mostrando imagen.")

    if st.button("📄 Exportar todo a PDF", key="exportar_pdf"):
        registros_pdf = cargar_todos_registros()
        if registros_pdf:
            pdf_data = generar_pdf(registros_pdf)
            st.download_button(label="Descargar PDF", data=pdf_data, file_name="diario_campo_moravia.pdf", mime="application/pdf")
        else:
            st.warning("No hay registros para exportar.")

# Pestañas solo para mostrar registros por lugar
for i,lugar in enumerate(LUGARES_FIJOS,start=1):
    with tabs[i]:
        st.header(f"Registros en {lugar}")
        if st.button(f"Cargar registros de {lugar}", key=f"btn_cargar_{i}"):
            regs = cargar_registros_por_lugar(lugar)
            if not regs:
                st.info(f"No hay registros para {lugar}.")
            for reg in regs:
                fecha_str = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
                with st.expander(f"{fecha_str} — {reg.get('lugar','Sin lugar')}"):
                    st.markdown("**Elementos de Contexto**")
                    for i, t in enumerate(reg.get("contexto",[]),1):
                        st.write(f"{i}. {t}")
                    st.markdown("**Elementos de la Investigación**")
                    for i, t in enumerate(reg.get("investigacion",[]),1):
                        st.write(f"{i}. {t}")
                    st.markdown("**Elementos de la Intervención**")
                    for i, t in enumerate(reg.get("intervencion",[]),1):
                        st.write(f"{i}. {t}")
                    if foto := reg.get("foto", None):
                        try:
                            img_bytes = base64.b64decode(foto)
                            st.image(img_bytes, use_container_width=True)
                        except:
                            st.write("Error mostrando imagen.")
