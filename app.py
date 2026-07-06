import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import plotly.graph_objects as go
from datetime import datetime, timedelta
from urllib.parse import quote
from pathlib import Path

st.set_page_config(page_title="CIAM&SUNI: Tu Salud, Personalizada", layout="wide", page_icon="🍎")

# =========================================================================================
# PALETA DE COLORES — UN COLOR DISTINTO POR CADA HOJA (inspirada en las pestañas del Excel)
# =========================================================================================
# idx : (numero, titulo, emoji, color_borde, color_fondo)
COLORES = {
    0:  ("0", "¡Introduce tus datos!",                       "📝", "#2196F3", "#E3F2FD"),
    1:  ("1", "Examen Médico de Sangre",                     "🩸", "#E53935", "#FFEBEE"),
    2:  ("2", "Índice de Masa Corporal y Percentil",         "⚖️", "#8E24AA", "#F3E5F5"),
    3:  ("3", "Tasa Metabólica Basal (TMB)",                 "⚡", "#FB8C00", "#FFF3E0"),
    4:  ("4", "Requerimiento Calórico Diario (RCD)",         "🔥", "#43A047", "#E8F5E9"),
    5:  ("5", "Subir, Mantener o Bajar el Peso",             "🎯", "#D81B60", "#FCE4EC"),
    6:  ("6", "Cálculo de los Macronutrientes",               "🍽️", "#FBC02D", "#FFFDE7"),
    7:  ("7", "Cálculo de las Porciones del Día",            "⏰", "#00ACC1", "#E0F7FA"),
    8:  ("8", "Página FatSecret",                             "🌐", "#00796B", "#E0F2F1"),
    9:  ("9", "Plan de Dieta Semanal",                        "🍱", "#FF7043", "#FBE9E7"),
    10: ("10", "Gasto Energético — Clima de Chiclayo",       "🌡️", "#F9A825", "#FFF8E1"),
    11: ("Aporte 1", "TMB en Embarazo",                       "👶", "#BA68C8", "#F8ECFB"),
    12: ("Aporte 2", "Hora Límite de Cafeína",                "🌙", "#5E35B1", "#EDE7F6"),
    13: ("13", "Línea de Tiempo: Tu Progreso Estimado",       "📈", "#3949AB", "#E8EAF6"),
    14: ("", "Sobre Nosotras",                                 "🎓", "#7A1F2B", "#FBEAEC"),
}

# =========================================================================================
# ESTILOS GLOBALES
# =========================================================================================
st.markdown("""
<style>
.big-title {
    background: linear-gradient(90deg, #56ab2f 0%, #a8e063 100%);
    padding: 22px 28px; border-radius: 18px; color: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15); margin-bottom: 6px;
}
.frase-motivadora {
    font-style: italic; color: #2e7d32; font-size: 1.05rem;
    text-align: center; margin: 6px 0 18px 0;
}
div[data-testid="stMetricValue"] { color: #2e7d32; font-weight: 800; }
div[data-testid="stMetric"] {
    background: #FAFAFA; border-radius: 14px; padding: 10px 14px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06); border: 1px solid #eee;
}

/* Pestañas más bonitas: negrita, más grandes, con separación */
button[data-baseweb="tab"] {
    font-weight: 700 !important;
    font-size: 0.92rem !important;
}
div[data-baseweb="tab-highlight"] { background-color: #56ab2f !important; height: 4px !important; }

/* Sidebar decorado */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f1f8e9 0%, #ffffff 60%);
}

/* Botones tipo link más redondeados */
a[data-testid="stLinkButton"] button, div[data-testid="stLinkButton"] button {
    border-radius: 20px !important;
    font-weight: 600 !important;
}

/* ---------- identidad visual tipo "landing page" ---------- */
.navbar {
    display: flex; align-items: center; justify-content: space-between;
    background: #ffffff; border-radius: 20px; padding: 10px 24px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08); margin-bottom: 18px;
    border: 1px solid #eef2ee;
}
.navbar-brand { display: flex; align-items: center; gap: 12px; }
.navbar-brand img { height: 78px; border-radius: 8px; }
.navbar-brand-text { line-height: 1.05; }
.navbar-brand-text .t1 { font-weight: 800; color: #2e7d32; font-size: 1.15rem; }
.navbar-brand-text .t2 { font-size: 0.82rem; color: #6b7a6c; }
.navbar-pill {
    background: #E8F5E9; color: #2e7d32; font-weight: 700; font-size: 0.78rem;
    padding: 6px 14px; border-radius: 999px; border: 1px solid #c8e6c9;
    white-space: nowrap;
}

.hero-card {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #2e7d32 0%, #56ab2f 55%, #8bc34a 100%);
    border-radius: 26px; padding: 42px 40px; color: white;
    box-shadow: 0 10px 30px rgba(46,125,50,0.25); margin-bottom: 22px;
}
.hero-card h1 { font-size: 2.1rem; font-weight: 800; margin: 0 0 10px 0; line-height: 1.15; }
.hero-card p.hero-sub { font-size: 1.02rem; opacity: 0.95; max-width: 640px; margin: 0 0 16px 0; }
.hero-badges { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.hero-badge {
    background: rgba(255,255,255,0.18); backdrop-filter: blur(2px);
    border: 1px solid rgba(255,255,255,0.35); color: white;
    padding: 7px 16px; border-radius: 999px; font-size: 0.82rem; font-weight: 600;
}
.hero-emoji-decor {
    position: absolute; right: 26px; top: 50%; transform: translateY(-50%);
    font-size: 6.5rem; opacity: 0.18; line-height: 1;
}

.feature-row { display: flex; gap: 16px; margin-bottom: 6px; }
.feature-card {
    flex: 1; background: #ffffff; border-radius: 18px; padding: 18px 18px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.06); border: 1px solid #f0f0f0;
    text-align: left;
}
.feature-card .fc-emoji { font-size: 1.8rem; }
.feature-card .fc-title { font-weight: 800; color: #2e2e2e; margin: 6px 0 4px 0; font-size: 0.98rem; }
.feature-card .fc-text { font-size: 0.82rem; color: #6b6b6b; line-height: 1.35; }

.equipo-card {
    background: #ffffff; border-radius: 16px; padding: 14px 18px; margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 6px solid #7A1F2B;
}
.equipo-card .nombre { font-weight: 800; color: #7A1F2B; font-size: 0.98rem; }
.equipo-card .puntos { font-size: 0.85rem; color: #555; margin-top: 2px; }
@media (max-width: 700px) {
    .feature-row { flex-direction: column; }
    .hero-emoji-decor { display: none; }
}
</style>
""", unsafe_allow_html=True)


def caja_util(texto, emoji="💡", color="#FFF3CD", borde="#FFC107"):
    """Caja amigable: '¿Para qué te sirve esto?' — pensada para público que no conoce las tablas técnicas."""
    st.markdown(f"""
    <div style="background-color:{color};padding:16px 20px;border-radius:14px;
                border-left:7px solid {borde};margin-top:14px;margin-bottom:6px;">
    <b>{emoji} ¿Para qué te sirve esto?</b><br>{texto}
    </div>
    """, unsafe_allow_html=True)


def hoja_header(idx, subtitulo=None):
    """Encabezado grande, en negrita y con el color propio de cada hoja (decora TODA la sección, no solo la tabla)."""
    numero, titulo, emoji, borde, fondo = COLORES[idx]
    sub_html = f"<p style='margin:4px 0 0 0;color:{borde};font-size:0.95rem;font-weight:500;'>{subtitulo}</p>" if subtitulo else ""
    st.markdown(f"""
    <div style="background:{fondo};border-left:10px solid {borde};border-radius:16px;
                padding:16px 26px;margin-bottom:16px;box-shadow:0 3px 10px rgba(0,0,0,0.10);">
    <h2 style="margin:0;color:{borde};font-weight:800;">{emoji} Hoja {numero}: {titulo}</h2>
    {sub_html}
    </div>
    """, unsafe_allow_html=True)


def tabla_bonita(df, idx):
    """Tabla con el color propio de la hoja: encabezado de color sólido y filas alternadas con el tono claro."""
    _, _, _, borde, fondo = COLORES[idx]
    styler = (
        df.style
        .set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", borde), ("color", "white"),
                ("font-weight", "700"), ("text-align", "center"),
                ("padding", "10px"), ("font-size", "0.92rem"),
            ]},
            {"selector": "tbody td", "props": [
                ("text-align", "center"), ("padding", "8px"), ("font-size", "0.9rem"),
            ]},
            {"selector": "tbody tr:nth-child(even)", "props": [("background-color", fondo)]},
            {"selector": "tbody tr:nth-child(odd)", "props": [("background-color", "#FFFFFF")]},
        ])
    )
    st.dataframe(styler, use_container_width=True, hide_index=True)


def caja_titulo(texto, idx):
    """Sub-título en negrita con el color de la hoja, para separar secciones dentro de una misma hoja."""
    _, _, _, borde, _ = COLORES[idx]
    st.markdown(f"<p style='color:{borde};font-weight:800;font-size:1.05rem;margin-top:14px;'>{texto}</p>",
                unsafe_allow_html=True)


def recursos_externos(idx, recursos):
    """Fila de botones 'para abrir' con recursos externos de confianza, en el color de la hoja."""
    st.markdown(f"<p style='font-weight:700;margin-bottom:2px;'>🔗 Quiero saber más:</p>", unsafe_allow_html=True)
    cols = st.columns(len(recursos))
    for c, (label, url) in zip(cols, recursos):
        with c:
            st.link_button(label, url, use_container_width=True)


# =========================================================================================
# TABLAS Y DATOS FIJOS (extraídos EXACTAMENTE del Excel "Grupo n°4 VER.2")
# =========================================================================================

FACTOR_ACTIVIDAD = {
    "Sedentaria": {"Hombre": 1.2, "Mujer": 1.2},
    "Ligero":     {"Hombre": 1.55, "Mujer": 1.56},
    "Moderada":   {"Hombre": 1.8, "Mujer": 1.64},
    "Intensa":    {"Hombre": 2.1, "Mujer": 1.82},
}

# Tablas de percentil IMC (Hoja 2), edad 2-20, (P5, P50, P85, P95)
PERCENTIL_MUJER = {
    2: (14.1, 16.3, 18.0, 19.1), 3: (13.5, 15.4, 17.1, 18.2), 4: (13.0, 15.1, 16.8, 18.0),
    5: (12.7, 15.0, 16.8, 18.2), 6: (12.7, 15.1, 17.2, 18.8), 7: (12.8, 15.4, 17.7, 19.6),
    8: (12.9, 15.7, 18.3, 20.6), 9: (13.1, 16.1, 19.1, 21.7), 10: (13.4, 16.6, 20.0, 22.9),
    11: (13.8, 17.2, 21.0, 24.1), 12: (14.3, 18.0, 22.0, 25.2), 13: (14.8, 18.7, 23.0, 26.3),
    14: (15.3, 19.3, 23.8, 27.3), 15: (15.8, 19.9, 24.5, 28.1), 16: (16.2, 20.3, 25.1, 28.9),
    17: (16.5, 20.6, 25.6, 29.6), 18: (16.7, 20.8, 26.0, 30.3), 19: (16.9, 21.0, 26.3, 31.0),
    20: (17.0, 21.2, 26.6, 31.7),
}
PERCENTIL_HOMBRE = {
    2: (14.5, 16.5, 18.2, 19.3), 3: (13.8, 15.6, 17.3, 18.3), 4: (13.3, 15.3, 16.8, 17.8),
    5: (13.0, 15.2, 16.6, 18.0), 6: (13.0, 15.3, 17.0, 18.5), 7: (13.1, 15.5, 17.4, 19.2),
    8: (13.3, 15.7, 18.0, 20.0), 9: (13.5, 16.1, 18.6, 21.0), 10: (13.7, 16.6, 19.4, 22.1),
    11: (14.1, 17.2, 20.2, 23.2), 12: (14.5, 17.8, 21.1, 24.2), 13: (14.9, 18.5, 21.9, 25.2),
    14: (15.5, 19.2, 22.7, 26.0), 15: (16.0, 19.8, 23.5, 26.8), 16: (16.5, 20.5, 24.2, 27.6),
    17: (16.9, 21.1, 24.9, 28.3), 18: (17.3, 21.7, 25.6, 29.0), 19: (17.6, 22.2, 26.3, 29.8),
    20: (17.9, 22.6, 26.9, 30.6),
}

