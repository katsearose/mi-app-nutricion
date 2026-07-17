import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import io
import plotly.graph_objects as go
from datetime import datetime, timedelta
from urllib.parse import quote
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

st.set_page_config(page_title="CIAM&SUNI: Tu Salud, Personalizada", layout="wide", page_icon="🍎")

# =========================================================================================
# PALETA DE COLORES — inspirada en los colores del sistema de iOS (systemBlue, systemGreen, etc.)
# Cada hoja conserva su propio acento, ahora dentro de la paleta de iOS, con fondos "tinted"
# muy suaves como los que usa iOS en tarjetas agrupadas (Ajustes, Salud, Recordatorios).
# =========================================================================================
# idx : (numero, titulo, emoji, color_borde, color_fondo)
COLORES = {
    0:  ("0", "¡Introduce tus datos!",                       "📝", "#007AFF", "#EAF3FF"),  # systemBlue
    1:  ("1", "Análisis Sanguíneo",                          "🩸", "#FF3B30", "#FFEDEC"),  # systemRed
    2:  ("2", "Índice de Masa Corporal y Percentil",         "⚖️", "#AF52DE", "#F6ECFC"),  # systemPurple
    3:  ("3", "Tasa Metabólica Basal (TMB)",                 "⚡", "#FF9500", "#FFF3E5"),  # systemOrange
    4:  ("4", "Requerimiento Calórico Diario (RCD)",         "🔥", "#34C759", "#EAFAEE"),  # systemGreen
    5:  ("5", "Subir, Mantener o Bajar el Peso",             "🎯", "#FF2D55", "#FFEBF0"),  # systemPink
    6:  ("6", "Cálculo de los Macronutrientes",               "🍽️", "#FFCC00", "#FFFAE0"),  # systemYellow
    7:  ("7", "Cálculo de las Porciones del Día",            "⏰", "#30B0C7", "#E6F7FA"),  # systemTeal
    8:  ("8", "Página FatSecret",                             "🌐", "#00C7BE", "#E1FBF9"),  # systemMint
    9:  ("9", "Plan de Dieta Semanal",                        "🍱", "#FF6B35", "#FFEEE6"),  # naranja cálido
    10: ("10", "Gasto Energético — Clima de Chiclayo",       "🌡️", "#FFB300", "#FFF6E0"),  # amarillo sol
    11: ("Aporte 1", "TMB en Embarazo",                       "👶", "#BF5AF2", "#F7ECFD"),  # púrpura claro
    12: ("Aporte 2", "Hora Límite de Cafeína",                "🌙", "#5856D6", "#ECEBFC"),  # systemIndigo
    13: ("13", "Línea de Tiempo: Tu Progreso Estimado",       "📈", "#5AC8FA", "#E9F8FF"),  # celeste claro
    14: ("14", "Mi Reporte de Resultados",                    "📄", "#32ADE6", "#E7F6FD"),  # systemCyan
    15: ("", "Sobre Nosotras",                                 "🎓", "#FF2D55", "#FFEBF0"),  # systemPink
}

# Colores base del sistema iOS, reutilizados para mantener coherencia visual en toda la app.
IOS_BLUE, IOS_GREEN, IOS_RED, IOS_ORANGE = "#007AFF", "#34C759", "#FF3B30", "#FF9500"
IOS_GRAY_BG, IOS_LABEL, IOS_SECONDARY = "#F2F2F7", "#1C1C1E", "#6C6C70"

# =========================================================================================
# ESTILOS GLOBALES
# =========================================================================================
st.markdown("""
<style>
/* =========================================================================================
   SISTEMA VISUAL ESTILO iOS — tipografía San Francisco, esquinas "continuas" muy redondeadas,
   tarjetas sobre fondo gris agrupado (#F2F2F7), acentos de los colores del sistema de iOS,
   y controles con la pulcritud de Ajustes / Salud / Recordatorios de Apple.
   ========================================================================================= */

:root {
    /* Paleta verde institucional (reemplaza la paleta azul de iOS por el Brand Green del proyecto) */
    --ios-blue: #1E5631; --ios-green: #34C759; --ios-red: #C0392B; --ios-orange: #E67E22;
    --ios-yellow: #FFCC00; --ios-purple: #AF52DE; --ios-pink: #FF2D55; --ios-teal: #30B0C7;
    --ios-indigo: #5856D6; --ios-gray: #8E8E93; --ios-gray-bg: #F7F9F7; --ios-card: #FFFFFF;
    --ios-label: #17301F; --ios-secondary: #5C6B60;
    --ios-radius-lg: 26px; --ios-radius-md: 20px; --ios-radius-sm: 14px;
    --brand-green: #1E5631; --accent-green: #4CAF50; --tint-green: #F4F9F4;
}

html, body, [class*="css"], .stApp {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                 "Helvetica Neue", "Inter", "Segoe UI", Roboto, sans-serif !important;
    color: var(--ios-label);
    letter-spacing: -0.01em;
}

.stApp {
    background: var(--ios-gray-bg);
}

h1, h2, h3, h4, h5 {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif !important;
    letter-spacing: -0.02em !important;
    font-weight: 800 !important;
}

.big-title {
    background: linear-gradient(135deg, var(--ios-blue) 0%, #5AC8FA 100%);
    padding: 22px 28px; border-radius: var(--ios-radius-md); color: white;
    box-shadow: 0 8px 24px rgba(0,122,255,0.22); margin-bottom: 6px;
}
.frase-motivadora {
    font-style: italic; color: var(--ios-secondary); font-size: 1.0rem;
    text-align: center; margin: 6px 0 18px 0; font-weight: 500;
}

/* ---------- métricas tipo "tarjeta de Salud" ---------- */
div[data-testid="stMetricValue"] { color: var(--ios-label); font-weight: 800; letter-spacing: -0.02em; }
div[data-testid="stMetricLabel"] { color: var(--ios-secondary); font-weight: 600; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.02em; }
div[data-testid="stMetric"] {
    background: var(--ios-card); border-radius: var(--ios-radius-sm); padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.05);
    border: 1px solid rgba(0,0,0,0.04);
}

/* ---------- pestañas (st.tabs) como segmented control de iOS ---------- */
div[data-baseweb="tab-list"] {
    background: #E9E9EE !important; border-radius: 12px !important; padding: 4px !important;
    gap: 2px !important;
}
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border-radius: 9px !important;
    color: var(--ios-secondary) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: var(--brand-green) !important; color: #FFFFFF !important;
    box-shadow: 0 2px 8px rgba(30,86,49,0.30) !important;
}
div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-baseweb="tab-border"] { display: none !important; }

/* ---------- radio horizontal (navegación por hojas) como segmented control grande, pill verde activa ---------- */
div[role="radiogroup"] {
    background: #EAEFEA; border-radius: 16px; padding: 6px; gap: 4px !important;
}
div[role="radiogroup"] label {
    background: transparent; border-radius: 12px !important; padding: 8px 14px !important;
    font-weight: 600 !important; font-size: 0.85rem !important; transition: all 0.15s ease;
}
div[role="radiogroup"] label:has(input:checked) {
    background: var(--brand-green) !important; box-shadow: 0 2px 8px rgba(30,86,49,0.30) !important;
}
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
div[role="radiogroup"] label:has(input:checked) span,
div[role="radiogroup"] label:has(input:checked) p {
    color: #FFFFFF !important;
}

/* ---------- sidebar tipo "Ajustes" de iOS ---------- */
section[data-testid="stSidebar"] {
    background: var(--tint-green);
    border-right: 1px solid rgba(30,86,49,0.08);
}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stNumberInput input,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: #FFFFFF !important; border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { font-weight: 800 !important; }

/* ---------- inputs generales redondeados como controles de iOS ---------- */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
.stTimeInput input, textarea {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    box-shadow: none !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--brand-green) !important;
    box-shadow: 0 0 0 3px rgba(30,86,49,0.15) !important;
}

/* ---------- botones estilo iOS (pill, sin sombras duras) ---------- */
.stButton button, .stDownloadButton button {
    border-radius: 999px !important;
    font-weight: 600 !important;
    border: none !important;
    background: var(--brand-green) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(30,86,49,0.28) !important;
    transition: transform 0.1s ease;
}
.stButton button:hover, .stDownloadButton button:hover { transform: scale(1.015); }

a[data-testid="stLinkButton"] button, div[data-testid="stLinkButton"] button {
    border-radius: 999px !important;
    font-weight: 600 !important;
    border: 1px solid rgba(30,86,49,0.22) !important;
    background: rgba(30,86,49,0.07) !important;
    color: var(--brand-green) !important;
    box-shadow: none !important;
}

/* ---------- alerts (info/success/warning) redondeados como banners de iOS ---------- */
div[data-testid="stAlert"] { border-radius: var(--ios-radius-sm) !important; border: none !important; }

/* ---------- expander como celda agrupada de iOS ---------- */
details {
    background: var(--ios-card) !important; border-radius: var(--ios-radius-sm) !important;
    border: 1px solid rgba(0,0,0,0.05) !important; overflow: hidden;
}

/* ---------- dataframes con esquinas redondeadas ---------- */
div[data-testid="stDataFrame"] { border-radius: var(--ios-radius-sm); overflow: hidden; }

/* ---------- todas las imágenes de la app (st.image) con esquinas redondeadas y sombra suave ---------- */
div[data-testid="stImage"] img {
    border-radius: var(--ios-radius-md) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 10px 26px rgba(0,0,0,0.10) !important;
    border: 1px solid rgba(0,0,0,0.04) !important;
}
div[data-testid="stImage"] { border-radius: var(--ios-radius-md); overflow: visible; }
div[data-testid="stImageCaption"] {
    text-align: center !important; color: var(--ios-secondary) !important;
    font-size: 0.82rem !important; font-weight: 500 !important; margin-top: 4px !important;
}

/* ---------- galería de imágenes propia (imagen_bonita) ---------- */
.img-bonita-wrap {
    background: var(--ios-card); border-radius: var(--ios-radius-lg); padding: 14px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05), 0 14px 34px rgba(0,0,0,0.12);
    border: 1px solid rgba(0,0,0,0.05); margin-top: 18px; margin-bottom: 6px;
}
.img-bonita-wrap img {
    width: 100%; display: block; border-radius: 18px;
    max-height: 620px; min-height: 320px; object-fit: cover;
}
.img-bonita-caption {
    text-align: center; color: var(--ios-secondary); font-size: 0.85rem;
    font-weight: 600; margin-top: 10px;
}

/* ---------- identidad visual tipo "landing page" con look iOS ---------- */
.navbar {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(255,255,255,0.85); backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--ios-radius-md); padding: 10px 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06); margin-bottom: 18px;
    border: 1px solid rgba(0,0,0,0.04);
}
.navbar-brand { display: flex; align-items: center; gap: 12px; }
.navbar-brand img { height: 78px; border-radius: 16px; }
.navbar-brand-text { line-height: 1.05; }
.navbar-brand-text .t1 { font-weight: 800; color: var(--brand-green); font-size: 1.15rem; letter-spacing: -0.02em; font-family: Georgia, "Times New Roman", serif; }
.navbar-brand-text .t2 { font-size: 0.82rem; color: var(--ios-secondary); font-weight: 500; }
.navbar-pill {
    background: rgba(30,86,49,0.09); color: var(--brand-green); font-weight: 700; font-size: 0.78rem;
    padding: 6px 14px; border-radius: 999px; border: 1px solid rgba(30,86,49,0.15);
    white-space: nowrap;
}

.hero-card {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #1E5631 0%, #2E7D32 55%, #6BBF59 100%);
    border-radius: var(--ios-radius-lg); padding: 44px 42px; color: white;
    box-shadow: 0 16px 40px rgba(30,86,49,0.30); margin-bottom: 22px;
}
.hero-card h1 { font-family: Georgia, "Times New Roman", serif !important; font-size: 2.15rem; font-weight: 800; margin: 0 0 10px 0; line-height: 1.15; letter-spacing: -0.01em; }
.hero-card p.hero-sub { font-size: 1.02rem; opacity: 0.95; max-width: 640px; margin: 0 0 16px 0; font-weight: 400; }
.hero-badges { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.hero-badge {
    background: rgba(255,255,255,0.2); backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,0.3); color: white;
    padding: 7px 16px; border-radius: 999px; font-size: 0.82rem; font-weight: 600;
}
.hero-emoji-decor {
    position: absolute; right: 26px; top: 50%; transform: translateY(-50%);
    font-size: 6.5rem; opacity: 0.16; line-height: 1;
}

.feature-row { display: flex; gap: 16px; margin-bottom: 6px; }
.feature-card {
    flex: 1; background: var(--ios-card); border-radius: var(--ios-radius-md); padding: 20px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.05);
    border: 1px solid rgba(0,0,0,0.04);
    text-align: left;
}
.feature-card .fc-emoji { font-size: 1.8rem; }
.feature-card .fc-title { font-weight: 800; color: var(--ios-label); margin: 6px 0 4px 0; font-size: 0.98rem; letter-spacing: -0.01em; }
.feature-card .fc-text { font-size: 0.83rem; color: var(--ios-secondary); line-height: 1.4; }

.equipo-card {
    background: var(--ios-card); border-radius: var(--ios-radius-sm); padding: 14px 18px; margin-bottom: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);
    border: 1px solid rgba(0,0,0,0.04); border-left: 4px solid var(--ios-pink);
}
.equipo-card .nombre { font-weight: 800; color: var(--ios-label); font-size: 0.98rem; }
.equipo-card .puntos { font-size: 0.85rem; color: var(--ios-secondary); margin-top: 2px; }
@media (max-width: 700px) {
    .feature-row { flex-direction: column; }
    .hero-emoji-decor { display: none; }
}

/* ---------- estilos de impresión: Hoja "MI REPORTE" ---------- */
@media print {
    section[data-testid="stSidebar"], header[data-testid="stHeader"], .navbar,
    div[role="radiogroup"], #MainMenu, footer, .stDeployButton,
    div[data-testid="stToolbar"], .no-print, iframe {
        display: none !important;
    }
    .print-only-report { box-shadow: none !important; border: 1px solid #ccc !important; }
    .stApp { background: #FFFFFF !important; }
}
</style>
""", unsafe_allow_html=True)


