import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import base64
import re
from openai import OpenAI

st.set_page_config(page_title="Diario de Campo - Moravia", layout="centered")
colombia = pytz.timezone("America/Bogota")

# MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["diario_campo"]
coleccion_moravia = db["moravia"]

# OpenAI cliente
openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# Funciones

def limpiar_texto(texto):
    texto = re.sub(r"^\s*\d+\.\s*", "", texto)
    texto = re.sub(r"^Elementos de Contexto:|^Elementos de la Investigación:|^Elementos de la Intervención:", "", texto, flags=re.IGNORECASE)
    return texto.strip()

def mostrar_registros_crudos_ordenados():
    LUGARES = ["Casa Cultural", "Viveros", "Almuerzo", "Barbería"]
    for lugar in LUGARES:
        st.subheader(f"Registros en {lugar}")
        regs = list(coleccion_moravia.find({"lugar": {"$regex": lugar, "$options": "i"}}).sort("fecha_hora", 1))
        if not regs:
            st.write("No hay registros.")
            continue
        hora_anter = None
        for r in regs:
            fecha = r["fecha_hora"].astimezone(colombia)
            hora_actual = fecha.strftime("%Y-%m-%d %H")
            if hora_anter and hora_actual != hora_anter:
                st.markdown("---")
                st.markdown(f"**Cambio de hora: {hora_actual}:00**")
            st.markdown(f"**{fecha.strftime('%Y-%m-%d %H:%M')}**")
            st.write("Contexto:")
            for c in r.get("contexto", []):
                txt = limpiar_texto(c)
                if txt: st.write(f"- {txt}")
            st.write("Investigación:")
            for i in r.get("investigacion", []):
                txt = limpiar_texto(i)
                if txt: st.write(f"- {txt}")
            st.write("Intervención:")
            for it in r.get("intervencion", []):
                txt = limpiar_texto(it)
                if txt: st.write(f"- {txt}")
            hora_anter = hora_actual

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

def prompt_dar_sentido_y_ubicar(registros, lugares_clave):
    registros = sorted(registros, key=lambda r: r["fecha_hora"])
    prompt = (
        f"Estos son registros tomados en campo, divididos en distintas áreas propuestas por la profesora:\n"
        f"- Elementos de Contexto\n- Elementos de la Investigación\n- Elementos de la Intervención\n"
        f"\nDebes interpretar cada texto y ubicarlo en la categoría correcta, organizando todo por lugar y fecha cronológica.\n"
        f"Da sentido al texto, estructúrale pero sin perder los detalles importantes. Elimina repeticiones y contenido claramente irrelevante.\n\n"
    )
    for reg in registros:
        fecha = reg["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
        lugar = reg.get("lugar", "Sin lugar")
        prompt += f"Lugar: {lugar}, Fecha: {fecha}\n"
        for campo, key in [("Elementos de Contexto", "contexto"), ("Elementos de la Investigación", "investigacion"), ("Elementos de la Intervención", "intervencion")]:
            textos = reg.get(key, [])
            if any(t.strip() for t in textos):
                prompt += f"{campo}:\n"
                for t in textos:
                    if t.strip():
                        prompt += f"- {t.strip()}\n"
        prompt += "\n---\n"
    prompt += "\nDevuelve un texto organizado con las categorías y registros claramente diferenciados, ordenados cronológicamente y por lugar."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages = [
                {"role": "system", "content": "Eres un asistente que organiza y da sentido profundo a registros de campo para trabajo académico."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error en OpenAI: {str(e)}"

# Inicializar estados
if "texto_ia" not in st.session_state:
    st.session_state["texto_ia"] = ""
if "texto_consentido" not in st.session_state:
    st.session_state["texto_consentido"] = ""

# Tabs sólida y orden
tabs = st.tabs(["1. Formulario", "2. Visualizar crudos", "3. Depurar IA", "4. Dar sentido IA"])

with tabs[0]:
    st.header("1. Ingresar nueva entrada")
    with st.form("form_registro", clear_on_submit=True):
        lugar = st.text_input("Lugar o Punto del recorrido")
        st.subheader("A. Elementos de Contexto")
        ctx1 = st.text_area("1. Principales hitos en la transformación territorial")
        ctx2 = st.text_area("2. Actores individuales y colectivos claves en la configuración del territorio")
        ctx3 = st.text_area("3. Principales transformaciones urbanas y su impacto social")
        ctx4 = st.text_area("4. Relaciones intergeneracionales e interculturales")
        ctx5 = st.text_area("5. Tensiones/conflictos en la concepción del territorio")
        ctx6 = st.text_area("6. Matrices de opresión identificadas en el territorio")
        st.subheader("B. Elementos asociados a la investigación")
        inv1 = st.text_area("1. Particularidades de la investigación en Moravia")
        inv2 = st.text_area("2. Intereses que movilizan las investigaciones")
        inv3 = st.text_area("3. Nexos entre investigación – acción – transformación")
        st.subheader("C. Elementos de la intervención")
        int1 = st.text_area("1. Actores que movilizan procesos de intervención barrial")
        int2 = st.text_area("2. Propuestas de intervención comunitarias")
        int3 = st.text_area("3. Propuestas de intervención institucionales")
        int4 = st.text_area("4. Papel de la memoria en los procesos de transformación territorial")
        int5 = st.text_area("5. Contradicciones en los procesos de intervención")
        foto = st.file_uploader("Foto (opcional)", type=["jpg", "jpeg", "png"])
        guardar = st.form_submit_button("Guardar entrada")
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
        st.success("Entrada guardada.")

with tabs[1]:
    st.header("2. Visualizar registros crudos organizados")
    mostrar_registros_crudos_ordenados()

with tabs[2]:
    st.header("3. Depurar y organizar con IA (sin resumir)")
    if st.button("Procesar limpieza IA"):
        registros = list(coleccion_moravia.find())
        texto_limpio = prompt_organizador_sin_resumir(registros, ["Casa Cultural", "Viveros", "Almuerzo", "Barbería"])
        st.session_state["texto_ia"] = texto_limpio or "No se obtuvo texto."
    if st.session_state["texto_ia"]:
        st.text_area("Texto limpio IA", st.session_state["texto_ia"], height=600)

with tabs[3]:
    st.header("4. Dar sentido y estructura final según profesora")
    if st.button("Interpretar y ubicar IA"):
        registros = list(coleccion_moravia.find())
        texto_final = prompt_dar_sentido_y_ubicar(registros, ["Casa Cultural", "Viveros", "Almuerzo", "Barbería"])
        st.session_state["texto_consentido"] = texto_final or "No se pudo generar texto."
    if st.session_state["texto_consentido"]:
        st.text_area("Texto con sentido IA", st.session_state["texto_consentido"], height=700)