# Alimentos por comida y macronutriente: {alimento: kcal base} — EXACTOS del Excel (Hoja 9)
DIETA = {
    "Desayuno": {
        "Carbohidrato": {"Avena cocida": 150, "Pan integral": 70, "Cereal integral": 110, "Manzana": 95,
                          "Tostada de pan de centeno": 65, "Pera": 100, "Batata cocida": 90, "Mandarina": 45},
        "Proteína": {"Huevo hervido": 155, "Claras de huevo": 52, "Leche descremada": 34,
                     "Queso cottage": 98, "Queso ricotta": 174, "Jamón serrano": 241},
        "Grasa": {"Palta": 160, "Almendras": 79, "Mantequilla de maní": 88,
                  "Semillas de chía": 86, "Nueces": 64, "Crema de almendra": 64},
    },
    "Merienda 1": {
        "Carbohidrato": {"Piña": 50, "Manzana verde": 52, "Uvas": 69, "Kiwi": 61,
                          "Pan pita integral": 275, "Zanahoria cruda": 41},
        "Proteína": {"Yogur natural": 61, "Atún": 132, "Clara de huevo cocida": 52, "Jamón serrano": 241},
        "Grasa": {"Pistachos": 52, "Avellanas": 68, "Semillas de calabaza": 75, "Aceite de oliva": 104},
    },
    "Almuerzo": {
        "Carbohidrato": {"Arroz integral": 123, "Quinoa cocida": 120, "Couscous cocido": 112,
                          "Garbanzos cocidos": 164, "Lentejas": 116},
        "Proteína": {"Pechuga de pollo": 165, "Fillete de res magra": 217, "Pescado blanco": 96,
                     "Salmón a la plancha": 208, "Pavo al horno": 135, "Bacalao a la plancha": 105},
        "Grasa": {"Aceite de oliva": 104, "Aceitunas verdes": 45, "Queso parmesano": 91,
                  "Queso gouda": 66, "Aguacate": 160, "Aceite de linaza": 84},
    },
    "Merienda 2": {
        "Carbohidrato": {"Pan integral": 70, "Galletas integrales": 120, "Banana": 89,
                         "Pan árabe": 275, "Barra de granola": 180, "Pan de maíz": 266},
        "Proteína": {"Queso ricotta": 174, "Yogurt griego": 97, "Pollo desmenuzado": 165,
                     "Yogur descremado": 34, "Clara de huevo": 52},
        "Grasa": {"Anacardos": 53, "Queso brie": 64, "Almendras fileteadas": 109, "Mantequilla": 94},
    },
    "Cena": {
        "Carbohidrato": {"Papa sancochada": 87, "Batata": 86, "Verduras mixtas": 65, "Palomitas de maíz": 387,
                          "Calabaza asada": 45, "Brócoli cocido": 35, "Tomates cherry": 18, "Espinaca salteada": 41},
        "Proteína": {"Huevos revueltos": 148, "Sardinas": 208, "Pechuga de pavo": 135,
                     "Pechuga de pollo": 165, "Filete de pescado blanco": 96},
        "Grasa": {"Aceitunas": 55, "Queso crema": 202, "Aceite de aguacate": 84, "Semillas de girasol": 54},
    },
}

# =========================================================================================
# LÍMITES BIOLÓGICOS MÁXIMOS DOCUMENTADOS (récords históricos) — usados como tope duro en los inputs
# =========================================================================================
PESO_MAX = {"Hombre": 635.0, "Mujer": 544.0}        # Jon Brower Minnoch / Carol Yager
ESTATURA_MAX = {"Hombre": 272, "Mujer": 248}         # Robert Wadlow / Zeng Jinlian
EDAD_MAX = {"Hombre": 116, "Mujer": 122}             # Jiroemon Kimura / Jeanne Calment

# Límites razonables para el examen médico (para evitar valores clínicamente imposibles)
HEMO_MAX = 25.0
TRIGLI_MAX = 2000.0
GLUCO_MAX = 700.0
COLES_MAX = 500.0
HIERRO_MAX = 500.0

# =========================================================================================
# FUNCIONES DE CLASIFICACIÓN CLÍNICA (réplica EXACTA de las fórmulas SI anidadas del Excel)
# =========================================================================================

def clasif_hemoglobina(valor, etapa, genero):
    if valor is None or valor == 0:
        return "Introducir datos"
    if valor > 20:
        return "Valor Imposible"
    if etapa == "Niñez":
        if valor < 8: return "Anemia grave"
        elif valor <= 10.9: return "Anemia moderada"
        elif valor <= 11.4: return "Anemia leve"
        else: return "Normal"
    if etapa == "Adolescencia" and genero == "Mujer":
        if valor < 8: return "Anemia grave"
        elif valor <= 10.9: return "Anemia moderada"
        elif valor <= 11.9: return "Anemia leve"
        else: return "Normal"
    if genero == "Hombre":
        if valor < 8: return "Anemia grave"
        elif valor <= 10.9: return "Anemia moderada"
        elif valor <= 12.9: return "Anemia leve"
        else: return "Normal"
    # Réplica fiel: el Excel original NO cubre "Mujer" en Adultez/Vejez -> "Revisa Datos"
    return "Revisa Datos"

def clasif_trigliceridos(valor):
    if valor is None or valor == 0: return "Introducir datos"
    if valor < 150: return "Normal"
    elif valor <= 199: return "Límite alto"
    elif valor <= 499: return "Alto"
    else: return "Muy alto"

def clasif_glucosa(valor):
    if valor is None or valor == 0: return "Introducir datos"
    if valor < 70: return "Hipoglucemia"
    elif valor <= 99: return "Normal"
    elif valor <= 125: return "Prediabetes"
    else: return "Diabetes"

def clasif_colesterol(valor):
    if valor is None or valor == 0: return "Introducir datos"
    if valor < 200: return "Deseable"
    elif valor <= 239: return "Límite alto"
    else: return "Alto"

def clasif_hierro(valor, etapa, genero):
    if valor is None or valor == 0: return "Introducir datos"
    if etapa in ["Niñez", "Adolescencia"]:
        if valor < 50: return "Bajo"
        elif valor <= 120: return "Normal"
        else: return "Alto"
    elif etapa in ["Adultez", "Vejez"]:
        if genero == "Mujer":
            if valor < 50: return "Bajo"
            elif valor <= 170: return "Normal"
            else: return "Alto"
        elif genero == "Hombre":
            if valor < 65: return "Bajo"
            elif valor <= 175: return "Normal"
            else: return "Alto"
        else:
            return "Género no válido"
    return "Etapa no válida"

# =========================================================================================
# SEMÁFORO CLÍNICO — protocolo de triaje digital (verde / ámbar / rojo)
# =========================================================================================
CATEGORIA_SEMAFORO = {
    # Hemoglobina
    "Normal": "verde", "Anemia leve": "ambar", "Anemia moderada": "rojo", "Anemia grave": "rojo",
    # Triglicéridos
    "Límite alto": "ambar", "Alto": "rojo", "Muy alto": "rojo",
    # Glucosa
    "Hipoglucemia": "ambar", "Prediabetes": "ambar", "Diabetes": "rojo",
    # Colesterol
    "Deseable": "verde",
    # Hierro
    "Bajo": "ambar",
    # Estados neutros / sin dato
    "Introducir datos": "gris", "Valor Imposible": "gris", "Revisa Datos": "gris",
    "Género no válido": "gris", "Etapa no válida": "gris", "Edad fuera de tabla (2-20 años)": "gris",
}

SEMAFORO_ESTILO = {
    "verde": {"hex": "#43A047", "fondo": "#E8F5E9", "emoji": "🟢", "etiqueta": "Normal"},
    "ambar": {"hex": "#FB8C00", "fondo": "#FFF3E0", "emoji": "🟡", "etiqueta": "Alerta"},
    "rojo":  {"hex": "#E53935", "fondo": "#FFEBEE", "emoji": "🔴", "etiqueta": "Crítico"},
    "gris":  {"hex": "#9E9E9E", "fondo": "#F5F5F5", "emoji": "⚪", "etiqueta": "Sin dato"},
}

MENSAJES_TRIAJE = {
    "Hemoglobina": {
        "verde": "¡Excelente balance! Tus niveles de hemoglobina están en equilibrio. Sigue priorizando hierro y proteínas de calidad.",
        "ambar": "Estás en una zona de atención. Prioriza alimentos ricos en hierro (carnes rojas, legumbres, espinaca) junto con vitamina C para mejorar su absorción.",
        "rojo": "Tus valores sugieren un riesgo de anemia. Te recomendamos consultar a un especialista y priorizar hierro y proteínas en tu dieta.",
        "gris": "Ingresa tu valor de hemoglobina para obtener una recomendación personalizada.",
    },
    "Triglicéridos": {
        "verde": "¡Muy bien! Tus triglicéridos están dentro del rango deseable. Mantén tu consumo de grasas saludables y actividad física.",
        "ambar": "Estás en una zona límite. Considera reducir azúcares y carbohidratos simples, y aumentar la fibra en tu dieta.",
        "rojo": "Tus valores están elevados. Te recomendamos consultar a un especialista y reducir grasas saturadas, azúcares y alcohol.",
        "gris": "Ingresa tu valor de triglicéridos para obtener una recomendación personalizada.",
    },
    "Glucosa": {
        "verde": "¡Excelente! Tu glucosa está en un rango saludable. Sigue manteniendo horarios de comida regulares.",
        "ambar": "Estás en una zona de atención. Reduce azúcares simples y controla el tamaño de tus porciones de carbohidratos.",
        "rojo": "Tus valores sugieren riesgo metabólico. Te recomendamos consultar a un especialista cuanto antes.",
        "gris": "Ingresa tu valor de glucosa para obtener una recomendación personalizada.",
    },
    "Colesterol": {
        "verde": "¡Muy bien! Tu colesterol está en un nivel deseable. Continúa priorizando grasas saludables como el aceite de oliva y el aguacate.",
        "ambar": "Estás en una zona límite. Considera reducir frituras y grasas saturadas, y aumentar el consumo de fibra.",
        "rojo": "Tus valores están elevados. Te recomendamos consultar a un especialista y priorizar una dieta baja en grasas saturadas.",
        "gris": "Ingresa tu valor de colesterol para obtener una recomendación personalizada.",
    },
    "Hierro": {
        "verde": "¡Excelente! Tus reservas de hierro están equilibradas. Sigue priorizando nutrientes naturales.",
        "ambar": "Estás en una zona de atención. Aumenta el consumo de alimentos ricos en hierro (carnes, legumbres, vegetales verdes).",
        "rojo": "Tus valores están fuera de rango. Te recomendamos consultar a un especialista para evaluar tu estado nutricional.",
        "gris": "Ingresa tu valor de hierro para obtener una recomendación personalizada.",
    },
}


