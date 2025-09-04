import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io
import re

# Configuración
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion = db["moravia"]

LUGARES = ["Centro Cultural", "Barbería", "Viveros", "Almuerzo"]

def generar_pdf(registros):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("LiberationMono", "", "LiberationMono-Regular.ttf", uni=True)
    pdf.set_font("LiberationMono", size=12)
    pdf.cell(0, 10, "Diario de Campo - Moravia 2025", ln=True, align="C")
    pdf.ln(10)
    for reg in registros:
        fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar", "Sin lugar")
        pdf.set_font("LiberationMono", "", 14)
        pdf.cell(0, 10, f"{fecha} — {lugar}", ln=True)
        pdf.set_font("LiberationMono", "", 12)
        for bloque, titulo in [("contexto", "Elementos de Contexto"), ("investigacion", "Elementos de la Investigación"), ("intervencion", "Elementos de la Intervención")]:
            pdf.cell(0, 8, f"{titulo}:", ln=True)
            for i, texto in enumerate(reg.get(bloque, []), 1):
                if texto.strip():
                    pdf.multi_cell(0, 8, f"{i}. {texto}")
        pdf.ln(5)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer = io.BytesIO(pdf_bytes)
    pdf_buffer.seek(0)
    return pdf_buffer

def cargar_registros(order=-1):
    return list(coleccion.find().sort("fecha_hora", order))

def cargar_por_lugar(lugar, order=-1):
    filtro = {"lugar": {"$regex": re.escape(lugar), "$options": "i"}}
    return list(coleccion.find(filtro).sort("fecha_hora", order))

# UI

st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Proyecto final funcional y claro.")

tabs = st.tabs(["Base / Nuevo Registro", "Consulta Total"] + LUGARES)

# Pestaña Base - Formulario + Historial mínimo
with tabs[0]:
    st.header("Nuevo registro")
    with st.form("form_nuevo", clear_on_submit=True):
        lugar = st.text_input("📍 Lugar o punto del recorrido", placeholder="Ej: Centro Cultural Moravia")
        st.markdown("### A. Elementos de Contexto")
        ctx = [st.text_area(f"{i+1}.", key=f"ctx_{i}") for i in range(6)]
        st.markdown("### B. Elementos de la Investigación")
        inv = [st.text_area(f"{i+1}.", key=f"inv_{i}") for i in range(3)]
        st.markdown("### C. Elementos de la Intervención")
        interv = [st.text_area(f"{i+1}.", key=f"int_{i}") for i in range(5)]
        foto = st.file_uploader("📷 Subir foto (opcional)", type=["jpg","jpeg","png"])
        guardar = st.form_submit_button("💾 Guardar")
    if guardar:
        fecha = datetime.now(colombia)
        foto64 = None
        if foto:
            foto_bytes = foto.read()
            foto64 = base64.b64encode(foto_bytes).decode("utf-8") if foto_bytes else None
        doc = {
            "fecha_hora": fecha,
            "lugar": lugar.strip(),
            "contexto": ctx,
            "investigacion": inv,
            "intervencion": interv,
            "foto": foto64,
        }
        coleccion.insert_one(doc)
        st.success("Registro guardado.")

    with st.expander("Historial completo (más recientes primero)"):
        for reg in cargar_registros():
            fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
            with st.expander(f"{fecha} — {reg.get('lugar', 'Sin lugar')}"):
                st.markdown("**Elementos de Contexto**")
                for i, t in enumerate(reg.get("contexto", []), 1):
                    st.write(f"{i}. {t}")
                st.markdown("**Elementos de la Investigación**")
                for i, t in enumerate(reg.get("investigacion", []), 1):
                    st.write(f"{i}. {t}")
                st.markdown("**Elementos de la Intervención**")
                for i, t in enumerate(reg.get("intervencion", []), 1):
                    st.write(f"{i}. {t}")
                if foto := reg.get("foto"):
                    try:
                        img_bytes = base64.b64decode(foto)
                        st.image(img_bytes, use_container_width=True)
                    except:
                        st.error("Error mostrando imagen.")

    if st.button("📄 Exportar todo a PDF"):
        regs = cargar_registros()
        if regs:
            pdf = generar_pdf(regs)
            st.download_button("Descargar PDF", pdf, file_name="diario_campo_moravia.pdf", mime="application/pdf")
        else:
            st.warning("No hay registros para exportar.")

# Pestaña Consulta Total - solo mostrar todo
with tabs[1]:
    st.header("Consulta Total")
    registros = cargar_registros()
    if not registros:
        st.info("No hay registros guardados.")
    for reg in registros:
        fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        with st.expander(f"{fecha} — {reg.get('lugar', 'Sin lugar')}"):
            st.markdown("**Elementos de Contexto**")
            for i, t in enumerate(reg.get("contexto", []), 1):
                st.write(f"{i}. {t}")
            st.markdown("**Elementos de la Investigación**")
            for i, t in enumerate(reg.get("investigacion", []), 1):
                st.write(f"{i}. {t}")
            st.markdown("**Elementos de la Intervención**")
            for i, t in enumerate(reg.get("intervencion", []), 1):
                st.write(f"{i}. {t}")
            if foto := reg.get("foto"):
                try:
                    img_bytes = base64.b64decode(foto)
                    st.image(img_bytes, use_container_width=True)
                except:
                    st.error("Error mostrando imagen.")

# Pestañas por lugar con botón para cargar registros de ese lugar
for i, lugar in enumerate(LUGARES, start=2):
    with tabs[i]:
        st.header(f"Registros en {lugar}")
        if st.button(f"Cargar registros de {lugar}", key=f"btn_{i}"):
            regs_lugar = cargar_por_lugar(lugar)
            if not regs_lugar:
                st.info(f"No hay registros para {lugar}.")
            for reg in regs_lugar:
                fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
                with st.expander(f"{fecha} — {reg.get('lugar', 'Sin lugar')}"):
                    st.markdown("**Elementos de Contexto**")
                    for i, t in enumerate(reg.get("contexto", []), 1):
                        st.write(f"{i}. {t}")
                    st.markdown("**Elementos de la Investigación**")
                    for i, t in enumerate(reg.get("investigacion", []), 1):
                        st.write(f"{i}. {t}")
                    st.markdown("**Elementos de la Intervención**")
                    for i, t in enumerate(reg.get("intervencion", []), 1):
                        st.write(f"{i}. {t}")
                    if foto := reg.get("foto"):
                        try:
                            img_bytes = base64.b64decode(foto)
                            st.image(img_bytes, use_container_width=True)
                        except:
                            st.error("Error mostrando imagen.")
