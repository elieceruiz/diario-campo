import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
from fpdf import FPDF
import io
import re
import PyPDF2
from openai import OpenAI

# === Configuración ===
st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === MongoDB conexión ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# === Cliente OpenAI ===
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# === Función limpiar texto ===
def limpiar_texto(texto):
    texto = re.sub(r"^\s*\d+\.\s*", "", texto)
    texto = re.sub(r"^Elementos de Contexto:|^Elementos de la Investigación:|^Elementos de la Intervención:", "", texto, flags=re.IGNORECASE)
    return texto.strip()

# === Función para organizar y limpiar con IA (sin resumir) ===
def prompt_organizador_sin_resumir(registros, lugares_clave):
    registros = sorted(registros, key=lambda r: r["fecha_hora"])
    prompt = f"Tienes registros crudos con numeraciones y etiquetas, relacionados a estos lugares: {', '.join(lugares_clave)}.\n"
    prompt += "Límpialos eliminando cualquier numeración, etiqueta clara y repetitiva, pero conserva todo el texto original.\n"
    prompt += "Organiza los registros por lugar y fecha, manteniendo toda la información, sin sintetizar o resumir.\n\n"

    for reg in registros:
        fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar", "Sin lugar")
        prompt += f"[{fecha} - {lugar}]\n"
        for seccion in ["contexto", "investigacion", "intervencion"]:
            textos = reg.get(seccion, [])
            for t in textos:
                if t.strip():
                    prompt += f"{t.strip()}\n"
        prompt += "\n---\n"

    prompt += "\nDevuélvelos organizados y limpios, sin eliminar texto, solo quitando etiquetas y numeraciones innecesarias para lecturabilidad.\n"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente que organiza y limpia textos sin resumir."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error con OpenAI: {str(e)}"

# === Código Base original ===
st.title("📓 Diario de Campo - Moravia 2025")
st.caption("Registro guiado con base en las preguntas orientadoras de la salida de campo.")

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

with st.expander("Historial", expanded=False):
    registros_hist = list(coleccion_moravia.find().sort("fecha_hora", -1))
    for reg in registros_hist:
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

if st.button("📄 Exportar todo a PDF"):
    registros_export = list(coleccion_moravia.find().sort("fecha_hora", -1))
    if registros_export:
        pdf_data = generar_pdf(registros_export)
        st.download_button(
            "Descargar PDF",
            data=pdf_data,
            file_name="diario_campo_moravia.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("No hay registros para exportar.")

# === Pestañas ===
if "texto_ia" not in st.session_state:
    st.session_state["texto_ia"] = ""

tabs = st.tabs(["Base / Nuevo registro", "Procesar registros con IA"])

with tabs[0]:
    st.write("### Debug / Mensajes")
    st.write(st.session_state.get("texto_ia", "Aquí se mostrarán resultados o errores del procesamiento IA."))

with tabs[1]:
    st.header("Organizar y limpiar registros con OpenAI (sin resumir)")

    if st.button("Organizar y limpiar registros con IA sin resumir"):
        try:
            registros = list(coleccion_moravia.find())
            texto_limpio = prompt_organizador_sin_resumir(registros, ["Casa Cultural", "Viveros", "Almuerzo", "Barbería"])
            st.session_state["texto_ia"] = texto_limpio or "No se obtuvo texto limpio."
        except Exception as err:
            st.session_state["texto_ia"] = f"Error inesperado: {err}"

    if st.session_state["texto_ia"]:
        st.text_area("Registros limpios y estructurados", st.session_state["texto_ia"], height=600)