def evaluar_estado_clinico(parametro, categoria):
    """Función de triaje digital: toma la categoría clínica ya calculada (ej. 'Anemia leve') y
    retorna el color de semáforo, su estilo visual y un mensaje de recomendación personalizado."""
    color = CATEGORIA_SEMAFORO.get(categoria, "gris")
    estilo = SEMAFORO_ESTILO[color]
    mensaje = MENSAJES_TRIAJE.get(parametro, {}).get(color, "Sin recomendación disponible.")
    return {
        "colorSemaforo": color,
        "hex": estilo["hex"],
        "fondo": estilo["fondo"],
        "emoji": estilo["emoji"],
        "etiqueta": estilo["etiqueta"],
        "mensajePersonalizado": mensaje,
    }


def tarjeta_semaforo(parametro, valor_texto, categoria):
    """Renderiza una tarjeta tipo 'semáforo clínico' con anillo de color, categoría y recomendación."""
    r = evaluar_estado_clinico(parametro, categoria)
    st.markdown(f"""
    <div style="background:#ffffff;border-radius:20px;padding:16px 14px;text-align:center;
                box-shadow:0 4px 14px rgba(0,0,0,0.08);border-top:6px solid {r['hex']};height:100%;">
        <div style="width:64px;height:64px;border-radius:50%;background:{r['fondo']};
                    border:3px solid {r['hex']};display:flex;align-items:center;justify-content:center;
                    margin:0 auto 10px auto;font-size:1.6rem;">{r['emoji']}</div>
        <div style="font-weight:800;color:#2e2e2e;font-size:0.95rem;">{parametro}</div>
        <div style="color:#777;font-size:0.8rem;margin-bottom:4px;">{valor_texto}</div>
        <div style="font-weight:800;color:{r['hex']};font-size:0.88rem;margin-bottom:8px;">{categoria}</div>
        <div style="font-size:0.76rem;color:#555;line-height:1.3;">{r['mensajePersonalizado']}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================================================
# IMPACTO DINÁMICO POR ÁMBITO — cómo afecta cada resultado clínico según Escolar/Laboral/Emocional
# =========================================================================================
EFECTOS_PARAMETRO = {
    "Hemoglobina": {
        "verde": "una buena oxigenación de tu cerebro y músculos",
        "ambar": "una oxigenación algo reducida, que puede generar cansancio leve",
        "rojo": "una oxigenación insuficiente por un posible cuadro de anemia",
        "gris": "datos insuficientes para evaluar tu oxigenación",
    },
    "Triglicéridos": {
        "verde": "un metabolismo de grasas equilibrado",
        "ambar": "una acumulación de grasa en la sangre que empieza a ser notoria",
        "rojo": "un riesgo cardiovascular por exceso de grasa en la sangre",
        "gris": "datos insuficientes para evaluar tus triglicéridos",
    },
    "Glucosa": {
        "verde": "niveles de energía estables durante el día",
        "ambar": "fluctuaciones de energía que pueden causar picos y bajones de concentración",
        "rojo": "un desbalance importante en tu energía y concentración",
        "gris": "datos insuficientes para evaluar tu glucosa",
    },
    "Colesterol": {
        "verde": "arterias limpias y una buena circulación",
        "ambar": "un inicio de acumulación de grasa en tus arterias",
        "rojo": "un riesgo de obstrucción arterial que afecta tu circulación",
        "gris": "datos insuficientes para evaluar tu colesterol",
    },
    "Hierro": {
        "verde": "buenas reservas de energía y defensas",
        "ambar": "reservas de hierro bajas que pueden causar cansancio",
        "rojo": "reservas de hierro muy comprometidas",
        "gris": "datos insuficientes para evaluar tus reservas de hierro",
    },
}

AMBITO_PLANTILLAS = {
    "Escolar/Académico": {
        "verde": "📚 En el colegio, tener {efecto} te ayuda a mantener la concentración en clase y rendir bien en tus evaluaciones. ¡Sigue así!",
        "ambar": "📚 En el colegio, {efecto} podría hacer que te cueste un poco más concentrarte o te sientas cansad@ en las últimas horas de clase. Presta atención a tu alimentación antes de estudiar.",
        "rojo": "📚 En el colegio, {efecto} puede afectar seriamente tu atención, memoria y rendimiento académico. Es importante que converses con un adulto responsable y consultes a un especialista.",
        "gris": "📚 Ingresa tu valor para saber cómo podría afectar tu rendimiento escolar.",
    },
    "Laboral": {
        "verde": "💼 En tu vida laboral, tener {efecto} te da la energía necesaria para cumplir tus tareas con enfoque y sin fatiga excesiva.",
        "ambar": "💼 En un entorno laboral, {efecto} podría traducirse en menor productividad hacia el final de la jornada. Vale la pena ajustar hábitos alimenticios.",
        "rojo": "💼 En un entorno laboral, {efecto} puede generar fatiga crónica, bajo rendimiento y mayor riesgo de errores. Se recomienda atención profesional antes de continuar con actividades exigentes.",
        "gris": "💼 Ingresa tu valor para saber cómo podría afectar tu desempeño laboral.",
    },
    "Psicológico/Emocional": {
        "verde": "💚 A nivel emocional, tener {efecto} contribuye a un estado de ánimo estable y mayor resistencia al estrés diario.",
        "ambar": "💚 A nivel emocional, {efecto} puede relacionarse con irritabilidad, cambios de humor leves o mayor sensación de estrés.",
        "rojo": "💚 A nivel emocional, {efecto} está asociado a mayor irritabilidad, ansiedad o desánimo. Cuidar este aspecto físico también ayuda a tu bienestar emocional — no dudes en buscar apoyo si lo necesitas.",
        "gris": "💚 Ingresa tu valor para saber cómo podría afectar tu estado emocional.",
    },
}


def generar_impacto_ambito(parametro, categoria, ambito):
    """Genera el texto dinámico de impacto de un resultado clínico según el ámbito elegido
    (Escolar/Académico, Laboral, Psicológico/Emocional), usando el color de semáforo ya calculado."""
    color = CATEGORIA_SEMAFORO.get(categoria, "gris")
    efecto = EFECTOS_PARAMETRO.get(parametro, {}).get(color, "")
    plantilla = AMBITO_PLANTILLAS[ambito][color]
    return plantilla.format(efecto=efecto)

def clasif_percentil(imc, edad, genero):
    """Réplica EXACTA de la fórmula del Excel (Hoja 2, celda K17:L17)."""
    tabla = PERCENTIL_HOMBRE if genero == "Hombre" else PERCENTIL_MUJER
    if edad not in tabla:
        return None, "Edad fuera de tabla (2-20 años)"
    p5, p50, p85, p95 = tabla[edad]
    if imc < p5: percentil, cat = "< 5", "Bajo Peso"
    elif imc < p85: percentil, cat = "50", "Peso Saludable"
    elif imc < p95: percentil, cat = "85", "Sobrepeso"
    else: percentil, cat = "95", "Obesidad"
    return percentil, cat

def clasif_imc_adulto(imc):
    if imc < 18.5: return "Bajo Peso"
    elif imc <= 24.9: return "Peso Saludable"
    elif imc <= 29.9: return "Sobrepeso"
    elif imc <= 34.9: return "Obesidad Clase 1"
    elif imc <= 39.9: return "Obesidad Clase 2"
    else: return "Obesidad Clase 3"


def grafico_percentil_peso(genero_tabla, estatura_m_usuario, edad_usuario=None, peso_usuario=None, genero_usuario=None):
    """Construye un gráfico interactivo de Plotly con las curvas de peso-para-la-edad (P5, P50, P85, P95),
    convirtiendo las tablas de percentil de IMC a kilogramos usando la estatura actual del usuario.
    Si la edad y género del usuario coinciden con esta tabla, agrega un punto destacado con su posición."""
    tabla = PERCENTIL_HOMBRE if genero_tabla == "Hombre" else PERCENTIL_MUJER
    edades = sorted(tabla.keys())
    p5 = [tabla[e][0] * estatura_m_usuario ** 2 for e in edades]
    p50 = [tabla[e][1] * estatura_m_usuario ** 2 for e in edades]
    p85 = [tabla[e][2] * estatura_m_usuario ** 2 for e in edades]
    p95 = [tabla[e][3] * estatura_m_usuario ** 2 for e in edades]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edades, y=p95, mode="lines", name="P95 (Obesidad)",
                              line=dict(color="#8E24AA", dash="dot", width=2)))
    fig.add_trace(go.Scatter(x=edades, y=p85, mode="lines", name="P85 (Sobrepeso)",
                              line=dict(color="#FB8C00", dash="dot", width=2)))
    fig.add_trace(go.Scatter(x=edades, y=p50, mode="lines", name="P50 (Peso Saludable)",
                              line=dict(color="#43A047", width=3)))
    fig.add_trace(go.Scatter(x=edades, y=p5, mode="lines", name="P5 (Bajo Peso)",
                              line=dict(color="#E53935", dash="dot", width=2)))

    if genero_usuario == genero_tabla and edad_usuario in tabla:
        fig.add_trace(go.Scatter(x=[edad_usuario], y=[peso_usuario], mode="markers+text",
                                  name="Tú estás aquí", text=["Tú"], textposition="top center",
                                  marker=dict(color="#1565C0", size=16, symbol="star",
                                              line=dict(color="white", width=1))))

    fig.update_layout(
        xaxis_title="Edad (años)", yaxis_title="Peso equivalente (kg)",
        height=380, margin=dict(t=20, l=10, r=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def nombre_display(nombre, genero="Mujer"):
    """Devuelve el nombre ingresado, o un saludo genérico según el género si aún no lo escribió."""
    nombre = (nombre or "").strip()
    if nombre:
        return nombre
    return "invitada" if genero == "Mujer" else "invitado"


def etapa_desde_edad(edad_valor):
    """Detecta automáticamente la etapa de vida a partir de la edad ingresada."""
    if edad_valor <= 11:
        return "Niñez"
    elif edad_valor <= 17:
        return "Adolescencia"
    elif edad_valor <= 59:
        return "Adultez"
    else:
        return "Vejez"

# =========================================================================================
# ENCABEZADO — estilo "landing page", con el logo real del colegio
# =========================================================================================
ASSETS_DIR = Path(__file__).parent / "assets"
_LOGO_ANCHO = ASSETS_DIR / "logo_santa_maria_reina.png"     # banner con los 4 escudos
_ESCUDO = ASSETS_DIR / "escudo_santa_maria_reina.png"        # escudo grande (para "Sobre Nosotros")

# --- Identidad de marca CIAM&SUNI y personajes educativos (stickers) ---
_LOGO_CIRCULAR = ASSETS_DIR / "logo_circular_ciamsuni.png"
_LOGO_WORDMARK = ASSETS_DIR / "logo_wordmark_ciamsuni.png"
_STICKER_NINA = ASSETS_DIR / "nina_escolar.png"
_STICKER_NINA_ALT = ASSETS_DIR / "nina_escolar_transparente.png"
_STICKER_MAESTRA = ASSETS_DIR / "maestra_animada_transparente.png"
_STICKER_PROFESOR = ASSETS_DIR / "profesor_escolar_transparente_bonito.png"
_STICKER_CORRIENDO = ASSETS_DIR / "muneca_santamaria_corriendo.png"


def mostrar_sticker(ruta, ancho=170):
    """Muestra un personaje/sticker si el archivo existe; no rompe la app si falta."""
    if ruta.exists():
        st.image(str(ruta), width=ancho)

def _img_b64(path):
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return None

_logo_b64 = _img_b64(_LOGO_ANCHO)

# --- Identidad de marca: logo circular + logotipo tipográfico, en una sola tarjeta ordenada ---
if _LOGO_CIRCULAR.exists() or _LOGO_WORDMARK.exists():
    _col_izq, _col_centro, _col_der = st.columns([1, 3, 1])
    with _col_centro:
        st.markdown("""
        <div style="background:#ffffff;border-radius:22px;padding:18px 28px;margin-bottom:6px;
                    box-shadow:0 4px 16px rgba(0,0,0,0.08);border:1px solid #eef2ee;">
        """, unsafe_allow_html=True)
        _lc, _lw = st.columns([1, 2.4])
        with _lc:
            if _LOGO_CIRCULAR.exists():
                st.image(str(_LOGO_CIRCULAR), width=110)
        with _lw:
            if _LOGO_WORDMARK.exists():
                st.image(str(_LOGO_WORDMARK), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- Barra de navegación superior, con el logo real del colegio ---
if _logo_b64:
    st.markdown(f"""
    <div class="navbar">
        <div class="navbar-brand">
            <img src="data:image/png;base64,{_logo_b64}" />
            <div class="navbar-brand-text">
                <div class="t1">🥦 CIAM&SUNI</div>
                <div class="t2">Tu Salud, Personalizada — C.E.P. "Santa María Reina", Chiclayo</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="navbar">
        <div class="navbar-brand">
            <div class="navbar-brand-text">
                <div class="t1">🥦 CIAM&SUNI</div>
                <div class="t2">Tu Salud, Personalizada — C.E.P. "Santa María Reina", Chiclayo</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Hero principal ---
st.markdown("""
<div class="hero-card">
    <div class="hero-emoji-decor">🥗🍎</div>
    <h1>CIAM&SUNI: Tu Salud, Personalizada</h1>
    <p class="hero-sub">Una réplica interactiva del Excel oficial del proyecto: ingresa tus datos una sola
    vez y obtén tu IMC, tu requerimiento calórico, tus macronutrientes y un plan de dieta armado —
    todo explicado paso a paso para que cualquier persona lo entienda. 😊</p>
    <div class="hero-badges">
        <span class="hero-badge">🎓 5° "C" Secundaria — Grupo N°04</span>
        <span class="hero-badge">🔬 Fórmulas científicas (Mifflin-St Jeor)</span>
        <span class="hero-badge">☀️ Ajustado al clima de Chiclayo</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Tarjetas de características (estilo landing page) ---
st.markdown("""
<div class="feature-row">
    <div class="feature-card">
        <div class="fc-emoji">🧮</div>
        <div class="fc-title">Cálculo preciso</div>
        <div class="fc-text">IMC, percentil, TMB, RCD y macronutrientes calculados con las mismas
        fórmulas del Excel original.</div>
    </div>
    <div class="feature-card">
        <div class="fc-emoji">🍽️</div>
        <div class="fc-title">Dieta a tu gusto</div>
        <div class="fc-text">Arma tu menú diario eligiendo alimentos reales, ajustados automáticamente
        a tu meta calórica.</div>
    </div>
    <div class="feature-card">
        <div class="fc-emoji">🩺</div>
        <div class="fc-title">Salud en simple</div>
        <div class="fc-text">Tus análisis de sangre traducidos a un lenguaje claro: Normal, Anemia leve,
        Alto, etc.</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="frase-motivadora">🍎 "Comer bien no es una dieta, es un acto de amor hacia ti mismo" 💚</p>', unsafe_allow_html=True)

# --- Acceso directo al Excel original, para que cualquiera pueda abrirlo/descargarlo libremente ---
_POSIBLES_NOMBRES_EXCEL = [
    "Grupo_n_4_VER_2.xlsx", "Grupo_n_4_VER_2__1_.xlsx", "Grupo n°4 VER.2.xlsx", "Grupo_n_4_VER.2.xlsx",
]
_ruta_excel = None
for _nombre in _POSIBLES_NOMBRES_EXCEL:
    _candidata = Path(__file__).parent / _nombre
    if _candidata.exists():
        _ruta_excel = _candidata
        break

with st.container():
    st.markdown("""
    <div style="background:#E8F5E9;border-left:9px solid #43A047;border-radius:16px;
                padding:14px 22px;margin-bottom:10px;box-shadow:0 3px 8px rgba(0,0,0,0.08);">
    <b>📂 ¿Quieres ver el Excel original completo?</b><br>
    Aquí puedes abrir o descargar el archivo de Excel tal cual, con todas sus hojas y fórmulas.
    </div>
    """, unsafe_allow_html=True)
    if _ruta_excel is not None:
        with open(_ruta_excel, "rb") as _f:
            st.download_button(
                "📥 Abrir / Descargar el Excel original",
                data=_f.read(),
                file_name="Proyecto_Sana_Alimentacion_Grupo_04.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.info("Para habilitar este botón, coloca el archivo del Excel (por ejemplo "
                "`Grupo_n_4_VER_2.xlsx`) en la misma carpeta que este script `app.py` antes de ejecutarlo.")

st.markdown("---")

# =========================================================================================
# SIDEBAR — HOJA 0.-DATOS
# =========================================================================================
if _ESCUDO.exists():
    st.sidebar.image(str(_ESCUDO), width=90)

st.sidebar.header("📝 ¡Introduce tus datos!")

genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"], index=1)

nombre_usuario = st.sidebar.text_input("¿Cómo te llamas?", "")
_nombre_saludo = nombre_display(nombre_usuario, genero)
if nombre_usuario.strip():
    st.sidebar.success(f"¡Paz y bien, {_nombre_saludo}! 🌟 Vamos a armar tu plan personalizado.")
else:
    st.sidebar.caption("✍️ Escribe tu nombre para que tu plan se sienta hecho a tu medida.")

peso_max_actual = PESO_MAX[genero]
peso = st.sidebar.number_input(
    "Peso (en kg):", min_value=1.0, max_value=peso_max_actual, value=min(75.0, peso_max_actual), step=0.1,
    help=f"Tope máximo: {peso_max_actual:.0f} kg."
)
st.sidebar.caption(
    "⚠️ No se puede superar el peso corporal más alto documentado en la historia médica: "
    f"{'Jon Brower Minnoch, ~635 kg (Hombres)' if genero=='Hombre' else 'Carol Yager, ~544 kg (Mujeres)'}. "
    "El sistema no acepta valores mayores."
)

estatura_max_actual = ESTATURA_MAX[genero]
estatura = st.sidebar.number_input(
    "Estatura (en cm):", min_value=30, max_value=estatura_max_actual, value=min(168, estatura_max_actual), step=1,
    help=f"Tope máximo: {estatura_max_actual} cm."
)
st.sidebar.caption(
    "⚠️ No se puede superar la estatura más alta documentada en la historia: "
    f"{'Robert Wadlow, 2.72 m (Hombres)' if genero=='Hombre' else 'Zeng Jinlian, 2.48 m (Mujeres)'}. "
    "El sistema no acepta valores mayores."
)

edad_max_actual = EDAD_MAX[genero]
edad = st.sidebar.number_input(
    "Edad (en años):", min_value=1, max_value=edad_max_actual, value=9, step=1,
    help=f"Tope máximo: {edad_max_actual} años."
)
st.sidebar.caption(
    "⚠️ No se puede superar la edad humana más longeva documentada: "
    f"{'Jiroemon Kimura, 116 años (Hombres)' if genero=='Hombre' else 'Jeanne Calment, 122 años (Mujeres)'}. "
    "El sistema no acepta valores mayores."
)

# --- Etapa detectada automáticamente al ingresar la edad (ya no se elige manualmente) ---
etapa = etapa_desde_edad(edad)
st.sidebar.success(f"🔎 Etapa detectada automáticamente: **{etapa}**")

actividad = st.sidebar.selectbox("Actividad física:", ["Sedentaria", "Ligero", "Moderada", "Intensa"], index=1)
objetivo = st.sidebar.selectbox("Objetivo:", ["Mantenerse", "Bajar de peso", "Subir de peso"], index=1)

if objetivo == "Bajar de peso":
    ajuste_txt = st.sidebar.selectbox("Ajuste calórico aplicado:", ["0", "10%", "15%", "20%"])
    ajuste_bajar = float(ajuste_txt.strip("%")) / 100 if "%" in ajuste_txt else 0.0
    ajuste_subir = 0.0
elif objetivo == "Subir de peso":
    ajuste_txt = st.sidebar.selectbox("Ajuste calórico aplicado:", ["0", "+10%", "+20%", "+30%"])
    ajuste_subir = float(ajuste_txt.replace("+", "").strip("%")) / 100 if "%" in ajuste_txt else 0.0
    ajuste_bajar = 0.0
else:
    ajuste_txt = "0"
    ajuste_bajar = 0.0
    ajuste_subir = 0.0

st.sidebar.markdown("---")
st.sidebar.info("ℹ️ **¿Cómo saber mi actividad física?**\n\n"
                 "**Sedentaria:** solo actividades de la vida diaria (estudiar, dormir).\n\n"
                 "**Ligero:** ejercicio 1-3 veces por semana.\n\n"
                 "**Moderada:** ejercicio 3-5 veces por semana.\n\n"
                 "**Intensa:** ejercicio diario de alta intensidad o deportista de competencia.")

# --- indicador de "¿qué significa el ajuste calórico y el plazo?" ---
if objetivo == "Mantenerse":
    st.sidebar.info("ℹ️ **¿Qué significa el ajuste calórico y el plazo?**\n\n"
                     "Como tu objetivo es **mantenerte**, no se aplica ningún ajuste (0%): "
                     "simplemente comerás lo mismo que gastas.\n\n"
                     "Si más adelante eliges *Bajar* o *Subir* de peso, aquí te explicaremos "
                     "qué significa cada porcentaje y cuánto tiempo toma ver resultados.")
else:
    st.sidebar.info("ℹ️ **¿Qué significa el ajuste calórico y el plazo?**\n\n"
                     "El **ajuste calórico** es cuánto le sumas o restas a tu RCD (Hoja 4) para lograr tu meta. "
                     "Mientras más alto el porcentaje, más rápido cambia tu peso — pero también exige más disciplina.\n\n"
                     "**Corto plazo (10%):** cambios notorios en pocas semanas. El más exigente y menos recomendado "
                     "para menores de edad.\n\n"
                     "**Plazo medio (15% bajar / 20% subir):** un punto intermedio entre velocidad y sostenibilidad.\n\n"
                     "**Plazo largo (20% bajar / 30% subir):** cambios más lentos, pero más seguros, fáciles de "
                     "mantener y adecuados para cuerpos en crecimiento.\n\n"
                     "**0%:** no aplica ningún cambio; tu peso se mantiene igual.")

st.sidebar.markdown("---")
st.sidebar.subheader("Datos adicionales (Hoja 1 - Examen médico)")
hemo = st.sidebar.number_input("Hemoglobina (g/dL):", min_value=0.0, max_value=HEMO_MAX, value=0.0, step=0.1,
                                help=f"Tope máximo: {HEMO_MAX:.0f} g/dL (valores mayores son clínicamente imposibles).")
trigli = st.sidebar.number_input("Triglicéridos (mg/dL):", min_value=0.0, max_value=TRIGLI_MAX, value=0.0, step=1.0,
                                  help=f"Tope máximo: {TRIGLI_MAX:.0f} mg/dL.")
gluco = st.sidebar.number_input("Glucosa (mg/dL):", min_value=0.0, max_value=GLUCO_MAX, value=0.0, step=1.0,
                                 help=f"Tope máximo: {GLUCO_MAX:.0f} mg/dL.")
coles = st.sidebar.number_input("Colesterol (mg/dL):", min_value=0.0, max_value=COLES_MAX, value=0.0, step=1.0,
                                 help=f"Tope máximo: {COLES_MAX:.0f} mg/dL.")
hierro = st.sidebar.number_input("Hierro (µg/dL):", min_value=0.0, max_value=HIERRO_MAX, value=0.0, step=1.0,
                                  help=f"Tope máximo: {HIERRO_MAX:.0f} µg/dL.")
st.sidebar.caption("⚠️ Estos topes evitan valores clínicamente imposibles; el sistema no acepta cifras mayores.")

# =========================================================================================
# CÁLCULOS CENTRALES (siguiendo el orden y las referencias EXACTAS de las hojas del Excel)
# =========================================================================================
estatura_m = estatura / 100.0
imc = round(peso / (estatura_m ** 2))  # =REDONDEAR(D30/F30) -> 0 decimales, igual que el Excel

if genero == "Hombre":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161

factor = FACTOR_ACTIVIDAD[actividad][genero]
rcd = tmb * factor  # Hoja 4: RCD = TMB x Factor de actividad

# Hoja 5: ajuste según objetivo
if objetivo == "Bajar de peso":
    ajuste_aplicado = ajuste_bajar
    rcd_final = rcd * (1 - ajuste_aplicado)
elif objetivo == "Subir de peso":
    ajuste_aplicado = ajuste_subir
    rcd_final = rcd * (1 + ajuste_aplicado)
else:
    ajuste_aplicado = 0.0
    rcd_final = rcd

# Plazo estimado (=S23 del Excel)
if ajuste_bajar == 0.10 or ajuste_subir == 0.10:
    plazo = "Corto plazo"
elif ajuste_bajar == 0.15 or ajuste_subir == 0.20:
    plazo = "Plazo medio"
elif ajuste_bajar == 0.20 or ajuste_subir == 0.30:
    plazo = "Plazo largo"
else:
    plazo = "—"

# Hoja 6: Macronutrientes
cal_prot = rcd_final * 0.20
cal_carb = rcd_final * 0.50
cal_gras = rcd_final * 0.30
gr_prot = cal_prot / 4
gr_carb = cal_carb / 4
gr_gras = cal_gras / 9

# Hoja 7: Porciones del día
porciones = {
    "Desayuno":   {"pct": 0.25, "kcal": rcd_final * 0.25},
    "Merienda 1": {"pct": 0.05, "kcal": rcd_final * 0.05},
    "Almuerzo":   {"pct": 0.40, "kcal": rcd_final * 0.40},
    "Merienda 2": {"pct": 0.05, "kcal": rcd_final * 0.05},
    "Cena":       {"pct": 0.25, "kcal": rcd_final * 0.25},
}

# Hoja 10: Gasto energético ajustado al clima de Chiclayo
rcd_chiclayo = rcd * 0.95

# =========================================================================================
# NAVEGACIÓN
# =========================================================================================
st.subheader("📋 Navegación por Hojas del Sistema (idéntica al Excel)")
tabs = st.tabs([
    "0.-DATOS", "1.-EXAMEN MÉDICO", "2.-IMC Y PERCENTIL", "3.-TMB", "4.-RCD",
    "5.-OBJETIVO", "6.-MACRONUTRIENTES", "7.-PORCIONES", "8.-FATSECRET",
    "9.-DIETA", "10.-CLIMA CHICLAYO", "11.-APORTE 1: EMBARAZO", "12.-APORTE 2: CAFEÍNA",
    "13.-LÍNEA DE TIEMPO", "🎓 SOBRE NOSOTROS"
])

# --- Al cambiar de pestaña, sube la página al inicio para que cada Hoja se sienta separada ---
components.html("""
<script>
function activarScrollAlCambiarTab() {
    const doc = window.parent.document;
    const botones = doc.querySelectorAll('button[data-baseweb="tab"]');
    botones.forEach((btn) => {
        if (!btn.dataset.scrollFixApplied) {
            btn.dataset.scrollFixApplied = "true";
            btn.addEventListener('click', () => {
                setTimeout(() => { window.parent.scrollTo({top: 0, behavior: 'smooth'}); }, 60);
            });
        }
    });
}
activarScrollAlCambiarTab();
new MutationObserver(activarScrollAlCambiarTab).observe(window.parent.document.body, {childList: true, subtree: true});
</script>
""", height=0)

# ---------------------------------------------------------------------------------------
with tabs[0]:
    hoja_header(0, "El punto de partida: aquí registras todo lo que la app necesita saber de ti.")

    col_datos, col_sticker = st.columns([2, 1])
    with col_datos:
        df0 = pd.DataFrame({
            "Variable": ["Nombre", "Peso", "Edad", "Estatura", "Estatura (m)", "Género", "Actividad física",
                         "Objetivo", "Ajuste (bajar)", "Ajuste (subir)", "Etapa (detectada)"],
            "Valor": [_nombre_saludo, f"{peso} kg", f"{edad} años", f"{estatura} cm", f"{estatura_m}", genero, actividad,
                      objetivo, f"{ajuste_bajar*100:.0f}%", f"{ajuste_subir*100:.0f}%", etapa]
        })
        tabla_bonita(df0, 0)
    with col_sticker:
        if _STICKER_NINA.exists():
            mostrar_sticker(_STICKER_NINA, ancho=190)
        elif _STICKER_NINA_ALT.exists():
            mostrar_sticker(_STICKER_NINA_ALT, ancho=190)
        st.caption(f"¡Bienvenid@, {_nombre_saludo}! 👋")

    st.divider()
    caja_util(f"¡Paz y bien, {_nombre_saludo}! Aquí registras tus datos básicos una sola vez, y toda la app se ajusta "
              "automáticamente a ti: desde tus calorías diarias hasta tu plan de comidas. La etapa de vida se "
              "detecta sola apenas escribes tu edad. ¡Es el punto de partida de todo tu plan personalizado! 🌟",
              emoji="📝", color="#E3F2FD", borde="#2196F3")

# ---------------------------------------------------------------------------------------
with tabs[1]:
    hoja_header(1, "Categoriza tus datos según su nivel correspondiente, exactamente como las fórmulas SI anidadas del Excel.")

    _cat_hemo = clasif_hemoglobina(hemo, etapa, genero)
    _cat_trigli = clasif_trigliceridos(trigli)
    _cat_gluco = clasif_glucosa(gluco)
    _cat_coles = clasif_colesterol(coles)
    _cat_hierro = clasif_hierro(hierro, etapa, genero)

    col_examen, col_docente = st.columns([3, 1])
    with col_docente:
        if _STICKER_MAESTRA.exists():
            mostrar_sticker(_STICKER_MAESTRA, ancho=170)
        elif _STICKER_PROFESOR.exists():
            mostrar_sticker(_STICKER_PROFESOR, ancho=170)
        st.caption("Tu guía experta interpreta cada resultado del semáforo por ti. 🩺")

    with col_examen:
        st.markdown("#### 🚦 Semáforo Clínico — protocolo de triaje digital")
        st.caption(f"No solo diagnostica: te sugiere una ruta de mejora inmediata, {_nombre_saludo}. 🟢 Normal · 🟡 Alerta · 🔴 Crítico")
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1: tarjeta_semaforo("Hemoglobina", f"{hemo} g/dL", _cat_hemo)
        with sc2: tarjeta_semaforo("Triglicéridos", f"{trigli} mg/dL", _cat_trigli)
        with sc3: tarjeta_semaforo("Glucosa", f"{gluco} mg/dL", _cat_gluco)
        with sc4: tarjeta_semaforo("Colesterol", f"{coles} mg/dL", _cat_coles)
        with sc5: tarjeta_semaforo("Hierro", f"{hierro} µg/dL", _cat_hierro)

    st.divider()

    df_examen = pd.DataFrame({
        "Parámetro": ["Hemoglobina", "Triglicéridos", "Glucosa", "Colesterol", "Hierro"],
        "Valor": [f"{hemo} g/dL", f"{trigli} mg/dL", f"{gluco} mg/dL", f"{coles} mg/dL", f"{hierro} µg/dL"],
        "Resultado obtenido": [_cat_hemo, _cat_trigli, _cat_gluco, _cat_coles, _cat_hierro]
    })
    tabla_bonita(df_examen, 1)

    st.divider()
    st.markdown("#### 🎯 ¿Cómo impacta esto en tu día a día?")
    ambito_seleccionado = st.selectbox(
        "Elige el ámbito en el que quieres ver reflejado el impacto de tus resultados:",
        ["Escolar/Académico", "Laboral", "Psicológico/Emocional"]
    )
    _resultados_ambito = [
        ("Hemoglobina", _cat_hemo), ("Triglicéridos", _cat_trigli), ("Glucosa", _cat_gluco),
        ("Colesterol", _cat_coles), ("Hierro", _cat_hierro),
    ]
    for _parametro, _categoria in _resultados_ambito:
        _color_pt = CATEGORIA_SEMAFORO.get(_categoria, "gris")
        _hex_pt = SEMAFORO_ESTILO[_color_pt]["hex"]
        _fondo_pt = SEMAFORO_ESTILO[_color_pt]["fondo"]
        _texto_impacto = generar_impacto_ambito(_parametro, _categoria, ambito_seleccionado)
        st.markdown(f"""
        <div style="background:{_fondo_pt};border-left:6px solid {_hex_pt};border-radius:12px;
                    padding:10px 16px;margin-bottom:8px;">
        <b>{_parametro}</b> ({_categoria}) — {_texto_impacto}
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 Ver tablas de referencia clínica completas"):
        caja_titulo("Hemoglobina", 1)
        tabla_bonita(pd.DataFrame({
            "Grupo Poblacional": ["Niños 5–11 años", "Adolescentes", "Mujeres", "Hombres", "Mujeres embarazadas"],
            "Normal": ["≥ 11,5 g/dL", "≥ 12,0 g/dL", "≥ 12,0 g/dL", "≥ 13,0 g/dL", "≥ 11,0 g/dL"],
            "Anemia leve": ["11,0 – 11,4", "11,0 – 11,9", "11,0 – 11,9", "12,0 – 12,9", "10,0 – 10,9"],
            "Anemia moderada": ["8,0 – 10,9", "8,0 – 10,9", "8,0 – 10,9", "8,0 – 10,9", "7,0 – 9,9"],
            "Anemia grave": ["< 8,0", "< 8,0", "< 8,0", "< 8,0", "< 7,0"]
        }), 1)
        caja_titulo("Hierro", 1)
        tabla_bonita(pd.DataFrame({
            "Grupo poblacional": ["Niños y adolescentes", "Mujeres", "Hombres"],
            "Bajo": ["< 50", "< 50", "< 65"], "Normal": ["50-120", "50-170", "65-175"],
            "Alto": ["> 120", "> 170", "> 175"]
        }), 1)
        caja_titulo("Triglicéridos / Glucosa / Colesterol", 1)
        tabla_bonita(pd.DataFrame({
            "Triglicéridos": ["Normal < 150", "Límite alto 150–199", "Alto 200–499", "Muy alto ≥ 500"],
            "Glucosa": ["Hipoglucemia < 70", "Normal 70–99", "Prediabetes 100–125", "Diabetes ≥ 126"],
            "Colesterol": ["Deseable < 200", "Límite alto 200–239", "Alto ≥ 240", ""]
        }), 1)
    st.warning("⚠️ Nota de fidelidad al Excel: la fórmula original de Hemoglobina no contempla el caso "
               "'Mujer' en etapa Adultez/Vejez, por lo que en ese caso el sistema (igual que el Excel) "
               "devuelve **'Revisa Datos'**.")
    recursos_externos(1, [
        ("🩸 Anemia (MedlinePlus)", "https://medlineplus.gov/spanish/anemia.html"),
        ("🫀 Colesterol (MedlinePlus)", "https://medlineplus.gov/spanish/cholesterol.html"),
        ("💉 Diabetes (OMS)", "https://www.who.int/es/news-room/fact-sheets/detail/diabetes"),
    ])
    caja_util("Un análisis de sangre trae puros números y siglas difíciles de entender (¿12.5 g/dL es bueno o malo?). "
              "Esta hoja traduce esos números a un lenguaje simple: 'Normal', 'Anemia leve', 'Alto', etc. "
              "Así sabes de un vistazo si algún valor necesita atención médica. 🩺❤️",
              emoji="🩸", color="#FFEBEE", borde="#E53935")

# ---------------------------------------------------------------------------------------
with tabs[2]:
    hoja_header(2, "El IMC sirve para saber si una persona tiene un peso saludable según su altura y peso. "
                   "En adolescentes y niños se incluye también el Percentil.")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Resultado IMC", imc)
        st.latex(r"IMC = \frac{Peso\ (kg)}{Altura\ (m)^2}")
    with col2:
        if etapa in ["Niñez", "Adolescencia"]:
            percentil, categoria = clasif_percentil(imc, edad, genero)
            if percentil is None:
                st.error(categoria)
            else:
                st.metric("Percentil", percentil)
                st.metric("Categoría", categoria)
        else:
            categoria = clasif_imc_adulto(imc)
            st.metric("Categoría (Adultez/Vejez, sin percentil)", categoria)

    caja_titulo("Categorías generales de IMC", 2)
    tabla_bonita(pd.DataFrame({
        "Clasificación": ["Bajo Peso", "Peso Saludable", "Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3 (Severa)"],
        "Rango de IMC": ["Menos de 18.5", "18.5 a 24.9", "25 a 29.9", "30 o más", "30 a 34.9", "35 a 39.9", "40 o más"]
    }), 2)

    st.markdown("#### 📈 Percentiles de peso por edad (2 a 20 años)")
    st.caption("Convertimos las curvas de percentil de IMC a kilogramos usando tu estatura actual, y marcamos "
               "tu posición exacta (edad vs. peso) con una estrella azul, si tu edad está entre 2 y 20 años.")
    sub_mujeres, sub_hombres = st.tabs(["👧 Mujeres", "👦 Hombres"])
    with sub_mujeres:
        st.plotly_chart(grafico_percentil_peso("Mujer", estatura_m, edad, peso, genero), use_container_width=True)
    with sub_hombres:
        st.plotly_chart(grafico_percentil_peso("Hombre", estatura_m, edad, peso, genero), use_container_width=True)
    if edad not in PERCENTIL_MUJER:
        st.caption("ℹ️ Tu edad actual está fuera del rango de 2-20 años, así que no aparece tu punto marcado en el gráfico.")

    with st.expander("📊 Ver tabla completa de percentiles (edad 2-20 años)"):
        cm, ch = st.columns(2)
        with cm:
            caja_titulo("Mujer", 2)
            st.dataframe(pd.DataFrame(PERCENTIL_MUJER, index=["P5 (Bajo Peso)", "P50 (Saludable)", "P85 (Sobrepeso)", "P95 (Obesidad)"]).T,
                         use_container_width=True)
        with ch:
            caja_titulo("Hombre", 2)
            st.dataframe(pd.DataFrame(PERCENTIL_HOMBRE, index=["P5 (Bajo Peso)", "P50 (Saludable)", "P85 (Sobrepeso)", "P95 (Obesidad)"]).T,
                         use_container_width=True)
    caja_util("El IMC te dice, de forma simple, si tu peso está en un rango saludable para tu altura. "
              "En niños y adolescentes se usa además el 'percentil', que te compara con otros chicos de tu misma "
              "edad y sexo — porque el cuerpo de un niño en crecimiento no se mide igual que el de un adulto. 📏⚖️",
              emoji="⚖️", color="#F3E5F5", borde="#8E24AA")

# ---------------------------------------------------------------------------------------
with tabs[3]:
    hoja_header(3, "Fórmula de Mifflin-St Jeor. Biológicamente, los hombres suelen tener más masa muscular y "
                   "las mujeres más porcentaje de grasa; como el músculo quema más energía, el resultado cambia según el sexo.")
    if genero == "Hombre":
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) + 5")
    else:
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) - 161")
    st.metric("Resultado TMB", f"{tmb:.0f} kcal/día")
    caja_util("La TMB es la energía mínima que tu cuerpo necesita para vivir si te quedaras todo el día en cama: "
              "respirar, hacer latir tu corazón, mantener tu temperatura, etc. Es la base sobre la que se calcula "
              "TODO lo demás en esta app (cuánto debes comer, cuánto puedes bajar o subir de peso, etc.). 🔥",
              emoji="⚡", color="#FFF3E0", borde="#FB8C00")

# ---------------------------------------------------------------------------------------
with tabs[4]:
    hoja_header(4)
    st.latex(r"RCD = TMB \times Factor\ de\ Actividad")
    tabla_bonita(pd.DataFrame({
        "Actividad": ["Sedentaria", "Ligero", "Moderada", "Intensa"],
        "Hombres": [1.2, 1.55, 1.8, 2.1],
        "Mujeres": [1.2, 1.56, 1.64, 1.82]
    }), 4)
    col1, col2 = st.columns(2)
    col1.metric(f"Factor aplicado ({actividad}, {genero})", factor)
    col2.metric("Resultado RCD", f"{rcd:.0f} kcal/día")
    caja_util("Este es el número más importante de toda la app: son las calorías reales que gastas en un día "
              "normal, sumando tu TMB (Hoja 3) más el movimiento que haces según tu nivel de actividad. "
              "Es tu 'punto de equilibrio' calórico. 🏃‍♀️🔥",
              emoji="🔥", color="#E8F5E9", borde="#43A047")

# ---------------------------------------------------------------------------------------
with tabs[5]:
    hoja_header(5)
    st.info("A diferencia de los adultos, el cuerpo de los menores necesita energía constante no solo para "
            "moverse, sino para el desarrollo de órganos y huesos. Por ello, cualquier ajuste calórico debe "
            "ser controlado para jamás arriesgar su correcto desarrollo biológico.")
    tabla_bonita(pd.DataFrame({
        "Objetivo nutricional": [objetivo],
        "Ajuste calórico aplicado": [f"{ajuste_aplicado*100:.0f}%"],
        "RCD (Hoja 4)": [f"{rcd:.0f}"],
        "Resultado final": [f"{rcd_final:.0f} kcal/día"]
    }), 5)
    st.metric("Plazo estimado del cambio", plazo)

    st.markdown(f"""
    <div style="background-color:#FCE4EC;padding:16px 20px;border-radius:14px;
                border-left:7px solid #D81B60;margin-top:10px;margin-bottom:6px;">
    <b>ℹ️ ¿Qué significa el plazo estimado?</b><br>
    <b>Corto plazo (10%):</b> el ajuste más fuerte; genera cambios notorios en pocas semanas, pero exige más
    disciplina y control médico, sobre todo en menores de edad.<br>
    <b>Plazo medio (15% bajar / 20% subir):</b> un punto intermedio entre velocidad de resultados y facilidad
    para mantenerlo en el día a día.<br>
    <b>Plazo largo (20% bajar / 30% subir):</b> el cambio más lento, pero también el más seguro y sostenible,
    ideal para cuerpos que todavía están en crecimiento.
    </div>
    """, unsafe_allow_html=True)

    st.caption("El porcentaje define la velocidad e impacto del cambio: 0% mantiene el peso, valores mayores "
               "aceleran el proceso, siempre evitando descompensaciones, fatiga crónica o alteración del crecimiento.")
    caja_util(f"¡Vamos, {_nombre_saludo}! Aquí se traduce tu meta ('quiero bajar/subir/mantener peso') en un "
              "número exacto de calorías al día. Es el paso que conecta tu objetivo personal con la ciencia: "
              "sin este ajuste, no sabrías cuánto comer realmente para lograr lo que quieres. 🎯",
              emoji="🎯", color="#FCE4EC", borde="#D81B60")

# ---------------------------------------------------------------------------------------
with tabs[6]:
    hoja_header(6, "Se usan las calorías recomendadas según el objetivo nutricional (Hoja 5), no el RCD base.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Proteínas (20%)", f"{gr_prot:.1f} g", f"{cal_prot:.1f} kcal/día")
    col2.metric("Carbohidratos (50%)", f"{gr_carb:.1f} g", f"{cal_carb:.1f} kcal/día")
    col3.metric("Grasas (30%)", f"{gr_gras:.1f} g", f"{cal_gras:.1f} kcal/día")
    tabla_bonita(pd.DataFrame({
        "Resumen energético": ["Proteínas", "Carbohidratos", "Grasas", "Total"],
        "Valor (kcal)": [f"{cal_prot:.1f}", f"{cal_carb:.1f}", f"{cal_gras:.1f}", f"{cal_prot+cal_carb+cal_gras:.1f}"]
    }), 6)

    st.divider()
    col_recom, col_graf1, col_graf2 = st.columns([1, 1, 1])
    with col_recom:
        st.info("🎯 **Objetivo de esta distribución**\n\n"
                "**20% Proteínas:** para la reparación y crecimiento de tus músculos y tejidos.\n\n"
                "**50% Carbohidratos:** tu principal fuente de energía para el día a día.\n\n"
                "**30% Grasas:** esenciales para tus hormonas, cerebro y absorción de vitaminas.\n\n"
                "Esta proporción está pensada para un balance saludable y sostenible, no para dietas extremas.")
    with col_graf1:
        st.markdown("**🥧 Distribución de calorías**")
        fig_pie_macros = go.Figure(data=[go.Pie(
            labels=["Proteínas", "Carbohidratos", "Grasas"],
            values=[cal_prot, cal_carb, cal_gras],
            marker=dict(colors=["#E53935", "#FB8C00", "#43A047"]),
            textinfo="label+percent", hole=0.0,
        )])
        fig_pie_macros.update_layout(height=300, margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
        st.plotly_chart(fig_pie_macros, use_container_width=True)
    with col_graf2:
        st.markdown("**🍽️ Tu Plato Nutricional**")
        fig_plato = go.Figure(data=[go.Pie(
            labels=["Proteínas", "Carbohidratos", "Grasas"],
            values=[gr_prot, gr_carb, gr_gras],
            marker=dict(colors=["#8E24AA", "#FBC02D", "#00ACC1"]),
            textinfo="label+percent", hole=0.45,
        )])
        fig_plato.update_layout(
            height=300, margin=dict(t=10, l=10, r=10, b=10), showlegend=False,
            annotations=[dict(text="Tu Plato", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        st.plotly_chart(fig_plato, use_container_width=True)

    caja_util("No basta con contar calorías: también importa DE QUÉ están hechas. Esta hoja reparte tu meta "
              "calórica en proteínas (para músculos), carbohidratos (para energía) y grasas (para hormonas y "
              "órganos), en gramos concretos que puedes usar al armar tus platos. 🍗🍚🥑",
              emoji="🍽️", color="#FFFDE7", borde="#FBC02D")

# ---------------------------------------------------------------------------------------
with tabs[7]:
    hoja_header(7, "Se toma el RCD final (según objetivo) y se multiplica por el factor de cada comida.")
    tabla_bonita(pd.DataFrame({
        "Comida": list(porciones.keys()),
        "Factor": [f"{v['pct']*100:.0f}%" for v in porciones.values()],
        "Calorías asignadas": [f"{v['kcal']:.1f} kcal" for v in porciones.values()]
    }), 7)

    st.divider()
    st.markdown("#### ❓ Preguntas frecuentes sobre los momentos de comida")
    FAQ_PORCIONES = {
        "¿Por qué es importante el desayuno?": (
            "El desayuno rompe el ayuno de la noche y le da a tu cerebro la glucosa que necesita para "
            "concentrarte desde temprano. Saltarlo se asocia con menor rendimiento escolar y más antojos de "
            "azúcar durante el día. Por eso se le asigna un 25% de tus calorías diarias."
        ),
        "¿Por qué es importante la merienda?": (
            "Las meriendas (5% cada una) evitan que llegues con demasiada hambre al almuerzo o la cena, lo "
            "que ayuda a que no comas de más de una sola vez. También mantienen estables tus niveles de "
            "energía y glucosa entre comidas principales."
        ),
        "¿Por qué es importante el almuerzo?": (
            "El almuerzo es la comida más grande del día (40%) porque coincide con el momento de mayor "
            "actividad física y mental. Aporta la mayor parte de tu energía, proteínas y nutrientes para "
            "sostenerte durante la tarde."
        ),
        "¿Por qué es importante la cena?": (
            "La cena (25%) repone lo gastado durante el día sin sobrecargar tu digestión antes de dormir. "
            "Una cena balanceada favorece un mejor descanso, y un mejor descanso reduce la ansiedad por "
            "comer dulce al día siguiente."
        ),
    }
    pregunta_faq = st.selectbox("Elige una pregunta:", list(FAQ_PORCIONES.keys()))
    st.info(FAQ_PORCIONES[pregunta_faq])

    caja_util("Comer todas tus calorías de una sola vez sería imposible (¡y poco saludable!). Esta hoja te dice "
              "cuánto puedes comer en cada momento del día: desayuno, meriendas, almuerzo y cena, para que "
              "llegues a tu meta sin pasar hambre ni excederte. ⏰🍴",
              emoji="🍽️", color="#E0F7FA", borde="#00ACC1")

# ---------------------------------------------------------------------------------------
with tabs[8]:
    hoja_header(8)
    st.markdown("*\"Conocer la información nutricional de los alimentos permite llevar una alimentación más "
                "equilibrada y saludable. Una buena nutrición ayuda al crecimiento, desarrollo y bienestar del organismo.\"*")
    st.write("FatSecret es una plataforma de nutrición que permite buscar información sobre distintos alimentos "
             "y conocer sus calorías, proteínas, grasas y carbohidratos.")

    with st.expander("ℹ️ ¿Qué significa cada dato en FatSecret?"):
        st.markdown("- **Calorías:** total de energía que aporta el alimento, para ajustarlo a tus necesidades diarias.")
        st.markdown("- **Fibra alimentaria:** indica qué tan natural o integral es el alimento; ayuda a la digestión y la saciedad.")
        st.markdown("- **Sodio:** alerta sobre la sal oculta, sobre todo en procesados; protege la salud cardiovascular.")
        st.markdown("- **Azúcares:** separa los carbohidratos saludables de los azúcares simples o añadidos.")
        st.markdown("- **Porción (g/ml):** cantidad exacta de comida a la que corresponden las calorías y nutrientes mostrados.")

    st.markdown("#### 🔎 Buscador Nutricional Interactivo")
    alimento = st.text_input("Coloca el alimento aquí:", "")
    if alimento.strip():
        url = f"https://www.fatsecret.es/calor%C3%ADas-nutrici%C3%B3n/search?q={quote(alimento.strip())}"
        st.link_button(f"🔍 Ver '{alimento}' en FatSecret", url, use_container_width=True)
    else:
        st.link_button("🌐 Abrir FatSecret", "https://www.fatsecret.es/", use_container_width=True)
    caja_util("Cuando no sepas cuántas calorías tiene un alimento, no tienes que adivinar: escribe su nombre "
              "aquí y con un clic vas directo a su ficha nutricional completa en FatSecret. Así armas tu dieta "
              "con información real, no con suposiciones. 🔍🥗",
              emoji="🌐", color="#E0F2F1", borde="#00796B")

# ---------------------------------------------------------------------------------------
with tabs[9]:
    hoja_header(9, "Elige un alimento por macronutriente en cada comida. Misma estructura y fórmulas exactas del "
                   "Excel: la Porción Corregida usa el % de macro (Carb 50% / Proteína 20% / Grasa 30%) sobre el "
                   "total de calorías de cada momento, y los Gramos finales se calculan como "
                   "ROUND((Porción Corregida / kcal del alimento) × 100, 1) — asumiendo que el kcal del alimento "
                   "es su valor por cada 100 g.")

    seleccion = {}
    for comida in DIETA:
        caja_titulo(comida.upper(), 9)
        c1, c2, c3 = st.columns(3)
        with c1:
            carb_sel = st.selectbox(f"Carbohidrato — {comida}", list(DIETA[comida]["Carbohidrato"].keys()), key=f"c_{comida}")
        with c2:
            prot_sel = st.selectbox(f"Proteína — {comida}", list(DIETA[comida]["Proteína"].keys()), key=f"p_{comida}")
        with c3:
            gras_sel = st.selectbox(f"Grasa — {comida}", list(DIETA[comida]["Grasa"].keys()), key=f"g_{comida}")
        seleccion[comida] = {
            "Carbohidrato": carb_sel,
            "Proteína": prot_sel,
            "Grasa": gras_sel,
        }

    # % de cada macronutriente dentro del total de calorías de CADA momento (igual que N/S/X del Excel: 50/20/30%)
    PCT_MACRO_MOMENTO = {"Carbohidrato": 0.50, "Proteína": 0.20, "Grasa": 0.30}

    filas = []
    suma_kcal_carb = suma_kcal_prot = suma_kcal_gras = 0
    suma_porcion_carb = suma_porcion_prot = suma_porcion_gras = 0

    for comida, alimentos in seleccion.items():
        fila = {"Momento": comida}
        for macro, col_prefix in [("Carbohidrato", "Carb"), ("Proteína", "Prot"), ("Grasa", "Gras")]:
            alimento = alimentos[macro]
            kcal_alimento = DIETA[comida][macro][alimento]
            porcion_kcal = round(porciones[comida]["kcal"] * PCT_MACRO_MOMENTO[macro], 2)
            gramos = round((porcion_kcal / kcal_alimento) * 100, 1)
            fila[macro] = alimento
            fila[f"kcal ({col_prefix})"] = kcal_alimento
            fila[f"Porción corregida ({col_prefix})"] = porcion_kcal
            fila[f"Gramos ({col_prefix})"] = gramos
            fila[f"Unidad ({col_prefix})"] = "gramos"
        filas.append(fila)
        suma_kcal_carb += fila["kcal (Carb)"]; suma_porcion_carb += fila["Porción corregida (Carb)"]
        suma_kcal_prot += fila["kcal (Prot)"]; suma_porcion_prot += fila["Porción corregida (Prot)"]
        suma_kcal_gras += fila["kcal (Gras)"]; suma_porcion_gras += fila["Porción corregida (Gras)"]

    df_dieta = pd.DataFrame(filas)
    fila_total = {"Momento": "TOTAL",
                  "Carbohidrato": "", "kcal (Carb)": suma_kcal_carb, "Porción corregida (Carb)": round(suma_porcion_carb, 2), "Gramos (Carb)": "", "Unidad (Carb)": "",
                  "Proteína": "", "kcal (Prot)": suma_kcal_prot, "Porción corregida (Prot)": round(suma_porcion_prot, 2), "Gramos (Prot)": "", "Unidad (Prot)": "",
                  "Grasa": "", "kcal (Gras)": suma_kcal_gras, "Porción corregida (Gras)": round(suma_porcion_gras, 2), "Gramos (Gras)": "", "Unidad (Gras)": ""}
    df_dieta = pd.concat([df_dieta, pd.DataFrame([fila_total])], ignore_index=True)
    tabla_bonita(df_dieta, 9)

    total_general = round(suma_porcion_carb + suma_porcion_prot + suma_porcion_gras, 2)
    col1, col2 = st.columns(2)
    col1.metric("Total de calorías diarias (dieta armada)", f"{total_general:.2f} kcal",
                help="= SUMA(Porción corregida Carb; Porción corregida Prot; Porción corregida Gras), igual que R48 del Excel.")
    col2.metric("Comparación con calorías meta (Hoja 5)", f"{rcd_final:.1f} kcal")
    if abs(total_general - rcd_final) < 1:
        st.success("✅ La dieta armada coincide con la meta calórica del objetivo nutricional.")
    recursos_externos(9, [
        ("🌐 Buscar alimentos en FatSecret", "https://www.fatsecret.es/"),
    ])
    caja_util("Aquí armas tu menú real del día eligiendo alimentos que te gusten, y la app hace toda la "
              "matemática por ti: cada momento del día reparte sus calorías en 50% carbohidratos, 20% proteínas "
              "y 30% grasas, y luego convierte esas calorías a gramos según el alimento específico que elegiste "
              "— exactamente igual que en la hoja de cálculo original. ¡Comer sano también puede ser rico! 😋",
              emoji="🍱", color="#FBE9E7", borde="#FF7043")

# ---------------------------------------------------------------------------------------
with tabs[10]:
    hoja_header(10)

    col_clima, col_sticker_clima = st.columns([3, 1])

    with col_sticker_clima:
        if _STICKER_CORRIENDO.exists():
            mostrar_sticker(_STICKER_CORRIENDO, ancho=170)
        st.caption("¡El movimiento también forma parte de tu metabolismo! 🏃‍♀️")

    with col_clima:
        st.info("Según la FAO, vivir en climas cálidos y desérticos continuos como Chiclayo genera una adaptación "
                "biológica: el cuerpo reduce su tasa metabólica basal para evitar producir calor interno excesivo. "
                "Por ello, se aplica un factor de **0.95**, restando automáticamente un 5% al gasto calórico diario total.")
        st.latex(r"RCD_{Chiclayo} = RCD \times 0.95")
        st.caption("Este cálculo usa el RCD base de la Hoja 4 (antes del ajuste por objetivo), igual que en el Excel original.")
        st.metric("Gasto energético ajustado al clima de Chiclayo", f"{rcd_chiclayo:.1f} kcal/día")

    st.divider()
    recursos_externos(10, [
        ("☀️ Clima de Chiclayo (Senamhi)", "https://www.senamhi.gob.pe/"),
    ])
    caja_util("Vivir en un lugar caluroso como Chiclayo también afecta cuántas calorías gasta tu cuerpo. Este "
              "dato extra te da una versión más realista y localizada de tu gasto calórico, pensada "
              "específicamente para nuestra región. ☀️🌴",
              emoji="🌡️", color="#FFF8E1", borde="#F9A825")

# ---------------------------------------------------------------------------------------
with tabs[11]:
    hoja_header(11, "Calculadora independiente (igual que en el Excel), no conectada a los datos generales de la Hoja 0.")
    nombre_emb = st.text_input("Nombre:", "")
    c1, c2, c3 = st.columns(3)
    with c1:
        edad_emb = st.number_input("Edad:", min_value=10, max_value=60, value=27, step=1, key="edad_emb")
    with c2:
        peso_emb = st.number_input("Peso (kg):", min_value=30.0, max_value=PESO_MAX["Mujer"], value=68.0, step=0.1, key="peso_emb")
    with c3:
        altura_emb = st.number_input("Altura (cm):", min_value=100, max_value=ESTATURA_MAX["Mujer"], value=162, step=1, key="altura_emb")
    trimestre = st.selectbox("Selecciona tu trimestre:", ["Primer trimestre", "Segundo trimestre", "Tercer trimestre"])
    ajuste_trim = {"Primer trimestre": 0, "Segundo trimestre": 340, "Tercer trimestre": 452}[trimestre]

    st.markdown("- **Primer trimestre:** no necesitas calorías extra.")
    st.markdown("- **Segundo trimestre:** suma +340 calorías al día.")
    st.markdown("- **Tercer trimestre:** suma +452 calorías al día.")

    tmb_emb = (10 * peso_emb) + (6.25 * altura_emb) - (5 * edad_emb) - 161 + ajuste_trim
    st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) - 161 + Ajuste\ Trimestre")
    if nombre_emb.strip():
        st.metric(f"Total TMB para {nombre_emb}", f"{tmb_emb:.0f} kcal/día")
    else:
        st.metric("Total TMB", f"{tmb_emb:.0f} kcal/día")
    caja_util("Durante el embarazo el cuerpo necesita energía extra para que el bebé se desarrolle sanamente. "
              "Esta calculadora te dice cuántas calorías adicionales necesitas según el trimestre en que estás, "
              "sin tener que adivinarlo ni arriesgar tu nutrición ni la de tu bebé. 🤰💕",
              emoji="👶", color="#F8ECFB", borde="#BA68C8")

# ---------------------------------------------------------------------------------------
with tabs[12]:
    hoja_header(12, "La cafeína tarda entre 5 y 6 horas en reducirse a la mitad en el cuerpo. Calcular de 8 a 10 horas "
                    "antes de acostarse asegura que el estimulante baje lo suficiente para no bloquear los receptores "
                    "cerebrales del sueño, protegiendo el descanso profundo.")
    hora_dormir = st.time_input("Hora de dormir:", value=datetime.strptime("22:00", "%H:%M").time())
    dt_dormir = datetime.combine(datetime.today(), hora_dormir)
    dt_limite = dt_dormir - timedelta(hours=8)
    st.latex(r"Hora\ L\'imite = RESIDUO\left(Hora\_Dormir - \frac{8}{24}\,;\,1\right)")
    st.metric("Hora límite recomendada para tomar cafeína", dt_limite.time().strftime("%H:%M"))
    st.info("Un buen descanso es fundamental en la dieta, ya que regula las hormonas del hambre y reduce la "
            "ansiedad por comer dulce al día siguiente.")
    recursos_externos(12, [
        ("☕ Cafeína y sueño (Sleep Foundation)", "https://www.sleepfoundation.org/nutrition/caffeine-and-sleep"),
    ])
    caja_util("¿Sabías que dormir mal te da más hambre y más ganas de comer dulce al día siguiente? Esta "
              "herramienta te dice hasta qué hora puedes tomar café sin arruinar tu descanso — y un buen "
              "descanso es tan importante para tu salud como una buena alimentación. ☕😴",
              emoji="🌙", color="#EDE7F6", borde="#5E35B1")

# ---------------------------------------------------------------------------------------
with tabs[13]:
    hoja_header(13, "Proyección basada en el principio termodinámico de las 7,700 kcal por kilogramo de grasa "
                    "corporal: la misma constante que usan los nutricionistas para estimar cambios de peso.")

    st.latex(r"PesoProyectado = \frac{Deficit Diario \times 60}{7700}")
    st.caption("DeficitDiario = TDEE (Hoja 4, tu gasto de mantenimiento) − Calorías Consumidas (Hoja 5, tu meta calórica). "
               "60 = número de días (2 meses). 7700 = kcal equivalentes a 1 kg de grasa corporal.")

    def calcular_proyeccion(calorias_consumidas, tdee, dias=60):
        """Función proyectiva: aplica la fórmula del déficit/superávit calórico y retorna
        (deficit_diario, peso_proyectado_kg) para el número de días indicado."""
        deficit_diario = tdee - calorias_consumidas
        peso_proyectado = (deficit_diario * dias) / 7700
        return deficit_diario, peso_proyectado

    deficit_diario, peso_cambio_60 = calcular_proyeccion(rcd_final, rcd, dias=60)

    # --- Tarjeta de resultado destacado (estilo "hero", coherente con la identidad visual de la app) ---
    if objetivo == "Mantenerse" or abs(peso_cambio_60) < 0.05:
        grad = "linear-gradient(135deg,#2e7d32 0%,#56ab2f 60%,#8bc34a 100%)"
        mensaje_destacado = f"Como tu objetivo es mantenerte, {_nombre_saludo}, tu peso se mantendría estable durante los próximos 60 días. ¡Vas por buen camino! 💚"
    elif peso_cambio_60 > 0:
        grad = "linear-gradient(135deg,#1565C0 0%,#1E88E5 55%,#64B5F6 100%)"
        mensaje_destacado = f"Si mantienes este hábito por 60 días, {_nombre_saludo}, tu proyección estimada de pérdida es de <b>{peso_cambio_60:.1f} kg</b>."
    else:
        grad = "linear-gradient(135deg,#EF6C00 0%,#FB8C00 55%,#FFB74D 100%)"
        mensaje_destacado = f"⚠️ Cuidado, {_nombre_saludo}: si mantienes este hábito, podrías <b>aumentar aproximadamente {abs(peso_cambio_60):.1f} kg</b> en 2 meses."

    st.markdown(f"""
    <div style="background:{grad};border-radius:24px;padding:30px 34px;color:white;
                box-shadow:0 10px 26px rgba(0,0,0,0.18);margin:10px 0 22px 0;">
        <div style="font-size:0.85rem;letter-spacing:1px;opacity:0.85;text-transform:uppercase;font-weight:700;">
            Proyección a 60 días (2 meses)</div>
        <div style="font-size:2.2rem;font-weight:800;margin:6px 0 10px 0;">
            {peso - peso_cambio_60:.1f} kg <span style="font-size:1rem;font-weight:500;opacity:0.85;">peso estimado</span></div>
        <div style="font-size:1rem;line-height:1.5;">{mensaje_destacado}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Curva de progreso día a día, para visualizar la tendencia ---
    dias_eje = list(range(0, 61, 5))
    pesos_dia = [round(peso - (deficit_diario * d) / 7700, 1) for d in dias_eje]
    df_tiempo = pd.DataFrame({"Día": dias_eje, "Peso estimado (kg)": pesos_dia}).set_index("Día")
    st.line_chart(df_tiempo)

    col1, col2, col3 = st.columns(3)
    col1.metric("Peso actual", f"{peso:.1f} kg")
    col2.metric("Estimado en 30 días", f"{pesos_dia[len(pesos_dia)//2]} kg")
    col3.metric("Estimado en 60 días", f"{pesos_dia[-1]} kg")

    st.caption("⚠️ Esta proyección es un cálculo matemático de referencia (no un diagnóstico médico) y asume "
               "que mantienes el mismo ajuste calórico todos los días. El cuerpo humano no cambia de forma "
               "perfectamente lineal, y en menores de edad cualquier cambio de peso debe estar supervisado por "
               "un profesional de la salud.")

    caja_util(f"Esta línea de tiempo te muestra, con la misma matemática que usan los nutricionistas, cómo "
              f"avanzarías en 60 días si sigues tu plan calórico. Ver el progreso estimado ayuda a entender que "
              f"los resultados reales toman semanas o meses de constancia — ¡tú puedes lograrlo, {_nombre_saludo}! 🌱",
              emoji="📈", color="#E8EAF6", borde="#3949AB")

with tabs[14]:
    _, titulo13, emoji13, borde13, fondo13 = COLORES[14]
    st.markdown(f"""
    <div style="background:{fondo13};border-left:10px solid {borde13};border-radius:16px;
                padding:16px 26px;margin-bottom:16px;box-shadow:0 3px 10px rgba(0,0,0,0.10);">
    <h2 style="margin:0;color:{borde13};font-weight:800;">{emoji13} {titulo13}</h2>
    <p style="margin:4px 0 0 0;color:{borde13};font-size:0.95rem;font-weight:500;">
    Conoce a las personas detrás de esta calculadora — ahora que ya la usaste, ¡es hora de conocer al equipo! 🎉
    </p>
    </div>
    """, unsafe_allow_html=True)

    col_escudo, col_texto = st.columns([1, 3])
    with col_escudo:
        if _ESCUDO.exists():
            st.image(str(_ESCUDO), width=150)
    with col_texto:
        st.markdown("""
        <div style="background:#FBEAEC;border-left:7px solid #7A1F2B;border-radius:14px;
                    padding:16px 20px;">
        <b>📖 Sobre nosotras</b><br><br>
        Somos un grupo de estudiantes de 5to de secundaria de la I.E. Santa María Reina, apasionadas
        por la tecnología y la salud. Este proyecto nace con el objetivo de fomentar hábitos saludables
        mediante herramientas digitales accesibles, aplicando conocimientos de nutrición y programación
        para mejorar el bienestar de nuestra comunidad escolar.
        </div>
        """, unsafe_allow_html=True)

    caja_titulo("👩‍🎓 Integrantes", 13)
    EQUIPO = ["Diana Chavez", "Kathia Paz", "Sofia Suarez", "Ariana Farro"]
    cols_equipo = st.columns(len(EQUIPO))
    for c, nombre in zip(cols_equipo, EQUIPO):
        with c:
            st.markdown(f"""
            <div class="equipo-card" style="text-align:center;">
                <div class="nombre">👤 {nombre}</div>
            </div>
            """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    col_a.metric("Grado y sección", '5° "C" Secundaria')
    col_b.metric("Docente", "Arnadis J. Talavera Oropeza")

    caja_util("Este proyecto fue construido en equipo: cada integrante desarrolló y explicó una parte "
              "distinta de la hoja de cálculo, y luego se unieron todas las piezas en esta app para que "
              "cualquier persona —sin saber de Excel ni de nutrición— pueda usarla fácilmente. 🤝🌱",
              emoji="🎓", color="#FBEAEC", borde="#7A1F2B")

st.markdown("---")
st.caption("Aplicación desarrollada en Streamlit — réplica fiel del Excel 'Grupo n°4 VER.2' (Proyecto Sana "
           "Alimentación) para el proyecto de tesis escolar sobre salud pública en Lambayeque, Grupo N°04.")