def caja_util(texto, emoji="💡", color="#FFF3CD", borde="#FFC107"):
    """Caja amigable: '¿Para qué te sirve esto?' — estilo tarjeta iOS con acento tintado a la izquierda."""
    st.markdown(f"""
    <div style="background-color:{color};padding:18px 22px;border-radius:20px;
                border-left:5px solid {borde};margin-top:14px;margin-bottom:6px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
    <b style="color:{borde};">{emoji} ¿Para qué te sirve esto?</b><br>
    <span style="color:#1C1C1E;">{texto}</span>
    </div>
    """, unsafe_allow_html=True)


def hoja_header(idx, subtitulo=None):
    """Encabezado tipo 'Hero Header Detallado': tarjeta blanca redondeada con sombra suave,
    ícono dentro de un círculo tintado a la izquierda, título en verde institucional y
    subtítulo explicativo — igual que la sección 'Encabezado de la Hoja Activa' de la maqueta."""
    numero, titulo, emoji, borde, fondo = COLORES[idx]
    sub_html = f"<p style='margin:6px 0 0 0;color:#5C6B60;font-size:0.92rem;font-weight:500;line-height:1.5;'>{subtitulo}</p>" if subtitulo else ""
    st.markdown(f"""
    <div style="background:#FFFFFF;border-radius:24px;padding:22px 28px;margin-bottom:16px;
                display:flex;align-items:flex-start;gap:18px;
                box-shadow:0 1px 2px rgba(30,86,49,0.04), 0 10px 26px rgba(30,86,49,0.08);
                border:1px solid rgba(30,86,49,0.06);">
        <div style="min-width:56px;height:56px;border-radius:50%;background:{fondo};
                    display:flex;align-items:center;justify-content:center;font-size:1.6rem;flex-shrink:0;">
            {emoji}
        </div>
        <div>
            <h2 style="margin:0;color:{borde};font-weight:800;letter-spacing:-0.02em;">Hoja {numero}: {titulo}</h2>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def tabla_bonita(df, idx):
    """Tabla con el color propio de la hoja: encabezado de color sólido y filas alternadas con el tono claro."""
    _, _, _, borde, fondo = COLORES[idx]
    styler = (
        df.style
        .set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", fondo), ("color", borde),
                ("font-weight", "800"), ("text-align", "center"),
                ("padding", "12px"), ("font-size", "0.85rem"),
                ("font-family", "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif"),
                ("letter-spacing", "0.01em"), ("text-transform", "uppercase"),
                ("border-bottom", f"2px solid {borde}33"),
            ]},
            {"selector": "tbody td", "props": [
                ("text-align", "center"), ("padding", "11px"), ("font-size", "0.9rem"),
                ("font-family", "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif"),
                ("color", "#17301F"),
            ]},
            {"selector": "tbody tr:nth-child(even)", "props": [("background-color", "#F7F9F7")]},
            {"selector": "tbody tr:nth-child(odd)", "props": [("background-color", "#FFFFFF")]},
        ])
    )
    st.dataframe(styler, use_container_width=True, hide_index=True)


def caja_titulo(texto, idx):
    """Sub-título en negrita con el color de la hoja, para separar secciones dentro de una misma hoja."""
    _, _, _, borde, _ = COLORES[idx]
    st.markdown(f"<p style='color:{borde};font-weight:800;font-size:1.05rem;margin-top:14px;'>{texto}</p>",
                unsafe_allow_html=True)


def _img_to_b64(ruta):
    """Convierte una imagen (ruta en disco) a base64. Devuelve None si no existe o falla."""
    try:
        return base64.b64encode(Path(ruta).read_bytes()).decode()
    except Exception:
        return None


def imagen_bonita(ruta, caption=None, ancho=None):
    """Muestra UNA imagen dentro de una tarjeta blanca con esquinas redondeadas y sombra
    suave, igual al resto de tarjetas de la app. Úsala en cualquier hoja para mostrar fotos,
    capturas o ilustraciones relacionadas con esa sección. Si el archivo no existe, no rompe
    la app (simplemente no muestra nada).
    `ruta` puede ser una ruta en disco (str/Path) o un objeto tipo bytes/BytesIO ya cargado."""
    b64 = None
    if isinstance(ruta, (str, Path)):
        if not Path(ruta).exists():
            return
        b64 = _img_to_b64(ruta)
        ext = Path(ruta).suffix.lstrip(".").lower() or "png"
    else:
        try:
            data = ruta.getvalue() if hasattr(ruta, "getvalue") else ruta.read()
            b64 = base64.b64encode(data).decode()
            ext = "png"
        except Exception:
            return
    if not b64:
        return
    ancho_css = f"max-width:{ancho}px;margin:0 auto;" if ancho else ""
    cap_html = f"<div class='img-bonita-caption'>{caption}</div>" if caption else ""
    st.markdown(f"""
    <div class="img-bonita-wrap" style="{ancho_css}">
        <img src="data:image/{ext};base64,{b64}" />
        {cap_html}
    </div>
    """, unsafe_allow_html=True)


def galeria_bonita(rutas_con_captions, columnas=3):
    """Muestra varias imágenes en una grilla de tarjetas redondeadas con sombra, en `columnas`
    columnas. `rutas_con_captions` es una lista de tuplas (ruta, caption) o solo rutas."""
    items = [(r, c) if isinstance(r, tuple) else (r, None) for r, c in
             [(x if isinstance(x, tuple) else (x, None)) for x in rutas_con_captions]]
    cols = st.columns(columnas)
    for i, (ruta, cap) in enumerate(items):
        with cols[i % columnas]:
            imagen_bonita(ruta, caption=cap)


def _rl_hex(hexcolor):
    """Convierte un color '#RRGGBB' a un color de reportlab."""
    return rl_colors.HexColor(hexcolor)


def generar_pdf_reporte(datos):
    """Genera el Informe de Resultados en un PDF real con estilo de informe médico/clínico
    (encabezado tipo consultorio, tablas de valores, semáforo de resultados en colores,
    plan de comidas y recomendaciones) — listo para imprimir o entregar al usuario.
    `datos` es un diccionario con toda la información necesaria (ver llamada en Hoja 14)."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title="Informe de Resultados - CIAM&SUNI",
    )

    VERDE = "#1E5631"
    GRIS_TXT = "#3C3C43"
    GRIS_SUAVE = "#6C6C70"
    LINEA = "#E3E8E3"

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("TituloInforme", parent=styles["Title"], fontName="Helvetica-Bold",
                                    fontSize=17, textColor=_rl_hex(VERDE), spaceAfter=2, alignment=TA_LEFT)
    estilo_subtitulo = ParagraphStyle("SubtituloInforme", parent=styles["Normal"], fontName="Helvetica",
                                       fontSize=9, textColor=_rl_hex(GRIS_SUAVE), alignment=TA_LEFT)
    estilo_fecha = ParagraphStyle("FechaInforme", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=9, textColor=_rl_hex(GRIS_SUAVE), alignment=TA_RIGHT)
    estilo_seccion = ParagraphStyle("Seccion", parent=styles["Heading2"], fontName="Helvetica-Bold",
                                     fontSize=12.5, textColor=_rl_hex(VERDE), spaceBefore=14, spaceAfter=6)
    estilo_texto = ParagraphStyle("Texto", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=9.5, textColor=_rl_hex(GRIS_TXT), leading=13.5)
    estilo_texto_bold = ParagraphStyle("TextoBold", parent=estilo_texto, fontName="Helvetica-Bold")
    estilo_aviso = ParagraphStyle("Aviso", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=8.5, textColor=_rl_hex("#8A5A00"), leading=12)
    estilo_recomendacion = ParagraphStyle("Recom", parent=estilo_texto, leftIndent=8, spaceAfter=4)

    story = []

    # ---------------- ENCABEZADO TIPO CONSULTORIO ----------------
    header_tbl = Table([
        [Paragraph("📄 Informe de Resultados — CIAM&amp;SUNI", estilo_titulo),
         Paragraph(f"Generado: {datos['fecha']}", estilo_fecha)],
        [Paragraph('C.E.P. "Santa María Reina", Chiclayo — Programa de Salud Escolar', estilo_subtitulo), ""],
    ], colWidths=[130 * mm, 44 * mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (0, 1), (1, 1)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.3, color=_rl_hex(VERDE)))
    story.append(Spacer(1, 10))

    # ---------------- DATOS DEL PACIENTE ----------------
    datos_paciente = Table([[
        Paragraph(f"<b>Paciente:</b> {datos['nombre']}", estilo_texto),
        Paragraph(f"<b>Edad:</b> {datos['edad']} años ({datos['etapa']})", estilo_texto),
        Paragraph(f"<b>Género:</b> {datos['genero']}", estilo_texto),
    ]], colWidths=[58 * mm, 58 * mm, 58 * mm])
    datos_paciente.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _rl_hex("#F4F9F4")),
        ("BOX", (0, 0), (-1, -1), 0.6, _rl_hex(LINEA)),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(datos_paciente)
    story.append(Spacer(1, 4))

    def _tabla_datos(filas, col_widths=(75 * mm, 99 * mm)):
        t = Table(filas, colWidths=list(col_widths))
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (-1, -1), _rl_hex(GRIS_TXT)),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ]))
        return t

    # ---------------- 1. DATOS ANTROPOMÉTRICOS ----------------
    story.append(Paragraph("📏 Datos antropométricos", estilo_seccion))
    story.append(_tabla_datos([
        ["Peso", f"{datos['peso']} kg"],
        ["Estatura", f"{datos['estatura']} cm"],
        ["IMC", f"{datos['imc']}  —  {datos['categoria_imc']}" + (f"  (Percentil {datos['percentil']})" if datos.get("percentil") else "")],
    ]))

    # ---------------- 2. REQUERIMIENTO ENERGÉTICO ----------------
    story.append(Paragraph("🔥 Requerimiento energético", estilo_seccion))
    story.append(_tabla_datos([
        ["TMB (Tasa Metabólica Basal)", f"{datos['tmb']:.0f} kcal/día"],
        ["RCD (Gasto calórico diario)", f"{datos['rcd']:.0f} kcal/día"],
        ["Meta calórica (según objetivo)", f"{datos['rcd_final']:.0f} kcal/día"],
        ["Objetivo nutricional", f"{datos['objetivo']}"],
    ]))

    # ---------------- 3. MACRONUTRIENTES ----------------
    story.append(Paragraph("🍽️ Macronutrientes recomendados (diarios)", estilo_seccion))
    tabla_macros = Table([
        ["Macronutriente", "Gramos", "Kcal/día", "% del total"],
        ["Proteínas", f"{datos['gr_prot']:.1f} g", f"{datos['cal_prot']:.0f}", "20%"],
        ["Carbohidratos", f"{datos['gr_carb']:.1f} g", f"{datos['cal_carb']:.0f}", "50%"],
        ["Grasas", f"{datos['gr_gras']:.1f} g", f"{datos['cal_gras']:.0f}", "30%"],
    ], colWidths=(58 * mm, 39 * mm, 39 * mm, 38 * mm))
    tabla_macros.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _rl_hex(VERDE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.3),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, _rl_hex("#F7F9F7")]),
        ("GRID", (0, 0), (-1, -1), 0.4, _rl_hex(LINEA)),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_macros)

    # ---------------- 4. ANÁLISIS SANGUÍNEO (semáforo clínico) ----------------
    story.append(Paragraph("🩸 Análisis sanguíneo — semáforo clínico", estilo_seccion))
    if datos["tiene_examen"]:
        filas_examen = [["Parámetro", "Valor", "Resultado", "Estado"]]
        estilos_extra = []
        for i, (parametro, valor_txt, categoria) in enumerate(datos["examen"], start=1):
            color_sem = CATEGORIA_SEMAFORO.get(categoria, "gris")
            estilo_sem = SEMAFORO_ESTILO[color_sem]
            filas_examen.append([parametro, valor_txt, categoria, estilo_sem["etiqueta"]])
            estilos_extra.append(("BACKGROUND", (3, i), (3, i), _rl_hex(estilo_sem["fondo"])))
            estilos_extra.append(("TEXTCOLOR", (3, i), (3, i), _rl_hex(estilo_sem["hex"])))
            estilos_extra.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
        tabla_examen = Table(filas_examen, colWidths=(46 * mm, 34 * mm, 40 * mm, 34 * mm))
        base_style = [
            ("BACKGROUND", (0, 0), (-1, 0), _rl_hex(VERDE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (2, -1), [rl_colors.white, _rl_hex("#F7F9F7")]),
            ("GRID", (0, 0), (-1, -1), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ] + estilos_extra
        tabla_examen.setStyle(TableStyle(base_style))
        story.append(tabla_examen)
    else:
        story.append(Paragraph("No se ingresaron valores de análisis sanguíneo en esta sesión.", estilo_texto))

    # ---------------- 5. PLAN DE COMIDAS ----------------
    story.append(Paragraph("🍱 Plan de comidas del día", estilo_seccion))
    if datos["tiene_dieta"]:
        filas_dieta = [["Comida", "Carbohidrato", "Proteína", "Grasa"]]
        for comida, alimentos in datos["dieta"].items():
            filas_dieta.append([comida, alimentos["Carbohidrato"], alimentos["Proteína"], alimentos["Grasa"]])
        tabla_dieta = Table(filas_dieta, colWidths=(30 * mm, 48 * mm, 48 * mm, 28 * mm))
        tabla_dieta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _rl_hex(VERDE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, _rl_hex("#F7F9F7")]),
            ("GRID", (0, 0), (-1, -1), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 5.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ]))
        story.append(tabla_dieta)
    else:
        story.append(Paragraph("Aún no se armó un plan de comidas en la Hoja 9.-DIETA durante esta sesión.", estilo_texto))

    # ---------------- 6. PROYECCIÓN A 60 DÍAS ----------------
    story.append(Paragraph("📈 Proyección estimada (60 días)", estilo_seccion))
    story.append(_tabla_datos([
        ["Peso actual", f"{datos['peso']} kg"],
        ["Peso estimado en 60 días", f"{datos['peso_proyectado']:.1f} kg"],
    ]))

    # ---------------- 7. RESUMEN CLÍNICO Y RECOMENDACIONES ----------------
    story.append(Paragraph("🩺 Resumen clínico y recomendaciones", estilo_seccion))
    for r in datos["recomendaciones"]:
        story.append(Paragraph(f"•  {r}", estilo_recomendacion))

    # ---------------- AVISO MÉDICO ----------------
    story.append(Spacer(1, 8))
    aviso_tbl = Table([[Paragraph(
        "<b>Recordar:</b> hable sobre su categoría de IMC y sus resultados con su proveedor de atención "
        "médica, ya que estos valores pueden estar relacionados con su salud y bienestar general. Este "
        "informe es una herramienta de detección orientativa y educativa; no reemplaza una evaluación "
        "médica o nutricional profesional y no pretende diagnosticar enfermedades ni dolencias.",
        estilo_aviso)]], colWidths=[178 * mm])
    aviso_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _rl_hex("#FFF3E5")),
        ("BOX", (0, 0), (-1, -1), 0.6, _rl_hex("#FFD59E")),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(aviso_tbl)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.6, color=_rl_hex(LINEA)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Informe generado por CIAM&amp;SUNI — Proyecto de Salud Escolar, Grupo N°04, 5° \"C\" Secundaria, "
        "C.E.P. Santa María Reina, Chiclayo. Ningún dato se almacena en servidores externos.",
        estilo_subtitulo))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


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
    "verde": {"hex": "#1E5631", "fondo": "#EAFAEE", "emoji": "🟢", "etiqueta": "Normal"},   # verde institucional
    "ambar": {"hex": "#E67E22", "fondo": "#FDF1E4", "emoji": "🟡", "etiqueta": "Alerta"},   # naranja del brief
    "rojo":  {"hex": "#C0392B", "fondo": "#FBEAE8", "emoji": "🔴", "etiqueta": "Crítico"},  # rojo del brief
    "gris":  {"hex": "#8E8E93", "fondo": "#F2F2F7", "emoji": "⚪", "etiqueta": "Sin dato"},  # gris neutro
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
    <div style="background:#ffffff;border-radius:24px;padding:18px 14px;text-align:center;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.07);
                border-top:4px solid {r['hex']};height:100%;">
        <div style="width:60px;height:60px;border-radius:50%;background:{r['fondo']};
                    display:flex;align-items:center;justify-content:center;
                    margin:0 auto 10px auto;font-size:1.5rem;">{r['emoji']}</div>
        <div style="font-weight:800;color:#1C1C1E;font-size:0.93rem;letter-spacing:-0.01em;">{parametro}</div>
        <div style="color:#8E8E93;font-size:0.78rem;margin-bottom:4px;">{valor_texto}</div>
        <div style="font-weight:700;color:{r['hex']};font-size:0.85rem;margin-bottom:8px;">{categoria}</div>
        <div style="font-size:0.74rem;color:#6C6C70;line-height:1.35;">{r['mensajePersonalizado']}</div>
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


def color_categoria_imc(categoria):
    """Asigna un color tipo semáforo a cada categoría de IMC: verde = saludable,
    ámbar = atención, rojo = riesgo alto. Se usa para pintar la categoría en pantalla."""
    if categoria == "Peso Saludable":
        color = "verde"
    elif categoria in ["Bajo Peso", "Sobrepeso"]:
        color = "ambar"
    elif categoria in ["Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"]:
        color = "rojo"
    else:
        color = "gris"
    return SEMAFORO_ESTILO[color]


def tarjeta_categoria_imc(titulo, categoria):
    """Tarjeta compacta que muestra la categoría de IMC con su color de semáforo correspondiente."""
    estilo = color_categoria_imc(categoria)
    st.markdown(f"""
    <div style="background:{estilo['fondo']};border-radius:22px;padding:16px 16px;text-align:center;
                border:1.5px solid {estilo['hex']}33;height:100%;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
        <div style="font-size:0.78rem;color:#6C6C70;font-weight:600;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.02em;">{titulo}</div>
        <div style="font-weight:800;font-size:1.25rem;color:{estilo['hex']};letter-spacing:-0.01em;">{estilo['emoji']} {categoria}</div>
    </div>
    """, unsafe_allow_html=True)


def grafico_percentil_bandas(genero_tabla, edad_usuario=None, imc_usuario=None, genero_usuario=None):
    """Recrea el gráfico de percentiles con bandas de color entre cada curva (P5, P50, P85, P95),
    con el IMC en el eje Y, etiquetas de dato en cada punto, y una estrella marcando la posición
    del usuario si corresponde."""
    tabla = PERCENTIL_HOMBRE if genero_tabla == "Hombre" else PERCENTIL_MUJER
    edades = sorted(tabla.keys())
    p5 = [tabla[e][0] for e in edades]
    p50 = [tabla[e][1] for e in edades]
    p85 = [tabla[e][2] for e in edades]
    p95 = [tabla[e][3] for e in edades]
    y_max = 35
    y_min = 0

    fig = go.Figure()

    # ---- Bandas de color (de abajo hacia arriba) ----
    fig.add_trace(go.Scatter(x=edades, y=[y_min] * len(edades), line=dict(width=0),
                              showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=edades, y=p5, fill="tonexty", fillcolor="rgba(206,147,216,0.30)",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=edades, y=p50, fill="tonexty", fillcolor="rgba(100,181,246,0.30)",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=edades, y=p85, fill="tonexty", fillcolor="rgba(129,199,132,0.30)",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=edades, y=p95, fill="tonexty", fillcolor="rgba(255,213,79,0.30)",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=edades, y=[y_max] * len(edades), fill="tonexty", fillcolor="rgba(239,83,80,0.25)",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))

    # ---- Líneas con etiquetas de dato en cada punto ----
    fig.add_trace(go.Scatter(x=edades, y=p5, mode="lines+markers+text", name="Percentil 5",
                              line=dict(color="#1E88E5", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p5], textposition="bottom center",
                              textfont=dict(color="#1E88E5", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p50, mode="lines+markers+text", name="Percentil 50",
                              line=dict(color="#43A047", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p50], textposition="top center",
                              textfont=dict(color="#2E7D32", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p85, mode="lines+markers+text", name="Percentil 85",
                              line=dict(color="#FBC02D", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p85], textposition="top center",
                              textfont=dict(color="#F9A825", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p95, mode="lines+markers+text", name="Percentil 95",
                              line=dict(color="#E53935", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p95], textposition="top center",
                              textfont=dict(color="#E53935", size=9)))

    if genero_usuario == genero_tabla and edad_usuario in tabla and imc_usuario is not None:
        fig.add_trace(go.Scatter(x=[edad_usuario], y=[imc_usuario], mode="markers+text",
                                  name="Tú estás aquí", text=["Tú"], textposition="bottom center",
                                  marker=dict(color="#1565C0", size=16, symbol="star",
                                              line=dict(color="white", width=1))))

    titulo_txt = "Percentil Niñas" if genero_tabla == "Mujer" else "Percentil Niños"
    titulo_color = "#E53935" if genero_tabla == "Mujer" else "#00838F"

    fig.update_layout(
        title=dict(text=titulo_txt, font=dict(color=titulo_color, size=24, family="Arial Black"), x=0.5, xanchor="center"),
        xaxis_title="Edad (años)", yaxis_title="IMC",
        yaxis=dict(range=[y_min, y_max]),
        xaxis=dict(dtick=1),
        height=430, margin=dict(t=60, l=10, r=10, b=10),
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

# --- Carpeta para las imágenes propias de cada hoja (que enviarás más adelante) ---
# Coloca en /assets/hojas/ un archivo con el nombre indicado para que aparezca automáticamente
# en la hoja correspondiente, dentro de una tarjeta con bordes redondeados y sombra.
IMG_HOJAS_DIR = ASSETS_DIR / "hojas"
IMAGENES_POR_HOJA = {
    0:  IMG_HOJAS_DIR / "hoja0_datos.png",
    1:  IMG_HOJAS_DIR / "hoja1_sangre.png",
    2:  IMG_HOJAS_DIR / "hoja2_imc.png",
    3:  IMG_HOJAS_DIR / "hoja3_tmb.png",
    4:  IMG_HOJAS_DIR / "hoja4_rcd.png",
    5:  IMG_HOJAS_DIR / "hoja5_objetivo.png",
    6:  IMG_HOJAS_DIR / "hoja6_macros.png",
    7:  IMG_HOJAS_DIR / "hoja7_porciones.png",
    8:  IMG_HOJAS_DIR / "hoja8_fatsecret.png",
    9:  IMG_HOJAS_DIR / "hoja9_dieta.png",
    10: IMG_HOJAS_DIR / "hoja10_clima.png",
    11: IMG_HOJAS_DIR / "hoja11_embarazo.png",
    12: IMG_HOJAS_DIR / "hoja12_cafeina.png",
    13: IMG_HOJAS_DIR / "hoja13_tiempo.png",
    14: IMG_HOJAS_DIR / "hoja14_reporte.png",
}


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

# --- Aviso médico: esta app es educativa y no reemplaza la consulta profesional ---
st.markdown("""
<div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:20px;
            padding:16px 24px;margin-bottom:18px;
            box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
<b style="color:#FF9500;">⚕️ Aviso importante:</b> esta aplicación es una herramienta educativa y orientativa.
No reemplaza la consulta con un médico, nutricionista u otro profesional de la salud.
Ante cualquier duda o resultado fuera de lo normal, acude siempre a un especialista.
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
    "Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx",
    "Grupo_n_4_VER_2.xlsx", "Grupo_n_4_VER_2__1_.xlsx", "Grupo n°4 VER.2.xlsx", "Grupo_n_4_VER.2.xlsx",
]
_ruta_excel = None
for _nombre in _POSIBLES_NOMBRES_EXCEL:
    _candidata = Path(__file__).parent / _nombre
    if _candidata.exists():
        _ruta_excel = _candidata
        break

st.markdown("---")

# =========================================================================================
# SIDEBAR — HOJA 0.-DATOS
# =========================================================================================
if _ESCUDO.exists():
    st.sidebar.image(str(_ESCUDO), width=130)

st.sidebar.header("📝 ¡Introduce tus datos!")
st.sidebar.caption("🔒 Tus datos son privados: solo se usan mientras tienes esta página abierta y no se guardan en ningún servidor.")

genero = st.sidebar.radio("Género:", ["Hombre", "Mujer"], index=0, horizontal=True,
                           format_func=lambda g: ("♂ Hombre" if g == "Hombre" else "♀ Mujer"))

nombre_usuario = st.sidebar.text_input("¿Cómo te llamas?", "")
_nombre_saludo = nombre_display(nombre_usuario, genero)
if nombre_usuario.strip():
    st.sidebar.success(f"¡Paz y bien, {_nombre_saludo}! 🌟 Vamos a armar tu plan personalizado.")
else:
    st.sidebar.caption("✍️ Escribe tu nombre para que tu plan se sienta hecho a tu medida.")

peso_max_actual = PESO_MAX[genero]
peso = st.sidebar.number_input(
    "Peso (en kg):", min_value=1.0, max_value=peso_max_actual, value=min(75.0, peso_max_actual), step=0.1,
    help=f"Tope máximo: {peso_max_actual:.0f} kg (récord mundial documentado)."
)

estatura_max_actual = ESTATURA_MAX[genero]
estatura = st.sidebar.number_input(
    "Estatura (en cm):", min_value=30, max_value=estatura_max_actual, value=min(168, estatura_max_actual), step=1,
    help=f"Tope máximo: {estatura_max_actual} cm (récord mundial documentado)."
)

edad_max_actual = EDAD_MAX[genero]
edad = st.sidebar.number_input(
    "Edad (en años):", min_value=1, max_value=edad_max_actual, value=9, step=1,
    help=f"Tope máximo: {edad_max_actual} años (récord mundial documentado)."
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
with st.sidebar.expander("ℹ️ ¿Cómo saber mi actividad física?"):
    st.caption("**Sedentaria:** poco o nada de ejercicio.\n\n"
               "**Ligero:** ejercicio 1-3 veces/semana.\n\n"
               "**Moderada:** ejercicio 3-5 veces/semana.\n\n"
               "**Intensa:** ejercicio diario o deportista.")

if objetivo != "Mantenerse":
    with st.sidebar.expander("ℹ️ ¿Qué significa el ajuste calórico?"):
        st.caption("Es cuánto le sumas o restas a tu gasto diario (RCD) para lograr tu meta. "
                   "A mayor porcentaje, cambios más rápidos pero más exigentes.\n\n"
                   "**10%:** corto plazo.\n\n**15%/20%:** plazo medio.\n\n**20%/30%:** plazo largo, "
                   "más lento y seguro — recomendado para cuerpos en crecimiento.")

st.sidebar.markdown("---")
st.sidebar.subheader("Análisis Sanguíneo")
hemo = st.sidebar.number_input("Hemoglobina (g/dL):", min_value=0.0, max_value=HEMO_MAX, value=0.0, step=0.1)
trigli = st.sidebar.number_input("Triglicéridos (mg/dL):", min_value=0.0, max_value=TRIGLI_MAX, value=0.0, step=1.0)
gluco = st.sidebar.number_input("Glucosa (mg/dL):", min_value=0.0, max_value=GLUCO_MAX, value=0.0, step=1.0)
coles = st.sidebar.number_input("Colesterol (mg/dL):", min_value=0.0, max_value=COLES_MAX, value=0.0, step=1.0)
hierro = st.sidebar.number_input("Hierro (µg/dL):", min_value=0.0, max_value=HIERRO_MAX, value=0.0, step=1.0)

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

# Categoría IMC del usuario (para reutilizar en Hoja 2 y en el Reporte)
if etapa in ["Niñez", "Adolescencia"]:
    _percentil_usuario, _categoria_imc_usuario = clasif_percentil(imc, edad, genero)
else:
    _percentil_usuario, _categoria_imc_usuario = None, clasif_imc_adulto(imc)

# =========================================================================================
# NAVEGACIÓN
# =========================================================================================
st.subheader("📋 Navegación por Hojas del Sistema (idéntica al Excel)")

OPCIONES_HOJAS = [
    "0.-DATOS", "1.-ANÁLISIS SANGUÍNEO", "2.-IMC Y PERCENTIL", "3.-TMB", "4.-RCD",
    "5.-OBJETIVO", "6.-MACRONUTRIENTES", "7.-PORCIONES", "8.-FATSECRET",
    "9.-DIETA", "10.-CLIMA CHICLAYO", "11.-APORTE 1: EMBARAZO", "12.-APORTE 2: CAFEÍNA",
    "13.-LÍNEA DE TIEMPO", "📄 MI REPORTE", "🎓 SOBRE NOSOTRAS"
]

if "hoja_activa" not in st.session_state:
    st.session_state["hoja_activa"] = OPCIONES_HOJAS[0]

hoja_activa = st.radio(
    "Navega por hoja:",
    OPCIONES_HOJAS,
    horizontal=True,
    label_visibility="collapsed",
    key="hoja_activa",
)
st.markdown("---")

# ---------------------------------------------------------------------------------------
if hoja_activa == "0.-DATOS":
    hoja_header(0, "El punto de partida: aquí registras todo lo que la app necesita saber de ti.")

    # --- Bloque destacado: por qué descargar el Excel original ---
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1E5631 0%,#2E7D32 60%,#4CAF50 100%);border-radius:26px;
                padding:28px 30px;color:white;margin-bottom:18px;
                box-shadow:0 14px 34px rgba(30,86,49,0.28);">
        <div style="font-size:0.8rem;letter-spacing:0.03em;text-transform:uppercase;font-weight:700;opacity:0.9;">
            📂 Antes de empezar</div>
        <div style="font-size:1.5rem;font-weight:800;margin:6px 0 10px 0;letter-spacing:-0.01em;">
            ¿Por qué deberías descargar el Excel original?</div>
        <div style="font-size:0.98rem;line-height:1.55;opacity:0.97;max-width:760px;">
            Esta app es una réplica bonita y fácil de usar, pero el Excel es la herramienta completa: es tuya,
            para siempre, y puedes llevarla contigo a donde quieras.
        </div>
    </div>
    """, unsafe_allow_html=True)

    ra1, ra2, ra3, ra4 = st.columns(4)
    _razones_excel = [
        ("🎨", "Personalízalo a tu gusto", "Cambia colores, agrega tus propias comidas o ajusta las "
         "fórmulas exactamente como tú quieras — es 100% tuyo para editar."),
        ("📴", "Úsalo sin internet", "No necesitas conexión ni esta página abierta: el Excel funciona "
         "perfecto en tu computadora aunque no tengas WiFi ni datos."),
        ("🧮", "Fórmulas a la mano", "Todas las fórmulas están visibles y editables en cada celda, así "
         "puedes revisarlas, aprenderlas o adaptarlas a otro caso."),
        ("📋", "Con las indicaciones incluidas", "Cada hoja trae sus propias notas e instrucciones, para "
         "que sepas exactamente cómo usarla paso a paso."),
    ]
    for col, (emoji_r, titulo_r, texto_r) in zip([ra1, ra2, ra3, ra4], _razones_excel):
        with col:
            st.markdown(f"""
            <div style="background:#FFFFFF;border-radius:20px;padding:16px 16px;height:100%;
                        box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.06);
                        border:1px solid rgba(0,0,0,0.04);">
                <div style="font-size:1.6rem;">{emoji_r}</div>
                <div style="font-weight:800;color:#1E5631;font-size:0.92rem;margin:6px 0 4px 0;">{titulo_r}</div>
                <div style="font-size:0.8rem;color:#5C6B60;line-height:1.4;">{texto_r}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if _ruta_excel is not None:
        with open(_ruta_excel, "rb") as _f:
            st.download_button(
                "📥 Descargar el Excel original ahora",
                data=_f.read(),
                file_name="Proyecto_Sana_Alimentacion_Grupo_04.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
    else:
        st.info("Para habilitar este botón, coloca el archivo del Excel (por ejemplo "
                "`Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx`) en la misma carpeta que este script "
                "`app.py` antes de ejecutarlo.")

    st.divider()

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
    imagen_bonita(IMAGENES_POR_HOJA[0], caption="Hoja 0 — Introduce tus datos")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "1.-ANÁLISIS SANGUÍNEO":
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
        <div style="background:{_fondo_pt};border-left:4px solid {_hex_pt};border-radius:16px;
                    padding:12px 18px;margin-bottom:8px;
                    box-shadow:0 1px 2px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.04);">
        <b style="color:{_hex_pt};">{_parametro}</b> <span style="color:#1C1C1E;">({_categoria})</span> — <span style="color:#1C1C1E;">{_texto_impacto}</span>
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
    imagen_bonita(IMAGENES_POR_HOJA[1], caption="Hoja 1 — Análisis Sanguíneo")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "2.-IMC Y PERCENTIL":
    hoja_header(2, "El IMC sirve para saber si una persona tiene un peso saludable según su altura y peso. "
                   "En adolescentes y niños se incluye también el Percentil.")
    def _kpi_card(titulo, valor, icono, color="#1E5631"):
        st.markdown(f"""
        <div style="background:#FFFFFF;border-radius:22px;padding:20px 22px;height:100%;
                    box-shadow:0 1px 2px rgba(30,86,49,0.04), 0 8px 20px rgba(30,86,49,0.07);
                    border:1px solid rgba(30,86,49,0.06);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <span style="color:#5C6B60;font-size:0.85rem;font-weight:600;">{titulo}</span>
                <span style="font-size:1.2rem;">{icono}</span>
            </div>
            <div style="font-size:2.3rem;font-weight:800;color:{color};letter-spacing:-0.02em;margin-top:4px;">{valor}</div>
        </div>
        """, unsafe_allow_html=True)

    if etapa in ["Niñez", "Adolescencia"] and _percentil_usuario is not None:
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            _kpi_card("RESULTADO IMC", imc, "📈")
        with kc2:
            _kpi_card("PERCENTIL", _percentil_usuario, "📊", color="#AF52DE")
        with kc3:
            tarjeta_categoria_imc("Categoría", _categoria_imc_usuario)
    elif etapa in ["Niñez", "Adolescencia"]:
        col1, col2 = st.columns(2)
        with col1:
            _kpi_card("RESULTADO IMC", imc, "📈")
        with col2:
            st.error(_categoria_imc_usuario)
    else:
        col1, col2 = st.columns(2)
        with col1:
            _kpi_card("RESULTADO IMC", imc, "📈")
        with col2:
            tarjeta_categoria_imc("Categoría (Adultez/Vejez, sin percentil)", _categoria_imc_usuario)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # --- Texto tipo "Resultados Detallados" + aviso "Recordar", igual al formato de referencia ---
    _riesgo_imc = _categoria_imc_usuario in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"]
    st.markdown(f"""
    <div style="background:#FFFFFF;border-radius:22px;padding:20px 24px;margin-bottom:14px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.06);
                border:1px solid rgba(0,0,0,0.05);">
        <div style="color:#17301F;font-size:0.95rem;line-height:1.6;">
        Según la información ingresada, tu Índice de Masa Corporal (IMC) es <b>{imc}</b>, lo que indica que tu
        peso se encuentra en la categoría de <b>{_categoria_imc_usuario}</b> para tu {"edad y sexo" if etapa in ["Niñez","Adolescencia"] else "estatura"}.
        </div>
        <hr style="border:none;border-top:1px solid #F2F2F7;margin:14px 0;">
        <div style="color:#5C6B60;font-size:0.88rem;line-height:1.6;">
        Hable sobre su categoría de IMC con su proveedor de atención médica, ya que el IMC puede estar
        relacionado con su salud y bienestar general. Su proveedor de atención médica podría determinar las
        posibles razones de su peso actual y recomendar apoyo o tratamiento. El IMC es una medida de detección
        y no pretende diagnosticar enfermedades o dolencias.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if _riesgo_imc:
        st.markdown("""
        <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:20px;
                    padding:16px 24px;margin-bottom:16px;
                    box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
        <b style="color:#FF9500;">Recordar</b><br>
        <span style="color:#1C1C1E;">Tener un IMC elevado aumenta el riesgo de padecer enfermedades crónicas, como
        presión arterial alta, diabetes tipo 2 y colesterol alto. Evalúa tu riesgo con esta prueba de riesgo de
        prediabetes de 1 minuto (enlace abajo). También puedes leer más sobre los riesgos para la salud
        asociados con la obesidad.</span>
        </div>
        """, unsafe_allow_html=True)
        recursos_externos(2, [
            ("🩺 Prueba de riesgo de prediabetes (CDC)", "https://www.cdc.gov/prediabetes/risktest/index.html"),
            ("📖 Riesgos de salud por obesidad (CDC)", "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html"),
        ])

    caja_titulo("Categorías generales de IMC", 2)
    tabla_bonita(pd.DataFrame({
        "Clasificación": ["Bajo Peso", "Peso Saludable", "Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3 (Severa)"],
        "Rango de IMC": ["Menos de 18.5", "18.5 a 24.9", "25 a 29.9", "30 o más", "30 a 34.9", "35 a 39.9", "40 o más"]
    }), 2)

    st.markdown("#### 📈 Percentiles de IMC por edad (2 a 20 años)")
    st.caption("Este gráfico te compara con otros niños y adolescentes de tu misma edad y sexo. Las franjas de "
               "colores son distintos rangos de peso: la franja central (celeste/verde) es el rango más saludable, "
               "mientras que las franjas de arriba o abajo indican bajo peso, sobrepeso u obesidad. La estrella ⭐ "
               "azul marca exactamente en qué punto te encuentras tú, si tu edad está entre 2 y 20 años.")
    sub_mujeres, sub_hombres = st.tabs(["👧 Mujeres", "👦 Hombres"])
    with sub_mujeres:
        st.plotly_chart(grafico_percentil_bandas("Mujer", edad, imc, genero), use_container_width=True)
    with sub_hombres:
        st.plotly_chart(grafico_percentil_bandas("Hombre", edad, imc, genero), use_container_width=True)
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
    imagen_bonita(IMAGENES_POR_HOJA[2], caption="Hoja 2 — IMC y Percentil")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "3.-TMB":
    hoja_header(3, "Biológicamente, los hombres suelen tener más masa muscular y las mujeres más porcentaje "
                   "de grasa; como el músculo quema más energía, el resultado cambia según el sexo.")
    st.metric("Resultado TMB", f"{tmb:.0f} kcal/día")
    caja_util("La TMB es la energía mínima que tu cuerpo necesita para vivir si te quedaras todo el día en cama: "
              "respirar, hacer latir tu corazón, mantener tu temperatura, etc. Es la base sobre la que se calcula "
              "TODO lo demás en esta app (cuánto debes comer, cuánto puedes bajar o subir de peso, etc.). 🔥",
              emoji="⚡", color="#FFF3E0", borde="#FB8C00")
    imagen_bonita(IMAGENES_POR_HOJA[3], caption="Hoja 3 — Tasa Metabólica Basal")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "4.-RCD":
    hoja_header(4)
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
    imagen_bonita(IMAGENES_POR_HOJA[4], caption="Hoja 4 — Requerimiento Calórico Diario")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "5.-OBJETIVO":
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

    with st.expander("ℹ️ ¿Qué significa el plazo estimado?"):
        st.caption("**Corto plazo (10%):** cambios notorios en pocas semanas, exige más disciplina.\n\n"
                   "**Plazo medio (15% bajar / 20% subir):** equilibrio entre velocidad y sostenibilidad.\n\n"
                   "**Plazo largo (20% bajar / 30% subir):** el cambio más lento, pero más seguro, ideal para "
                   "cuerpos en crecimiento.")

    caja_util(f"¡Vamos, {_nombre_saludo}! Aquí se traduce tu meta ('quiero bajar/subir/mantener peso') en un "
              "número exacto de calorías al día. Es el paso que conecta tu objetivo personal con la ciencia: "
              "sin este ajuste, no sabrías cuánto comer realmente para lograr lo que quieres. 🎯",
              emoji="🎯", color="#FCE4EC", borde="#D81B60")
    imagen_bonita(IMAGENES_POR_HOJA[5], caption="Hoja 5 — Subir, Mantener o Bajar el Peso")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "6.-MACRONUTRIENTES":
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
    col_recom, col_graf1 = st.columns([1, 1])
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
            marker=dict(colors=["#FF3B30", "#FF9500", "#34C759"]),
            textinfo="label+percent", hole=0.0,
        )])
        fig_pie_macros.update_layout(height=300, margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
        st.plotly_chart(fig_pie_macros, use_container_width=True)

    caja_util("No basta con contar calorías: también importa DE QUÉ están hechas. Esta hoja reparte tu meta "
              "calórica en proteínas (para músculos), carbohidratos (para energía) y grasas (para hormonas y "
              "órganos), en gramos concretos que puedes usar al armar tus platos. 🍗🍚🥑",
              emoji="🍽️", color="#FFFDE7", borde="#FBC02D")
    imagen_bonita(IMAGENES_POR_HOJA[6], caption="Hoja 6 — Cálculo de los Macronutrientes")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "7.-PORCIONES":
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
    pregunta_faq = st.selectbox("Elige una pregunta:", list(FAQ_PORCIONES.keys()), key="faq_porciones")
    st.info(FAQ_PORCIONES[pregunta_faq])

    caja_util("Comer todas tus calorías de una sola vez sería imposible (¡y poco saludable!). Esta hoja te dice "
              "cuánto puedes comer en cada momento del día: desayuno, meriendas, almuerzo y cena, para que "
              "llegues a tu meta sin pasar hambre ni excederte. ⏰🍴",
              emoji="🍽️", color="#E0F7FA", borde="#00ACC1")
    imagen_bonita(IMAGENES_POR_HOJA[7], caption="Hoja 7 — Porciones del Día")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "8.-FATSECRET":
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
    imagen_bonita(IMAGENES_POR_HOJA[8], caption="Hoja 8 — Página FatSecret")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "9.-DIETA":
    hoja_header(9, "Elige un alimento por macronutriente en cada comida y arma tu menú diario personalizado.")

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
                help="Suma de la Porción corregida de Carbohidrato + Proteína + Grasa, igual que R48 del Excel.")
    col2.metric("Comparación con calorías meta (Hoja 5)", f"{rcd_final:.1f} kcal")
    if abs(total_general - rcd_final) < 1:
        st.success("✅ La dieta armada coincide con la meta calórica del objetivo nutricional.")

    st.divider()
    st.markdown("#### ❓ Guía para entender tu tabla de dieta")
    FAQ_DIETA = {
        "¿Qué significa la columna 'kcal'?": (
            "Es la cantidad de calorías que aporta ese alimento, tomando como referencia cada 100 gramos "
            "de ese alimento (así viene definido en la base de datos nutricional del proyecto)."
        ),
        "¿Qué significa 'Porción corregida'?": (
            "Es cuántas calorías del momento del día (Desayuno, Almuerzo, etc.) le corresponden a ese "
            "macronutriente en particular. Por ejemplo, si el Almuerzo tiene 1000 kcal en total, la Porción "
            "corregida de Carbohidrato será el 50% de esas 1000 kcal, la de Proteína el 20% y la de Grasa el 30%."
        ),
        "¿Qué significa 'Gramos finales a consumir'?": (
            "Es la cantidad exacta, en gramos, que debes comer de ESE alimento específico para llegar a la "
            "Porción corregida en calorías. Se calcula dividiendo la Porción corregida entre el kcal del "
            "alimento y multiplicando por 100."
        ),
        "Entonces, ¿cuánto tengo que comer en cada comida?": (
            "Debes preparar los tres alimentos que elegiste para ese momento del día (Carbohidrato, Proteína "
            "y Grasa), cada uno en la cantidad de 'Gramos finales a consumir' que te muestra la tabla. Juntos, "
            "esos tres alimentos completan las calorías que te corresponden en esa comida."
        ),
        "¿Por qué el total coincide con mis calorías meta?": (
            "Porque el sistema reparte tu meta calórica diaria (Hoja 5) primero entre los 5 momentos del día "
            "(Hoja 7) y luego, dentro de cada momento, entre los 3 macronutrientes. Al sumar todo de nuevo, "
            "el resultado debe coincidir con tu meta calórica original."
        ),
    }
    pregunta_dieta = st.selectbox("Elige una pregunta sobre tu tabla de dieta:", list(FAQ_DIETA.keys()), key="faq_dieta")
    st.info(FAQ_DIETA[pregunta_dieta])

    recursos_externos(9, [
        ("🌐 Buscar alimentos en FatSecret", "https://www.fatsecret.es/"),
    ])
    caja_util("Aquí armas tu menú real del día eligiendo alimentos que te gusten, y la app hace toda la "
              "matemática por ti: cada momento del día reparte sus calorías en 50% carbohidratos, 20% proteínas "
              "y 30% grasas, y luego convierte esas calorías a gramos según el alimento específico que elegiste "
              "— exactamente igual que en la hoja de cálculo original. ¡Comer sano también puede ser rico! 😋",
              emoji="🍱", color="#FBE9E7", borde="#FF7043")
    imagen_bonita(IMAGENES_POR_HOJA[9], caption="Hoja 9 — Plan de Dieta Semanal")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "10.-CLIMA CHICLAYO":
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
        st.caption("Este cálculo usa el RCD base de la Hoja 4 (antes del ajuste por objetivo).")
        st.metric("Gasto energético ajustado al clima de Chiclayo", f"{rcd_chiclayo:.1f} kcal/día")

    st.divider()
    recursos_externos(10, [
        ("☀️ Clima de Chiclayo (Senamhi)", "https://www.senamhi.gob.pe/"),
    ])
    caja_util("Vivir en un lugar caluroso como Chiclayo también afecta cuántas calorías gasta tu cuerpo. Este "
              "dato extra te da una versión más realista y localizada de tu gasto calórico, pensada "
              "específicamente para nuestra región. ☀️🌴",
              emoji="🌡️", color="#FFF8E1", borde="#F9A825")
    imagen_bonita(IMAGENES_POR_HOJA[10], caption="Hoja 10 — Gasto Energético según el Clima de Chiclayo")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "11.-APORTE 1: EMBARAZO":
    hoja_header(11, "Calculadora independiente, no conectada a los datos generales de la Hoja 0.")
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
    if nombre_emb.strip():
        st.metric(f"Total TMB para {nombre_emb}", f"{tmb_emb:.0f} kcal/día")
    else:
        st.metric("Total TMB", f"{tmb_emb:.0f} kcal/día")
    caja_util("Durante el embarazo el cuerpo necesita energía extra para que el bebé se desarrolle sanamente. "
              "Esta calculadora te dice cuántas calorías adicionales necesitas según el trimestre en que estás, "
              "sin tener que adivinarlo ni arriesgar tu nutrición ni la de tu bebé. 🤰💕",
              emoji="👶", color="#F8ECFB", borde="#BA68C8")
    imagen_bonita(IMAGENES_POR_HOJA[11], caption="Aporte 1 — TMB en Embarazo")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "12.-APORTE 2: CAFEÍNA":
    hoja_header(12, "La cafeína tarda entre 5 y 6 horas en reducirse a la mitad en el cuerpo. Calcular de 8 a 10 horas "
                    "antes de acostarse asegura que el estimulante baje lo suficiente para no bloquear los receptores "
                    "cerebrales del sueño, protegiendo el descanso profundo.")
    hora_dormir = st.time_input("Hora de dormir:", value=datetime.strptime("22:00", "%H:%M").time())
    dt_dormir = datetime.combine(datetime.today(), hora_dormir)
    dt_limite = dt_dormir - timedelta(hours=8)
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
    imagen_bonita(IMAGENES_POR_HOJA[12], caption="Aporte 2 — Hora Límite de Cafeína")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "13.-LÍNEA DE TIEMPO":
    hoja_header(13, "Proyección basada en el principio termodinámico de las 7,700 kcal por kilogramo de grasa "
                    "corporal: la misma constante que usan los nutricionistas para estimar cambios de peso.")

    st.caption("Se calcula comparando tu gasto de mantenimiento (Hoja 4) con tu meta calórica (Hoja 5), "
               "proyectado a 60 días (2 meses), usando 7,700 kcal como el equivalente a 1 kg de grasa corporal.")

    def calcular_proyeccion(calorias_consumidas, tdee, dias=60):
        """Función proyectiva: aplica la fórmula del déficit/superávit calórico y retorna
        (deficit_diario, peso_proyectado_kg) para el número de días indicado."""
        deficit_diario = tdee - calorias_consumidas
        peso_proyectado = (deficit_diario * dias) / 7700
        return deficit_diario, peso_proyectado

    deficit_diario, peso_cambio_60 = calcular_proyeccion(rcd_final, rcd, dias=60)

    # --- Tarjeta de resultado destacado (estilo "hero", coherente con la identidad visual de la app) ---
    if objetivo == "Mantenerse" or abs(peso_cambio_60) < 0.05:
        grad = "linear-gradient(135deg,#34C759 0%,#30D158 60%,#63E6A5 100%)"
        sombra = "rgba(52,199,89,0.30)"
        mensaje_destacado = f"Como tu objetivo es mantenerte, {_nombre_saludo}, tu peso se mantendría estable durante los próximos 60 días. ¡Vas por buen camino! 💚"
    elif peso_cambio_60 > 0:
        grad = "linear-gradient(135deg,#007AFF 0%,#5AC8FA 55%,#64D2FF 100%)"
        sombra = "rgba(0,122,255,0.30)"
        mensaje_destacado = f"Si mantienes este hábito por 60 días, {_nombre_saludo}, tu proyección estimada de pérdida es de <b>{peso_cambio_60:.1f} kg</b>."
    else:
        grad = "linear-gradient(135deg,#FF9500 0%,#FFB300 55%,#FFCC66 100%)"
        sombra = "rgba(255,149,0,0.30)"
        mensaje_destacado = f"⚠️ Cuidado, {_nombre_saludo}: si mantienes este hábito, podrías <b>aumentar aproximadamente {abs(peso_cambio_60):.1f} kg</b> en 2 meses."

    st.markdown(f"""
    <div style="background:{grad};border-radius:28px;padding:32px 36px;color:white;
                box-shadow:0 16px 36px {sombra};margin:10px 0 22px 0;">
        <div style="font-size:0.82rem;letter-spacing:0.03em;opacity:0.9;text-transform:uppercase;font-weight:700;">
            Proyección a 60 días (2 meses)</div>
        <div style="font-size:2.2rem;font-weight:800;margin:6px 0 10px 0;letter-spacing:-0.02em;">
            {peso - peso_cambio_60:.1f} kg <span style="font-size:1rem;font-weight:500;opacity:0.9;">peso estimado</span></div>
        <div style="font-size:1rem;line-height:1.5;font-weight:400;">{mensaje_destacado}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Curva de progreso día a día: gráfico Plotly claro, con hitos marcados en 0/30/60 días ---
    dias_eje = list(range(0, 61))
    pesos_dia_completo = [round(peso - (deficit_diario * d) / 7700, 2) for d in dias_eje]

    color_linea = "#34C759" if (objetivo == "Mantenerse" or abs(peso_cambio_60) < 0.05) else ("#007AFF" if peso_cambio_60 > 0 else "#FF9500")

    fig_tiempo = go.Figure()
    fig_tiempo.add_trace(go.Scatter(
        x=dias_eje, y=pesos_dia_completo, mode="lines", name="Peso estimado",
        line=dict(color=color_linea, width=4, shape="spline"),
        fill="tozeroy", fillcolor=color_linea.replace(")", ",0.12)").replace("#", "rgba(") if False else None,
    ))
    # Relleno suave bajo la curva
    fig_tiempo.update_traces(fill="tonexty")
    fig_tiempo.add_trace(go.Scatter(x=dias_eje, y=[0]*len(dias_eje), line=dict(width=0), showlegend=False, hoverinfo="skip"))

    # Puntos de hito: hoy, 30 días, 60 días
    hitos_x = [0, 30, 60]
    hitos_y = [pesos_dia_completo[0], pesos_dia_completo[30], pesos_dia_completo[60]]
    hitos_txt = ["Hoy", "En 1 mes", "En 2 meses"]
    fig_tiempo.add_trace(go.Scatter(
        x=hitos_x, y=hitos_y, mode="markers+text", name="Hitos",
        marker=dict(size=14, color="#FFFFFF", line=dict(color=color_linea, width=4)),
        text=[f"{t}<br><b>{v:.1f} kg</b>" for t, v in zip(hitos_txt, hitos_y)],
        textposition="top center", textfont=dict(size=13, color="#17301F", family="-apple-system"),
        showlegend=False,
    ))

    _rango_min = min(pesos_dia_completo) - 3
    _rango_max = max(pesos_dia_completo) + 5
    fig_tiempo.update_layout(
        title=dict(text="¿Cómo cambiará tu peso en los próximos 60 días?", x=0.02, xanchor="left",
                   font=dict(size=18, color="#17301F", family="-apple-system")),
        xaxis_title="Días a partir de hoy", yaxis_title="Peso estimado (kg)",
        xaxis=dict(dtick=10, gridcolor="#F0F0F0"), yaxis=dict(range=[_rango_min, _rango_max], gridcolor="#F0F0F0"),
        height=430, margin=dict(t=60, l=10, r=10, b=10),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    st.plotly_chart(fig_tiempo, use_container_width=True)
    st.caption("👀 Lee el gráfico así: la línea muestra tu peso estimado día a día. Los tres círculos marcan "
               "'Hoy', 'En 1 mes' y 'En 2 meses', con el peso exacto proyectado en cada punto. Si la línea "
               "baja, significa que irías perdiendo peso; si sube, irías ganando peso; y si se mantiene plana, "
               "tu peso no cambiaría.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Peso actual (hoy)", f"{pesos_dia_completo[0]:.1f} kg")
    col2.metric("Estimado en 30 días", f"{pesos_dia_completo[30]:.1f} kg",
                delta=f"{pesos_dia_completo[30]-pesos_dia_completo[0]:.1f} kg")
    col3.metric("Estimado en 60 días", f"{pesos_dia_completo[60]:.1f} kg",
                delta=f"{pesos_dia_completo[60]-pesos_dia_completo[0]:.1f} kg")

    st.caption("⚠️ Esta proyección es un cálculo matemático de referencia (no un diagnóstico médico) y asume "
               "que mantienes el mismo ajuste calórico todos los días. El cuerpo humano no cambia de forma "
               "perfectamente lineal, y en menores de edad cualquier cambio de peso debe estar supervisado por "
               "un profesional de la salud.")

    caja_util(f"Esta línea de tiempo te muestra, con la misma matemática que usan los nutricionistas, cómo "
              f"avanzarías en 60 días si sigues tu plan calórico. Ver el progreso estimado ayuda a entender que "
              f"los resultados reales toman semanas o meses de constancia — ¡tú puedes lograrlo, {_nombre_saludo}! 🌱",
              emoji="📈", color="#E8EAF6", borde="#3949AB")
    imagen_bonita(IMAGENES_POR_HOJA[13], caption="Hoja 13 — Línea de Tiempo")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "📄 MI REPORTE":
    hoja_header(14, "Un informe médico completo, con tus datos, resultados y recomendaciones — listo para imprimir.")

    st.markdown(f"""
    <div style="background:#E7F6FD;border-left:5px solid #32ADE6;border-radius:20px;
                padding:16px 24px;margin-bottom:16px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);" class="no-print">
    🔒 <b style="color:#1C7DAD;">Privacidad:</b> este reporte se genera únicamente con la información que ingresaste en esta sesión.
    Nada se guarda en un servidor ni queda almacenado al cerrar o recargar la página.
    </div>
    """, unsafe_allow_html=True)

    _fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- Encabezado tipo "informe médico" ---
    st.markdown(f"""
    <div class="print-only-report" style="background:#ffffff;border:1px solid rgba(50,173,230,0.25);border-radius:24px;padding:24px 28px;margin-bottom:18px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 22px rgba(0,0,0,0.06);">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;">
            <div>
                <div style="font-size:1.3rem;font-weight:800;color:#32ADE6;letter-spacing:-0.02em;">📄 Informe de Resultados — CIAM&SUNI</div>
                <div style="color:#6C6C70;font-size:0.9rem;">C.E.P. "Santa María Reina", Chiclayo</div>
            </div>
            <div style="text-align:right;color:#6C6C70;font-size:0.85rem;">Generado: {_fecha_reporte}</div>
        </div>
        <hr style="border:none;border-top:1px solid #F2F2F7;margin:14px 0;">
        <b>Nombre:</b> {_nombre_saludo} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>Edad:</b> {edad} años ({etapa}) &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>Género:</b> {genero}
    </div>
    """, unsafe_allow_html=True)

    # --- Bloque 1: Datos antropométricos ---
    st.markdown("#### 📏 Datos antropométricos")
    r1, r2, r3 = st.columns(3)
    r1.metric("Peso", f"{peso} kg")
    r2.metric("Estatura", f"{estatura} cm")
    with r3:
        if etapa in ["Niñez", "Adolescencia"]:
            tarjeta_categoria_imc(f"IMC: {imc}", _categoria_imc_usuario)
        else:
            tarjeta_categoria_imc(f"IMC: {imc}", _categoria_imc_usuario)

    st.markdown("#### 🔥 Requerimiento energético")
    r4, r5, r6 = st.columns(3)
    r4.metric("TMB", f"{tmb:.0f} kcal/día")
    r5.metric("RCD (gasto diario)", f"{rcd:.0f} kcal/día")
    r6.metric("Meta calórica (objetivo)", f"{rcd_final:.0f} kcal/día")

    st.markdown("#### 🍽️ Macronutrientes recomendados")
    r7, r8, r9 = st.columns(3)
    r7.metric("Proteínas", f"{gr_prot:.1f} g")
    r8.metric("Carbohidratos", f"{gr_carb:.1f} g")
    r9.metric("Grasas", f"{gr_gras:.1f} g")

    # --- Bloque 2: Análisis sanguíneo, si hay datos ---
    st.markdown("#### 🩸 Análisis sanguíneo")
    _valores_examen = [hemo, trigli, gluco, coles, hierro]
    _tiene_examen = any(v > 0 for v in _valores_examen)
    if _tiene_examen:
        _cat_hemo_r = clasif_hemoglobina(hemo, etapa, genero)
        _cat_trigli_r = clasif_trigliceridos(trigli)
        _cat_gluco_r = clasif_glucosa(gluco)
        _cat_coles_r = clasif_colesterol(coles)
        _cat_hierro_r = clasif_hierro(hierro, etapa, genero)
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        with rc1: tarjeta_semaforo("Hemoglobina", f"{hemo} g/dL", _cat_hemo_r)
        with rc2: tarjeta_semaforo("Triglicéridos", f"{trigli} mg/dL", _cat_trigli_r)
        with rc3: tarjeta_semaforo("Glucosa", f"{gluco} mg/dL", _cat_gluco_r)
        with rc4: tarjeta_semaforo("Colesterol", f"{coles} mg/dL", _cat_coles_r)
        with rc5: tarjeta_semaforo("Hierro", f"{hierro} µg/dL", _cat_hierro_r)
    else:
        st.info("Aún no ingresaste tus valores de análisis sanguíneo en la barra lateral.")
        _cat_hemo_r = _cat_trigli_r = _cat_gluco_r = _cat_coles_r = _cat_hierro_r = "Introducir datos"

    # --- Bloque 3: Plan de dieta armado (si el usuario visitó la Hoja 9) ---
    st.markdown("#### 🍱 Tu plan de comidas del día")
    _tiene_dieta = all(f"c_{comida}" in st.session_state for comida in DIETA)
    if _tiene_dieta:
        filas_r = []
        for comida in DIETA:
            filas_r.append({
                "Comida": comida,
                "Carbohidrato": st.session_state.get(f"c_{comida}", "—"),
                "Proteína": st.session_state.get(f"p_{comida}", "—"),
                "Grasa": st.session_state.get(f"g_{comida}", "—"),
            })
        tabla_bonita(pd.DataFrame(filas_r), 9)
    else:
        st.info("Aún no armaste tu plan de comidas en la Hoja 9.-DIETA. Visítala para que aparezca aquí.")

    # --- Bloque 4: Proyección a 60 días ---
    st.markdown("#### 📈 Proyección estimada (60 días)")
    _deficit_r = rcd - rcd_final
    _peso_cambio_r = (_deficit_r * 60) / 7700
    _peso_proyectado_r = peso - _peso_cambio_r
    st.metric("Peso estimado en 60 días", f"{_peso_proyectado_r:.1f} kg")

    # =====================================================================================
    # BLOQUE 5: RESUMEN CLÍNICO Y RECOMENDACIONES — estilo informe médico profesional
    # =====================================================================================
    st.divider()
    st.markdown("#### 🩺 Resumen clínico y recomendaciones")

    # Construimos una lista de recomendaciones según cada resultado obtenido
    _recomendaciones = []

    # IMC
    if _categoria_imc_usuario == "Peso Saludable":
        _recomendaciones.append("Tu IMC se encuentra en un rango saludable. Mantén tus hábitos actuales de alimentación y actividad física.")
    elif _categoria_imc_usuario in ["Bajo Peso"]:
        _recomendaciones.append("Tu IMC sugiere bajo peso. Conversa con tu médico o nutricionista para evaluar si necesitas aumentar tu ingesta calórica de forma segura.")
    elif _categoria_imc_usuario in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"]:
        _recomendaciones.append("Tu IMC sugiere un peso por encima del rango saludable, lo que puede aumentar el riesgo de enfermedades crónicas como hipertensión, diabetes tipo 2 y colesterol alto. Se recomienda evaluación con un profesional de la salud.")

    # Análisis sanguíneo
    if _tiene_examen:
        for _param, _cat in [("Hemoglobina", _cat_hemo_r), ("Triglicéridos", _cat_trigli_r),
                              ("Glucosa", _cat_gluco_r), ("Colesterol", _cat_coles_r), ("Hierro", _cat_hierro_r)]:
            _color_r = CATEGORIA_SEMAFORO.get(_cat, "gris")
            if _color_r in ["ambar", "rojo"]:
                _recomendaciones.append(f"**{_param}** ({_cat}): {MENSAJES_TRIAJE.get(_param, {}).get(_color_r, '')}")

    if not _recomendaciones:
        _recomendaciones.append("No se detectaron alertas con la información ingresada hasta el momento.")

    st.markdown(f"""
    <div class="print-only-report" style="background:#FFFFFF;border:1px solid rgba(30,86,49,0.15);border-radius:20px;
                padding:20px 24px;box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
        <ul style="margin:0;padding-left:20px;color:#17301F;line-height:1.7;font-size:0.92rem;">
            {''.join(f"<li>{r}</li>" for r in _recomendaciones)}
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="print-only-report" style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:20px;
                padding:16px 24px;margin-top:16px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
    <b style="color:#FF9500;">Recordar:</b> hable sobre su categoría de IMC y sus resultados con su proveedor de
    atención médica, ya que estos valores pueden estar relacionados con su salud y bienestar general. Su
    proveedor de atención médica podría determinar las posibles razones de los resultados obtenidos y
    recomendar apoyo o tratamiento. Este informe es una herramienta de detección orientativa y no pretende
    diagnosticar enfermedades ni dolencias.
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("⚕️ Este informe es orientativo y educativo. No reemplaza una evaluación médica o nutricional "
               "profesional.")

    # =====================================================================================
    # GENERACIÓN DEL PDF — informe clínico real, listo para descargar e imprimir
    # =====================================================================================
    _examen_pdf = [
        ("Hemoglobina", f"{hemo} g/dL", _cat_hemo_r),
        ("Triglicéridos", f"{trigli} mg/dL", _cat_trigli_r),
        ("Glucosa", f"{gluco} mg/dL", _cat_gluco_r),
        ("Colesterol", f"{coles} mg/dL", _cat_coles_r),
        ("Hierro", f"{hierro} µg/dL", _cat_hierro_r),
    ]
    _dieta_pdf = {}
    if _tiene_dieta:
        for comida in DIETA:
            _dieta_pdf[comida] = {
                "Carbohidrato": st.session_state.get(f"c_{comida}", "—"),
                "Proteína": st.session_state.get(f"p_{comida}", "—"),
                "Grasa": st.session_state.get(f"g_{comida}", "—"),
            }

    _datos_pdf = {
        "fecha": _fecha_reporte,
        "nombre": _nombre_saludo,
        "edad": edad,
        "etapa": etapa,
        "genero": genero,
        "peso": peso,
        "estatura": estatura,
        "imc": imc,
        "categoria_imc": _categoria_imc_usuario,
        "percentil": _percentil_usuario,
        "tmb": tmb,
        "rcd": rcd,
        "rcd_final": rcd_final,
        "objetivo": objetivo,
        "gr_prot": gr_prot, "cal_prot": cal_prot,
        "gr_carb": gr_carb, "cal_carb": cal_carb,
        "gr_gras": gr_gras, "cal_gras": cal_gras,
        "tiene_examen": _tiene_examen,
        "examen": _examen_pdf,
        "tiene_dieta": _tiene_dieta,
        "dieta": _dieta_pdf,
        "peso_proyectado": _peso_proyectado_r,
        "recomendaciones": _recomendaciones,
    }

    _pdf_bytes = generar_pdf_reporte(_datos_pdf)
    _nombre_archivo = f"Informe_CIAMSUNI_{_nombre_saludo}".replace(" ", "_") + ".pdf"

    st.markdown("#### 📥 Descarga tu informe")
    st.caption("Genera un PDF con estilo de informe clínico (no una captura de la página) que puedes "
               "guardar, enviar o imprimir directamente desde tu lector de PDF.")
    st.download_button(
        "📄 Descargar Informe en PDF",
        data=_pdf_bytes,
        file_name=_nombre_archivo,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

    caja_util(f"Este es tu informe final, {_nombre_saludo}: reúne en un solo lugar todo lo que calculamos en "
              "las hojas anteriores, con el formato de un informe que te entregarían en un consultorio. "
              "Usa el botón '📄 Descargar Informe en PDF' para obtener un archivo PDF real, listo para "
              "imprimir o compartir. 📄✨",
              emoji="📄", color="#E0F2F1", borde="#00695C")
    imagen_bonita(IMAGENES_POR_HOJA[14], caption="Hoja 14 — Mi Reporte de Resultados")

elif hoja_activa == "🎓 SOBRE NOSOTRAS":
    _, titulo13, emoji13, borde13, fondo13 = COLORES[15]
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
        if _LOGO_CIRCULAR.exists():
            st.image(str(_LOGO_CIRCULAR), width=190)
        elif _ESCUDO.exists():
            st.image(str(_ESCUDO), width=190)
    with col_texto:
        st.markdown("""
        <div style="background:#FFEBF0;border-left:5px solid #FF2D55;border-radius:20px;
                    padding:18px 22px;
                    box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
        <b style="color:#FF2D55;">📖 Sobre nosotras</b><br><br>
        <span style="color:#1C1C1E;">Somos un grupo de estudiantes de 5to de secundaria de la I.E. Santa María Reina, apasionadas
        por la tecnología y la salud. Este proyecto nace con el objetivo de fomentar hábitos saludables
        mediante herramientas digitales accesibles, aplicando conocimientos de nutrición y programación
        para mejorar el bienestar de nuestra comunidad escolar.</span>
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
           "Alimentación) para el proyecto de tesis escolar sobre salud pública en Lambayeque, Grupo N°04. "
           "🔒 Ningún dato ingresado se almacena: toda la información vive solo en tu sesión actual.")
