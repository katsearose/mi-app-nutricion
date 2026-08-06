import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import io
import math
import uuid
import textwrap
import plotly.graph_objects as go
import altair as alt
from datetime import datetime, timedelta
from urllib.parse import quote
from pathlib import Path


def _hex_a_rgba(color_hex, alpha=0.12):
    """Convierte un color '#RRGGBB' a 'rgba(r,g,b,alpha)'. Evita el error de Plotly
    con algunos entornos que no aceptan hex de 8 dígitos (#RRGGBBAA) como fillcolor."""
    color_hex = (color_hex or "#34C759").lstrip("#")
    if len(color_hex) >= 6:
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
    else:
        r, g, b = 52, 199, 89
    return f"rgba({r},{g},{b},{alpha})"

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether, Image, PageBreak
)
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="CIAM&SUNI: Tu Salud, Personalizada", layout="wide", page_icon="🍎")

# =========================================================================================
# IDIOMA / LANGUAGE — selector global (sidebar, Bloque 0) + helper de traducción T(es, en)
# =========================================================================================
st.session_state.setdefault("idioma", "Español")


def T(es, en=None):
    """Devuelve el texto en español o inglés según el idioma elegido en el sidebar.
    Si no se provee versión en inglés, devuelve el texto en español como respaldo."""
    if st.session_state.get("idioma", "Español") == "English" and en is not None:
        return en
    return es


# Diccionarios de traducción compartidos entre el panel de datos (sidebar) y otras hojas
# (p.ej. el resumen de la Hoja 0) que necesitan mostrar los mismos valores ya traducidos.
_ETAPA_EN = {"Niñez": "Childhood", "Adolescencia": "Adolescence", "Adultez": "Adulthood", "Vejez": "Old Age"}
_ACT_LABEL_ES = {
    "Sedentaria": "🪑 Sedentario o Poco Activo (Factor 1.2)",
    "Ligero": "🚶 Ligeramente Activo (Factor 1.375-1.55)",
    "Moderada": "🏃 Moderadamente Activo (Factor 1.55-1.75)",
    "Intensa": "🔥 Muy Activo / Intenso (Factor 1.8-2.1)",
}
_ACT_LABEL_EN = {
    "Sedentaria": "🪑 Sedentary or Low Activity (Factor 1.2)",
    "Ligero": "🚶 Lightly Active (Factor 1.375-1.55)",
    "Moderada": "🏃 Moderately Active (Factor 1.55-1.75)",
    "Intensa": "🔥 Very Active / Intense (Factor 1.8-2.1)",
}
_OBJ_EN = {"Bajar de peso": "Lose weight", "Subir de peso": "Gain weight", "Mantenerse": "Maintain weight"}

# =========================================================================================
# BASE PERUANA DE ALIMENTOS — datos reales extraídos de las Tablas Peruanas de Composición
# de Alimentos (INS/CENAN, 11.ª edición digital, marzo 2025, ISBN 978-612-310-178-7).
# Curaduría de ~343 alimentos de mayor consumo en el Perú, de los ~970 alimentos crudos
# que contiene la publicación oficial. Valores expresados por 100 g de porción comestible.
# Columnas: (código, nombre, grupo, kcal, proteínas g, grasas g, CHO disponible g,
#            fibra g, calcio mg, hierro mg, vitamina C mg)
# =========================================================================================
FOOD_DB_RAW = [
    ('A3', 'Arroz blanco corriente', 'A', 358.0, 7.8, 0.7, None, None, 6.0, 1.04, 0.9),
    ('A2', 'Arroz pilado o pulido cocido', 'A', 115.0, 2.4, 0.1, None, None, 11.0, 0.3, 0.0),
    ('A167', 'Hojuela precocida de avena con quinua', 'A', 369.0, 11.1, 10.8, 58.3, 9.3, 40.0, 3.14, None),
    ('A5', 'Avena envasada', 'A', 380.0, 13.7, 4.7, None, None, 51.0, 3.5, 0.0),
    ('A6', 'Hojuela cocida de avena', 'A', 54.0, 1.3, 0.5, None, None, 21.0, 0.5, 0.0),
    ('A7', 'Hojuela cruda de avena', 'A', 333.0, 13.3, 4.0, 61.6, 10.6, 49.0, 4.1, 0.0),
    ('A12', 'Cebada con cáscara', 'A', 284.0, 8.4, 2.0, 60.2, 17.3, 61.0, 4.58, 0.0),
    ('A15', 'Cebada pelada para mote', 'A', 328.0, 8.2, 1.1, None, None, 47.0, 3.6, 0.0),
    ('A17', 'Cebada perlada o resbalada cocida', 'A', 59.0, 1.0, 0.1, 13.9, 3.8, 9.0, 0.9, 0.0),
    ('A18', 'Cebada perlada o resbalada cruda', 'A', 277.0, 5.3, 0.6, 64.2, 15.6, 18.0, 4.0, 2.0),
    ('A19', 'Cebada tostada y molida (chaquepa)', 'A', 349.0, 7.7, 0.8, None, None, 55.0, 7.1, 0.0),
    ('A16', 'Cebada tostada, harina integral', 'A', 274.0, 8.7, 3.2, 54.8, 25.4, None, 9.6, None),
    ('A13', 'Llunka de cebada (morón americano)', 'A', 249.0, 1.9, 0.7, 59.8, 17.3, 42.0, 9.7, 2.1),
    ('A14', 'Mashka o machica de cebada (harina de cebada tostada)', 'A', 302.0, 8.6, 0.7, 67.3, 10.1, 74.0, 12.3, 1.9),
    ('A21', 'Fideo crudo fortificado con hierro', 'A', 337.0, 9.4, 0.2, 74.5, 3.2, 24.0, 5.5, 0.0),
    ('A22', 'Fideo tallarín crudo fortificado con hierro', 'A', 305.0, 9.5, 0.1, 66.4, 3.2, 40.0, 5.5, 0.0),
    ('A83', 'Galleta de soda (San Jorge)', 'A', 440.0, 9.3, 13.3, None, None, 68.0, 7.7, 0.0),
    ('A24', 'Galleta de soda (salada)', 'A', 433.0, 10.1, 14.7, 65.0, 3.0, 38.0, 1.5, 0.0),
    ('A84', 'Galleta de vainilla (Field)', 'A', 462.0, 7.3, 15.6, None, None, None, 4.4, None),
    ('A25', 'Galleta de vainilla (dulce)', 'A', 434.0, 6.0, 12.7, 73.8, 1.1, 22.0, 0.6, 0.0),
    ('A1', 'Kiwicha, achita o achis o amaranto', 'A', 351.0, 12.8, 6.6, 59.8, 9.3, 236.0, 7.32, 1.3),
    ('A104', 'Harina de maíz morado (api)', 'A', 318.0, 8.5, 4.2, 64.5, 9.8, 29.0, 6.47, None),
    ('A34', 'Maíz, grano fresco (choclo)', 'A', 104.0, 3.3, 0.8, 25.1, 2.7, 8.0, 0.8, 4.8),
    ('A112', 'Pan cuay de trigo de Carhuaz', 'A', 358.0, 10.0, 11.6, None, None, None, 5.62, None),
    ('A113', 'Pan cuay de trigo de Huaraz', 'A', 297.0, 7.6, 10.1, 43.8, 5.1, None, 4.45, None),
    ('A45', 'Pan de cebada (serrano)', 'A', 295.0, 7.2, 0.2, None, None, 60.0, 6.5, None),
    ('A47', 'Pan de molde', 'A', 317.0, 6.8, 2.5, 66.8, 2.4, 13.0, 0.4, 0.0),
    ('A186', 'Pan de molde integral', 'A', 274.0, 12.4, 5.9, 42.8, 6.4, 308.0, 5.65, 0.0),
    ('A122', 'Pan de quinua de Lima', 'A', 241.0, 9.5, 1.7, None, None, None, 3.31, None),
    ('A123', 'Pan de trigo artesanal de Carhuaz', 'A', 286.0, 8.8, 4.6, None, None, None, 5.11, None),
    ('A49', 'Pan francés fortificado con hierro', 'A', 277.0, 8.4, 0.2, 60.5, 2.4, 35.0, 3.14, 1.0),
    ('A129', 'Pan integral', 'A', 339.0, 9.1, 9.0, None, None, None, 5.16, None),
    ('A54', 'Quinua', 'A', 351.0, 13.6, 5.8, 60.7, 5.9, 56.0, 7.5, 0.5),
    ('A52', 'Quinua blanca (Puno)', 'A', 355.0, 13.3, 6.1, 61.2, 5.9, 120.0, 4.31, 0.0),
    ('A51', 'Quinua blanca (Junín)', 'A', 334.0, 12.5, 6.5, 56.0, 10.0, 85.0, 3.03, 0.0),
    ('A53', 'Quinua cocida', 'A', 89.0, 2.8, 1.3, None, None, 27.0, 1.6, 0.0),
    ('A55', 'Quinua dulce, blanca (Junín)', 'A', 361.0, 11.1, 7.7, 61.5, 5.9, 93.0, 4.3, 2.2),
    ('A56', 'Quinua dulce, blanca (Puno)', 'A', 349.0, 11.6, 5.3, 63.0, 5.9, 115.0, 5.3, 1.1),
    ('A57', 'Quinua dulce, rosada (Junín)', 'A', 360.0, 12.3, 7.2, 61.2, 5.9, 80.0, 4.3, 1.1),
    ('A60', 'Quinua rosada (Puno)', 'A', 356.0, 12.5, 6.4, 61.7, 5.9, 124.0, 5.2, 0.0),
    ('A50', 'Afrecho de quinua', 'A', 351.0, 10.7, 4.5, None, None, 573.0, 4.0, None),
    ('A58', 'Harina de quinua', 'A', 337.0, 12.4, 6.0, 57.9, 9.3, 104.0, 9.65, None),
    ('A59', 'Hojuela de quinua', 'A', 376.0, 13.9, 7.4, None, None, 114.0, 5.46, None),
    ('A61', 'Sémola de quinua', 'A', 362.0, 19.5, 10.7, 47.9, 5.9, 76.0, 3.6, 0.0),
    ('A144', 'Quinua, variedad Ayara (Puno)', 'A', 276.0, 14.0, 6.3, 41.1, 21.5, None, 6.25, None),
    ('A147', 'Quinua, variedad CICA-127 (Puno)', 'A', 360.0, 15.8, 5.2, 62.0, 5.1, None, 5.81, None),
    ('A146', 'Quinua, variedad CICA-18 (Puno)', 'A', 345.0, 14.4, 5.7, 58.7, 7.6, None, 4.37, None),
    ('A149', 'Quinua, variedad Choclito (Puno)', 'A', 342.0, 13.4, 5.2, 59.9, 7.2, None, 4.49, None),
    ('A150', 'Quinua, variedad Chullpi- roja (Puno)', 'A', 330.0, 13.7, 5.5, 55.9, 10.9, None, 5.87, None),
    ('A148', 'Quinua, variedad Cuchiwilla (Puno)', 'A', 317.0, 15.2, 5.2, 52.1, 12.2, None, 4.15, None),
    ('A151', 'Quinua, variedad Misa Jiura (Puno)', 'A', 349.0, 12.3, 5.4, 62.2, 6.4, None, 4.0, None),
    ('A152', 'Quinua, variedad Pasankalla-roja (Puno)', 'A', 355.0, 12.7, 6.2, 61.6, 6.9, None, 4.85, None),
    ('A153', "Quinua, variedad Q' OITU-negra (Puno)", 'A', 308.0, 11.6, 4.9, 53.9, 14.3, None, 11.53, None),
    ('A154', 'Quinua, variedad Wariponcho (Puno)', 'A', 347.0, 12.6, 5.5, 61.2, 6.7, None, 3.77, None),
    ('A155', 'Quinua, variedad Witulla (Puno)', 'A', 350.0, 13.7, 5.9, 60.2, 7.7, None, 4.99, None),
    ('A145', 'Quinua, variedad blanca de Juli (Puno)', 'A', 347.0, 11.6, 4.8, 63.7, 6.9, None, 4.32, None),
    ('A143', 'Quinua, variedad real', 'A', 331.0, 14.2, 5.1, 56.7, 9.1, None, 4.0, None),
    ('A73', 'Trigo', 'A', 289.0, 10.3, 1.9, 62.5, 12.2, 36.0, 3.87, 4.8),
    ('A67', 'Trigo para mote pelado cocido', 'A', 63.0, 1.9, 0.1, None, None, 29.0, 0.4, 0.0),
    ('A68', 'Trigo para mote pelado crudo', 'A', 325.0, 9.8, 0.9, None, None, 80.0, 2.5, 0.9),
    ('A70', 'Trigo resbalado cocido', 'A', 83.0, 2.8, 0.3, None, None, 5.0, 0.5, 0.7),
    ('A71', 'Trigo resbalado crudo', 'A', 327.0, 11.4, 1.8, None, None, 17.0, 4.8, 4.5),
    ('A159', 'Trigo sin tostar (chaquepa)', 'A', 338.0, 7.0, 2.2, None, None, None, 2.43, None),
    ('A160', 'Trigo tostado (chaquepa)', 'A', 369.0, 7.6, 2.5, None, None, None, 1.73, None),
    ('A63', 'Harina fortificada con hierro de trigo', 'A', 362.0, 10.5, 2.0, 73.6, 2.7, 36.0, 5.5, 1.8),
    ('A65', 'Harina tostada de trigo (machica)', 'A', 330.0, 7.9, 1.2, 77.2, 2.7, 67.0, 0.9, 2.7),
    ('A158', 'Hojuela de trigo (chaque)', 'A', 322.0, 10.0, 2.5, None, None, None, 2.1, None),
    ('A64', 'Llunka de trigo', 'A', 312.0, 9.1, 1.0, None, None, 60.0, 1.6, 2.0),
    ('A66', 'Mote de trigo sancochado', 'A', 154.0, 2.5, 0.6, None, None, 38.0, 2.5, 0.4),
    ('A69', 'Trigo pelado', 'A', 330.0, 8.4, 1.4, None, None, 51.0, 4.6, None),
    ('A72', 'Sémola de trigo', 'A', 319.0, 7.8, 1.1, 74.5, 3.9, 40.0, 0.8, 0.0),
    ('B3', 'Ají amarillo fresco', 'B', 39.0, 0.9, 0.7, None, None, 31.0, 0.9, 60.0),
    ('B4', 'Ají amarillo fresco, molido sin sal', 'B', 52.0, 1.9, 1.7, None, None, 97.0, 3.5, 16.2),
    ('B5', 'Ají amarillo seco', 'B', 199.0, 7.3, 6.3, 36.1, 28.7, 124.0, 8.2, 6.0),
    ('B12', 'Ají verde', 'B', 57.0, 2.5, 0.8, None, None, 21.0, 1.3, 48.5),
    ('B15', 'Alcachofa', 'B', 24.0, 2.2, 0.2, 4.9, 14.0, 42.0, 1.0, 1.42),
    ('B17', 'Apio, tallo sin hojas', 'B', 8.0, 1.0, 0.2, 1.1, 2.8, 91.0, 1.2, 7.99),
    ('B18', 'Berenjena', 'B', 12.0, 1.0, 0.1, 2.3, 3.6, 20.0, 4.03, 8.82),
    ('B19', 'Berenjena Costeña o tomate de árbol', 'B', 41.0, 1.3, 0.3, None, None, 18.0, 0.2, 2.3),
    ('B21', 'Brocoli', 'B', 32.0, 3.9, 1.3, 3.3, 0.7, 93.0, 0.84, 114.0),
    ('B32', 'Col crespa o repollo sin cogollo', 'B', 15.0, 1.5, 0.3, 2.6, 2.3, 70.0, 0.4, 48.5),
    ('B35', 'Hojas de col', 'B', 32.0, 2.7, 0.6, 5.6, 2.0, 170.0, 0.1, 96.3),
    ('B106', 'Coliflor con tallo y sin hojas', 'B', 20.0, 2.1, 0.6, 2.9, 1.8, None, 0.49, None),
    ('B38', 'Coliflor sin tallo y sin hojas', 'B', 17.0, 2.2, 0.6, 1.9, 2.5, 26.0, 0.6, 75.3),
    ('B39', 'Culantro sin tallo', 'B', 34.0, 3.3, 1.3, 4.2, 2.8, 259.0, 5.3, 37.2),
    ('B107', 'Culantro, con hojas y tallo', 'B', 15.0, 3.5, 0.2, 1.2, 4.7, 135.0, 4.5, 4.78),
    ('B43', 'Esparragos', 'B', 15.0, 2.2, 0.3, 2.1, 1.7, 35.0, 1.33, 2.32),
    ('B44', 'Espinaca blanca', 'B', 24.0, 1.9, 0.6, 4.1, 2.2, 80.0, 4.6, 16.4),
    ('B45', 'Espinaca negra sin tronco', 'B', 24.0, 2.8, 0.9, 2.7, 2.2, 234.0, 4.3, 15.2),
    ('B108', 'Espinaca, hojas sin tallo', 'B', 30.0, 4.8, 1.4, 1.9, 2.8, None, 21.29, None),
    ('B53', 'Lechuga americana', 'B', 7.0, 0.6, 0.1, 1.2, 1.2, 52.0, 0.1, 1.5),
    ('B112', 'Lechuga de seda', 'B', 10.0, 1.3, 0.1, 1.7, 0.6, 39.0, 1.3, 10.0),
    ('B54', 'Lechuga larga', 'B', 12.0, 1.5, 0.2, 1.8, 2.1, 64.0, 1.6, 14.5),
    ('B128', 'Lechuga morada, hojas sin tallo', 'B', 11.0, 1.2, 0.1, 1.9, 0.4, 50.0, 2.27, 23.82),
    ('B55', 'Lechuga redonda', 'B', 8.0, 1.3, 0.2, 0.8, 1.3, 47.0, 1.0, 7.4),
    ('B60', 'Nabo', 'B', 10.0, 0.6, 0.2, 1.8, 1.8, 34.0, 0.1, 21.1),
    ('B61', 'Hojas de nabo', 'B', 24.0, 2.9, 0.4, 3.8, 3.2, 367.0, 2.8, 49.2),
    ('B130', 'Pepinillo japonés con cáscara y pepas', 'B', 7.0, 0.9, 0.0, 1.3, 0.6, 15.0, 0.08, 12.5),
    ('B67', 'Pepinillo sin cáscara', 'B', 9.0, 0.5, 0.1, 1.9, 0.7, 20.0, 0.3, 12.6),
    ('B68', 'Perejil sin tallo', 'B', 41.0, 4.8, 0.7, 6.6, 3.3, 202.0, 8.7, 95.8),
    ('B131', 'Pimiento amarillo', 'B', 24.0, 1.0, 0.2, 5.5, 0.8, 7.0, 0.18, 162.47),
    ('B69', 'Pimiento rojo', 'B', 27.0, 1.2, 1.3, 3.7, 0.9, 12.0, 0.36, 108.3),
    ('B116', 'Pimiento verde', 'B', 19.0, 1.1, 0.1, 4.3, 0.7, 21.0, 0.17, 55.0),
    ('B71', 'Poro sin hojas', 'B', 34.0, 2.7, 0.8, 5.8, 1.8, 78.0, 0.7, 8.6),
    ('B73', 'Rabanitos', 'B', 7.0, 0.8, 0.1, 1.3, 1.6, 36.0, 1.0, 18.6),
    ('B76', 'Rocoto fresco', 'B', 36.0, 1.2, 0.5, None, None, 6.0, 0.5, 14.9),
    ('B78', 'Siuca culantro', 'B', 28.0, 1.9, 0.5, 5.3, 2.8, 195.0, 4.9, 0.7),
    ('B79', 'Tomate', 'B', 15.0, 0.8, 0.2, 3.1, 1.2, 7.0, 0.6, 18.4),
    ('B119', 'Tomate de palito', 'B', 44.0, 1.6, 0.2, None, None, 15.0, 0.8, 4.9),
    ('B80', 'Tomate italiano', 'B', 12.0, 0.8, 0.2, 2.4, 1.2, 7.0, 0.3, 32.5),
    ('B132', 'Tomate italiano, sin pepas, sin cáscara', 'B', 18.0, 0.8, 0.1, 4.2, 0.7, 8.0, 0.12, 32.64),
    ('B120', 'Tomate redondo, con cáscara', 'B', 18.0, 0.7, 0.3, 4.0, 0.7, 24.0, 0.45, 10.18),
    ('B81', 'Salsa de tomate con carne', 'B', 106.0, 2.7, 5.7, None, None, 20.0, 2.1, 9.4),
    ('B83', 'Salsa concentrada de tomate', 'B', 75.0, 2.7, 1.0, None, None, 19.0, 2.9, 26.8),
    ('B82', 'Salsa de tomate', 'B', 18.0, 1.5, 0.7, 2.4, 1.5, 117.0, 3.0, 0.0),
    ('B133', 'Vainita sancochada sin sal', 'B', 17.0, 2.2, 0.1, 3.1, 3.1, 48.0, 1.28, 0.0),
    ('B84', 'Vainitas', 'B', 25.0, 2.4, 0.3, 4.7, 3.4, 88.0, 1.4, 9.6),
    ('B85', 'Zanahoria', 'B', 19.0, 1.0, 0.3, 3.6, 4.1, 51.0, 0.3, 3.23),
    ('B86', 'Harina de zanahoria', 'B', 293.0, 7.3, 1.5, None, None, 418.0, None, 10.0),
    ('C100', 'Aguaymanto', 'C', 51.0, 1.9, 0.0, 12.4, 4.9, 11.0, 1.24, 43.3),
    ('C12', 'Chirimoya', 'C', 72.0, 1.9, 0.3, 17.7, 4.0, 102.0, 0.29, 10.36),
    ('C13', 'Ciruela', 'C', 82.0, 1.0, 0.2, None, None, 20.0, 0.9, 36.8),
    ('C15', 'Agua de coco', 'C', 10.0, 0.7, 0.1, 2.0, 1.1, 21.0, 0.0, 0.8),
    ('C107', 'Néctar envasado de durazno', 'C', 6.0, 0.0, 0.0, 1.4, 1.7, None, 0.05, 5.35),
    ('C7', 'Durazno-Melocotón', 'C', 43.0, 0.8, 0.2, 10.8, 1.6, None, 0.59, 0.77),
    ('C18', 'Fresa', 'C', 34.0, 0.7, 0.8, 6.9, 2.0, 37.0, 1.2, 42.0),
    ('C20', 'Granadilla', 'C', 51.0, 2.5, 2.7, 5.7, 5.8, 17.0, 1.28, 9.88),
    ('C21', 'Jugo enlatado de granadilla', 'C', 62.0, 1.1, 0.0, None, None, 6.0, 0.6, 129.6),
    ('C108', 'Jugo natural de granadilla, sin azúcar', 'C', 25.0, 1.1, 0.2, 5.4, 1.9, 6.0, 0.42, 11.25),
    ('C22', 'Guanábana', 'C', 44.0, 0.9, 0.2, 11.0, 3.3, 38.0, 0.7, 19.0),
    ('C35', 'Lúcuma', 'C', 97.0, 2.1, 0.2, 24.7, 10.2, 16.0, 0.79, 0.77),
    ('C36', 'Harina de lúcuma', 'C', 329.0, 4.0, 2.4, None, None, 92.0, 4.6, 11.6),
    ('C40', 'Mandarina', 'C', 29.0, 0.6, 0.3, 6.8, 1.8, 19.0, 0.3, 48.7),
    ('C41', 'Mango', 'C', 54.0, 0.4, 0.2, 14.1, 1.8, 17.0, 0.4, 24.8),
    ('C152', 'Mango Edward', 'C', 69.0, 0.6, 0.3, 17.9, 0.9, 7.0, 0.08, 61.17),
    ('C86', 'Mango ciruelo o taperibá', 'C', 56.0, 0.6, 0.3, None, None, 39.0, 0.7, 5.9),
    ('C151', 'Mango criollo', 'C', 66.0, 0.4, 0.2, 17.4, 0.3, 6.0, 0.0, 9.6),
    ('C154', 'Mango kafro', 'C', 64.0, 0.7, 0.4, 16.4, 0.5, None, 0.14, 21.3),
    ('C155', 'Mango kent', 'C', 65.0, 0.7, 0.0, 17.5, 0.6, None, 0.17, 14.95),
    ('C113', 'Néctar envasado de mango', 'C', 44.0, 0.0, 0.0, 11.0, 1.5, None, 0.03, 0.94),
    ('C123', 'Jugo natural envasado de maracuyá', 'C', 35.0, None, None, 8.7, 1.4, 11.0, 0.2, 0.0),
    ('C43', 'Jugo puro de maracuyá', 'C', 61.0, 0.9, 0.1, 15.9, 0.2, 13.0, 3.0, 22.0),
    ('C124', 'Néctar envasado de maracuyá', 'C', 9.0, 0.0, 0.0, 2.1, 0.2, None, 0.02, 24.05),
    ('C45', 'Melón', 'C', 21.0, 0.5, 0.1, 5.0, 0.8, 13.0, 0.5, 23.0),
    ('C46', 'Melón enano', 'C', 20.0, 0.6, 0.2, None, None, 23.0, 0.4, 15.3),
    ('C47', 'Membrillo', 'C', 36.0, 0.3, 0.1, 9.6, 1.9, 9.0, 0.7, 12.5),
    ('C48', 'Naranja', 'C', 31.0, 0.6, 0.2, 7.7, 2.4, 23.0, 0.2, 92.3),
    ('C49', 'Jugo de naranja agria', 'C', 32.0, 0.5, 0.2, 8.0, 0.2, 31.0, 0.2, 42.0),
    ('C50', 'Naranja de Guayaquil', 'C', 31.0, 0.5, 0.2, 7.8, 2.4, 37.0, 0.1, 42.2),
    ('C51', 'Naranja de Huando', 'C', 36.0, 1.2, 0.2, 8.5, 2.4, 30.0, 0.1, 43.9),
    ('C128', 'Naranja tangelo', 'C', 24.0, 1.0, 0.2, 5.2, 2.2, None, 0.63, 11.74),
    ('C129', 'Jugo natural de naranja tangelo', 'C', 16.0, 0.7, 0.2, 3.5, 2.4, None, 0.26, 9.16),
    ('C125', 'Bebida envasada de naranja', 'C', 56.0, 0.0, 0.0, 14.0, 0.7, None, 0.02, 52.25),
    ('C126', 'Jugo natural envasado de naranja', 'C', 16.0, None, None, 4.1, 0.9, 10.0, 0.11, 72.94),
    ('C127', 'Néctar envasado de naranja', 'C', 43.0, None, None, 10.7, 1.6, 6.0, 0.38, 17.92),
    ('C131', 'Palta "fuerte"', 'C', 104.0, 1.9, 8.9, 6.5, 10.6, 11.0, 0.49, 3.82),
    ('C161', 'Palta Hass', 'C', 204.0, 1.0, 23.5, 1.0, 6.8, 9.0, 0.57, 0.0),
    ('C59', 'Papaya', 'C', 25.0, 0.4, 0.1, 6.4, 1.8, 23.0, 0.3, 47.7),
    ('C132', 'Papaya arequipeña', 'C', 17.0, 1.0, 0.3, 3.3, 0.5, None, 0.3, 34.45),
    ('C162', 'Néctar natural de papaya, sin azúcar', 'C', 15.0, 0.4, 0.5, 2.4, 0.6, 10.0, 0.14, 12.58),
    ('C133', 'Néctar envasado de pera', 'C', 46.0, 0.0, 0.0, 11.4, 0.0, None, 0.02, 0.81),
    ('C69', 'Piña', 'C', 33.0, 0.4, 0.2, 8.4, 1.4, 10.0, 0.4, 19.9),
    ('C164', 'Piña Golden o baby golden', 'C', 55.0, 0.6, 0.1, 14.3, 1.3, 11.0, 0.18, 53.46),
    ('C165', 'Piña Hawaiana', 'C', 44.0, 0.6, 0.4, 10.7, 1.2, 8.0, 0.19, 32.38),
    ('C166', 'Piña Selva', 'C', 30.0, 0.5, 0.4, 7.1, 2.1, 6.0, 0.15, 29.04),
    ('C167', 'Néctar natural de piña Selva, sin azúcar', 'C', 19.0, 0.2, 0.5, 3.5, 0.0, 2.0, 0.17, 6.52),
    ('C134', 'Bebida envasada de piña', 'C', 29.0, 0.0, 0.0, 7.2, 1.1, None, 0.01, 33.87),
    ('C83', 'Sandia', 'C', 23.0, 0.7, 0.1, 5.5, 0.4, 6.0, 0.3, 3.0),
    ('C170', 'Uva Red Globe con cáscara, sin pepas', 'C', 52.0, 0.6, 0.4, 12.8, 0.8, 11.0, 0.34, 5.65),
    ('C93', 'Uva blanca', 'C', 40.0, 0.3, 0.2, 10.4, 0.9, 5.0, 0.8, 1.4),
    ('C94', 'Uva borgoña', 'C', 79.0, 0.9, 0.3, 20.4, 0.9, 18.0, 1.1, 4.7),
    ('C95', 'Uva italia', 'C', 63.0, 0.4, 0.1, 16.8, 0.9, 19.0, 0.5, 2.8),
    ('C96', 'Uva negra', 'C', 63.0, 0.2, 0.1, 17.2, 0.9, 6.0, 2.2, 2.2),
    ('C97', 'Uva quebranta', 'C', 66.0, 0.5, 0.1, None, None, 14.0, 0.4, 0.7),
    ('D3', 'Aceite vegetal de algodón', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D4', 'Aceite vegetal de girasol', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D43', 'Aceite vegetal de girasol con canola', 'D', 883.0, 0.0, 99.9, None, None, 0.0, 0.0, None),
    ('D6', 'Aceite vegetal de maní', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D5', 'Aceite vegetal de maíz', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D44', 'Aceite vegetal de oliva extravirgen', 'D', 883.0, 0.0, 99.9, None, None, 0.0, 0.0, None),
    ('D7', 'Aceite vegetal de olivo', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D8', 'Aceite vegetal de palma', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D45', 'Aceite vegetal de sacha Inchi', 'D', 883.0, 0.0, 99.9, None, None, 0.0, 0.0, None),
    ('D9', 'Aceite vegetal de soya', 'D', 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D40', 'Semilla de ajonjolí negro', 'D', 501.0, 16.0, 51.3, 3.8, 17.9, 995.0, None, None),
    ('D39', 'Semilla de ajonjolí', 'D', 525.0, 17.7, 49.7, 11.7, 11.8, 975.0, 14.55, 0.0),
    ('D10', 'Almendra', 'D', 554.0, 19.4, 54.1, 8.4, 9.9, 195.0, 3.72, 0.0),
    ('D17', 'Manteca de cerdo', 'D', 879.0, 0.0, 99.4, 0.0, 0.0, 0.0, 0.0, 0.0),
    ('D19', 'Mantequilla', 'D', 729.0, 2.0, 82.0, None, None, 0.0, 0.0, 0.0),
    ('D20', 'Mantequilla con sal', 'D', 717.0, 0.9, 81.1, 0.1, 0.0, 24.0, 0.02, 0.0),
    ('D46', 'Mantequilla sin sal', 'D', 746.0, 0.2, 84.7, None, None, 18.0, 0.08, 0.0),
    ('D21', 'Margarina vegetal con sal', 'D', 720.0, 0.6, 81.0, 0.3, 0.0, 0.0, 0.0, 0.0),
    ('D29', 'Margarina, Dorina Light al 50% de grasa', 'D', 409.0, 0.0, 46.2, None, None, None, None, None),
    ('D31', 'Margarina, La Preferida 70% grasa', 'D', 598.0, 0.0, 67.6, None, None, None, None, None),
    ('D32', 'Margarina, Manty 40% de grasa vegetal', 'D', 325.0, 0.0, 36.8, None, None, None, None, None),
    ('D33', 'Margarina, Sello de Oro', 'D', 607.0, 0.0, 68.6, None, None, None, None, None),
    ('D35', 'Margarina, Swis 60% de grasa', 'D', 479.0, 0.0, 54.1, None, None, None, None, None),
    ('D34', 'Margarina, Swis Light', 'D', 407.0, 0.0, 46.1, None, None, None, None, None),
    ('D37', 'Pecana', 'D', 670.0, 9.1, 73.8, 5.2, 6.5, 43.0, 2.53, 1.0),
    ('E5', 'Camaroncito seco (chino)', 'E', 247.0, 52.3, 1.9, None, None, 524.0, 4.9, 0.0),
    ('E6', 'Camarones frescos', 'E', 88.0, 17.8, 0.2, None, None, 117.0, 0.1, 5.2),
    ('E7', 'Cangrejo', 'E', 94.0, 19.8, 0.6, None, None, 108.0, 0.82, 2.0),
    ('E8', 'Cangrejo cocido', 'E', 97.0, 14.8, 2.9, None, None, 423.0, 4.1, None),
    ('E91', 'Pulpa cocida envasada de choro (mejillón)', 'E', 101.0, 17.2, 1.5, None, None, 58.0, 0.12, None),
    ('E12', 'Concha de abanico', 'E', 92.0, 15.9, 1.8, None, None, 12.0, 0.29, 11.6),
    ('E14', 'Langostino blanco', 'E', 69.0, 14.5, 0.8, None, None, 89.0, 2.03, None),
    ('E77', 'Pescado Tilapia, fresco', 'E', 100.0, 18.4, 2.1, None, None, 23.0, 0.23, 0.0),
    ('E18', 'Pescado anchoveta', 'E', 156.0, 19.1, 8.2, None, None, 77.0, 3.04, 8.7),
    ('E19', 'Pescado atún, en conserva', 'E', 181.0, 22.9, 9.9, None, None, None, None, None),
    ('E21', 'Pescado atún, enlatado en aceite', 'E', 186.0, 26.5, 8.1, None, 0.0, 4.0, 1.2, 0.0),
    ('E20', 'Pescado atún, enlatado en agua', 'E', 116.0, 25.5, 0.8, None, None, 11.0, 1.53, 0.0),
    ('E22', 'Pescado atún, fresco', 'E', 141.0, 23.3, 4.6, None, None, None, None, None),
    ('E27', 'Pescado bonito', 'E', 138.0, 23.4, 4.2, None, None, 28.0, 0.7, 1.6),
    ('E29', 'Pescado bonito fresco, músculo claro', 'E', 115.0, 23.5, 1.3, None, None, 20.0, 1.03, None),
    ('E30', 'Pescado bonito fresco, músculo oscuro', 'E', 106.0, 23.1, 0.7, None, None, 10.0, 1.93, None),
    ('E28', 'Huevera de pescado bonito', 'E', 101.0, 17.2, 3.0, None, None, 24.0, 1.8, 10.1),
    ('E31', 'Pescado bonito, pulpa asada', 'E', 136.0, 24.0, 3.7, None, None, 15.0, 1.0, None),
    ('E32', 'Pescado bonito, seco salado', 'E', 184.0, 32.3, 5.1, None, None, 112.0, 6.1, 0.0),
    ('E34', 'Pescado caballa, en conserva', 'E', 225.0, 24.8, 14.0, None, None, None, None, None),
    ('E35', 'Pescado caballa, fresco', 'E', 182.0, 21.5, 10.0, None, None, 90.0, 1.96, None),
    ('E36', 'Pescado caballa, salado', 'E', 132.0, 21.4, 4.1, None, None, 120.0, 2.45, None),
    ('E47', 'Pescado corvina', 'E', 124.0, 19.5, 4.5, None, 0.0, 57.0, 1.1, 1.5),
    ('E49', 'Pescado jurel, en conserva', 'E', 127.0, 23.2, 3.8, None, None, None, None, None),
    ('E50', 'Pescado jurel, fresco', 'E', 121.0, 22.2, 2.7, None, None, 37.0, 1.56, None),
    ('E51', 'Pescado lenguado', 'E', 91.0, 18.8, 1.2, None, 0.0, 18.0, 0.7, 2.0),
    ('E57', 'Pescado merluza, fresco', 'E', 72.0, 15.8, 0.5, None, None, 15.0, 0.2, 1.0),
    ('E58', 'Pescado merluza, seco', 'E', 363.0, 73.8, 5.3, None, None, None, None, None),
    ('E63', 'Pescado pejerrey', 'E', 105.0, 19.6, 2.4, None, None, 105.0, 0.7, 0.0),
    ('E81', 'Pescado trucha rosada', 'E', 110.0, 20.9, 2.3, None, None, 8.0, 0.2, 8.4),
    ('E82', 'Pescado trucha, en conserva', 'E', 167.0, 21.5, 9.0, None, None, None, None, None),
    ('E83', 'Pescado trucha, fresca', 'E', 111.0, 19.5, 3.1, None, None, 19.0, 0.22, 1.0),
    ('E89', 'Concentrado proteico de pota', 'E', 396.0, 91.8, 0.3, None, None, None, None, None),
    ('E90', 'Pulpo', 'E', 80.0, 13.6, 1.4, None, None, 53.0, 3.0, 3.2),
    ('E92', 'Mezcla de mariscos: mejillones, caracol y concha de abanico', 'E', 80.0, 15.3, 0.9, None, None, 29.0, 0.06, None),
    ('F61', 'Carne pulpa de alpaca', 'F', 109.0, 24.1, 0.5, None, None, 11.0, 2.2, 7.0),
    ('F13', 'Carne de cerdo sin hueso', 'F', 198.0, 14.4, 15.1, 0.1, 0.0, 12.0, 1.3, 0.6),
    ('F14', 'Hígado de cerdo', 'F', 128.0, 18.5, 4.7, 1.7, 0.0, 17.0, 6.2, 9.8),
    ('F49', 'Chorizo', 'F', 287.0, 21.0, 21.9, 0.0, 0.0, 56.0, 4.0, 0.0),
    ('F72', 'Pierna cruda de cordero', 'F', 128.0, 20.6, 4.5, 0.0, 0.0, 6.0, 1.82, 0.0),
    ('F74', 'Carne de cuy', 'F', 96.0, 19.0, 1.6, 0.1, 0.0, 29.0, 1.9, 0.0),
    ('F20', 'Pechuga de gallina sin piel', 'F', 108.0, 19.2, 2.9, 0.0, 0.0, 5.0, 0.8, 4.4),
    ('F21', 'Pierna de gallina sin piel', 'F', 120.0, 20.6, 3.6, 0.0, 0.0, 9.0, 0.9, 4.7),
    ('F58', 'Hot Dog', 'F', 364.0, 11.0, 34.3, None, None, 76.0, 1.3, 0.0),
    ('F50', 'Jamón del país', 'F', 344.0, 24.7, 26.4, 0.0, 0.0, 48.0, 2.1, 0.0),
    ('F25', 'Carne de pavo', 'F', 160.0, 20.4, 8.0, 0.0, 0.0, 15.0, 3.8, 0.0),
    ('F118', 'Pechuga de pavo con piel', 'F', 94.0, 17.7, 1.3, None, None, 21.0, 0.31, None),
    ('F119', 'Pierna de pavo con piel', 'F', 105.0, 16.4, 2.6, None, None, 115.0, 1.2, None),
    ('F26', 'Pollo, carne pulpa', 'F', 119.0, 21.4, 3.1, 0.0, 0.0, 12.0, 1.5, 2.3),
    ('F89', 'Carne molida de res, cruda', 'F', 164.0, 21.0, 8.3, None, None, 13.0, 1.95, 0.0),
    ('F35', 'Carne pulpa de res', 'F', 105.0, 21.3, 1.6, 0.0, 0.0, 16.0, 3.4, 0.0),
    ('F38', 'Hígado de res', 'F', 140.0, 20.0, 4.6, 3.3, 0.0, 13.0, 5.4, 19.5),
    ('F95', 'Lengua cocida de res', 'F', 269.0, 16.6, 18.2, None, None, 18.0, 2.4, 0.0),
    ('F39', 'Lengua de res', 'F', 173.0, 16.5, 11.2, 0.3, 0.0, 9.0, 2.2, 1.9),
    ('F56', 'Salchicha blanca chica', 'F', 449.0, 12.0, 43.2, 2.0, 0.0, 22.0, 3.2, 2.3),
    ('F57', 'Salchicha blanca grande', 'F', 363.0, 13.6, 32.3, 3.5, 0.0, 76.0, 1.2, 2.5),
    ('F59', 'Salchicha de "Huacho"', 'F', 461.0, 12.9, 44.0, 2.4, 0.0, 80.0, 5.5, 0.0),
    ('F60', 'Tocino', 'F', 493.0, 13.5, 47.9, 0.8, 0.0, 26.0, 1.2, 1.9),
    ('F134', 'Tocino, sancochado', 'F', 350.0, 25.0, 27.0, None, None, 21.0, 1.6, None),
    ('G1', 'Crema de leche espesa', 'G', 345.0, 2.1, 37.0, 2.8, 0.0, 65.0, 0.1, 0.6),
    ('G2', 'Crema de leche rala (líquida)', 'G', 195.0, 2.7, 19.3, 3.7, 0.0, 96.0, 0.1, 0.8),
    ('G4', 'Leche en polvo descremada', 'G', 362.0, 36.2, 0.8, 52.0, 0.0, 1257.0, 1.2, 6.8),
    ('G5', 'Leche en polvo entera', 'G', 484.0, 27.0, 26.1, 36.1, 0.0, 848.0, 0.2, 9.0),
    ('G6', 'Leche evaporada descremada', 'G', 79.0, 7.1, 0.9, 10.5, 0.0, None, None, 13.0),
    ('G7', 'Leche evaporada entera', 'G', 133.0, 6.3, 7.7, 10.9, 0.0, 231.0, None, 0.0),
    ('G8', 'Leche fresca con menos de 1% de grasa', 'G', 43.0, 3.5, 1.0, 4.7, 0.0, 130.0, 0.05, 5.2),
    ('G10', 'Leche fresca de cabra', 'G', 66.0, 3.2, 3.8, 5.0, 0.0, 171.0, None, 0.0),
    ('G11', 'Leche fresca de vaca', 'G', 63.0, 3.1, 3.5, 4.9, 0.0, 106.0, 1.3, 0.5),
    ('G21', 'Leche fresca de vaca descremada', 'G', 30.0, 2.5, 0.0, 5.0, 0.0, None, None, None),
    ('G9', 'Leche fresca entera (Plusa)', 'G', 64.0, 3.2, 3.2, 5.1, 0.0, 106.0, 0.3, 0.5),
    ('G30', 'Queso edam', 'G', 330.0, 24.4, 25.3, None, None, 935.0, 0.31, 0.64),
    ('G13', 'Queso fresco de cabra', 'G', 173.0, 16.3, 10.3, 3.4, 0.0, 310.0, 0.8, 0.0),
    ('G14', 'Queso fresco de vaca', 'G', 265.0, 17.2, 20.2, 3.6, 0.0, 1105.0, 0.14, 0.64),
    ('G15', 'Queso mantecoso', 'G', 322.0, 19.5, 26.5, None, None, 266.0, 0.39, 0.64),
    ('G16', 'Queso parmesano duro', 'G', 440.0, 39.1, 30.3, 1.8, 0.0, 1260.0, 0.6, 0.0),
    ('G26', 'Yogurt bebible de fresa', 'G', 78.0, 2.7, 1.2, None, None, 127.0, 0.08, None),
    ('G17', 'Yogurt de leche entera', 'G', 61.0, 3.5, 3.3, 4.7, 0.0, 121.0, 0.05, 0.53),
    ('G19', 'Yogurt frutado de leche descremada', 'G', 95.0, 4.4, 0.2, 19.0, 0.0, 152.0, 0.07, 0.7),
    ('G37', 'Yogurt griego descremado con fresas', 'G', 74.0, 4.2, 0.3, 14.0, 1.0, 151.0, 0.07, 0.64),
    ('G38', 'Yogurt griego natural sin azúcar', 'G', 79.0, 4.0, 3.9, 7.2, 0.7, 126.0, 0.03, 0.64),
    ('G20', 'Yogurt natural de leche descremada', 'G', 56.0, 5.7, 0.2, 7.7, 0.0, 199.0, 0.09, 0.9),
    ('H16', 'Café sin azúcar', 'H', 2.0, 0.1, 0.0, 0.6, 0.0, 4.0, 0.2, 0.0),
    ('H21', 'Refresco de carambola con azúcar', 'H', 30.0, 0.0, 0.0, 7.3, 0.1, None, 0.22, None),
    ('H23', 'Refresco de cebada con azúcar', 'H', 22.0, 0.1, 0.0, 5.4, 0.0, None, 0.08, None),
    ('H1', 'Cerveza', 'H', 36.0, 0.3, 0.0, 5.1, 0.0, 0.0, 0.1, 0.0),
    ('H29', 'Refresco de manzana con azúcar', 'H', 34.0, 0.1, 0.1, 8.2, 0.0, None, 0.08, None),
    ('H30', 'Refresco de maracuyá con azúcar', 'H', 34.0, 0.1, 0.2, 7.9, 0.0, None, 0.21, None),
    ('J4', 'Huevo de gallina entero crudo', 'J', 166.0, 12.7, 11.1, None, None, 29.0, 2.6, None),
    ('J2', 'Clara de huevo de gallina', 'J', 51.0, 10.9, 0.2, 0.7, 0.0, 7.0, 0.08, 0.0),
    ('J5', 'Yema de huevo de gallina', 'J', 354.0, 15.6, 30.9, 1.9, 0.0, 136.0, 4.3, 0.0),
    ('K2', 'Azúcar rubia', 'K', 380.0, 0.0, 0.0, 97.5, 0.0, 45.0, 1.7, 0.0),
    ('K4', 'Miel de abeja', 'K', 330.0, 0.0, 0.0, 85.4, 0.2, 26.0, 0.4, 1.3),
    ('L1', 'Achiote seco', 'L', 388.0, 11.3, 5.3, None, None, 11.0, 5.6, 0.0),
    ('L4', 'Café grano sin tostar', 'L', 203.0, 11.7, 10.8, None, None, 120.0, 2.9, None),
    ('L38', 'Chocolate simple con azúcar (para taza)', 'L', 248.0, 3.8, 16.8, None, None, 46.0, 2.8, 0.0),
    ('L23', 'Levadura fresca para pan', 'L', 113.0, 13.4, 0.3, None, None, 20.0, 2.3, None),
    ('L24', 'Levadura seca', 'L', 359.0, 41.6, 1.2, None, None, 47.0, 9.8, None),
    ('L42', 'Mayonesa envasada con sal', 'L', 390.0, 0.9, 33.4, 23.9, 0.0, 14.0, 0.2, 0.0),
    ('L12', 'Té hojas secas', 'L', 308.0, 8.0, 4.0, None, None, 400.0, 11.9, 5.0),
    ('L50', 'Vinagre', 'L', 21.0, 0.0, 0.0, 6.0, 0.0, 7.0, 0.5, 0.0),
    ('Q1', 'Fórmula infantil maternizada Al 110', 'Q', 502.0, 14.0, 25.0, None, None, 450.0, 6.0, 40.0),
    ('Q2', 'Cereal infantil Cerelac sabor manzana', 'Q', 414.0, 11.0, 7.4, None, None, 275.0, 6.3, 20.0),
    ('Q3', 'Cereal infantil Cerelac de trigo', 'Q', 425.0, 11.5, 7.8, None, None, 275.0, 6.3, 20.0),
    ('Q4', 'Fórmula infantil maternizada Eledón', 'Q', 417.0, 27.9, 12.0, 49.8, 0.0, 1070.0, 0.4, 10.4),
    ('Q5', 'Fórmula infantil maternizada Nan', 'Q', 509.0, 11.4, 26.0, None, None, 320.0, 6.0, 41.0),
    ('Q6', 'Cereal infantil Nestúm, cereal mixto', 'Q', 380.0, 9.4, 1.2, None, None, 690.0, 15.6, 45.0),
    ('Q7', 'Cereal infantil Nestúm, tres cereales', 'Q', 376.0, 10.7, 2.4, None, None, 690.0, 14.7, 45.0),
    ('Q8', 'Fórmula infantil maternizada Pelargón', 'Q', 458.0, 16.5, 17.1, None, None, 590.0, 6.0, 37.0),
    ('T3', 'Arveja, seca sin cáscara', 'T', 247.0, 21.7, 3.2, 35.6, 25.5, 65.0, 2.6, 3.5),
    ('T15', 'Frejol canario', 'T', 236.0, 21.9, 2.1, 35.0, 25.1, 138.0, 6.6, 6.3),
    ('T16', 'Frejol canario cocido', 'T', 43.0, 5.2, 0.5, 5.1, 10.4, 45.0, 1.6, 0.0),
    ('T18', 'Frejol canario serranito', 'T', 238.0, 19.2, 1.8, 38.4, 24.9, 149.0, 4.0, 4.5),
    ('T17', 'Frejol canario fresco (frejol verde)', 'T', 102.0, 9.7, 0.6, 15.6, 14.0, 60.0, 2.18, 5.22),
    ('T20', 'Frejol castilla', 'T', 227.0, 23.3, 2.7, 30.5, 26.4, 97.0, 6.65, 2.1),
    ('T64', 'Frejol castilla sancochado sin sal', 'T', 119.0, 10.1, 1.8, 17.1, 5.6, 39.0, 3.18, 0.0),
    ('T26', 'Frejol negro', 'T', 270.0, 18.2, 1.3, 48.2, 15.2, 133.0, 9.3, 2.3),
    ('T69', 'Frejol negro sancochado sin sal', 'T', 104.0, 9.8, 1.7, 13.8, 9.1, 64.0, 2.3, 0.0),
    ('T30', 'Frejol palo fresco (lenteja verde)', 'T', 82.0, 7.0, 0.8, 12.5, 10.7, 114.0, 1.09, 7.06),
    ('T31', 'Frejol panamito', 'T', 235.0, 21.5, 1.7, 35.8, 24.9, 174.0, 6.3, 5.8),
    ('T71', 'Frejol panamito sancochado sin sal', 'T', 106.0, 9.5, 1.4, 15.1, 10.3, 78.0, 1.95, 0.0),
    ('T44', 'Garbanzo', 'T', 293.0, 17.6, 5.4, 45.9, 17.4, 120.0, 5.95, 5.4),
    ('T43', 'Garbanzo, cocido', 'T', 127.0, 6.9, 2.5, 20.2, 7.6, 54.0, 1.9, 0.0),
    ('T52', 'Lentejas chicas', 'T', 211.0, 22.6, 1.0, 30.5, 30.5, 73.0, 7.6, 5.5),
    ('T53', 'Lentejas chicas cocidas', 'T', 65.0, 6.4, 0.1, 10.4, 7.9, 43.0, 1.7, 0.0),
    ('T54', 'Lentejas grandes', 'T', 214.0, 23.2, 1.1, 30.5, 30.5, 71.0, 4.8, 4.4),
    ('T58', 'Pallar cocido, con cáscara', 'T', 94.0, 7.7, 0.8, 14.9, 7.0, 28.0, 1.28, 0.1),
    ('T83', 'Pallar del río Manú', 'T', 329.0, 22.0, 0.9, None, None, 186.0, 4.0, 2.9),
    ('T55', 'Pallar morado', 'T', 259.0, 20.0, 1.3, 43.8, 19.0, 51.0, 3.8, 0.0),
    ('T56', 'Pallar seco', 'T', 253.0, 20.4, 1.2, 42.4, 19.0, 70.0, 6.7, 7.5),
    ('T57', 'Pallar sin cáscara', 'T', 260.0, 21.6, 1.4, 42.6, 19.0, 38.0, 5.2, 0.0),
    ('U3', 'Camote amarillo sin cáscara', 'U', 95.0, 2.0, 0.0, 20.5, 2.9, 41.0, 0.43, 22.46),
    ('U4', 'Camote blanco', 'U', 114.0, 1.7, 0.1, None, None, 26.0, 2.5, 12.9),
    ('U41', 'Camote de Huarayoc', 'U', 106.0, 1.6, 0.2, None, None, 6.0, 0.5, 12.0),
    ('U42', 'Camote deshidratado', 'U', 333.0, 3.7, 0.7, None, None, 120.0, 2.9, 0.8),
    ('U43', 'Camote deshidratado tratado con lejía', 'U', 327.0, 5.3, 0.8, None, None, 73.0, 1.9, 0.5),
    ('U5', 'Camote morado sin cáscara', 'U', 105.0, 1.4, 0.3, None, None, 36.0, 1.4, 13.6),
    ('U6', 'Harina de camote', 'U', 341.0, 2.1, 0.9, 81.3, 3.0, 153.0, 5.7, 7.9),
    ('U13', 'Maca, afrechillo', 'U', 316.0, 10.5, 0.6, None, None, 475.0, 29.3, 2.0),
    ('U14', 'Maca, almidón', 'U', 350.0, 6.1, 1.2, None, None, 175.0, 31.7, 2.8),
    ('U47', 'Harina de maca', 'U', 328.0, 8.7, 4.1, 70.3, 8.6, 61.0, 7.97, None),
    ('U15', 'Maca, pasta integral', 'U', 310.0, 14.0, 1.0, None, None, 245.0, 25.0, 8.0),
    ('U16', 'Mashua o isaño', 'U', 32.0, 0.7, 0.1, 7.7, 2.9, None, 0.37, 42.06),
    ('U17', 'Olluco sin cáscara', 'U', 59.0, 1.1, 0.1, None, None, 3.0, 1.1, 11.5),
    ('U38', 'Harina de yuca', 'U', 333.0, 0.3, 0.1, 82.1, 0.1, 155.0, 1.31, 13.6),
]

FOOD_COLS = ["codigo", "nombre", "grupo_cod", "kcal", "proteinas", "grasas", "cho", "fibra", "calcio", "hierro", "vitc"]
FOOD_DB = [dict(zip(FOOD_COLS, fila)) for fila in FOOD_DB_RAW]

# Traducción de TODOS los nombres de alimentos de la Base Peruana (343 alimentos) al inglés.
# Cubre el 100% de FOOD_DB_RAW (verificado por script), incluyendo nombres con nomenclatura
# propia peruana (quinua, palta, camote, olluco, mashua, rocoto, choclo, etc.), que también
# se traducen para que la Food Library quede completamente en inglés cuando ese es el idioma
# activo. Los valores nutricionales de FOOD_DB permanecen exactamente iguales; solo cambia
# el nombre mostrado.
FOOD_NOMBRE_EN = {
    "Aceite vegetal de algodón": "Cottonseed Vegetable Oil",
    "Aceite vegetal de girasol": "Sunflower Vegetable Oil",
    "Aceite vegetal de girasol con canola": "Sunflower and Canola Vegetable Oil",
    "Aceite vegetal de maní": "Peanut Vegetable Oil",
    "Aceite vegetal de maíz": "Corn Vegetable Oil",
    "Aceite vegetal de oliva extravirgen": "Extra Virgin Olive Oil",
    "Aceite vegetal de olivo": "Olive Vegetable Oil",
    "Aceite vegetal de palma": "Palm Vegetable Oil",
    "Aceite vegetal de sacha Inchi": "Sacha Inchi Vegetable Oil",
    "Aceite vegetal de soya": "Soybean Vegetable Oil",
    "Achiote seco": "Dried Annatto",
    "Afrecho de quinua": "Quinoa Bran",
    "Agua de coco": "Coconut Water",
    "Aguaymanto": "Cape Gooseberry (Goldenberry)",
    "Ají amarillo fresco": "Fresh Yellow Chili Pepper",
    "Ají amarillo fresco, molido sin sal": "Fresh Yellow Chili Pepper, Ground without Salt",
    "Ají amarillo seco": "Dried Yellow Chili Pepper",
    "Ají verde": "Green Chili Pepper",
    "Alcachofa": "Artichoke",
    "Almendra": "Almond",
    "Apio, tallo sin hojas": "Celery, Stalk without Leaves",
    "Arroz blanco corriente": "Common White Rice",
    "Arroz pilado o pulido cocido": "Cooked Milled Rice",
    "Arveja, seca sin cáscara": "Pea, Dried without Shell",
    "Avena envasada": "Packaged Oats",
    "Azúcar rubia": "Brown Sugar",
    "Bebida envasada de naranja": "Packaged Orange Drink",
    "Bebida envasada de piña": "Packaged Pineapple Drink",
    "Berenjena": "Eggplant",
    "Berenjena Costeña o tomate de árbol": "Coastal Eggplant or Tree Tomato",
    "Brocoli": "Broccoli",
    "Café grano sin tostar": "Unroasted Coffee Beans",
    "Café sin azúcar": "Coffee, No Sugar",
    "Camaroncito seco (chino)": "Dried Small Shrimp (Chinese)",
    "Camarones frescos": "Fresh Shrimp",
    "Camote amarillo sin cáscara": "Yellow Sweet Potato, Peeled",
    "Camote blanco": "White Sweet Potato",
    "Camote de Huarayoc": "Huarayoc Sweet Potato",
    "Camote deshidratado": "Dehydrated Sweet Potato",
    "Camote deshidratado tratado con lejía": "Dehydrated Sweet Potato Treated with Lye",
    "Camote morado sin cáscara": "Purple Sweet Potato, Peeled",
    "Cangrejo": "Crab",
    "Cangrejo cocido": "Cooked Crab",
    "Carne de cerdo sin hueso": "Boneless Pork",
    "Carne de cuy": "Guinea Pig Meat",
    "Carne de pavo": "Turkey Meat",
    "Carne molida de res, cruda": "Ground Beef, Raw",
    "Carne pulpa de alpaca": "Alpaca Meat (Boneless)",
    "Carne pulpa de res": "Beef (Boneless)",
    "Cebada con cáscara": "Barley with Husk",
    "Cebada pelada para mote": "Peeled Barley for Mote",
    "Cebada perlada o resbalada cocida": "Cooked Pearl Barley",
    "Cebada perlada o resbalada cruda": "Raw Pearl Barley",
    "Cebada tostada y molida (chaquepa)": "Toasted and Ground Barley (Chaquepa)",
    "Cebada tostada, harina integral": "Toasted Barley, Whole Flour",
    "Cereal infantil Cerelac de trigo": "Cerelac Wheat Infant Cereal",
    "Cereal infantil Cerelac sabor manzana": "Cerelac Apple-Flavored Infant Cereal",
    "Cereal infantil Nestúm, cereal mixto": "Nestúm Mixed Grain Infant Cereal",
    "Cereal infantil Nestúm, tres cereales": "Nestúm Three-Grain Infant Cereal",
    "Cerveza": "Beer",
    "Chirimoya": "Custard Apple (Cherimoya)",
    "Chocolate simple con azúcar (para taza)": "Plain Chocolate with Sugar (Drinking)",
    "Chorizo": "Chorizo",
    "Ciruela": "Plum",
    "Clara de huevo de gallina": "Chicken Egg White",
    "Col crespa o repollo sin cogollo": "Curly Cabbage or Headless Cabbage",
    "Coliflor con tallo y sin hojas": "Cauliflower with Stem, without Leaves",
    "Coliflor sin tallo y sin hojas": "Cauliflower without Stem or Leaves",
    "Concentrado proteico de pota": "Jumbo Squid Protein Concentrate",
    "Concha de abanico": "Scallop",
    "Crema de leche espesa": "Thick Cream",
    "Crema de leche rala (líquida)": "Light (Liquid) Cream",
    "Culantro sin tallo": "Cilantro without Stem",
    "Culantro, con hojas y tallo": "Cilantro, with Leaves and Stem",
    "Durazno-Melocotón": "Peach",
    "Esparragos": "Asparagus",
    "Espinaca blanca": "White Spinach",
    "Espinaca negra sin tronco": "Black Spinach without Stem",
    "Espinaca, hojas sin tallo": "Spinach, Leaves without Stem",
    "Fideo crudo fortificado con hierro": "Raw Iron-Fortified Noodles",
    "Fideo tallarín crudo fortificado con hierro": "Raw Iron-Fortified Spaghetti Noodles",
    "Frejol canario": "Canary Bean",
    "Frejol canario cocido": "Cooked Canary Bean",
    "Frejol canario fresco (frejol verde)": "Fresh Canary Bean (Green Bean)",
    "Frejol canario serranito": "Serranito Canary Bean",
    "Frejol castilla": "Castilla Bean",
    "Frejol castilla sancochado sin sal": "Boiled Castilla Bean, No Salt",
    "Frejol negro": "Black Bean",
    "Frejol negro sancochado sin sal": "Boiled Black Bean, No Salt",
    "Frejol palo fresco (lenteja verde)": "Fresh Pigeon Pea (Green Lentil)",
    "Frejol panamito": "Panamito Bean",
    "Frejol panamito sancochado sin sal": "Boiled Panamito Bean, No Salt",
    "Fresa": "Strawberry",
    "Fórmula infantil maternizada Al 110": "Al 110 Infant Formula",
    "Fórmula infantil maternizada Eledón": "Eledón Infant Formula",
    "Fórmula infantil maternizada Nan": "Nan Infant Formula",
    "Fórmula infantil maternizada Pelargón": "Pelargón Infant Formula",
    "Galleta de soda (San Jorge)": "Soda Cracker (San Jorge)",
    "Galleta de soda (salada)": "Soda Cracker (Salted)",
    "Galleta de vainilla (Field)": "Vanilla Cookie (Field)",
    "Galleta de vainilla (dulce)": "Vanilla Cookie (Sweet)",
    "Garbanzo": "Chickpea",
    "Garbanzo, cocido": "Chickpea, Cooked",
    "Granadilla": "Granadilla (Sweet Passion Fruit)",
    "Guanábana": "Soursop",
    "Harina de camote": "Sweet Potato Flour",
    "Harina de lúcuma": "Lúcuma Flour",
    "Harina de maca": "Maca Flour",
    "Harina de maíz morado (api)": "Purple Corn Flour (Api)",
    "Harina de quinua": "Quinoa Flour",
    "Harina de yuca": "Cassava Flour",
    "Harina de zanahoria": "Carrot Flour",
    "Harina fortificada con hierro de trigo": "Iron-Fortified Wheat Flour",
    "Harina tostada de trigo (machica)": "Toasted Wheat Flour (Machica)",
    "Hojas de col": "Cabbage Leaves",
    "Hojas de nabo": "Turnip Greens",
    "Hojuela cocida de avena": "Cooked Oat Flakes",
    "Hojuela cruda de avena": "Raw Oat Flakes",
    "Hojuela de quinua": "Quinoa Flakes",
    "Hojuela de trigo (chaque)": "Wheat Flakes (Chaque)",
    "Hojuela precocida de avena con quinua": "Precooked Oat and Quinoa Flakes",
    "Hot Dog": "Hot Dog",
    "Huevera de pescado bonito": "Bonito Fish Roe",
    "Huevo de gallina entero crudo": "Whole Raw Chicken Egg",
    "Hígado de cerdo": "Pork Liver",
    "Hígado de res": "Beef Liver",
    "Jamón del país": "Local Cooked Ham",
    "Jugo de naranja agria": "Sour Orange Juice",
    "Jugo enlatado de granadilla": "Canned Granadilla Juice",
    "Jugo natural de granadilla, sin azúcar": "Natural Granadilla Juice, No Sugar",
    "Jugo natural de naranja tangelo": "Natural Tangelo Orange Juice",
    "Jugo natural envasado de maracuyá": "Bottled Natural Passion Fruit Juice",
    "Jugo natural envasado de naranja": "Bottled Natural Orange Juice",
    "Jugo puro de maracuyá": "Pure Passion Fruit Juice",
    "Kiwicha, achita o achis o amaranto": "Kiwicha (Amaranth)",
    "Langostino blanco": "White Prawn",
    "Leche en polvo descremada": "Skim Milk Powder",
    "Leche en polvo entera": "Whole Milk Powder",
    "Leche evaporada descremada": "Skim Evaporated Milk",
    "Leche evaporada entera": "Whole Evaporated Milk",
    "Leche fresca con menos de 1% de grasa": "Fresh Milk with Less than 1% Fat",
    "Leche fresca de cabra": "Fresh Goat Milk",
    "Leche fresca de vaca": "Fresh Cow Milk",
    "Leche fresca de vaca descremada": "Fresh Skim Cow Milk",
    "Leche fresca entera (Plusa)": "Fresh Whole Milk (Plusa)",
    "Lechuga americana": "Iceberg Lettuce",
    "Lechuga de seda": "Silk Lettuce",
    "Lechuga larga": "Romaine Lettuce",
    "Lechuga morada, hojas sin tallo": "Purple Lettuce, Leaves without Stem",
    "Lechuga redonda": "Round (Butterhead) Lettuce",
    "Lengua cocida de res": "Cooked Beef Tongue",
    "Lengua de res": "Beef Tongue",
    "Lentejas chicas": "Small Lentils",
    "Lentejas chicas cocidas": "Cooked Small Lentils",
    "Lentejas grandes": "Large Lentils",
    "Levadura fresca para pan": "Fresh Bread Yeast",
    "Levadura seca": "Dry Yeast",
    "Llunka de cebada (morón americano)": "Barley Llunka (American Morón)",
    "Llunka de trigo": "Wheat Llunka",
    "Lúcuma": "Lúcuma",
    "Maca, afrechillo": "Maca, Bran",
    "Maca, almidón": "Maca, Starch",
    "Maca, pasta integral": "Maca, Whole Paste",
    "Mandarina": "Tangerine",
    "Mango": "Mango",
    "Mango Edward": "Edward Mango",
    "Mango ciruelo o taperibá": "Plum Mango (Taperibá)",
    "Mango criollo": "Criollo Mango",
    "Mango kafro": "Kafro Mango",
    "Mango kent": "Kent Mango",
    "Manteca de cerdo": "Pork Lard",
    "Mantequilla": "Butter",
    "Mantequilla con sal": "Salted Butter",
    "Mantequilla sin sal": "Unsalted Butter",
    "Margarina vegetal con sal": "Salted Vegetable Margarine",
    "Margarina, Dorina Light al 50% de grasa": "Margarine, Dorina Light 50% Fat",
    "Margarina, La Preferida 70% grasa": "Margarine, La Preferida 70% Fat",
    "Margarina, Manty 40% de grasa vegetal": "Margarine, Manty 40% Vegetable Fat",
    "Margarina, Sello de Oro": "Margarine, Sello de Oro",
    "Margarina, Swis 60% de grasa": "Margarine, Swis 60% Fat",
    "Margarina, Swis Light": "Margarine, Swis Light",
    "Mashka o machica de cebada (harina de cebada tostada)": "Mashka (Toasted Barley Flour)",
    "Mashua o isaño": "Mashua (Andean Tuber)",
    "Mayonesa envasada con sal": "Packaged Mayonnaise with Salt",
    "Maíz, grano fresco (choclo)": "Corn, Fresh Kernel (Choclo)",
    "Melón": "Melon (Cantaloupe)",
    "Melón enano": "Dwarf Melon",
    "Membrillo": "Quince",
    "Mezcla de mariscos: mejillones, caracol y concha de abanico": "Seafood Mix: Mussels, Sea Snail and Scallop",
    "Miel de abeja": "Honey",
    "Mote de trigo sancochado": "Boiled Wheat Mote",
    "Nabo": "Turnip",
    "Naranja": "Orange",
    "Naranja de Guayaquil": "Guayaquil Orange",
    "Naranja de Huando": "Huando Orange",
    "Naranja tangelo": "Tangelo Orange",
    "Néctar envasado de durazno": "Packaged Peach Nectar",
    "Néctar envasado de mango": "Packaged Mango Nectar",
    "Néctar envasado de maracuyá": "Packaged Passion Fruit Nectar",
    "Néctar envasado de naranja": "Packaged Orange Nectar",
    "Néctar envasado de pera": "Packaged Pear Nectar",
    "Néctar natural de papaya, sin azúcar": "Natural Papaya Nectar, No Sugar",
    "Néctar natural de piña Selva, sin azúcar": "Natural Selva Pineapple Nectar, No Sugar",
    "Olluco sin cáscara": "Olluco, Peeled",
    "Pallar cocido, con cáscara": "Cooked Lima Bean, with Skin",
    "Pallar del río Manú": "Manú River Lima Bean",
    "Pallar morado": "Purple Lima Bean",
    "Pallar seco": "Dried Lima Bean",
    "Pallar sin cáscara": "Lima Bean, Peeled",
    "Palta \"fuerte\"": "\"Fuerte\" Avocado",
    "Palta Hass": "Hass Avocado",
    "Pan cuay de trigo de Carhuaz": "Carhuaz Wheat \"Cuay\" Bread",
    "Pan cuay de trigo de Huaraz": "Huaraz Wheat \"Cuay\" Bread",
    "Pan de cebada (serrano)": "Barley Bread (Highland-style)",
    "Pan de molde": "Sliced Bread",
    "Pan de molde integral": "Whole Wheat Sliced Bread",
    "Pan de quinua de Lima": "Lima Quinoa Bread",
    "Pan de trigo artesanal de Carhuaz": "Carhuaz Artisanal Wheat Bread",
    "Pan francés fortificado con hierro": "Iron-Fortified French Bread",
    "Pan integral": "Whole Wheat Bread",
    "Papaya": "Papaya",
    "Papaya arequipeña": "Arequipa Papaya",
    "Pecana": "Pecan",
    "Pechuga de gallina sin piel": "Skinless Chicken Breast",
    "Pechuga de pavo con piel": "Turkey Breast with Skin",
    "Pepinillo japonés con cáscara y pepas": "Japanese Cucumber, with Skin and Seeds",
    "Pepinillo sin cáscara": "Cucumber, Peeled",
    "Perejil sin tallo": "Parsley without Stem",
    "Pescado Tilapia, fresco": "Fresh Tilapia",
    "Pescado anchoveta": "Anchovy",
    "Pescado atún, en conserva": "Canned Tuna",
    "Pescado atún, enlatado en aceite": "Tuna, Canned in Oil",
    "Pescado atún, enlatado en agua": "Tuna, Canned in Water",
    "Pescado atún, fresco": "Fresh Tuna",
    "Pescado bonito": "Bonito Fish",
    "Pescado bonito fresco, músculo claro": "Fresh Bonito, Light Muscle",
    "Pescado bonito fresco, músculo oscuro": "Fresh Bonito, Dark Muscle",
    "Pescado bonito, pulpa asada": "Bonito, Roasted Flesh",
    "Pescado bonito, seco salado": "Bonito, Dried and Salted",
    "Pescado caballa, en conserva": "Canned Mackerel",
    "Pescado caballa, fresco": "Fresh Mackerel",
    "Pescado caballa, salado": "Salted Mackerel",
    "Pescado corvina": "Corvina (Sea Bass)",
    "Pescado jurel, en conserva": "Canned Jack Mackerel",
    "Pescado jurel, fresco": "Fresh Jack Mackerel",
    "Pescado lenguado": "Sole (Flatfish)",
    "Pescado merluza, fresco": "Fresh Hake",
    "Pescado merluza, seco": "Dried Hake",
    "Pescado pejerrey": "Silverside Fish",
    "Pescado trucha rosada": "Pink Trout",
    "Pescado trucha, en conserva": "Canned Trout",
    "Pescado trucha, fresca": "Fresh Trout",
    "Pierna cruda de cordero": "Raw Leg of Lamb",
    "Pierna de gallina sin piel": "Skinless Chicken Leg",
    "Pierna de pavo con piel": "Turkey Leg with Skin",
    "Pimiento amarillo": "Yellow Bell Pepper",
    "Pimiento rojo": "Red Bell Pepper",
    "Pimiento verde": "Green Bell Pepper",
    "Piña": "Pineapple",
    "Piña Golden o baby golden": "Golden Pineapple (Baby Golden)",
    "Piña Hawaiana": "Hawaiian Pineapple",
    "Piña Selva": "Selva Pineapple",
    "Pollo, carne pulpa": "Chicken, Boneless Meat",
    "Poro sin hojas": "Leek without Leaves",
    "Pulpa cocida envasada de choro (mejillón)": "Cooked Packaged Mussel Meat",
    "Pulpo": "Octopus",
    "Queso edam": "Edam Cheese",
    "Queso fresco de cabra": "Fresh Goat Cheese",
    "Queso fresco de vaca": "Fresh Cow Cheese",
    "Queso mantecoso": "Creamy Cheese",
    "Queso parmesano duro": "Hard Parmesan Cheese",
    "Quinua": "Quinoa",
    "Quinua blanca (Junín)": "White Quinoa (Junín)",
    "Quinua blanca (Puno)": "White Quinoa (Puno)",
    "Quinua cocida": "Cooked Quinoa",
    "Quinua dulce, blanca (Junín)": "Sweet White Quinoa (Junín)",
    "Quinua dulce, blanca (Puno)": "Sweet White Quinoa (Puno)",
    "Quinua dulce, rosada (Junín)": "Sweet Pink Quinoa (Junín)",
    "Quinua rosada (Puno)": "Pink Quinoa (Puno)",
    "Quinua, variedad Ayara (Puno)": "Quinoa, Ayara Variety (Puno)",
    "Quinua, variedad CICA-127 (Puno)": "Quinoa, CICA-127 Variety (Puno)",
    "Quinua, variedad CICA-18 (Puno)": "Quinoa, CICA-18 Variety (Puno)",
    "Quinua, variedad Choclito (Puno)": "Quinoa, Choclito Variety (Puno)",
    "Quinua, variedad Chullpi- roja (Puno)": "Quinoa, Red Chullpi Variety (Puno)",
    "Quinua, variedad Cuchiwilla (Puno)": "Quinoa, Cuchiwilla Variety (Puno)",
    "Quinua, variedad Misa Jiura (Puno)": "Quinoa, Misa Jiura Variety (Puno)",
    "Quinua, variedad Pasankalla-roja (Puno)": "Quinoa, Red Pasankalla Variety (Puno)",
    "Quinua, variedad Q' OITU-negra (Puno)": "Quinoa, Black Q'oitu Variety (Puno)",
    "Quinua, variedad Wariponcho (Puno)": "Quinoa, Wariponcho Variety (Puno)",
    "Quinua, variedad Witulla (Puno)": "Quinoa, Witulla Variety (Puno)",
    "Quinua, variedad blanca de Juli (Puno)": "Quinoa, White Juli Variety (Puno)",
    "Quinua, variedad real": "Quinoa, Royal Variety",
    "Rabanitos": "Radishes",
    "Refresco de carambola con azúcar": "Sweetened Starfruit Refreshment",
    "Refresco de cebada con azúcar": "Sweetened Barley Refreshment",
    "Refresco de manzana con azúcar": "Sweetened Apple Refreshment",
    "Refresco de maracuyá con azúcar": "Sweetened Passion Fruit Refreshment",
    "Rocoto fresco": "Fresh Rocoto Pepper",
    "Salchicha blanca chica": "Small White Sausage",
    "Salchicha blanca grande": "Large White Sausage",
    "Salchicha de \"Huacho\"": "\"Huacho\" Sausage",
    "Salsa concentrada de tomate": "Concentrated Tomato Sauce",
    "Salsa de tomate": "Tomato Sauce",
    "Salsa de tomate con carne": "Tomato Sauce with Meat",
    "Sandia": "Watermelon",
    "Semilla de ajonjolí": "Sesame Seed",
    "Semilla de ajonjolí negro": "Black Sesame Seed",
    "Siuca culantro": "Siuca Cilantro (Long Coriander)",
    "Sémola de quinua": "Quinoa Semolina",
    "Sémola de trigo": "Wheat Semolina",
    "Tocino": "Bacon",
    "Tocino, sancochado": "Bacon, Boiled",
    "Tomate": "Tomato",
    "Tomate de palito": "Cherry Tomato (on the Vine)",
    "Tomate italiano": "Italian Tomato",
    "Tomate italiano, sin pepas, sin cáscara": "Italian Tomato, Seedless and Peeled",
    "Tomate redondo, con cáscara": "Round Tomato, with Skin",
    "Trigo": "Wheat",
    "Trigo para mote pelado cocido": "Cooked Peeled Wheat for Mote",
    "Trigo para mote pelado crudo": "Raw Peeled Wheat for Mote",
    "Trigo pelado": "Peeled Wheat",
    "Trigo resbalado cocido": "Cooked Rolled Wheat",
    "Trigo resbalado crudo": "Raw Rolled Wheat",
    "Trigo sin tostar (chaquepa)": "Untoasted Wheat (Chaquepa)",
    "Trigo tostado (chaquepa)": "Toasted Wheat (Chaquepa)",
    "Té hojas secas": "Dried Tea Leaves",
    "Uva Red Globe con cáscara, sin pepas": "Red Globe Grape, with Skin, Seedless",
    "Uva blanca": "White Grape",
    "Uva borgoña": "Burgundy Grape",
    "Uva italia": "Italia Grape",
    "Uva negra": "Black Grape",
    "Uva quebranta": "Quebranta Grape",
    "Vainita sancochada sin sal": "Boiled Green Bean, No Salt",
    "Vainitas": "Green Beans",
    "Vinagre": "Vinegar",
    "Yema de huevo de gallina": "Chicken Egg Yolk",
    "Yogurt bebible de fresa": "Strawberry Drinkable Yogurt",
    "Yogurt de leche entera": "Whole Milk Yogurt",
    "Yogurt frutado de leche descremada": "Fruit-Flavored Skim Milk Yogurt",
    "Yogurt griego descremado con fresas": "Skim Greek Yogurt with Strawberries",
    "Yogurt griego natural sin azúcar": "Plain Greek Yogurt, No Sugar",
    "Yogurt natural de leche descremada": "Plain Skim Milk Yogurt",
    "Zanahoria": "Carrot",
}


def _nombre_alimento(nombre):
    """Devuelve el nombre del alimento en el idioma actual. Cuando el idioma activo es
    English, traduce usando FOOD_NOMBRE_EN (cobertura completa de los 343 alimentos de
    FOOD_DB); en Español devuelve el nombre original tal cual está en la base."""
    if st.session_state.get("idioma", "Español") == "English":
        return FOOD_NOMBRE_EN.get(nombre, nombre)
    return nombre

GRUPOS_ALIMENTOS = {
    "A": {"nombre": "Cereales y derivados", "icono": "🥖",
          "aporta": "Aportan energía y carbohidratos complejos, base de la alimentación diaria.",
          "tips": ["Prefiere las versiones integrales.", "Combina con verduras y una fuente de proteína.",
                    "Modera la porción si tu objetivo es bajar de peso.", "Evita el exceso de harinas refinadas."]},
    "B": {"nombre": "Verduras y hortalizas", "icono": "🥬",
          "aporta": "Ricas en fibra, vitaminas y minerales; bajas en calorías.",
          "tips": ["Llena la mitad de tu plato con verduras.", "Varía los colores para más variedad de nutrientes.",
                    "Prefiérelas crudas, al vapor o salteadas.", "Lávalas bien antes de consumir."]},
    "C": {"nombre": "Frutas y derivados", "icono": "🍎",
          "aporta": "Fuente natural de vitaminas, fibra y antioxidantes.",
          "tips": ["Consume frutas enteras, no solo en jugo.", "Prefiere frutas de temporada.",
                    "No reemplaces el agua por jugos.", "Incluye variedad de colores."]},
    "D": {"nombre": "Grasas, aceites y oleaginosas", "icono": "🥑",
          "aporta": "Aportan energía concentrada y ácidos grasos esenciales.",
          "tips": ["Usa aceites vegetales con moderación.", "Prefiere grasas no saturadas (palta, frutos secos).",
                    "Evita frituras frecuentes.", "Controla el tamaño de la porción."]},
    "E": {"nombre": "Pescados y mariscos", "icono": "🐟",
          "aporta": "Proteína de alto valor biológico y ácidos grasos omega-3.",
          "tips": ["Prefiere cocción al vapor, horno o plancha.", "Incluye pescado azul 2 a 3 veces por semana.",
                    "Modera la sal al preparar.", "Verifica su frescura antes de comprar."]},
    "F": {"nombre": "Carnes y derivados", "icono": "🥩",
          "aporta": "Fuente principal de proteína de alto valor biológico y hierro.",
          "tips": ["Prefiere carnes magras.", "Retira la grasa visible.",
                    "Evita frituras frecuentes.", "Combina con verduras."]},
    "G": {"nombre": "Leches y derivados", "icono": "🥛",
          "aporta": "Aportan calcio, proteína y vitaminas para huesos y músculos.",
          "tips": ["Prefiere versiones bajas en grasa.", "Aportan calcio para huesos y dientes.",
                    "Evita las versiones con exceso de azúcar.", "Modera los quesos maduros por su sodio."]},
    "H": {"nombre": "Bebidas", "icono": "🥤",
          "aporta": "Hidratan, aunque algunas aportan azúcares y calorías extra.",
          "tips": ["El agua debe ser tu bebida principal.", "Modera bebidas azucaradas y alcohólicas.",
                    "Revisa el contenido de azúcar añadida.", "Prefiere jugos naturales sin azúcar agregada."]},
    "J": {"nombre": "Huevos y derivados", "icono": "🍳",
          "aporta": "Proteína completa y nutrientes esenciales como colina y vitamina D.",
          "tips": ["Prefiere cocción con poco aceite.", "Combínalo con verduras.",
                    "Modera el consumo si tienes indicación médica.", "Consérvalo refrigerado."]},
    "K": {"nombre": "Productos azucarados", "icono": "🍯",
          "aporta": "Aportan energía rápida, con poco valor nutricional adicional.",
          "tips": ["Consume con moderación.", "Prefiere endulzantes naturales en poca cantidad.",
                    "Evita el consumo diario.", "Revisa etiquetas de azúcares añadidos."]},
    "L": {"nombre": "Misceláneos", "icono": "🧂",
          "aporta": "Ingredientes complementarios: condimentos, infusiones y otros.",
          "tips": ["Usa la sal con moderación.", "Prefiere infusiones sin azúcar añadida.",
                    "Cuida la porción al usar condimentos.", "Úsalos como complemento, no como base del plato."]},
    "Q": {"nombre": "Alimentos infantiles", "icono": "🍼",
          "aporta": "Formulados para cubrir necesidades específicas en la primera infancia.",
          "tips": ["Usa solo según indicación del pediatra o nutricionista.", "Respeta las porciones por edad.",
                    "No reemplaces la lactancia materna sin indicación médica.", "Verifica la fecha de vencimiento."]},
    "T": {"nombre": "Leguminosas y derivados", "icono": "🫘",
          "aporta": "Buena fuente de proteína vegetal, fibra y hierro.",
          "tips": ["Combínalas con cereales para una proteína más completa.", "Ayudan a la saciedad por su fibra.",
                    "Remójalas antes de cocinar para mejorar la digestión.", "Inclúyelas varias veces por semana."]},
    "U": {"nombre": "Tubérculos, raíces y derivados", "icono": "🥔",
          "aporta": "Fuente de energía y carbohidratos, con vitaminas y minerales.",
          "tips": ["Prefiere sancochado o al vapor antes que frito.", "Modera la porción si buscas bajar de peso.",
                    "Consúmelos con cáscara bien lavada cuando sea posible.", "Combina con proteínas y verduras."]},
}

GRUPOS_ALIMENTOS_EN = {
    "A": {"nombre": "Cereals and Derivatives", "icono": "🥖",
          "aporta": "Provide energy and complex carbohydrates, the base of daily eating.",
          "tips": ["Choose whole-grain versions.", "Combine with vegetables and a protein source.",
                    "Moderate the portion if your goal is to lose weight.", "Avoid excess refined flours."]},
    "B": {"nombre": "Vegetables", "icono": "🥬",
          "aporta": "Rich in fiber, vitamins, and minerals; low in calories.",
          "tips": ["Fill half your plate with vegetables.", "Vary the colors for a wider range of nutrients.",
                    "Prefer them raw, steamed, or sautéed.", "Wash them well before eating."]},
    "C": {"nombre": "Fruits and Derivatives", "icono": "🍎",
          "aporta": "A natural source of vitamins, fiber, and antioxidants.",
          "tips": ["Eat whole fruit, not just juice.", "Prefer seasonal fruit.",
                    "Don't replace water with juice.", "Include a variety of colors."]},
    "D": {"nombre": "Fats, Oils and Oilseeds", "icono": "🥑",
          "aporta": "Provide concentrated energy and essential fatty acids.",
          "tips": ["Use vegetable oils in moderation.", "Prefer unsaturated fats (avocado, nuts).",
                    "Avoid frequent fried foods.", "Watch your portion size."]},
    "E": {"nombre": "Fish and Seafood", "icono": "🐟",
          "aporta": "High biological value protein and omega-3 fatty acids.",
          "tips": ["Prefer steaming, baking, or grilling.", "Include oily fish 2 to 3 times a week.",
                    "Moderate the salt when preparing it.", "Check its freshness before buying."]},
    "F": {"nombre": "Meat and Meat Products", "icono": "🥩",
          "aporta": "Main source of high biological value protein and iron.",
          "tips": ["Prefer lean cuts.", "Remove visible fat.",
                    "Avoid frequent fried foods.", "Combine with vegetables."]},
    "G": {"nombre": "Milk and Dairy Products", "icono": "🥛",
          "aporta": "Provide calcium, protein, and vitamins for bones and muscles.",
          "tips": ["Prefer low-fat versions.", "They provide calcium for bones and teeth.",
                    "Avoid versions with excess sugar.", "Moderate aged cheeses due to their sodium."]},
    "H": {"nombre": "Beverages", "icono": "🥤",
          "aporta": "Provide hydration, although some add extra sugars and calories.",
          "tips": ["Water should be your main beverage.", "Moderate sugary and alcoholic drinks.",
                    "Check the added-sugar content.", "Prefer natural juices with no added sugar."]},
    "J": {"nombre": "Eggs and Egg Products", "icono": "🍳",
          "aporta": "Complete protein and essential nutrients like choline and vitamin D.",
          "tips": ["Prefer cooking with little oil.", "Combine it with vegetables.",
                    "Moderate intake if you have a medical indication.", "Keep it refrigerated."]},
    "K": {"nombre": "Sugary Products", "icono": "🍯",
          "aporta": "Provide quick energy, with little additional nutritional value.",
          "tips": ["Consume in moderation.", "Prefer natural sweeteners in small amounts.",
                    "Avoid daily consumption.", "Check labels for added sugars."]},
    "L": {"nombre": "Miscellaneous", "icono": "🧂",
          "aporta": "Complementary ingredients: condiments, infusions, and others.",
          "tips": ["Use salt in moderation.", "Prefer infusions without added sugar.",
                    "Watch the portion when using condiments.", "Use them as a complement, not as the base of the meal."]},
    "Q": {"nombre": "Infant Foods", "icono": "🍼",
          "aporta": "Formulated to meet specific needs during early childhood.",
          "tips": ["Use only as directed by a pediatrician or nutritionist.", "Follow age-appropriate portions.",
                    "Don't replace breastfeeding without medical guidance.", "Check the expiration date."]},
    "T": {"nombre": "Legumes and Derivatives", "icono": "🫘",
          "aporta": "A good source of plant protein, fiber, and iron.",
          "tips": ["Combine with cereals for more complete protein.", "They help with satiety thanks to their fiber.",
                    "Soak them before cooking to improve digestion.", "Include them several times a week."]},
    "U": {"nombre": "Tubers, Roots and Derivatives", "icono": "🥔",
          "aporta": "A source of energy and carbohydrates, with vitamins and minerals.",
          "tips": ["Prefer boiled or steamed over fried.", "Moderate the portion if you're aiming to lose weight.",
                    "Eat them with the well-washed skin when possible.", "Combine with protein and vegetables."]},
}

def _grupo_campo(cod, campo):
    """Devuelve el campo (nombre/icono/aporta/tips) de un grupo de alimentos en el idioma
    actual, usando GRUPOS_ALIMENTOS_EN cuando corresponde."""
    fuente = GRUPOS_ALIMENTOS_EN if st.session_state.get("idioma", "Español") == "English" else GRUPOS_ALIMENTOS
    return fuente.get(cod, GRUPOS_ALIMENTOS.get(cod, {})).get(campo)

GRUPOS_COLORES = {
    "A": ("#FF9500", "#FFF3E5"), "B": ("#34C759", "#EAFAEE"), "C": ("#FF3B30", "#FFEDEC"),
    "D": ("#AF52DE", "#F6ECFC"), "E": ("#30B0C7", "#E6F7FA"), "F": ("#8E4A2E", "#F5E9E3"),
    "G": ("#5AC8FA", "#E9F8FF"), "H": ("#32ADE6", "#E7F6FD"), "J": ("#FFCC00", "#FFFAE0"),
    "K": ("#FF2D55", "#FFEBF0"), "L": ("#8E8E93", "#F2F2F7"), "Q": ("#BF5AF2", "#F7ECFD"),
    "T": ("#00C7BE", "#E1FBF9"), "U": ("#A2845E", "#F3ECE4"),
}

def _limpiar_nombre_alimento(nombre):
    """Limpia nombres para la vista del buscador: quita asteriscos de nota al pie
    sueltos y espacios repetidos, sin alterar el dato original de la base."""
    import re
    n = (nombre or "").strip()
    n = re.sub(r'\*+\s*$', '', n).strip()
    n = re.sub(r'\s{2,}', ' ', n)
    return n

GUIAS_ALIMENTARIAS_PERU = [
    ("🥦", "Llena la mitad de tu plato con verduras.", "En cada comida principal."),
    ("🍎", "Consume frutas todos los días.", "Enteras, mejor que en jugo."),
    ("🥛", "Incluye lácteos según tu edad.", "Prefiere las versiones bajas en grasa."),
    ("🫘", "Prefiere alimentos naturales.", "Menos ultraprocesados, más alimentos frescos."),
    ("💧", "El agua es tu bebida principal.", "Evita reemplazarla por bebidas azucaradas."),
    ("🏃", "Realiza actividad física.", "Al menos 30 minutos la mayoría de días."),
]

GUIAS_ALIMENTARIAS_PERU_EN = [
    ("🥦", "Fill half your plate with vegetables.", "At every main meal."),
    ("🍎", "Eat fruit every day.", "Whole fruit is better than juice."),
    ("🥛", "Include dairy according to your age.", "Prefer low-fat versions."),
    ("🫘", "Prefer natural foods.", "Fewer ultra-processed foods, more fresh foods."),
    ("💧", "Water is your main beverage.", "Avoid replacing it with sugary drinks."),
    ("🏃", "Get physical activity.", "At least 30 minutes most days."),
]


def _norm_txt(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


def buscar_alimentos(consulta, limite=12):
    q = _norm_txt(consulta).strip()
    if not q:
        return []
    idioma_en = st.session_state.get("idioma", "Español") == "English"
    exact, word_start, word_mid, contains = [], [], [], []
    for f in FOOD_DB:
        # Nombre en el idioma activo (lo que el usuario espera buscar/ver) y nombre en el
        # otro idioma como respaldo, para que la búsqueda funcione escriba lo que escriba
        # (p. ej. "chicken" o "pollo" encuentran el mismo alimento, sin importar el idioma).
        n_primario = _norm_txt(FOOD_NOMBRE_EN.get(f["nombre"], f["nombre"]) if idioma_en else f["nombre"])
        n_alterno = _norm_txt(f["nombre"] if idioma_en else FOOD_NOMBRE_EN.get(f["nombre"], f["nombre"]))
        n = n_primario if q in n_primario else (n_alterno if q in n_alterno else n_primario)
        if n == q:
            exact.append((0, f))
            continue
        if n.startswith(q):
            word_start.append((0, f))
            continue
        idx = n.find(q)
        if idx == -1:
            continue
        # ¿coincide con el inicio de una palabra? (tras espacio, coma o inicio)
        es_inicio_palabra = idx == 0 or n[idx - 1] in " ,("
        if es_inicio_palabra:
            word_mid.append((idx, f))
        else:
            contains.append((idx, f))
    word_mid.sort(key=lambda t: (t[0], t[1]["nombre"]))
    contains.sort(key=lambda t: (t[0], t[1]["nombre"]))
    orden = [f for _, f in exact] + [f for _, f in word_start] + [f for _, f in word_mid] + [f for _, f in contains]
    return orden[:limite]

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
    5:  ("5", "Control de Peso",                              "🎯", "#FF2D55", "#FFEBF0"),  # systemPink
    6:  ("6", "Plan Nutricional Basado en la OMS",             "⚖️", "#FFCC00", "#FFFAE0"),  # systemYellow
    7:  ("7", "Cálculo de las Porciones del Día",            "⏰", "#30B0C7", "#E6F7FA"),  # systemTeal
    8:  ("8", "Biblioteca Alimentaria",                         "🥗", "#00C7BE", "#E1FBF9"),  # systemMint
    9:  ("9", "Plan de Dieta Semanal",                        "🍱", "#FF6B35", "#FFEEE6"),  # naranja cálido
    10: ("10", "¿El Clima Influye en tu Gasto Energético?",  "🌤️", "#FFB300", "#FFF6E0"),  # amarillo sol
    11: ("Aporte 1", "Energía durante el Embarazo",             "👶", "#BF5AF2", "#F7ECFD"),  # púrpura claro
    12: ("Aporte 2", "Hora Límite para Consumir Cafeína",     "🌙", "#1B2A4A", "#FFF4DE"),  # azul noche + amarillo café
    13: ("13", "¿Cómo cambiaría tu peso?",                    "🎯", "#5AC8FA", "#E9F8FF"),  # celeste claro
    14: ("14", "Mi Reporte de Resultados",                    "📄", "#32ADE6", "#E7F6FD"),  # systemCyan
    15: ("", "Sobre Nosotras",                                 "🎓", "#FF2D55", "#FFEBF0"),  # systemPink
}

COLORES_EN = {
    0:  ("0", "Enter your data!",                            "📝", "#007AFF", "#EAF3FF"),
    1:  ("1", "Blood Test",                                  "🩸", "#FF3B30", "#FFEDEC"),
    2:  ("2", "Body Mass Index and Percentile",              "⚖️", "#AF52DE", "#F6ECFC"),
    3:  ("3", "Basal Metabolic Rate (BMR)",                  "⚡", "#FF9500", "#FFF3E5"),
    4:  ("4", "Daily Caloric Requirement (DCR)",             "🔥", "#34C759", "#EAFAEE"),
    5:  ("5", "Weight Control",                              "🎯", "#FF2D55", "#FFEBF0"),
    6:  ("6", "WHO Macronutrient Plan",                      "⚖️", "#FFCC00", "#FFFAE0"),
    7:  ("7", "Daily Portions Calculation",                  "⏰", "#30B0C7", "#E6F7FA"),
    8:  ("8", "Food Library",                                "🥗", "#00C7BE", "#E1FBF9"),
    9:  ("9", "Weekly Diet Plan",                             "🍱", "#FF6B35", "#FFEEE6"),
    10: ("10", "Does Climate Affect Your Energy Expenditure?", "🌤️", "#FFB300", "#FFF6E0"),
    11: ("Bonus 1", "Energy During Pregnancy",                 "👶", "#BF5AF2", "#F7ECFD"),
    12: ("Bonus 2", "Caffeine Cut-Off Time",                  "🌙", "#1B2A4A", "#FFF4DE"),
    13: ("13", "How Would Your Weight Change?",               "🎯", "#5AC8FA", "#E9F8FF"),
    14: ("14", "My Results Report",                           "📄", "#32ADE6", "#E7F6FD"),
    15: ("", "About Us",                                       "🎓", "#FF2D55", "#FFEBF0"),
}

# Etiqueta/badge corta que acompaña cada encabezado de sección (reemplaza el prefijo "Hoja N:")
BADGE_HOJAS = {
    0: "Configuración", 1: "Módulo Clínico", 2: "Módulo Clínico", 3: "Módulo Energético",
    4: "Módulo Energético", 5: "Control de Peso", 6: "Módulo Nutricional", 7: "Módulo Nutricional",
    8: "Recurso Externo", 9: "Plan Alimenticio", 10: "Módulo Climático", 11: "Aporte Especial",
    12: "Aporte Especial", 13: "Proyección", 14: "Reporte Final", 15: "Equipo",
}

BADGE_HOJAS_EN = {
    0: "Setup", 1: "Clinical Module", 2: "Clinical Module", 3: "Energy Module",
    4: "Energy Module", 5: "Weight Control", 6: "Nutrition Module", 7: "Nutrition Module",
    8: "External Resource", 9: "Meal Plan", 10: "Climate Module", 11: "Special Bonus",
    12: "Special Bonus", 13: "Projection", 14: "Final Report", 15: "Team",
}

# Colores base del sistema iOS, reutilizados para mantener coherencia visual en toda la app.
IOS_BLUE, IOS_GREEN, IOS_RED, IOS_ORANGE = "#007AFF", "#34C759", "#FF3B30", "#FF9500"
IOS_GRAY_BG, IOS_LABEL, IOS_SECONDARY = "#F2F2F7", "#1C1C1E", "#6C6C70"

# =========================================================================================
# ESTILOS GLOBALES
# =========================================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Nunito:wght@400;600;700;800;900&display=swap');

/* =========================================================================================
   SISTEMA VISUAL ESTILO iOS — tipografía San Francisco, esquinas "continuas" muy redondeadas,
   tarjetas sobre fondo gris agrupado (#F2F2F7), acentos de los colores del sistema de iOS,
   y controles con la pulcritud de Ajustes / Salud / Recordatorios de Apple.
   Tipografía redonda (Nunito/Poppins) para el sistema de "Bento Grid" de tarjetas nuevas.
   ========================================================================================= */

:root {
    /* Paleta verde institucional (reemplaza la paleta azul de iOS por el Brand Green del proyecto) */
    --ios-blue: #1E5631; --ios-green: #34C759; --ios-red: #C0392B; --ios-orange: #E67E22;
    --ios-yellow: #FFCC00; --ios-purple: #AF52DE; --ios-pink: #FF2D55; --ios-teal: #30B0C7;
    --ios-indigo: #5856D6; --ios-gray: #8E8E93; --ios-gray-bg: #F7F9F7; --ios-card: #FFFFFF;
    --ios-label: #17301F; --ios-secondary: #5C6B60;
    --ios-radius-lg: 26px; --ios-radius-md: 20px; --ios-radius-sm: 14px;
    --brand-green: #1E5631; --accent-green: #4CAF50; --tint-green: #F4F9F4;
    --font-round: 'Nunito', 'Poppins', -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    /* Design tokens del "Bento Grid" (tarjetas pastel redondeadas) */
    --bento-radius: 22px; --bento-radius-lg: 24px; --bento-pill: 50px;
    --bento-shadow: 0 8px 24px -4px rgba(149,157,165,0.16);
    --bmi-blue: #42A5F5; --bmi-green: #34C759; --bmi-orange: #FF9F43; --bmi-red: #FF5C7C;
    --girl-pink: #FCE4EC; --girl-pink-dark: #C2185B;
    --boy-blue: #E3F2FD; --boy-blue-dark: #1976D2;
}

html, body, [class*="css"], .stApp {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                 "Helvetica Neue", "Inter", "Segoe UI", Roboto, sans-serif !important;
    color: var(--ios-label);
    letter-spacing: -0.01em;
}

/* Las tarjetas nuevas tipo Bento Grid usan la tipografía redonda Nunito/Poppins */
.bento-card, .bento-card * { font-family: var(--font-round) !important; }

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

/* ---------- Wizard/Stepper: diferenciar botones "activos" (primary) de "inactivos" (secondary) ---------- */
div[data-testid="stButton"] button[kind="secondary"] {
    background: #EAEFEA !important;
    color: var(--brand-green) !important;
    box-shadow: none !important;
    border: 1px solid rgba(30,86,49,0.14) !important;
    font-weight: 600 !important;
    transform: none !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(30,86,49,0.12) !important;
    transform: scale(1.01) !important;
}
div[data-testid="stButton"] button[kind="primary"] {
    background: var(--brand-green) !important;
    color: #FFFFFF !important;
    box-shadow: 0 6px 16px rgba(30,86,49,0.32) !important;
}
.stepper-wrap div[data-testid="stButton"] button {
    font-size: 0.86rem !important;
    padding: 14px 10px !important;
    white-space: normal !important;
    line-height: 1.25 !important;
}
.subtabs-wrap div[data-testid="stButton"] button {
    font-size: 0.8rem !important;
    padding: 8px 10px !important;
    white-space: normal !important;
    line-height: 1.2 !important;
}

/* ---------- Navegación lateral tipo "Pills" (sidebar, 15 secciones siempre visibles) ---------- */
.sidebar-nav-title {
    font-weight: 800; color: var(--brand-green); font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.06em; margin: 2px 0 6px 4px; display:flex; align-items:center; gap:6px;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 14px !important;
    font-size: 0.83rem !important;
    padding: 9px 14px !important;
    margin-bottom: 3px !important;
    white-space: normal !important;
    line-height: 1.25 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"] {
    background: #FFFFFF !important;
    color: var(--ios-label) !important;
    border: 1px solid rgba(30,86,49,0.10) !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(30,86,49,0.08) !important;
    border-color: rgba(30,86,49,0.22) !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-green) 0%, #2E7D32 100%) !important;
    color: #FFFFFF !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 12px rgba(30,86,49,0.35) !important;
    border: 1px solid transparent !important;
}

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

/* ---------- Hoja 5: Control de Peso — tarjetas creativas, misión y glassmorphism ---------- */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&display=swap');

@keyframes cp5-fadeup {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
.cp5-card {
    border-radius: 22px; padding: 20px 20px; height: 100%;
    color: white; position: relative; overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    animation: cp5-fadeup 0.6s ease both;
    box-shadow: 0 10px 26px rgba(0,0,0,0.16);
}
.cp5-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 18px 36px rgba(0,0,0,0.26);
}
.cp5-card .cp5-icon { width: 54px; height: 54px; margin-bottom: 8px; }
.cp5-card .cp5-title { font-weight: 800; font-size: 1.08rem; margin-bottom: 6px; letter-spacing: -0.01em; }
.cp5-card .cp5-text { font-size: 0.86rem; line-height: 1.5; opacity: 0.96; }
.cp5-card.cp5-selected { outline: 3px solid rgba(255,255,255,0.85); box-shadow: 0 0 0 5px rgba(255,255,255,0.18), 0 18px 36px rgba(0,0,0,0.26); }

.cp5-mission-wrap {
    background: linear-gradient(180deg,#0B1220 0%,#111A2E 100%);
    border-radius: 28px; padding: 26px 24px; margin-bottom: 6px;
}
.cp5-mission-card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px; padding: 18px 22px; margin-bottom: 14px;
    backdrop-filter: blur(10px); animation: cp5-fadeup 0.7s ease both;
}
.cp5-mission-card.cp5-active { border: 1.5px solid var(--mc-accent); box-shadow: 0 0 24px var(--mc-glow); }
.cp5-mission-title {
    font-family: 'Orbitron', sans-serif; font-weight: 800; letter-spacing: 0.02em;
    font-size: 1.05rem; color: var(--mc-accent); margin-bottom: 10px;
}
.cp5-timeline-track { position: relative; height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); margin: 14px 0 6px 0; }
.cp5-timeline-fill { position: absolute; top:0; left:0; height:100%; border-radius: 999px; }
.cp5-timeline-flag { position: absolute; top: -22px; font-size: 1.05rem; transform: translateX(-50%); }
.cp5-timeline-labels { display:flex; justify-content:space-between; font-size:0.72rem; color:#8892A6; margin-top:2px; }

.cp5-glass-flow {
    display:flex; align-items:center; gap: 14px; flex-wrap: wrap;
}
.cp5-flow-card {
    flex:1; min-width: 190px; border-radius: 22px; padding: 18px 20px;
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    background: rgba(255,255,255,0.55); border: 1px solid rgba(255,255,255,0.6);
    box-shadow: 0 8px 24px rgba(30,86,49,0.10);
}
.cp5-flow-arrow { font-size: 1.8rem; color: #1E5631; opacity: 0.55; }
.cp5-flow-label { font-size: 0.78rem; color: #5C6B60; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; }
.cp5-flow-value { font-size: 1.7rem; font-weight: 800; color: #17301F; letter-spacing: -0.02em; margin: 2px 0 4px 0; }
.cp5-flow-legend { font-size: 0.78rem; color: #5C6B60; line-height: 1.35; }

.cp5-progressbar-track { width:100%; height:22px; border-radius:999px; background:#EEF2EE; overflow:hidden; position:relative; }
.cp5-progressbar-fill { height:100%; border-radius:999px; display:flex; align-items:center; }

/* =========================================================================================
   BENTO GRID — tarjetas KPI (gauge IMC, percentil, alerta de categoría) de la Hoja 2
   ========================================================================================= */
.bento-card {
    background: #FFFFFF; border-radius: var(--bento-radius); padding: 20px 22px; height: 100%;
    box-shadow: var(--bento-shadow); border: 1px solid rgba(0,0,0,0.04);
}
.bento-eyebrow {
    color: #8A94A6; font-size: 0.76rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 2px;
}
.bento-pill {
    display: inline-block; border-radius: var(--bento-pill); padding: 5px 14px;
    font-weight: 800; font-size: 0.78rem; letter-spacing: 0.01em;
}
.gauge-needle-pivot { transform-box: fill-box; transform-origin: center; }

/* ---------- Tabla de rangos de IMC ("Categorías Generales de IMC") ---------- */
.imc-table-wrap {
    border-radius: var(--bento-radius-lg); overflow: hidden; box-shadow: var(--bento-shadow);
    border: 1px solid rgba(0,0,0,0.05); background: #FFFFFF; margin-bottom: 10px;
    font-family: var(--font-round);
}
.imc-table-topbar {
    display: flex; align-items: center; gap: 16px; padding: 18px 24px 8px 24px; position: relative;
}
.imc-table-icon {
    width: 48px; height: 48px; border-radius: 14px; background: #F3EAF7; display: flex;
    align-items: center; justify-content: center; font-size: 1.5rem; flex-shrink: 0;
}
.imc-table-title { font-weight: 800; font-size: 1.35rem; color: #6A1B9A; letter-spacing: -0.01em; }
.imc-table-sub { font-size: 0.82rem; color: #8A94A6; margin-top: 2px; max-width: 520px; }
.imc-table-head {
    background: #9C6FC9; color: #FFFFFF; margin-top: 14px;
    padding: 12px 24px; display: grid; grid-template-columns: 1.6fr 1fr 2fr; gap: 18px;
}
.imc-table-head span { font-weight: 800; font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.04em; }
.imc-row {
    display: grid; grid-template-columns: 1.6fr 1fr 2fr; gap: 18px; align-items: center;
    padding: 14px 24px;
}
.imc-row:nth-child(even) { background: #FAFAFC; }
.imc-clasif-avatar {
    width: 40px; height: 40px; border-radius: 50%; display: inline-flex; align-items: center;
    justify-content: center; font-size: 1.15rem; margin-right: 12px; flex-shrink: 0;
}
.imc-clasif-title { font-weight: 800; font-size: 0.94rem; }
.imc-clasif-sub { font-size: 0.76rem; color: #8A94A6; margin-top: 1px; }
.imc-range-num { font-weight: 800; font-size: 0.95rem; }
.imc-line-track { position: relative; width: 100%; height: 4px; border-radius: 4px; background: #E6E6EC; margin-top: 6px; }
.imc-line-seg { position: absolute; top: 0; height: 4px; border-radius: 4px; }
.imc-line-dot { position: absolute; top: -4px; width: 12px; height: 12px; border-radius: 50%; border: 2.5px solid #FFFFFF; box-shadow: 0 0 0 1.5px currentColor; }
.imc-line-vals { position: relative; height: 16px; margin-top: 2px; font-size: 0.72rem; font-weight: 800; }
.imc-line-vals span.val-mark { position: absolute; transform: translateX(-50%); }
.imc-scale-ends { display: flex; justify-content: space-between; font-size: 0.66rem; color: #C2C6D0; font-weight: 700; margin-top: 1px; }
.imc-footer-banner {
    display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: #F7F4FB;
    border-top: 1px solid rgba(0,0,0,0.05); flex-wrap: wrap;
}
.imc-footer-avatar {
    width: 46px; height: 46px; border-radius: 50%; background: #FFFFFF; display: flex;
    align-items: center; justify-content: center; font-size: 1.3rem; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.imc-footer-tip {
    margin-left: auto; background: #FFFFFF; border-radius: 14px; padding: 10px 16px;
    font-size: 0.78rem; font-weight: 700; color: #6A1B9A; display: flex; align-items: center; gap: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05); max-width: 260px;
}

/* ---------- Tabla de percentiles por género (split rosa/azul) ---------- */
.perc-card { border-radius: var(--bento-radius-lg); overflow: hidden; box-shadow: var(--bento-shadow);
             border: 1px solid rgba(0,0,0,0.05); background: #FFFFFF; font-family: var(--font-round); }
.perc-banner { padding: 16px 20px; display: flex; align-items: center; gap: 12px; }
.perc-banner-icon { font-size: 1.6rem; }
.perc-banner-title { font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em; }
.perc-badge { margin-left: auto; font-size: 1.1rem; opacity: 0.65; }
.perc-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.perc-table th { padding: 9px 4px; text-align: center; font-weight: 800; font-size: 0.72rem; }
.perc-table td { padding: 8px 4px; text-align: center; font-weight: 600; color: #2A2E35; }
.perc-table tr.zebra { background: rgba(0,0,0,0.025); }
.perc-table tr.user-row td { box-shadow: inset 0 0 0 2px #24262B33; font-weight: 800; }

/* ---------- Info de 3 columnas (¿Qué significa? / Relacionado con / Recordar) ---------- */
.info3-card { background:#FFFFFF; border-radius: var(--bento-radius); padding: 18px 20px; height: 100%;
              box-shadow: var(--bento-shadow); border: 1px solid rgba(0,0,0,0.04); font-family: var(--font-round); }
.info3-title { font-weight: 800; font-size: 0.88rem; color: #24262B; margin-bottom: 8px; }
.dominio-icono {
    display:flex; flex-direction:column; align-items:center; text-align:center; gap:6px; flex:1; min-width:0;
}
.dominio-circulo {
    width:44px; height:44px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:1.15rem; flex-shrink:0;
}
.dominio-label { font-size: 0.68rem; font-weight: 700; color: #5C6B60; line-height: 1.2; }
.cta-pill-card {
    display:flex; align-items:center; gap:14px; background:#FFFFFF; border-radius:18px; padding:14px 18px;
    box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.04); font-family: var(--font-round);
    flex:1; min-width:240px; text-decoration:none;
}
.cta-pill-icon { width:42px; height:42px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:1.2rem; flex-shrink:0; }
.cta-pill-title { font-weight:800; font-size:0.85rem; color:#24262B; margin-bottom:2px; }
.cta-pill-desc { font-size:0.74rem; color:#8A94A6; line-height:1.3; }
.cta-pill-btn { display:inline-block; margin-top:6px; font-size:0.74rem; font-weight:800; padding:5px 14px;
                border-radius: var(--bento-pill); }

/* ---------- Panel "Tu Diagnóstico Nutricional" (Hoja 2 · IMC) ---------- */
.diag-panel { background:#FFFFFF; border-radius: var(--bento-radius-lg); padding:22px 24px; margin-bottom:14px;
              box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.05); font-family: var(--font-round); }
.diag-panel-title { font-weight:800; font-size:1.1rem; color:#6A1B9A; margin-bottom:14px; }
.diag-kpi-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap:14px; }
.diag-kpi { background:#F7F4FB; border-radius:16px; padding:14px 10px; text-align:center; }
.diag-kpi-icon { font-size:1.3rem; }
.diag-kpi-label { font-size:0.72rem; font-weight:800; color:#8A94A6; text-transform:uppercase; letter-spacing:0.04em; margin-top:4px; }
.diag-kpi-val { font-size:1.02rem; font-weight:800; margin-top:4px; line-height:1.2; }
.diag-frase { margin-top:16px; background:#FAFAFC; border-radius:14px; padding:14px 18px; display:flex;
              gap:10px; align-items:flex-start; font-size:0.9rem; color:#2A2E35; line-height:1.5; }

/* ---------- Escala horizontal de IMC (reemplaza al velocímetro como foco principal) ---------- */
.escala-imc-wrap { background:#FFFFFF; border-radius: var(--bento-radius); padding:18px 20px; height:100%;
                    box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.04); font-family: var(--font-round); }
.escala-imc-zonas { display:flex; width:100%; height:14px; border-radius:999px; overflow:hidden; margin:34px 0 6px 0; position:relative; }
.escala-imc-labels { display:flex; width:100%; }
.escala-imc-labels span { flex:1; text-align:center; font-size:0.68rem; font-weight:800; color:#8A94A6; }
.escala-imc-marker { position:absolute; top:-30px; transform:translateX(-50%); text-align:center; }
.escala-imc-marker-tri { width:0; height:0; margin:0 auto; border-left:7px solid transparent;
                          border-right:7px solid transparent; border-top:9px solid #24262B; }

/* ---------- Percentil visual "de cada 100" ---------- */
.perc-visual-wrap { background:#FFFFFF; border-radius: var(--bento-radius); padding:18px 20px; height:100%;
                     box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.04); font-family: var(--font-round); }
.perc-visual-grid { display:grid; grid-template-columns: repeat(10, 1fr); gap:3px; margin:12px auto; max-width:220px; }
.perc-visual-dot { width:100%; padding-top:100%; border-radius:2px; }

/* ---------- Estado nutricional (checklist) ---------- */
.estado-nutri-item { display:flex; align-items:center; gap:8px; font-size:0.82rem; color:#2A2E35; margin-top:6px; }

/* ---------- ¿Qué puedes hacer desde hoy? ---------- */
.accion-card { background:#FFFFFF; border-radius:16px; padding:14px 12px; text-align:center; height:100%;
               box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.04); font-family: var(--font-round); }
.accion-card .accion-emoji { font-size:1.5rem; }
.accion-card .accion-txt { font-size:0.76rem; font-weight:700; color:#2A2E35; margin-top:6px; line-height:1.3; }

/* ---------- Barra de progreso hacia meta de IMC ---------- */
.progreso-imc-track { position:relative; width:100%; height:16px; border-radius:999px; background:#EDEDF2; margin:26px 0 8px 0; }
.progreso-imc-fill { position:absolute; top:0; left:0; height:100%; border-radius:999px; background:linear-gradient(90deg,#42A5F5,#34C759); }
.progreso-imc-meta { position:absolute; top:-22px; transform:translateX(-50%); font-size:0.7rem; font-weight:800; color:#34C759; text-align:center; }
.progreso-imc-tu { position:absolute; top:20px; transform:translateX(-50%); font-size:0.7rem; font-weight:800; color:#1565C0; text-align:center; }

/* ---------- Conexión con el resto del sistema ---------- */
.conexion-card { display:flex; align-items:center; gap:14px; background:#FFFFFF; border-radius:16px; padding:14px 16px;
                  box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.04); text-decoration:none;
                  font-family: var(--font-round); margin-bottom:10px; }
.conexion-icon { width:42px; height:42px; border-radius:50%; display:flex; align-items:center; justify-content:center;
                  font-size:1.2rem; flex-shrink:0; }
.conexion-title { font-weight:800; font-size:0.85rem; color:#24262B; }
.conexion-desc { font-size:0.76rem; color:#8A94A6; margin-top:1px; }
.conexion-arrow { margin-left:auto; font-weight:800; color:#8A94A6; flex-shrink:0; }

/* ---------- Hoja 3 (TMB) — ilustración, resultado, fórmula horizontal, flujo y central energética ---------- */
.tmb-ilustra-wrap { background:#FFFFFF; border-radius: var(--bento-radius-lg); padding:22px 24px;
                     box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.05); font-family: var(--font-round);
                     text-align:center; }
.tmb-ilustra-item { font-size:0.92rem; font-weight:700; color:#2A2E35; margin:6px 0; }
.tmb-ilustra-flecha { font-size:1.2rem; color:#C2C6D0; margin:2px 0; }
.tmb-resultado-card { background:linear-gradient(120deg,#FFF3E0 0%,#FFFFFF 75%); border-radius: var(--bento-radius-lg);
                       padding:26px 28px; text-align:center; box-shadow: var(--bento-shadow);
                       border:1px solid rgba(251,140,0,0.18); font-family: var(--font-round); }
.tmb-resultado-num { font-size:2.6rem; font-weight:800; color:#E67E22; letter-spacing:-0.02em; margin:6px 0; }
.tmb-formula-genero-wrap { background:#FFFFFF; border-radius: var(--bento-radius); padding:18px 20px; margin-bottom:14px;
                            box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.05); font-family: var(--font-round); }
.tmb-formula-genero-title { font-weight:800; font-size:0.95rem; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
.tmb-formula-flow { display:flex; align-items:center; flex-wrap:wrap; gap:6px; }
.tmb-formula-box { border-radius:14px; padding:10px 14px; text-align:center; font-weight:800; font-size:0.86rem;
                    min-width:78px; }
.tmb-formula-box .tmb-box-sub { display:block; font-size:0.66rem; font-weight:700; opacity:0.85; margin-top:2px; }
.tmb-formula-arrow { font-size:1.3rem; font-weight:800; flex-shrink:0; }
.tmb-quien-card { background:#F5F0FF; border-radius: var(--bento-radius); padding:18px 20px; height:100%;
                   box-shadow: var(--bento-shadow); border:1px solid rgba(88,86,214,0.14); font-family: var(--font-round); }
.tmb-porque-card { background:#EAFAF6; border-radius: var(--bento-radius); padding:18px 20px; height:100%;
                    box-shadow: var(--bento-shadow); border:1px solid rgba(0,199,160,0.16); font-family: var(--font-round); }
.tmb-porque-item { display:flex; align-items:flex-start; gap:8px; font-size:0.84rem; color:#1E5631; margin-top:8px; line-height:1.4; }
.tmb-central-wrap { background:#171A2B; border-radius: var(--bento-radius-lg); padding:28px 24px; text-align:center;
                     font-family: var(--font-round); color:#FFFFFF; box-shadow: var(--bento-shadow); }
.tmb-central-kcal { font-size:1.9rem; font-weight:800; color:#FFD54F; margin:6px 0 18px 0; }
.tmb-central-organos { display:flex; justify-content:center; gap:26px; flex-wrap:wrap; }
.tmb-central-organo { display:flex; flex-direction:column; align-items:center; gap:6px; }
.tmb-central-led { width:10px; height:10px; border-radius:50%; background:#FFD54F; box-shadow:0 0 8px 2px #FFD54F99; }
.tmb-central-label { font-size:0.7rem; font-weight:700; color:#C7CBE0; }
.tmb-flujo-wrap { background:#FFFFFF; border-radius: var(--bento-radius); padding:20px; text-align:center;
                   box-shadow: var(--bento-shadow); border:1px solid rgba(0,0,0,0.05); font-family: var(--font-round); }
.tmb-flujo-row { display:flex; justify-content:center; align-items:center; gap:10px; flex-wrap:wrap; margin-top:14px; }
.tmb-flujo-chip { background:#F7F4FB; border-radius:14px; padding:10px 16px; font-weight:800; font-size:0.82rem; color:#24262B; }

/* ---------- Semáforo Clínico — tarjetas-gauge dinámicas (Hoja 1 y Reporte) ---------- */
.sema-card {
    background:#FFFFFF; border-radius:20px; padding:16px 14px; height:100%;
    box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.07);
    transition: transform 0.2s ease, box-shadow 0.2s ease; cursor: help;
}
.sema-card:hover { transform: translateY(-4px); box-shadow:0 4px 8px rgba(0,0,0,0.05), 0 16px 30px rgba(0,0,0,0.13); }
.sema-gauge-track { position:relative; width:100%; height:14px; border-radius:999px; overflow:hidden; margin:8px 0 4px 0; background:#EEE; }
.sema-gauge-seg { position:absolute; top:0; height:100%; }
.sema-gauge-marker {
    position:absolute; top:-4px; width:0; height:0; transform:translateX(-50%);
    border-left:7px solid transparent; border-right:7px solid transparent; border-top:11px solid #1C1C1E;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.35));
}

/* ---------- Panel de tablas de referencia clínica (Hemoglobina / Hierro) ---------- */
.ref-panel { background:#F8FAFC; border-radius:16px; padding:22px 22px; box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 10px 24px rgba(0,0,0,0.05); border:1px solid rgba(0,0,0,0.04); margin-bottom:14px; }
.ref-panel-title { display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.05rem; color:#1C1C1E; margin-bottom:14px; }
.ref-row { display:grid; align-items:center; gap:10px; padding:6px 0; }
.ref-group-label { font-weight:700; color:#3C3C43; font-size:0.86rem; }
.ref-chip { border-radius:8px; padding:9px 8px; text-align:center; font-weight:700; font-size:0.82rem; }
.ref-header-chip { border-radius:8px; padding:7px 8px; text-align:center; font-weight:800; font-size:0.74rem; text-transform:uppercase; letter-spacing:0.02em; color:#5C6B60; background:#EEF1F4; }

/* ---------- Hoja 6: Macronutrientes — tarjetas por color y tooltips info ---------- */
.macro-card {
    border-radius: 20px; padding: 18px 20px; height: 100%; position: relative;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 8px 20px rgba(0,0,0,0.07);
    border: 1px solid rgba(0,0,0,0.04);
}
.macro-card.prot { background: linear-gradient(150deg,#FFEDEC 0%,#FFFFFF 70%); border-left: 5px solid #FF3B30; }
.macro-card.gras { background: linear-gradient(150deg,#FFF3E0 0%,#FFFFFF 70%); border-left: 5px solid #FF9500; }
.macro-card.carb { background: linear-gradient(150deg,#EAFAEE 0%,#FFFFFF 70%); border-left: 5px solid #34C759; }
.macro-card .mc-head { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.macro-card .mc-icon { font-size:1.4rem; }
.macro-card .mc-title { font-weight:800; font-size:1rem; color:#17301F; }
.macro-card .mc-tip {
    margin-left:auto; cursor:help; font-size:0.85rem; color:#8A94A6;
    border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center;
    background:rgba(0,0,0,0.05);
}
.macro-card .mc-value { font-size:1.7rem; font-weight:800; letter-spacing:-0.02em; margin:4px 0 2px 0; }
.macro-card.prot .mc-value { color:#C0392B; }
.macro-card.gras .mc-value { color:#E67E22; }
.macro-card.carb .mc-value { color:#1E5631; }
.macro-card .mc-sub { font-size:0.78rem; color:#5C6B60; line-height:1.4; }
.macro-niveles-table { width:100%; border-collapse:separate; border-spacing:0; font-size:0.86rem; }
.macro-niveles-table th { background:#1E5631; color:#FFFFFF; padding:10px 12px; font-weight:800; text-align:center; }
.macro-niveles-table th:first-child { border-top-left-radius:14px; }
.macro-niveles-table th:last-child { border-top-right-radius:14px; }
.macro-niveles-table td { padding:9px 12px; text-align:center; background:#FFFFFF; border-bottom:1px solid #F0F0F0; }
.macro-niveles-table tr:nth-child(even) td { background:#F7F9F7; }
.badge-tu-nivel { display:inline-block; background:#FFCC00; color:#5C4700; font-size:0.62rem; font-weight:900;
    padding:2px 9px; border-radius:999px; margin-left:6px; vertical-align:middle; letter-spacing:0.02em; }
.macro-final-table { width:100%; border-collapse:separate; border-spacing:0; font-size:0.92rem; border-radius:16px; overflow:hidden; box-shadow:0 1px 2px rgba(0,0,0,0.04), 0 8px 20px rgba(0,0,0,0.06); }
.macro-final-table th { background:linear-gradient(135deg,#1E5631,#2E7D32); color:#FFFFFF; padding:12px 14px; font-weight:800; text-align:center; }
.macro-final-table td { padding:12px 14px; text-align:center; background:#FFFFFF; border-bottom:1px solid #F0F0F0; font-weight:600; color:#17301F; }
.macro-final-table tr.fila-total td { background:#1E5631; color:#FFFFFF; font-weight:800; font-size:1rem; }

/* ---------- Hoja 7: Distribución Calórica por Comidas ---------- */
.rcd-hero-card {
    position:relative; overflow:hidden;
    background: linear-gradient(120deg,#FF6B35 0%,#FF9500 26%,#FFCC00 52%,#34C759 80%,#30B0C7 100%);
    border-radius: 28px; padding: 32px 34px; color: white; text-align:center;
    box-shadow: 0 18px 40px rgba(255,111,0,0.35); margin-bottom: 12px;
}
.rcd-hero-card::before {
    content:""; position:absolute; inset:0; pointer-events:none;
    background: radial-gradient(circle at 15% 20%, rgba(255,255,255,0.28) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(255,255,255,0.20) 0%, transparent 50%);
}
.rcd-hero-decor { position:absolute; font-size:5.5rem; opacity:0.16; line-height:1; pointer-events:none; }
.rcd-hero-decor.d1 { top:-14px; left:-10px; transform:rotate(-15deg); }
.rcd-hero-decor.d2 { bottom:-20px; right:-8px; transform:rotate(12deg); }
.rcd-hero-card .rcd-label {
    position:relative; font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em;
    opacity:0.96; display:inline-flex; align-items:center; gap:6px;
    background:rgba(255,255,255,0.22); padding:6px 18px; border-radius:999px; backdrop-filter:blur(4px);
}
@keyframes rcd-glow {
    0%,100% { text-shadow:0 0 18px rgba(255,255,255,0.55), 0 4px 14px rgba(0,0,0,0.18); }
    50%     { text-shadow:0 0 34px rgba(255,255,255,0.90), 0 4px 14px rgba(0,0,0,0.18); }
}
.rcd-hero-card .rcd-value {
    position:relative; font-size:2.9rem; font-weight:900; letter-spacing:-0.02em; margin:14px 0 8px 0;
    animation: rcd-glow 2.4s ease-in-out infinite;
}
.rcd-hero-card .rcd-sub {
    position:relative; font-size:0.92rem; max-width:660px; margin:6px auto 18px auto; opacity:0.97; line-height:1.55;
}
.rcd-hero-badges { position:relative; display:flex; justify-content:center; gap:10px; flex-wrap:wrap; }
.rcd-hero-badge {
    background:rgba(255,255,255,0.24); border:1px solid rgba(255,255,255,0.38); backdrop-filter:blur(6px);
    padding:7px 14px; border-radius:999px; font-size:0.8rem; font-weight:800; display:flex; align-items:center; gap:6px;
}

.comidas-table-wrap {
    border-radius:20px; overflow:hidden; margin-top:14px;
    box-shadow:0 1px 2px rgba(0,0,0,0.04), 0 8px 22px rgba(0,0,0,0.07);
    border:1px solid rgba(0,0,0,0.04);
}
.comidas-table { width:100%; border-collapse:collapse; font-family:var(--font-round); }
.comidas-table thead th {
    background: linear-gradient(135deg,#FFB300,#FF9500); color:#FFFFFF; padding:12px 16px;
    font-weight:800; text-align:center; font-size:0.82rem; text-transform:uppercase; letter-spacing:0.03em;
}
.comidas-table tbody td { padding:12px 16px; text-align:center; font-weight:600; color:#5A3E1B; }
.comidas-table tbody tr { background:#FFF8EE; }
.comidas-table tbody tr:nth-child(even) { background:#FFF1DC; }
.comidas-table td.comida-nombre { text-align:left; font-weight:800; color:#B15E00; }
.comidas-table tr.fila-total-comidas td { background:#FF9500; color:#FFFFFF; font-weight:800; font-size:1rem; }

@keyframes validacion-fadein {
    from { opacity:0; transform: translateY(10px); }
    to   { opacity:1; transform: translateY(0); }
}
.validacion-ok {
    margin-top:14px; border-radius:18px; padding:16px 20px;
    background:#EAFAEE; border:1.5px solid #34C759; color:#1E5631; font-weight:700;
    display:flex; align-items:center; gap:10px; font-size:0.94rem;
    animation: validacion-fadein 0.5s ease both;
    box-shadow: 0 6px 18px rgba(52,199,89,0.18);
}
.validacion-error {
    margin-top:14px; border-radius:18px; padding:16px 20px;
    background:#FBEAE8; border:1.5px solid #C0392B; color:#8A1F13; font-weight:700;
    display:flex; align-items:center; gap:10px; font-size:0.94rem;
    animation: validacion-fadein 0.5s ease both;
}

/* ---------- Hoja 7: Panel de validación RCD vs. Total Distribuido ---------- */
.val-card {
    background:#FFFFFF; border-radius:20px; padding:22px 24px; margin-top:18px;
    box-shadow:0 1px 2px rgba(0,0,0,0.04), 0 8px 22px rgba(0,0,0,0.07);
    border:1px solid rgba(0,0,0,0.05);
}
.val-card-title { font-weight:800; font-size:1rem; margin-bottom:12px; display:flex; align-items:center; gap:8px; color:#17301F; }
.val-comparacion-table { width:100%; border-collapse:collapse; font-size:0.9rem; margin-bottom:20px; }
.val-comparacion-table td { padding:11px 6px; border-bottom:1px solid #F0F0F0; }
.val-comparacion-table td:first-child { font-weight:700; color:#5C6B60; }
.val-comparacion-table td:last-child { text-align:right; font-weight:800; color:#17301F; }
.val-comparacion-table tr:last-child td { border-bottom:none; }
.val-comparacion-table tr.val-row-estado-ok td:last-child { color:#1E5631; }
.val-comparacion-table tr.val-row-estado-bad td:last-child { color:#C0392B; }

.val-checklist {
    background:#F7F9F7; border-radius:14px; padding:16px 20px;
    font-family: "SFMono-Regular", Consolas, "Courier New", monospace;
    font-size:0.84rem; line-height:2.1; color:#17301F; white-space:pre;
    overflow-x:auto;
}
.val-checklist .val-ok { color:#1E5631; font-weight:800; }
.val-checklist .val-bad { color:#C0392B; font-weight:800; }

.val-banner-ok, .val-banner-error {
    margin-top:18px; border-radius:20px; padding:22px 24px; text-align:center;
    animation: validacion-fadein 0.5s ease both;
}
.val-banner-ok {
    background:linear-gradient(135deg,#EAFAEE 0%,#D7F5DE 100%); border:2px solid #34C759; color:#1E5631;
    box-shadow:0 10px 26px rgba(52,199,89,0.22);
}
.val-banner-error {
    background:linear-gradient(135deg,#FBEAE8 0%,#FAD9D5 100%); border:2px solid #C0392B; color:#8A1F13;
    box-shadow:0 10px 26px rgba(192,57,43,0.18);
}
.val-banner-icon { font-size:2.2rem; display:block; margin-bottom:6px; }
.val-banner-title { font-weight:900; font-size:1.05rem; letter-spacing:-0.01em; }
.val-banner-sub { font-size:0.86rem; font-weight:600; margin-top:6px; opacity:0.9; }

/* ---------- Componente global: FormulaBadge — tooltip discreto de fórmula clínica ---------- */
.formula-badge {
    display:inline-flex; align-items:center; gap:4px; cursor:help;
    background:rgba(30,86,49,0.08); color:#1E5631; font-size:0.70rem; font-weight:800;
    padding:3px 10px; border-radius:999px; margin-left:8px; vertical-align:middle;
    border:1px solid rgba(30,86,49,0.18); transition: background 0.15s ease, transform 0.15s ease;
    white-space:nowrap;
}
.formula-badge:hover { background:rgba(30,86,49,0.18); transform:translateY(-1px); }
.formula-badge-txt { font-family: var(--font-round); font-weight:700; letter-spacing:0.01em; }
.formula-badge-row { display:flex; align-items:center; flex-wrap:wrap; gap:6px; margin:-6px 0 14px 2px; }
@media (max-width:700px) {
    .rcd-hero-card { padding:22px 18px; }
    .rcd-hero-card .rcd-value { font-size:2.1rem; }
    .rcd-hero-decor { font-size:3.5rem; }
    .comidas-table thead th, .comidas-table tbody td { padding:9px 8px; font-size:0.78rem; }
}

/* ---------- Hoja 9: Dieta — panel resumen, selector de alimentos y menú tipo tablas de color ---------- */
.resumen-nutri-wrap { display:flex; gap:16px; flex-wrap:wrap; margin-top:10px; }
.resumen-nutri-card {
    flex:1; min-width:230px; background:#FFFFFF; border-radius:22px; padding:20px 22px;
    box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 20px rgba(0,0,0,0.06); border:1px solid rgba(0,0,0,0.04);
}
.resumen-nutri-card .rn-title { font-weight:800; font-size:0.92rem; display:flex; align-items:center; gap:8px; margin-bottom:10px; }
.resumen-nutri-card.rn-tiempos { background:linear-gradient(160deg,#E6F7FA 0%,#FFFFFF 65%); }
.resumen-nutri-card.rn-macros { background:linear-gradient(160deg,#F3EAF7 0%,#FFFFFF 65%); }
.resumen-nutri-card.rn-rcd { background:linear-gradient(150deg,#1E5631 0%,#2E7D32 60%,#4CAF50 100%); color:#FFFFFF; text-align:center; }
.rn-tiempos-row { display:flex; justify-content:space-between; align-items:center; padding:6px 0; font-size:0.84rem; border-bottom:1px dashed rgba(0,0,0,0.08); }
.rn-tiempos-row:last-child { border-bottom:none; }
.rn-tiempos-row .rn-kcal { font-weight:800; color:#0E7C86; background:#E0F7FA; padding:2px 10px; border-radius:999px; font-size:0.8rem; }
.rn-macro-row { display:flex; justify-content:space-between; align-items:center; padding:7px 0; font-size:0.86rem; }
.rn-macro-pill { font-weight:800; padding:3px 12px; border-radius:999px; font-size:0.8rem; }
.rn-rcd-value { font-size:2.4rem; font-weight:900; letter-spacing:-0.02em; margin:6px 0; }

.selector-menu-title {
    text-align:center; font-weight:900; font-size:1.85rem; letter-spacing:-0.02em;
    background:linear-gradient(120deg,#FF6B35,#FF9500,#34C759,#1E88E5);
    -webkit-background-clip:text; background-clip:text; color:transparent;
    margin:26px 0 4px 0;
}
.selector-menu-sub { text-align:center; color:#5C6B60; font-size:0.92rem; margin-bottom:18px; }
.comida-momento-banner {
    display:flex; align-items:center; gap:10px; background:linear-gradient(120deg,#FFF3E0,#FFFFFF);
    border-left:5px solid #FF9500; border-radius:16px; padding:10px 18px; margin:22px 0 10px 0;
    font-weight:800; font-size:1.02rem; color:#B15E00;
}
.macro-select-label { display:flex; align-items:center; gap:6px; font-weight:800; font-size:0.82rem;
    padding:6px 12px; border-radius:999px; margin-bottom:6px; width:fit-content; }
.macro-select-label.carb { background:#E1F5FE; color:#0277BD; }
.macro-select-label.prot { background:#F3E5F5; color:#8E24AA; }
.macro-select-label.gras { background:#FFF3E0; color:#E65100; }

.menu-titulo-grande {
    text-align:center; font-weight:900; font-size:2rem; letter-spacing:-0.01em; color:#FFFFFF;
    background:linear-gradient(120deg,#1E5631,#2E7D32,#4CAF50); border-radius:22px; padding:20px 24px;
    margin:28px 0 18px 0; box-shadow:0 14px 30px rgba(30,86,49,0.28);
}
.dieta-menu-table { width:100%; border-collapse:collapse; font-family:var(--font-round); font-size:0.86rem; }
.dieta-menu-table thead th { padding:12px 14px; text-align:center; font-weight:800; color:#FFFFFF; }
.dieta-menu-table tbody td { padding:11px 14px; text-align:center; }
.dieta-menu-table tbody tr:nth-child(even) td { filter:brightness(0.98); }
.dieta-menu-table td.dm-momento { text-align:left; font-weight:800; }
.dieta-menu-wrap { border-radius:20px; overflow:hidden; margin-bottom:24px;
    box-shadow:0 1px 2px rgba(0,0,0,0.04), 0 8px 22px rgba(0,0,0,0.07); border:1px solid rgba(0,0,0,0.04); }

.dieta-menu-wrap.carb .dieta-menu-table thead th { background:linear-gradient(135deg,#1E88E5,#4FC3F7); }
.dieta-menu-wrap.carb .dieta-menu-table tbody tr { background:#EAF6FE; }
.dieta-menu-wrap.carb .dieta-menu-table tbody td { color:#0D47A1; }
.dieta-menu-wrap.carb .dieta-menu-table tr.dm-total td { background:#1565C0; color:#FFFFFF; font-weight:800; }

.dieta-menu-wrap.prot .dieta-menu-table thead th { background:linear-gradient(135deg,#8E24AA,#CE93D8); }
.dieta-menu-wrap.prot .dieta-menu-table tbody tr { background:#F6ECFA; }
.dieta-menu-wrap.prot .dieta-menu-table tbody td { color:#6A1B9A; }
.dieta-menu-wrap.prot .dieta-menu-table tr.dm-total td { background:#7B1FA2; color:#FFFFFF; font-weight:800; }

.dieta-menu-wrap.gras .dieta-menu-table thead th { background:linear-gradient(135deg,#F9A825,#FFD54F); }
.dieta-menu-wrap.gras .dieta-menu-table tbody tr { background:#FFF8E1; }
.dieta-menu-wrap.gras .dieta-menu-table tbody td { color:#B15E00; }
.dieta-menu-wrap.gras .dieta-menu-table tr.dm-total td { background:#EF6C00; color:#FFFFFF; font-weight:800; }

.dieta-total-bar {
    position:relative; overflow:hidden; margin-top:8px;
    background:linear-gradient(120deg,#1E88E5 0%,#8E24AA 35%,#F9A825 68%,#1E5631 100%);
    border-radius:24px; padding:26px 30px; color:#FFFFFF; text-align:center;
    box-shadow:0 18px 40px rgba(30,86,49,0.30);
}
.dieta-total-bar .dt-label { font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; opacity:0.92; }
.dieta-total-bar .dt-formula { font-size:1.05rem; font-weight:700; margin:10px 0 6px 0; opacity:0.96; }
.dieta-total-bar .dt-value { font-size:2.3rem; font-weight:900; letter-spacing:-0.02em; margin:6px 0; }
.dieta-total-bar .dt-check { font-size:0.92rem; font-weight:700; background:rgba(255,255,255,0.22); display:inline-block;
    padding:6px 16px; border-radius:999px; margin-top:6px; }

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
    <b style="color:{borde};">{emoji} {T("¿Para qué te sirve esto?", "What is this useful for?")}</b><br>
    <span style="color:#1C1C1E;">{texto}</span>
    </div>
    """, unsafe_allow_html=True)


def hoja_header(idx, subtitulo=None, ilustracion=None, tip=None):
    """Encabezado tipo banner: degradado pastel suave, título profesional SIN el prefijo
    'Hoja N:', subtítulo descriptivo y un badge de color al costado (p. ej. 'Módulo Clínico').
    Admite opcionalmente una ilustración SVG decorativa a la derecha y una burbuja de
    'tip' tipo chat, para las hojas con hero enriquecido (Bento Grid)."""
    numero, titulo, emoji, borde, fondo = (COLORES_EN if st.session_state.get("idioma", "Español") == "English" else COLORES)[idx]
    badge = (BADGE_HOJAS_EN if st.session_state.get("idioma", "Español") == "English" else BADGE_HOJAS).get(idx, "Módulo")
    sub_html = f"<p style='margin:6px 0 0 0;color:#5C6B60;font-size:0.92rem;font-weight:500;line-height:1.5;max-width:480px;'>{subtitulo}</p>" if subtitulo else ""
    ilustracion_html = f'<div style="flex-shrink:0;position:relative;">{ilustracion}</div>' if ilustracion else ""
    tip_html = (
        f'''<div style="background:#FFFFFF;border-radius:16px;padding:8px 14px;font-size:0.78rem;
             font-weight:700;color:{borde};box-shadow:0 4px 14px rgba(0,0,0,0.10);
             position:relative;max-width:170px;font-family:var(--font-round);">
             {tip}
             <div style="position:absolute;bottom:-6px;left:22px;width:12px;height:12px;
                  background:#FFFFFF;transform:rotate(45deg);"></div>
             </div>'''
        if tip else ""
    )
    html = f"""<div style="background:linear-gradient(120deg,{fondo} 0%,#FFFFFF 70%);border-radius:24px;padding:22px 28px;margin-bottom:16px;
display:flex;align-items:flex-start;justify-content:space-between;gap:18px;flex-wrap:wrap;
box-shadow:0 1px 2px rgba(30,86,49,0.04), 0 10px 26px rgba(30,86,49,0.08);
border:1px solid rgba(30,86,49,0.06);">
<div style="display:flex;align-items:flex-start;gap:18px;">
<div style="min-width:56px;height:56px;border-radius:50%;background:{fondo};
display:flex;align-items:center;justify-content:center;font-size:1.6rem;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.06);">{emoji}</div>
<div>
<h2 style="margin:0;color:{borde};font-weight:800;letter-spacing:-0.02em;">{titulo}</h2>
{sub_html}
</div>
</div>
<div style="display:flex;flex-direction:column;align-items:flex-end;gap:10px;">
<div style="background:{borde};color:#FFFFFF;padding:7px 16px;border-radius:999px;font-size:0.72rem;
font-weight:800;letter-spacing:0.05em;text-transform:uppercase;white-space:nowrap;box-shadow:0 4px 12px {borde}55;">{badge}</div>
<div style="display:flex;align-items:center;gap:14px;">
{ilustracion_html}
{tip_html}
</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def _ilustracion_imc_svg(size_h=110):
    """Ilustración SVG decorativa (autocontenida, sin archivos externos): una niña de pie
    sobre una balanza, con cinta métrica y una manzana — recreando la escena del hero de
    referencia (Imagen 2) sin depender de assets externos."""
    return f"""
    <svg width="{size_h*1.55:.0f}" height="{size_h}" viewBox="0 0 170 110" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="85" cy="102" rx="55" ry="7" fill="#AF52DE" opacity="0.08"/>
        <rect x="45" y="78" width="60" height="18" rx="8" fill="#FFFFFF" stroke="#D8C7EE" stroke-width="2"/>
        <circle cx="75" cy="87" r="5" fill="#AF52DE"/>
        <text x="75" y="90" font-size="5" fill="#FFFFFF" text-anchor="middle" font-weight="800">0</text>
        <!-- cuerpo -->
        <circle cx="75" cy="40" r="12" fill="#FFD9B3"/>
        <path d="M63 50 Q75 44 87 50 L90 78 Q75 84 60 78 Z" fill="#6C63FF"/>
        <rect x="66" y="76" width="8" height="14" rx="3" fill="#FFD9B3"/>
        <rect x="80" y="76" width="8" height="14" rx="3" fill="#FFD9B3"/>
        <path d="M66 33 Q75 24 84 33 Q84 26 75 25 Q66 26 66 33 Z" fill="#4A2E1A"/>
        <!-- cinta metrica -->
        <rect x="108" y="55" width="26" height="18" rx="4" fill="#FFCC00"/>
        <rect x="112" y="47" width="4" height="14" fill="#FFCC00"/>
        <!-- manzana -->
        <circle cx="30" cy="70" r="10" fill="#FF3B30"/>
        <path d="M30 60 Q33 55 36 58" stroke="#1E5631" stroke-width="2" fill="none"/>
        <!-- destellos -->
        <circle cx="140" cy="22" r="3" fill="#FF2D55" opacity="0.6"/>
        <circle cx="18" cy="30" r="2.4" fill="#5AC8FA" opacity="0.6"/>
        <path d="M150 40 l3 6 l6 3 l-6 3 l-3 6 l-3-6 l-6-3 l6-3 Z" fill="#FFCC00" opacity="0.75"/>
    </svg>
    """





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


def _html_sin_lineas_vacias(html):
    """Elimina líneas vacías (o con solo espacios) dentro de un bloque de HTML antes de
    renderizarlo con st.markdown. Es NECESARIO cuando el HTML se arma concatenando varios
    f-strings multilínea (por ejemplo, una fila por cada elemento de una lista): si entre dos
    fragmentos queda una línea en blanco, Streamlit/CommonMark interpreta que el bloque de HTML
    "crudo" terminó ahí, y todo el contenido indentado que sigue se muestra como texto plano
    (bloque de código) en vez de renderizarse como HTML. Al quitar esas líneas en blanco, el
    bloque de HTML se mantiene continuo y se renderiza correctamente de principio a fin."""
    return "\n".join(linea for linea in html.split("\n") if linea.strip() != "")


def formula_badge(formula, autor="", referencia="", icono="ℹ️", texto=None):
    """Insignia discreta tipo 'chip' que muestra, al pasar el cursor (tooltip nativo del
    navegador vía atributo `title`), la fórmula clínica exacta junto con su autor y su
    referencia científica — cumpliendo la norma clínica 4.1 sin saturar visualmente la
    pantalla. Se usa junto a títulos, métricas o resultados en cada hoja de la app."""
    if texto is None:
        texto = T("Ver fórmula", "View Formula")
    partes = [f"{T('Fórmula', 'Formula')}: {formula}"]
    if autor:
        partes.append(f"{T('Autor', 'Author')}: {autor}")
    if referencia:
        partes.append(f"{T('Referencia', 'Reference')}: {referencia}")
    tooltip = " · ".join(partes).replace('"', "'").replace("\n", " ")
    return (f'<span class="formula-badge" title="{tooltip}">{icono} '
            f'<span class="formula-badge-txt">{texto}</span></span>')


@st.cache_data(show_spinner=False)
def _resolver_imagen(ruta):
    """Busca una imagen probando varias ubicaciones (la ruta indicada, directamente en /assets,
    y en /assets/hojas) y varias extensiones/mayúsculas (.jpg, .JPG, .jpeg, .png, etc.).
    Devuelve la primera ruta que exista, o None si no encuentra nada.
    Cacheado: el sistema de archivos de /assets no cambia durante la sesión, así que evitamos
    repetir estas búsquedas en disco en cada rerun (mejora notable la velocidad de la app)."""
    ruta = Path(ruta)
    nombre_base = ruta.stem
    carpetas_candidatas = [ruta.parent, ASSETS_DIR, ASSETS_DIR / "hojas"]
    extensiones = ["jpg", "JPG", "Jpg", "jpeg", "JPEG", "png", "PNG", "Png", "webp", "WEBP"]
    vistos = set()
    # primero prueba la ruta exacta tal cual vino
    if ruta.exists():
        return ruta
    for carpeta in carpetas_candidatas:
        for ext in extensiones:
            candidato = carpeta / f"{nombre_base}.{ext}"
            if candidato in vistos:
                continue
            vistos.add(candidato)
            if candidato.exists():
                return candidato
    return None


@st.cache_data(show_spinner=False)
def _img_to_b64(ruta):
    """Convierte una imagen (ruta en disco) a base64. Devuelve None si no existe o falla.
    Cacheado para no releer/recodificar el mismo archivo en cada rerun."""
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
        ruta_resuelta = _resolver_imagen(ruta)
        if ruta_resuelta is None:
            return
        b64 = _img_to_b64(ruta_resuelta)
        ext = ruta_resuelta.suffix.lstrip(".").lower() or "png"
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
    """Genera el 'Informe de Orientación Nutricional Clínica' en 2 páginas A4, con el diseño
    modular tipo ficha clínica (encabezado institucional, semáforos de signos vitales y
    análisis sanguíneo, módulos de antropometría/energía/macronutrientes en grillas de 2
    columnas, y en la página 2 las 3 tablas cromáticas del plan alimentario + recomendaciones
    y aviso médico-legal) — listo para imprimir o entregar al usuario.
    `datos` es un diccionario con toda la información necesaria (ver llamada en Hoja 14)."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=14 * mm, bottomMargin=12 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=T("Informe de Orientación Nutricional Clínica - CIAM&SUNI",
                 "Clinical Nutritional Guidance Report - CIAM&SUNI"),
    )

    CONTENT_W = 178 * mm
    MOD_W = 87 * mm
    GAP_W = 4 * mm

    AZUL_TXT    = "#17324A"
    VERDE       = "#1E5631"
    GRIS_TXT    = "#3C3C43"
    GRIS_SUAVE  = "#6C6C70"
    LINEA       = "#E3E8E3"
    GRIS_MOD    = "#F1F4F2"
    AZUL_CARB, AZUL_CARB_CLARO       = "#2980b9", "#ebf5fb"
    MORADO_PROT, MORADO_PROT_CLARO   = "#8e44ad", "#f4ecf7"
    NARANJA_GRA, NARANJA_GRA_CLARO   = "#d35400", "#fbeee6"

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("TituloInforme", parent=styles["Title"], fontName="Helvetica-Bold",
                                    fontSize=15, textColor=_rl_hex(AZUL_TXT), spaceAfter=1, alignment=TA_LEFT, leading=17.5)
    estilo_subtitulo = ParagraphStyle("SubtituloInforme", parent=styles["Normal"], fontName="Helvetica",
                                       fontSize=8.6, textColor=_rl_hex(GRIS_SUAVE), alignment=TA_LEFT)
    estilo_meta = ParagraphStyle("MetaInforme", parent=styles["Normal"], fontName="Helvetica",
                                  fontSize=8.2, textColor=_rl_hex(GRIS_TXT), alignment=TA_RIGHT, leading=11.6)
    estilo_modulo = ParagraphStyle("ModuloHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=9.2, textColor=_rl_hex(AZUL_TXT))
    estilo_texto = ParagraphStyle("Texto", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=8.5, textColor=_rl_hex(GRIS_TXT), leading=12.2)
    estilo_texto_bold = ParagraphStyle("TextoBold", parent=estilo_texto, fontName="Helvetica-Bold")
    estilo_explic = ParagraphStyle("Explicacion", parent=estilo_texto, fontSize=8.3, leading=11.8,
                                    spaceBefore=3, spaceAfter=11)
    estilo_pill = ParagraphStyle("Pill", parent=styles["Normal"], fontName="Helvetica-Bold",
                                  fontSize=7.4, alignment=TA_CENTER)
    estilo_pagina2_tit = ParagraphStyle("Pag2Tit", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                         fontSize=13, textColor=_rl_hex(AZUL_TXT), spaceAfter=1)
    estilo_seccion2 = ParagraphStyle("Seccion2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                                      fontSize=10.2, textColor=_rl_hex(AZUL_TXT), spaceBefore=10, spaceAfter=5)
    estilo_recom_tit = ParagraphStyle("RecomTit", parent=estilo_texto_bold, fontSize=8.7, textColor=_rl_hex(VERDE))
    estilo_recom_txt = ParagraphStyle("RecomTxt", parent=estilo_texto, leftIndent=2, spaceAfter=7, leading=11.8)
    estilo_aviso = ParagraphStyle("Aviso", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=6.5, textColor=_rl_hex("#6C6C70"), leading=9)

    story = []
    _embarazada_pdf = bool(datos.get("embarazada", False))

    # ---------------- helper: imagen con alto fijo (mm) y ancho proporcional ----------------
    def _imagen_flowable(ruta, alto_mm):
        try:
            if not Path(ruta).exists():
                return None
            lector = ImageReader(str(ruta))
            ancho_px, alto_px = lector.getSize()
            alto = alto_mm * mm
            ancho = alto * (ancho_px / alto_px) if alto_px else alto
            return Image(str(ruta), width=ancho, height=alto)
        except Exception:
            return None

    def _membrete_institucional():
        img_membrete = _imagen_flowable(_LOGO_ANCHO, 20)
        if img_membrete is None:
            img_membrete = _imagen_flowable(_ESCUDO, 20)
        if img_membrete is None:
            return
        t = Table([[img_membrete]], colWidths=[CONTENT_W])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # ---------------- helpers de módulo (grilla 2 columnas, semáforos y tablas clave/valor) ----------------
    def _cab_modulo(titulo, ancho=MOD_W):
        t = Table([[Paragraph(titulo, estilo_modulo)]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _rl_hex(GRIS_MOD)),
            ("LINEBEFORE", (0, 0), (0, -1), 2.6, _rl_hex(AZUL_TXT)),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    def _pill(texto, color_key, ancho=38 * mm):
        est = SEMAFORO_ESTILO[color_key]
        p = Paragraph(f"{est['emoji']} {texto}",
                      ParagraphStyle("PillTxt", parent=estilo_pill, textColor=_rl_hex(est["hex"])))
        t = Table([[p]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _rl_hex(est["fondo"])),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def _tabla_kv(filas, ancho=MOD_W, col1=46 * mm):
        celdas = [[Paragraph(f"<b>{k}</b>", estilo_texto),
                   v if not isinstance(v, str) else Paragraph(v, estilo_texto)] for k, v in filas]
        t = Table(celdas, colWidths=[col1, ancho - col1])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    def _tabla_vitales(filas_vitales, ancho=MOD_W, col1=46 * mm):
        celdas = [[Paragraph(label, estilo_texto), _pill(etiqueta, color, ancho=ancho - col1 - 2)]
                  for label, etiqueta, color in filas_vitales]
        t = Table(celdas, colWidths=[col1, ancho - col1])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    def _fila_doble(izq_flows, der_flows):
        t = Table([[izq_flows, "", der_flows]], colWidths=[MOD_W, GAP_W, MOD_W])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    # ==========================================================================================
    # PÁGINA 1 — EVALUACIÓN Y PARÁMETROS CLÍNICOS
    # ==========================================================================================
    _membrete_institucional()

    _grupo_txt = datos.get("grupo", 'N°04 - 5° "C"')
    _etapa_hdr_txt = T(datos['etapa'], _ETAPA_EN.get(datos['etapa'], datos['etapa']))
    header_tbl = Table([
        [Paragraph(T("INFORME DE ORIENTACIÓN NUTRICIONAL CLÍNICA", "CLINICAL NUTRITIONAL GUIDANCE REPORT"), estilo_titulo),
         Paragraph(f"<b>{T('PACIENTE', 'PATIENT')}:</b> {datos['nombre'].upper()}", estilo_meta)],
        [Paragraph(T('Programa de Salud Escolar CIAM&amp;SUNI | C.E.P. "Santa María Reina", Chiclayo',
                      'CIAM&amp;SUNI School Health Program | C.E.P. "Santa María Reina", Chiclayo'), estilo_subtitulo),
         Paragraph(f"<b>{T('Edad', 'Age')}:</b> {datos['edad']} {T('años', 'years')} ({_etapa_hdr_txt})", estilo_meta)],
        ["", Paragraph(f"<b>{T('Fecha', 'Date')}:</b> {datos['fecha']} | <b>{T('Grupo', 'Group')}:</b> {_grupo_txt}", estilo_meta)],
    ], colWidths=[CONTENT_W - 55 * mm, 55 * mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.1, color=_rl_hex(AZUL_TXT)))
    story.append(Spacer(1, 9))

    # ---------------- MÓDULO 1 / 2: Información personal + Signos vitales ----------------
    _sexo_txt = T("Femenino", "Female") if datos["genero"] == "Mujer" else T("Masculino", "Male")
    _idioma_pdf_en = st.session_state.get("idioma", "Español") == "English"
    _trimestre_txt = datos.get('trimestre', '')
    if _idioma_pdf_en:
        _trimestre_txt = (_trimestre_txt.replace('Primer', '1st').replace('Segundo', '2nd').replace('Tercer', '3rd')
                           .replace('Trimestre', 'Trimester'))
        _estado_fisio_txt = f"Gestational ({_trimestre_txt})" if _embarazada_pdf else "Not pregnant"
        _etapa_pdf_txt = _ETAPA_EN.get(datos['etapa'], datos['etapa'])
    else:
        _trimestre_txt = _trimestre_txt.replace('Primer', '1°').replace('Segundo', '2°').replace('Tercer', '3°')
        _estado_fisio_txt = f"Gestacional ({_trimestre_txt})" if _embarazada_pdf else "No gestante"
        _etapa_pdf_txt = datos['etapa']

    mod1 = [_cab_modulo(T("1. INFORMACIÓN PERSONAL Y FISIOLÓGICA", "1. PERSONAL & PHYSIOLOGICAL INFORMATION")), Spacer(1, 2),
            _tabla_kv([
                (T("Etapa de Vida", "Life Stage"), f"{_etapa_pdf_txt} ({datos['edad']} {T('años', 'years')})"),
                (T("Sexo Biológico", "Biological Sex"), _sexo_txt),
                (T("Estado Fisiológico", "Physiological State"), _estado_fisio_txt),
                (T("Nivel de Actividad", "Activity Level"), datos.get("actividad", "—")),
            ])]

    _VITAL_LABEL_EN = {
        "Sin datos": "No data", "Baja / Hipotensión": "Low / Hypotension", "Normal / Óptima": "Normal / Optimal",
        "Elevado": "Elevated", "Emergencia Hipertensiva": "Hypertensive Emergency",
        "Hipertensión Estadio 2": "Hypertension Stage 2", "Hipertensión Estadio 1": "Hypertension Stage 1",
        "Hipoxia": "Hypoxia", "Aceptable": "Acceptable", "Excelente": "Excellent",
        "Hipotermia": "Hypothermia", "Temperatura baja": "Low Temperature", "Normal": "Normal",
        "Febrícula": "Low-grade Fever", "Fiebre": "Fever", "Fiebre alta": "High Fever",
        "Bradicardia": "Bradycardia", "Taquicardia": "Tachycardia",
    }

    def _vt(etiqueta):
        return _VITAL_LABEL_EN.get(etiqueta, etiqueta) if _idioma_pdf_en else etiqueta

    def _clasif_pa_pdf(_pas, _pad):
        if _pas <= 0 or _pad <= 0: return _vt("Sin datos"), "gris"
        if _pas < 90 or _pad < 60: return _vt("Baja / Hipotensión"), "ambar"
        if 90 <= _pas <= 119 and 60 <= _pad <= 79: return _vt("Normal / Óptima"), "verde"
        if 120 <= _pas <= 129 and _pad < 80: return _vt("Elevado"), "ambar"
        if _pas > 180 or _pad > 120: return _vt("Emergencia Hipertensiva"), "rojo"
        if 140 <= _pas <= 180 or 90 <= _pad <= 120: return _vt("Hipertensión Estadio 2"), "rojo"
        if 130 <= _pas <= 139 or 80 <= _pad <= 89: return _vt("Hipertensión Estadio 1"), "rojo"
        return _vt("Normal / Óptima"), "verde"

    def _clasif_spo2_pdf(_s):
        if _s <= 0: return _vt("Sin datos"), "gris"
        if _s < 90: return _vt("Hipoxia"), "rojo"
        if _s < 95: return _vt("Aceptable"), "ambar"
        return _vt("Excelente"), "verde"

    def _clasif_temp_pdf(_t):
        if _t <= 34.0: return _vt("Sin datos"), "gris"
        if _t < 35.0: return _vt("Hipotermia"), "rojo"
        if _t < 36.1: return _vt("Temperatura baja"), "ambar"
        if _t <= 37.2: return _vt("Normal"), "verde"
        if _t <= 37.9: return _vt("Febrícula"), "ambar"
        if _t <= 39.5: return _vt("Fiebre"), "rojo"
        return _vt("Fiebre alta"), "rojo"

    def _clasif_pulso_pdf(_p):
        if _p <= 0: return _vt("Sin datos"), "gris"
        if _p < 60: return _vt("Bradicardia"), "ambar"
        if _p <= 100: return _vt("Normal"), "verde"
        return _vt("Taquicardia"), "ambar"

    _pas, _pad = datos.get("pas", 0), datos.get("pad", 0)
    _spo2, _temp, _pulso = datos.get("spo2", 0.0), datos.get("temp_corp", 34.0), datos.get("pulso", 0)
    _cat_pa, _col_pa = _clasif_pa_pdf(_pas, _pad)
    _cat_ox, _col_ox = _clasif_spo2_pdf(_spo2)
    _cat_te, _col_te = _clasif_temp_pdf(_temp)
    _cat_pu, _col_pu = _clasif_pulso_pdf(_pulso)
    _hay_algun_vital = any(c != "gris" for c in (_col_pa, _col_ox, _col_te, _col_pu))
    _hay_alerta_vital = any(c in ("rojo", "ambar") for c in (_col_pa, _col_ox, _col_te, _col_pu))

    _ETIQUETA_SEMAFORO_EN = {"Normal": "Normal", "Alerta": "Alert", "Crítico": "Critical", "Sin dato": "No data"}

    def _et(color_key):
        _e = SEMAFORO_ESTILO[color_key]["etiqueta"]
        return _ETIQUETA_SEMAFORO_EN.get(_e, _e) if _idioma_pdf_en else _e

    mod2 = [_cab_modulo(T("2. SIGNOS VITALES (ESTADO FISIOLÓGICO)", "2. VITAL SIGNS (PHYSIOLOGICAL STATE)")), Spacer(1, 2),
            _tabla_vitales([
                (T("Presión Arterial", "Blood Pressure"), _et(_col_pa), _col_pa),
                (T("Oxigenación (SpO₂)", "Oxygenation (SpO₂)"), _et(_col_ox), _col_ox),
                (T("Temperatura", "Temperature"), _et(_col_te), _col_te),
                (T("Pulso en Reposo", "Resting Pulse"), _et(_col_pu), _col_pu),
            ])]
    story.append(_fila_doble(mod1, mod2))

    _explic1 = (
        T("En el segundo/tercer trimestre gestacional se incrementan las demandas hemodinámicas. ",
          "In the second/third gestational trimester, hemodynamic demands increase. ")
        + (T("Se detectaron valores fuera de rango en los signos vitales (ver etiquetas en alerta o crítico "
             "en la tabla); se recomienda evaluación médica presencial para descartar trastornos "
             "hipertensivos del embarazo.",
             "Out-of-range values were detected in the vital signs (see alert or critical labels in the "
             "table); an in-person medical evaluation is recommended to rule out hypertensive disorders "
             "of pregnancy.") if _hay_alerta_vital else
           T("La monitorización periódica de la presión arterial, SpO₂, pulso y temperatura es crucial "
             "para descartar trastornos hipertensivos del embarazo.",
             "Periodic monitoring of blood pressure, SpO₂, pulse, and temperature is crucial to rule out "
             "hypertensive disorders of pregnancy.") if _hay_algun_vital else
           T("La ausencia de registros de signos vitales (presión arterial, SpO₂, pulso y temperatura) "
             "requiere control prenatal presencial para descartar desórdenes hipertensivos o "
             "alteraciones hemodinámicas.",
             "The absence of vital sign records (blood pressure, SpO₂, pulse, and temperature) requires "
             "an in-person prenatal check-up to rule out hypertensive disorders or hemodynamic "
             "alterations."))
    ) if _embarazada_pdf else (
        T("Los signos vitales permiten una primera aproximación al estado fisiológico general. ",
          "Vital signs provide an initial approximation of general physiological state. ")
        + (T("Se detectaron valores fuera de rango (ver etiquetas en alerta o crítico en la tabla); se "
             "recomienda evaluación médica para precisar el hallazgo.",
             "Out-of-range values were detected (see alert or critical labels in the table); a medical "
             "evaluation is recommended to clarify the finding.") if _hay_alerta_vital else
           T("Los valores registrados se encuentran dentro de los parámetros esperables; continúa con "
             "controles periódicos.",
             "The recorded values are within the expected parameters; continue with periodic check-ups.") if _hay_algun_vital else
           T("No se registraron signos vitales en esta sesión; se recomienda completarlos para un "
             "seguimiento clínico más preciso.",
             "No vital signs were recorded in this session; it is recommended to complete them for more "
             "precise clinical follow-up."))
    )
    story.append(Paragraph(f"<b>{T('Explicación Clínica:', 'Clinical Explanation:')}</b> {_explic1}", estilo_explic))

    # ---------------- MÓDULO 3 / 4: Antropometría + Requerimiento energético ----------------
    _peso_delta = datos["peso_proyectado"] - datos["peso"]
    _bono_gestacional = datos["rcd_final"] - datos["rcd"]
    _cat_imc_pdf_txt = _cat_imc_txt(datos['categoria_imc'])
    _obj_pdf_txt = T(datos.get('objetivo', ''), _OBJ_EN.get(datos.get('objetivo', ''), datos.get('objetivo', '')))
    _trimestre_expl_txt = datos.get('trimestre', '') or T('trimestre gestacional', 'gestational trimester')
    if _idioma_pdf_en:
        _trimestre_expl_txt = (_trimestre_expl_txt.replace('Primer', '1st').replace('Segundo', '2nd')
                                .replace('Tercer', '3rd').replace('Trimestre', 'Trimester'))
    mod3 = [_cab_modulo(T("3. ANTROPOMETRÍA Y PROYECCIÓN", "3. ANTHROPOMETRY & PROJECTION")), Spacer(1, 2),
            _tabla_kv([
                (T("Peso Actual", "Current Weight"), f"{datos['peso']:.2f} kg"),
                (T("Estatura", "Height"), f"{datos['estatura']} cm ({datos['estatura']/100:.2f} m)"),
                (T("IMC Actual", "Current BMI"), f"{datos['imc']} kg/m²  —  {_cat_imc_pdf_txt}"
                 + (f" (P{datos['percentil']})" if datos.get("percentil") else "")),
                (T("Proyección (60 días)", "Projection (60 days)"), f"{datos['peso_proyectado']:.2f} kg ({'+' if _peso_delta >= 0 else ''}{_peso_delta:.2f} kg)"),
            ])]
    _edad_pdf = datos.get("edad", 0) or 0
    if _embarazada_pdf:
        _limite_cafeina_txt = T("Máx. 200 mg/día (embarazo)", "Max. 200 mg/day (pregnancy)")
    elif _edad_pdf < 12:
        _limite_cafeina_txt = T("Evitar (no recomendado en niños)", "Avoid (not recommended for children)")
    elif _edad_pdf < 18:
        _limite_cafeina_txt = T("Máx. 100 mg/día (adolescente)", "Max. 100 mg/day (adolescent)")
    else:
        _limite_cafeina_txt = T("Máx. 400 mg/día", "Max. 400 mg/day")
    mod4 = [_cab_modulo(T("4. REQUERIMIENTO ENERGÉTICO Y LÍMITES", "4. ENERGY REQUIREMENT & LIMITS")), Spacer(1, 2),
            _tabla_kv([
                (T("Tasa Metabólica (TMB)", "Metabolic Rate (BMR)"), f"{datos['tmb']:.2f} kcal/{T('día', 'day')}"),
                (T("Gasto Calórico Diario", "Daily Caloric Expenditure"), f"{datos['rcd']:.2f} kcal/{T('día', 'day')}"),
                (T("Meta Gestacional Total", "Total Gestational Goal") if _embarazada_pdf else T("Meta Calórica", "Caloric Goal"),
                 f"{datos['rcd_final']:.2f} kcal/{T('día', 'day')}" + (f"  (+{_bono_gestacional:.0f} kcal)" if _embarazada_pdf and _bono_gestacional > 0 else "")),
                (T("Límite de Cafeína", "Caffeine Limit"), _limite_cafeina_txt),
            ])]
    story.append(_fila_doble(mod3, mod4))

    if _embarazada_pdf:
        _explic2 = T(
            f"Tu IMC actual de {datos['imc']} se clasifica en un rango {_cat_imc_pdf_txt.lower()}"
            + (f" (Percentil {datos['percentil']})" if datos.get("percentil") else "") + ". "
            f"Para el {_trimestre_expl_txt.lower()} se suma un bono calórico de "
            f"+{_bono_gestacional:.0f} kcal sobre tu tasa basal para garantizar el desarrollo fetal adecuado. "
            f"La ganancia ponderal estimada en 60 días ({datos['peso_proyectado']:.2f} kg) sigue una curva "
            "saludable, sin restricciones calóricas severas. La cafeína debe mantenerse estrictamente "
            "<200 mg/día para mitigar riesgos gestacionales.",
            f"Your current BMI of {datos['imc']} is classified in a {_cat_imc_pdf_txt.lower()} range"
            + (f" (Percentile {datos['percentil']})" if datos.get("percentil") else "") + ". "
            f"For the {_trimestre_expl_txt.lower()}, a caloric bonus of "
            f"+{_bono_gestacional:.0f} kcal is added to your basal rate to ensure proper fetal development. "
            f"The estimated weight gain over 60 days ({datos['peso_proyectado']:.2f} kg) follows a healthy "
            "curve, without severe caloric restrictions. Caffeine must be kept strictly under 200 mg/day "
            "to mitigate gestational risks.")
    else:
        _explic2 = T(
            f"Tu IMC actual de {datos['imc']} se clasifica como {_cat_imc_pdf_txt.lower()}"
            + (f" (Percentil {datos['percentil']})" if datos.get("percentil") else "") + ". "
            f"Tu meta calórica diaria de {datos['rcd_final']:.2f} kcal/día se calculó según tu objetivo "
            f"nutricional ({_obj_pdf_txt}), a partir de tu Tasa Metabólica Basal y tu nivel de "
            "actividad física.",
            f"Your current BMI of {datos['imc']} is classified as {_cat_imc_pdf_txt.lower()}"
            + (f" (Percentile {datos['percentil']})" if datos.get("percentil") else "") + ". "
            f"Your daily caloric goal of {datos['rcd_final']:.2f} kcal/day was calculated based on your "
            f"nutritional goal ({_obj_pdf_txt}), from your Basal Metabolic Rate and your activity level.")
    story.append(Paragraph(f"<b>{T('Explicación Clínica:', 'Clinical Explanation:')}</b> {_explic2}", estilo_explic))

    # ---------------- MÓDULO 5 / 6: Análisis sanguíneo + Macronutrientes ----------------
    _sin_datos_txt = T("Sin datos", "No data")
    _examen_map = {p: (v, c) for p, v, c in datos.get("examen", [])}
    _v_hemo, _c_hemo = _examen_map.get("Hemoglobina", (_sin_datos_txt, "Sin datos"))
    _v_gluco, _c_gluco = _examen_map.get("Glucosa", (_sin_datos_txt, "Sin datos"))
    _v_hierro, _c_hierro = _examen_map.get("Hierro", (_sin_datos_txt, "Sin datos"))
    _v_trigli, _c_trigli = _examen_map.get("Triglicéridos", (_sin_datos_txt, "Sin datos"))
    _v_coles, _c_coles = _examen_map.get("Colesterol", (_sin_datos_txt, "Sin datos"))
    _col_hemo = CATEGORIA_SEMAFORO.get(_c_hemo, "gris")
    _col_gluco = CATEGORIA_SEMAFORO.get(_c_gluco, "gris")
    _col_hierro = CATEGORIA_SEMAFORO.get(_c_hierro, "gris")
    _col_trigli = CATEGORIA_SEMAFORO.get(_c_trigli, "gris")
    _col_coles = CATEGORIA_SEMAFORO.get(_c_coles, "gris")
    _ORDEN_RIESGO = {"gris": 0, "verde": 1, "ambar": 2, "rojo": 3}
    _col_lipidico = max([_col_trigli, _col_coles], key=lambda c: _ORDEN_RIESGO.get(c, 0))
    _et_lipidico = _sin_datos_txt if _col_lipidico == "gris" else _et(_col_lipidico)

    mod5 = [_cab_modulo(T("5. ANÁLISIS SANGUÍNEO (SEMÁFORO)", "5. BLOOD ANALYSIS (TRIAGE)")), Spacer(1, 2),
            _tabla_vitales([
                (T("Hemoglobina", "Hemoglobin"), _et(_col_hemo) if datos["tiene_examen"] else _sin_datos_txt, _col_hemo),
                (T("Glucosa Basal", "Fasting Glucose"), _et(_col_gluco) if datos["tiene_examen"] else _sin_datos_txt, _col_gluco),
                (T("Hierro Sérico", "Serum Iron"), _et(_col_hierro) if datos["tiene_examen"] else _sin_datos_txt, _col_hierro),
                (T("Perfil Lipídico", "Lipid Profile"), _et_lipidico, _col_lipidico),
            ])]

    _total_kcal_macros = max(datos["cal_prot"] + datos["cal_carb"] + datos["cal_gras"], 1)
    _pct_prot_pdf = datos["cal_prot"] / _total_kcal_macros * 100
    _pct_carb_pdf = datos["cal_carb"] / _total_kcal_macros * 100
    _pct_gras_pdf = datos["cal_gras"] / _total_kcal_macros * 100
    mod6 = [_cab_modulo(T("6. DISTRIBUCIÓN DE MACRONUTRIENTES", "6. MACRONUTRIENT DISTRIBUTION")), Spacer(1, 2),
            _tabla_kv([
                (f"{T('Proteínas', 'Protein')} ({_pct_prot_pdf:.0f}%)", f"{datos['gr_prot']:.2f} g  |  {datos['cal_prot']:.2f} kcal"),
                (f"{T('Carbohidratos', 'Carbohydrates')} ({_pct_carb_pdf:.0f}%)", f"{datos['gr_carb']:.2f} g  |  {datos['cal_carb']:.2f} kcal"),
                (f"{T('Grasas', 'Fats')} ({_pct_gras_pdf:.0f}%)", f"{datos['gr_gras']:.2f} g  |  {datos['cal_gras']:.2f} kcal"),
                (T("Energía Total", "Total Energy"), f"{datos['rcd_final']:.2f} kcal/{T('día', 'day')}"),
            ])]
    story.append(_fila_doble(mod5, mod6))

    if datos["tiene_examen"]:
        _explic3 = T(
            "Se registraron analíticas sanguíneas en esta sesión. "
            + ("En el embarazo es prioritario evaluar la Hemoglobina (descarte de anemia gestacional) y la "
               "Glucosa en ayunas (descarte de diabetes gestacional). " if _embarazada_pdf else
               "Se recomienda revisar junto a un profesional de salud cualquier valor fuera del rango normal. ")
            + "La distribución de macronutrientes asigna un "
            f"{_pct_prot_pdf:.0f}% de proteínas para el aporte estructural"
            + (" fetal y placentario." if _embarazada_pdf else " y de mantenimiento muscular."),
            "Blood tests were recorded in this session. "
            + ("In pregnancy, it is a priority to evaluate Hemoglobin (to rule out gestational anemia) and "
               "fasting Glucose (to rule out gestational diabetes). " if _embarazada_pdf else
               "It is recommended to review any out-of-range value together with a healthcare professional. ")
            + "The macronutrient distribution assigns "
            f"{_pct_prot_pdf:.0f}% protein for structural support"
            + (", fetal and placental." if _embarazada_pdf else " and muscle maintenance."))
    else:
        _explic3 = T(
            "No se registraron analíticas sanguíneas en esta sesión. "
            + ("En el embarazo es prioritario evaluar la Hemoglobina (descarte de anemia gestacional) y la "
               "Glucosa en ayunas (descarte de diabetes gestacional). " if _embarazada_pdf else
               "Se recomienda completar un panel básico (hemoglobina, glucosa, hierro y perfil lipídico) "
               "para un seguimiento clínico más completo. ")
            + "La distribución de macronutrientes asigna un "
            f"{_pct_prot_pdf:.0f}% de proteínas para el aporte estructural"
            + (" fetal y placentario." if _embarazada_pdf else " y de mantenimiento muscular."),
            "No blood tests were recorded in this session. "
            + ("In pregnancy, it is a priority to evaluate Hemoglobin (to rule out gestational anemia) and "
               "fasting Glucose (to rule out gestational diabetes). " if _embarazada_pdf else
               "It is recommended to complete a basic panel (hemoglobin, glucose, iron, and lipid profile) "
               "for more complete clinical follow-up. ")
            + "The macronutrient distribution assigns "
            f"{_pct_prot_pdf:.0f}% protein for structural support"
            + (", fetal and placental." if _embarazada_pdf else " and muscle maintenance."))
    story.append(Paragraph(f"<b>{T('Explicación Clínica:', 'Clinical Explanation:')}</b> {_explic3}", estilo_explic))

    # ==========================================================================================
    # PÁGINA 2 — PLAN ALIMENTARIO DETALLADO Y RECOMENDACIONES CLÍNICAS
    # ==========================================================================================
    story.append(PageBreak())
    _membrete_institucional()

    _MOMENTO_EN_PDF = {"Desayuno": "Breakfast", "Merienda 1": "Morning Snack", "Almuerzo": "Lunch",
                        "Merienda 2": "Afternoon Snack", "Cena": "Dinner"}
    _MACRO_EN_PDF = {"Carbohidrato": "Carbohydrate", "Proteína": "Protein", "Grasa": "Fat"}

    def _mom_pdf(nombre):
        return T(nombre, _MOMENTO_EN_PDF.get(nombre, nombre))

    def _mac_pdf(nombre):
        return T(nombre, _MACRO_EN_PDF.get(nombre, nombre))

    def _alim_pdf(nombre):
        return T(nombre, FOOD_NOMBRE_EN.get(nombre, nombre)) if _idioma_pdf_en else nombre

    header2 = Table([
        [Paragraph(T("PLAN DE ALIMENTACIÓN Y PRESCRIPCIÓN DIETÉTICA", "MEAL PLAN & DIETARY PRESCRIPTION"), estilo_pagina2_tit),
         Paragraph(T("Página 2 de 2", "Page 2 of 2"), estilo_meta)],
        [Paragraph(f"{T('Programa de Salud Escolar', 'School Health Program')} CIAM&amp;SUNI | {T('Paciente', 'Patient')}: {datos['nombre'].upper()} ({datos['edad']} {T('años', 'years')})",
                    estilo_subtitulo),
         Paragraph(f"<b>{T('Meta:', 'Goal:')}</b> {datos['rcd_final']:.2f} kcal/{T('día', 'day')}", estilo_meta)],
    ], colWidths=[CONTENT_W - 45 * mm, 45 * mm])
    header2.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header2)
    story.append(Spacer(1, 5))
    story.append(HRFlowable(width="100%", thickness=1.1, color=_rl_hex(AZUL_TXT)))
    story.append(Spacer(1, 8))

    # ---------------- 7. PLAN ALIMENTARIO (3 tablas cromáticas, datos reales seleccionados) ----------------
    story.append(Paragraph(T("7. PLAN ALIMENTARIO DETALLADO POR MACRONUTRIENTES", "7. DETAILED MEAL PLAN BY MACRONUTRIENT"), estilo_seccion2))

    def _tabla_macro_color(macro_key, titulo_col, color_cab, color_fila):
        filas_html = [[T("Momento", "Meal"), f"{T('Alimento', 'Food')} ({_mac_pdf(titulo_col)})",
                        "Kcal/100g", T("Porción Corregida", "Adjusted Portion"), T("Gramos Finales", "Final Grams")]]
        for fila in datos["dieta_filas"]:
            d = fila[macro_key]
            filas_html.append([_mom_pdf(fila["momento"]), _alim_pdf(d["alimento"]), f"{d['kcal']:.0f} kcal",
                                f"{d['porcion']:.1f} kcal", f"{d['gramos']:.1f} g"])
        _tot = datos["dieta_totales"][macro_key]
        filas_html.append(["TOTAL", "", "—", f"{_tot['porcion']:.1f} kcal", f"{_tot['gramos']:.1f} g"])
        t = Table(filas_html, colWidths=[24 * mm, 62 * mm, 24 * mm, 38 * mm, 30 * mm])
        n = len(filas_html)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _rl_hex(color_cab)),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [rl_colors.white, _rl_hex(color_fila)]),
            ("SPAN", (0, n - 1), (1, n - 1)),
            ("BACKGROUND", (0, n - 1), (-1, n - 1), _rl_hex(color_cab)),
            ("TEXTCOLOR", (0, n - 1), (-1, n - 1), rl_colors.white),
            ("FONTNAME", (0, n - 1), (-1, n - 1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, _rl_hex(LINEA)),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    if datos["tiene_dieta"]:
        story.append(_tabla_macro_color("Carbohidrato", "Carbohidrato", AZUL_CARB, AZUL_CARB_CLARO))
        story.append(Spacer(1, 8))
        story.append(_tabla_macro_color("Proteína", "Proteína", MORADO_PROT, MORADO_PROT_CLARO))
        story.append(Spacer(1, 8))
        story.append(_tabla_macro_color("Grasa", "Grasa", NARANJA_GRA, NARANJA_GRA_CLARO))
        story.append(Spacer(1, 6))
    else:
        story.append(Paragraph(T("Aún no se armó un plan de comidas en la Hoja 9.-DIETA durante esta sesión.",
                                  "No meal plan has been built yet in Sheet 9.-DIET during this session."),
                                estilo_texto))
        story.append(Spacer(1, 6))

    # ---------------- 8. RECOMENDACIONES CLÍNICAS Y GUÍA NUTRICIONAL ----------------
    story.append(Paragraph(T("8. RECOMENDACIONES CLÍNICAS Y GUÍA NUTRICIONAL", "8. CLINICAL RECOMMENDATIONS & NUTRITIONAL GUIDE"), estilo_seccion2))

    estilo_subcat = ParagraphStyle("SubcatRecom", parent=estilo_seccion2, fontSize=10.5,
                                    spaceBefore=6, spaceAfter=3)

    def _dedup(lst):
        vistos, out = set(), []
        for x in lst:
            if x not in vistos:
                vistos.add(x); out.append(x)
        return out

    _alimentos_recom, _acciones_recom, _evitar_recom = [], [], []

    _cat_imc_pdf = datos.get("categoria_imc", "")
    if _cat_imc_pdf == "Peso Saludable":
        _acciones_recom.append(T("Mantén tus hábitos actuales de alimentación balanceada y actividad física regular.",
                                  "Keep up your current balanced eating habits and regular physical activity."))
    elif _cat_imc_pdf == "Bajo Peso":
        _alimentos_recom.append(T("Incluye fuentes calóricas densas y saludables (frutos secos, palta, aceite de oliva, cereales integrales) para favorecer una ganancia de peso segura.",
                                   "Include dense, healthy caloric sources (nuts, avocado, olive oil, whole grains) to support safe weight gain."))
        _acciones_recom.append(T("Aumenta la frecuencia de comidas y consulta con tu médico o nutricionista para evaluar tu ingesta calórica.",
                                  "Increase your meal frequency and consult your doctor or nutritionist to assess your caloric intake."))
    elif _cat_imc_pdf in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"]:
        _alimentos_recom.append(T("Prioriza verduras, frutas enteras, proteínas magras y granos integrales; reduce el tamaño de las porciones de forma gradual.",
                                   "Prioritize vegetables, whole fruits, lean proteins, and whole grains; gradually reduce portion sizes."))
        _evitar_recom.append(T("Evita bebidas azucaradas, frituras y alimentos ultraprocesados de alta densidad calórica.",
                                "Avoid sugary drinks, fried foods, and high-calorie-density ultra-processed foods."))

    for _param, _valtxt, _cat in datos.get("examen", []):
        _color_e = CATEGORIA_SEMAFORO.get(_cat, "gris")
        if _color_e not in ("ambar", "rojo"):
            continue
        if _param == "Hemoglobina":
            _alimentos_recom.append(T("Prioriza alimentos ricos en hierro (carnes rojas, legumbres, espinaca) junto con vitamina C para mejorar su absorción.",
                                       "Prioritize iron-rich foods (red meat, legumes, spinach) along with vitamin C to improve absorption."))
            _evitar_recom.append(T("Evita el té o café junto con las comidas principales, ya que reducen la absorción del hierro.",
                                    "Avoid tea or coffee with main meals, as they reduce iron absorption."))
        elif _param == "Triglicéridos":
            _alimentos_recom.append(T("Aumenta el consumo de fibra (avena, legumbres, verduras) y grasas saludables (pescado, aceite de oliva).",
                                       "Increase your fiber intake (oats, legumes, vegetables) and healthy fats (fish, olive oil)."))
            _evitar_recom.append(T("Reduce azúcares simples, harinas refinadas, grasas saturadas y alcohol.",
                                    "Reduce simple sugars, refined flours, saturated fats, and alcohol."))
        elif _param == "Glucosa" and _cat == "Hipoglucemia":
            _alimentos_recom.append(T("Combina carbohidratos de absorción compleja con proteína en cada comida para estabilizar tu glucosa.",
                                       "Combine slow-absorption carbohydrates with protein in each meal to stabilize your glucose."))
            _acciones_recom.append(T("Evita el ayuno prolongado; realiza comidas y meriendas frecuentes a lo largo del día.",
                                      "Avoid prolonged fasting; eat frequent meals and snacks throughout the day."))
        elif _param == "Glucosa":
            _alimentos_recom.append(T("Prioriza carbohidratos de absorción lenta (granos integrales, legumbres) y aumenta el consumo de fibra.",
                                       "Prioritize slow-absorption carbohydrates (whole grains, legumes) and increase your fiber intake."))
            _evitar_recom.append(T("Reduce azúcares simples y controla el tamaño de tus porciones de carbohidratos.",
                                    "Reduce simple sugars and watch your carbohydrate portion sizes."))
        elif _param == "Colesterol":
            _alimentos_recom.append(T("Prioriza grasas saludables como el aceite de oliva, la palta y el pescado.",
                                       "Prioritize healthy fats such as olive oil, avocado, and fish."))
            _evitar_recom.append(T("Reduce frituras, grasas saturadas y alimentos ultraprocesados.",
                                    "Reduce fried foods, saturated fats, and ultra-processed foods."))
        elif _param == "Hierro":
            _alimentos_recom.append(T("Aumenta el consumo de alimentos ricos en hierro (carnes, legumbres, vegetales verdes).",
                                       "Increase your intake of iron-rich foods (meat, legumes, green vegetables)."))

    if _embarazada_pdf:
        _alimentos_recom.append(T("Incluye lácteos pasteurizados, carnes y huevos bien cocidos, y cítricos junto con las proteínas.",
                                   "Include pasteurized dairy, well-cooked meats and eggs, and citrus fruits along with your proteins."))
        _acciones_recom.append(T("Mantén un consumo de 2.5 a 3.0 litros de agua al día y sigue la suplementación indicada por tu ginecólogo-obstetra (Sulfato Ferroso + Ácido Fólico).",
                                  "Maintain a water intake of 2.5 to 3.0 liters per day and follow the supplementation prescribed by your OB-GYN (Ferrous Sulfate + Folic Acid)."))
        _evitar_recom.append(T("Evita pescados/carnes crudos o poco cocidos, embutidos sin cocer, lácteos no pasteurizados y el exceso de cafeína (máx. 200 mg/día).",
                                "Avoid raw or undercooked fish/meat, uncooked cold cuts, unpasteurized dairy, and excess caffeine (max. 200 mg/day)."))
    else:
        _acciones_recom.append(T("Mantén un consumo adecuado de agua a lo largo del día (aprox. 30-35 ml por kg de peso corporal) y respeta el esquema de 5 comidas diarias.",
                                  "Maintain adequate water intake throughout the day (approx. 30-35 ml per kg of body weight) and follow the 5-meals-a-day schedule."))
        _evitar_recom.append(T("Evita saltarte comidas y el exceso de alimentos ultraprocesados.",
                                "Avoid skipping meals and excess ultra-processed foods."))
        if _edad_pdf < 18:
            _evitar_recom.append(T("Evita bebidas energizantes y limita la cafeína (máx. 100 mg/día en adolescentes).",
                                    "Avoid energy drinks and limit caffeine (max. 100 mg/day for adolescents)."))

    _alimentos_recom = _dedup(_alimentos_recom)
    _acciones_recom = _dedup(_acciones_recom)
    _evitar_recom = _dedup(_evitar_recom)

    story.append(Paragraph(T("🥦 Alimentos Recomendados", "🥦 Recommended Foods"), estilo_subcat))
    for r in (_alimentos_recom or [T("Mantén una alimentación variada y balanceada según tu plan asignado.",
                                      "Maintain a varied, balanced diet according to your assigned plan.")]):
        story.append(Paragraph(f"•  {r}", estilo_recom_txt))

    story.append(Paragraph(T("✅ Acciones / Conductas Saludables", "✅ Healthy Actions / Behaviors"), estilo_subcat))
    for r in (_acciones_recom or [T("Continúa con tus hábitos actuales de alimentación y actividad física.",
                                     "Continue with your current eating habits and physical activity.")]):
        story.append(Paragraph(f"•  {r}", estilo_recom_txt))

    story.append(Paragraph(T("⚠️ Alimentos y Conductas a Evitar", "⚠️ Foods & Behaviors to Avoid"), estilo_subcat))
    for r in (_evitar_recom or [T("No se detectaron alertas específicas con la información ingresada.",
                                   "No specific alerts were detected with the information entered.")]):
        story.append(Paragraph(f"•  {r}", estilo_recom_txt))

    # ---------------- PIE DE PÁGINA MÉDICO-LEGAL ----------------
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.6, color=_rl_hex(LINEA)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        T("<b>AVISO MÉDICO-LEGAL IMPORTANTE:</b> Este documento representa un informe automatizado de "
          "distribución de porciones y energía generado por el aplicativo CIAM&amp;SUNI con fines estrictamente "
          "educativos y de investigación escolar (Proyecto de Salud Escolar, Grupo N°04, 5° \"C\" Secundaria, "
          "C.E.P. \"Santa María Reina\", Chiclayo). NO SUSTITUYE LA EVALUACIÓN CLÍNICA PRENATAL, EL DIAGNÓSTICO "
          "MÉDICO NI LAS INDICACIONES PRESCRIPTIVAS DE UN MÉDICO GINECÓLOGO-OBSTETRA O NUTRICIONISTA CLÍNICO "
          "COLEGIADO. Ningún dato personal o de salud es almacenado en servidores externos.",
          "<b>IMPORTANT MEDICAL-LEGAL NOTICE:</b> This document represents an automated portion and energy "
          "distribution report generated by the CIAM&amp;SUNI application for strictly educational and school "
          "research purposes (School Health Project, Group No. 04, 5th Grade \"C\" Secondary School, "
          "C.E.P. \"Santa María Reina\", Chiclayo). IT DOES NOT REPLACE PRENATAL CLINICAL EVALUATION, MEDICAL "
          "DIAGNOSIS, OR THE PRESCRIPTIVE INDICATIONS OF A LICENSED OB-GYN OR CLINICAL NUTRITIONIST. No personal "
          "or health data is stored on external servers."), estilo_aviso))

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


# Paleta pastel exacta pedida para el panel de tablas de referencia clínica (Hemoglobina / Hierro)
_REF_PASTEL = {
    "normal":   ("#E6F4EA", "#137333"),
    "leve":     ("#FEF7E0", "#B06000"),
    "moderada": ("#FFE8D6", "#C45100"),
    "grave":    ("#FCE8E6", "#C5221F"),
    "bajo":     ("#E8F0FE", "#1A56DB"),
    "alto":     ("#F3E8FF", "#7C3AED"),
}

# Todos los iconos del panel de referencia llevan un tamaño FIJO (evita el bug del SVG gigante
# cuando no se define width/height y el navegador usa su tamaño intrínseco por defecto).
_ICONO_ESTILO = 'style="width:24px;height:24px;flex-shrink:0;display:block;"'

_ICONO_GOTA = f"""<svg {_ICONO_ESTILO} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 5 C16 5 6 17 6 23 a10 10 0 0 0 20 0 C26 17 16 5 16 5 Z" fill="#FCE8E6" stroke="#C5221F" stroke-width="2"/>
</svg>"""
_ICONO_MOLECULA = f"""<svg {_ICONO_ESTILO} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="10" cy="10" r="4.2" fill="#E8F0FE" stroke="#1A56DB" stroke-width="1.8"/>
    <circle cx="22" cy="10" r="4.2" fill="#F3E8FF" stroke="#7C3AED" stroke-width="1.8"/>
    <circle cx="16" cy="21" r="4.2" fill="#E6F4EA" stroke="#137333" stroke-width="1.8"/>
    <path d="M12.8 12.5 L14.5 18 M19.2 12.5 L17.5 18 M13.7 9.5 L18.3 9.5" stroke="#8E8E93" stroke-width="1.4"/>
</svg>"""
_ICONO_LIPIDO = f"""<svg {_ICONO_ESTILO} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 6 C12 6 5 16 5 21 a7 7 0 0 0 14 0 C19 16 12 6 12 6 Z" fill="#FFE8D6" stroke="#C45100" stroke-width="1.8"/>
    <path d="M22 12 C22 12 18 18 18 21.5 a4.5 4.5 0 0 0 9 0 C27 18 22 12 22 12 Z" fill="#FFE8D6" stroke="#C45100" stroke-width="1.8"/>
</svg>"""
_ICONO_AZUCAR = f"""<svg {_ICONO_ESTILO} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="7" y="7" width="12" height="12" rx="2" fill="#FEF7E0" stroke="#B06000" stroke-width="1.8"/>
    <circle cx="23" cy="22" r="5" fill="#FEF7E0" stroke="#B06000" stroke-width="1.8"/>
</svg>"""
_ICONO_CORAZON = f"""<svg {_ICONO_ESTILO} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 25 C7 19 4 14 7 10 C9 7 13.5 7 16 11 C18.5 7 23 7 25 10 C28 14 25 19 16 25 Z"
          fill="#E6F4EA" stroke="#137333" stroke-width="1.8" stroke-linejoin="round"/>
</svg>"""


def _ref_chip(texto, categoria):
    fondo, color_txt = _REF_PASTEL[categoria]
    return f'<div class="ref-chip" style="background:{fondo};color:{color_txt};">{texto}</div>'


def _ref_header_chip(texto, categoria=None):
    if categoria:
        fondo, color_txt = _REF_PASTEL[categoria]
        return f'<div class="ref-header-chip" style="background:{fondo};color:{color_txt};">{texto}</div>'
    return f'<div class="ref-header-chip">{texto}</div>'


def _panel_referencia_una_fila(icono, titulo, categorias):
    """Panel pastel de una sola fila de datos (sin columna de 'Grupo Poblacional'), usado
    para Triglicéridos, Glucosa y Colesterol — cada parámetro con su propia tarjeta,
    sin compartir tabla con los demás."""
    n = len(categorias)
    cols_css = " ".join(["1fr"] * n)
    html = ['<div class="ref-panel">']
    html.append(f'<div class="ref-panel-title">{icono} {titulo}</div>')
    html.append(f'<div class="ref-row" style="grid-template-columns:{cols_css};">')
    for etiqueta, _valor, color_key in categorias:
        html.append(_ref_header_chip(etiqueta, color_key))
    html.append('</div>')
    html.append(f'<div class="ref-row" style="grid-template-columns:{cols_css};">')
    for _etiqueta, valor, color_key in categorias:
        html.append(_ref_chip(valor, color_key))
    html.append('</div>')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def panel_referencia_hemo_hierro():
    """Panel de tarjetas pastel (Prompt 1) que reemplaza las tablas planas de Hemoglobina y
    Hierro: contenedor con bordes redondeados, encabezados por columna en color y una
    tarjeta por cada rango de dato, en tonos suaves — sin fondos oscuros ni negros."""
    filas_hemo = [
        ("Niños 5–11 años", "≥ 11,5 g/dL", "11,0 – 11,4", "8,0 – 10,9", "< 8,0"),
        ("Adolescentes", "≥ 12,0 g/dL", "11,0 – 11,9", "8,0 – 10,9", "< 8,0"),
        ("Mujeres", "≥ 12,0 g/dL", "11,0 – 11,9", "8,0 – 10,9", "< 8,0"),
        ("Hombres", "≥ 13,0 g/dL", "12,0 – 12,9", "8,0 – 10,9", "< 8,0"),
        ("Mujeres embarazadas", "≥ 11,0 g/dL", "10,0 – 10,9", "7,0 – 9,9", "< 7,0"),
    ]
    filas_hierro = [
        ("Niños y adolescentes", "< 50", "50 – 120", "> 120"),
        ("Mujeres", "< 50", "50 – 170", "> 170"),
        ("Hombres", "< 65", "65 – 175", "> 175"),
    ]

    html = ['<div class="ref-panel">']
    html.append(f'<div class="ref-panel-title">{_ICONO_GOTA} Hemoglobina (g/dL)</div>')
    html.append('<div class="ref-row" style="grid-template-columns:1.3fr 1fr 1fr 1fr 1fr;">')
    html.append(_ref_header_chip("Grupo Poblacional"))
    html.append(_ref_header_chip("Normal", "normal"))
    html.append(_ref_header_chip("Anemia Leve", "leve"))
    html.append(_ref_header_chip("Anemia Moderada", "moderada"))
    html.append(_ref_header_chip("Anemia Grave", "grave"))
    html.append('</div>')
    for grupo, normal, leve, moderada, grave in filas_hemo:
        html.append('<div class="ref-row" style="grid-template-columns:1.3fr 1fr 1fr 1fr 1fr;">')
        html.append(f'<div class="ref-group-label">{grupo}</div>')
        html.append(_ref_chip(normal, "normal"))
        html.append(_ref_chip(leve, "leve"))
        html.append(_ref_chip(moderada, "moderada"))
        html.append(_ref_chip(grave, "grave"))
        html.append('</div>')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)

    html2 = ['<div class="ref-panel">']
    html2.append(f'<div class="ref-panel-title">{_ICONO_MOLECULA} Hierro Sérico (µg/dL)</div>')
    html2.append('<div class="ref-row" style="grid-template-columns:1.3fr 1fr 1fr 1fr;">')
    html2.append(_ref_header_chip("Grupo Poblacional"))
    html2.append(_ref_header_chip("Bajo", "bajo"))
    html2.append(_ref_header_chip("Normal", "normal"))
    html2.append(_ref_header_chip("Alto", "alto"))
    html2.append('</div>')
    for grupo, bajo, normal, alto in filas_hierro:
        html2.append('<div class="ref-row" style="grid-template-columns:1.3fr 1fr 1fr 1fr;">')
        html2.append(f'<div class="ref-group-label">{grupo}</div>')
        html2.append(_ref_chip(bajo, "bajo"))
        html2.append(_ref_chip(normal, "normal"))
        html2.append(_ref_chip(alto, "alto"))
        html2.append('</div>')
    html2.append('</div>')
    st.markdown("".join(html2), unsafe_allow_html=True)


def panel_referencia_trigli_gluco_coles():
    """Tres paneles pastel INDEPENDIENTES (uno por parámetro) para Triglicéridos, Glucosa
    y Colesterol — mismo estilo de tarjetas que Hemoglobina/Hierro, cada uno con su propia
    tabla, sin compartir columnas entre sí."""
    _panel_referencia_una_fila(_ICONO_LIPIDO, "Triglicéridos (mg/dL)", [
        ("Normal", "< 150", "normal"),
        ("Límite Alto", "150 – 199", "leve"),
        ("Alto", "200 – 499", "moderada"),
        ("Muy Alto", "≥ 500", "grave"),
    ])
    _panel_referencia_una_fila(_ICONO_AZUCAR, "Glucosa (mg/dL)", [
        ("Hipoglucemia", "< 70", "leve"),
        ("Normal", "70 – 99", "normal"),
        ("Prediabetes", "100 – 125", "moderada"),
        ("Diabetes", "≥ 126", "grave"),
    ])
    _panel_referencia_una_fila(_ICONO_CORAZON, "Colesterol (mg/dL)", [
        ("Deseable", "< 200", "normal"),
        ("Límite Alto", "200 – 239", "leve"),
        ("Alto", "≥ 240", "grave"),
    ])



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
        "Carbohidrato": {"Avena cocida": 150, "Pan integral": 70, "Cereal integral": 110, "Manzana": 95, "Tostada de pan de centeno": 65, "Pera": 100, "Batata cocida": 90, "Mandarina": 45, "Avena": 375, "Arroz blanco": 416.33, "Yuca": 173, "Granola": 419.35, "Quinoa": 363.64, "Spaghetti": 423.08, "Papa": 104, "Camote": 86, "Pan blanco": 266, "Cebada cocida": 396, "Cuscús": 409.09, "Plátano": 362.07, "Mango": 364.86, "Granola clásica": 419.35, "Cancha": 535.71},
        "Proteína": {"Huevo hervido": 155, "Claras de huevo": 52, "Leche descremada": 34, "Queso cottage": 98, "Queso ricotta": 174, "Jamón serrano": 241, "Pechuga de pollo (sin piel)": 165, "Pechuga de pavo": 135, "Lomo de res / ternera": 217, "Atún en agua": 116, "Salmón": 206, "Lomo de cerdo": 143, "Camarones / Langostinos": 99, "Queso Cottage": 98, "Yogur griego natural": 59, "Huevo entero": 155, "Tofu firme": 76, "Lentejas (cocidas)": 116, "Garbanzos (cocidos)": 164, "Seitán": 118, "Maní / Cacahuate": 567},
        "Grasa": {"Palta": 160, "Almendras": 573.33, "Mantequilla de maní": 88, "Semillas de chía": 86, "Nueces": 653.57, "Crema de almendra": 64, "Mayonesa": 316.67, "Maní": 500, "Tocino": 537.5, "Salmón (graso)": 116},
    },
    "Merienda 1": {
        "Carbohidrato": {"Piña": 50, "Manzana verde": 52, "Uvas": 69, "Kiwi": 61, "Pan pita integral": 275, "Zanahoria cruda": 41, "Avena": 375, "Arroz blanco": 416.33, "Yuca": 173, "Granola": 419.35, "Quinoa": 363.64, "Spaghetti": 423.08, "Papa": 104, "Camote": 86, "Pan blanco": 266, "Cebada cocida": 396, "Cuscús": 409.09, "Plátano": 362.07, "Mango": 364.86, "Granola clásica": 419.35, "Cancha": 535.71},
        "Proteína": {"Yogur natural": 61, "Atún": 132, "Clara de huevo cocida": 52, "Jamón serrano": 241, "Pechuga de pollo (sin piel)": 165, "Pechuga de pavo": 135, "Lomo de res / ternera": 217, "Atún en agua": 116, "Salmón": 206, "Lomo de cerdo": 143, "Camarones / Langostinos": 99, "Queso Cottage": 98, "Yogur griego natural": 59, "Huevo entero": 155, "Tofu firme": 76, "Lentejas (cocidas)": 116, "Garbanzos (cocidos)": 164, "Seitán": 118, "Maní / Cacahuate": 567},
        "Grasa": {"Pistachos": 52, "Avellanas": 68, "Semillas de calabaza": 75, "Aceite de oliva": 104, "Mayonesa": 316.67, "Palta": 160, "Maní": 500, "Almendras": 573.33, "Nueces": 653.57, "Tocino": 537.5, "Salmón (graso)": 116},
    },
    "Almuerzo": {
        "Carbohidrato": {"Arroz integral": 123, "Quinoa cocida": 120, "Couscous cocido": 112, "Garbanzos cocidos": 164, "Lentejas": 116, "Avena": 375, "Arroz blanco": 416.33, "Yuca": 173, "Granola": 419.35, "Quinoa": 363.64, "Spaghetti": 423.08, "Papa": 104, "Camote": 86, "Pan blanco": 266, "Cebada cocida": 396, "Cuscús": 409.09, "Plátano": 362.07, "Mango": 364.86, "Granola clásica": 419.35, "Cancha": 535.71},
        "Proteína": {"Pechuga de pollo": 165, "Fillete de res magra": 217, "Pescado blanco": 96, "Salmón a la plancha": 208, "Pavo al horno": 135, "Bacalao a la plancha": 105, "Pechuga de pollo (sin piel)": 165, "Pechuga de pavo": 135, "Lomo de res / ternera": 217, "Atún en agua": 116, "Salmón": 206, "Lomo de cerdo": 143, "Camarones / Langostinos": 99, "Queso Cottage": 98, "Yogur griego natural": 59, "Huevo entero": 155, "Tofu firme": 76, "Lentejas (cocidas)": 116, "Garbanzos (cocidos)": 164, "Seitán": 118, "Maní / Cacahuate": 567},
        "Grasa": {"Aceite de oliva": 104, "Aceitunas verdes": 45, "Queso parmesano": 91, "Queso gouda": 66, "Aguacate": 160, "Aceite de linaza": 84, "Mayonesa": 316.67, "Palta": 160, "Maní": 500, "Almendras": 573.33, "Nueces": 653.57, "Tocino": 537.5, "Salmón (graso)": 116},
    },
    "Merienda 2": {
        "Carbohidrato": {"Pan integral": 70, "Galletas integrales": 120, "Banana": 89, "Pan árabe": 275, "Barra de granola": 180, "Pan de maíz": 266, "Avena": 375, "Arroz blanco": 416.33, "Yuca": 173, "Granola": 419.35, "Quinoa": 363.64, "Spaghetti": 423.08, "Papa": 104, "Camote": 86, "Pan blanco": 266, "Cebada cocida": 396, "Cuscús": 409.09, "Plátano": 362.07, "Mango": 364.86, "Granola clásica": 419.35, "Cancha": 535.71},
        "Proteína": {"Queso ricotta": 174, "Yogurt griego": 97, "Pollo desmenuzado": 165, "Yogur descremado": 34, "Clara de huevo": 52, "Pechuga de pollo (sin piel)": 165, "Pechuga de pavo": 135, "Lomo de res / ternera": 217, "Atún en agua": 116, "Salmón": 206, "Lomo de cerdo": 143, "Camarones / Langostinos": 99, "Queso Cottage": 98, "Yogur griego natural": 59, "Huevo entero": 155, "Tofu firme": 76, "Lentejas (cocidas)": 116, "Garbanzos (cocidos)": 164, "Seitán": 118, "Maní / Cacahuate": 567},
        "Grasa": {"Anacardos": 53, "Queso brie": 64, "Almendras fileteadas": 109, "Mantequilla": 94, "Mayonesa": 316.67, "Palta": 160, "Maní": 500, "Almendras": 573.33, "Nueces": 653.57, "Tocino": 537.5, "Salmón (graso)": 116},
    },
    "Cena": {
        "Carbohidrato": {"Papa sancochada": 87, "Batata": 86, "Palomitas de maíz": 387, "Camote": 86, "Avena": 375, "Arroz blanco": 416.33, "Yuca": 173, "Granola": 419.35, "Quinoa": 363.64, "Spaghetti": 423.08, "Papa": 104, "Pan blanco": 266, "Cebada cocida": 396, "Cuscús": 409.09, "Plátano": 362.07, "Mango": 364.86, "Granola clásica": 419.35, "Cancha": 535.71},
        "Proteína": {"Huevos revueltos": 148, "Sardinas": 208, "Pechuga de pavo": 135, "Pechuga de pollo": 165, "Filete de pescado blanco": 96, "Pechuga de pollo (sin piel)": 165, "Lomo de res / ternera": 217, "Atún en agua": 116, "Salmón": 206, "Lomo de cerdo": 143, "Camarones / Langostinos": 99, "Queso Cottage": 98, "Yogur griego natural": 59, "Huevo entero": 155, "Tofu firme": 76, "Lentejas (cocidas)": 116, "Garbanzos (cocidos)": 164, "Seitán": 118, "Maní / Cacahuate": 567},
        "Grasa": {"Aceitunas": 55, "Queso crema": 202, "Aceite de aguacate": 84, "Semillas de girasol": 54, "Mayonesa": 316.67, "Palta": 160, "Maní": 500, "Almendras": 573.33, "Nueces": 653.57, "Tocino": 537.5, "Salmón (graso)": 116},
    },
}

# =========================================================================================
# FILTRO DE SEGURIDAD ALIMENTARIA — MODO EMBARAZO (FDA, "Seguridad Alimentaria para Futuras
# Mamás"): bloquea alimentos de alto riesgo microbiológico (Listeria, Salmonella, Toxoplasma).
# =========================================================================================
_PALABRAS_RIESGO_EMBARAZO = [
    "crudo", "cruda", "crudos", "crudas", "semicocid", "ceviche", "tiradito", "sushi", "sashimi",
    "tártaro", "tartar", "carpaccio", "mayonesa", "término medio", "jamón serrano", "embutido",
    "queso fresco artesanal", "queso artesanal", "no pasteurizad", "leche cruda",
]


def _es_alimento_riesgo_embarazo(nombre_alimento):
    """True si el nombre del alimento coincide con un ítem de alto riesgo microbiológico
    (pescado/marisco crudo, huevo crudo, embutidos sin cocer, lácteos no pasteurizados, etc.)."""
    _n = (nombre_alimento or "").lower()
    return any(_p in _n for _p in _PALABRAS_RIESGO_EMBARAZO)


def dieta_filtrada_para(comida, macro, embarazada_flag):
    """Devuelve el diccionario {alimento: kcal} de DIETA[comida][macro], quitando los
    alimentos de alto riesgo si el Modo Embarazo está activo."""
    _opciones = DIETA[comida][macro]
    if not embarazada_flag:
        return _opciones
    return {k: v for k, v in _opciones.items() if not _es_alimento_riesgo_embarazo(k)}

# =========================================================================================
# TRADUCCIÓN DE NOMBRES DE ALIMENTOS DEL PLAN DE COMIDAS (Hoja 9.-DIETA) AL INGLÉS
# Las claves de DIETA se mantienen SIEMPRE en español (son la fuente de verdad usada en
# session_state, cálculos de kcal/porciones/gramos y el PDF). Este diccionario solo se usa
# para mostrar el nombre traducido en pantalla (selectbox, tablas, resúmenes) cuando el
# idioma activo es English, vía la función _dieta_nombre().
# =========================================================================================
DIETA_NOMBRE_EN = {
    "Aceite de aguacate": "Avocado Oil",
    "Aceite de linaza": "Flaxseed Oil",
    "Aceite de oliva": "Olive Oil",
    "Aceitunas": "Olives",
    "Aceitunas verdes": "Green Olives",
    "Aguacate": "Avocado",
    "Almendras": "Almonds",
    "Almendras fileteadas": "Sliced Almonds",
    "Anacardos": "Cashews",
    "Arroz blanco": "White Rice",
    "Arroz integral": "Brown Rice",
    "Atún": "Tuna",
    "Atún en agua": "Tuna in Water",
    "Avellanas": "Hazelnuts",
    "Avena": "Oats",
    "Avena cocida": "Cooked Oatmeal",
    "Bacalao a la plancha": "Grilled Cod",
    "Banana": "Banana",
    "Barra de granola": "Granola Bar",
    "Batata": "Sweet Potato",
    "Batata cocida": "Boiled Sweet Potato",
    "Camarones / Langostinos": "Shrimp / Prawns",
    "Camote": "Sweet Potato",
    "Cancha": "Toasted Corn Nuts",
    "Cebada cocida": "Cooked Barley",
    "Cereal integral": "Whole Grain Cereal",
    "Clara de huevo": "Egg White",
    "Clara de huevo cocida": "Cooked Egg White",
    "Claras de huevo": "Egg Whites",
    "Couscous cocido": "Cooked Couscous",
    "Crema de almendra": "Almond Butter",
    "Cuscús": "Couscous",
    "Filete de pescado blanco": "White Fish Fillet",
    "Fillete de res magra": "Lean Beef Fillet",
    "Galletas integrales": "Whole Grain Crackers",
    "Garbanzos (cocidos)": "Chickpeas (Cooked)",
    "Garbanzos cocidos": "Cooked Chickpeas",
    "Granola": "Granola",
    "Granola clásica": "Classic Granola",
    "Huevo entero": "Whole Egg",
    "Huevo hervido": "Boiled Egg",
    "Huevos revueltos": "Scrambled Eggs",
    "Jamón serrano": "Cured Ham",
    "Kiwi": "Kiwi",
    "Leche descremada": "Skim Milk",
    "Lentejas": "Lentils",
    "Lentejas (cocidas)": "Lentils (Cooked)",
    "Lomo de cerdo": "Pork Loin",
    "Lomo de res / ternera": "Beef / Veal Loin",
    "Mandarina": "Tangerine",
    "Mango": "Mango",
    "Mantequilla": "Butter",
    "Mantequilla de maní": "Peanut Butter",
    "Manzana": "Apple",
    "Manzana verde": "Green Apple",
    "Maní": "Peanuts",
    "Maní / Cacahuate": "Peanuts",
    "Mayonesa": "Mayonnaise",
    "Nueces": "Walnuts",
    "Palomitas de maíz": "Popcorn",
    "Palta": "Avocado",
    "Pan blanco": "White Bread",
    "Pan de maíz": "Corn Bread",
    "Pan integral": "Whole Wheat Bread",
    "Pan pita integral": "Whole Wheat Pita Bread",
    "Pan árabe": "Pita Bread",
    "Papa": "Potato",
    "Papa sancochada": "Boiled Potato",
    "Pavo al horno": "Baked Turkey",
    "Pechuga de pavo": "Turkey Breast",
    "Pechuga de pollo": "Chicken Breast",
    "Pechuga de pollo (sin piel)": "Chicken Breast (Skinless)",
    "Pera": "Pear",
    "Pescado blanco": "White Fish",
    "Pistachos": "Pistachios",
    "Piña": "Pineapple",
    "Plátano": "Plantain",
    "Pollo desmenuzado": "Shredded Chicken",
    "Queso Cottage": "Cottage Cheese",
    "Queso brie": "Brie Cheese",
    "Queso cottage": "Cottage Cheese",
    "Queso crema": "Cream Cheese",
    "Queso gouda": "Gouda Cheese",
    "Queso parmesano": "Parmesan Cheese",
    "Queso ricotta": "Ricotta Cheese",
    "Quinoa": "Quinoa",
    "Quinoa cocida": "Cooked Quinoa",
    "Salmón": "Salmon",
    "Salmón (graso)": "Salmon (Fatty)",
    "Salmón a la plancha": "Grilled Salmon",
    "Sardinas": "Sardines",
    "Seitán": "Seitan",
    "Semillas de calabaza": "Pumpkin Seeds",
    "Semillas de chía": "Chia Seeds",
    "Semillas de girasol": "Sunflower Seeds",
    "Spaghetti": "Spaghetti",
    "Tocino": "Bacon",
    "Tofu firme": "Firm Tofu",
    "Tostada de pan de centeno": "Rye Toast",
    "Uvas": "Grapes",
    "Yogur descremado": "Skim Yogurt",
    "Yogur griego natural": "Plain Greek Yogurt",
    "Yogur natural": "Plain Yogurt",
    "Yogurt griego": "Greek Yogurt",
    "Yuca": "Cassava",
    "Zanahoria cruda": "Raw Carrot",
}


def _dieta_nombre(nombre):
    """Devuelve el nombre del alimento del plan de comidas (Hoja 9.-DIETA) en el idioma
    activo. Las claves internas (session_state, cálculos, PDF) siguen siempre en español;
    esta función solo controla lo que se MUESTRA en pantalla."""
    if st.session_state.get("idioma", "Español") == "English":
        return DIETA_NOMBRE_EN.get(nombre, nombre)
    return nombre

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
    """Clasifica la hemoglobina según etapa y género. CORREGIDO: antes, una mujer en
    Adultez o Vejez (p. ej. 87 años) no encajaba en ninguna condición y el sistema
    devolvía 'Revisa Datos' en vez de un diagnóstico. Ahora el umbral de 'Mujer' se
    aplica a cualquier edad no-infantil, así el semáforo siempre calcula un resultado."""
    if valor is None or valor == 0:
        return "Introducir datos"
    if valor > 20:
        return "Valor Imposible"
    if etapa == "Niñez":
        if valor < 8: return "Anemia grave"
        elif valor <= 10.9: return "Anemia moderada"
        elif valor <= 11.4: return "Anemia leve"
        else: return "Normal"
    if genero == "Mujer":
        if valor < 8: return "Anemia grave"
        elif valor <= 10.9: return "Anemia moderada"
        elif valor <= 11.9: return "Anemia leve"
        else: return "Normal"
    if genero == "Hombre":
        if etapa == "Adolescencia":
            if valor < 8: return "Anemia grave"
            elif valor <= 10.9: return "Anemia moderada"
            elif valor <= 12.9: return "Anemia leve"
            else: return "Normal"
        else:  # Adultez / Vejez
            if valor < 8: return "Anemia grave"
            elif valor <= 10.9: return "Anemia moderada"
            elif valor <= 13.7: return "Anemia leve"
            else: return "Normal"
    # Solo se alcanza si el género no es "Hombre" ni "Mujer" (no debería ocurrir desde la UI)
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


MENSAJES_TRIAJE_CATEGORIA = {
    # Excepciones donde dos categorías comparten color de semáforo pero requieren mensajes
    # clínicos opuestos (p.ej. Hipoglucemia y Prediabetes son ambas "ambar" en Glucosa, pero
    # la Hipoglucemia NO debe recibir el consejo de "reducir azúcares").
    "Hipoglucemia": ("Tu glucosa está por debajo de lo recomendado. Evita el ayuno prolongado, realiza "
                      "comidas y meriendas frecuentes, y combina carbohidratos de absorción compleja con "
                      "proteína para estabilizar tus niveles."),
}


MENSAJES_TRIAJE_EN = {
    "Hemoglobina": {
        "verde": "Excellent balance! Your hemoglobin levels are in equilibrium. Keep prioritizing iron and quality proteins.",
        "ambar": "You're in a zone that needs attention. Prioritize iron-rich foods (red meat, legumes, spinach) along with vitamin C to improve absorption.",
        "rojo": "Your values suggest a risk of anemia. We recommend consulting a specialist and prioritizing iron and protein in your diet.",
        "gris": "Enter your hemoglobin value to get a personalized recommendation.",
    },
    "Triglicéridos": {
        "verde": "Great job! Your triglycerides are within the desirable range. Keep up your healthy fat intake and physical activity.",
        "ambar": "You're in a borderline zone. Consider reducing sugars and simple carbohydrates, and increasing fiber in your diet.",
        "rojo": "Your values are elevated. We recommend consulting a specialist and reducing saturated fats, sugars, and alcohol.",
        "gris": "Enter your triglyceride value to get a personalized recommendation.",
    },
    "Glucosa": {
        "verde": "Excellent! Your glucose is in a healthy range. Keep maintaining regular meal times.",
        "ambar": "You're in a zone that needs attention. Reduce simple sugars and watch your carbohydrate portion sizes.",
        "rojo": "Your values suggest metabolic risk. We recommend consulting a specialist as soon as possible.",
        "gris": "Enter your glucose value to get a personalized recommendation.",
    },
    "Colesterol": {
        "verde": "Great job! Your cholesterol is at a desirable level. Keep prioritizing healthy fats like olive oil and avocado.",
        "ambar": "You're in a borderline zone. Consider reducing fried foods and saturated fats, and increasing your fiber intake.",
        "rojo": "Your values are elevated. We recommend consulting a specialist and prioritizing a diet low in saturated fats.",
        "gris": "Enter your cholesterol value to get a personalized recommendation.",
    },
    "Hierro": {
        "verde": "Excellent! Your iron reserves are balanced. Keep prioritizing natural nutrients.",
        "ambar": "You're in a zone that needs attention. Increase your intake of iron-rich foods (meat, legumes, green vegetables).",
        "rojo": "Your values are out of range. We recommend consulting a specialist to evaluate your nutritional status.",
        "gris": "Enter your iron value to get a personalized recommendation.",
    },
}

MENSAJES_TRIAJE_CATEGORIA_EN = {
    "Hipoglucemia": ("Your glucose is below the recommended level. Avoid prolonged fasting, eat frequent "
                      "meals and snacks, and combine slow-absorption carbohydrates with protein to "
                      "stabilize your levels."),
}

_PARAMETRO_EN = {
    "Hemoglobina": "Hemoglobin", "Triglicéridos": "Triglycerides", "Glucosa": "Glucose",
    "Colesterol": "Cholesterol", "Hierro": "Iron",
}

_CATEGORIA_CLINICA_EN = {
    "Introducir datos": "Enter data", "Valor Imposible": "Impossible Value",
    "Revisa Datos": "Check Data", "Género no válido": "Invalid Gender", "Etapa no válida": "Invalid Stage",
    "Edad fuera de tabla (2-20 años)": "Age out of range (2-20 years)",
    "Anemia grave": "Severe Anemia", "Anemia moderada": "Moderate Anemia", "Anemia leve": "Mild Anemia",
    "Normal": "Normal", "Límite alto": "Borderline High", "Alto": "High", "Muy alto": "Very High",
    "Hipoglucemia": "Hypoglycemia", "Prediabetes": "Prediabetes", "Diabetes": "Diabetes",
    "Deseable": "Desirable", "Bajo": "Low",
}


def _parametro_txt(parametro):
    """Traduce el nombre de un parámetro clínico (Hemoglobina, Glucosa, etc.) según el idioma."""
    return T(parametro, _PARAMETRO_EN.get(parametro, parametro))


def _categoria_clinica_txt(categoria):
    """Traduce una categoría clínica (clave interna en español, usada para cálculos/colores)
    al idioma activo, sin modificar la clave interna."""
    return T(categoria, _CATEGORIA_CLINICA_EN.get(categoria, categoria))


def _mensaje_triaje_txt(parametro, categoria, color):
    """Devuelve el mensaje de recomendación de triaje ya traducido según el idioma activo."""
    if st.session_state.get("idioma", "Español") == "English":
        return MENSAJES_TRIAJE_CATEGORIA_EN.get(categoria) or MENSAJES_TRIAJE_EN.get(parametro, {}).get(color, "No recommendation available.")
    return MENSAJES_TRIAJE_CATEGORIA.get(categoria) or MENSAJES_TRIAJE.get(parametro, {}).get(color, "Sin recomendación disponible.")


def evaluar_estado_clinico(parametro, categoria):
    """Función de triaje digital: toma la categoría clínica ya calculada (ej. 'Anemia leve') y
    retorna el color de semáforo, su estilo visual y un mensaje de recomendación personalizado."""
    color = CATEGORIA_SEMAFORO.get(categoria, "gris")
    estilo = SEMAFORO_ESTILO[color]
    mensaje = MENSAJES_TRIAJE_CATEGORIA.get(categoria) or MENSAJES_TRIAJE.get(parametro, {}).get(color, "Sin recomendación disponible.")
    return {
        "colorSemaforo": color,
        "hex": estilo["hex"],
        "fondo": estilo["fondo"],
        "emoji": estilo["emoji"],
        "etiqueta": estilo["etiqueta"],
        "mensajePersonalizado": mensaje,
    }


# Colores pastel para el borde superior/inferior de la tarjeta y para las zonas del gauge.
PASTEL_ESTADO = {
    "verde": "#A8E6B5",
    "ambar": "#FFD59E",
    "rojo":  "#FFAFAF",
    "gris":  "#DADFE3",
}

# Iconos SVG ilustrativos fijos por parámetro (se colorean dinámicamente según el estado actual).
ICONOS_PARAMETRO = {
    "Hemoglobina": """<svg width="100%" height="100%" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 6 C20 6 9 20 9 27 a11 11 0 0 0 22 0 C31 20 20 6 20 6 Z"
              fill="{fondo}" stroke="{hex}" stroke-width="2.2" stroke-linejoin="round"/>
        <path d="M14 27 a6 6 0 0 0 6 6" stroke="{hex}" stroke-width="1.6" stroke-linecap="round" fill="none"/>
    </svg>""",
    "Triglicéridos": """<svg width="100%" height="100%" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 9 C15 9 8 19 8 24 a7 7 0 0 0 14 0 C22 19 15 9 15 9 Z" fill="{fondo}" stroke="{hex}" stroke-width="2"/>
        <path d="M27 15 C27 15 22 22 22 26 a5 5 0 0 0 10 0 C32 22 27 15 27 15 Z" fill="{fondo}" stroke="{hex}" stroke-width="2"/>
    </svg>""",
    "Glucosa": """<svg width="100%" height="100%" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="9" y="9" width="15" height="15" rx="2" fill="{fondo}" stroke="{hex}" stroke-width="2.2"/>
        <circle cx="28" cy="27" r="6" fill="{fondo}" stroke="{hex}" stroke-width="2.2"/>
        <circle cx="28" cy="27" r="1.6" fill="{hex}"/>
    </svg>""",
    "Colesterol": """<svg width="100%" height="100%" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 30 C10 23 6 17 9 12 C11.5 8 17 8 20 13 C23 8 28.5 8 31 12 C34 17 30 23 20 30 Z"
              fill="{fondo}" stroke="{hex}" stroke-width="2.2" stroke-linejoin="round"/>
        <path d="M9 22 L14 22 L17 16 L20 26 L23 20 L27 22 L31 22" stroke="{hex}" stroke-width="1.6"
              fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "Hierro": """<svg width="100%" height="100%" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 6 L32 11 V20 C32 27 27 32 20 34 C13 32 8 27 8 20 V11 Z"
              fill="{fondo}" stroke="{hex}" stroke-width="2.2" stroke-linejoin="round"/>
        <circle cx="20" cy="20" r="5" fill="none" stroke="{hex}" stroke-width="2"/>
        <circle cx="20" cy="20" r="1.6" fill="{hex}"/>
    </svg>""",
}


def _umbral_normal_hemo(etapa, genero):
    """Réplica el umbral 'Normal ≥' de hemoglobina usado en clasif_hemoglobina, para dibujar
    las zonas del gauge de forma coherente con el diagnóstico calculado."""
    if etapa == "Niñez":
        return 11.5
    if genero == "Mujer":
        return 12.0
    if genero == "Hombre" and etapa == "Adolescencia":
        return 13.0
    return 13.8


def _zonas_gauge(parametro, etapa=None, genero=None):
    """Devuelve (min, max, segmentos) para dibujar el medidor de 3 zonas de cada parámetro.
    Los cortes de Hemoglobina y Hierro se adaptan a la etapa/género del usuario, igual que
    la lógica de clasificación, para que el gauge sea coherente con el diagnóstico."""
    if parametro == "Hemoglobina":
        normal = _umbral_normal_hemo(etapa, genero)
        return 0, 20, [(0, 10.9, "rojo"), (10.9, normal, "ambar"), (normal, 20, "verde")]
    if parametro == "Triglicéridos":
        return 0, 500, [(0, 150, "verde"), (150, 200, "ambar"), (200, 500, "rojo")]
    if parametro == "Glucosa":
        return 0, 200, [(0, 70, "ambar"), (70, 100, "verde"), (100, 126, "ambar"), (126, 200, "rojo")]
    if parametro == "Colesterol":
        return 0, 400, [(0, 200, "verde"), (200, 240, "ambar"), (240, 400, "rojo")]
    if parametro == "Hierro":
        if etapa in ["Niñez", "Adolescencia"]:
            bajo, alto = 50, 120
        elif genero == "Hombre":
            bajo, alto = 65, 175
        else:
            bajo, alto = 50, 170
        tope = round(alto * 1.3)
        return 0, tope, [(0, bajo, "ambar"), (bajo, alto, "verde"), (alto, tope, "gris")]
    return 0, 100, [(0, 100, "gris")]


def _gauge_track_html(valor_num, min_v, max_v, segmentos):
    """Construye el HTML del medidor de 3 zonas con el marcador en la posición exacta del valor."""
    rango = max(max_v - min_v, 1e-6)
    piezas = ['<div class="sema-gauge-track">']
    for ini, fin, color_estado in segmentos:
        izq = max(0.0, min(100.0, (ini - min_v) / rango * 100))
        ancho = max(0.0, min(100.0 - izq, (fin - ini) / rango * 100))
        piezas.append(f'<div class="sema-gauge-seg" style="left:{izq:.1f}%;width:{ancho:.1f}%;background:{PASTEL_ESTADO[color_estado]};"></div>')
    if valor_num is not None:
        pct = max(0.0, min(100.0, (valor_num - min_v) / rango * 100))
        piezas.append(f'<div class="sema-gauge-marker" style="left:{pct:.1f}%;"></div>')
    piezas.append('</div>')
    return "".join(piezas)


def tarjeta_semaforo(parametro, valor_texto, categoria, valor_num=None, etapa=None, genero=None):
    """Tarjeta-gauge del Semáforo Clínico: icono ilustrativo fijo por parámetro, medidor de
    3 zonas (verde/ámbar/rojo) con marcador en el valor exacto, borde dinámico según el
    resultado, efecto hover de elevación y tooltip con la recomendación personalizada."""
    r = evaluar_estado_clinico(parametro, categoria)
    borde_pastel = PASTEL_ESTADO.get(r["colorSemaforo"], "#DADFE3")
    icono_svg = ICONOS_PARAMETRO.get(parametro, "").format(fondo=r["fondo"], hex=r["hex"])
    min_v, max_v, segmentos = _zonas_gauge(parametro, etapa, genero)
    gauge_html = _gauge_track_html(valor_num, min_v, max_v, segmentos)
    tooltip = r["mensajePersonalizado"].replace('"', "'")
    st.markdown(f"""
    <div class="sema-card" style="border-top:5px solid {borde_pastel};border-bottom:5px solid {borde_pastel};"
         title="{tooltip}">
        <div style="width:52px;height:52px;border-radius:50%;background:{r['fondo']};
                    display:flex;align-items:center;justify-content:center;
                    margin:0 auto 8px auto;padding:10px;box-sizing:border-box;">{icono_svg}</div>
        <div style="text-align:center;font-weight:800;color:#1C1C1E;font-size:0.92rem;letter-spacing:-0.01em;">{parametro}</div>
        <div style="text-align:center;color:#8E8E93;font-size:0.76rem;margin-bottom:2px;">{valor_texto}</div>
        {gauge_html}
        <div style="text-align:center;margin-top:6px;">
            <span style="background:{r['fondo']};color:{r['hex']};font-weight:800;font-size:0.78rem;
                         padding:4px 12px;border-radius:999px;">{r['emoji']} {categoria}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# Degradados vivos para el panel de resumen visual (mucho más saturados que los pastel de las
# tarjetas-gauge, a propósito, para que el resumen se vea como un "flujo" llamativo).
_GRAD_RESUMEN = {
    "verde": ("#34D399", "#059669"),
    "ambar": ("#FBBF24", "#D97706"),
    "rojo":  ("#F87171", "#DC2626"),
    "gris":  ("#A5B4C3", "#64748B"),
}


def panel_resumen_semaforo_creativo(resultados, nombre_saludo=""):
    """Reemplaza la tabla plana 'Parámetro | Valor | Resultado' por un panel de tarjetas
    en degradado conectadas con flechas — un resumen visual tipo 'flujo sanguíneo' del
    panel completo, muy colorido, con icono, valor grande y badge de resultado por tarjeta."""
    st.markdown("#### 🌈 Resumen Visual de tu Panel Sanguíneo")
    st.caption(f"El mismo diagnóstico de arriba, pero de un vistazo — como una línea de flujo, {nombre_saludo}. 🩸➡️🍬➡️🫀")
    piezas = ['<div style="display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;">']
    for i, (parametro, valor_texto, categoria) in enumerate(resultados):
        r = evaluar_estado_clinico(parametro, categoria)
        c1_, c2_ = _GRAD_RESUMEN.get(r["colorSemaforo"], _GRAD_RESUMEN["gris"])
        icono_svg = ICONOS_PARAMETRO.get(parametro, "").format(fondo="rgba(255,255,255,0.30)", hex="#FFFFFF")
        piezas.append(f'''
        <div class="cp5-card" style="flex:1;min-width:150px;text-align:center;
             background:linear-gradient(155deg,{c1_} 0%,{c2_} 100%);padding:16px 12px;">
            <div style="width:42px;height:42px;margin:0 auto 8px auto;">{icono_svg}</div>
            <div class="cp5-title" style="font-size:0.92rem;margin-bottom:2px;">{parametro}</div>
            <div style="font-size:0.78rem;opacity:0.92;margin-bottom:8px;">{valor_texto}</div>
            <div style="background:rgba(255,255,255,0.28);border-radius:999px;padding:5px 10px;
                        font-weight:800;font-size:0.78rem;display:inline-block;">{r['emoji']} {categoria}</div>
        </div>''')
        if i < len(resultados) - 1:
            piezas.append('<div style="display:flex;align-items:center;font-size:1.5rem;color:#B0B8C1;padding:0 2px;">→</div>')
    piezas.append('</div>')
    st.markdown("".join(piezas), unsafe_allow_html=True)


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

EFECTOS_PARAMETRO_EN = {
    "Hemoglobina": {
        "verde": "good oxygenation of your brain and muscles",
        "ambar": "somewhat reduced oxygenation, which can cause mild tiredness",
        "rojo": "insufficient oxygenation due to a possible case of anemia",
        "gris": "not enough data to evaluate your oxygenation",
    },
    "Triglicéridos": {
        "verde": "a balanced fat metabolism",
        "ambar": "a buildup of fat in the blood that is starting to become noticeable",
        "rojo": "a cardiovascular risk from excess fat in the blood",
        "gris": "not enough data to evaluate your triglycerides",
    },
    "Glucosa": {
        "verde": "stable energy levels throughout the day",
        "ambar": "energy fluctuations that can cause spikes and dips in concentration",
        "rojo": "a significant imbalance in your energy and concentration",
        "gris": "not enough data to evaluate your glucose",
    },
    "Colesterol": {
        "verde": "clean arteries and good circulation",
        "ambar": "the beginning of fat buildup in your arteries",
        "rojo": "a risk of arterial blockage that affects your circulation",
        "gris": "not enough data to evaluate your cholesterol",
    },
    "Hierro": {
        "verde": "good energy reserves and defenses",
        "ambar": "low iron reserves that can cause tiredness",
        "rojo": "severely compromised iron reserves",
        "gris": "not enough data to evaluate your iron reserves",
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

AMBITO_PLANTILLAS_EN = {
    "Escolar/Académico": {
        "verde": "📚 At school, having {efecto} helps you stay focused in class and do well on your tests. Keep it up!",
        "ambar": "📚 At school, {efecto} could make it a bit harder to concentrate or leave you feeling tired in the last hours of class. Pay attention to what you eat before studying.",
        "rojo": "📚 At school, {efecto} can seriously affect your attention, memory, and academic performance. It's important to talk to a trusted adult and consult a specialist.",
        "gris": "📚 Enter your value to see how it could affect your school performance.",
    },
    "Laboral": {
        "verde": "💼 At work, having {efecto} gives you the energy you need to get your tasks done with focus and without excessive fatigue.",
        "ambar": "💼 At work, {efecto} could translate into lower productivity toward the end of the day. It's worth adjusting your eating habits.",
        "rojo": "💼 At work, {efecto} can cause chronic fatigue, poor performance, and a higher risk of mistakes. Professional attention is recommended before continuing with demanding activities.",
        "gris": "💼 Enter your value to see how it could affect your work performance.",
    },
    "Psicológico/Emocional": {
        "verde": "💚 Emotionally, having {efecto} contributes to a stable mood and greater resistance to daily stress.",
        "ambar": "💚 Emotionally, {efecto} can be linked to irritability, mild mood swings, or an increased feeling of stress.",
        "rojo": "💚 Emotionally, {efecto} is associated with greater irritability, anxiety, or low mood. Taking care of this physical aspect also supports your emotional wellbeing — don't hesitate to seek support if you need it.",
        "gris": "💚 Enter your value to see how it could affect your emotional state.",
    },
}


def generar_impacto_ambito(parametro, categoria, ambito):
    """Genera el texto dinámico de impacto de un resultado clínico según el ámbito elegido
    (Escolar/Académico, Laboral, Psicológico/Emocional), usando el color de semáforo ya calculado."""
    color = CATEGORIA_SEMAFORO.get(categoria, "gris")
    _en = st.session_state.get("idioma", "Español") == "English"
    _efectos = EFECTOS_PARAMETRO_EN if _en else EFECTOS_PARAMETRO
    _plantillas = AMBITO_PLANTILLAS_EN if _en else AMBITO_PLANTILLAS
    efecto = _efectos.get(parametro, {}).get(color, "")
    plantilla = _plantillas[ambito][color]
    return plantilla.format(efecto=efecto)

def clasif_percentil(imc, edad, genero):
    """Réplica EXACTA de la fórmula del Excel (Hoja 2, celda K17:L17)."""
    tabla = PERCENTIL_HOMBRE if genero == "Hombre" else PERCENTIL_MUJER
    if edad not in tabla:
        return None, T("Edad fuera de tabla (2-20 años)", "Age out of table range (2-20 years)")
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
    elif categoria in ["Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3", "Obesidad Clase 3 (Severa)"]:
        color = "rojo"
    else:
        color = "gris"
    estilo = dict(SEMAFORO_ESTILO[color])
    estilo["colorSemaforo"] = color
    return estilo


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

    _en_graf = st.session_state.get("idioma", "Español") == "English"
    _lbl_p5 = "Percentile 5" if _en_graf else "Percentil 5"
    _lbl_p50 = "Percentile 50" if _en_graf else "Percentil 50"
    _lbl_p85 = "Percentile 85" if _en_graf else "Percentil 85"
    _lbl_p95 = "Percentile 95" if _en_graf else "Percentil 95"

    # ---- Líneas con etiquetas de dato en cada punto ----
    fig.add_trace(go.Scatter(x=edades, y=p5, mode="lines+markers+text", name=_lbl_p5,
                              line=dict(color="#1E88E5", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p5], textposition="bottom center",
                              textfont=dict(color="#1E88E5", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p50, mode="lines+markers+text", name=_lbl_p50,
                              line=dict(color="#43A047", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p50], textposition="top center",
                              textfont=dict(color="#2E7D32", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p85, mode="lines+markers+text", name=_lbl_p85,
                              line=dict(color="#FBC02D", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p85], textposition="top center",
                              textfont=dict(color="#F9A825", size=9)))
    fig.add_trace(go.Scatter(x=edades, y=p95, mode="lines+markers+text", name=_lbl_p95,
                              line=dict(color="#E53935", width=3), marker=dict(size=5),
                              text=[f"{v:.1f}" for v in p95], textposition="top center",
                              textfont=dict(color="#E53935", size=9)))

    if genero_usuario == genero_tabla and edad_usuario in tabla and imc_usuario is not None:
        fig.add_trace(go.Scatter(x=[edad_usuario], y=[imc_usuario], mode="markers+text",
                                  name=("You are here" if _en_graf else "Tú estás aquí"),
                                  text=[("You" if _en_graf else "Tú")], textposition="bottom center",
                                  marker=dict(color="#1565C0", size=16, symbol="star",
                                              line=dict(color="white", width=1))))

    if _en_graf:
        titulo_txt = "Girls Percentile" if genero_tabla == "Mujer" else "Boys Percentile"
    else:
        titulo_txt = "Percentil Niñas" if genero_tabla == "Mujer" else "Percentil Niños"
    titulo_color = "#E53935" if genero_tabla == "Mujer" else "#00838F"

    fig.update_layout(
        title=dict(text=titulo_txt, font=dict(color=titulo_color, size=24, family="Arial Black"), x=0.5, xanchor="center"),
        xaxis_title=("Age (years)" if _en_graf else "Edad (años)"), yaxis_title=("BMI" if _en_graf else "IMC"),
        yaxis=dict(range=[y_min, y_max]),
        xaxis=dict(dtick=1),
        height=430, margin=dict(t=60, l=10, r=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

# =========================================================================================
# GAUGE SEMICIRCULAR SVG — "Resultado IMC" como velocímetro de 4 zonas con aguja dinámica
# =========================================================================================
def _polar(cx, cy, r, angle_deg):
    """Punto sobre una circunferencia; angle_deg=180 -> izquierda, 270 -> arriba, 360 -> derecha."""
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def gauge_imc_svg(imc, categoria, min_v=10.0, max_v=42.0, size=230):
    """Velocímetro semicircular (SVG) para el resultado de IMC, con 4 zonas de color
    (Azul=Bajo peso, Verde=Saludable, Naranja=Sobrepeso, Rojo=Obesidad) y una aguja que
    apunta al valor exacto, con una animación suave de entrada vía CSS @keyframes."""
    zonas_val = [
        (min_v, 18.5, "#42A5F5"),
        (18.5, 25.0, "#34C759"),
        (25.0, 30.0, "#FF9F43"),
        (30.0, max_v, "#FF5C7C"),
    ]
    cx, cy, r = size / 2, size * 0.56, size * 0.40
    grosor = size * 0.11
    piezas = []
    for ini, fin, color in zonas_val:
        f_ini = max(0.0, min(1.0, (ini - min_v) / (max_v - min_v)))
        f_fin = max(0.0, min(1.0, (fin - min_v) / (max_v - min_v)))
        ang_ini, ang_fin = 180 + f_ini * 180, 180 + f_fin * 180
        x1, y1 = _polar(cx, cy, r, ang_ini)
        x2, y2 = _polar(cx, cy, r, ang_fin)
        piezas.append(f'<path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 0 1 {x2:.1f} {y2:.1f}" '
                       f'stroke="{color}" stroke-width="{grosor:.1f}" fill="none" stroke-linecap="butt"/>')

    valor_clamp = max(min_v, min(max_v, imc))
    frac = (valor_clamp - min_v) / (max_v - min_v)
    deg_final = frac * 180 - 90  # -90 = min (izquierda), 0 = centro (arriba), 90 = max (derecha)
    largo_aguja = r * 0.86
    anim_id = "gaugeneedle" + uuid.uuid4().hex[:8]

    # colorcito del texto/badge según la categoría, coherente con las 4 zonas
    if categoria == "Peso Saludable":
        color_txt = "#2E9E4A"
    elif categoria in ("Bajo Peso",):
        color_txt = "#1E88E5"
    elif categoria in ("Sobrepeso",):
        color_txt = "#E67E22"
    else:
        color_txt = "#E0335A"

    svg = f"""
    <div style="position:relative;width:100%;max-width:{size}px;margin:0 auto;">
    <style>
    @keyframes {anim_id} {{ from {{ transform: rotate(-90deg); }} to {{ transform: rotate({deg_final:.1f}deg); }} }}
    </style>
    <svg viewBox="0 0 {size} {size*0.66:.0f}" width="100%" xmlns="http://www.w3.org/2000/svg">
        {''.join(piezas)}
        <g class="gauge-needle-pivot" style="transform-origin:{cx}px {cy}px;
             animation:{anim_id} 0.9s cubic-bezier(.34,1.4,.64,1) forwards;">
            <line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy-largo_aguja:.1f}"
                  stroke="#24262B" stroke-width="4.5" stroke-linecap="round"/>
        </g>
        <circle cx="{cx}" cy="{cy}" r="8" fill="#24262B"/>
    </svg>
    <div style="text-align:center;margin-top:-6px;">
        <div style="font-size:2.1rem;font-weight:800;color:{color_txt};letter-spacing:-0.02em;line-height:1;">{imc}</div>
        <span class="bento-pill" style="background:{color_txt}1A;color:{color_txt};margin-top:6px;">⚖️ {categoria}</span>
    </div>
    </div>
    """
    return svg


def card_gauge_imc(imc, categoria):
    """Tarjeta Bento con el velocímetro de IMC, reemplazando el KPI de texto plano."""
    st.markdown(f"""
    <div class="bento-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <span class="bento-eyebrow">Resultado IMC</span>
            <span style="font-size:1.1rem;">📈</span>
        </div>
        {gauge_imc_svg(imc, categoria)}
    </div>
    """, unsafe_allow_html=True)


# =========================================================================================
# TARJETA DE PERCENTIL — barra vertical tipo termómetro con degradado azul
# =========================================================================================
_PERCENTIL_ALTURA = {"< 5": 8, "50": 50, "85": 85, "95": 96}


def card_percentil_barra(percentil_valor, categoria=None):
    """Tarjeta Bento con una barra vertical de progreso (degradado azul) que representa
    de forma visual el percentil del usuario, con el número grande destacado arriba."""
    altura_pct = _PERCENTIL_ALTURA.get(str(percentil_valor), 50)
    st.markdown(f"""
    <div class="bento-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <span class="bento-eyebrow">Percentil</span>
            <span style="font-size:1.1rem;">📊</span>
        </div>
        <div style="display:flex;align-items:flex-end;gap:16px;margin-top:6px;">
            <div style="flex-shrink:0;">
                <div style="font-size:3rem;font-weight:800;color:#1E88E5;letter-spacing:-0.03em;line-height:1;">{percentil_valor}</div>
                <div style="font-size:0.78rem;color:#8A94A6;font-weight:700;margin-top:4px;">de cada 100 niños{' de tu edad y sexo' if percentil_valor not in ('< 5',) else ''}</div>
            </div>
            <div style="flex:1;height:88px;border-radius:12px;background:#EAF2FB;position:relative;overflow:hidden;min-width:34px;max-width:44px;margin-left:auto;">
                <div style="position:absolute;bottom:0;left:0;width:100%;height:{altura_pct}%;
                     border-radius:12px 12px 0 0;
                     background:linear-gradient(180deg, #42A5F5 0%, #1E88E5 100%);
                     transition: height 0.8s ease-in-out;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================================================
# TARJETA DE CATEGORÍA / ALERTA — reemplaza tarjeta_categoria_imc con badge de alerta
# =========================================================================================
_ILUSTRA_CATEGORIA = {
    "verde": "🟢", "ambar": "🟠", "rojo": "🔴", "gris": "⚪",
}


def tarjeta_categoria_imc(titulo, categoria):
    """Tarjeta Bento de categoría de IMC con fondo pastel de alerta y badge de advertencia
    cuando la categoría implica riesgo (sobrepeso u obesidad)."""
    estilo = color_categoria_imc(categoria)
    es_alerta = estilo["colorSemaforo"] in ("ambar", "rojo")
    badge_alerta = (
        f'<div class="bento-pill" style="background:{estilo["hex"]};color:#FFFFFF;margin-top:8px;">⚠️ {T("Requiere atención", "Needs attention")}</div>'
        if es_alerta else
        f'<div class="bento-pill" style="background:{estilo["hex"]}1A;color:{estilo["hex"]};margin-top:8px;">✅ {T("En buen camino", "On track")}</div>'
    )
    st.markdown(f"""
    <div class="bento-card" style="background:{estilo['fondo']};text-align:center;
                border:1.5px solid {estilo['hex']}33;">
        <div class="bento-eyebrow" style="text-align:center;">{titulo}</div>
        <div style="font-size:2.2rem;margin-top:6px;">{_ILUSTRA_CATEGORIA.get(estilo['colorSemaforo'], '⚪')}</div>
        <div style="font-weight:800;font-size:1.15rem;color:{estilo['hex']};letter-spacing:-0.01em;margin-top:2px;">{_cat_imc_txt(categoria)}</div>
        {badge_alerta}
    </div>
    """, unsafe_allow_html=True)


# =========================================================================================
# TABLA VISUAL — "Categorías Generales de IMC" con avatares, rangos y barra de posición
# =========================================================================================
_CATEGORIAS_IMC_DEF = [
    ("Bajo Peso",                "Menos de 18.5", "Tu peso está por debajo de lo recomendado para tu altura.", "🛡️", "#34C759", None, 18.5, ("🟢 Bajo", "#34C759")),
    ("Peso Saludable",           "18.5 a 24.9",   "Tu peso está dentro del rango saludable.",                   "💚", "#2E9E4A", 18.5, 24.9, ("🟢 Bajo", "#34C759")),
    ("Sobrepeso",                "25 a 29.9",     "Tu peso está por encima de lo saludable.",                   "🏋️", "#1E88E5", 25, 29.9, ("🟡 Moderado", "#FFCC00")),
    ("Obesidad",                 "30 o más",      "Tu peso está muy por encima de lo saludable.",               "⚠️", "#FF9F43", 30, None, ("🟠 Alto", "#FF9500")),
    ("Obesidad Clase 1",         "30 a 34.9",     "Riesgo moderado para la salud.",                             "1️⃣", "#FF6B81", 30, 34.9, ("🔴 Muy alto", "#FF3B30")),
    ("Obesidad Clase 2",         "35 a 39.9",     "Mayor riesgo para la salud.",                                "2️⃣", "#F0384A", 35, 39.9, ("🔴 Muy alto", "#FF3B30")),
    ("Obesidad Clase 3 (Severa)", "40 o más",     "Riesgo muy alto para la salud.",                             "3️⃣", "#B71C33", 40, None, ("🔴 Muy alto", "#FF3B30")),
]

_CATEGORIAS_IMC_DEF_EN = [
    ("Underweight",              "Less than 18.5", "Your weight is below what's recommended for your height.",  "🛡️", "#34C759", None, 18.5, ("🟢 Low", "#34C759")),
    ("Healthy Weight",           "18.5 to 24.9",   "Your weight is within the healthy range.",                   "💚", "#2E9E4A", 18.5, 24.9, ("🟢 Low", "#34C759")),
    ("Overweight",               "25 to 29.9",     "Your weight is above the healthy range.",                    "🏋️", "#1E88E5", 25, 29.9, ("🟡 Moderate", "#FFCC00")),
    ("Obesity",                  "30 or more",     "Your weight is well above the healthy range.",               "⚠️", "#FF9F43", 30, None, ("🟠 High", "#FF9500")),
    ("Obesity Class 1",          "30 to 34.9",     "Moderate risk to your health.",                              "1️⃣", "#FF6B81", 30, 34.9, ("🔴 Very High", "#FF3B30")),
    ("Obesity Class 2",          "35 to 39.9",     "Higher risk to your health.",                                "2️⃣", "#F0384A", 35, 39.9, ("🔴 Very High", "#FF3B30")),
    ("Obesity Class 3 (Severe)", "40 or more",     "Very high risk to your health.",                             "3️⃣", "#B71C33", 40, None, ("🔴 Very High", "#FF3B30")),
]
_ESCALA_MIN, _ESCALA_MAX = 0, 40


def tabla_categorias_imc_visual(imc_usuario=None):
    """Tabla de alto impacto visual (reemplaza tabla_bonita en esta sección): encabezado con
    icono + subtítulo, cabecera de columnas lila, avatar circular + subtexto por clasificación,
    y en la 3ra columna un indicador de línea con dos puntos marcando el inicio/fin de cada
    rango sobre la escala global (0 a 40+), muy similar a la referencia de diseño."""
    _en_tabla = st.session_state.get("idioma", "Español") == "English"
    _def_lista = _CATEGORIAS_IMC_DEF_EN if _en_tabla else _CATEGORIAS_IMC_DEF
    filas_html = []
    for nombre, rango_txt, subtxt, icono, color, ini, fin, riesgo in _def_lista:
        ini_v = _ESCALA_MIN if ini is None else ini
        fin_v = _ESCALA_MAX if fin is None else fin
        izq = max(0.0, min(100.0, (ini_v - _ESCALA_MIN) / (_ESCALA_MAX - _ESCALA_MIN) * 100))
        der = max(0.0, min(100.0, (fin_v - _ESCALA_MIN) / (_ESCALA_MAX - _ESCALA_MIN) * 100))
        ancho = max(1.0, der - izq)
        etiqueta_ini = "0" if ini is None else f"{ini:g}"
        etiqueta_fin = "40+" if fin is None else f"{fin:g}"

        marcador_usuario = ""
        if imc_usuario is not None:
            en_rango = (ini is None or imc_usuario >= ini) and (fin is None or imc_usuario <= fin)
            if en_rango:
                pos_usuario = max(0.0, min(100.0, (imc_usuario - _ESCALA_MIN) / (_ESCALA_MAX - _ESCALA_MIN) * 100))
                marcador_usuario = (f'<div style="position:absolute;top:-14px;left:{pos_usuario:.1f}%;'
                                     f'transform:translateX(-50%);font-size:0.85rem;">📍</div>')

        _r_txt, _r_color = riesgo
        filas_html.append(f"""
        <div class="imc-row" style="grid-template-columns:1.5fr 0.9fr 1.7fr 1fr;">
            <div style="display:flex;align-items:center;">
                <span class="imc-clasif-avatar" style="background:{color}22;">{icono}</span>
                <div>
                    <div class="imc-clasif-title" style="color:{color};">{nombre}</div>
                    <div class="imc-clasif-sub">{subtxt}</div>
                </div>
            </div>
            <div class="imc-range-num" style="color:{color};">{rango_txt}</div>
            <div style="position:relative;padding-top:14px;">
                {marcador_usuario}
                <div class="imc-line-track">
                    <div class="imc-line-seg" style="left:{izq:.1f}%;width:{ancho:.1f}%;background:{color};"></div>
                    <div class="imc-line-dot" style="left:calc({izq:.1f}% - 6px);background:{color};color:{color};"></div>
                    <div class="imc-line-dot" style="left:calc({der:.1f}% - 6px);background:{color};color:{color};"></div>
                </div>
                <div class="imc-line-vals" style="color:{color};">
                    <span class="val-mark" style="left:{izq:.1f}%;">{etiqueta_ini}</span>
                    <span class="val-mark" style="left:{der:.1f}%;">{etiqueta_fin}</span>
                </div>
                <div class="imc-scale-ends"><span>0</span><span>40+</span></div>
            </div>
            <div style="text-align:center;">
                <span class="bento-pill" style="background:{_r_color}1A;color:{_r_color};">{_r_txt}</span>
            </div>
        </div>
        """)

    _html_tabla_imc = f"""
    <div class="imc-table-wrap">
        <div class="imc-table-topbar">
            <span class="imc-table-icon">⚖️</span>
            <div>
                <div class="imc-table-title">{T("Categorías generales de IMC", "General BMI Categories")}</div>
                <div class="imc-table-sub">{T("El Índice de Masa Corporal (IMC) es una guía que relaciona tu peso con tu altura para conocer tu estado nutricional.",
                                                "Body Mass Index (BMI) is a guide that relates your weight to your height to determine your nutritional status.")}</div>
            </div>
        </div>
        <div class="imc-table-head" style="grid-template-columns:1.5fr 0.9fr 1.7fr 1fr;">
            <span>🔖 {T("Clasificación", "Classification")}</span><span>📝 {T("Rango de IMC", "BMI Range")}</span><span>📊 {T("¿Dónde te encuentras?", "Where do you stand?")}</span><span>🚨 {T("Riesgo", "Risk")}</span>
        </div>
        {''.join(filas_html)}
        <div class="imc-footer-banner">
            <span class="imc-footer-avatar">👩‍⚕️</span>
            <div style="font-size:0.82rem;color:#5C6B60;max-width:480px;">
                <b style="color:#6A1B9A;">💡 {T("Importante:", "Important:")}</b> {T("el IMC es una referencia general.",
                "BMI is a general reference.")}
                {T("Consulta siempre con un profesional de salud para una evaluación completa y recomendaciones personalizadas.",
                   "Always consult a health professional for a complete evaluation and personalized recommendations.")}
            </div>
            <div class="imc-footer-tip">🛡️ {T("¡Pequeños cambios hoy, grandes resultados mañana!", "Small changes today, big results tomorrow!")}</div>
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_imc), unsafe_allow_html=True)


# =========================================================================================
# TABLA VISUAL — Percentiles por edad y género, en dos tarjetas (rosa Mujer / azul Hombre)
# =========================================================================================
_PERC_COL_ESTILO = [
    ("P5", "Bajo Peso", "#E1F5FE", "#0288D1"),
    ("P50", "Saludable", "#E8F5E9", "#388E3C"),
    ("P85", "Sobrepeso", "#FFF3E0", "#F57C00"),
    ("P95", "Obesidad", "#FFEBEE", "#D32F2F"),
]

_PERC_COL_ESTILO_EN = [
    ("P5", "Underweight", "#E1F5FE", "#0288D1"),
    ("P50", "Healthy", "#E8F5E9", "#388E3C"),
    ("P85", "Overweight", "#FFF3E0", "#F57C00"),
    ("P95", "Obesity", "#FFEBEE", "#D32F2F"),
]


_PERC_CATEGORIA_COL = {"Bajo Peso": 0, "Peso Saludable": 1, "Sobrepeso": 2, "Obesidad": 3}


def _tarjeta_percentil_genero(genero_tabla, tabla, edad_usuario=None, genero_usuario=None, categoria_usuario=None):
    """Construye una tarjeta de percentiles (Mujer=rosa / Hombre=azul) con cabecera ilustrada,
    columnas P5/P50/P85/P95 con color propio, filas alternadas, la fila del usuario resaltada,
    y además la columna (P5/P50/P85/P95) donde cayó su IMC resaltada con un marco de color."""
    _en_perc = st.session_state.get("idioma", "Español") == "English"
    if genero_tabla == "Mujer":
        fondo_banner, color_titulo, icono, badge = "#FCE4EC", "#C2185B", "👧", "♀"
        _titulo_genero = "GIRLS" if _en_perc else "MUJER"
    else:
        fondo_banner, color_titulo, icono, badge = "#E3F2FD", "#1976D2", "👦", "♂"
        _titulo_genero = "BOYS" if _en_perc else "HOMBRE"

    col_activa = _PERC_CATEGORIA_COL.get(categoria_usuario) if genero_usuario == genero_tabla else None

    filas = []
    for i, edad in enumerate(sorted(tabla.keys())):
        p5, p50, p85, p95 = tabla[edad]
        es_usuario = (edad_usuario == edad and genero_usuario == genero_tabla)
        clases = ("zebra " if i % 2 == 1 else "") + ("user-row" if es_usuario else "")
        _vals = [p5, p50, p85, p95]
        _tds = "".join(
            f'<td style="{"box-shadow:inset 0 0 0 2px " + color_titulo + ";background:" + color_titulo + "14;font-weight:800;" if (es_usuario and col_activa == _j) else ""}">{_v}</td>'
            for _j, _v in enumerate(_vals)
        )
        filas.append(f"""<tr class="{clases.strip()}">
            <td style="font-weight:800;color:{color_titulo};">{edad}{' ⭐' if es_usuario else ''}</td>
            {_tds}
        </tr>""")

    _col_lista = _PERC_COL_ESTILO_EN if _en_perc else _PERC_COL_ESTILO
    ths = "".join(
        f'<th style="background:{bg};color:{fg};">{cod}<br><span style="font-weight:600;font-size:0.62rem;">{lbl}</span></th>'
        for cod, lbl, bg, fg in _col_lista
    )

    _edad_txt = T("Edad", "Age")
    _anios_txt = T("(años)", "(years)")
    html = f"""
    <div class="perc-card">
        <div class="perc-banner" style="background:{fondo_banner};">
            <span class="perc-banner-icon">{icono}</span>
            <span class="perc-banner-title" style="color:{color_titulo};">{_titulo_genero}</span>
            <span class="perc-badge" style="color:{color_titulo};">{badge}</span>
        </div>
        <div style="max-height:340px;overflow-y:auto;">
        <table class="perc-table">
            <thead><tr><th style="background:#F5F5F7;color:#5C6B60;">{_edad_txt}<br><span style="font-weight:600;font-size:0.62rem;">{_anios_txt}</span></th>{ths}</tr></thead>
            <tbody>{''.join(filas)}</tbody>
        </table>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def tabla_percentiles_genero_visual(edad_usuario=None, genero_usuario=None, categoria_usuario=None):
    """Layout split de dos columnas (grid) con las tarjetas de percentil de Mujer y Hombre,
    reemplazando las dos tablas planas de st.dataframe."""
    col_m, col_h = st.columns(2)
    with col_m:
        _tarjeta_percentil_genero("Mujer", PERCENTIL_MUJER, edad_usuario, genero_usuario, categoria_usuario)
    with col_h:
        _tarjeta_percentil_genero("Hombre", PERCENTIL_HOMBRE, edad_usuario, genero_usuario, categoria_usuario)


def fila_dominios_salud(dominios):
    """Fila de iconos redondeados representando a qué ámbitos afecta un resultado
    (Salud general, Atención médica, Apoyo y tratamiento, Detección temprana, etc.)."""
    items = "".join(
        f"""<div class="dominio-icono">
                <div class="dominio-circulo" style="background:{color}1A;">{icono}</div>
                <div class="dominio-label">{label}</div>
            </div>"""
        for icono, color, label in dominios
    )
    st.markdown(f'<div style="display:flex;gap:10px;margin-top:6px;">{items}</div>', unsafe_allow_html=True)


def cta_pill(icono, color, titulo, desc, boton_texto, url):
    """Tarjeta CTA tipo 'pill' con icono, título, descripción breve y botón redondeado
    con flecha, para enlaces a recursos externos (ej. pruebas del CDC)."""
    st.markdown(f"""
    <a href="{url}" target="_blank" class="cta-pill-card">
        <span class="cta-pill-icon" style="background:{color}1A;">{icono}</span>
        <div>
            <div class="cta-pill-title">{titulo}</div>
            <div class="cta-pill-desc">{desc}</div>
            <span class="cta-pill-btn" style="background:{color};color:#FFFFFF;">{boton_texto} →</span>
        </div>
    </a>
    """, unsafe_allow_html=True)


# =========================================================================================
# HOJA 2 (IMC) — componentes rediseñados: panel-resumen, escala horizontal, percentil visual,
# estado nutricional, acciones, progreso hacia meta y conexión con el resto del sistema.
# =========================================================================================
_RIESGO_POR_CATEGORIA = {
    "Bajo Peso": ("Moderado", "#FF9500"),
    "Peso Saludable": ("Bajo", "#34C759"),
    "Sobrepeso": ("Moderado", "#FF9500"),
    "Obesidad": ("Alto", "#FF3B30"),
    "Obesidad Clase 1": ("Alto", "#FF3B30"),
    "Obesidad Clase 2": ("Muy alto", "#D70015"),
    "Obesidad Clase 3": ("Muy alto", "#D70015"),
    "Obesidad Clase 3 (Severa)": ("Muy alto", "#D70015"),
}

_RIESGO_POR_CATEGORIA_EN = {
    "Bajo Peso": ("Moderate", "#FF9500"),
    "Peso Saludable": ("Low", "#34C759"),
    "Sobrepeso": ("Moderate", "#FF9500"),
    "Obesidad": ("High", "#FF3B30"),
    "Obesidad Clase 1": ("High", "#FF3B30"),
    "Obesidad Clase 2": ("Very High", "#D70015"),
    "Obesidad Clase 3": ("Very High", "#D70015"),
    "Obesidad Clase 3 (Severa)": ("Very High", "#D70015"),
}

_FRASE_POR_CATEGORIA = {
    "Bajo Peso": "Según tus datos actuales, tu peso se encuentra por debajo del rango recomendado para tu edad y estatura.",
    "Peso Saludable": "Según tus datos actuales, tu peso se encuentra dentro del rango recomendado para tu edad y estatura. ¡Sigue así!",
    "Sobrepeso": "Según tus datos actuales, tu peso se encuentra por encima del rango recomendado para tu edad y estatura.",
    "Obesidad": "Según tus datos actuales, tu peso se encuentra muy por encima del rango recomendado para tu edad y estatura.",
    "Obesidad Clase 1": "Según tus datos actuales, tu peso se encuentra por encima del rango recomendado, con riesgo moderado para tu salud.",
    "Obesidad Clase 2": "Según tus datos actuales, tu peso se encuentra muy por encima del rango recomendado, con mayor riesgo para tu salud.",
    "Obesidad Clase 3": "Según tus datos actuales, tu peso se encuentra muy por encima del rango recomendado, con riesgo alto para tu salud.",
    "Obesidad Clase 3 (Severa)": "Según tus datos actuales, tu peso se encuentra muy por encima del rango recomendado, con riesgo muy alto para tu salud.",
}

_FRASE_POR_CATEGORIA_EN = {
    "Bajo Peso": "Based on your current data, your weight is below the recommended range for your age and height.",
    "Peso Saludable": "Based on your current data, your weight is within the recommended range for your age and height. Keep it up!",
    "Sobrepeso": "Based on your current data, your weight is above the recommended range for your age and height.",
    "Obesidad": "Based on your current data, your weight is well above the recommended range for your age and height.",
    "Obesidad Clase 1": "Based on your current data, your weight is above the recommended range, with moderate risk to your health.",
    "Obesidad Clase 2": "Based on your current data, your weight is well above the recommended range, with higher risk to your health.",
    "Obesidad Clase 3": "Based on your current data, your weight is well above the recommended range, with high risk to your health.",
    "Obesidad Clase 3 (Severa)": "Based on your current data, your weight is well above the recommended range, with very high risk to your health.",
}

# Mapa de categorías clínicas de IMC (claves internas en español, usadas en todo el sistema)
# a su etiqueta traducida — para mostrar en pantalla según el idioma seleccionado.
_CATEGORIA_IMC_EN = {
    "Bajo Peso": "Underweight",
    "Peso Saludable": "Healthy Weight",
    "Sobrepeso": "Overweight",
    "Obesidad": "Obesity",
    "Obesidad Clase 1": "Obesity Class 1",
    "Obesidad Clase 2": "Obesity Class 2",
    "Obesidad Clase 3": "Obesity Class 3",
    "Obesidad Clase 3 (Severa)": "Obesity Class 3 (Severe)",
}


def _cat_imc_txt(categoria):
    """Devuelve la categoría de IMC (clave interna en español) traducida al idioma activo,
    sin modificar la clave interna usada en el resto del sistema para cálculos/estilos."""
    if st.session_state.get("idioma", "Español") == "English":
        return _CATEGORIA_IMC_EN.get(categoria, categoria)
    return categoria


def _riesgo_imc_txt(categoria):
    """Devuelve (texto_riesgo, color) para una categoría de IMC, traducido según el idioma."""
    _dic = _RIESGO_POR_CATEGORIA_EN if st.session_state.get("idioma", "Español") == "English" else _RIESGO_POR_CATEGORIA
    return _dic.get(categoria, ("—", "#8E8E93"))


def _frase_imc_txt(categoria):
    """Devuelve la frase-resumen del diagnóstico nutricional, traducida según el idioma."""
    _dic = _FRASE_POR_CATEGORIA_EN if st.session_state.get("idioma", "Español") == "English" else _FRASE_POR_CATEGORIA
    return _dic.get(categoria, T("Revisa tus datos para conocer tu diagnóstico nutricional.",
                                  "Check your data to see your nutritional diagnosis."))


def panel_diagnostico_nutricional(imc, percentil_valor, categoria, con_percentil=True):
    """Sección 1: 'Tu Diagnóstico Nutricional' — 4 tarjetas iguales (IMC, Percentil, Estado,
    Riesgo) seguidas de una frase-resumen grande, en vez del flujo largo de cajas dispersas."""
    estilo = color_categoria_imc(categoria)
    riesgo_txt, riesgo_color = _riesgo_imc_txt(categoria)
    perc_display = f"P{percentil_valor}" if (con_percentil and percentil_valor is not None) else "—"
    tarjetas = [
        ("IMC" if st.session_state.get("idioma", "Español") != "English" else "BMI", str(imc), "⚖️", "#1E5631"),
        (T("Percentil", "Percentile"), perc_display, "📊", "#1E88E5"),
        (T("Estado", "Status"), _cat_imc_txt(categoria), "🩺", estilo["hex"]),
        (T("Riesgo", "Risk"), riesgo_txt, "🚨", riesgo_color),
    ]
    _kpis = "".join(f"""
        <div class="diag-kpi">
            <div class="diag-kpi-icon">{ic}</div>
            <div class="diag-kpi-label">{lbl}</div>
            <div class="diag-kpi-val" style="color:{col};">{val}</div>
        </div>""" for lbl, val, ic, col in tarjetas)
    frase = _frase_imc_txt(categoria)
    st.markdown(f"""
    <div class="diag-panel">
        <div class="diag-panel-title">🩺 {T("Tu Diagnóstico Nutricional", "Your Nutritional Diagnosis")}</div>
        <div class="diag-kpi-grid">{_kpis}</div>
        <div class="diag-frase" style="border-left:5px solid {estilo['hex']};">
            <span style="font-size:1.3rem;">{_ILUSTRA_CATEGORIA.get(estilo['colorSemaforo'], '⚪')}</span>
            <span>{frase}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


_ESCALA_ADULTO_ZONAS = [("Bajo", "#42A5F5", 0, 18.5), ("Normal", "#34C759", 18.5, 25.0),
                         ("Sobrepeso", "#FF9F43", 25.0, 30.0), ("Obesidad", "#FF5C7C", 30.0, 40.0)]
_ESCALA_INFANTIL_ZONAS = [("Bajo Peso", "#42A5F5", "< 5"), ("Saludable", "#34C759", "5 – 85"),
                           ("Sobrepeso", "#FF9F43", "85 – 95"), ("Obesidad", "#FF5C7C", "> 95")]

_ESCALA_ADULTO_ZONAS_EN = ["Low", "Normal", "Overweight", "Obesity"]
_ESCALA_INFANTIL_ZONAS_EN = ["Underweight", "Healthy", "Overweight", "Obesity"]


def escala_horizontal_imc(imc, categoria, etapa, percentil_valor=None):
    """Sección 2: escala horizontal (reemplaza el velocímetro como pieza principal) que muestra
    de un vistazo en qué zona cae el valor del usuario, con una flecha marcando su posición."""
    _en = st.session_state.get("idioma", "Español") == "English"
    _es_infantil = etapa in ("Niñez", "Adolescencia") and percentil_valor is not None
    if _es_infantil:
        _nombres_colores = [(n, c) for n, c, _ in _ESCALA_INFANTIL_ZONAS]
        if _en:
            _nombres_colores = [(n, c) for n, (_, c) in zip(_ESCALA_INFANTIL_ZONAS_EN, _nombres_colores)]
        _idx_map = {"Bajo Peso": 0, "Peso Saludable": 1, "Sobrepeso": 2, "Obesidad": 3}
        _idx_activo = _idx_map.get(categoria, 1)
        _pos_pct = {0: 5, 1: 45, 2: 82, 3: 96}.get(_idx_activo, 45)
        _valor_mostrar = f"P{percentil_valor}"
    else:
        _nombres_colores = [(n, c) for n, c, _, _ in _ESCALA_ADULTO_ZONAS]
        if _en:
            _nombres_colores = [(n, c) for n, (_, c) in zip(_ESCALA_ADULTO_ZONAS_EN, _nombres_colores)]
        _min_v, _max_v = 10.0, 40.0
        _pos_pct = max(2.0, min(98.0, (imc - _min_v) / (_max_v - _min_v) * 100))
        _valor_mostrar = str(imc)

    _segmentos = "".join(f'<div style="flex:1;background:{c};"></div>' for _, c in _nombres_colores)
    _etiquetas = "".join(f"<span>{n}</span>" for n, _ in _nombres_colores)
    estilo = color_categoria_imc(categoria)
    st.markdown(f"""
    <div class="escala-imc-wrap">
        <span class="bento-eyebrow">{T("Dónde te ubicas", "Where you stand")}</span>
        <div style="position:relative;">
            <div class="escala-imc-marker" style="left:{_pos_pct:.1f}%;">
                <div style="font-weight:800;font-size:0.95rem;color:{estilo['hex']};">{T("Tú", "You")} ({_valor_mostrar})</div>
                <div class="escala-imc-marker-tri"></div>
            </div>
            <div class="escala-imc-zonas">{_segmentos}</div>
        </div>
        <div class="escala-imc-labels">{_etiquetas}</div>
    </div>
    """, unsafe_allow_html=True)


def percentil_visual_card(percentil_valor):
    """Sección 3: representación visual de 100 puntos (10x10) donde se colorean cuántos niños
    quedan por debajo del percentil del usuario, con una frase explicativa sencilla."""
    _debajo_map = {"< 5": 5, "50": 50, "85": 85, "95": 95}
    _debajo = _debajo_map.get(str(percentil_valor), 50)
    _dots = "".join(
        f'<div class="perc-visual-dot" style="background:{"#1E88E5" if _i < _debajo else "#E3F2FD"};"></div>'
        for _i in range(100)
    )
    st.markdown(f"""
    <div class="perc-visual-wrap">
        <span class="bento-eyebrow">👦 {T("Percentil", "Percentile")} {percentil_valor}</span>
        <div style="font-size:0.82rem;color:#5C6B60;margin-top:4px;">{T("De cada 100 niños de tu misma edad y sexo:", "Out of every 100 kids of your same age and sex:")}</div>
        <div class="perc-visual-grid">{_dots}</div>
        <div style="font-size:0.85rem;color:#17301F;line-height:1.5;">
            <b style="color:#1E88E5;">{_debajo}</b> {T("están por debajo de tu IMC.", "are below your BMI.")}<br>
            {T("Solo", "Only")} <b style="color:#1E88E5;">{100 - _debajo}</b> {T("tienen un IMC mayor.", "have a higher BMI.")}
        </div>
    </div>
    """, unsafe_allow_html=True)


_ESTADO_CHECKLIST = {
    "Bajo Peso": ["Riesgo de déficit nutricional ↑", "Puede afectar energía y defensas", "Conviene aumentar ingesta calórica de calidad", "Recomendable acudir a nutrición"],
    "Peso Saludable": ["Riesgo cardiovascular bajo", "Riesgo metabólico bajo", "Mantén tus hábitos actuales", "Sigue con controles periódicos"],
    "Sobrepeso": ["Riesgo cardiovascular ↑", "Riesgo metabólico ↑", "Conviene mejorar la alimentación", "Recomendable acudir a nutrición"],
    "Obesidad": ["Riesgo cardiovascular ↑↑", "Riesgo metabólico ↑↑", "Conviene reducir peso", "Recomendable acudir a nutrición"],
}

_ESTADO_CHECKLIST_EN = {
    "Bajo Peso": ["Increased risk of nutritional deficiency ↑", "May affect energy and immune defenses", "Consider increasing quality caloric intake", "Recommended to see a nutritionist"],
    "Peso Saludable": ["Low cardiovascular risk", "Low metabolic risk", "Keep up your current habits", "Continue with periodic check-ups"],
    "Sobrepeso": ["Increased cardiovascular risk ↑", "Increased metabolic risk ↑", "Consider improving your diet", "Recommended to see a nutritionist"],
    "Obesidad": ["Increased cardiovascular risk ↑↑", "Increased metabolic risk ↑↑", "Consider reducing weight", "Recommended to see a nutritionist"],
}


def tarjeta_estado_nutricional(categoria):
    """Sección 4: tarjeta 'Estado Nutricional' tipo diagnóstico con checklist, en vez de
    mostrar solamente la palabra de la categoría."""
    estilo = color_categoria_imc(categoria)
    _en = st.session_state.get("idioma", "Español") == "English"
    _dic = _ESTADO_CHECKLIST_EN if _en else _ESTADO_CHECKLIST
    _fallback_key = "Sobrepeso"
    _items = _dic.get(categoria, _dic[_fallback_key])
    _lis = "".join(f'<div class="estado-nutri-item"><span>✓</span><span>{it}</span></div>' for it in _items)
    st.markdown(f"""
    <div class="bento-card" style="border-top:4px solid {estilo['hex']};">
        <span class="bento-eyebrow">🩺 {T("Estado Nutricional", "Nutritional Status")}</span>
        <div style="font-weight:800;font-size:1.2rem;color:{estilo['hex']};margin:4px 0 8px 0;">{_cat_imc_txt(categoria)}</div>
        {_lis}
    </div>
    """, unsafe_allow_html=True)


def interpretacion_inteligente_imc(imc, categoria, etapa, riesgo_txt):
    """Sección 5: caja 'Interpretación Inteligente' con bullets, en el mismo estilo que el
    resumen clínico del análisis sanguíneo."""
    _en = st.session_state.get("idioma", "Español") == "English"
    _puntos = []
    if categoria == "Peso Saludable":
        if _en:
            _puntos = ["Your weight is within the healthy range for your age and height.",
                        "The goal is to maintain your current habits.",
                        "Continue with regular physical activity.",
                        "Keep a varied, balanced diet."]
        else:
            _puntos = ["Tu peso está dentro del rango saludable para tu edad y estatura.",
                        "El objetivo es mantener tus hábitos actuales.",
                        "Continúa con actividad física regular.",
                        "Mantén una alimentación variada y equilibrada."]
    else:
        if _en:
            _puntos = [f"There is a weight {'deficit' if categoria == 'Bajo Peso' else 'excess'} according to your BMI{' and percentile' if etapa in ('Niñez', 'Adolescencia') else ''}.",
                        "Growth and weight changes should continue to be monitored.",
                        "Consider reducing sugary drinks and ultra-processed foods." if categoria != "Bajo Peso" else "Consider increasing caloric intake with nutritious foods.",
                        "Increase physical activity and take care of sleep hours."]
        else:
            _puntos = [f"Existe {'déficit' if categoria == 'Bajo Peso' else 'exceso'} de peso según tu IMC{' y percentil' if etapa in ('Niñez', 'Adolescencia') else ''}.",
                        "El crecimiento y la evolución del peso deben seguir vigilándose.",
                        "Conviene reducir bebidas azucaradas y ultraprocesados." if categoria != "Bajo Peso" else "Conviene aumentar el aporte calórico con alimentos nutritivos.",
                        "Incrementar la actividad física y cuidar las horas de sueño."]
    _bg = "#EAFAEE" if categoria == "Peso Saludable" else "#FFF6E0"
    _color = "#1E5631" if categoria == "Peso Saludable" else "#B8860B"
    _lis = "".join(f"<li>{p}</li>" for p in _puntos)
    _seg_texto = T(f"Según tu IMC{' y tu percentil' if etapa in ('Niñez','Adolescencia') else ''} (riesgo: {riesgo_txt}):",
                   f"According to your BMI{' and percentile' if etapa in ('Niñez','Adolescencia') else ''} (Risk: {riesgo_txt}):")
    st.markdown(f"""
    <div style="background:{_bg};border-radius:18px;padding:16px 20px;margin-top:6px;">
        <div style="font-weight:800;color:{_color};margin-bottom:6px;">🧠 {T("Interpretación Inteligente", "Smart Interpretation")}</div>
        <div style="font-size:0.85rem;color:#3A3A3C;">{_seg_texto}</div>
        <ul style="margin:6px 0 0 18px;padding:0;font-size:0.85rem;color:#3A3A3C;line-height:1.7;">{_lis}</ul>
    </div>
    """, unsafe_allow_html=True)


def que_influye_imc():
    """Sección 6: '¿Qué puede influir en tu IMC?' con iconos grandes (reemplaza el bloque
    'Tu IMC puede estar relacionado con', que sonaba a publicidad)."""
    st.markdown(f'<div class="info3-title" style="margin-top:4px;">🔎 {T("¿Qué puede influir en tu IMC?", "What can influence your BMI?")}</div>', unsafe_allow_html=True)
    fila_dominios_salud([
        ("🥤", "#1E88E5", T("Bebidas azucaradas", "Sugary Drinks")),
        ("🍔", "#FF9500", T("Alimentación", "Diet")),
        ("🏃", "#34C759", T("Actividad física", "Physical Activity")),
        ("😴", "#AF52DE", T("Sueño", "Sleep")),
        ("🧬", "#FF2D55", T("Genética", "Genetics")),
    ])


def recordar_alerta_clinica():
    """Sección 7: alerta tipo clínica para el aviso 'El IMC no diagnostica enfermedades'."""
    st.markdown(T("""
    <div style="background:#FFF9E5;border:1px solid #FFE58F55;border-radius:16px;padding:16px 18px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">💡 Importante</div>
        <div style="font-size:0.85rem;color:#7A5C00;line-height:1.6;">
        El IMC <b>NO</b> diagnostica enfermedades. Es una herramienta de detección.<br>
        Siempre debe interpretarse junto con:<br>
        ✔ Edad &nbsp;&nbsp; ✔ Sexo &nbsp;&nbsp; ✔ Composición corporal &nbsp;&nbsp; ✔ Evaluación clínica
        </div>
    </div>
    """, """
    <div style="background:#FFF9E5;border:1px solid #FFE58F55;border-radius:16px;padding:16px 18px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">💡 Important</div>
        <div style="font-size:0.85rem;color:#7A5C00;line-height:1.6;">
        BMI does <b>NOT</b> diagnose diseases. It is a screening tool.<br>
        It should always be interpreted together with:<br>
        ✔ Age &nbsp;&nbsp; ✔ Sex &nbsp;&nbsp; ✔ Body composition &nbsp;&nbsp; ✔ Clinical evaluation
        </div>
    </div>
    """), unsafe_allow_html=True)


def links_uniformes_mas_info():
    """Sección 8: fila de enlaces 'Más información' con estilo uniforme (CDC, OMS, MedlinePlus,
    Mayo Clinic), reemplazando los botones grandes tipo anuncio."""
    st.markdown(f'<div class="info3-title" style="margin-top:4px;">📚 {T("Más información", "More Information")}</div>', unsafe_allow_html=True)
    cl1, cl2, cl3, cl4 = st.columns(4)
    _en_links = st.session_state.get("idioma", "Español") == "English"
    _links = [
        ("📚", "#1565C0", "CDC", "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html" if _en_links else "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html"),
        ("❤️", "#C0392B", "WHO" if _en_links else "OMS", "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight" if _en_links else "https://www.who.int/es/news-room/fact-sheets/detail/obesity-and-overweight"),
        ("🥗", "#2E9E4A", "MedlinePlus", "https://medlineplus.gov/ency/article/007196.htm" if _en_links else "https://medlineplus.gov/spanish/ency/article/007196.htm"),
        ("🏥", "#AF52DE", "Mayo Clinic", "https://www.mayoclinic.org/healthy-lifestyle/adult-health/in-depth/bmi-calculator/itt-20084938" if _en_links else "https://www.mayoclinic.org/es/healthy-lifestyle/adult-health/in-depth/bmi-calculator/itt-20084938"),
    ]
    for _col, (_ic, _co, _tt, _url) in zip([cl1, cl2, cl3, cl4], _links):
        with _col:
            st.markdown(f"""
            <a href="{_url}" target="_blank" style="text-decoration:none;">
                <div class="bento-card" style="text-align:center;padding:14px 8px;">
                    <div style="font-size:1.3rem;">{_ic}</div>
                    <div style="font-weight:800;font-size:0.78rem;color:{_co};margin-top:4px;">{_tt}</div>
                </div>
            </a>
            """, unsafe_allow_html=True)


_ACCIONES_DESDE_HOY = [
    ("🥛", "Cambia gaseosas por agua"), ("🚶", "Camina 30 minutos"), ("🍎", "Come fruta"),
    ("🥦", "Más verduras"), ("😴", "Duerme suficiente"), ("⚽", "Muévete todos los días"),
]

_ACCIONES_DESDE_HOY_EN = [
    ("🥛", "Swap soda for water"), ("🚶", "Walk 30 minutes"), ("🍎", "Eat fruit"),
    ("🥦", "More vegetables"), ("😴", "Sleep enough"), ("⚽", "Move every day"),
]


def acciones_desde_hoy():
    """Sección 12: '¿Qué puedes hacer desde hoy?' con tarjetas cortas de hábitos, en vez de
    consejos largos en párrafo."""
    st.markdown(T("#### 🌱 ¿Qué puedes hacer desde hoy?", "#### 🌱 What can you do starting today?"))
    _lista = _ACCIONES_DESDE_HOY_EN if st.session_state.get("idioma", "Español") == "English" else _ACCIONES_DESDE_HOY
    _cols = st.columns(len(_lista))
    for _col, (_em, _txt) in zip(_cols, _lista):
        with _col:
            st.markdown(f"""
            <div class="accion-card">
                <div class="accion-emoji">{_em}</div>
                <div class="accion-txt">{_txt}</div>
            </div>
            """, unsafe_allow_html=True)


def progreso_hacia_meta_imc(imc, categoria):
    """Sección 13: barra de progreso del IMC actual hacia la meta saludable (22), conectando
    con la hoja de Control de Peso / Proyección."""
    if categoria == "Peso Saludable":
        st.success(T(f"🎯 Tu IMC actual ({imc}) ya está dentro del rango saludable (18.5 – 24.9). ¡Sigue así!",
                      f"🎯 Your current BMI ({imc}) is already within the healthy range (18.5 – 24.9). Keep it up!"))
        return
    _min_v, _max_v, _meta = 10.0, 40.0, 22.0
    _pos_tu = max(2.0, min(98.0, (imc - _min_v) / (_max_v - _min_v) * 100))
    _pos_meta = max(2.0, min(98.0, (_meta - _min_v) / (_max_v - _min_v) * 100))
    _fill_izq, _fill_der = (min(_pos_tu, _pos_meta), max(_pos_tu, _pos_meta))
    _diff = round(abs(imc - _meta), 1)
    st.markdown(f"""
    <div class="bento-card">
        <span class="bento-eyebrow">📈 {T("Progreso hacia un IMC saludable", "Progress toward a healthy BMI")}</span>
        <div style="position:relative;">
            <div class="progreso-imc-meta" style="left:{_pos_meta:.1f}%;">🎯 {T("Meta", "Goal")}<br>{_meta:g}</div>
            <div class="progreso-imc-track">
                <div class="progreso-imc-fill" style="left:{_fill_izq:.1f}%;width:{max(1.0, _fill_der - _fill_izq):.1f}%;"></div>
            </div>
            <div class="progreso-imc-tu" style="left:{_pos_tu:.1f}%;">📍 {T("Tú", "You")}<br>{imc:g}</div>
        </div>
        <div style="margin-top:26px;font-size:0.85rem;color:#5C6B60;">
        {T("Faltan aproximadamente", "About")} <b style="color:#1E5631;">{_diff} {T("puntos de IMC", "BMI points")}</b> {T("para entrar al rango saludable.", "left to reach the healthy range.")}
        </div>
    </div>
    """, unsafe_allow_html=True)


def conexion_resto_sistema():
    """Sección 14: enlaces cruzados hacia otras hojas del sistema para que se sienta como
    una sola plataforma y no como hojas aisladas."""
    st.markdown(T("#### 🔗 ¿Cómo influye este resultado en el resto del sistema?",
                   "#### 🔗 How does this result affect the rest of the system?"))
    _en_con = st.session_state.get("idioma", "Español") == "English"
    _conexiones = [
        ("🩸", "#FF3B30", "Blood Test" if _en_con else "Análisis sanguíneo",
         "Overweight can raise cholesterol and triglycerides." if _en_con else "El sobrepeso puede elevar colesterol y triglicéridos."),
        ("🔥", "#FF9500", "BMR", "Your metabolism was calculated using this data." if _en_con else "Tu metabolismo se calculó usando estos datos."),
        ("🍎", "#34C759", "Diet" if _en_con else "Dieta",
         "Your meal plan was generated considering your BMI." if _en_con else "Tu plan alimenticio fue generado considerando tu IMC."),
        ("📈", "#5AC8FA", "Projection" if _en_con else "Proyección",
         "Simulate how your weight would change with your current goal." if _en_con else "Simula cómo cambiaría tu peso con tu meta actual."),
    ]
    for _ic, _co, _tt, _de in _conexiones:
        st.markdown(f"""
        <div class="conexion-card">
            <span class="conexion-icon" style="background:{_co}1A;color:{_co};">{_ic}</span>
            <div>
                <div class="conexion-title">{_tt}</div>
                <div class="conexion-desc">{_de}</div>
            </div>
            <span class="conexion-arrow">→</span>
        </div>
        """, unsafe_allow_html=True)


# =========================================================================================
# HOJA 3 (TMB) — ilustración de qué es, resultado, fórmula horizontal por género (colores
# distintos, sin azul/rosa, flechas hacia la derecha), tarjeta de autoría corregida, etc.
# =========================================================================================
def ilustracion_que_es_tmb():
    """Sección 1: ilustración simple de qué es la TMB (mientras duermes, tu cuerpo sigue
    gastando energía en funciones vitales)."""
    st.markdown(T("""
    <div class="tmb-ilustra-wrap">
        <div style="font-size:2.4rem;">😴</div>
        <div class="tmb-ilustra-item">Estás durmiendo</div>
        <div class="tmb-ilustra-flecha">↓</div>
        <div class="tmb-ilustra-item">❤️ Sigue latiendo &nbsp;·&nbsp; 🫁 Sigues respirando</div>
        <div class="tmb-ilustra-item">🧠 El cerebro trabaja &nbsp;·&nbsp; 🌡️ Mantienes tu temperatura</div>
        <div class="tmb-ilustra-flecha">↓</div>
        <div style="font-size:1.3rem;font-weight:800;color:#E67E22;">🔥 Todo eso necesita energía</div>
        <div style="margin-top:14px;font-size:0.86rem;color:#5C6B60;line-height:1.6;max-width:560px;margin-left:auto;margin-right:auto;">
        Tu cuerpo nunca se "apaga". Incluso mientras descansas sigue gastando energía para mantenerte con vida.
        A esa energía la llamamos <b style="color:#E67E22;">Tasa Metabólica Basal (TMB)</b>.
        </div>
    </div>
    """, """
    <div class="tmb-ilustra-wrap">
        <div style="font-size:2.4rem;">😴</div>
        <div class="tmb-ilustra-item">You're sleeping</div>
        <div class="tmb-ilustra-flecha">↓</div>
        <div class="tmb-ilustra-item">❤️ Heart keeps beating &nbsp;·&nbsp; 🫁 You keep breathing</div>
        <div class="tmb-ilustra-item">🧠 Your brain keeps working &nbsp;·&nbsp; 🌡️ You maintain your temperature</div>
        <div class="tmb-ilustra-flecha">↓</div>
        <div style="font-size:1.3rem;font-weight:800;color:#E67E22;">🔥 All of that needs energy</div>
        <div style="margin-top:14px;font-size:0.86rem;color:#5C6B60;line-height:1.6;max-width:560px;margin-left:auto;margin-right:auto;">
        Your body never "shuts off". Even while you rest it keeps burning energy to keep you alive.
        We call that energy your <b style="color:#E67E22;">Basal Metabolic Rate (BMR)</b>.
        </div>
    </div>
    """), unsafe_allow_html=True)


def tarjeta_resultado_tmb(tmb_valor):
    """Sección 2: tarjeta grande y limpia con el resultado de la TMB."""
    st.markdown(T(f"""
    <div class="tmb-resultado-card">
        <span class="bento-eyebrow">🔥 Tu TMB</span>
        <div class="tmb-resultado-num">{tmb_valor:.0f} kcal/día</div>
        <div style="font-size:0.88rem;color:#5C6B60;max-width:420px;margin:0 auto;line-height:1.6;">
        Tu cuerpo necesita aproximadamente <b style="color:#E67E22;">{tmb_valor:.0f} kcal</b> al día
        únicamente para mantener sus funciones vitales.
        </div>
    </div>
    """, f"""
    <div class="tmb-resultado-card">
        <span class="bento-eyebrow">🔥 Your BMR</span>
        <div class="tmb-resultado-num">{tmb_valor:.0f} kcal/day</div>
        <div style="font-size:0.88rem;color:#5C6B60;max-width:420px;margin:0 auto;line-height:1.6;">
        Your body needs approximately <b style="color:#E67E22;">{tmb_valor:.0f} kcal</b> per day
        just to maintain its vital functions.
        </div>
    </div>
    """), unsafe_allow_html=True)


def formula_horizontal_tmb(peso, estatura, edad, genero_activo, tmb_valor):
    """Sección 3: fórmula de Mifflin-St Jeor mostrada de forma horizontal para Hombre y Mujer,
    cada una con su propio color (sin usar azul/rosa) y flechas apuntando a la derecha."""
    _lbl_peso, _lbl_altura, _lbl_edad, _lbl_const = (T("Peso", "Weight"), T("Altura", "Height"),
                                                      T("Edad", "Age"), T("Constante", "Constant"))
    _filas = [
        ("Hombre", T("Hombre", "Man"), "🧑", "#00897B", "#E0F2F1",
         [(_lbl_peso, f"10 × {peso:g}", f"{10*peso:.1f}"), (_lbl_altura, f"+ 6.25 × {estatura:g}", f"{6.25*estatura:.1f}"),
          (_lbl_edad, f"− 5 × {edad:g}", f"−{5*edad:.1f}"), (_lbl_const, "+ 5", "+5")],
         (10 * peso) + (6.25 * estatura) - (5 * edad) + 5),
        ("Mujer", T("Mujer", "Woman"), "🧑‍🦱", "#D4692B", "#FFF1E6",
         [(_lbl_peso, f"10 × {peso:g}", f"{10*peso:.1f}"), (_lbl_altura, f"+ 6.25 × {estatura:g}", f"{6.25*estatura:.1f}"),
          (_lbl_edad, f"− 5 × {edad:g}", f"−{5*edad:.1f}"), (_lbl_const, "− 161", "−161")],
         (10 * peso) + (6.25 * estatura) - (5 * edad) - 161),
    ]
    for _nombre, _nombre_disp, _icono, _color, _fondo, _pasos, _res in _filas:
        _es_activo = _nombre == genero_activo
        _boxes = "".join(
            f'<div class="tmb-formula-box" style="background:{_color}1A;color:{_color};">{p}<span class="tmb-box-sub">{op}</span></div>'
            f'<span class="tmb-formula-arrow" style="color:{_color};">→</span>'
            for p, op, val in _pasos
        )
        _txt_formula_para = T("Fórmula para", "Formula for")
        _txt_tu_formula = T("Tu fórmula", "Your formula")
        _txt_tmb_lbl = T("TMB", "BMR")
        _txt_dia_lbl = T("día", "day")
        st.markdown(f"""
        <div class="tmb-formula-genero-wrap" style="{'box-shadow:0 0 0 2px ' + _color + ';' if _es_activo else ''}">
            <div class="tmb-formula-genero-title" style="color:{_color};">{_icono} {_txt_formula_para} {_nombre_disp}
                {' <span class=\"bento-pill\" style=\"background:' + _color + ';color:#FFFFFF;\">' + _txt_tu_formula + '</span>' if _es_activo else ''}</div>
            <div class="tmb-formula-flow">
                {_boxes}
                <div class="tmb-formula-box" style="background:{_color};color:#FFFFFF;">= {_txt_tmb_lbl}<span class="tmb-box-sub">{_res:.0f} kcal/{_txt_dia_lbl}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def tarjeta_quien_creo_formula():
    """Sección 3b (corregida): Mifflin-St Jeor no es una persona, sino el nombre de la
    ecuación publicada en 1990 por un equipo de investigadores."""
    st.markdown(T("""
    <div class="tmb-quien-card">
        <div style="font-weight:800;color:#5856D6;margin-bottom:6px;">👨‍🔬 ¿Quién desarrolló esta fórmula?</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        La ecuación de <b>Mifflin–St Jeor</b> fue publicada en 1990 por los investigadores
        <b>Mark D. Mifflin</b>, <b>Sachiko T. St Jeor</b> y su equipo. Actualmente es una de las
        fórmulas más utilizadas por nutricionistas y hospitales para estimar la Tasa Metabólica
        Basal, por su buena precisión en adultos.
        </div>
    </div>
    """, """
    <div class="tmb-quien-card">
        <div style="font-weight:800;color:#5856D6;margin-bottom:6px;">👨‍🔬 Who developed this formula?</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        The <b>Mifflin–St Jeor</b> equation was published in 1990 by researchers
        <b>Mark D. Mifflin</b>, <b>Sachiko T. St Jeor</b> and their team. It is currently one of the
        formulas most widely used by nutritionists and hospitals to estimate Basal Metabolic
        Rate, due to its good accuracy in adults.
        </div>
    </div>
    """), unsafe_allow_html=True)


def tarjeta_por_que_mifflin():
    """Sección 4: mini comparación de por qué se usa Mifflin-St Jeor."""
    _items = [T("Mayor precisión que fórmulas antiguas.", "Higher accuracy than older formulas."),
              T("Recomendada en nutrición clínica.", "Recommended in clinical nutrition."),
              T("Utilizada por profesionales de la salud.", "Used by healthcare professionals."),
              T("Sirve para calcular las calorías que necesita el cuerpo en reposo.",
                "Used to calculate the calories the body needs at rest.")]
    _lis = "".join(f'<div class="tmb-porque-item"><span>✔</span><span>{it}</span></div>' for it in _items)
    st.markdown(f"""
    <div class="tmb-porque-card">
        <div style="font-weight:800;color:#0E6B4F;margin-bottom:2px;">📚 {T("¿Por qué usamos Mifflin-St Jeor?", "Why do we use Mifflin-St Jeor?")}</div>
        {_lis}
    </div>
    """, unsafe_allow_html=True)


def flujo_modulos_tmb():
    """Sección 5: flujo horizontal (flechas a la derecha) de los módulos que usan la TMB."""
    st.markdown(T("""
    <div class="tmb-flujo-wrap">
        <span class="bento-eyebrow">🔗 ¿Qué módulos usan la TMB?</span>
        <div class="tmb-flujo-row">
            <div class="tmb-flujo-chip" style="background:#FFF3E0;color:#E67E22;">🔥 TMB</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">⚡ RCD</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">🥗 Dieta</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">🍚 Macronutrientes</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">📈 Proyección</div>
        </div>
        <div style="margin-top:14px;font-size:0.84rem;color:#5C6B60;">
        Toda la plataforma utiliza este cálculo como punto de partida.
        </div>
    </div>
    """, """
    <div class="tmb-flujo-wrap">
        <span class="bento-eyebrow">🔗 Which modules use BMR?</span>
        <div class="tmb-flujo-row">
            <div class="tmb-flujo-chip" style="background:#FFF3E0;color:#E67E22;">🔥 BMR</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">⚡ DCR</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">🥗 Diet</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">🍚 Macronutrients</div>
            <span class="tmb-formula-arrow" style="color:#8A94A6;">→</span>
            <div class="tmb-flujo-chip">📈 Projection</div>
        </div>
        <div style="margin-top:14px;font-size:0.84rem;color:#5C6B60;">
        The whole platform uses this calculation as its starting point.
        </div>
    </div>
    """), unsafe_allow_html=True)


def central_energetica_tmb(tmb_valor):
    """Ilustración alternativa tipo 'central eléctrica': la TMB alimenta los órganos vitales,
    cada uno con un pequeño indicador luminoso."""
    _organos = [("❤️", T("Corazón", "Heart")), ("🧠", T("Cerebro", "Brain")), ("🫁", T("Pulmones", "Lungs")),
                ("🌡️", T("Temperatura", "Temperature")), ("🩸", T("Circulación", "Circulation"))]
    _leds = "".join(f'<div class="tmb-central-organo"><div style="font-size:1.6rem;">{ic}</div>'
                     f'<div class="tmb-central-led"></div><div class="tmb-central-label">{lb}</div></div>' for ic, lb in _organos)
    _txt_central = T("CENTRAL ENERGÉTICA", "ENERGY POWER PLANT")
    st.markdown(f"""
    <div class="tmb-central-wrap">
        <div style="font-size:1.6rem;">⚡</div>
        <div style="font-weight:800;letter-spacing:0.06em;font-size:0.85rem;color:#C7CBE0;">{_txt_central}</div>
        <div class="tmb-central-kcal">🔥 {tmb_valor:.0f} kcal</div>
        <div class="tmb-central-organos">{_leds}</div>
    </div>
    """, unsafe_allow_html=True)


def interpretacion_inteligente_tmb(tmb_valor):
    """Sección 6: resumen inteligente breve, dejando claro que la TMB no incluye actividad física."""
    st.markdown(T(f"""
    <div style="background:#FFF3E0;border-radius:18px;padding:16px 20px;margin-top:6px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">🧠 Interpretación Inteligente</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        Tu organismo necesita aproximadamente <b>{tmb_valor:.0f} kcal</b> al día para mantener sus funciones vitales.<br>
        Este valor <b>NO</b> representa las calorías que necesitas para hacer ejercicio, caminar o estudiar.<br>
        Es la energía mínima necesaria para vivir.
        </div>
    </div>
    """, f"""
    <div style="background:#FFF3E0;border-radius:18px;padding:16px 20px;margin-top:6px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">🧠 Smart Interpretation</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        Your body needs approximately <b>{tmb_valor:.0f} kcal</b> per day to maintain its vital functions.<br>
        This value does <b>NOT</b> represent the calories you need to exercise, walk, or study.<br>
        It is the minimum energy necessary to live.
        </div>
    </div>
    """), unsafe_allow_html=True)


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
# HOJA 5 — CONTROL DE PESO: componentes visuales creativos
# (tarjetas de lapsos/ajuste, línea de tiempo de misión, diales de macros, panel integrado)
# =========================================================================================

_ICONS_SVG = {
    "bascula": """<svg width="100%" height="100%" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="30" width="48" height="26" rx="6" fill="rgba(255,255,255,0.18)" stroke="white" stroke-width="2.5"/>
        <circle cx="32" cy="43" r="8" fill="none" stroke="white" stroke-width="2.5"/>
        <path d="M32 43 L36 37" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M32 8 L32 20 M24 14 L40 14" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M18 20 L32 20 L26 28 Z" fill="white"/>
    </svg>""",
    "musculo": """<svg width="100%" height="100%" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 44 C10 34 12 22 22 16 C26 13 32 13 36 16 C34 18 33 21 34 24 C40 22 46 24 49 29
                 C52 34 51 40 47 44 C50 46 51 50 49 53 C46 57 40 56 37 53 C33 57 25 58 20 54
                 C15 51 13 47 14 44 Z" fill="rgba(255,255,255,0.20)" stroke="white" stroke-width="2.5" stroke-linejoin="round"/>
        <path d="M22 30 C26 27 32 27 36 30" stroke="white" stroke-width="2" stroke-linecap="round"/>
    </svg>""",
    "balanza": """<svg width="100%" height="100%" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M32 10 L32 50" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M14 50 L50 50" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M10 16 L54 16" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="32" cy="12" r="3" fill="white"/>
        <path d="M10 16 L4 30 A9 9 0 0 0 16 30 Z" fill="rgba(255,255,255,0.25)" stroke="white" stroke-width="2"/>
        <path d="M54 16 L48 30 A9 9 0 0 0 60 30 Z" fill="rgba(255,255,255,0.25)" stroke="white" stroke-width="2"/>
    </svg>""",
}


def _tarjeta_creativa(icono_key, color1, color2, titulo, texto, seleccionada=False):
    """Tarjeta con gradiente vibrante, icono SVG grande y efecto hover de zoom/brillo (Prompt 1)."""
    clase_extra = " cp5-selected" if seleccionada else ""
    st.markdown(f"""
    <div class="cp5-card{clase_extra}" style="background:linear-gradient(135deg,{color1} 0%,{color2} 100%);">
        <div class="cp5-icon">{_ICONS_SVG[icono_key]}</div>
        <div class="cp5-title">{titulo}</div>
        <div class="cp5-text">{texto}</div>
    </div>
    """, unsafe_allow_html=True)


def _build_tarjetas_lapsos_y_ajuste(objetivo_actual):
    """Fila 1 'Respetar Lapsos' + Fila 2 'Ajuste Calórico', como cuadrícula de tarjetas
    gráficas animadas con lenguaje coloquial (reemplaza los dos expanders de texto)."""
    st.markdown("#### ⏳ ¡Respeta los Lapsos!")
    f1, f2, f3 = st.columns(3)
    with f1:
        _tarjeta_creativa("bascula", "#FF3B30", "#C0392B", "¡Dale un Descanso a tu Cuerpo!",
                           "No te pases de 16 semanas. El cuerpo se acostumbra y el cambio es lento. "
                           "Haz paradas técnicas de una semana.",
                           seleccionada=(objetivo_actual == "Bajar de peso"))
    with f2:
        _tarjeta_creativa("musculo", "#007AFF", "#0A3D91", "¡Con Calma, sin Prisa!",
                           "Más comida no significa más músculo. ¡Significa más grasa! "
                           "Sube de peso poco a poco.",
                           seleccionada=(objetivo_actual == "Subir de peso"))
    with f3:
        _tarjeta_creativa("balanza", "#34C759", "#1E5631", "¡El Truco Maestro!",
                           "Usa esto para estabilizar tu nuevo peso antes de cambiar de meta. "
                           "Es el 'reset' hormonal.",
                           seleccionada=(objetivo_actual == "Mantenerse"))

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("#### 🔥 ¡Elige tu Ajuste Calórico!")
    if objetivo_actual == "Bajar de peso":
        a1, a2, a3 = st.columns(3)
        niveles = [
            (a1, "#FFADAD", "#FF3B30", "Conservador -10%",
             "Cerca de tu peso ideal? Este es suave y cuida al máximo tu músculo.", "bascula"),
            (a2, "#FF6B6B", "#C0392B", "Moderado -20%",
             "¡El punto justo! Funciona para la mayoría de personas, sin sufrir.", "bascula"),
            (a3, "#8B1E1E", "#4A0E0E", "Agresivo -30%",
             "Solo si tienes bastante que bajar, y por poco tiempo (4-6 semanas).", "bascula"),
        ]
    elif objetivo_actual == "Subir de peso":
        a1, a2, a3 = st.columns(3)
        niveles = [
            (a1, "#9EC5FF", "#007AFF", "Limpio / Magro +10%",
             "Sube poquito a poco, ganando músculo sin llenarte de grasa de más.", "musculo"),
            (a2, "#4A90E2", "#0A3D91", "Moderado +15%",
             "El estándar para ganar músculo de forma progresiva y pareja.", "musculo"),
            (a3, "#1B3A6B", "#0A1F3D", "Exigente +20%",
             "Para cuando tu metabolismo es súper rápido y cuesta mucho subir.", "musculo"),
        ]
    else:
        a1, a2, a3 = st.columns([1, 1, 1])
        niveles = [
            (a2, "#7BE0A0", "#1E5631", "Ajuste 0%",
             "¡Aquí no se sube ni se baja! Comes justo lo que gastas para estabilizarte.", "balanza"),
        ]
    for col, c1_, c2_, titulo_n, texto_n, icono_n in niveles:
        with col:
            _tarjeta_creativa(icono_n, c1_, c2_, titulo_n, texto_n, seleccionada=True)


def _gauge_altair(pct, color_hex, big_text, sub_text, key):
    """Dial tipo velocímetro/donut con Altair — usado para los diales de macronutrientes (Prompt 2)."""
    pct = max(0.0, min(pct, 1.0))
    df = pd.DataFrame({"cat": ["valor", "resto"], "val": [pct, 1 - pct]})
    orden = pd.CategoricalDtype(categories=["valor", "resto"], ordered=True)
    df["cat"] = df["cat"].astype(orden)
    arco = alt.Chart(df).mark_arc(innerRadius=62, outerRadius=88, cornerRadius=10).encode(
        theta=alt.Theta("val:Q", stack=True),
        color=alt.Color("cat:N", scale=alt.Scale(domain=["valor", "resto"], range=[color_hex, "#EDEDED"]), legend=None),
        order=alt.Order("cat", sort="ascending"),
    ).properties(width=190, height=190)
    texto = alt.Chart(pd.DataFrame({"t": [f"{pct*100:.0f}%"]})).mark_text(
        fontSize=26, fontWeight="bold", color=color_hex
    ).encode(text="t:N")
    st.altair_chart(arco + texto, use_container_width=True)
    st.markdown(f"""
    <div style="text-align:center;margin-top:-10px;">
        <div style="font-weight:800;font-size:1.05rem;color:{color_hex};">{big_text}</div>
        <div style="font-size:0.8rem;color:#5C6B60;margin-top:2px;">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


def _datos_interpretacion_objetivo(objetivo_v):
    """Devuelve (color, fondo, texto, checks) según el objetivo elegido — usado tanto por la
    tarjeta de interpretación como por la tarjeta combinada del panel de macros."""
    if objetivo_v == "Bajar de peso":
        color, fondo = "#FF9500", "#FFF3E0"
        texto = T(
            "Con este ajuste, consumirás <b>menos energía de la que gastas</b>.<br>"
            "Tu cuerpo utilizará parte de sus reservas de grasa para completar esa diferencia.",
            "With this adjustment, you'll consume <b>less energy than you burn</b>.<br>"
            "Your body will use part of its fat reserves to make up that difference."
        )
        checks = [T("Déficit calórico controlado", "Controlled caloric deficit"),
                  T("Sin bajar de tu TMB", "Never below your BMR"),
                  T("Compatible con un plan saludable", "Compatible with a healthy plan")]
    elif objetivo_v == "Subir de peso":
        color, fondo = "#007AFF", "#EAF3FF"
        texto = T(
            "Con este ajuste, consumirás <b>más energía de la que gastas</b>.<br>"
            "Tu cuerpo usará ese excedente para construir tejido nuevo, como músculo.",
            "With this adjustment, you'll consume <b>more energy than you burn</b>.<br>"
            "Your body will use that surplus to build new tissue, such as muscle."
        )
        checks = [T("Superávit calórico controlado", "Controlled caloric surplus"),
                  T("Por encima de tu TMB", "Above your BMR"),
                  T("Compatible con un plan saludable", "Compatible with a healthy plan")]
    else:
        color, fondo = "#34C759", "#EAFAEE"
        texto = T(
            "Con este ajuste, consumirás <b>aproximadamente la misma energía que gastas</b>.<br>"
            "Tu cuerpo no necesita usar reservas ni acumular un excedente.",
            "With this adjustment, you'll consume <b>approximately the same energy you burn</b>.<br>"
            "Your body doesn't need to use reserves or build up a surplus."
        )
        checks = [T("Sin déficit ni superávit", "No deficit or surplus"),
                  T("Por encima de tu TMB", "Above your BMR"),
                  T("Ideal para conservar tu peso actual", "Ideal for maintaining your current weight")]
    return color, fondo, texto, checks


def _tarjeta_interpretacion_objetivo(objetivo_v, ajuste_aplicado_v, tmb_v):
    """Tarjeta corta 'Qué significa tu nuevo objetivo': explica en pocas líneas qué hace el
    cuerpo con el ajuste calórico elegido, según el objetivo (dinámico)."""
    color, fondo, texto, checks = _datos_interpretacion_objetivo(objetivo_v)

    _checks_html = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:6px;">'
        f'<span style="color:{color};font-weight:900;">✔</span>'
        f'<span style="font-size:0.85rem;color:#17301F;">{c}</span></div>'
        for c in checks
    )
    st.markdown(f"""
    <div class="bento-card" style="background:{fondo};border:1.5px solid {color}33;">
        <div style="font-weight:800;color:{color};font-size:0.95rem;margin-bottom:6px;">🧠 {T('¿Qué significa tu nuevo objetivo?', 'What does your new goal mean?')}</div>
        <div style="font-size:0.85rem;color:#3C3C43;line-height:1.55;">{texto}</div>
        {_checks_html}
    </div>
    """, unsafe_allow_html=True)


def _build_panel_macros_creativo(gr_prot_v, gr_gras_v, gr_carb_v, peso_v, objetivo_v):
    """Tarjeta combinada de interpretación del objetivo + recordatorio de recálculo
    (reemplaza el aviso naranja anterior y el panel de diales de macros, ya retirado)."""
    _color_o, _fondo_o, _texto_o, _checks_o = _datos_interpretacion_objetivo(objetivo_v)
    _checks_html_o = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:6px;">'
        f'<span style="color:{_color_o};font-weight:900;">✔</span>'
        f'<span style="font-size:0.85rem;color:#17301F;">{c}</span></div>'
        for c in _checks_o
    )
    st.markdown(f"""
    <div class="bento-card" style="background:{_fondo_o};border:1.5px solid {_color_o}33;margin-top:14px;">
        <div style="font-weight:800;color:{_color_o};font-size:0.95rem;margin-bottom:6px;">🧠 {T('¿Qué significa tu nuevo objetivo?', 'What does your new goal mean?')}</div>
        <div style="font-size:0.85rem;color:#3C3C43;line-height:1.55;">{_texto_o}</div>
        {_checks_html_o}
        <hr style="border:none;border-top:1px solid {_color_o}33;margin:12px 0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:1.1rem;">📌</span>
            <span style="font-weight:800;color:{_color_o};">{T('Recuerda', 'Remember')}</span>
        </div>
        <div style="font-size:0.85rem;color:#3C3C43;line-height:1.7;">
            {T('Tu plan debe actualizarse cuando:', 'Your plan should be updated when:')}<br>
            ⚖️ {T('Cambies entre 3 y 5 kg.', 'You change between 3 and 5 kg.')}<br>
            🏃 {T('Cambie tu actividad física.', 'Your physical activity changes.')}<br>
            📏 {T('Cambien tus medidas corporales.', 'Your body measurements change.')}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _speedometer_svg(pct, color_hex):
    """Mini velocímetro semicircular en SVG puro (aguja), para las tarjetas de misión (Prompt 3)."""
    pct = max(0.0, min(pct, 1.0))
    angulo = -90 + (pct * 180)
    import math
    rad = math.radians(angulo)
    cx, cy, r = 60, 60, 46
    x2 = cx + r * math.cos(rad)
    y2 = cy + r * math.sin(rad)
    return f"""<svg viewBox="0 0 120 70" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 60 A46 46 0 0 1 106 60" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="10" stroke-linecap="round"/>
        <path d="M14 60 A46 46 0 0 1 106 60" fill="none" stroke="{color_hex}" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="{pct*145} 999"/>
        <line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="white" stroke-width="3" stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy}" r="5" fill="white"/>
    </svg>"""


def _build_mission_timeline(objetivo_actual):
    """Panel oscuro tipo 'línea de tiempo de misión' que reemplaza la tabla de Ritmos y lapsos (Prompt 3)."""
    st.markdown("#### 🚀 Panel de Misión: Ritmos y Lapsos")
    misiones = [
        {"nombre": "Pérdida", "accent": "#FF3B30", "glow": "rgba(255,59,48,0.45)", "max_sem": 16, "eje_max": 24,
         "ritmo_txt": "0.5% – 1.0% semanal", "ritmo_pct": 0.75, "activo": objetivo_actual == "Bajar de peso"},
        {"nombre": "Ganancia", "accent": "#0A84FF", "glow": "rgba(10,132,255,0.45)", "max_sem": 24, "eje_max": 24,
         "ritmo_txt": "0.25% – 0.5% semanal", "ritmo_pct": 0.45, "activo": objetivo_actual == "Subir de peso"},
        {"nombre": "Mantenimiento", "accent": "#34C759", "glow": "rgba(52,199,89,0.45)", "max_sem": 0, "eje_max": 24,
         "ritmo_txt": "0% (± 1 kg)", "ritmo_pct": 0.05, "activo": objetivo_actual == "Mantenerse"},
    ]
    html = ['<div class="cp5-mission-wrap">']
    for m in misiones:
        clase_activa = " cp5-active" if m["activo"] else ""
        pct_barra = (m["max_sem"] / m["eje_max"]) * 100 if m["eje_max"] else 0
        html.append(f'<div class="cp5-mission-card{clase_activa}" style="--mc-accent:{m["accent"]};--mc-glow:{m["glow"]};">')
        html.append('<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center;">')
        html.append('<div style="flex:2;min-width:260px;">')
        etiqueta_activa = " 🟢 TU MISIÓN ACTUAL" if m["activo"] else ""
        html.append(f'<div class="cp5-mission-title">🛰️ {m["nombre"].upper()}{etiqueta_activa}</div>')
        html.append('<div class="cp5-timeline-track">')
        html.append(f'<div class="cp5-timeline-fill" style="width:{pct_barra:.0f}%;background:{m["accent"]};"></div>')
        if m["max_sem"] > 0:
            html.append(f'<div class="cp5-timeline-flag" style="left:{pct_barra:.0f}%;">🏁</div>')
        html.append('</div>')
        texto_max = f'Máximo {m["max_sem"]} semanas' if m["max_sem"] > 0 else 'Sin límite fijo — usa pausas'
        html.append(f'<div class="cp5-timeline-labels"><span>0</span><span style="color:{m["accent"]};font-weight:700;">{texto_max}</span><span>{m["eje_max"]} sem</span></div>')
        html.append('</div>')
        html.append(f'<div style="flex:1;min-width:150px;text-align:center;">{_speedometer_svg(m["ritmo_pct"], m["accent"])}')
        html.append(f'<div style="color:white;font-weight:800;font-size:0.95rem;margin-top:2px;">{m["ritmo_txt"]}</div>')
        html.append('<div style="color:#8892A6;font-size:0.72rem;">Tu Velocidad de Cambio</div></div>')
        html.append('</div></div>')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def _build_panel_control_definitivo(rcd_v, tmb_v, rcd_final_v, ajuste_aplicado_v, objetivo_v,
                                     plazo_v, cambio_semanal_kg_v, ritmo_pct_semanal_v, recortada_tmb):
    """Panel de control integrado, con flujo visual RCD → Ajuste → ICO, gráfico de áreas de
    Plotly (RCD/TMB/ICO), dial de ritmo estimado y barra de plazo (Prompt 4)."""
    signo = "-" if objetivo_v == "Bajar de peso" else ("+" if objetivo_v == "Subir de peso" else "")

    st.markdown("#### 🖥️ Panel de Control: de tu Gasto a tu Plato")
    st.markdown(f"""
    <div class="cp5-glass-flow">
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">📊 RCD</div>
            <div class="cp5-flow-value">{rcd_v:.0f} kcal/día</div>
            <div class="cp5-flow-legend">Esto es lo que tu cuerpo gasta sin hacer nada extra.</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">🌀 Ajuste</div>
            <div class="cp5-flow-value">{signo}{ajuste_aplicado_v*100:.0f}%</div>
            <div class="cp5-flow-legend">Para {"bajar" if objetivo_v=="Bajar de peso" else ("subir" if objetivo_v=="Subir de peso" else "mantener")} de peso, este es el ajuste "justo".</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card" style="background:rgba(30,86,49,0.10);border-color:rgba(30,86,49,0.35);">
            <div class="cp5-flow-label">🍽️ ICO — Calorías Objetivo</div>
            <div class="cp5-flow-value" style="color:#1E5631;">{rcd_final_v:.0f} kcal/día</div>
            <div class="cp5-flow-legend">¡Este es tu número mágico para hoy!</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if recortada_tmb:
        st.warning(f"⚠️ **Límite fisiológico aplicado:** el ajuste elegido bajaría tu ingesta por debajo de tu "
                   f"TMB ({tmb_v:.0f} kcal/día). Nunca se debe comer menos que la TMB. Por seguridad, tu ICO "
                   f"se ajustó automáticamente a {rcd_final_v:.0f} kcal/día.")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    col_area, col_lado = st.columns([2, 1])

    with col_area:
        fig = go.Figure()
        x_eje = [0, 1]
        capas = [
            ("TMB (mínimo vital)", [tmb_v, tmb_v], "#FF9500", "rgba(255,149,0,0.15)"),
            ("RCD (mantenimiento)", [rcd_v, rcd_v], "#34C759", "rgba(52,199,89,0.15)"),
            ("ICO (tu objetivo)", [rcd_final_v, rcd_final_v], "#1E5631", "rgba(30,86,49,0.25)"),
        ]
        for nombre, y_vals, color_l, color_f in capas:
            fig.add_trace(go.Scatter(x=x_eje, y=y_vals, mode="lines", name=nombre,
                                      line=dict(color=color_l, width=3), fill="tozeroy", fillcolor=color_f))
        fig.update_layout(
            title=dict(text="Relación entre TMB, RCD e ICO", font=dict(size=15, color="#17301F")),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(title="kcal/día", gridcolor="#F0F0F0"),
            height=300, margin=dict(t=40, l=10, r=10, b=10),
            plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_lado:
        if objetivo_v != "Mantenerse":
            max_ritmo_pct = 1.0 if objetivo_v == "Bajar de peso" else 0.5
            pct_ritmo = min(ritmo_pct_semanal_v / max_ritmo_pct, 1.0) if max_ritmo_pct else 0
            color_ritmo = "#FF3B30" if objetivo_v == "Bajar de peso" else "#0A84FF"
            _gauge_altair(pct_ritmo, color_ritmo, f"{cambio_semanal_kg_v:.2f} kg/semana",
                          f"Estimamos que {'bajarás' if objetivo_v=='Bajar de peso' else 'subirás'} a este "
                          "ritmo, sin perder músculo.", "ritmo")
        else:
            _gauge_altair(0.05, "#34C759", "0 kg/semana", "Variación esperada: ± 1 kg. ¡Estás estabilizando!", "ritmo")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    _color_plazo = "#FF3B30" if objetivo_v == "Bajar de peso" else ("#0A84FF" if objetivo_v == "Subir de peso" else "#34C759")
    st.markdown(f"""
    <div style="background:#FFFFFF;border-radius:18px;padding:16px 20px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);
                border:1px solid rgba(0,0,0,0.04);">
        <div style="font-weight:800;color:{_color_plazo};font-size:0.95rem;margin-bottom:8px;">⏱️ Tu plazo recomendado</div>
        <div class="cp5-progressbar-track">
            <div class="cp5-progressbar-fill" style="width:100%;background:linear-gradient(90deg,{_color_plazo}55,{_color_plazo});"></div>
        </div>
        <div style="margin-top:8px;color:#17301F;font-size:0.9rem;">{plazo_v} ¡Haz una parada de mantenimiento después de esto!</div>
    </div>
    """, unsafe_allow_html=True)


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

@st.cache_data(show_spinner=False)
def _img_b64(path):
    """Codifica una imagen a base64 UNA sola vez (cacheado) — evita releer/recodificar
    el mismo archivo en cada rerun de Streamlit, lo que agiliza el cambio entre pestañas."""
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return None

_logo_b64 = _img_b64(_LOGO_ANCHO)

# =========================================================================================
# ENCABEZADO "LANDING" (membrete, hero, tarjetas, onboarding) — SOLO en la página de inicio
# ("0.-DATOS"). Antes se renderizaba en TODAS las hojas, lo que hacía la app notablemente más
# lenta al navegar o escribir datos (Streamlit vuelve a ejecutar todo el script en cada
# interacción). Ahora solo se construye cuando realmente se está viendo esa página.
# =========================================================================================
_EN_PORTADA = st.session_state.get("hoja_activa", "0.-DATOS") == "0.-DATOS"

if _EN_PORTADA:
    # --- 1. MEMBRETE INSTITUCIONAL — banner ancho del colegio, arriba de todo (tamaño moderado) ---
    if _LOGO_ANCHO.exists():
        st.markdown('<div style="text-align:center;margin-bottom:14px;">', unsafe_allow_html=True)
        _col_memb_l, _col_memb_c, _col_memb_r = st.columns([1, 3, 1])
        with _col_memb_c:
            st.image(str(_LOGO_ANCHO), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. LOGO (escudo) a la izquierda + HERO CIAM&SUNI (bloque verde) a la derecha, más ancho ---
    _col_esc, _col_hero = st.columns([1, 2.2])
    with _col_esc:
        _escudo_b64 = _img_b64(_ESCUDO) if _ESCUDO.exists() else None
        _escudo_img_tag = (f'<img src="data:image/png;base64,{_escudo_b64}" '
                            f'style="max-width:78%;max-height:210px;object-fit:contain;" />') if _escudo_b64 else ""
        st.markdown(f"""
        <div style="background:linear-gradient(120deg,#FFFFFF 0%,#F4F9F4 100%);border-radius:26px;
        padding:20px;margin-bottom:14px;box-shadow:0 6px 20px rgba(30,86,49,0.10);
        border:1.5px solid rgba(30,86,49,0.14);height:100%;min-height:260px;
        display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
        {_escudo_img_tag}
        <p style="margin:12px 0 0 0;font-weight:800;color:#1E5631;font-size:1.05rem;letter-spacing:-0.01em;
           font-family:Georgia,'Times New Roman',serif;">🏫 C.E.P. "Santa María Reina"</p>
        <p style="margin:2px 0 0 0;color:#5C6B60;font-size:0.85rem;font-weight:600;">Chiclayo</p>
        </div>
        """, unsafe_allow_html=True)
    with _col_hero:
        st.markdown(f"""
        <div class="hero-card" style="height:100%;min-height:260px;box-sizing:border-box;">
            <div class="hero-emoji-decor">🥗🍎🥦🥛🥑</div>
            <h1>🥗 CIAM&amp;SUNI</h1>
            <p style="margin:0 0 14px 0;font-size:1.15rem;font-weight:700;opacity:0.95;">{T("Tu Salud, Personalizada", "Your Health, Personalized")}</p>
            <p class="hero-sub">{T("CIAM&amp;SUNI analiza tu información para estimar tu estado nutricional, calcular tu "
            "requerimiento energético y ayudarte a comprender cómo influye la alimentación en tu salud, mediante "
            "explicaciones sencillas y visuales.",
            "CIAM&amp;SUNI analyzes your information to estimate your nutritional status, calculate your energy "
            "requirement, and help you understand how nutrition affects your health, through simple, visual "
            "explanations.")}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- Tarjetas de características (reemplazan los chips: 4 tarjetas claras) ---
    st.markdown(f"""
    <div class="feature-row">
        <div class="feature-card">
            <div class="fc-emoji">🍎</div>
            <div class="fc-title">{T("Nutrición personalizada", "Personalized nutrition")}</div>
            <div class="fc-text">{T("Cálculos adaptados a tus propios datos: edad, peso, altura y etapa de vida.",
            "Calculations tailored to your own data: age, weight, height and life stage.")}</div>
        </div>
        <div class="feature-card">
            <div class="fc-emoji">🧮</div>
            <div class="fc-title">{T("Basado en evidencia científica", "Based on scientific evidence")}</div>
            <div class="fc-text">{T("Fórmulas reconocidas (Mifflin-St Jeor, FAO/OMS/UNU) aplicadas paso a paso.",
            "Recognized formulas (Mifflin-St Jeor, FAO/WHO/UNU) applied step by step.")}</div>
        </div>
        <div class="feature-card">
            <div class="fc-emoji">🌡️</div>
            <div class="fc-title">{T("Adaptado al clima de Chiclayo", "Adapted to Chiclayo's climate")}</div>
            <div class="fc-text">{T("Un ajuste extra que considera el clima cálido de nuestra región.",
            "An extra adjustment that accounts for our region's warm climate.")}</div>
        </div>
        <div class="feature-card">
            <div class="fc-emoji">📊</div>
            <div class="fc-title">{T("Resultados fáciles de comprender", "Easy-to-understand results")}</div>
            <div class="fc-text">{T("Cada cálculo se explica en lenguaje simple: qué significa y qué hacer con él.",
            "Every calculation is explained in simple language: what it means and what to do about it.")}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 3. "Comienza aquí" — Onboarding Steps rediseñado (Cards Grid + Callout) -------------
    st.markdown(f"""
    <div style="margin:18px 0 0 0;">
    <p style="margin:0 0 2px 0;font-weight:700;color:#1E5631;font-size:1.35rem;">🚀 {T("¿Cómo empezar?", "How to get started?")}</p>
    <p style="margin:0 0 16px 0;color:#5C6B60;font-size:0.92rem;">{T("Sigue estos simples pasos para obtener tu diagnóstico personalizado.",
    "Follow these simple steps to get your personalized diagnosis.")}</p>
    </div>
    """, unsafe_allow_html=True)

    _ONBOARD_STEPS = [
        ("1", "📝", T("Ingresa tus datos", "Enter your data"), T("Completa tu información personal en el panel izquierdo.", "Fill in your personal information in the left-hand panel."),
         "#EAF4FE", "#8FC1F2", "#1565C0"),
        ("2", "🧩", T("Explora las secciones", "Explore the sections"), T("Navega libremente por las 17 áreas del centro de control.", "Freely browse the 17 areas of the control center."),
         "#F3EEFB", "#C6AEE8", "#6A3FA0"),
        ("3", "🔍", T("Revisa tus resultados", "Review your results"), T("Descubre tus indicadores explicados paso a paso.", "Discover your indicators explained step by step."),
         "#EAFAEE", "#9BD8AE", "#1E5631"),
        ("4", "📄", T("Descarga tu PDF", "Download your PDF"), T("Obtén tu reporte final completo y listo para guardar.", "Get your complete final report, ready to save."),
         "#FFF6E0", "#F4D27A", "#B8860B"),
    ]
    _cols_onboard = st.columns(4)
    for _col_ob, (_num, _ic, _tit, _txt, _fondo, _borde, _hex) in zip(_cols_onboard, _ONBOARD_STEPS):
        with _col_ob:
            st.markdown(f"""
            <div style="position:relative;background:{_fondo};border:1px solid {_borde};border-radius:20px;
            padding:22px 16px 16px 16px;height:170px;box-shadow:0 4px 14px rgba(0,0,0,0.05);">
            <div style="position:absolute;top:-10px;left:-10px;width:30px;height:30px;border-radius:50%;
            background:{_hex};color:#FFFFFF;font-weight:800;font-size:0.9rem;display:flex;align-items:center;
            justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.18);">{_num}</div>
            <div style="font-size:1.6rem;margin-bottom:8px;">{_ic}</div>
            <p style="margin:0 0 4px 0;font-weight:800;color:{_hex};font-size:0.92rem;">{_tit}</p>
            <p style="margin:0;color:#5C6B60;font-size:0.8rem;line-height:1.4;">{_txt}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;background:#F2F7F3;border:1px solid #D8E6DA;
    border-radius:999px;padding:12px 22px;margin:14px 0 4px 0;">
    <span style="font-size:1.1rem;">🔒</span>
    <span style="color:#3C4A3F;font-size:0.85rem;">{T("Solo tendrás que ingresar tus datos una vez durante esta sesión. "
    "Luego podrás moverte libremente entre todas las secciones cuando quieras.",
    "You'll only need to enter your data once during this session. Afterwards you can move freely "
    "between all sections whenever you like.")}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <p style="text-align:center;color:#5C6B60;font-size:0.9rem;font-style:italic;margin:0 0 18px 0;">
    "{T("Cada persona tiene necesidades nutricionales diferentes. Esta aplicación adapta los cálculos utilizando "
    "la información que ingreses, para brindarte resultados personalizados y fáciles de interpretar.",
    "Every person has different nutritional needs. This application adapts its calculations using the "
    "information you enter, to give you personalized, easy-to-interpret results.")}"</p>
    """, unsafe_allow_html=True)

    # --- Aviso médico: esta app es educativa y no reemplaza la consulta profesional ---
    st.markdown(f"""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:20px;
                padding:16px 24px;margin-bottom:18px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);">
    <b style="color:#FF9500;">⚕️ {T("Aviso importante:", "Important notice:")}</b> {T("esta aplicación es una herramienta educativa y orientativa. "
    "No reemplaza la consulta con un médico, nutricionista u otro profesional de la salud. "
    "Ante cualquier duda o resultado fuera de lo normal, acude siempre a un especialista.",
    "this application is an educational, informational tool. It does not replace consultation with a "
    "doctor, nutritionist or other health professional. If you have any doubts or abnormal results, "
    "always see a specialist.")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<p class="frase-motivadora">🍎 "{T("Comer bien no es una dieta, es un acto de amor hacia ti mismo", "Eating well is not a diet, it is an act of love toward yourself")}" 💚</p>', unsafe_allow_html=True)

    st.markdown("---")

# --- Acceso directo al Excel original, para que cualquiera pueda abrirlo/descargarlo libremente ---
_POSIBLES_NOMBRES_EXCEL = [
    "Proyecto sana alimentacion - GrupoN4 CIAM&SUNI.xlsx",
    "Proyecto_sana_alimentacion_-_GrupoN4_CIAM_SUNI.xlsx",
    "Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx",
    "Grupo_n_4_VER_2.xlsx", "Grupo_n_4_VER_2__1_.xlsx", "Grupo n°4 VER.2.xlsx", "Grupo_n_4_VER.2.xlsx",
]
@st.cache_data(show_spinner=False)
def _buscar_excel_original():
    """Busca el Excel original en disco. Cacheado: el resultado no cambia durante la sesión,
    así que evitamos repetir el escaneo de la carpeta (glob) en cada rerun."""
    for _nombre in _POSIBLES_NOMBRES_EXCEL:
        _candidata = Path(__file__).parent / _nombre
        if _candidata.exists():
            return _candidata
    _candidatos_xlsx = list(Path(__file__).parent.glob("*.xlsx"))
    _prioritarios = [c for c in _candidatos_xlsx if "grupon4" in c.name.lower() or "ciam" in c.name.lower()]
    _lista_final = _prioritarios if _prioritarios else _candidatos_xlsx
    if _lista_final:
        return sorted(_lista_final, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return None

_ruta_excel = _buscar_excel_original()

# =========================================================================================
# NAVEGACIÓN — 15 secciones en un panel lateral fijo (Sidebar Pill Navigation)
# Todas las secciones existen simultáneamente en la app; el sidebar decide cuál se pinta.
# =========================================================================================
OPCIONES_HOJAS = [
    "0.-DATOS",
    "1.-ANÁLISIS SANGUÍNEO",
    "1B.-ESTADO FISIOLÓGICO",
    "2.-IMC Y PERCENTIL",
    "3.-TMB",
    "4.-RCD",
    "5.-CONTROL DE PESO",
    "6.-MACRONUTRIENTES",
    "7.-PORCIONES",
    "8.-FATSECRET",
    "9.-DIETA",
    "12.-APORTE 2: CAFEÍNA",
    "13.-LÍNEA DE TIEMPO",
    "📄 MI REPORTE",
    "🎓 SOBRE NOSOTRAS",
]

# Ícono + etiqueta corta para cada píldora del sidebar (15 secciones, siempre visibles)
ETIQUETAS_NAV = {
    "0.-DATOS":                    ("👤", "Información Personal"),
    "1.-ANÁLISIS SANGUÍNEO":       ("🩸", "Análisis de Sangre"),
    "1B.-ESTADO FISIOLÓGICO":      ("❤️", "Estado Fisiológico"),
    "2.-IMC Y PERCENTIL":          ("⚖️", "Índice de Masa Corporal (IMC)"),
    "3.-TMB":                      ("🔥", "Tasa Metabólica Basal"),
    "4.-RCD":                      ("⚡", "Requerimiento Calórico Diario"),
    "5.-CONTROL DE PESO":          ("📈", "Control de Peso"),
    "6.-MACRONUTRIENTES":          ("🥗", "Distribución de Macronutrientes"),
    "7.-PORCIONES":                ("🍎", "Porciones Diarias Recomendadas"),
    "8.-FATSECRET":                ("🥬", "Base de Alimentos"),
    "9.-DIETA":                    ("📝", "Plan de Alimentación"),
    "12.-APORTE 2: CAFEÍNA":       ("☕", "Límite de Consumo de Cafeína"),
    "13.-LÍNEA DE TIEMPO":         ("📊", "Proyección del Peso"),
    "📄 MI REPORTE":               ("📄", "Reporte Nutricional"),
    "🎓 SOBRE NOSOTRAS":           ("👥", "Acerca de Nosotros"),
}

ETIQUETAS_NAV_EN = {
    "0.-DATOS":                    ("👤", "Personal Information"),
    "1.-ANÁLISIS SANGUÍNEO":       ("🩸", "Blood Test"),
    "1B.-ESTADO FISIOLÓGICO":      ("❤️", "Physiological State"),
    "2.-IMC Y PERCENTIL":          ("⚖️", "Body Mass Index (BMI)"),
    "3.-TMB":                      ("🔥", "Basal Metabolic Rate"),
    "4.-RCD":                      ("⚡", "Daily Caloric Requirement"),
    "5.-CONTROL DE PESO":          ("📈", "Weight Control"),
    "6.-MACRONUTRIENTES":          ("🥗", "Macronutrient Distribution"),
    "7.-PORCIONES":                ("🍎", "Recommended Daily Portions"),
    "8.-FATSECRET":                ("🥬", "Food Database"),
    "9.-DIETA":                    ("📝", "Meal Plan"),
    "12.-APORTE 2: CAFEÍNA":       ("☕", "Caffeine Intake Limit"),
    "13.-LÍNEA DE TIEMPO":         ("📊", "Weight Projection"),
    "📄 MI REPORTE":               ("📄", "Nutrition Report"),
    "🎓 SOBRE NOSOTRAS":           ("👥", "About Us"),
}


def _etiquetas_nav_activas():
    return ETIQUETAS_NAV_EN if st.session_state.get("idioma", "Español") == "English" else ETIQUETAS_NAV

_DEFAULTS_SESION = {
    "nombre_usuario": "", "genero": "Hombre", "peso": 75.0, "estatura": 168, "edad": 9,
    "actividad": "Ligero", "objetivo": "Bajar de peso",
    "ajuste_bajar_sel": "Equilibrado (-20%) ⭐ Recomendado",
    "ajuste_subir_sel": "Equilibrado (+15%) ⭐ Recomendado",
    "spo2": 0.0, "pulso": 0, "temp_corp": 34.0, "pas": 0, "pad": 0,
    "hemo": 0.0, "trigli": 0.0, "gluco": 0.0, "coles": 0.0, "hierro": 0.0,
    "embarazada": False, "trimestre_emb": "Primer trimestre", "vive_en_chiclayo": False,
}
for _clave, _valor_defecto in _DEFAULTS_SESION.items():
    if _clave not in st.session_state:
        st.session_state[_clave] = _valor_defecto

if "hoja_activa" not in st.session_state:
    st.session_state["hoja_activa"] = OPCIONES_HOJAS[0]

# =========================================================================================
# SIDEBAR — CENTRO DE CONTROL DEL USUARIO
# Insignia superior (con elementos decorativos a los lados) y, debajo, el formulario completo
# para llenar los datos del usuario (Bloques 1-4), siempre visible sin importar la hoja activa.
# =========================================================================================
st.sidebar.markdown("""
<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin:2px 0 12px 0;">
    <span style="font-size:1.3rem;opacity:0.55;">🍏</span>
    <div style="background:linear-gradient(135deg,#1E5631 0%,#2E7D32 55%,#4CAF50 100%);border-radius:999px;
                padding:8px 20px;box-shadow:0 6px 16px rgba(30,86,49,0.30);text-align:center;">
        <span style="color:#FFFFFF;font-weight:800;font-size:0.92rem;letter-spacing:0.02em;white-space:nowrap;">
            🥦 CIAM&amp;SUNI — Centro de Control</span>
    </div>
    <span style="font-size:1.3rem;opacity:0.55;">🥗</span>
</div>
""", unsafe_allow_html=True)

@st.fragment
def _panel_llenar_datos():
    """Panel del sidebar para ingresar/editar datos del usuario.
    Decorado con @st.fragment: al escribir o cambiar cualquier campo aquí dentro,
    Streamlit solo vuelve a ejecutar ESTA función (no todo el script de 7000+ líneas),
    por lo que los datos se guardan al instante y la app se siente mucho más rápida,
    sin necesidad de un botón para 'aplicar' los cambios.
    """
    def _badge_vital(valor, unidad, color_key, etiqueta):
        est = SEMAFORO_ESTILO[color_key]
        st.markdown(f"""<div style="margin-top:4px;display:inline-block;background:{est['fondo']};color:{est['hex']};
                    font-weight:800;font-size:0.78rem;padding:4px 12px;border-radius:999px;">
                    {est['emoji']} {etiqueta}{f' · {valor}{unidad}' if valor not in (0, 0.0) else ''}</div>""",
                    unsafe_allow_html=True)

    # ===== BLOQUE 0: Idioma / Language =====
    st.markdown('<div style="background:linear-gradient(120deg,#F3EEFB 0%,#E6DFFA 100%);border-radius:20px;'
                'padding:14px 22px;margin-bottom:14px;border:1px solid #8E6FCE33;">'
                '<h4 style="margin:0 0 8px 0;color:#5E35B1;">🌐 Idioma / Language</h4></div>',
                unsafe_allow_html=True)
    st.selectbox("Idioma / Language", ["Español", "English"], key="idioma",
                 label_visibility="collapsed")

    # ===== BLOQUE 1: Perfil Básico =====
    st.markdown('<div style="background:linear-gradient(120deg,#EAF3FF 0%,#D6EBFF 100%);border-radius:20px;'
                'padding:18px 22px;margin-bottom:14px;border:1px solid #007AFF22;">'
                f'<h4 style="margin:0 0 8px 0;color:#007AFF;">👤 {T("Bloque 1 · Tu Perfil Básico", "Block 1 · Your Basic Profile")}</h4>'
                f'<p style="margin:0;color:#3C6E9E;font-size:0.82rem;">{T("Con tu peso, estatura, edad y género "
                "calculamos tu metabolismo (TMB) y detectamos tu etapa de vida — la base de todo tu plan.",
                "With your weight, height, age and gender we calculate your metabolism (BMR) and detect your "
                "life stage — the foundation of your whole plan.")}</p></div>',
                unsafe_allow_html=True)
    b1c1, b1c2 = st.columns(2)
    with b1c1:
        nombre_usuario = st.text_input(T("¿Cómo te llamas?", "What's your name?"), value=st.session_state.get("nombre_usuario", ""),
                                        key="nombre_usuario", help=T("Tu plan se sentirá hecho a tu medida.", "Your plan will feel tailor-made for you."))
    with b1c2:
        genero = st.radio(T("Género:", "Gender:"), ["Hombre", "Mujer"], horizontal=True, key="genero",
                           format_func=lambda g: (T("♂ Hombre", "♂ Male") if g == "Hombre" else T("♀ Mujer", "♀ Female")))
    _nombre_saludo = nombre_display(nombre_usuario, genero)
    if nombre_usuario.strip():
        st.success(T(f"¡Paz y bien, {_nombre_saludo}! 🌟", f"Welcome, {_nombre_saludo}! 🌟"))
    else:
        st.caption(T("✍️ Escribe tu nombre.", "✍️ Enter your name."))

    peso_max_actual = PESO_MAX[genero]
    estatura_max_actual = ESTATURA_MAX[genero]
    edad_max_actual = EDAD_MAX[genero]
    # --- Ajusta valores previos que puedan exceder el nuevo tope al cambiar de género (evita error) ---
    if st.session_state.get("estatura", 0) and st.session_state["estatura"] > min(250, estatura_max_actual):
        st.session_state["estatura"] = min(250, estatura_max_actual)
    if st.session_state.get("edad", 0) and st.session_state["edad"] > min(120, edad_max_actual):
        st.session_state["edad"] = min(120, edad_max_actual)
    if st.session_state.get("peso", 0) and st.session_state["peso"] > min(300.0, peso_max_actual):
        st.session_state["peso"] = min(300.0, peso_max_actual)

    b1c3, b1c4, b1c5 = st.columns(3)
    with b1c3:
        peso = st.number_input(T("Peso (kg):", "Weight (kg):"), min_value=20.0, max_value=min(300.0, peso_max_actual),
                                value=min(75.0, peso_max_actual), step=0.1, key="peso",
                                help=T("Rango válido: 20 a 300 kg.", "Valid range: 20 to 300 kg."))
    with b1c4:
        estatura = st.number_input(T("Estatura (cm):", "Height (cm):"), min_value=50, max_value=min(250, estatura_max_actual),
                                    value=min(168, estatura_max_actual), step=1, key="estatura",
                                    help=T("Rango válido: 50 a 250 cm.", "Valid range: 50 to 250 cm."))
    with b1c5:
        edad = st.number_input(T("Edad (años):", "Age (years):"), min_value=1, max_value=min(120, edad_max_actual),
                                value=9, step=1, key="edad", help=T("Rango válido: 1 a 120 años.", "Valid range: 1 to 120 years."))
    etapa = etapa_desde_edad(edad)
    st.info(T(f"🔎 Etapa detectada automáticamente: **{etapa}**",
              f"🔎 Automatically detected life stage: **{_ETAPA_EN.get(etapa, etapa)}**"))

    embarazada = False
    trimestre = st.session_state.get("trimestre_emb", "Primer trimestre")
    if genero == "Mujer":
        embarazada = st.checkbox(T("🤰 ¿Estás embarazada?", "🤰 Are you pregnant?"), key="embarazada",
                                  help=T("Si activas esto, tu TMB se calculará con la fórmula de gestación "
                                       "en vez de Mifflin-St Jeor, y se reflejará en toda la app.",
                                       "If you enable this, your BMR will be calculated with the gestational "
                                       "formula instead of Mifflin-St Jeor, and it will be reflected across the app."))
        if embarazada:
            trimestre = st.selectbox(T("Trimestre de embarazo:", "Trimester of pregnancy:"),
                                      ["Primer trimestre", "Segundo trimestre", "Tercer trimestre"],
                                      key="trimestre_emb",
                                      format_func=lambda x: T(x, {"Primer trimestre": "First trimester",
                                                                   "Segundo trimestre": "Second trimester",
                                                                   "Tercer trimestre": "Third trimester"}[x]))
    vive_en_chiclayo = st.checkbox(T("🌤️ ¿Vives en Chiclayo?", "🌤️ Do you live in Chiclayo?"), key="vive_en_chiclayo",
                                    help=(T("Ajusta tu RCD según el clima cálido de la ciudad (−5%).",
                                            "Adjusts your DCR for the city's warm climate (−5%).") if not embarazada
                                    else T("Desactivado en Modo Embarazo: el gasto cardiovascular gestacional "
                                         "anula cualquier ahorro energético por clima (ACOG).",
                                         "Disabled in Pregnancy Mode: gestational cardiovascular expenditure "
                                         "overrides any climate-based energy saving (ACOG).")),
                                    disabled=embarazada)
    if embarazada:
        vive_en_chiclayo = False

    # ===== BLOQUE 2: Estilo de Vida y Objetivos =====
    st.markdown('<div style="background:linear-gradient(120deg,#EAFAEE 0%,#D2F5DC 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #1E563122;">'
                f'<h4 style="margin:0 0 8px 0;color:#1E5631;">🏃 {T("Bloque 2 · Estilo de Vida y Objetivos", "Block 2 · Lifestyle and Goals")}</h4>'
                f'<p style="margin:0;color:#3E7050;font-size:0.82rem;">{T("Tu nivel de actividad y tu meta definen "
                "cuántas calorías gastas al día (RCD) y a qué ritmo ajustamos tu alimentación.",
                "Your activity level and your goal determine how many calories you burn per day (DCR) and at "
                "what pace we adjust your nutrition.")}</p></div>',
                unsafe_allow_html=True)
    st.caption(T("🏃 Nivel de Actividad Física (selecciona la que mejor describa tu día a día):",
                 "🏃 Physical Activity Level (choose the one that best describes your day-to-day):"))
    actividad = st.radio(
        T("Actividad:", "Activity:"), ["Sedentaria", "Ligero", "Moderada", "Intensa"],
        index=1, key="actividad", label_visibility="collapsed",
        format_func=lambda a: T(_ACT_LABEL_ES[a], _ACT_LABEL_EN[a]),
    )
    _DESC_ACTIVIDAD = [
        ("Sedentaria", "🪑", "#8E8E93", "#F2F2F7",
         T("Sedentario o Poco Activo (Factor 1.2)", "Sedentary or Low Activity (Factor 1.2)"),
         T("Días en 'modo reposo'. Pasas la mayor parte del día sentado (oficina, estudio, manejo) y tu "
           "movilidad fuera de estar sentado es mínima o nula.",
           "Days in 'rest mode'. You spend most of the day seated (office, studying, driving) and your "
           "movement outside of sitting is minimal or none.")),
        ("Ligero", "🚶", "#34C759", "#EAFAEE",
         T("Ligeramente Activo (Factor 1.375 - 1.55)", "Lightly Active (Factor 1.375 - 1.55)"),
         T("Movimiento cotidiano acumulado. Trabajas sentado, pero caminas distancias razonables a diario, "
           "usas transporte público activo, haces compras a pie o labores del hogar de forma constante.",
           "Accumulated everyday movement. You work seated, but you walk reasonable distances daily, use "
           "active public transport, walk to run errands, or do household chores regularly.")),
        ("Moderada", "🏃", "#007AFF", "#EAF3FF",
         T("Moderadamente Activo (Factor 1.55 - 1.75)", "Moderately Active (Factor 1.55 - 1.75)"),
         T("Cuerpo en acción la mitad del día. Tienes un trabajo de pie o con desplazamiento constante "
           "(maestro, vendedor, salud) O tu trabajo es sentado pero realizas actividades físicas dinámicas "
           "de forma regular.",
           "Body in motion for half the day. You have a job that's standing or constantly moving "
           "(teacher, salesperson, healthcare) OR your job is seated but you do dynamic physical "
           "activities regularly.")),
        ("Intensa", "🔥", "#FF3B30", "#FFEDEC",
         T("Muy Activo / Intenso (Factor 1.8 - 2.1)", "Very Active / Intense (Factor 1.8 - 2.1)"),
         T("Alto esfuerzo físico diario. Entrenamientos intensos diarios o trabajos de alta exigencia física "
           "(construcción, agricultura, atletas).",
           "High daily physical effort. Intense daily training or physically demanding jobs "
           "(construction, farming, athletes).")),
    ]
    for _clave, _ic, _col, _fon, _tit, _desc in _DESC_ACTIVIDAD:
        _sel = (_clave == actividad)
        _estilo = (f"border:2.5px solid {_col};box-shadow:0 8px 20px {_col}40;transform:translateX(4px);"
                   if _sel else "border:1px solid rgba(0,0,0,0.06);")
        st.markdown(f"""
        <div style="background:{_fon};border-radius:16px;padding:12px 18px;margin-bottom:8px;{_estilo}
                    transition:all 0.2s ease;display:flex;gap:12px;align-items:flex-start;">
            <div style="font-size:1.4rem;">{_ic}</div>
            <div><b style="color:{_col};">{_tit}</b>{' ✓' if _sel else ''}<br>
            <span style="font-size:0.84rem;color:#3C3C43;">{_desc}</span></div>
        </div>
        """, unsafe_allow_html=True)

    if genero == "Mujer" and embarazada:
        # Modo Embarazo: el selector de objetivo (bajar/subir/mantener) y los ritmos tipo
        # fitness (±10/15/20/30%) se OCULTAN por completo. El aporte calórico es automático
        # y aditivo por trimestre e IMC previo (IOM / FAO-OMS / ACOG).
        objetivo = "Mantenerse"
        ajuste_txt = None
        st.info(T("🤰 En Modo Embarazo no se elige objetivo ni ritmo: tus calorías se calculan automáticamente "
                "sumando el bloque energético de tu trimestre a tu TMB gestacional. Nunca se resta energía.",
                "🤰 In Pregnancy Mode you don't choose a goal or pace: your calories are calculated automatically "
                "by adding your trimester's energy block to your gestational BMR. Energy is never subtracted."))
    else:
        objetivo = st.selectbox(T("🎯 ¿Cuál es tu objetivo principal?", "🎯 What's your main goal?"),
                                 ["Bajar de peso", "Subir de peso", "Mantenerse"],
                                 key="objetivo", format_func=lambda o: T(o, _OBJ_EN[o]))

        st.caption(T("⚙️ Ajuste del Ritmo (Velocidad del proceso):", "⚙️ Pace Adjustment (Process speed):"))
        _AJ_EN = {
            "Gradual (-10%)": "Gradual (-10%)", "Equilibrado (-20%) ⭐ Recomendado": "Balanced (-20%) ⭐ Recommended",
            "Intensivo (-30%)": "Intensive (-30%)", "Gradual (+10%)": "Gradual (+10%)",
            "Equilibrado (+15%) ⭐ Recomendado": "Balanced (+15%) ⭐ Recommended", "Acelerado (+20%)": "Accelerated (+20%)",
        }
        if objetivo == "Bajar de peso":
            ajuste_txt = st.selectbox(T("Ajuste del Ritmo:", "Pace Adjustment:"), label_visibility="collapsed",
                options=["Gradual (-10%)", "Equilibrado (-20%) ⭐ Recomendado", "Intensivo (-30%)"], index=1,
                key="ajuste_bajar_sel", format_func=lambda o: T(o, _AJ_EN[o]))
        elif objetivo == "Subir de peso":
            ajuste_txt = st.selectbox(T("Ajuste del Ritmo:", "Pace Adjustment:"), label_visibility="collapsed",
                options=["Gradual (+10%)", "Equilibrado (+15%) ⭐ Recomendado", "Acelerado (+20%)"], index=1,
                key="ajuste_subir_sel", format_func=lambda o: T(o, _AJ_EN[o]))
        else:
            ajuste_txt = None
            st.caption(T("Sin ajuste calórico: se mantiene tu RCD.", "No caloric adjustment: your DCR stays the same."))

        if objetivo in ("Bajar de peso", "Subir de peso"):
            _DESC_AJUSTE = {
                "Bajar de peso": [
                    ("Gradual (-10%)", "🌱", "#34C759", "#EAFAEE",
                     T("Ideal para quienes están cerca de su peso objetivo o prefieren cambios lentos y sostenibles.",
                       "Ideal for those close to their target weight or who prefer slow, sustainable changes.")),
                    ("Equilibrado (-20%) ⭐ Recomendado", "⚡", "#007AFF", "#EAF3FF",
                     T("La opción ideal para la mayoría. Permite una pérdida de peso constante manteniendo hábitos saludables.",
                       "The ideal option for most people. Allows steady weight loss while keeping healthy habits.")),
                    ("Intensivo (-30%)", "🚀", "#FF3B30", "#FFEDEC",
                     T("Produce cambios más rápidos. Se recomienda principalmente en personas con obesidad o por "
                       "periodos cortos y con seguimiento.",
                       "Produces faster changes. Mainly recommended for people with obesity or for short periods "
                       "with supervision.")),
                ],
                "Subir de peso": [
                    ("Gradual (+10%)", "🌱", "#34C759", "#EAFAEE",
                     T("Aumenta las calorías de forma moderada para favorecer una ganancia progresiva.",
                       "Increases calories moderately to favor progressive weight gain.")),
                    ("Equilibrado (+15%) ⭐ Recomendado", "⚡", "#007AFF", "#EAF3FF",
                     T("La opción ideal para la mayoría. Favorece una ganancia constante con menor acumulación de grasa.",
                       "The ideal option for most people. Favors steady gain with less fat accumulation.")),
                    ("Acelerado (+20%)", "🚀", "#FF3B30", "#FFEDEC",
                     T("Pensado para personas con metabolismo muy rápido o que necesitan aumentar peso rápidamente. "
                       "Requiere una alimentación bien planificada.",
                       "Designed for people with a very fast metabolism or who need to gain weight quickly. "
                       "Requires a well-planned diet.")),
                ],
            }[objetivo]
            for _tit_a, _ic_a, _col_a, _fon_a, _desc_a in _DESC_AJUSTE:
                _sel_a = (_tit_a == ajuste_txt)
                _tit_a_disp = T(_tit_a, _AJ_EN[_tit_a])
                _estilo_a = (f"border:2.5px solid {_col_a};box-shadow:0 8px 20px {_col_a}40;transform:translateX(4px);"
                             if _sel_a else "border:1px solid rgba(0,0,0,0.06);")
                st.markdown(f"""
                <div style="background:{_fon_a};border-radius:16px;padding:12px 18px;margin-bottom:8px;{_estilo_a}
                            transition:all 0.2s ease;display:flex;gap:12px;align-items:flex-start;">
                    <div style="font-size:1.4rem;">{_ic_a}</div>
                    <div><b style="color:{_col_a};">{_tit_a_disp}</b>{' ✓' if _sel_a else ''}<br>
                    <span style="font-size:0.84rem;color:#3C3C43;">{_desc_a}</span></div>
                </div>
                """, unsafe_allow_html=True)
            if (objetivo == "Bajar de peso" and ajuste_txt == "Intensivo (-30%)") or \
               (objetivo == "Subir de peso" and ajuste_txt == "Acelerado (+20%)"):
                st.warning(T("🟨 Este ritmo produce cambios más rápidos: úsalo solo bajo seguimiento o en casos específicos.",
                              "🟨 This pace produces faster changes: use it only under supervision or in specific cases."))

        st.caption(T("ℹ️ **¿Qué significa este ajuste?** Define qué tan rápido deseas alcanzar tu objetivo, adaptando "
                   "tus calorías diarias a partir de tu Requerimiento Calórico Diario (RCD). ⚡ El ritmo Equilibrado "
                   "suele ser la opción recomendada, ya que combina buenos resultados con una mejor adherencia a largo plazo.",
                   "ℹ️ **What does this adjustment mean?** It defines how fast you want to reach your goal, adapting "
                   "your daily calories from your Daily Caloric Requirement (DCR). ⚡ The Balanced pace is usually "
                   "the recommended option, since it combines good results with better long-term adherence."))

    # ===== BLOQUE 3: Monitoreo de Signos Vitales =====
    st.markdown('<div style="background:linear-gradient(120deg,#FFEBEE 0%,#FFD9DE 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #C0392B22;">'
                f'<h4 style="margin:0 0 8px 0;color:#C0392B;">💓 {T("Bloque 3 · Monitoreo de Signos Vitales", "Block 3 · Vital Signs Monitoring")}</h4>'
                f'<p style="margin:0;color:#8A5252;font-size:0.82rem;">{T("Estos indicadores muestran cómo está "
                "funcionando tu cuerpo en este momento, y ayudan a detectar señales de alerta a tiempo.",
                "These indicators show how your body is functioning right now, and help detect warning "
                "signs early.")}</p></div>',
                unsafe_allow_html=True)
    spo2 = st.number_input(T("Oxigenación SpO2 (%):", "Oxygen Saturation SpO2 (%):"), min_value=0.0, max_value=100.0, value=0.0, step=1.0,
                            key="spo2", help=T("Normal: 95% a 100%.", "Normal: 95% to 100%."))
    if spo2 > 0:
        _c = "verde" if spo2 >= 95 else ("rojo" if spo2 < 90 else "ambar")
        _badge_vital(spo2, "%", _c, T("Normal", "Normal") if _c == "verde" else (T("Bajo", "Low") if _c == "rojo" else T("Atención", "Alert")))

    pulso = st.number_input(T("Pulso (lpm):", "Pulse (bpm):"), min_value=0, max_value=220, value=0, step=1,
                             key="pulso", help=T("Ideal en reposo: 60 a 100 lpm.", "Ideal at rest: 60 to 100 bpm."))
    if pulso > 0:
        _c = "verde" if 60 <= pulso <= 100 else "ambar"
        _badge_vital(pulso, " lpm", _c, T("Normal", "Normal") if _c == "verde" else T("Atención", "Alert"))

    temp_corp = st.number_input(T("Temperatura (°C):", "Temperature (°C):"), min_value=34.0, max_value=42.0, value=34.0, step=0.1,
                                 key="temp_corp", help=T("Normal: 36.5°C a 37.5°C.", "Normal: 36.5°C to 37.5°C."))
    if temp_corp > 34.0:
        _c = "verde" if 36.5 <= temp_corp <= 37.5 else "ambar"
        _badge_vital(temp_corp, "°C", _c, T("Normal", "Normal") if _c == "verde" else T("Atención", "Alert"))

    st.markdown(f"**{T('Presión Arterial (mmHg):', 'Blood Pressure (mmHg):')}**")
    pas = st.number_input(T("Sistólica:", "Systolic:"), min_value=0, max_value=250, value=0, step=1, key="pas")
    pad = st.number_input(T("Diastólica:", "Diastolic:"), min_value=0, max_value=150, value=0, step=1, key="pad")
    if pas > 0 and pad > 0:
        if pas < 50 or pas > 300 or pad < 30 or pad > 200:
            st.markdown(f'<p style="color:#C0392B;font-weight:700;font-size:0.78rem;">'
                         f'⚠️ {T("Valor fuera de rango clínico. Por favor verifica tus datos", "Value outside clinical range. Please check your data")}</p>', unsafe_allow_html=True)
        else:
            _c = "verde" if (90 <= pas <= 119 and 60 <= pad <= 79) else "ambar"
            _badge_vital(f"{pas}/{pad}", "", _c, T("Normal", "Normal") if _c == "verde" else T("Atención", "Alert"))

    # ===== BLOQUE 4: Perfil Bioquímico (Análisis Sanguíneo) =====
    st.markdown('<div style="background:linear-gradient(120deg,#F3E5F5 0%,#E6CCEB 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #7B1FA222;">'
                f'<h4 style="margin:0 0 8px 0;color:#7B1FA2;">🩸 {T("Bloque 4 · Perfil Bioquímico (Análisis Sanguíneo)", "Block 4 · Biochemical Profile (Blood Test)")}</h4>'
                f'<p style="margin:0;color:#8E5FA3;font-size:0.82rem;">{T("Con tus valores de sangre identificamos "
                "riesgos como anemia, colesterol alto o glucosa elevada, para darte recomendaciones más precisas.",
                "With your blood values we identify risks such as anemia, high cholesterol or elevated glucose, "
                "to give you more precise recommendations.")}</p></div>',
                unsafe_allow_html=True)
    hemo = st.number_input(T("Hemoglobina (g/dL):", "Hemoglobin (g/dL):"), min_value=0.0, max_value=HEMO_MAX, value=0.0, step=0.1,
                            key="hemo", help=T("Normal: 12-17 g/dL, varía por género.", "Normal: 12-17 g/dL, varies by gender."))
    gluco = st.number_input(T("Glucosa (mg/dL):", "Glucose (mg/dL):"), min_value=0.0, max_value=GLUCO_MAX, value=0.0, step=1.0,
                             key="gluco", help=T("Normal en ayunas: 70-100 mg/dL.", "Normal fasting: 70-100 mg/dL."))
    coles = st.number_input(T("Colesterol (mg/dL):", "Cholesterol (mg/dL):"), min_value=0.0, max_value=COLES_MAX, value=0.0, step=1.0,
                             key="coles", help=T("Ideal: menor a 200 mg/dL.", "Ideal: less than 200 mg/dL."))
    trigli = st.number_input(T("Triglicéridos (mg/dL):", "Triglycerides (mg/dL):"), min_value=0.0, max_value=TRIGLI_MAX, value=0.0, step=1.0,
                              key="trigli", help=T("Ideal: menor a 150 mg/dL.", "Ideal: less than 150 mg/dL."))
    hierro = st.number_input(T("Hierro Sérico (µg/dL):", "Serum Iron (µg/dL):"), min_value=0.0, max_value=HIERRO_MAX, value=0.0, step=1.0,
                              key="hierro", help=T("Normal: 60-170 µg/dL.", "Normal: 60-170 µg/dL."))

with st.sidebar.expander("📝 Llenar / Editar Mis Datos", expanded=True):
    _panel_llenar_datos()

# ===== Reconstruye a nivel de script las variables que usan las demás hojas =====
# (el panel de arriba corre como @st.fragment, así que sus variables son locales a esa
# función; aquí las recuperamos desde st.session_state, que el fragment ya actualizó al vuelo)
nombre_usuario = st.session_state.get("nombre_usuario", "")
genero = st.session_state.get("genero", "Hombre")
peso = st.session_state.get("peso", 75.0)
estatura = st.session_state.get("estatura", 168)
edad = st.session_state.get("edad", 9)
etapa = etapa_desde_edad(edad)
embarazada = st.session_state.get("embarazada", False) if genero == "Mujer" else False
trimestre = st.session_state.get("trimestre_emb", "Primer trimestre")
vive_en_chiclayo = st.session_state.get("vive_en_chiclayo", False)
actividad = st.session_state.get("actividad", "Ligero")
objetivo = st.session_state.get("objetivo", "Bajar de peso")
if objetivo == "Bajar de peso":
    ajuste_txt = st.session_state.get("ajuste_bajar_sel", "Equilibrado (-20%) ⭐ Recomendado")
elif objetivo == "Subir de peso":
    ajuste_txt = st.session_state.get("ajuste_subir_sel", "Equilibrado (+15%) ⭐ Recomendado")
else:
    ajuste_txt = None
spo2 = st.session_state.get("spo2", 0.0)
pulso = st.session_state.get("pulso", 0)
temp_corp = st.session_state.get("temp_corp", 34.0)
pas = st.session_state.get("pas", 0)
pad = st.session_state.get("pad", 0)
hemo = st.session_state.get("hemo", 0.0)
gluco = st.session_state.get("gluco", 0.0)
coles = st.session_state.get("coles", 0.0)
trigli = st.session_state.get("trigli", 0.0)
hierro = st.session_state.get("hierro", 0.0)
_nombre_saludo = nombre_display(nombre_usuario, genero)

# ---- Sidebar: navegación tipo píldoras verticales coloridas, con las 15 secciones siempre visibles ----
st.sidebar.markdown(
    f'<div class="sidebar-nav-title">🧭 {T("Navegación · 15 secciones", "Navigation · 15 sections")}</div>',
    unsafe_allow_html=True,
)

NAV_COLORES = {
    "0.-DATOS":                    ("#007AFF", "#EAF3FF"),
    "1.-ANÁLISIS SANGUÍNEO":       ("#FF3B30", "#FFEDEC"),
    "1B.-ESTADO FISIOLÓGICO":      ("#FF2D55", "#FFEBF0"),
    "2.-IMC Y PERCENTIL":          ("#AF52DE", "#F6ECFC"),
    "3.-TMB":                      ("#FF9500", "#FFF3E5"),
    "4.-RCD":                      ("#34C759", "#EAFAEE"),
    "5.-CONTROL DE PESO":          ("#FF375F", "#FFEBF0"),
    "6.-MACRONUTRIENTES":          ("#FFCC00", "#FFFAE0"),
    "7.-PORCIONES":                ("#30B0C7", "#E6F7FA"),
    "8.-FATSECRET":                ("#00C7BE", "#E1FBF9"),
    "9.-DIETA":                    ("#FF6B35", "#FFEEE6"),
    "12.-APORTE 2: CAFEÍNA":       ("#5856D6", "#ECEBFB"),
    "13.-LÍNEA DE TIEMPO":         ("#5AC8FA", "#E9F8FF"),
    "📄 MI REPORTE":               ("#32ADE6", "#E7F6FD"),
    "🎓 SOBRE NOSOTRAS":           ("#FF2D55", "#FFEBF0"),
}

_nav_colores_css = "<style>\n"
for _i_nav, _hoja_nav_css in enumerate(OPCIONES_HOJAS, start=1):
    _borde_css, _fondo_css = NAV_COLORES.get(_hoja_nav_css, ("#1E5631", "#EAFAEE"))
    _nav_colores_css += f'''
section[data-testid="stSidebar"] div[data-testid="stButton"]:nth-of-type({_i_nav}) button[kind="secondary"] {{
    background:{_fondo_css} !important; color:{_borde_css} !important;
    border:1.5px solid {_borde_css}55 !important; font-weight:700 !important;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"]:nth-of-type({_i_nav}) button[kind="secondary"]:hover {{
    border-color:{_borde_css} !important; transform:translateX(2px);
}}
section[data-testid="stSidebar"] div[data-testid="stButton"]:nth-of-type({_i_nav}) button[kind="primary"] {{
    background:linear-gradient(135deg,{_borde_css} 0%,{_borde_css}CC 100%) !important; color:#FFFFFF !important;
    box-shadow:0 4px 14px {_borde_css}66 !important; border:1.5px solid {_borde_css} !important;
}}
'''
_nav_colores_css += "</style>"
st.sidebar.markdown(_nav_colores_css, unsafe_allow_html=True)

for _hoja_nav in OPCIONES_HOJAS:
    _icono_nav, _titulo_nav = _etiquetas_nav_activas()[_hoja_nav]
    _es_activo_nav = (_hoja_nav == st.session_state["hoja_activa"])
    if st.sidebar.button(
        f"{_icono_nav}  {_titulo_nav}",
        key=f"nav_{_hoja_nav}",
        use_container_width=True,
        type="primary" if _es_activo_nav else "secondary",
    ):
        st.session_state["hoja_activa"] = _hoja_nav
        st.rerun()

st.sidebar.markdown("---")

# =========================================================================================
# DATOS DEL USUARIO — ahora se ingresan en la hoja "0.-DATOS" (Mis Datos), no en el sidebar.
# Aquí solo leemos los valores actuales de session_state (con valores por defecto) para que
# los cálculos centrales funcionen sin importar en qué hoja esté el usuario.
# =========================================================================================
st.sidebar.caption("🔒 Tus datos son privados y no se guardan en ningún servidor.")

genero = st.session_state["genero"]
nombre_usuario = st.session_state["nombre_usuario"]
_nombre_saludo = nombre_display(nombre_usuario, genero)

peso_max_actual = PESO_MAX[genero]
peso = st.session_state["peso"]

estatura_max_actual = ESTATURA_MAX[genero]
estatura = st.session_state["estatura"]

edad_max_actual = EDAD_MAX[genero]
edad = st.session_state["edad"]

etapa = etapa_desde_edad(edad)

actividad = st.session_state["actividad"]
objetivo = st.session_state["objetivo"]

if genero == "Mujer" and embarazada:
    # Modo Embarazo: nunca se aplica déficit ni superávit tipo fitness; el ajuste calórico
    # es 100% automático por trimestre/IMC (ver bloque de TMB/RCD gestacional más abajo).
    ajuste_txt = "0"
    ajuste_bajar = 0.0
    ajuste_subir = 0.0
elif objetivo == "Bajar de peso":
    ajuste_txt = st.session_state["ajuste_bajar_sel"]
    _MAPA_BAJAR = {"Gradual (-10%)": 0.10, "Equilibrado (-20%) ⭐ Recomendado": 0.20, "Intensivo (-30%)": 0.30}
    ajuste_bajar = _MAPA_BAJAR.get(ajuste_txt, 0.20)
    ajuste_subir = 0.0
elif objetivo == "Subir de peso":
    ajuste_txt = st.session_state["ajuste_subir_sel"]
    _MAPA_SUBIR = {"Gradual (+10%)": 0.10, "Equilibrado (+15%) ⭐ Recomendado": 0.15, "Acelerado (+20%)": 0.20}
    ajuste_subir = _MAPA_SUBIR.get(ajuste_txt, 0.15)
    ajuste_bajar = 0.0
else:
    ajuste_txt = "0"
    ajuste_bajar = 0.0
    ajuste_subir = 0.0

# --- Signos vitales (Bloque 3, persistente) ---
spo2 = st.session_state["spo2"]
pulso = st.session_state["pulso"]
temp_corp = st.session_state["temp_corp"]
pas = st.session_state["pas"]
pad = st.session_state["pad"]

# --- Perfil bioquímico (Bloque 4, persistente) ---
hemo = st.session_state["hemo"]
trigli = st.session_state["trigli"]
gluco = st.session_state["gluco"]
coles = st.session_state["coles"]
hierro = st.session_state["hierro"]

# =========================================================================================
# CÁLCULOS CENTRALES (siguiendo el orden y las referencias EXACTAS de las hojas del Excel)
# =========================================================================================
estatura_m = estatura / 100.0
imc = round(peso / (estatura_m ** 2))  # =REDONDEAR(D30/F30) -> 0 decimales, igual que el Excel

_imc_previo_obesidad = (round(peso / ((estatura / 100.0) ** 2)) >= 30) if (estatura and peso) else False

if genero == "Mujer" and embarazada:
    # Modo Embarazo (ACOG / FAO-OMS / IOM): la TMB gestacional es el punto de partida y el
    # RCD se calcula SUMANDO bloques fijos de kcal por trimestre — nunca restando — con un
    # incremento moderado si hay obesidad previa (IMC ≥ 30) para evitar macrosomía/preeclampsia.
    _AJUSTE_TRIMESTRE_NORMAL = {"Primer trimestre": 0, "Segundo trimestre": 340, "Tercer trimestre": 450}
    _AJUSTE_TRIMESTRE_OBESIDAD = {"Primer trimestre": 0, "Segundo trimestre": 200, "Tercer trimestre": 250}
    tmb_base_gestacion = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
    tmb = tmb_base_gestacion
    tabla_trimestre = _AJUSTE_TRIMESTRE_OBESIDAD if _imc_previo_obesidad else _AJUSTE_TRIMESTRE_NORMAL
    ajuste_gestacion = tabla_trimestre.get(trimestre, 0)
    tmb_fuente = "embarazo_" + trimestre.split(" ")[0].lower()

    factor = 1.0  # en Modo Embarazo no se aplica factor de actividad tipo fitness sobre el RCD
    rcd_base = tmb
    rcd = rcd_base  # el clima de Chiclayo NUNCA reduce el RCD gestacional (gasto cardíaco/térmico ya elevado)
    ajuste_clima_aplicado = False

    ajuste_aplicado = 0.0
    rcd_final = tmb + ajuste_gestacion  # RCD = TMB gestacional + bloque fijo del trimestre (IOM/FAO-OMS)
    _ico_recortada_por_tmb = False
else:
    tmb_base_gestacion = None
    ajuste_gestacion = 0
    if genero == "Hombre":
        tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5
    else:
        tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
    tmb_fuente = "mifflin_st_jeor"

    factor = FACTOR_ACTIVIDAD[actividad][genero]
    rcd_base = tmb * factor  # RCD base = TMB x Factor de actividad
    rcd = rcd_base * 0.95 if vive_en_chiclayo else rcd_base  # RCD (con ajuste de clima si vive en Chiclayo)
    ajuste_clima_aplicado = vive_en_chiclayo

    # Hoja 5: ajuste según objetivo (Control de Peso) — respetando el límite fisiológico de no bajar de la TMB
    if objetivo == "Bajar de peso":
        ajuste_aplicado = ajuste_bajar
        rcd_final = max(rcd * (1 - ajuste_aplicado), tmb)
    elif objetivo == "Subir de peso":
        ajuste_aplicado = ajuste_subir
        rcd_final = rcd * (1 + ajuste_aplicado)
    else:
        ajuste_aplicado = 0.0
        rcd_final = rcd

    _ico_recortada_por_tmb = (objetivo == "Bajar de peso") and (rcd * (1 - ajuste_bajar) < tmb)

# Plazo estimado, según los lapsos máximos recomendados (Guía de Ritmos y Lapsos Seguros)
if objetivo == "Bajar de peso":
    if ajuste_bajar == 0.10:
        plazo = "Corto plazo (hasta 12-16 semanas)"
    elif ajuste_bajar == 0.20:
        plazo = "Plazo medio (hasta 12-16 semanas, con pausas de mantenimiento)"
    elif ajuste_bajar == 0.30:
        plazo = "Plazo agresivo (máximo 4-6 semanas seguidas)"
    else:
        plazo = "—"
elif objetivo == "Subir de peso":
    if ajuste_subir == 0.10:
        plazo = "Limpio / magro (16-24 semanas)"
    elif ajuste_subir == 0.15:
        plazo = "Plazo medio (16-24 semanas)"
    elif ajuste_subir == 0.20:
        plazo = "Plazo exigente (16-24 semanas)"
    else:
        plazo = "—"
else:
    plazo = "Indefinido / con pausas (variación ± 1 kg)"

# Estimación de ritmo y semanas necesarias (Paso 2 de la Guía de Operación)
_diferencia_diaria = abs(rcd - rcd_final)
_cambio_semanal_kg = (_diferencia_diaria * 7) / 7700
_ritmo_pct_semanal = (_cambio_semanal_kg / peso) * 100 if peso > 0 else 0

# Hoja 6: Macronutrientes
if genero == "Mujer" and embarazada:
    # Modo Embarazo (IOM — DRIs para Macronutrientes): proteína mínima 1.1 g/kg de peso actual,
    # carbohidratos SIEMPRE entre 45%-55% del RCD (nunca low-carb/keto, por riesgo de cetosis
    # neurotóxica fetal), y grasas completando el resto priorizando insaturadas (Omega-3 DHA).
    gr_prot = max(peso * 1.1, (rcd_final * 0.20) / 4)
    cal_prot = gr_prot * 4
    cal_carb = rcd_final * 0.50  # punto medio del rango seguro 45%-55%
    gr_carb = cal_carb / 4
    cal_gras = max(rcd_final - cal_prot - cal_carb, 0)
    gr_gras = cal_gras / 9
else:
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

# RCD ya incluye el ajuste de clima de Chiclayo si corresponde (ver cálculo de `rcd` arriba)

# Categoría IMC del usuario (para reutilizar en Hoja 2 y en el Reporte)
if etapa in ["Niñez", "Adolescencia"]:
    _percentil_usuario, _categoria_imc_usuario = clasif_percentil(imc, edad, genero)
else:
    _percentil_usuario, _categoria_imc_usuario = None, clasif_imc_adulto(imc)

# =========================================================================================
# CONTENIDO PRINCIPAL — la navegación vive en el sidebar (pills verticales); aquí solo se
# pinta la sección actualmente seleccionada.
# =========================================================================================
hoja_activa = st.session_state["hoja_activa"]
_icono_actual, _titulo_actual = _etiquetas_nav_activas()[hoja_activa]
st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
    <span style="font-size:1.4rem;">{_icono_actual}</span>
    <span style="font-size:0.82rem;color:#8A94A6;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;">
        Sección {OPCIONES_HOJAS.index(hoja_activa)+1} de {len(OPCIONES_HOJAS)} &nbsp;•&nbsp; {_titulo_actual}</span>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------------------------------------------------------------------
if hoja_activa == "0.-DATOS":
    # --- Bloque destacado: por qué descargar el Excel original (va antes del formulario) ---
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E5631 0%,#2E7D32 60%,#4CAF50 100%);border-radius:26px;
                padding:28px 30px;color:white;margin-bottom:18px;
                box-shadow:0 14px 34px rgba(30,86,49,0.28);">
        <div style="font-size:0.8rem;letter-spacing:0.03em;text-transform:uppercase;font-weight:700;opacity:0.9;">
            📂 {T("Antes de empezar", "Before you start")}</div>
        <div style="font-size:1.5rem;font-weight:800;margin:6px 0 10px 0;letter-spacing:-0.01em;">
            {T("¿Por qué deberías descargar el Excel original?", "Why should you download the original Excel file?")}</div>
        <div style="font-size:0.98rem;line-height:1.55;opacity:0.97;max-width:760px;">
            {T("Esta app es una réplica bonita y fácil de usar, pero el Excel es la herramienta completa: es tuya, "
            "para siempre, y puedes llevarla contigo a donde quieras.",
            "This app is a nice, easy-to-use replica, but the Excel file is the complete tool: it's yours, "
            "forever, and you can take it with you anywhere.")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    ra1, ra2, ra3, ra4 = st.columns(4)
    _razones_excel = [
        ("🎨", T("Personalízalo a tu gusto", "Customize it to your taste"), T("Cambia colores, agrega tus propias comidas o ajusta las "
         "fórmulas exactamente como tú quieras — es 100% tuyo para editar.",
         "Change colors, add your own foods, or adjust the formulas exactly as you like — it's 100% yours to edit.")),
        ("📴", T("Úsalo sin internet", "Use it without internet"), T("No necesitas conexión ni esta página abierta: el Excel funciona "
         "perfecto en tu computadora aunque no tengas WiFi ni datos.",
         "You don't need a connection or this page open: the Excel file works perfectly on your computer "
         "even without WiFi or data.")),
        ("🧮", T("Fórmulas a la mano", "Formulas at hand"), T("Todas las fórmulas están visibles y editables en cada celda, así "
         "puedes revisarlas, aprenderlas o adaptarlas a otro caso.",
         "All formulas are visible and editable in every cell, so you can review them, learn them, or "
         "adapt them to another case.")),
        ("📋", T("Con las indicaciones incluidas", "With instructions included"), T("Cada hoja trae sus propias notas e instrucciones, para "
         "que sepas exactamente cómo usarla paso a paso.",
         "Each sheet comes with its own notes and instructions, so you know exactly how to use it step by step.")),
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
                T("📥 Descargar el Excel original ahora", "📥 Download the original Excel file now"),
                data=_f.read(),
                file_name=_ruta_excel.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
    else:
        st.info(T("Para habilitar este botón, coloca el archivo del Excel (por ejemplo "
                "`Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx`) en la misma carpeta que este script "
                "`app.py` antes de ejecutarlo.",
                "To enable this button, place the Excel file (e.g. "
                "`Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx`) in the same folder as this "
                "`app.py` script before running it."))

    st.divider()

    col_escudo_intro, col_intro_hero = st.columns([1, 3.2])
    with col_escudo_intro:
        _escudo_b64_intro = _img_b64(_ESCUDO) if _ESCUDO.exists() else None
        _escudo_intro_tag = (f'<img src="data:image/png;base64,{_escudo_b64_intro}" '
                              f'style="max-width:80%;max-height:170px;object-fit:contain;" />') if _escudo_b64_intro else ""
        st.markdown(f"""
        <div style="background:linear-gradient(120deg,#FFFFFF 0%,#F4F9F4 100%);border-radius:26px;
        padding:18px;box-shadow:0 6px 20px rgba(30,86,49,0.10);border:1.5px solid rgba(30,86,49,0.14);
        height:100%;min-height:210px;display:flex;align-items:center;justify-content:center;">
        {_escudo_intro_tag}
        </div>
        """, unsafe_allow_html=True)
    with col_intro_hero:
        st.markdown(f"""
        <div style="position:relative;overflow:hidden;background:linear-gradient(120deg,#007AFF 0%,#5AC8FA 45%,#34C759 100%);
                    border-radius:28px;padding:30px 34px;color:#FFFFFF;height:100%;min-height:210px;box-sizing:border-box;
                    box-shadow:0 18px 40px rgba(0,122,255,0.28);">
            <div style="position:absolute;right:20px;top:50%;transform:translateY(-50%);font-size:5.5rem;opacity:0.18;">📝✨</div>
            <div style="font-size:0.8rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.92;">{T("Paso 1 de tu plan", "Step 1 of your plan")}</div>
            <h1 style="margin:6px 0 6px 0;font-weight:900;letter-spacing:-0.02em;">📝 {T("¡Introduce tus datos!", "Enter your data!")}</h1>
            <p style="margin:0;font-size:1rem;opacity:0.96;max-width:600px;">{T('El punto de partida: llena el formulario "📝 Llenar / Editar Mis Datos" en el panel lateral izquierdo (sidebar) — se mantiene visible en todas las hojas. Aquí abajo verás un resumen de lo que ya registraste. 🌈',
            'The starting point: fill in the "📝 Fill In / Edit My Data" form in the left sidebar panel — it stays visible on every sheet. Below you\'ll see a summary of what you\'ve already entered. 🌈')}</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown(f"""
    <div style="background:#EAF3FF;border-left:5px solid #007AFF;border-radius:16px;padding:12px 20px;">
    🔒 <b style="color:#007AFF;">{T("Tus datos son privados:", "Your data is private:")}</b> {T("solo se usan mientras tienes esta página abierta y no se guardan en ningún servidor.",
    "it is only used while you have this page open and is never stored on any server.")}
    </div>
    """, unsafe_allow_html=True)


    st.divider()
    st.markdown(f"#### 📋 {T('Resumen de tus datos ingresados', 'Summary of your entered data')}")

    col_datos, col_sticker = st.columns([2, 1])
    with col_datos:
        _sd = lambda v: T("Sin dato", "No data") if v is None else v
        _tablas_resumen = [
            (0, T("👤 Bloque 1 · Perfil Básico", "👤 Block 1 · Basic Profile"), [
                (T("Nombre", "Name"), _nombre_saludo), (T("Género", "Gender"), T(genero, "Male" if genero == "Hombre" else "Female")), (T("Peso", "Weight"), f"{peso:.2f} kg"),
                (T("Estatura", "Height"), f"{estatura} cm ({estatura_m:.2f} m)"), (T("Edad", "Age"), T(f"{edad} años", f"{edad} years")),
                (T("Etapa detectada", "Detected life stage"), T(etapa, _ETAPA_EN.get(etapa, etapa))),
            ]),
            (4, T("🏃 Bloque 2 · Estilo de Vida y Objetivos", "🏃 Block 2 · Lifestyle and Goals"), [
                (T("Actividad física", "Physical activity"), T(_ACT_LABEL_ES.get(actividad, actividad), _ACT_LABEL_EN.get(actividad, actividad))),
                (T("Objetivo", "Goal"), T(objetivo, _OBJ_EN.get(objetivo, objetivo))),
                (T("Ajuste (bajar)", "Adjustment (lose)"), f"{ajuste_bajar*100:.0f}%"), (T("Ajuste (subir)", "Adjustment (gain)"), f"{ajuste_subir*100:.0f}%"),
            ]),
            (1, T("💓 Bloque 3 · Signos Vitales", "💓 Block 3 · Vital Signs"), [
                (T("SpO2", "SpO2"), f"{spo2:.2f}%" if spo2 > 0 else T("Sin dato", "No data")),
                (T("Pulso", "Pulse"), f"{pulso} lpm" if pulso > 0 else T("Sin dato", "No data")),
                (T("Temperatura", "Temperature"), f"{temp_corp:.2f}°C" if temp_corp > 34.0 else T("Sin dato", "No data")),
                (T("Presión arterial", "Blood pressure"), f"{pas}/{pad} mmHg" if pas > 0 and pad > 0 else T("Sin dato", "No data")),
            ]),
            (1, T("🩸 Bloque 4 · Perfil Bioquímico", "🩸 Block 4 · Biochemical Profile"), [
                (T("Hemoglobina", "Hemoglobin"), f"{hemo:.2f} g/dL" if hemo > 0 else T("Sin dato", "No data")),
                (T("Glucosa", "Glucose"), f"{gluco:.2f} mg/dL" if gluco > 0 else T("Sin dato", "No data")),
                (T("Colesterol", "Cholesterol"), f"{coles:.2f} mg/dL" if coles > 0 else T("Sin dato", "No data")),
                (T("Triglicéridos", "Triglycerides"), f"{trigli:.2f} mg/dL" if trigli > 0 else T("Sin dato", "No data")),
                (T("Hierro", "Iron"), f"{hierro:.2f} µg/dL" if hierro > 0 else T("Sin dato", "No data")),
            ]),
        ]
        for _idx_col, _titulo_tabla, _filas_tabla in _tablas_resumen:
            caja_titulo(_titulo_tabla, _idx_col)
            tabla_bonita(pd.DataFrame({T("Variable", "Variable"): [f[0] for f in _filas_tabla],
                                        T("Valor", "Value"): [f[1] for f in _filas_tabla]}), _idx_col)
    with col_sticker:
        st.caption(T(f"¡Bienvenid@, {_nombre_saludo}! 👋", f"Welcome, {_nombre_saludo}! 👋"))

    st.divider()
    caja_util(T(f"¡Paz y bien, {_nombre_saludo}! Aquí registras tus datos básicos una sola vez, y toda la app se ajusta "
              "automáticamente a ti: desde tus calorías diarias hasta tu plan de comidas. La etapa de vida se "
              "detecta sola apenas escribes tu edad. ¡Es el punto de partida de todo tu plan personalizado! 🌟",
              f"Welcome, {_nombre_saludo}! Here you enter your basic data just once, and the whole app adjusts "
              "automatically to you: from your daily calories to your meal plan. Your life stage is detected "
              "automatically as soon as you enter your age. It's the starting point of your whole personalized plan! 🌟"),
              emoji="📝", color="#E3F2FD", borde="#2196F3")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "1.-ANÁLISIS SANGUÍNEO":
    hoja_header(1, T("No solo mostramos tus números: te explicamos qué significan, por qué ocurren y qué podrías hacer.",
                     "We don't just show you your numbers: we explain what they mean, why they happen, and what you could do."))

    _PARAM_EN = {"Hemoglobina": "Hemoglobin", "Triglicéridos": "Triglycerides", "Glucosa": "Glucose",
                 "Colesterol": "Cholesterol", "Hierro": "Iron"}
    def _pn(p):
        return T(p, _PARAM_EN.get(p, p))

    _cat_hemo = clasif_hemoglobina(hemo, etapa, genero)
    _cat_trigli = clasif_trigliceridos(trigli)
    _cat_gluco = clasif_glucosa(gluco)
    _cat_coles = clasif_colesterol(coles)
    _cat_hierro = clasif_hierro(hierro, etapa, genero)

    st.markdown(f"#### 🚦 {T('Semáforo Clínico — protocolo de triaje digital', 'Clinical Traffic Light — digital triage protocol')}")
    st.caption(f"{T('No solo diagnostica: te sugiere una ruta de mejora inmediata', 'Not just a diagnosis: it suggests an immediate path to improvement')}, "
               f"{_nombre_saludo}. 🟢 {T('Normal', 'Normal')} · 🟡 {T('Alerta', 'Alert')} · 🔴 {T('Crítico', 'Critical')}")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: tarjeta_semaforo("Hemoglobina", f"{hemo} g/dL", _cat_hemo, valor_num=hemo, etapa=etapa, genero=genero)
    with sc2: tarjeta_semaforo("Triglicéridos", f"{trigli} mg/dL", _cat_trigli, valor_num=trigli)
    with sc3: tarjeta_semaforo("Glucosa", f"{gluco} mg/dL", _cat_gluco, valor_num=gluco)
    with sc4: tarjeta_semaforo("Colesterol", f"{coles} mg/dL", _cat_coles, valor_num=coles)
    with sc5: tarjeta_semaforo("Hierro", f"{hierro} µg/dL", _cat_hierro, valor_num=hierro, etapa=etapa, genero=genero)

    st.divider()

    # ===== 1. Tarjetas informativas por parámetro: qué mide, qué significa, recomendaciones, dato curioso =====
    _INFO_PARAM = {
        "Hemoglobina": {
            "icono": "🩸", "unidad": " g/dL", "valor": hemo, "categoria": _cat_hemo,
            "que_mide": T("Proteína de los glóbulos rojos que transporta el oxígeno desde los pulmones hacia todo el cuerpo.",
                          "The protein in red blood cells that carries oxygen from the lungs to the rest of the body."),
            "recomendaciones": [("🥩", T("Alimentos ricos en hierro", "Iron-rich foods")),
                                 ("🍊", T("Vitamina C (mejora la absorción)", "Vitamin C (improves absorption)")),
                                 ("🩺", T("Evaluación médica si hay síntomas", "Medical evaluation if symptoms occur"))],
            "riesgo": [T("🍖 Baja ingesta de hierro", "🍖 Low iron intake"), T("🤰 Embarazo", "🤰 Pregnancy"),
                       T("🩸 Sangrados", "🩸 Bleeding"), T("🫘 Déficit nutricional", "🫘 Nutritional deficiency")],
            "curioso": T("La hemoglobina puede disminuir durante el embarazo debido al aumento del volumen sanguíneo.",
                         "Hemoglobin can decrease during pregnancy due to the increase in blood volume."),
        },
        "Triglicéridos": {
            "icono": "🫒", "unidad": " mg/dL", "valor": trigli, "categoria": _cat_trigli,
            "que_mide": T("Tipo de grasa en la sangre que el cuerpo usa como reserva de energía.",
                          "A type of fat in the blood that the body uses as an energy reserve."),
            "recomendaciones": [("🥑", T("Priorizar grasas saludables", "Prioritize healthy fats")),
                                 ("🚶", T("Actividad física regular", "Regular physical activity")),
                                 ("🍬", T("Reducir azúcares simples", "Reduce simple sugars"))],
            "riesgo": [T("🍩 Exceso de azúcares", "🍩 Excess sugar"), T("🍺 Consumo de alcohol", "🍺 Alcohol consumption"),
                       T("⚖️ Sobrepeso", "⚖️ Overweight"), T("🧬 Factores genéticos", "🧬 Genetic factors")],
            "curioso": T("Los triglicéridos suben temporalmente después de comer; por eso muchas pruebas piden ayuno.",
                         "Triglycerides rise temporarily after eating; that's why many tests require fasting."),
        },
        "Glucosa": {
            "icono": "🍬", "unidad": " mg/dL", "valor": gluco, "categoria": _cat_gluco,
            "que_mide": T("Nivel de azúcar disponible en la sangre, la principal fuente de energía del cuerpo.",
                          "The level of sugar available in the blood, the body's main source of energy."),
            "recomendaciones": [("🥗", T("Más fibra, menos azúcar simple", "More fiber, less simple sugar")),
                                 ("🚶", T("Actividad física", "Physical activity")),
                                 ("⏰", T("Horarios de comida regulares", "Regular meal times"))],
            "riesgo": [T("🍭 Dieta alta en azúcares", "🍭 High-sugar diet"), T("⚖️ Sobrepeso", "⚖️ Overweight"),
                       T("🧬 Antecedentes familiares", "🧬 Family history"), T("😴 Mal descanso", "😴 Poor sleep")],
            "curioso": T("La glucosa aumenta naturalmente después de comer; por eso muchas pruebas se hacen en ayunas.",
                         "Glucose naturally rises after eating; that's why many tests are done fasting."),
        },
        "Colesterol": {
            "icono": "🫀", "unidad": " mg/dL", "valor": coles, "categoria": _cat_coles,
            "que_mide": T("Grasa esencial para producir hormonas y formar membranas celulares, en exceso puede obstruir arterias.",
                          "A fat essential for producing hormones and forming cell membranes; in excess it can clog arteries."),
            "recomendaciones": [("🥑", T("Priorizar grasas saludables", "Prioritize healthy fats")),
                                 ("🚶", T("Actividad física", "Physical activity")),
                                 ("🥗", T("Más fibra", "More fiber")), ("🚭", T("Evitar tabaco", "Avoid tobacco"))],
            "riesgo": [T("🍟 Grasas saturadas/trans", "🍟 Saturated/trans fats"), T("🚬 Tabaco", "🚬 Tobacco"),
                       T("🧬 Factores genéticos", "🧬 Genetic factors"), T("⚖️ Sobrepeso", "⚖️ Overweight")],
            "curioso": T("El colesterol no siempre es perjudicial: el organismo lo necesita para producir hormonas.",
                         "Cholesterol isn't always harmful: the body needs it to produce hormones."),
        },
        "Hierro": {
            "icono": "⚙️", "unidad": " µg/dL", "valor": hierro, "categoria": _cat_hierro,
            "que_mide": T("Mineral esencial para fabricar hemoglobina y transportar oxígeno en el cuerpo.",
                          "An essential mineral for making hemoglobin and transporting oxygen in the body."),
            "recomendaciones": [("🥩", T("Carnes rojas y legumbres", "Red meat and legumes")),
                                 ("🍊", T("Vitamina C junto a las comidas", "Vitamin C with meals")),
                                 ("☕", T("Evitar café/té con las comidas", "Avoid coffee/tea with meals"))],
            "riesgo": [T("🍖 Baja ingesta de hierro", "🍖 Low iron intake"), T("🩸 Pérdidas de sangre", "🩸 Blood loss"),
                       T("🤰 Embarazo", "🤰 Pregnancy"), T("🫘 Mala absorción intestinal", "🫘 Poor intestinal absorption")],
            "curioso": T("El té y el café pueden reducir la absorción de hierro si se toman junto a las comidas.",
                         "Tea and coffee can reduce iron absorption if consumed with meals."),
        },
    }
    st.markdown(f"#### 🔎 {T('¿Qué significa cada resultado?', 'What does each result mean?')}")
    for _param, _info in _INFO_PARAM.items():
        _r = evaluar_estado_clinico(_param, _info["categoria"])
        with st.expander(f"{_info['icono']} {_pn(_param)} — {_info['valor']}{_info['unidad']} · {_r['emoji']} {_info['categoria']}"):
            st.markdown(f"**🧠 {T('¿Qué mide?', 'What does it measure?')}** {_info['que_mide']}")
            st.markdown(f"**📋 {T('¿Qué significa tu resultado?', 'What does your result mean?')}** {_r['mensajePersonalizado']}")
            _reco_html = " &nbsp; ".join(f"{ic} {tx}" for ic, tx in _info["recomendaciones"])
            st.markdown(f"**✅ {T('Recomendaciones generales (educativas, no médicas):', 'General recommendations (educational, not medical):')}** {_reco_html}")
            if _r["colorSemaforo"] in ("ambar", "rojo"):
                st.markdown(f"**⚠️ {T('Posibles factores relacionados', 'Possible related factors')}** "
                            f"({T('no constituye diagnóstico', 'not a diagnosis')}): "
                            + " &nbsp; ".join(_info["riesgo"]))
            st.markdown(f"**💡 {T('¿Sabías qué?', 'Did you know?')}** {_info['curioso']}")

    st.divider()

    # ===== 2. Interpretación Clínica Inteligente (reemplaza el panel de flujo anterior) =====
    st.markdown(f"#### 🧠 {T('Interpretación Clínica Inteligente', 'Smart Clinical Interpretation')}")
    _todos = [("Hemoglobina", _cat_hemo), ("Triglicéridos", _cat_trigli), ("Glucosa", _cat_gluco),
              ("Colesterol", _cat_coles), ("Hierro", _cat_hierro)]
    _con_dato = [(p, c) for p, c in _todos if c != "Introducir datos"]
    _verdes = [p for p, c in _con_dato if CATEGORIA_SEMAFORO.get(c, "gris") == "verde"]
    _no_verdes = [(p, c) for p, c in _con_dato if CATEGORIA_SEMAFORO.get(c, "gris") in ("ambar", "rojo")]
    _pct_salud = round((len(_verdes) / len(_con_dato)) * 100) if _con_dato else 0

    if _con_dato:
        icol1, icol2 = st.columns(2)
        with icol1:
            st.success(f"🟢 " + T(f"{len(_verdes)} parámetro(s) normal(es)", f"{len(_verdes)} normal parameter(s)"))
            if _no_verdes:
                st.warning(f"🟡 " + T(f"{len(_no_verdes)} parámetro(s) requiere(n) seguimiento", f"{len(_no_verdes)} parameter(s) need follow-up"))
            st.markdown(f"**✔ {T('Fortalezas', 'Strengths')}**")
            st.markdown("\n".join(f"- ✔ " + T(f"{_pn(p)} adecuada", f"Adequate {_pn(p)}") for p in _verdes)
                        or f"- {T('Aún sin fortalezas identificadas.', 'No strengths identified yet.')}")
        with icol2:
            st.markdown(f"**⚠ {T('Aspectos a mejorar', 'Areas to improve')}**")
            if _no_verdes:
                for p, c in _no_verdes:
                    _reco_corta = _INFO_PARAM[p]["recomendaciones"][0]
                    st.markdown(f"- ⚠ {_pn(p)} ({c}) — {T('sugerencia', 'suggestion')}: {_reco_corta[0]} {_reco_corta[1]}")
            else:
                st.markdown(f"- {T('Sin aspectos pendientes por ahora. 🎉', 'No pending issues for now. 🎉')}")
        st.markdown(f"**{T('Nivel general · Salud metabólica', 'Overall level · Metabolic health')}: {_pct_salud}%**")
        st.progress(_pct_salud / 100)
    else:
        st.info(T("Ingresa al menos un valor en la hoja 'Mis Datos' (Bloque 4) para ver tu interpretación clínica.",
                  "Enter at least one value in the 'My Data' sheet (Block 4) to see your clinical interpretation."))

    # ===== Mini motor de reglas (no es IA real, solo asociaciones simples) =====
    _insights = []
    if _cat_hemo in ("Anemia leve", "Anemia moderada", "Anemia grave") and _cat_hierro == "Bajo":
        _insights.append(T("Existe una posible asociación entre tu hemoglobina baja y tu hierro bajo: podría sugerir "
                          "una deficiencia de hierro. Se recomienda acudir al profesional de salud para una valoración clínica.",
                          "There may be a link between your low hemoglobin and low iron: this could suggest an iron "
                          "deficiency. It's recommended to see a health professional for a clinical assessment."))
    if _cat_gluco in ("Prediabetes", "Diabetes") and _cat_coles in ("Límite alto", "Alto"):
        _insights.append(T("Tu glucosa y tu colesterol elevados en conjunto suelen asociarse a un mayor riesgo metabólico. "
                          "Se recomienda una valoración médica integral.",
                          "Your elevated glucose and cholesterol together are usually associated with a higher metabolic "
                          "risk. A comprehensive medical assessment is recommended."))
    if _cat_trigli in ("Alto", "Muy alto") and _cat_coles in ("Límite alto", "Alto"):
        _insights.append(T("Triglicéridos y colesterol elevados juntos pueden asociarse a mayor riesgo cardiovascular. "
                          "Se recomienda consultar a un profesional de salud.",
                          "Elevated triglycerides and cholesterol together can be associated with a higher cardiovascular "
                          "risk. Consulting a health professional is recommended."))
    if _insights:
        st.markdown(f"#### 🧠 {T('Posibles asociaciones entre tus resultados', 'Possible associations between your results')}")
        for _ins in _insights:
            st.info(f"🧠 {_ins}")

    st.divider()

    st.markdown(f"#### 🎯 {T('¿Cómo impacta esto en tu día a día? (Análisis Sanguíneo)', 'How does this impact your daily life? (Blood Test)')}")
    _ambito_en_map = {"Escolar/Académico": "School/Academic", "Laboral": "Work", "Psicológico/Emocional": "Psychological/Emotional"}
    ambito_seleccionado = st.selectbox(
        T("Elige el ámbito en el que quieres ver reflejado el impacto de tus resultados:",
          "Choose the area where you want to see the impact of your results reflected:"),
        ["Escolar/Académico", "Laboral", "Psicológico/Emocional"], key="ambito_sangre",
        format_func=lambda x: T(x, _ambito_en_map.get(x, x))
    )
    for _parametro, _categoria in _todos:
        _color_pt = CATEGORIA_SEMAFORO.get(_categoria, "gris")
        _hex_pt = SEMAFORO_ESTILO[_color_pt]["hex"]
        _fondo_pt = SEMAFORO_ESTILO[_color_pt]["fondo"]
        _texto_impacto = generar_impacto_ambito(_parametro, _categoria, ambito_seleccionado)
        st.markdown(f"""
        <div style="background:{_fondo_pt};border-left:4px solid {_hex_pt};border-radius:16px;
                    padding:12px 18px;margin-bottom:8px;
                    box-shadow:0 1px 2px rgba(0,0,0,0.02), 0 4px 12px rgba(0,0,0,0.04);">
        <b style="color:{_hex_pt};">{_pn(_parametro)}</b> <span style="color:#1C1C1E;">({_categoria})</span> — <span style="color:#1C1C1E;">{_texto_impacto}</span>
        </div>
        """, unsafe_allow_html=True)

    with st.expander(f"📊 {T('Ver tablas de referencia clínica completas', 'View full clinical reference tables')}"):
        panel_referencia_hemo_hierro()
        panel_referencia_trigli_gluco_coles()
    recursos_externos(1, [
        (T("🩸 Anemia (MedlinePlus)", "🩸 Anemia (MedlinePlus)"), "https://medlineplus.gov/spanish/anemia.html"),
        (T("🫀 Colesterol (MedlinePlus)", "🫀 Cholesterol (MedlinePlus)"), "https://medlineplus.gov/spanish/cholesterol.html"),
        (T("💉 Diabetes (OMS)", "💉 Diabetes (WHO)"), "https://www.who.int/es/news-room/fact-sheets/detail/diabetes"),
    ])

    st.markdown(f"""
    <div style="background:#F5F5F7;border-radius:16px;padding:12px 18px;margin-top:14px;font-size:0.8rem;color:#5C6B60;">
    📚 <b>{T('Fuentes consultadas:', 'Sources consulted:')}</b> {T('Organización Mundial de la Salud (OMS)', 'World Health Organization (WHO)')} · American Diabetes Association ·
    MedlinePlus · Mayo Clinic · {T('Ministerio de Salud del Perú (MINSA)', "Peru's Ministry of Health (MINSA)")}.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:16px;padding:12px 18px;margin-top:10px;font-size:0.82rem;color:#7A4A00;">
    ⚠️ <b>{T('Información importante:', 'Important information:')}</b> {T('esta plataforma tiene fines educativos y de apoyo para la comprensión de resultados clínicos. No reemplaza el diagnóstico, tratamiento ni la valoración realizada por un médico o nutricionista.', 'this platform is for educational purposes and to support the understanding of clinical results. It does not replace the diagnosis, treatment, or assessment made by a doctor or nutritionist.')}
    </div>
    """, unsafe_allow_html=True)

    caja_util(T("Un análisis de sangre trae puros números y siglas difíciles de entender (¿12.5 g/dL es bueno o malo?). "
              "Esta hoja traduce esos números a un lenguaje simple: 'Normal', 'Anemia leve', 'Alto', etc., y te explica "
              "qué significan, por qué ocurren y qué podrías hacer. Así sabes de un vistazo si algún valor necesita "
              "atención médica. 🩺❤️",
              "A blood test comes with nothing but numbers and hard-to-understand abbreviations (is 12.5 g/dL good or "
              "bad?). This sheet translates those numbers into simple language: 'Normal', 'Mild Anemia', 'High', etc., "
              "and explains what they mean, why they happen, and what you could do. That way you know at a glance if "
              "any value needs medical attention. 🩺❤️"),
              emoji="🩸", color="#FFEBEE", borde="#E53935")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "1B.-ESTADO FISIOLÓGICO":
    # ===== 3. MÓDULO: Estado Fisiológico (signos vitales del Bloque 3) =====================
    def _clasif_pa(_pas, _pad):
        if _pas <= 0 or _pad <= 0: return "Sin datos", "gris"
        if _pas < 50 or _pas > 300 or _pad < 30 or _pad > 200: return "Valor no válido", "gris"
        if _pas < 90 or _pad < 60: return "Baja / Hipotensión", "ambar"
        if 90 <= _pas <= 119 and 60 <= _pad <= 79: return "Normal / Óptima", "verde"
        if 120 <= _pas <= 129 and _pad < 80: return "Elevado", "ambar"
        if _pas > 180 or _pad > 120: return "Emergencia Hipertensiva", "rojo"
        if 140 <= _pas <= 180 or 90 <= _pad <= 120: return "Hipertensión Estadio 2", "rojo"
        if 130 <= _pas <= 139 or 80 <= _pad <= 89: return "Hipertensión Estadio 1", "rojo"
        return "Normal / Óptima", "verde"

    def _clasif_spo2(_s):
        if _s <= 0: return "Sin datos", "gris"
        if _s < 90: return "Hipoxia", "rojo"
        if _s < 95: return "Aceptable", "ambar"
        return "Excelente", "verde"

    def _clasif_temp(_t):
        if _t <= 34.0: return "Sin datos", "gris"
        if _t < 35.0: return "Hipotermia", "rojo"
        if _t < 36.1: return "Temperatura baja", "ambar"
        if _t <= 37.2: return "Normal", "verde"
        if _t <= 37.9: return "Febrícula", "ambar"
        if _t <= 39.5: return "Fiebre", "rojo"
        return "Fiebre alta", "rojo"

    def _clasif_pulso(_p):
        if _p <= 0: return "Sin datos", "gris"
        if _p < 60: return "Bradicardia", "ambar"
        if _p <= 100: return "Normal", "verde"
        return "Taquicardia", "ambar"

    _cat_pa, _col_pa = _clasif_pa(pas, pad)
    _cat_ox, _col_ox = _clasif_spo2(spo2)
    _cat_te, _col_te = _clasif_temp(temp_corp)
    _cat_pu, _col_pu = _clasif_pulso(pulso)

    # --- 3.1 Hero del módulo -------------------------------------------------------------
    st.markdown("""
    <div style="background:linear-gradient(120deg,#FFEBEE 0%,#FFFFFF 75%);border-radius:24px;
    padding:22px 28px;margin-bottom:16px;border:1px solid rgba(224,54,54,0.15);
    box-shadow:0 6px 18px rgba(224,54,54,0.08);">
    <p style="margin:0 0 4px 0;font-weight:900;color:#C0392B;font-size:1.85rem;letter-spacing:-0.02em;">❤️ {ESTFISIO_TITULO}</p>
    <p style="margin:0 0 8px 0;color:#5C2A26;font-weight:700;font-size:0.98rem;">{ESTFISIO_SUB}</p>
    <p style="margin:0;color:#7A4A44;font-size:0.88rem;line-height:1.5;">{ESTFISIO_DESC}</p>
    </div>
    """.format(
        ESTFISIO_TITULO=T("Estado Fisiológico", "Physiological State"),
        ESTFISIO_SUB=T("Así está funcionando tu cuerpo en este momento", "This is how your body is functioning right now"),
        ESTFISIO_DESC=T("No solo mostramos tus signos vitales: te explicamos qué significan, qué pueden indicar y cuándo "
                         "conviene prestarles atención.",
                         "We don't just show your vital signs: we explain what they mean, what they can indicate, and "
                         "when it's worth paying attention to them."),
    ), unsafe_allow_html=True)

    _VITAL_EN = {"Presión Arterial": "Blood Pressure", "Oxigenación (SpO₂)": "Oxygenation (SpO₂)",
                 "Temperatura": "Temperature", "Pulso": "Pulse", "Pulso en Reposo": "Resting Pulse"}
    def _vn(v):
        return T(v, _VITAL_EN.get(v, v))

    # --- 3.2 Semáforo fisiológico — dashboard de 4 tarjetas -------------------------------
    st.markdown(f"##### 🚦 {T('Una vista rápida del estado general de tus signos vitales', 'A quick look at the overall state of your vital signs')}")
    _vitales_dash = [
        ("❤️", "Presión Arterial", f"{pas}/{pad} mmHg" if pas > 0 and pad > 0 else "—", _cat_pa, _col_pa),
        ("🫁", "Oxigenación (SpO₂)", f"{spo2:.0f} %" if spo2 > 0 else "—", _cat_ox, _col_ox),
        ("🌡️", "Temperatura", f"{temp_corp:.1f} °C" if temp_corp > 34.0 else "—", _cat_te, _col_te),
        ("💓", "Pulso en Reposo", f"{pulso} lpm" if pulso > 0 else "—", _cat_pu, _col_pu),
    ]
    _cols_vd = st.columns(4)
    for _col, (_em, _tt, _val, _cat, _colk) in zip(_cols_vd, _vitales_dash):
        _st = SEMAFORO_ESTILO[_colk]
        with _col:
            st.markdown(f"""
            <div class="bento-card" style="border-top:4px solid {_st['hex']};text-align:center;">
            <div style="font-size:1.5rem;">{_em}</div>
            <p style="margin:6px 0 2px 0;color:#5C6B60;font-size:0.76rem;font-weight:700;text-transform:uppercase;">{_vn(_tt)}</p>
            <p style="margin:0 0 6px 0;font-weight:800;font-size:1.15rem;color:#17301F;">{_val}</p>
            <span style="background:{_st['fondo']};color:{_st['hex']};padding:4px 12px;border-radius:999px;
            font-size:0.74rem;font-weight:800;">{_st['emoji']} {_cat}</span>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # --- 3.3 Detalle: ¿Qué significa cada resultado? (4 sub-tarjetas por signo vital) -----
    st.markdown(f"##### 🔎 {T('¿Qué significa cada resultado?', 'What does each result mean?')}")
    _PASTEL_CARD = {
        "mide":  {"fondo": "#EAF4FE", "borde": "#8FC1F2", "titulo": "#1565C0"},
        "signif":{"fondo": "#F3EEFB", "borde": "#C6AEE8", "titulo": "#6A3FA0"},
        "reco":  {"fondo": "#EAFAEE", "borde": "#9BD8AE", "titulo": "#1E5631"},
        "curio": {"fondo": "#FFF6E0", "borde": "#F4D27A", "titulo": "#B8860B"},
    }
    _INFO_VITAL = {
        "Presión Arterial": {
            "icono": "❤️", "valor": f"{pas}/{pad} mmHg" if pas > 0 and pad > 0 else "—", "categoria": _cat_pa, "color": _col_pa,
            "que_mide": T("Mide la fuerza con la que el corazón bombea sangre a través de las arterias hacia el resto del cuerpo.",
                          "Measures the force with which the heart pumps blood through the arteries to the rest of the body."),
            "sin_dato": T("Aún no ingresaste tu presión arterial. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
                          "You haven't entered your blood pressure yet. Go to 'My Data' → Block 3 to record it."),
            "recomendaciones": [("🥗", T("Menos sal, más frutas y verduras", "Less salt, more fruits and vegetables")),
                                 ("💧", T("Buena hidratación", "Good hydration")),
                                 ("🩺", T("Consulta si persiste alta", "See a doctor if it stays high"))],
            "curioso": T("La postura, el estrés y hasta hablar durante la medición pueden alterar el resultado hasta en 10 mmHg.",
                         "Posture, stress, and even talking during the measurement can alter the result by up to 10 mmHg."),
        },
        "Oxigenación (SpO₂)": {
            "icono": "🫁", "valor": f"{spo2:.0f} %" if spo2 > 0 else "—", "categoria": _cat_ox, "color": _col_ox,
            "que_mide": T("Indica el porcentaje de oxígeno que transporta tu sangre hacia órganos y músculos.",
                          "Indicates the percentage of oxygen your blood carries to your organs and muscles."),
            "sin_dato": T("Aún no ingresaste tu oxigenación. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
                          "You haven't entered your oxygenation yet. Go to 'My Data' → Block 3 to record it."),
            "recomendaciones": [("🫁", T("Respiración profunda", "Deep breathing")),
                                 ("🚭", T("Evitar el humo/tabaco", "Avoid smoke/tobacco")),
                                 ("🩺", T("Consulta si baja de 95%", "See a doctor if it drops below 95%"))],
            "curioso": T("La altura geográfica reduce naturalmente el SpO₂; a mayor altitud, el aire tiene menos oxígeno disponible.",
                         "Altitude naturally reduces SpO₂; the higher the altitude, the less oxygen the air has available."),
        },
        "Temperatura": {
            "icono": "🌡️", "valor": f"{temp_corp:.1f} °C" if temp_corp > 34.0 else "—", "categoria": _cat_te, "color": _col_te,
            "que_mide": T("Refleja qué tan bien tu organismo regula el calor interno para mantener sus funciones vitales.",
                          "Reflects how well your body regulates internal heat to keep its vital functions running."),
            "sin_dato": T("Aún no ingresaste tu temperatura. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
                          "You haven't entered your temperature yet. Go to 'My Data' → Block 3 to record it."),
            "recomendaciones": [("💧", T("Hidratación constante", "Stay well hydrated")),
                                 ("🛌", T("Reposo si hay fiebre", "Rest if you have a fever")),
                                 ("🩺", T("Consulta si persiste alta", "See a doctor if it stays high"))],
            "curioso": T("El ejercicio intenso, la ropa abrigada o el ambiente caluroso pueden subir tu temperatura sin que estés enferma/o.",
                         "Intense exercise, warm clothing, or a hot environment can raise your temperature even if you're not sick."),
        },
        "Pulso": {
            "icono": "💓", "valor": f"{pulso} lpm" if pulso > 0 else "—", "categoria": _cat_pu, "color": _col_pu,
            "que_mide": T("Cuenta cuántas veces late tu corazón en un minuto mientras estás en reposo.",
                          "Counts how many times your heart beats in a minute while you're at rest."),
            "sin_dato": T("Aún no ingresaste tu pulso. Ve a 'Mis Datos' → Bloque 3 para registrarlo.",
                          "You haven't entered your pulse yet. Go to 'My Data' → Block 3 to record it."),
            "recomendaciones": [("🚶", T("Actividad física regular", "Regular physical activity")),
                                 ("☕", T("Moderar la cafeína", "Moderate caffeine")),
                                 ("🩺", T("Consulta si es muy alto/bajo", "See a doctor if it's very high/low"))],
            "curioso": T("La cafeína, las emociones fuertes y la fiebre pueden acelerar tu pulso incluso en reposo.",
                         "Caffeine, strong emotions, and fever can speed up your pulse even while resting."),
        },
    }
    for _param, _info in _INFO_VITAL.items():
        _st = SEMAFORO_ESTILO[_info["color"]]
        st.markdown(f"""
        <div style="background:#FFFFFF;border-radius:22px;padding:16px 18px 20px 18px;margin-bottom:14px;
        border:1px solid rgba(0,0,0,0.06);box-shadow:0 4px 14px rgba(0,0,0,0.05);">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
        <span style="font-size:1.3rem;">{_info['icono']}</span>
        <b style="font-size:1.02rem;color:#17301F;">{_vn(_param)}</b>
        <span style="margin-left:auto;background:{_st['fondo']};color:{_st['hex']};padding:4px 12px;
        border-radius:999px;font-size:0.76rem;font-weight:800;">{_st['emoji']} {_info['valor']} · {_info['categoria']}</span>
        </div>
        """, unsafe_allow_html=True)

        _significado_txt = _info["sin_dato"] if _info["color"] == "gris" else \
            T(f"Con tu resultado de <b>{_info['valor']}</b>, tu estado se clasifica como <b>{_info['categoria']}</b> {_st['emoji']}.",
              f"With your result of <b>{_info['valor']}</b>, your state is classified as <b>{_info['categoria']}</b> {_st['emoji']}.")
        _reco_chips_html = "".join(
            f"""<span style="display:inline-block;background:#FFFFFF;border:1px solid #D8ECDD;border-radius:999px;
            padding:5px 12px;margin:3px 5px 3px 0;font-size:0.78rem;color:#1E5631;font-weight:700;">{_ic} {_tx}</span>"""
            for _ic, _tx in _info["recomendaciones"]
        )

        _c1, _c2, _c3, _c4 = st.columns(4)
        with _c1:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['mide']['fondo']};border:1px solid {_PASTEL_CARD['mide']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['mide']['titulo']};font-size:0.84rem;">🧠 {T('¿Qué mide?', 'What does it measure?')}</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_info['que_mide']}</p>
            </div>""", unsafe_allow_html=True)
        with _c2:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['signif']['fondo']};border:1px solid {_PASTEL_CARD['signif']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['signif']['titulo']};font-size:0.84rem;">📋 {T('¿Qué significa tu resultado?', 'What does your result mean?')}</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_significado_txt}</p>
            </div>""", unsafe_allow_html=True)
        with _c3:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['reco']['fondo']};border:1px solid {_PASTEL_CARD['reco']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;overflow:hidden;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['reco']['titulo']};font-size:0.84rem;">✅ {T('Recomendaciones generales', 'General recommendations')}</p>
            <div style="line-height:1.9;">{_reco_chips_html}</div>
            </div>""", unsafe_allow_html=True)
        with _c4:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['curio']['fondo']};border:1px solid {_PASTEL_CARD['curio']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['curio']['titulo']};font-size:0.84rem;">💡 {T('¿Sabías qué?', 'Did you know?')}</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_info['curioso']}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

    st.write("")

    # --- 3.4 Interpretación Fisiológica Inteligente ---------------------------------------
    st.markdown(f"##### 🧠 {T('Interpretación Fisiológica Inteligente', 'Smart Physiological Interpretation')}")
    _todos_vitales = [("Presión Arterial", _col_pa), ("Oxigenación (SpO₂)", _col_ox),
                       ("Temperatura", _col_te), ("Pulso", _col_pu)]
    _con_dato_v = [(p, c) for p, c in _todos_vitales if c != "gris"]
    _rojos_v = [p for p, c in _con_dato_v if c == "rojo"]
    _ambar_v = [p for p, c in _con_dato_v if c == "ambar"]

    if not _con_dato_v:
        st.info(T("Ingresa tus signos vitales en 'Mis Datos' → Bloque 3 para ver tu interpretación fisiológica.",
                  "Enter your vital signs in 'My Data' → Block 3 to see your physiological interpretation."))
    elif _rojos_v:
        _lista_r = ", ".join(T(p, _VITAL_EN.get(p, p)) for p in _rojos_v)
        st.markdown(f"""
        <div style="background:#FBEAE8;border-radius:20px;padding:18px 24px;border-left:5px solid #C0392B;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#C0392B;">🔴 {T('Atención Requerida', 'Attention Required')}</p>
        <p style="margin:0;color:#7A2E27;font-size:0.9rem;line-height:1.5;">
        {T('Se detectó un valor fuera de rango en', 'An out-of-range value was detected in')}: <b>{_lista_r}</b>. {T('Puede deberse a distintos factores fisiológicos o a una lectura incorrecta del sensor.', 'This may be due to various physiological factors or an incorrect sensor reading.')} <i>{T('Recomendación', 'Recommendation')}:</i> {T('si la medición persiste o sientes malestar, consulta con un profesional de salud.', 'if the reading persists or you feel unwell, consult a health professional.')}</p>
        </div>
        """, unsafe_allow_html=True)
    elif _ambar_v:
        _lista_a = ", ".join(T(p, _VITAL_EN.get(p, p)) for p in _ambar_v)
        st.markdown(f"""
        <div style="background:#FDF1E4;border-radius:20px;padding:18px 24px;border-left:5px solid #E67E22;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#E67E22;">🟡 {T('Atención Ligera', 'Mild Attention')}</p>
        <p style="margin:0;color:#7A5A26;font-size:0.9rem;line-height:1.5;">
        <b>{_lista_a}</b> {T('se encuentra ligeramente fuera del rango habitual. No suele ser motivo de alarma, pero conviene observar cómo evoluciona.', 'is slightly outside the usual range. This is usually not a cause for alarm, but it is worth watching how it develops.')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#EAFAEE;border-radius:20px;padding:18px 24px;border-left:5px solid #1E5631;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#1E5631;">🟢 {T('Estado General', 'Overall State')}</p>
        <p style="margin:0 0 8px 0;color:#17301F;font-size:0.9rem;">
        {" &nbsp;·&nbsp; ".join(f"{SEMAFORO_ESTILO[c]['emoji']} {_vn(p)}" for p, c in _con_dato_v)}</p>
        <p style="margin:0;color:#17301F;font-size:0.88rem;"><b>{T('Resultado general', 'Overall result')}:</b> {T('tus signos vitales se encuentran dentro de los rangos esperados para una persona en reposo.', 'your vital signs are within the expected ranges for a person at rest.')}</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # --- 3.5 Impacto en la vida diaria — segmented control --------------------------------
    st.markdown(f"##### 🎯 {T('Impacto en la vida diaria (Signos Vitales)', 'Impact on daily life (Vital Signs)')}")
    _IMPACTO_VITAL = {
        T("🏫 Colegio", "🏫 School"): {
            "Presión Arterial": T("Puede causar dolor de cabeza, somnolencia o falta de concentración en clase.",
                                   "It can cause headaches, drowsiness, or trouble concentrating in class."),
            "Oxigenación (SpO₂)": T("Causa fatiga rápida al subir escaleras o caminar; menor resistencia en educación física.",
                                     "It causes quick fatigue when climbing stairs or walking; lower stamina in PE class."),
            "Temperatura": T("Rendimiento académico y cognitivo reducido; es recomendable no asistir y descansar.",
                              "Reduced academic and cognitive performance; it's best to stay home and rest."),
            "Pulso": T("Sensación de agitación; evita esfuerzos físicos intensos y mantén una buena hidratación.",
                       "A feeling of being on edge; avoid intense physical effort and stay well hydrated."),
        },
        T("🏠 Casa", "🏠 Home"): {
            "Presión Arterial": T("Puede generar cansancio o mareos al hacer tareas domésticas exigentes.",
                                   "It can cause tiredness or dizziness when doing demanding chores."),
            "Oxigenación (SpO₂)": T("Sensación de falta de aire al subir escaleras o realizar quehaceres.",
                                     "A feeling of shortness of breath when climbing stairs or doing chores."),
            "Temperatura": T("Conviene guardar reposo, hidratarte bien y evitar esfuerzos en casa.",
                              "It's best to rest, stay well hydrated, and avoid exertion at home."),
            "Pulso": T("Puede sentirse como palpitaciones; prioriza el descanso y evita sustos o sobresaltos.",
                       "It may feel like palpitations; prioritize rest and avoid sudden frights or startles."),
        },
        T("🏃 Actividad Física", "🏃 Physical Activity"): {
            "Presión Arterial": T("Conviene evitar ejercicio intenso hasta que el valor se normalice.",
                                   "It's best to avoid intense exercise until the value returns to normal."),
            "Oxigenación (SpO₂)": T("El rendimiento físico baja notablemente; reduce la intensidad del entrenamiento.",
                                     "Physical performance drops noticeably; reduce training intensity."),
            "Temperatura": T("No se recomienda hacer deporte con fiebre; el cuerpo ya está en sobreesfuerzo.",
                              "Exercising with a fever isn't recommended; the body is already under strain."),
            "Pulso": T("Un pulso elevado en reposo indica que conviene posponer el ejercicio intenso.",
                       "An elevated resting pulse suggests it's best to postpone intense exercise."),
        },
        T("💼 Trabajo", "💼 Work"): {
            "Presión Arterial": T("Puede afectar la concentración en tareas que requieren atención sostenida.",
                                   "It can affect concentration on tasks that require sustained attention."),
            "Oxigenación (SpO₂)": T("Mayor cansancio en jornadas largas o con esfuerzo físico.",
                                     "Greater fatigue during long workdays or physical effort."),
            "Temperatura": T("Es preferible descansar en casa en vez de asistir a trabajar.",
                              "It's preferable to rest at home instead of going to work."),
            "Pulso": T("Evita situaciones de alta presión o estrés hasta que el ritmo se normalice.",
                       "Avoid high-pressure or stressful situations until the rhythm returns to normal."),
        },
    }
    _tab_colegio, _tab_casa, _tab_actividad, _tab_trabajo = st.tabs(list(_IMPACTO_VITAL.keys()))
    for _tab, _ambito_v in zip([_tab_colegio, _tab_casa, _tab_actividad, _tab_trabajo], _IMPACTO_VITAL.keys()):
        with _tab:
            for _param, _colk in _todos_vitales:
                _st = SEMAFORO_ESTILO[_colk]
                st.markdown(f"""
                <div style="background:{_st['fondo']};border-left:4px solid {_st['hex']};border-radius:16px;
                padding:10px 16px;margin-bottom:6px;">
                <b style="color:{_st['hex']};">{_vn(_param)}</b> — <span style="color:#1C1C1E;font-size:0.88rem;">
                {_IMPACTO_VITAL[_ambito_v][_param]}</span>
                </div>
                """, unsafe_allow_html=True)

    st.write("")

    # --- 3.6 Tablas de referencia clínica — filas con highlight dinámico (Bento Grid) ------
    st.markdown(f"##### 📊 {T('Tablas de Referencia Clínica', 'Clinical Reference Tables')}")
    st.caption(T("Rangos clínicos oficiales. La fila que corresponde a tu valor actual se enciende con un glow.",
                 "Official clinical ranges. The row matching your current value lights up with a glow."))

    _TABLE_CSS = """
    <style>
    .tabla-ref-wrap{background:#FFFFFF;border-radius:16px;padding:18px 20px 14px 20px;margin-bottom:18px;
    border:1px solid rgba(0,0,0,0.06);box-shadow:0 4px 14px rgba(0,0,0,0.05);}
    .tabla-ref-head{display:flex;align-items:baseline;gap:10px;margin-bottom:2px;flex-wrap:wrap;}
    .tabla-ref-titulo{font-weight:800;font-size:1rem;color:#17301F;}
    .tabla-ref-fuente{font-size:0.8rem;color:gray;}
    table.tabla-ref{width:100%;border-collapse:separate;border-spacing:0 6px;margin-top:8px;font-size:0.85rem;}
    table.tabla-ref th{text-align:left;font-size:0.74rem;color:#8E8E93;font-weight:800;
    text-transform:uppercase;letter-spacing:.02em;padding:0 16px 6px 16px;}
    table.tabla-ref td{padding:12px 16px;border-bottom:1px solid rgba(0,0,0,0.05);}
    table.tabla-ref tr.fila-ref td:first-child{border-top-left-radius:12px;border-bottom-left-radius:12px;}
    table.tabla-ref tr.fila-ref td:last-child{border-top-right-radius:12px;border-bottom-right-radius:12px;}
    .badge-activo{display:inline-block;margin-left:8px;background:#1C1C1E;color:#FFFFFF;font-weight:900;
    font-size:0.68rem;padding:3px 9px;border-radius:999px;white-space:nowrap;}
    @keyframes pulse-ref{0%{box-shadow:0 0 0 0 rgba(52,199,89,0.55);}70%{box-shadow:0 0 0 10px rgba(52,199,89,0);}
    100%{box-shadow:0 0 0 0 rgba(52,199,89,0);}}
    .fila-pulse{animation:pulse-ref 1.8s infinite;}
    </style>
    """
    st.markdown(_TABLE_CSS, unsafe_allow_html=True)

    def _fila_ref(_celdas, _tono_pastel, _tono_vibrante, _activa, _pulse=False):
        """_celdas: lista de textos por columna. Devuelve <tr> con estilo pastel o vibrante+glow si activa."""
        if _activa:
            _fondo, _texto = _tono_vibrante["fondo"], _tono_vibrante["texto"]
            _borde = f"2px solid {_tono_vibrante['borde']}"
            _glow = f"box-shadow:0 0 15px {_tono_vibrante['glow']};"
            _badge = f'<span class="badge-activo">📍 {T("TU VALOR ACTUAL", "YOUR CURRENT VALUE")}</span>'
        else:
            _fondo, _texto = _tono_pastel["fondo"], _tono_pastel["texto"]
            _borde = "1px solid rgba(0,0,0,0.04)"
            _glow = ""
            _badge = ""
        _clase = "fila-ref" + (" fila-pulse" if _activa and _pulse else "")
        _tds = "".join(
            f'<td style="background:{_fondo};color:{_texto};border-top:{_borde};border-bottom:{_borde};">'
            f'{_c}{_badge if _i == len(_celdas)-1 else ""}</td>'
            for _i, _c in enumerate(_celdas)
        )
        return f'<tr class="{_clase}">{_tds}</tr>'

    _TONO2 = {
        "azul":     {"pastel": {"fondo": "#E3F2FD", "texto": "#1565C0"}, "vibrante": {"fondo": "#5AC8FA", "texto": "#0D3C61", "borde": "#1565C0", "glow": "rgba(90,200,250,0.6)"}},
        "verde":    {"pastel": {"fondo": "#E8F5E9", "texto": "#1E5631"}, "vibrante": {"fondo": "#34C759", "texto": "#FFFFFF", "borde": "#1E5631", "glow": "rgba(52,199,89,0.55)"}},
        "menta":    {"pastel": {"fondo": "#E1F7EC", "texto": "#0E6B4F"}, "vibrante": {"fondo": "#00C7A0", "texto": "#FFFFFF", "borde": "#0E6B4F", "glow": "rgba(0,199,160,0.55)"}},
        "amarillo": {"pastel": {"fondo": "#FFFDE7", "texto": "#8A6D00"}, "vibrante": {"fondo": "#FFD600", "texto": "#4A3900", "borde": "#B8860B", "glow": "rgba(255,214,0,0.6)"}},
        "naranja":  {"pastel": {"fondo": "#FFF1E0", "texto": "#B0530A"}, "vibrante": {"fondo": "#FF9500", "texto": "#FFFFFF", "borde": "#B0530A", "glow": "rgba(255,149,0,0.55)"}},
        "rojo":     {"pastel": {"fondo": "#FFEBEE", "texto": "#C0392B"}, "vibrante": {"fondo": "#FF3B30", "texto": "#FFFFFF", "borde": "#8E1B12", "glow": "rgba(255,59,48,0.6)"}},
        "rojo_osc": {"pastel": {"fondo": "#FBDADA", "texto": "#8E1B12"}, "vibrante": {"fondo": "#D70015", "texto": "#FFFFFF", "borde": "#5A0A0A", "glow": "rgba(215,0,21,0.6)"}},
        "purpura":  {"pastel": {"fondo": "#F3E5F5", "texto": "#6A3FA0"}, "vibrante": {"fondo": "#AF52DE", "texto": "#FFFFFF", "borde": "#4B2270", "glow": "rgba(175,82,222,0.6)"}},
    }

    def _render_tabla_html(_icono, _titulo, _fuente, _headers, _filas_html):
        _ths = "".join(f"<th>{_h}</th>" for _h in _headers)
        st.markdown(f"""
        <div class="tabla-ref-wrap">
        <div class="tabla-ref-head"><span style="font-size:1.2rem;">{_icono}</span>
        <span class="tabla-ref-titulo">{_titulo}</span></div>
        <div class="tabla-ref-fuente">{_fuente}</div>
        <table class="tabla-ref"><thead><tr>{_ths}</tr></thead><tbody>{_filas_html}</tbody></table>
        </div>
        """, unsafe_allow_html=True)

    # --- 1. Presión Arterial (AHA) ---
    _pa_rango_invalido = pas > 0 and pad > 0 and (pas < 50 or pas > 300 or pad < 30 or pad > 200)

    _idx_pa_activa = None
    if pas > 0 and pad > 0 and not _pa_rango_invalido:
        if pas < 90 or pad < 60:
            _idx_pa_activa = 0   # Baja / Hipotensión
        elif 90 <= pas <= 119 and 60 <= pad <= 79:
            _idx_pa_activa = 1   # Normal / Óptima
        elif 120 <= pas <= 129 and pad < 80:
            _idx_pa_activa = 2   # Elevado
        elif pas > 180 or pad > 120:
            _idx_pa_activa = 5   # Hipertensión Severa / Emergencia Hipertensiva
        elif 140 <= pas <= 180 or 90 <= pad <= 120:
            _idx_pa_activa = 4   # Hipertensión Estadio 2
        elif 130 <= pas <= 139 or 80 <= pad <= 89:
            _idx_pa_activa = 3   # Hipertensión Estadio 1
        else:
            _idx_pa_activa = 1

    _pa_filas_data = [
        (["Baja / Hipotensión", "&lt; 90", "o", "&lt; 60"], "azul"),
        (["Normal / Óptima", "90 – 119", "y", "60 – 79"], "verde"),
        (["Elevado", "120 – 129", "y", "&lt; 80"], "amarillo"),
        (["Hipertensión Estadio 1", "130 – 139", "o", "80 – 89"], "naranja"),
        (["Hipertensión Estadio 2", "≥ 140", "o", "≥ 90"], "rojo"),
        (["Emergencia Hipertensiva", "&gt; 180", "y/o", "&gt; 120"], "purpura"),
    ]
    _pa_html = "".join(
        _fila_ref(_d, _TONO2[_t]["pastel"], _TONO2[_t]["vibrante"], _i == _idx_pa_activa)
        for _i, (_d, _t) in enumerate(_pa_filas_data)
    )
    _render_tabla_html("❤️", T("Presión Arterial", "Blood Pressure"), T("Fuente: American Heart Association (AHA)", "Source: American Heart Association (AHA)"),
                        [T("Categoría", "Category"), T("Sistólica (mmHg)", "Systolic (mmHg)"), T("Condición", "Condition"), T("Diastólica (mmHg)", "Diastolic (mmHg)")], _pa_html)
    if _pa_rango_invalido:
        st.markdown(f'<p style="color:#C0392B;font-weight:800;font-size:0.85rem;margin-top:-8px;">'
                     f'⚠️ {T("Valor fuera de rango clínico. Por favor verifica tus datos", "Value outside clinical range. Please check your data")}</p>', unsafe_allow_html=True)

    # --- 2. Saturación de Oxígeno (SpO₂) ---
    _idx_ox_activa = None
    if spo2 > 0:
        if spo2 < 67:
            _idx_ox_activa = 4
        elif spo2 < 85:
            _idx_ox_activa = 3
        elif spo2 < 95:
            _idx_ox_activa = 2
        elif spo2 <= 100 and etapa in ("Niñez", "Adolescencia"):
            _idx_ox_activa = 0
        else:
            _idx_ox_activa = 1

    _ox_filas_data = [
        (["≥ 97%", "Normal (Lactantes/Niños)", "Excelente oxigenación tisular"], "menta"),
        (["95% – 100%", "Normal (Adultos / &gt;70 años)", "Transporte idóneo de O₂"], "verde"),
        (["85% – 94%", "Anormal / Alerta Leve", "Hipoxemia leve / monitoreo"], "amarillo"),
        (["80% – 85%", "Compromiso Cerebral (Hipoxia)", "Riesgo de alteración neurológica"], "naranja"),
        (["&lt; 67%", "Cianosis Severa", "Coloración azulada (Urgencia)"], "rojo"),
    ]
    _ox_html = "".join(
        _fila_ref(_d, _TONO2[_t]["pastel"], _TONO2[_t]["vibrante"], _i == _idx_ox_activa)
        for _i, (_d, _t) in enumerate(_ox_filas_data)
    )
    _render_tabla_html("🫁", T("Saturación de Oxígeno (SpO₂)", "Oxygen Saturation (SpO₂)"), T("Fuente: Organización Mundial de la Salud (OMS)", "Source: World Health Organization (WHO)"),
                        [T("Rango de SpO₂", "SpO₂ Range"), T("Estado Clínico", "Clinical State"), T("Manifestación Fisiológica", "Physiological Manifestation")], _ox_html)

    # --- 3. Temperatura Corporal (°C) ---
    _idx_te_activa = None
    if temp_corp > 34.0:
        if edad <= 2:
            _idx_te_activa = 0
        elif edad <= 10:
            _idx_te_activa = 1
        elif edad <= 65:
            _idx_te_activa = 2
        else:
            _idx_te_activa = 3

    _te_filas_data = [
        ([T("Bebés (0–2 años)", "Infants (0–2 years)"), "36.6 – 38.0 °C", "≥ 38.0 °C", "&gt; 39.0 °C"], "verde"),
        ([T("Niños (3–10 años)", "Children (3–10 years)"), "35.5 – 37.5 °C", "≥ 38.0 °C", "&gt; 39.0 °C"], "verde"),
        ([T("Adolescentes y Adultos (11–65 años)", "Adolescents and Adults (11–65 years)"), "36.4 – 37.6 °C", "≥ 38.0 °C", "&gt; 39.5 °C"], "verde"),
        ([T("Adultos (&gt;65 años)", "Adults (&gt;65 years)"), "35.8 – 36.9 °C", "≥ 38.0 °C", "&gt; 39.5 °C"], "verde"),
    ]
    _te_alerta = temp_corp >= 38.0
    _te_html = "".join(
        _fila_ref(_d, _TONO2["verde"]["pastel"], _TONO2["rojo" if _te_alerta else "verde"]["vibrante"],
                  _i == _idx_te_activa)
        for _i, (_d, _t) in enumerate(_te_filas_data)
    )
    _render_tabla_html("🌡️", T("Temperatura Corporal (°C)", "Body Temperature (°C)"), T("Fuente: Rangos clínicos por grupo de edad", "Source: Clinical ranges by age group"),
                        [T("Grupo de Edad", "Age Group"), T("Normal (°C)", "Normal (°C)"), T("Fiebre (°C)", "Fever (°C)"), T("Fiebre Alta (°C)", "High Fever (°C)")], _te_html)
    if _idx_te_activa is not None and _te_alerta:
        st.markdown(f'<p style="color:#C0392B;font-weight:800;font-size:0.85rem;margin-top:-8px;">'
                     f'⚠️ {T("¡Atención: Fiebre detectada!", "Attention: Fever detected!")}</p>', unsafe_allow_html=True)

    # --- 4. Frecuencia Cardíaca (Pulso en Reposo) ---
    _idx_pu_activa = None
    if pulso > 0:
        if edad <= 3:
            _idx_pu_activa = 3
        elif edad <= 5:
            _idx_pu_activa = 4
        elif edad <= 12:
            _idx_pu_activa = 5
        else:
            _idx_pu_activa = 6

    _pu_filas_data = [
        (["Pretérmino", "120 – 180 lpm", "&lt; 120 o &gt; 180 lpm"], "amarillo"),
        (["Recién Nacido (0–1 mes)", "100 – 160 lpm", "&lt; 100 o &gt; 160 lpm"], "verde"),
        (["Bebé (1–12 meses)", "80 – 140 lpm", "&lt; 80 o &gt; 140 lpm"], "verde"),
        (["Niño Pequeño (1–3 años)", "80 – 130 lpm", "&lt; 80 o &gt; 130 lpm"], "verde"),
        (["Preescolar (3–5 años)", "80 – 110 lpm", "&lt; 80 o &gt; 110 lpm"], "verde"),
        (["Edad Escolar (6–12 años)", "70 – 100 lpm", "&lt; 70 o &gt; 100 lpm"], "verde"),
        (["Adolescentes y Adultos", "60 – 100 lpm", "&lt; 60 o &gt; 100 lpm"], "verde"),
    ]
    _pu_html = "".join(
        _fila_ref(_d, _TONO2[_t]["pastel"], _TONO2[_t]["vibrante"], _i == _idx_pu_activa, _pulse=True)
        for _i, (_d, _t) in enumerate(_pu_filas_data)
    )
    _render_tabla_html("💓", T("Frecuencia Cardíaca (Pulso en Reposo)", "Heart Rate (Resting Pulse)"), T("Fuente: American Heart Association (AHA)", "Source: American Heart Association (AHA)"),
                        [T("Grupo de Edad", "Age Group"), T("Rango Normal en Reposo", "Normal Resting Range"), T("Estado Anormal (Alerta)", "Abnormal State (Alert)")], _pu_html)

    st.write("")

    # --- 3.7 Fuentes científicas — chips con enlaces ---------------------------------------
    st.markdown(f"##### 🔗 {T('Fuentes de consulta médica', 'Medical reference sources')}")
    _fuentes_vitales = [
        ("OMS", "https://www.who.int/es"), ("AHA", "https://www.heart.org/"),
        ("ESC", "https://www.escardio.org/"), ("Mayo Clinic", "https://www.mayoclinic.org/es-es"),
        ("MINSA", "https://www.gob.pe/minsa"), ("MedlinePlus", "https://medlineplus.gov/spanish/"),
    ]
    _cols_fuentes = st.columns(len(_fuentes_vitales))
    for _col, (_nom, _url) in zip(_cols_fuentes, _fuentes_vitales):
        with _col:
            st.link_button(_nom, _url, use_container_width=True)

    # --- 3.8 Finalidad educativa -------------------------------------------------------------
    caja_util(T("Cuando recibes tus signos vitales normalmente solo ves números aislados sin saber si requieren "
              "atención. Esta sección traduce esos valores a un lenguaje claro y accesible, explicando qué "
              "significan y cómo influyen en tu día a día. Es una herramienta informativa pensada para ayudarte "
              "a comprender mejor tu organismo antes de acudir a un profesional de la salud. ❤️🩺",
              "When you get your vital signs, you usually just see isolated numbers without knowing if they need "
              "attention. This section translates those values into clear, accessible language, explaining what "
              "they mean and how they affect your daily life. It's an informational tool meant to help you better "
              "understand your body before seeing a health professional. ❤️🩺"),
              emoji="❤️", color="#FFEBEE", borde="#C0392B")
    st.caption(T("Estos signos vitales se ingresan en 'Mis Datos' → Bloque 3.",
                 "These vital signs are entered in 'My Data' → Block 3."))

    st.divider()

elif hoja_activa == "2.-IMC Y PERCENTIL":
    hoja_header(2, T("El IMC sirve para saber si una persona tiene un peso saludable según su altura y peso. "
                   "En adolescentes y niños se incluye también el Percentil.",
                   "BMI helps determine whether a person has a healthy weight for their height. "
                   "In teens and children, the Percentile is also included."),
                ilustracion=_ilustracion_imc_svg(), tip=T("¡Conoce tu IMC y cuida tu salud! 👍",
                                                            "Know your BMI and take care of your health! 👍"))
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "IMC = Peso (kg) / [Altura (m)]²" if st.session_state.get("idioma", "Español") != "English" else "BMI = Weight (kg) / [Height (m)]²",
        referencia=T("Organización Mundial de la Salud (OMS)", "World Health Organization (WHO)"))}</div>""", unsafe_allow_html=True)

    _con_percentil = etapa in ["Niñez", "Adolescencia"] and _percentil_usuario is not None
    _riesgo_imc = _categoria_imc_usuario in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3", "Obesidad Clase 3 (Severa)"]
    _riesgo_txt, _ = _riesgo_imc_txt(_categoria_imc_usuario)

    # --- 1. Tu Diagnóstico Nutricional ------------------------------------------------------
    panel_diagnostico_nutricional(imc, _percentil_usuario, _categoria_imc_usuario, con_percentil=_con_percentil)

    # --- 2 y 4. Escala horizontal + Estado Nutricional (checklist) --------------------------
    ec1, ec2 = st.columns([1.4, 1])
    with ec1:
        escala_horizontal_imc(imc, _categoria_imc_usuario, etapa, _percentil_usuario if _con_percentil else None)
    with ec2:
        tarjeta_estado_nutricional(_categoria_imc_usuario)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # --- 3. Percentil con protagonismo (solo Niñez/Adolescencia) ----------------------------
    if _con_percentil:
        percentil_visual_card(_percentil_usuario)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    elif etapa in ["Niñez", "Adolescencia"]:
        st.error(_categoria_imc_usuario)

    # --- 5. Interpretación Inteligente --------------------------------------------------------
    interpretacion_inteligente_imc(imc, _categoria_imc_usuario, etapa, _riesgo_txt)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # --- 6 y 7. ¿Qué puede influir en tu IMC? / Recordar (alerta clínica) -------------------
    ic1, ic2 = st.columns(2)
    with ic1:
        st.markdown('<div class="info3-card">', unsafe_allow_html=True)
        que_influye_imc()
        st.markdown('</div>', unsafe_allow_html=True)
    with ic2:
        recordar_alerta_clinica()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 8. Más información — enlaces uniformes ----------------------------------------------
    links_uniformes_mas_info()
    if _riesgo_imc:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        cta1, cta2 = st.columns(2)
        with cta1:
            cta_pill("🩸", "#FF3B30", T("Prueba de riesgo de prediabetes (CDC)", "Prediabetes Risk Test (CDC)"),
                     T("Responde un breve cuestionario de 1 minuto y conoce tu riesgo.",
                       "Answer a brief 1-minute questionnaire to learn your risk."),
                     T("Realizar prueba", "Take the test"), "https://www.cdc.gov/prediabetes/risktest/index.html")
        with cta2:
            cta_pill("❤️", "#1E88E5", T("Riesgos de salud por obesidad (CDC)", "Health Risks of Obesity (CDC)"),
                     T("Conoce las enfermedades y condiciones asociadas al sobrepeso y la obesidad.",
                       "Learn about the diseases and conditions associated with overweight and obesity."),
                     T("Ver más información", "See more information"), "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 9. Tabla de categorías de IMC (con columna de Riesgo) ------------------------------
    tabla_categorias_imc_visual(imc_usuario=imc)

    # --- 13. Progreso hacia una meta saludable ------------------------------------------------
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    progreso_hacia_meta_imc(imc, _categoria_imc_usuario)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 10. Gráfico de percentiles por edad (bandas de colores, ya intuitivo) ---------------
    st.markdown(T("#### 📈 Percentiles de IMC por edad (2 a 20 años)", "#### 📈 BMI Percentiles by Age (2 to 20 years)"))
    st.caption(T("Este gráfico te compara con otros niños y adolescentes de tu misma edad y sexo. Las franjas de "
               "colores son distintos rangos de peso: la franja central (celeste/verde) es el rango más saludable, "
               "mientras que las franjas de arriba o abajo indican bajo peso, sobrepeso u obesidad. La estrella ⭐ "
               "azul marca exactamente en qué punto te encuentras tú, si tu edad está entre 2 y 20 años.",
               "This chart compares you with other children and teens of your same age and sex. The colored bands "
               "represent different weight ranges: the central band (light blue/green) is the healthiest range, "
               "while the bands above or below indicate underweight, overweight, or obesity. The blue star ⭐ "
               "marks exactly where you stand, if your age is between 2 and 20 years."))
    sub_mujeres, sub_hombres = st.tabs([T("👧 Mujeres", "👧 Girls"), T("👦 Hombres", "👦 Boys")])
    with sub_mujeres:
        st.plotly_chart(grafico_percentil_bandas("Mujer", edad, imc, genero), use_container_width=True)
    with sub_hombres:
        st.plotly_chart(grafico_percentil_bandas("Hombre", edad, imc, genero), use_container_width=True)
    if edad not in PERCENTIL_MUJER:
        st.caption(T("ℹ️ Tu edad actual está fuera del rango de 2-20 años, así que no aparece tu punto marcado en el gráfico.",
                      "ℹ️ Your current age is outside the 2-20 year range, so your point isn't marked on the chart."))

    # --- 11. Tabla de percentiles — fila Y columna del usuario resaltadas -------------------
    with st.expander(T("📊 Ver tabla completa de percentiles (edad 2-20 años)", "📊 View full percentile table (age 2-20 years)"), expanded=False):
        tabla_percentiles_genero_visual(edad_usuario=edad, genero_usuario=genero, categoria_usuario=_categoria_imc_usuario)
        st.markdown(T("""
        <div style="margin-top:10px;background:#F3EAF7;border-radius:14px;padding:12px 16px;font-size:0.8rem;color:#6A1B9A;">
        💡 <b>¿Cómo usar esta tabla?</b> Busca la fila de tu edad y compara tu IMC con las columnas P5/P50/P85/P95:
        si tu IMC cae antes de P5 estás en Bajo Peso, entre P5 y P85 en Peso Saludable, entre P85 y P95 en Sobrepeso,
        y por encima de P95 en Obesidad. La columna marcada con tu color es la que corresponde a tu resultado actual.
        </div>
        """, """
        <div style="margin-top:10px;background:#F3EAF7;border-radius:14px;padding:12px 16px;font-size:0.8rem;color:#6A1B9A;">
        💡 <b>How to use this table?</b> Find your age row and compare your BMI with the P5/P50/P85/P95 columns:
        if your BMI falls before P5 you are Underweight, between P5 and P85 Healthy Weight, between P85 and P95 Overweight,
        and above P95 Obesity. The column marked with your color is the one matching your current result.
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 12. ¿Qué puedes hacer desde hoy? ------------------------------------------------------
    acciones_desde_hoy()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 14. Conexión con el resto del sistema ------------------------------------------------
    conexion_resto_sistema()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    caja_util(T("El IMC te dice, de forma simple, si tu peso está en un rango saludable para tu altura. "
              "En niños y adolescentes se usa además el 'percentil', que te compara con otros chicos de tu misma "
              "edad y sexo — porque el cuerpo de un niño en crecimiento no se mide igual que el de un adulto. 📏⚖️",
              "BMI tells you, in simple terms, whether your weight is in a healthy range for your height. "
              "In children and teens, the 'percentile' is also used, comparing you with other kids of your same "
              "age and sex — because a growing child's body isn't measured the same way as an adult's. 📏⚖️"),
              emoji="⚖️", color="#F3E5F5", borde="#8E24AA")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "3.-TMB":
    hoja_header(3, T("Biológicamente, los hombres suelen tener más masa muscular y las mujeres más porcentaje "
                   "de grasa; como el músculo quema más energía, el resultado cambia según el sexo.",
                   "Biologically, men tend to have more muscle mass and women a higher body fat percentage; "
                   "since muscle burns more energy, the result changes based on sex."))

    # --- 1. ¿Qué es la TMB? -------------------------------------------------------------
    st.markdown(T("#### 😴 ¿Qué es la TMB?", "#### 😴 What is BMR?"))
    ilustracion_que_es_tmb()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 2. ¿Cuál es tu resultado? --------------------------------------------------------
    st.markdown(T("#### 🔥 ¿Cuál es tu resultado?", "#### 🔥 What is your result?"))
    tarjeta_resultado_tmb(tmb)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 3. ¿Cómo se calculó? — fórmula horizontal Hombre/Mujer, flechas a la derecha ----
    st.markdown(T("#### 🧪 ¿Cómo se calculó?", "#### 🧪 How was it calculated?"))
    formula_horizontal_tmb(peso, estatura, edad, genero, tmb)
    tarjeta_quien_creo_formula()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 4. ¿Por qué usamos esta fórmula? -------------------------------------------------
    tarjeta_por_que_mifflin()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- Ilustración "central energética" (opcional, muy visual) --------------------------
    central_energetica_tmb(tmb)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 5. ¿Qué módulos usan la TMB? — flujo horizontal ----------------------------------
    flujo_modulos_tmb()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 6. Resumen Inteligente -------------------------------------------------------------
    interpretacion_inteligente_tmb(tmb)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    caja_util("La TMB es la energía mínima que tu cuerpo necesita para vivir si te quedaras todo el día en cama: "
              "respirar, hacer latir tu corazón, mantener tu temperatura, etc. Es la base sobre la que se calcula "
              "TODO lo demás en esta app (cuánto debes comer, cuánto puedes bajar o subir de peso, etc.). 🔥",
              emoji="⚡", color="#FFF3E0", borde="#FB8C00")


    if genero == "Mujer" and embarazada:
        st.divider()
        st.markdown(f"""
        <div style="background:linear-gradient(120deg,#F8ECFB 0%,#FFFFFF 70%);border-radius:24px;padding:20px 26px;
        margin-bottom:14px;border:1px solid rgba(186,104,200,0.18);">
        <h3 style="margin:0;color:#8E24AA;font-weight:800;">🤰 {T("Complemento: TMB durante el Embarazo", "Supplement: BMR during Pregnancy")}</h3>
        <p style="margin:6px 0 0 0;color:#5C6B60;font-size:0.92rem;">{T("El embarazo cambia las necesidades de energía del cuerpo. Aquí ajustamos tu TMB según tu etapa de gestación.", "Pregnancy changes the body's energy needs. Here we adjust your BMR based on your stage of pregnancy.")}</p>
        </div>
        """, unsafe_allow_html=True)
        # =================================================================================
        # RAMA: TMB durante el Embarazo (usa perfil global: peso, estatura, edad, trimestre)
        # Se muestra como COMPLEMENTO de la TMB normal (no la reemplaza), igual que la hoja
        # de RCD se complementa con el ajuste de Clima Chiclayo cuando aplica.
        # =================================================================================
        st.markdown(f"""<div class="formula-badge-row">{formula_badge(
            T("TMB(mujer) + ajuste por trimestre: 1er trim. +0 kcal · 2do trim. +340 kcal/día · 3er trim. +452 kcal/día",
              "BMR(woman) + trimester adjustment: 1st trim. +0 kcal · 2nd trim. +340 kcal/day · 3rd trim. +452 kcal/day"),
            autor="MD Mifflin, ST St Jeor et al. (1990)",
            referencia=T("Ecuación de Mifflin-St Jeor + ajuste gestacional", "Mifflin-St Jeor equation + gestational adjustment"))}</div>""", unsafe_allow_html=True)

        st.markdown(T("""
        <div style="background:#F8ECFB;border-radius:16px;padding:12px 18px;margin-bottom:14px;
        border-left:5px solid #BA68C8;font-size:0.86rem;color:#5C2A6B;">
        📌 Esta sección usa tus datos ya registrados (edad, peso, altura) y el trimestre que seleccionaste
        en "Mis Datos", pensada exclusivamente para mujeres embarazadas.</div>
        """, """
        <div style="background:#F8ECFB;border-radius:16px;padding:12px 18px;margin-bottom:14px;
        border-left:5px solid #BA68C8;font-size:0.86rem;color:#5C2A6B;">
        📌 This section uses the data you already entered (age, weight, height) and the trimester you selected
        in "My Data", designed exclusively for pregnant women.</div>
        """), unsafe_allow_html=True)

        _nombre_disp = nombre_usuario.strip() if nombre_usuario.strip() else T("ti", "you")

        # --- Flujo visual: datos → trimestre → TMB → aporte → resultado ---------------------
        st.markdown(T("#### 🔎 De tus datos a tu resultado", "#### 🔎 From your data to your result"))
        _pasos_emb = [
            ("#5AC8FA", "👩", T("Datos ingresados", "Data entered"), f"{edad:.0f} {T('años','years')} · {peso:.0f} kg · {estatura:.0f} cm"),
            ("#BA68C8", "🤰", T("Trimestre", "Trimester"), trimestre),
            ("#FF9500", "🔥", T("TMB calculada", "Calculated BMR"), f"{tmb_base_gestacion:.0f} kcal/{T('día','day')}"),
            ("#34C759", "🍽️", T("Calorías adicionales", "Additional calories"), f"+{ajuste_gestacion} kcal"),
            ("#FF2D55", "❤️", T("Resultado recomendado", "Recommended result"), f"{tmb:.0f} kcal/{T('día','day')}"),
        ]
        _html_pasos_emb = ['<div style="max-width:520px;margin:0 auto;">']
        for _i, (_bc, _em, _tt, _tx) in enumerate(_pasos_emb):
            _es_ultimo = _i == len(_pasos_emb) - 1
            _fondo_paso = "rgba(255,45,85,0.08)" if _es_ultimo else "#FFFFFF"
            _html_pasos_emb.append(f"""
            <div style="display:flex;align-items:center;gap:14px;background:{_fondo_paso};border-radius:18px;
            padding:12px 18px;box-shadow:0 4px 14px rgba(0,0,0,0.05);border-left:5px solid {_bc};margin-bottom:4px;">
            <div style="font-size:1.5rem;">{_em}</div>
            <div><p style="margin:0;font-weight:800;color:#17301F;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.02em;">{_tt}</p>
            <p style="margin:0;color:#17301F;font-size:1rem;font-weight:700;">{_tx}</p></div>
            </div>""")
            if not _es_ultimo:
                _html_pasos_emb.append('<div style="text-align:center;font-size:1.3rem;color:#BA68C8;opacity:0.7;margin:2px 0;">↓</div>')
        _html_pasos_emb.append('</div>')
        st.markdown(_html_sin_lineas_vacias("".join(_html_pasos_emb)), unsafe_allow_html=True)

        # --- ¿Qué significa este resultado? --------------------------------------------------
        st.markdown(T(f"""
        <div class="bento-card" style="border-left:5px solid #FF2D55;margin-top:16px;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#C2185B;">🤔 ¿Qué significa este resultado?</p>
        <p style="margin:0;color:#3C3C43;line-height:1.55;font-size:0.92rem;">
        Tu cuerpo necesita aproximadamente <b>{tmb:.0f} kcal al día</b> para mantener sus funciones vitales
        (respirar, mantener la temperatura corporal, funcionamiento de órganos, etc.), sin considerar la
        actividad física.</p>
        </div>
        """, f"""
        <div class="bento-card" style="border-left:5px solid #FF2D55;margin-top:16px;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#C2185B;">🤔 What does this result mean?</p>
        <p style="margin:0;color:#3C3C43;line-height:1.55;font-size:0.92rem;">
        Your body needs approximately <b>{tmb:.0f} kcal per day</b> to maintain its vital functions
        (breathing, maintaining body temperature, organ function, etc.), without considering
        physical activity.</p>
        </div>
        """), unsafe_allow_html=True)

        st.write("")

        # --- ¿Por qué cambia según el trimestre? — tres tarjetas -----------------------------
        st.markdown(T("#### 🤰 ¿Por qué cambia según el trimestre?", "#### 🤰 Why does it change by trimester?"))
        _tri_data = [
            ("Primer trimestre", "#4CAF50", "#EAFAEE", "🌱", T("Primer trimestre", "First trimester"),
             T("No suelen necesitarse calorías adicionales. Lo más importante es mantener una alimentación "
             "equilibrada y cubrir todos los nutrientes esenciales.",
             "Additional calories usually aren't needed. The most important thing is to maintain a "
             "balanced diet and cover all essential nutrients.")),
            ("Segundo trimestre", "#FF9500", "#FFF3E5", "👶", T("Segundo trimestre", "Second trimester"),
             T("El bebé comienza un crecimiento más rápido. Generalmente se requieren alrededor de "
             "340 kcal adicionales al día.",
             "The baby begins growing faster. Around 340 additional kcal per day are generally needed.")),
            ("Tercer trimestre", "#FF2D55", "#FFEBF0", "❤️", T("Tercer trimestre", "Third trimester"),
             T("Es la etapa de mayor crecimiento fetal. Las necesidades energéticas aumentan aproximadamente "
             "452 kcal por día.",
             "This is the stage of greatest fetal growth. Energy needs increase by approximately "
             "452 kcal per day.")),
        ]
        _txt_etapa_actual = T("✓ TU ETAPA ACTUAL", "✓ YOUR CURRENT STAGE")
        _cols_tri = st.columns(3)
        for _col, (_clave, _borde, _fondo, _emoji, _titulo, _texto) in zip(_cols_tri, _tri_data):
            _sel = (_clave == trimestre)
            _op = "1" if _sel else "0.45"
            _borde_w = "2.5px solid " + _borde if _sel else f"1px solid {_borde}33"
            _sombra = f"0 10px 24px {_borde}44" if _sel else "0 2px 8px rgba(0,0,0,0.03)"
            with _col:
                st.markdown(f"""
                <div class="bento-card" style="background:{_fondo};border:{_borde_w};text-align:center;
                opacity:{_op};box-shadow:{_sombra};transition:all 0.25s ease;">
                <div style="font-size:1.8rem;margin-bottom:6px;">{_emoji}</div>
                <p style="margin:0 0 6px 0;font-weight:800;color:{_borde};font-size:0.95rem;">{_titulo}</p>
                <p style="margin:0;color:#3C3C43;font-size:0.8rem;line-height:1.45;">{_texto}</p>
                {'<p style="margin:8px 0 0 0;font-weight:800;color:'+_borde+';font-size:0.72rem;">'+_txt_etapa_actual+'</p>' if _sel else ''}
                </div>
                """, unsafe_allow_html=True)

        st.write("")

        # --- ¿Por qué aumentan las calorías? — mini infografía -------------------------------
        st.markdown(T("#### 🔥 ¿Por qué aumentan las calorías?", "#### 🔥 Why do calories increase?"))
        _pasos_porque = [
            ("#BA68C8", "🤰", T("El bebé crece", "The baby grows")),
            ("#FF9500", "🦴", T("Se forman nuevos tejidos", "New tissues form")),
            ("#FF2D55", "❤️", T("Trabaja más el organismo", "The body works harder")),
            ("#FF3B30", "🔥", T("Se necesita más energía", "More energy is needed")),
        ]
        _cols_porque = st.columns(len(_pasos_porque) * 2 - 1)
        for _i, (_bc, _em, _tt) in enumerate(_pasos_porque):
            with _cols_porque[_i * 2]:
                st.markdown(f"""
                <div style="text-align:center;">
                <div style="width:56px;height:56px;border-radius:50%;background:{_bc}22;display:flex;
                align-items:center;justify-content:center;font-size:1.6rem;margin:0 auto 6px auto;">{_em}</div>
                <p style="margin:0;font-size:0.72rem;font-weight:700;color:#17301F;">{_tt}</p>
                </div>
                """, unsafe_allow_html=True)
            if _i < len(_pasos_porque) - 1:
                with _cols_porque[_i * 2 + 1]:
                    st.markdown('<div style="text-align:center;font-size:1.4rem;color:#BA68C8;opacity:0.6;margin-top:16px;">→</div>',
                                unsafe_allow_html=True)

        st.write("")

        # --- Comparación: TMB Base → Aporte → Resultado ---------------------------------------
        st.markdown(T("#### 📊 Antes y después del ajuste", "#### 📊 Before and after the adjustment"))
        _trimestre_disp_lower = T(trimestre.lower(), {"primer trimestre": "1st trimester",
            "segundo trimestre": "2nd trimester", "tercer trimestre": "3rd trimester"}.get(trimestre.lower(), trimestre.lower()))
        st.markdown(T(f"""
        <div class="cp5-glass-flow">
            <div class="cp5-flow-card">
                <div class="cp5-flow-label">🔥 TMB Base</div>
                <div class="cp5-flow-value">{tmb_base_gestacion:.0f} kcal</div>
                <div class="cp5-flow-legend">Tu gasto energético sin ajuste gestacional.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(186,104,200,0.10);border-color:rgba(186,104,200,0.35);">
                <div class="cp5-flow-label">👶 Aporte por embarazo</div>
                <div class="cp5-flow-value" style="color:#8E24AA;">+{ajuste_gestacion} kcal</div>
                <div class="cp5-flow-legend">Energía extra para {trimestre.lower()}.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,45,85,0.12);border-color:rgba(255,45,85,0.4);">
                <div class="cp5-flow-label">❤️ Resultado para {_nombre_disp}</div>
                <div class="cp5-flow-value" style="color:#C2185B;">{tmb:.0f} kcal</div>
                <div class="cp5-flow-legend">Tu gasto energético recomendado hoy.</div>
            </div>
        </div>
        """, f"""
        <div class="cp5-glass-flow">
            <div class="cp5-flow-card">
                <div class="cp5-flow-label">🔥 Base BMR</div>
                <div class="cp5-flow-value">{tmb_base_gestacion:.0f} kcal</div>
                <div class="cp5-flow-legend">Your energy expenditure without gestational adjustment.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(186,104,200,0.10);border-color:rgba(186,104,200,0.35);">
                <div class="cp5-flow-label">👶 Pregnancy contribution</div>
                <div class="cp5-flow-value" style="color:#8E24AA;">+{ajuste_gestacion} kcal</div>
                <div class="cp5-flow-legend">Extra energy for the {_trimestre_disp_lower}.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,45,85,0.12);border-color:rgba(255,45,85,0.4);">
                <div class="cp5-flow-label">❤️ Result for {_nombre_disp}</div>
                <div class="cp5-flow-value" style="color:#C2185B;">{tmb:.0f} kcal</div>
                <div class="cp5-flow-legend">Your recommended energy expenditure today.</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

        st.divider()

        # --- 🍽 Recuerda: prioriza calidad, no solo cantidad ----------------------------------
        st.markdown(T("#### 🍽️ Recuerda", "#### 🍽️ Remember"))
        st.markdown(T("""
        <div class="bento-card" style="border-left:5px solid #FF9500;">
        <p style="margin:0 0 10px 0;color:#3C3C43;font-size:0.9rem;">No todas las calorías son iguales. Durante
        el embarazo es importante priorizar alimentos ricos en:</p>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <span style="background:#FFEBF0;color:#C2185B;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥩 Proteínas</span>
        <span style="background:#E9F8FF;color:#0277BD;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥛 Calcio</span>
        <span style="background:#EAFAEE;color:#137333;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥬 Hierro</span>
        <span style="background:#FFF3E5;color:#B06000;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🍊 Ácido fólico</span>
        <span style="background:#F8ECFB;color:#8E24AA;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🫘 Fibra</span>
        </div>
        <p style="margin:10px 0 0 0;color:#3C3C43;font-size:0.85rem;">No solo aumentar la cantidad de comida.</p>
        </div>
        """, """
        <div class="bento-card" style="border-left:5px solid #FF9500;">
        <p style="margin:0 0 10px 0;color:#3C3C43;font-size:0.9rem;">Not all calories are equal. During
        pregnancy it's important to prioritize foods rich in:</p>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <span style="background:#FFEBF0;color:#C2185B;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥩 Protein</span>
        <span style="background:#E9F8FF;color:#0277BD;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥛 Calcium</span>
        <span style="background:#EAFAEE;color:#137333;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🥬 Iron</span>
        <span style="background:#FFF3E5;color:#B06000;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🍊 Folic acid</span>
        <span style="background:#F8ECFB;color:#8E24AA;padding:6px 14px;border-radius:999px;font-weight:700;font-size:0.82rem;">🫘 Fiber</span>
        </div>
        <p style="margin:10px 0 0 0;color:#3C3C43;font-size:0.85rem;">Not just increasing the amount of food.</p>
        </div>
        """), unsafe_allow_html=True)

        st.write("")

        # --- ¿Qué puedes hacer desde hoy? -----------------------------------------------------
        st.markdown(T("#### ✅ ¿Qué puedes hacer desde hoy?", "#### ✅ What can you do starting today?"))
        _acciones_emb = [
            ("#0277BD", "#E9F8FF", "🥛", T("Consumir lácteos", "Consume dairy")),
            ("#137333", "#EAFAEE", "🥬", T("Incluir verduras diariamente", "Include vegetables daily")),
            ("#1976D2", "#E3F2FD", "🐟", T("Proteínas de buena calidad", "Good quality protein")),
            ("#00B8D9", "#E1FBF9", "💧", T("Mantener buena hidratación", "Stay well hydrated")),
            ("#FF9500", "#FFF3E5", "🚶", T("Actividad física autorizada", "Authorized physical activity")),
        ]
        _cols_acc = st.columns(5)
        for _col, (_borde, _fondo, _emoji, _texto) in zip(_cols_acc, _acciones_emb):
            with _col:
                st.markdown(f"""
                <div class="bento-card" style="background:{_fondo};text-align:center;padding:14px 10px;">
                <div style="font-size:1.4rem;margin-bottom:4px;">{_emoji}</div>
                <p style="margin:0;color:{_borde};font-weight:700;font-size:0.72rem;line-height:1.3;">{_texto}</p>
                </div>
                """, unsafe_allow_html=True)

        st.write("")

        # --- ⚠️ Importante ----------------------------------------------------------------------
        st.markdown(T("""
        <div style="background:#FFF3E5;border-radius:18px;padding:16px 20px;border-left:5px solid #FF9500;">
        <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">⚠️ Importante</p>
        <p style="margin:0;color:#5C4A1E;font-size:0.88rem;line-height:1.5;">
        Las necesidades nutricionales durante el embarazo varían entre cada mujer. Este cálculo es una
        estimación educativa y no reemplaza la evaluación realizada por un obstetra o nutricionista.</p>
        </div>
        """, """
        <div style="background:#FFF3E5;border-radius:18px;padding:16px 20px;border-left:5px solid #FF9500;">
        <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">⚠️ Important</p>
        <p style="margin:0;color:#5C4A1E;font-size:0.88rem;line-height:1.5;">
        Nutritional needs during pregnancy vary from woman to woman. This calculation is an
        educational estimate and does not replace an evaluation by an obstetrician or nutritionist.</p>
        </div>
        """), unsafe_allow_html=True)

        caja_util(T("Durante el embarazo el cuerpo necesita energía extra para que el bebé se desarrolle sanamente. "
                  "Esta calculadora te dice cuántas calorías adicionales necesitas según el trimestre en que estás, "
                  "sin tener que adivinarlo ni arriesgar tu nutrición ni la de tu bebé. 🤰💕",
                  "During pregnancy the body needs extra energy so the baby can develop healthily. "
                  "This calculator tells you how many additional calories you need based on your current trimester, "
                  "without having to guess or risk your nutrition or your baby's. 🤰💕"),
                  emoji="👶", color="#F8ECFB", borde="#BA68C8")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "4.-RCD":
    hoja_header(4, subtitulo=T("El Requerimiento Calórico Diario (RCD) es la cantidad de energía que tu cuerpo "
                             "necesita cada día para funcionar y moverte según tu nivel de actividad actual. "
                             "Se calcula multiplicando tu metabolismo basal (TMB) por un factor de actividad física.",
                             "The Daily Caloric Requirement (DCR) is the amount of energy your body needs "
                             "each day to function and move based on your current activity level. "
                             "It's calculated by multiplying your basal metabolism (BMR) by a physical activity factor."))
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        T("RCD = TMB × Factor de Actividad Física", "DCR = BMR × Physical Activity Factor"),
        autor="OMS / FAO / UNU", referencia=T("Factor de Actividad Física", "Physical Activity Factor"))}</div>""", unsafe_allow_html=True)

    _txt_nivel_actividad = {"Sedentario": T("Sedentario", "Sedentary"), "Ligero": T("Ligero", "Light"),
                             "Moderado": T("Moderado", "Moderate"), "Intenso": T("Intenso", "Intense")}
    _actividad_disp = _txt_nivel_actividad.get(actividad, actividad)

    # ===== 4 tarjetas grandes: TMB → Nivel de actividad → Factor aplicado → RCD =====
    _desc_nivel_rcd = {
        "Sedentario": T("Realizas muy poca actividad física durante el día.", "You do very little physical activity during the day."),
        "Ligero": T("Realizas actividad física ligera durante el día.", "You do light physical activity during the day."),
        "Moderado": T("Realizas actividad física moderada durante el día.", "You do moderate physical activity during the day."),
        "Intenso": T("Realizas actividad física intensa durante el día.", "You do intense physical activity during the day."),
    }
    _tarjetas_grandes_rcd = [
        ("🧍", T("Tu metabolismo basal (TMB)", "Your basal metabolism (BMR)"), f"{tmb:.0f} kcal/{T('día','day')}",
         T("La energía que tu cuerpo necesita incluso en reposo.", "The energy your body needs even at rest."), "#34C759", "#EAFAEE"),
        ("🏃", T("Tu nivel de actividad", "Your activity level"), f"{_actividad_disp}",
         _desc_nivel_rcd.get(actividad, T("Tu nivel de actividad física habitual durante el día.", "Your usual physical activity level during the day.")), "#007AFF", "#EAF3FF"),
        ("📈", T("Factor aplicado", "Factor applied"), f"{factor:.2f}",
         T("Coeficiente utilizado para calcular tu gasto diario.", "Coefficient used to calculate your daily expenditure."), "#AF52DE", "#F6ECFC"),
        ("🔥", T("RCD base (antes del clima)", "Base DCR (before climate)") if vive_en_chiclayo else T("Tu RCD", "Your DCR"), f"{rcd_base:.0f} kcal/{T('día','day')}",
         T("Las calorías aproximadas que necesitas consumir para mantener tu peso.", "The approximate calories you need to eat to maintain your weight."), "#FF9500", "#FFF3E5"),
    ]
    _tarjetas_html_rcd = ""
    for i, (icono_g, titulo_g, valor_g, desc_g, color_g, fondo_g) in enumerate(_tarjetas_grandes_rcd):
        _tarjetas_html_rcd += f"""
        <div style="background:{fondo_g};border:1.5px solid {color_g}33;border-radius:22px;
                    padding:22px 26px;text-align:center;box-shadow:0 6px 18px rgba(0,0,0,0.05);">
            <div style="font-size:2.1rem;">{icono_g}</div>
            <div style="font-size:0.78rem;font-weight:800;color:{color_g};text-transform:uppercase;
                        letter-spacing:0.03em;margin-top:4px;">{titulo_g}</div>
            <div style="font-size:1.8rem;font-weight:900;color:#17301F;margin:6px 0;">{valor_g}</div>
            <div style="font-size:0.85rem;color:#5C6B60;font-style:italic;max-width:420px;margin:0 auto;">
                "{desc_g}"</div>
        </div>"""
        if i < len(_tarjetas_grandes_rcd) - 1:
            _tarjetas_html_rcd += """
        <div style="text-align:center;font-size:1.4rem;color:#B0B8C1;margin:2px 0;">↓</div>"""
    st.markdown(_html_sin_lineas_vacias(f"""<div style="display:flex;flex-direction:column;gap:2px;margin:16px 0 22px 0;">
        {_tarjetas_html_rcd}
    </div>"""), unsafe_allow_html=True)

    # ===== Tarjeta informativa: Nivel · Coeficiente · Sexo · Fórmula · Referencia =====
    _genero_disp = T(genero, "Man" if genero == "Hombre" else "Woman")
    st.markdown(T(f"""
    <div class="bento-card" style="margin-bottom:18px;">
        <div class="bento-eyebrow">Resumen del cálculo aplicado</div>
        <div style="display:flex;flex-wrap:wrap;gap:22px;margin-top:10px;">
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🏃 Nivel de actividad</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{_actividad_disp}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📈 Coeficiente aplicado</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#34C759;">{factor:.2f}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🚻 Sexo del paciente</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{_genero_disp}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📖 Fórmula</div>
                 <div style="font-size:1.0rem;font-weight:700;color:#17301F;">RCD = TMB × Factor de actividad</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📚 Referencia</div>
                 <div style="font-size:1.0rem;font-weight:700;color:#17301F;">Organización Mundial de la Salud (OMS)</div></div>
        </div>
        <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(0,0,0,0.06);
                    font-size:0.85rem;color:#5C6B60;line-height:1.5;">
            Partimos de tu <b>TMB</b> (calculada en la hoja anterior) y la multiplicamos por el <b>coeficiente</b>
            que corresponde a tu sexo y a tu nivel de actividad física. El resultado es tu <b>RCD</b>: la energía
            total que tu cuerpo gasta en un día normal, sumando tanto el reposo como el movimiento.
        </div>
    </div>
    """, f"""
    <div class="bento-card" style="margin-bottom:18px;">
        <div class="bento-eyebrow">Summary of the applied calculation</div>
        <div style="display:flex;flex-wrap:wrap;gap:22px;margin-top:10px;">
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🏃 Activity level</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{_actividad_disp}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📈 Coefficient applied</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#34C759;">{factor:.2f}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🚻 Patient's sex</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{_genero_disp}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📖 Formula</div>
                 <div style="font-size:1.0rem;font-weight:700;color:#17301F;">DCR = BMR × Activity factor</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📚 Reference</div>
                 <div style="font-size:1.0rem;font-weight:700;color:#17301F;">World Health Organization (WHO)</div></div>
        </div>
        <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(0,0,0,0.06);
                    font-size:0.85rem;color:#5C6B60;line-height:1.5;">
            We start from your <b>BMR</b> (calculated on the previous sheet) and multiply it by the <b>coefficient</b>
            that matches your sex and your physical activity level. The result is your <b>DCR</b>: the total
            energy your body spends in a normal day, combining both rest and movement.
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ===== 4 tarjetas de nivel de actividad (reemplazan la tabla), con la seleccionada iluminada =====
    st.markdown(T("#### 🏋️ Nivel de Actividad Física", "#### 🏋️ Physical Activity Level"))
    _NIVELES_RCD = [
        ("Sedentario", "Sedentaria", "🪑", 1.2, "#8E8E93", "#F2F2F7"),
        ("Ligero",     "Ligero",     "🚶", FACTOR_ACTIVIDAD["Ligero"][genero],   "#34C759", "#EAFAEE"),
        ("Moderado",   "Moderada",   "🏃", FACTOR_ACTIVIDAD["Moderada"][genero], "#007AFF", "#EAF3FF"),
        ("Intenso",    "Intensa",    "🔥", FACTOR_ACTIVIDAD["Intensa"][genero],  "#FF3B30", "#FFEDEC"),
    ]
    cols_niv = st.columns(4)
    for col_n, (nombre_niv, clave_niv, icono_niv, factor_niv, color_niv, fondo_niv) in zip(cols_niv, _NIVELES_RCD):
        _es_sel = (clave_niv == actividad)
        _nombre_niv_disp = _txt_nivel_actividad.get(nombre_niv, nombre_niv)
        with col_n:
            _estilo_sel = (f"background:linear-gradient(150deg,{color_niv}22 0%,#FFFFFF 75%);"
                           f"border:2.5px solid {color_niv};box-shadow:0 10px 26px {color_niv}40;transform:translateY(-3px);"
                           if _es_sel else
                           f"background:{fondo_niv};border:1.5px solid rgba(0,0,0,0.05);")
            _badge_sel = (f'<div style="margin-top:8px;background:{color_niv};color:#FFFFFF;font-size:0.68rem;'
                          f'font-weight:800;padding:3px 10px;border-radius:999px;display:inline-block;">✓ {T("SELECCIONADO","SELECTED")}</div>'
                          if _es_sel else "")
            st.markdown(f"""
            <div style="{_estilo_sel}border-radius:20px;padding:16px 14px;text-align:center;transition:all 0.2s ease;">
                <div style="font-size:1.7rem;">{icono_niv}</div>
                <div style="font-weight:800;color:{color_niv};font-size:0.92rem;margin-top:4px;">{_nombre_niv_disp}</div>
                <div style="font-size:0.72rem;color:#8A94A6;font-weight:700;text-transform:uppercase;margin-top:2px;">{T("Factor","Factor")}</div>
                <div style="font-size:1.5rem;font-weight:900;color:{color_niv};letter-spacing:-0.02em;">{factor_niv:.2f}</div>
                {_badge_sel}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ===== ¿Qué significa tu RCD? =====
    st.markdown(T(f"""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#C06000;font-size:1rem;margin-bottom:6px;">💡 ¿Qué significa tu RCD?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            Si consumes aproximadamente 🔥 <b>{rcd_base:.0f} kcal al día</b> y mantienes el mismo nivel de actividad
            física, ⚖️ <b>tu peso tenderá a mantenerse estable</b>. Este es tu punto de equilibrio calórico: comes
            la misma energía que gastas, así que no ganas ni pierdes peso.
        </div>
    </div>
    """, f"""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#C06000;font-size:1rem;margin-bottom:6px;">💡 What does your DCR mean?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            If you eat approximately 🔥 <b>{rcd_base:.0f} kcal per day</b> and keep the same activity
            level, ⚖️ <b>your weight will tend to stay stable</b>. This is your caloric balance point: you eat
            the same energy you burn, so you neither gain nor lose weight.
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ===== ¿Qué representa el factor de actividad? =====
    st.markdown(T(f"""
    <div style="background:#EAF3FF;border-left:5px solid #007AFF;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#0B4DA8;font-size:1rem;margin-bottom:6px;">📈 ¿Qué representa el factor de actividad?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            Mientras más te mueves durante el día, más energía necesita tu cuerpo. Por eso el cálculo utiliza un
            coeficiente que aumenta el gasto calórico según tu nivel de actividad física: multiplica tu TMB para
            reflejar la energía extra que gastas al trabajar, caminar, hacer ejercicio y todas tus actividades diarias.
        </div>
    </div>
    """, f"""
    <div style="background:#EAF3FF;border-left:5px solid #007AFF;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#0B4DA8;font-size:1rem;margin-bottom:6px;">📈 What does the activity factor represent?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            The more you move during the day, the more energy your body needs. That's why the calculation uses a
            coefficient that increases caloric expenditure based on your physical activity level: it multiplies your BMR to
            reflect the extra energy you spend working, walking, exercising, and doing all your daily activities.
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ===== ¿Quién recomienda este método? =====
    st.markdown(T("""
    <div style="background:#EAFAEE;border-left:5px solid #34C759;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#1E5631;font-size:1rem;margin-bottom:10px;">📚 ¿Quién recomienda este método?</div>
        <div style="display:flex;flex-direction:column;gap:10px;">
            <div><b style="color:#17301F;">🇺🇳 Organización Mundial de la Salud (OMS)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Establece las pautas internacionales sobre los
                requerimientos de energía y nutrición que se usan como referencia en esta app.</div></div>
            <div><b style="color:#17301F;">🌾 FAO (Organización de las Naciones Unidas para la Alimentación y la Agricultura)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Junto con la OMS, elabora los reportes técnicos con
                las tablas de necesidades energéticas humanas usadas a nivel mundial.</div></div>
            <div><b style="color:#17301F;">🎓 UNU (Universidad de las Naciones Unidas)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Colabora con la OMS y la FAO en la investigación y
                validación científica de los factores de actividad física utilizados en este cálculo.</div></div>
        </div>
    </div>
    """, """
    <div style="background:#EAFAEE;border-left:5px solid #34C759;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#1E5631;font-size:1rem;margin-bottom:10px;">📚 Who recommends this method?</div>
        <div style="display:flex;flex-direction:column;gap:10px;">
            <div><b style="color:#17301F;">🇺🇳 World Health Organization (WHO)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Sets the international guidelines on
                energy and nutrition requirements used as a reference in this app.</div></div>
            <div><b style="color:#17301F;">🌾 FAO (Food and Agriculture Organization of the United Nations)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Together with WHO, produces the technical reports with
                the human energy needs tables used worldwide.</div></div>
            <div><b style="color:#17301F;">🎓 UNU (United Nations University)</b>
                <div style="color:#5C6B60;font-size:0.85rem;">Collaborates with WHO and FAO on the research and
                scientific validation of the physical activity factors used in this calculation.</div></div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ===== Diagrama del cálculo: TMB → × Factor → = RCD =====
    st.markdown(T("#### 🧮 Diagrama del Cálculo", "#### 🧮 Calculation Diagram"))
    st.markdown(T(f"""
    <div class="cp5-glass-flow" style="margin-top:6px;">
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">⚡ TMB</div>
            <div class="cp5-flow-value">{tmb:.2f}</div>
            <div class="cp5-flow-legend">kcal/día — tu gasto en reposo (Hoja 3)</div>
        </div>
        <div class="cp5-flow-arrow">×</div>
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">🏃 Factor de actividad</div>
            <div class="cp5-flow-value">{factor:.2f}</div>
            <div class="cp5-flow-legend">{actividad} · {genero}</div>
        </div>
        <div class="cp5-flow-arrow">=</div>
        <div class="cp5-flow-card" style="background:rgba(255,149,0,0.12);border-color:rgba(255,149,0,0.35);">
            <div class="cp5-flow-label">🔥 RCD base</div>
            <div class="cp5-flow-value" style="color:#E67E22;">{rcd_base:.2f}</div>
            <div class="cp5-flow-legend">kcal/día — antes del ajuste por clima</div>
        </div>
    </div>
    """, f"""
    <div class="cp5-glass-flow" style="margin-top:6px;">
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">⚡ BMR</div>
            <div class="cp5-flow-value">{tmb:.2f}</div>
            <div class="cp5-flow-legend">kcal/day — your resting expenditure (Sheet 3)</div>
        </div>
        <div class="cp5-flow-arrow">×</div>
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">🏃 Activity factor</div>
            <div class="cp5-flow-value">{factor:.2f}</div>
            <div class="cp5-flow-legend">{_actividad_disp} · {_genero_disp}</div>
        </div>
        <div class="cp5-flow-arrow">=</div>
        <div class="cp5-flow-card" style="background:rgba(255,149,0,0.12);border-color:rgba(255,149,0,0.35);">
            <div class="cp5-flow-label">🔥 Base DCR</div>
            <div class="cp5-flow-value" style="color:#E67E22;">{rcd_base:.2f}</div>
            <div class="cp5-flow-legend">kcal/day — before climate adjustment</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ===== Fórmula desarrollada, con los números reales del usuario =====
    st.markdown(f"""
    <div style="text-align:center;background:#F7F9F7;border-radius:18px;padding:16px 20px;margin-top:16px;
                font-family:var(--font-round);border:1px solid rgba(0,0,0,0.04);">
        <span style="font-size:1.3rem;font-weight:800;color:#17301F;">{tmb:.2f}</span>
        <span style="font-size:1.1rem;color:#8A94A6;margin:0 10px;">×</span>
        <span style="font-size:1.3rem;font-weight:800;color:#34C759;">{factor:.2f}</span>
        <span style="font-size:1.1rem;color:#8A94A6;margin:0 10px;">=</span>
        <span style="font-size:1.5rem;font-weight:900;color:#E67E22;">{rcd_base:.2f} kcal</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ===== Ajuste por clima cálido de Chiclayo (solo si el usuario vive en Chiclayo) =====
    if vive_en_chiclayo:
        _ajuste_kcal = rcd_base - rcd
        st.markdown(f"""<div class="formula-badge-row">{formula_badge(
            "RCD = RCD_base × 0.95",
            referencia=T("Corrección Térmica de Clima Cálido — factor 5% por temperatura ambiental promedio",
                          "Warm Climate Thermal Correction — 5% factor for average ambient temperature"))}</div>""",
            unsafe_allow_html=True)

        st.markdown(T("""
        <div style="background:linear-gradient(120deg,#FFF6E0 0%,#FFFFFF 75%);border-radius:22px;
        padding:20px 24px;margin:6px 0 18px 0;border:1px solid rgba(255,179,0,0.25);
        box-shadow:0 6px 18px rgba(255,179,0,0.10);">
        <p style="margin:0 0 8px 0;font-weight:800;color:#B06000;font-size:1.05rem;">
        🌤️ ¿El clima influye en las calorías que gasta tu cuerpo?</p>
        <p style="margin:0;color:#5C4A1E;line-height:1.55;">
        <b>Sí, aunque el cambio suele ser pequeño.</b> En lugares cálidos como Chiclayo, tu cuerpo necesita
        producir un poco menos de calor interno para mantener su temperatura, por lo que el gasto energético
        diario puede disminuir ligeramente. Eso es justo lo que este cálculo tiene en cuenta.</p>
        </div>
        """, """
        <div style="background:linear-gradient(120deg,#FFF6E0 0%,#FFFFFF 75%);border-radius:22px;
        padding:20px 24px;margin:6px 0 18px 0;border:1px solid rgba(255,179,0,0.25);
        box-shadow:0 6px 18px rgba(255,179,0,0.10);">
        <p style="margin:0 0 8px 0;font-weight:800;color:#B06000;font-size:1.05rem;">
        🌤️ Does climate affect the calories your body burns?</p>
        <p style="margin:0;color:#5C4A1E;line-height:1.55;">
        <b>Yes, although the change is usually small.</b> In warm places like Chiclayo, your body needs to
        produce slightly less internal heat to maintain its temperature, so daily energy expenditure
        can decrease slightly. That's exactly what this calculation takes into account.</p>
        </div>
        """), unsafe_allow_html=True)

        st.markdown(T("#### 📊 De tu cálculo general al resultado para Chiclayo", "#### 📊 From your general calculation to the result for Chiclayo"))
        st.markdown(T(f"""
        <div class="cp5-glass-flow">
            <div class="cp5-flow-card">
                <div class="cp5-flow-label">🌍 RCD base</div>
                <div class="cp5-flow-value">{rcd_base:.0f} kcal</div>
                <div class="cp5-flow-legend">Tu gasto diario sin considerar el clima local.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,179,0,0.10);border-color:rgba(255,179,0,0.35);">
                <div class="cp5-flow-label">☀️ Ajuste por clima cálido</div>
                <div class="cp5-flow-value" style="color:#B06000;">−{_ajuste_kcal:.0f} kcal</div>
                <div class="cp5-flow-legend">Tu cuerpo produce un poco menos de calor interno.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,149,0,0.12);border-color:rgba(255,149,0,0.4);">
                <div class="cp5-flow-label">📍 Resultado para Chiclayo</div>
                <div class="cp5-flow-value" style="color:#E67E22;">{rcd:.0f} kcal</div>
                <div class="cp5-flow-legend">Tu gasto energético ya ajustado al clima. ☀️</div>
            </div>
        </div>
        """, f"""
        <div class="cp5-glass-flow">
            <div class="cp5-flow-card">
                <div class="cp5-flow-label">🌍 Base DCR</div>
                <div class="cp5-flow-value">{rcd_base:.0f} kcal</div>
                <div class="cp5-flow-legend">Your daily expenditure without considering local climate.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,179,0,0.10);border-color:rgba(255,179,0,0.35);">
                <div class="cp5-flow-label">☀️ Warm climate adjustment</div>
                <div class="cp5-flow-value" style="color:#B06000;">−{_ajuste_kcal:.0f} kcal</div>
                <div class="cp5-flow-legend">Your body produces slightly less internal heat.</div>
            </div>
            <div class="cp5-flow-arrow">→</div>
            <div class="cp5-flow-card" style="background:rgba(255,149,0,0.12);border-color:rgba(255,149,0,0.4);">
                <div class="cp5-flow-label">📍 Result for Chiclayo</div>
                <div class="cp5-flow-value" style="color:#E67E22;">{rcd:.0f} kcal</div>
                <div class="cp5-flow-legend">Your energy expenditure already adjusted for climate. ☀️</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

        col_signif, col_duda = st.columns(2)
        with col_signif:
            st.markdown(T("""
            <div class="bento-card" style="border-left:5px solid #FFB300;">
            <p style="margin:0 0 6px 0;font-weight:800;color:#B06000;">🤔 ¿Qué significa esto?</p>
            <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
            Debido al clima cálido de Chiclayo, tu cuerpo gasta ligeramente menos energía para mantener
            su temperatura. Por eso el cálculo ajusta aproximadamente un <b>5%</b> de tu gasto energético diario.</p>
            </div>
            """, """
            <div class="bento-card" style="border-left:5px solid #FFB300;">
            <p style="margin:0 0 6px 0;font-weight:800;color:#B06000;">🤔 What does this mean?</p>
            <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
            Because of Chiclayo's warm climate, your body spends slightly less energy maintaining
            its temperature. That's why the calculation adjusts approximately <b>5%</b> of your daily energy expenditure.</p>
            </div>
            """), unsafe_allow_html=True)
        with col_duda:
            st.markdown(T("""
            <div class="bento-card" style="border-left:5px solid #34C759;">
            <p style="margin:0 0 6px 0;font-weight:800;color:#137333;">❓ ¿Debo comer menos porque hace calor?</p>
            <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
            <b>No necesariamente.</b> Este ajuste solo mejora la precisión del cálculo. La diferencia suele ser
            pequeña y no significa que debas dejar de alimentarte ni hacer dietas por vivir en un clima cálido.</p>
            </div>
            """, """
            <div class="bento-card" style="border-left:5px solid #34C759;">
            <p style="margin:0 0 6px 0;font-weight:800;color:#137333;">❓ Should I eat less because it's hot?</p>
            <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
            <b>Not necessarily.</b> This adjustment only improves the accuracy of the calculation. The difference is usually
            small and doesn't mean you should stop eating properly or diet just because you live in a warm climate.</p>
            </div>
            """), unsafe_allow_html=True)

        st.write("")

        st.markdown(T("#### 🌴 ¿Cómo aprovechar este conocimiento?", "#### 🌴 How to make the most of this knowledge?"))
        col_h, col_c, col_a = st.columns(3)
        _tarjetas_clima = [
            (col_h, "#5AC8FA", "#E9F8FF", "💧", T("Mantente hidratado", "Stay hydrated"),
             T("Las altas temperaturas aumentan la pérdida de agua mediante el sudor.",
               "High temperatures increase water loss through sweat.")),
            (col_c, "#34C759", "#EAFAEE", "🥗", T("Prefiere comidas ligeras", "Prefer light meals"),
             T("Las frutas y verduras ayudan a mantener una buena hidratación.",
               "Fruits and vegetables help maintain good hydration.")),
            (col_a, "#FF9500", "#FFF3E5", "🚶", T("Sigue activo", "Stay active"),
             T("Aunque haga calor, caminar y hacer actividad física sigue siendo importante para tu salud.",
               "Even in hot weather, walking and physical activity remain important for your health.")),
        ]
        for _col, _borde, _fondo, _emoji, _titulo, _texto in _tarjetas_clima:
            with _col:
                st.markdown(f"""
                <div class="bento-card" style="background:{_fondo};border:1px solid {_borde}33;text-align:center;height:auto;">
                <div style="font-size:1.8rem;margin-bottom:6px;">{_emoji}</div>
                <p style="margin:0 0 6px 0;font-weight:800;color:{_borde};font-size:0.95rem;">{_titulo}</p>
                <p style="margin:0;color:#3C3C43;font-size:0.82rem;line-height:1.45;">{_texto}</p>
                </div>
                """, unsafe_allow_html=True)

        st.write("")

        st.markdown(T("#### ☀️ ¿Cómo responde tu cuerpo cuando hace calor?", "#### ☀️ How does your body respond when it's hot?"))
        _pasos_calor = [
            ("#FFB300", "☀️", T("Hace más calor", "It gets hotter"), T("La temperatura ambiental sube en tu entorno.", "The ambient temperature rises around you.")),
            ("#5AC8FA", "💧", T("Sudas más", "You sweat more"), T("Tu piel libera calor a través del sudor.", "Your skin releases heat through sweat.")),
            ("#FF3B30", "❤️", T("Tu cuerpo trabaja para mantener su temperatura", "Your body works to maintain its temperature"), T("El organismo regula su termostato interno.", "Your body regulates its internal thermostat.")),
            ("#34C759", "🍉", T("Necesitas hidratarte correctamente", "You need to hydrate properly"), T("Repones el agua que pierdes con el calor.", "You replenish the water you lose from the heat.")),
            ("#FF9500", "📊", T("El cálculo ajusta ligeramente tu gasto", "The calculation slightly adjusts your expenditure"), T("Aproximadamente un 5% menos de energía diaria.", "Approximately 5% less daily energy.")),
        ]
        _html_pasos = ['<div style="max-width:520px;margin:0 auto;">']
        for _i, (_bc, _em, _tt, _tx) in enumerate(_pasos_calor):
            _html_pasos.append(f"""
            <div style="display:flex;align-items:center;gap:14px;background:#FFFFFF;border-radius:18px;
            padding:12px 18px;box-shadow:0 4px 14px rgba(0,0,0,0.05);border-left:5px solid {_bc};margin-bottom:4px;">
            <div style="font-size:1.5rem;">{_em}</div>
            <div><p style="margin:0;font-weight:800;color:#17301F;font-size:0.9rem;">{_tt}</p>
            <p style="margin:0;color:#5C6B60;font-size:0.78rem;">{_tx}</p></div>
            </div>""")
            if _i < len(_pasos_calor) - 1:
                _html_pasos.append('<div style="text-align:center;font-size:1.3rem;color:#FFB300;opacity:0.7;margin:2px 0;">↓</div>')
        _html_pasos.append('</div>')
        st.markdown(_html_sin_lineas_vacias("".join(_html_pasos)), unsafe_allow_html=True)

        st.divider()

        st.markdown(T("""
        <div style="background:#FFF6E0;border-radius:18px;padding:16px 20px;margin-bottom:10px;
        border-left:5px solid #FFB300;">
        <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">📖 Base científica</p>
        <p style="margin:0;color:#5C4A1E;font-size:0.9rem;line-height:1.5;">
        Este cálculo utiliza información sobre adaptación fisiológica al clima cálido descrita por organismos
        internacionales como la FAO y estudios sobre gasto energético humano.</p>
        </div>
        """, """
        <div style="background:#FFF6E0;border-radius:18px;padding:16px 20px;margin-bottom:10px;
        border-left:5px solid #FFB300;">
        <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">📖 Scientific basis</p>
        <p style="margin:0;color:#5C4A1E;font-size:0.9rem;line-height:1.5;">
        This calculation uses information on physiological adaptation to warm climates described by
        international bodies such as the FAO and studies on human energy expenditure.</p>
        </div>
        """), unsafe_allow_html=True)
        recursos_externos(4, [
            (T("📄 Ver referencias (FAO/OMS/UNU)", "📄 View references (FAO/WHO/UNU)"), "https://www.fao.org/"),
            (T("☀️ Clima de Chiclayo (Senamhi)", "☀️ Chiclayo climate (Senamhi)"), "https://www.senamhi.gob.pe/"),
        ])
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ===== Resultado final destacado, con fondo degradado naranja-rojo =====
    _sub_hero_rcd = (T(f"Factor aplicado: <b>{actividad}</b> ({factor:.2f}) · Sexo: <b>{genero}</b>",
                        f"Factor applied: <b>{_actividad_disp}</b> ({factor:.2f}) · Sex: <b>{_genero_disp}</b>")
                      + (T(" · ☀️ Ajuste de clima Chiclayo (−5%) aplicado", " · ☀️ Chiclayo climate adjustment (−5%) applied") if vive_en_chiclayo else ""))
    st.markdown(T(f"""
    <div style="position:relative;overflow:hidden;background:linear-gradient(120deg,#FF9500 0%,#FF6B35 55%,#FF3B30 100%);
                border-radius:26px;padding:30px 34px;text-align:center;color:#FFFFFF;
                box-shadow:0 18px 40px rgba(255,111,0,0.35);">
        <div style="position:absolute;right:18px;top:50%;transform:translateY(-50%);font-size:5rem;opacity:0.16;">🔥</div>
        <div style="font-size:0.82rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.95;">
            Resultado Final · Requerimiento Calórico Diario</div>
        <div style="font-size:2.6rem;font-weight:900;letter-spacing:-0.02em;margin:8px 0;">🔥 {rcd:.2f} <span style="font-size:1.2rem;font-weight:700;">kcal/día</span></div>
        <div style="font-size:0.86rem;opacity:0.92;">{_sub_hero_rcd}</div>
    </div>
    """, f"""
    <div style="position:relative;overflow:hidden;background:linear-gradient(120deg,#FF9500 0%,#FF6B35 55%,#FF3B30 100%);
                border-radius:26px;padding:30px 34px;text-align:center;color:#FFFFFF;
                box-shadow:0 18px 40px rgba(255,111,0,0.35);">
        <div style="position:absolute;right:18px;top:50%;transform:translateY(-50%);font-size:5rem;opacity:0.16;">🔥</div>
        <div style="font-size:0.82rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.95;">
            Final Result · Daily Caloric Requirement</div>
        <div style="font-size:2.6rem;font-weight:900;letter-spacing:-0.02em;margin:8px 0;">🔥 {rcd:.2f} <span style="font-size:1.2rem;font-weight:700;">kcal/day</span></div>
        <div style="font-size:0.86rem;opacity:0.92;">{_sub_hero_rcd}</div>
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    with st.expander(T("📋 Ver tabla completa de factores de actividad (Hombres / Mujeres)",
                        "📋 View full activity factor table (Men / Women)")):
        _FILAS_FACTOR_TABLA = [
            (T("🪑 Sedentaria", "🪑 Sedentary"), "#8E8E93", "#F2F2F7", 1.2, 1.2, "Sedentaria"),
            (T("🚶 Ligero", "🚶 Light"),     "#34C759", "#EAFAEE", FACTOR_ACTIVIDAD["Ligero"]["Hombre"],   FACTOR_ACTIVIDAD["Ligero"]["Mujer"], "Ligero"),
            (T("🏃 Moderada", "🏃 Moderate"),   "#007AFF", "#EAF3FF", FACTOR_ACTIVIDAD["Moderada"]["Hombre"], FACTOR_ACTIVIDAD["Moderada"]["Mujer"], "Moderada"),
            (T("🔥 Intensa", "🔥 Intense"),    "#FF3B30", "#FFEDEC", FACTOR_ACTIVIDAD["Intensa"]["Hombre"],  FACTOR_ACTIVIDAD["Intensa"]["Mujer"], "Intensa"),
        ]
        _filas_tabla_html = ""
        for _nom, _col, _fon, _fh, _fm, _clave_orig in _FILAS_FACTOR_TABLA:
            _es_fila_activa = (_clave_orig == actividad)
            _resalte = f"box-shadow:inset 0 0 0 2px {_col};" if _es_fila_activa else ""
            _filas_tabla_html += f"""
            <tr style="background:{_fon};{_resalte}">
                <td style="text-align:left;font-weight:800;color:{_col};padding:12px 16px;border-radius:12px 0 0 12px;">{_nom}{' ⭐' if _es_fila_activa else ''}</td>
                <td style="text-align:center;font-weight:800;color:#1976D2;padding:12px 16px;">♂ {_fh:.2f}</td>
                <td style="text-align:center;font-weight:800;color:#C2185B;padding:12px 16px;border-radius:0 12px 12px 0;">♀ {_fm:.2f}</td>
            </tr>"""
        _th_actividad = T("Actividad", "Activity")
        _th_hombres = T("Hombres", "Men")
        _th_mujeres = T("Mujeres", "Women")
        st.markdown(_html_sin_lineas_vacias(f"""
        <table style="width:100%;border-collapse:separate;border-spacing:0 8px;font-family:var(--font-round);">
            <thead><tr>
                <th style="text-align:left;padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">{_th_actividad}</th>
                <th style="padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">{_th_hombres}</th>
                <th style="padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">{_th_mujeres}</th>
            </tr></thead>
            <tbody>{_filas_tabla_html}</tbody>
        </table>
        """), unsafe_allow_html=True)

    caja_util(T("Este es el número más importante de toda la app: son las calorías reales que gastas en un día "
              "normal, sumando tu TMB (Hoja 3) más el movimiento que haces según tu nivel de actividad. "
              "Es tu 'punto de equilibrio' calórico. 🏃‍♀️🔥",
              "This is the most important number in the whole app: it's the real calories you burn on a "
              "normal day, adding your BMR (Sheet 3) to the movement you do based on your activity level. "
              "It's your caloric 'balance point'. 🏃‍♀️🔥"),
              emoji="🔥", color="#E8F5E9", borde="#43A047")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "5.-CONTROL DE PESO":
    hoja_header(5, "En un solo vistazo podrás entender cuánto necesitas, cuál es tu objetivo "
                   "y cuántas calorías debes consumir cada día.")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Bajar: RCD_Final = RCD×(1−%déficit)  |  Mantener: RCD_Final = RCD  |  "
        "Subir: RCD_Final = RCD×(1+%superávit)",
        autor="OMS / FAO / UNU", referencia="Ajuste de Control de Peso")}</div>""", unsafe_allow_html=True)

    _diferencia_rcd = rcd_final - rcd
    _signo_dif = "" if abs(_diferencia_rcd) < 1 else ("+" if _diferencia_rcd > 0 else "")
    _obj_emoji = {"Bajar de peso": "📉", "Subir de peso": "📈", "Mantenerse": "⚖️"}[objetivo]
    _obj_color = {"Bajar de peso": "#FF9500", "Subir de peso": "#007AFF", "Mantenerse": "#34C759"}[objetivo]

    # ===== 1. HERO PRINCIPAL =====
    st.markdown(f"""
    <div style="background:linear-gradient(120deg,#1E5631 0%,#2E7D32 55%,#4CAF50 100%);border-radius:26px;
                padding:26px 30px;color:#FFFFFF;text-align:center;margin-bottom:18px;
                box-shadow:0 16px 36px rgba(30,86,49,0.28);">
        <div style="font-size:1.9rem;font-weight:900;letter-spacing:-0.01em;">🎯 Tu Plan de Control de Peso</div>
        <div style="font-size:1rem;opacity:0.95;max-width:640px;margin:8px auto 0 auto;line-height:1.5;">
            "No es una dieta. Es un ajuste inteligente de tus calorías para ayudarte a alcanzar tu objetivo,
            {_nombre_saludo}, de forma segura."
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== 2. FLUJO: RCD inicial → Objetivo → Ajuste → RCD objetivo (4 tarjetas grandes) =====
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;gap:6px;max-width:520px;margin:0 auto;">
        <div style="background:#EAFAEE;border:2px solid #34C759;border-radius:20px;padding:16px 20px;text-align:center;">
            <div style="font-size:0.78rem;font-weight:800;color:#1E5631;text-transform:uppercase;">🟢 RCD Inicial</div>
            <div style="font-size:2rem;font-weight:900;color:#1E5631;letter-spacing:-0.02em;">{rcd:.0f} <span style="font-size:1rem;font-weight:700;">kcal/día</span></div>
            <div style="font-size:0.78rem;color:#3E7050;">Las calorías que tu cuerpo necesita para mantener tu peso.</div>
        </div>
        <div style="text-align:center;font-size:1.4rem;color:#B0B8C1;">↓</div>
        <div style="background:{_obj_color}1A;border:2px solid {_obj_color};border-radius:20px;padding:14px 20px;text-align:center;">
            <div style="font-size:0.78rem;font-weight:800;color:{_obj_color};text-transform:uppercase;">Objetivo seleccionado</div>
            <div style="font-size:1.5rem;font-weight:900;color:{_obj_color};">{_obj_emoji} {objetivo}</div>
        </div>
        <div style="text-align:center;font-size:1.4rem;color:#B0B8C1;">↓</div>
        <div style="background:#EAF3FF;border:2px solid #007AFF;border-radius:20px;padding:14px 20px;text-align:center;">
            <div style="font-size:0.78rem;font-weight:800;color:#007AFF;text-transform:uppercase;">🔵 Ajuste aplicado</div>
            <div style="font-size:1.5rem;font-weight:900;color:#007AFF;">
                {("-" if objetivo == "Bajar de peso" else ("+" if objetivo == "Subir de peso" else "")) + f"{ajuste_aplicado*100:.0f}%" if ajuste_aplicado else "0% (sin cambio)"}
            </div>
        </div>
        <div style="text-align:center;font-size:1.4rem;color:#B0B8C1;">↓</div>
        <div style="background:#FFEBF0;border:2px solid #FF2D55;border-radius:20px;padding:18px 20px;text-align:center;">
            <div style="font-size:0.78rem;font-weight:800;color:#D81B60;text-transform:uppercase;">🎯 RCD Objetivo</div>
            <div style="font-size:2.3rem;font-weight:900;color:#D81B60;letter-spacing:-0.02em;">{rcd_final:.0f} <span style="font-size:1.1rem;font-weight:700;">kcal/día</span></div>
            <div style="font-size:0.78rem;color:#9C1948;">Las calorías recomendadas para cumplir tu meta.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if _ico_recortada_por_tmb:
        st.warning(f"⚠️ Tu ajuste se limitó automáticamente para nunca bajar de tu TMB ({tmb:.0f} kcal/día), "
                   "el mínimo vital de tu cuerpo. Por eso tu RCD Objetivo no bajó más de ahí.")

    st.divider()

    # ===== 3. ¿QUÉ CAMBIÓ? — comparación Antes / Ahora / Diferencia con barras =====
    st.markdown("#### 📊 Comparación de tu plan")
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown(f"""<div class="bento-card" style="text-align:center;">
            <div class="bento-eyebrow">Antes</div>
            <div style="font-size:1.7rem;font-weight:900;color:#17301F;">{rcd:.0f} kcal</div>
        </div>""", unsafe_allow_html=True)
    with _c2:
        st.markdown(f"""<div class="bento-card" style="text-align:center;">
            <div class="bento-eyebrow">Ahora</div>
            <div style="font-size:1.7rem;font-weight:900;color:#D81B60;">{rcd_final:.0f} kcal</div>
        </div>""", unsafe_allow_html=True)
    with _c3:
        st.markdown(f"""<div class="bento-card" style="text-align:center;">
            <div class="bento-eyebrow">Diferencia</div>
            <div style="font-size:1.7rem;font-weight:900;color:{_obj_color};">{_signo_dif}{_diferencia_rcd:.0f} kcal</div>
        </div>""", unsafe_allow_html=True)

    _max_barra = max(rcd, rcd_final, 1)
    _pct_antes = max(6, round(rcd / _max_barra * 100))
    _pct_ahora = max(6, round(rcd_final / _max_barra * 100))
    st.markdown(f"""
    <div style="margin-top:16px;">
        <div style="font-size:0.82rem;font-weight:700;color:#5C6B60;margin-bottom:4px;">Calorías necesarias (RCD)</div>
        <div style="height:26px;border-radius:999px;background:#EEF1F4;overflow:hidden;">
            <div style="width:{_pct_antes}%;height:100%;border-radius:999px;background:linear-gradient(90deg,#34C759,#1E5631);
                        display:flex;align-items:center;padding-left:12px;color:white;font-weight:800;font-size:0.8rem;">{rcd:.0f} kcal</div>
        </div>
        <div style="font-size:0.82rem;font-weight:700;color:#5C6B60;margin:12px 0 4px 0;">Calorías objetivo (RCD Objetivo)</div>
        <div style="height:26px;border-radius:999px;background:#EEF1F4;overflow:hidden;">
            <div style="width:{_pct_ahora}%;height:100%;border-radius:999px;background:linear-gradient(90deg,#FF2D55,#D81B60);
                        display:flex;align-items:center;padding-left:12px;color:white;font-weight:800;font-size:0.8rem;">{rcd_final:.0f} kcal</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ===== 4. EXPLICACIÓN SENCILLA =====
    st.markdown("#### 💬 ¿Qué significa este cambio?")
    if objetivo == "Bajar de peso":
        _texto_expl = (f"Para alcanzar tu objetivo de **bajar de peso**, se aplicó un déficit calórico del "
                        f"**{ajuste_aplicado*100:.0f}%**. Este ajuste favorece la pérdida gradual de grasa "
                        "corporal sin reducir tu consumo por debajo del mínimo necesario para el funcionamiento "
                        "del organismo.")
    elif objetivo == "Subir de peso":
        _texto_expl = (f"Para alcanzar tu objetivo de **subir de peso**, se aplicó un superávit calórico del "
                        f"**{ajuste_aplicado*100:.0f}%**. Este ajuste le da a tu cuerpo la energía extra "
                        "necesaria para construir tejido nuevo de forma controlada.")
    else:
        _texto_expl = ("Para **mantener tu peso**, tu RCD Objetivo es igual a tu RCD Inicial: consumirás "
                        "aproximadamente lo mismo que gastas, sin déficit ni superávit.")
    st.markdown(f"""<div class="info3-card">{_texto_expl}</div>""", unsafe_allow_html=True)

    st.divider()

    # ===== 5. TU OBJETIVO EXPLICADO (reemplaza el panel de misión) =====
    st.markdown("#### 🧭 Tu objetivo explicado")
    st.caption("Según el objetivo elegido, cambia el comportamiento de tus calorías.")
    _oc1, _oc2, _oc3 = st.columns(3)
    _objetivos_info = [
        (_oc1, "Bajar de peso", "📉", "#FF9500", "#FFF3E0",
         "El cuerpo utilizará parte de la grasa almacenada como fuente de energía."),
        (_oc2, "Mantenerse", "⚖️", "#34C759", "#EAFAEE",
         "Consumirás aproximadamente las mismas calorías que gastas."),
        (_oc3, "Subir de peso", "📈", "#007AFF", "#EAF3FF",
         "Consumirás más energía para favorecer el crecimiento y desarrollo corporal."),
    ]
    for _col_o, _tit_o, _ic_o, _col_hex_o, _fon_o, _desc_o in _objetivos_info:
        _es_sel_o = (_tit_o == objetivo)
        with _col_o:
            _estilo_o = (f"border:2.5px solid {_col_hex_o};box-shadow:0 8px 20px {_col_hex_o}40;"
                         if _es_sel_o else "border:1px solid rgba(0,0,0,0.06);")
            st.markdown(f"""
            <div style="background:{_fon_o};border-radius:18px;padding:16px 14px;height:100%;{_estilo_o}">
                <div style="font-size:1.8rem;text-align:center;">{_ic_o}</div>
                <div style="font-weight:800;color:{_col_hex_o};font-size:0.9rem;text-align:center;margin:4px 0;">{_tit_o}{' ✓' if _es_sel_o else ''}</div>
                <div style="font-size:0.78rem;color:#3C3C43;text-align:center;">{_desc_o}</div>
            </div>
            """, unsafe_allow_html=True)

    st.info("🛡️ **¿Es seguro?** Sí — tu RCD Objetivo nunca baja de tu TMB (el mínimo vital de tu cuerpo), así que "
            "siempre recibes la energía necesaria para funcionar bien. Este ajuste no reemplaza la evaluación de "
            "un profesional de salud.")

    st.divider()

    # ===== 6. Distribución de macronutrientes (se conserva) =====
    _build_panel_macros_creativo(gr_prot, gr_gras, gr_carb, peso, objetivo)

    caja_util("Esta sección transforma tu objetivo (bajar, mantener o subir de peso) en un requerimiento "
              "calórico diario personalizado. Así sabes exactamente cuántas calorías consumir para alcanzar "
              "tu meta de forma segura, respetando siempre las necesidades mínimas de tu organismo. Consulta "
              "la sección \"Proyección de Peso\" para visualizar cómo podría evolucionar tu peso si mantienes "
              "este plan.",
              emoji="🎯", color="#FCE4EC", borde="#D81B60")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "6.-MACRONUTRIENTES":
    hoja_header(6, T(
        "Proteínas y grasas se calculan según tus gramos por kilo de peso corporal; los "
        "carbohidratos cubren la energía restante hasta completar tu Requerimiento Calórico Diario.",
        "Protein and fat are calculated based on your grams per kilogram of body weight; "
        "carbohydrates cover the remaining energy needed to complete your Daily Caloric Requirement."
    ))

    # ---- Mapas de traducción locales para esta hoja (niveles Mínimo/Intermedio/Máximo) ----
    _NIVEL_EN = {"Mínimo": "Minimum", "Intermedio": "Intermediate", "Máximo": "Maximum"}

    def _niv(nivel):
        return T(nivel, _NIVEL_EN[nivel])

    # ===== RCD grande y destacado arriba de todo =====
    st.markdown(f"""
    <div style="background:linear-gradient(120deg,#1E5631 0%,#2E7D32 60%,#4CAF50 100%);border-radius:26px;
                padding:26px 30px;text-align:center;color:#FFFFFF;margin-bottom:18px;
                box-shadow:0 16px 36px rgba(30,86,49,0.30);">
        <div style="font-size:0.8rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.92;">
            🔥 {T('Tu Requerimiento Calórico Diario (RCD)', 'Your Daily Caloric Requirement (DCR)')}</div>
        <div style="font-size:2.8rem;font-weight:900;letter-spacing:-0.02em;margin:6px 0;">{rcd_final:.2f} <span style="font-size:1.1rem;font-weight:700;">{T('kcal/día', 'kcal/day')}</span></div>
        <div style="font-size:0.84rem;opacity:0.9;">{T('Sobre este total se reparten tus macronutrientes.', 'Your macronutrients are distributed across this total.')}</div>
    </div>
    """, unsafe_allow_html=True)

    # =====================================================================================
    # VARIABLES DE ENTRADA (equivalentes a pesoUsuario / rcdUsuario / objetivoUsuario)
    # =====================================================================================
    peso_usuario = peso
    rcd_usuario = rcd_final
    objetivo_usuario = objetivo

    # ---- Constantes universales: calorías que aporta 1 gramo de cada macronutriente ----
    KCAL_POR_G_PROT = 4
    KCAL_POR_G_CARB = 4
    KCAL_POR_G_GRAS = 9

    # ---- Factores g/kg de peso corporal para cada nivel (Mínimo / Intermedio / Máximo) ----
    FACTORES_PROT = {"Mínimo": 1.8, "Intermedio": 2.1, "Máximo": 2.5}
    FACTORES_GRAS = {"Mínimo": 0.5, "Intermedio": 1.0, "Máximo": 1.5}

    # ---- Excepción de conversión de Grasa: en el nivel Máximo se usa 4 kcal/g (no 9) ----
    KCAL_POR_G_GRAS_POR_NIVEL = {"Mínimo": KCAL_POR_G_GRAS, "Intermedio": KCAL_POR_G_GRAS, "Máximo": 4}

    def _calcular_nivel_macros(nivel, factor_prot, factor_gras):
        """Fórmulas exactas de cálculo para un nivel (Mínimo/Intermedio/Máximo):
        Proteína (g)  = peso × factor_prot   |  Proteína (kcal/día) = g × 4
        Grasa (g)     = peso × factor_gras   |  Grasa (kcal/día)    = g × 9
            (EXCEPCIÓN: en el nivel Máximo, la grasa se convierte con 4 kcal/g, no 9)
        Kcal Restantes = Kcal Proteína (de ese nivel) + Kcal Grasa (de ese nivel)
        Carbohidrato (kcal/día) = RCD − Kcal Restantes   ← energía restante de ese nivel
        Carbohidrato (g)        = Kcal Carbohidrato/día / 4
        """
        gr_p = peso_usuario * factor_prot
        kcal_p = gr_p * KCAL_POR_G_PROT
        gr_g = peso_usuario * factor_gras
        kcal_g = gr_g * KCAL_POR_G_GRAS_POR_NIVEL[nivel]
        kcal_restantes = kcal_p + kcal_g
        kcal_c = rcd_usuario - kcal_restantes
        gr_c = kcal_c / KCAL_POR_G_CARB
        return {"gr_prot": gr_p, "kcal_prot": kcal_p, "gr_gras": gr_g, "kcal_gras": kcal_g,
                "kcal_restantes": kcal_restantes, "kcal_carb": kcal_c, "gr_carb": gr_c}

    niveles_calculados = {
        nivel: _calcular_nivel_macros(nivel, FACTORES_PROT[nivel], FACTORES_GRAS[nivel])
        for nivel in ["Mínimo", "Intermedio", "Máximo"]
    }

    # ---- Filtro inteligente: el objetivo del usuario define qué nivel de factor se aplica ----
    MAPA_OBJETIVO_NIVEL = {
        "Bajar de peso": "Mínimo",
        "Mantenerse": "Intermedio",
        "Subir de peso": "Máximo",
    }
    nivel_final = MAPA_OBJETIVO_NIVEL.get(objetivo_usuario, "Intermedio")
    datos_final = niveles_calculados[nivel_final]
    total_kcal_final = datos_final["kcal_prot"] + datos_final["kcal_gras"] + datos_final["kcal_carb"]
    total_gr_final = datos_final["gr_prot"] + datos_final["gr_gras"] + datos_final["gr_carb"]

    _pct_prot_final = (datos_final["kcal_prot"] / total_kcal_final * 100) if total_kcal_final else 0
    _pct_gras_final = (datos_final["kcal_gras"] / total_kcal_final * 100) if total_kcal_final else 0
    _pct_carb_final = (datos_final["kcal_carb"] / total_kcal_final * 100) if total_kcal_final else 0

    # =====================================================================================
    # 1. ¿CÓMO SE REPARTEN TUS CALORÍAS? — mapa visual en vez de 3 tarjetas iguales
    # =====================================================================================
    st.markdown(f"#### 🍽️ {T('¿Cómo se reparten tus calorías?', 'How are your calories distributed?')}")
    st.markdown(f"""
    <div style="text-align:center;margin:6px 0 18px 0;">
        <div style="font-size:2.1rem;font-weight:900;color:#17301F;">{rcd_final:.0f} <span style="font-size:1rem;font-weight:700;color:#8E8E93;">{T('kcal', 'kcal')}</span></div>
        <div style="font-size:1.3rem;color:#8E8E93;margin:2px 0 14px 0;">↓</div>
    </div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;">
        <div style="flex:1;min-width:150px;background:#FFEBF0;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #FF2D5533;">
            <div style="font-size:1.6rem;">❤️</div>
            <div style="font-weight:800;color:#C2185B;margin:4px 0 2px 0;">{T('Proteínas', 'Protein')}</div>
            <div style="font-size:0.78rem;color:#8A5252;">{T('Construyen', 'Build')}</div>
            <div style="font-weight:800;color:#C2185B;margin-top:6px;">4 kcal/g</div>
        </div>
        <div style="flex:1;min-width:150px;background:#EAFAEE;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #34C75933;">
            <div style="font-size:1.6rem;">🥑</div>
            <div style="font-weight:800;color:#1E5631;margin:4px 0 2px 0;">{T('Grasas', 'Fat')}</div>
            <div style="font-size:0.78rem;color:#3E7050;">{T('Protegen', 'Protect')}</div>
            <div style="font-weight:800;color:#1E5631;margin-top:6px;">9 kcal/g</div>
        </div>
        <div style="flex:1;min-width:150px;background:#FFF8E1;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #FFCC0055;">
            <div style="font-size:1.6rem;">🌾</div>
            <div style="font-weight:800;color:#8A6D00;margin:4px 0 2px 0;">{T('Carbohidratos', 'Carbohydrates')}</div>
            <div style="font-size:0.78rem;color:#9C8300;">{T('Dan energía', 'Provide Energy')}</div>
            <div style="font-weight:800;color:#8A6D00;margin-top:6px;">4 kcal/g</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # =====================================================================================
    # 2. RECOMENDACIÓN INTERNACIONAL — tarjeta OMS bien visible
    # =====================================================================================
    st.markdown(f"""
    <div style="background:linear-gradient(120deg,#EAF3FF 0%,#DCEBFF 100%);border-radius:20px;
                padding:20px 24px;margin-bottom:18px;border:1.5px solid #007AFF33;">
        <div style="font-weight:800;color:#007AFF;font-size:1rem;margin-bottom:10px;">
            🌍 {T('Recomendación internacional', 'International Recommendation')}</div>
        <p style="margin:0 0 6px 0;color:#17301F;font-size:0.86rem;">
            {T('Según la Organización Mundial de la Salud (OMS):', 'According to the World Health Organization (WHO):')}</p>
        <p style="margin:0 0 4px 0;color:#3C3C43;font-size:0.84rem;">✔ {T('Proteínas y grasas son nutrientes esenciales.', 'Protein and fat are essential nutrients.')}</p>
        <p style="margin:0 0 4px 0;color:#3C3C43;font-size:0.84rem;">✔ {T('Los carbohidratos son la principal fuente práctica de energía.', 'Carbohydrates are the main practical source of energy.')}</p>
        <p style="margin:0 0 8px 0;color:#3C3C43;font-size:0.84rem;">✔ {T('Una alimentación saludable debe incluir un equilibrio entre los tres macronutrientes.', 'A healthy diet should include a balance of all three macronutrients.')}</p>
        <p style="margin:0;color:#8E8E93;font-size:0.7rem;">{T('Referencia: Organización Mundial de la Salud (OMS).', 'Reference: World Health Organization (WHO).')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.info(T(
        "🌾 **Dato importante (OMS):** a diferencia de las proteínas y las grasas, los **carbohidratos "
        "no son un nutriente esencial**: el cuerpo puede obtener energía de grasas y proteínas mediante "
        "gluconeogénesis. Se incluyen en la dieta por ser una fuente práctica y eficiente de energía, "
        "pero no son indispensables para sobrevivir ni para una nutrición adecuada.",
        "🌾 **Important WHO Note:** unlike protein and fat, **carbohydrates are not an essential "
        "nutrient**: the body can obtain energy from fat and protein through gluconeogenesis. They "
        "are included in the diet because they're a practical and efficient source of energy, but "
        "they aren't indispensable for survival or for adequate nutrition."
    ))

    st.divider()

    # =====================================================================================
    # 3. TARJETAS CON PERSONALIDAD — qué función cumple cada macronutriente
    # =====================================================================================
    st.markdown(f"#### 🧠 {T('¿Qué hace cada macronutriente?', 'What does each macronutrient do?')}")
    tp1, tp2, tp3 = st.columns(3)
    with tp1:
        st.markdown(f"""
        <div class="macro-card prot">
            <div class="mc-head"><span class="mc-icon">❤️</span><span class="mc-title">{T('Proteínas', 'Protein')}</span>
                <span class="mc-tip" title="{T('1 gramo de proteína equivale a 4 kcal. Se calcula multiplicando tu peso (kg) por un factor de 1.8 a 2.5 g/kg.', '1 gram of protein equals 4 kcal. It is calculated by multiplying your weight (kg) by a factor of 1.8 to 2.5 g/kg.')}">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🏗 {T('Construyen músculos', 'Build muscle')}</p>
            <p style="margin:2px 0;font-size:0.82rem;">🩹 {T('Reparan tejidos', 'Repair tissue')}</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🛡 {T('Forman enzimas', 'Form enzymes')}</p>
            <div class="mc-value">⚡ 4 kcal/g</div>
            <div class="mc-sub">{T('Factores (g/kg de peso)', 'Factors (g/kg of weight)')}:<br>{T('Mínimo', 'Minimum')} <b>1.8</b> · {T('Intermedio', 'Intermediate')} <b>2.1</b> · {T('Máximo', 'Maximum')} <b>2.5</b></div>
        </div>
        """, unsafe_allow_html=True)
    with tp2:
        st.markdown(f"""
        <div class="macro-card gras">
            <div class="mc-head"><span class="mc-icon">🥑</span><span class="mc-title">{T('Grasas', 'Fat')}</span>
                <span class="mc-tip" title="{T('1 gramo de grasa equivale a 9 kcal. Se calcula multiplicando tu peso (kg) por un factor de 0.5 a 1.5 g/kg.', '1 gram of fat equals 9 kcal. It is calculated by multiplying your weight (kg) by a factor of 0.5 to 1.5 g/kg.')}">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🧠 {T('Protegen el cerebro', 'Protect the brain')}</p>
            <p style="margin:2px 0;font-size:0.82rem;">🔥 {T('Reserva energética', 'Energy reserve')}</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🫀 {T('Ayudan a absorber vitaminas', 'Help absorb vitamins')}</p>
            <div class="mc-value">⚡ 9 kcal/g</div>
            <div class="mc-sub">{T('Factores (g/kg de peso)', 'Factors (g/kg of weight)')}:<br>{T('Mínimo', 'Minimum')} <b>0.5</b> · {T('Intermedio', 'Intermediate')} <b>1.0</b> · {T('Máximo', 'Maximum')} <b>1.5</b></div>
        </div>
        """, unsafe_allow_html=True)
    with tp3:
        st.markdown(f"""
        <div class="macro-card carb">
            <div class="mc-head"><span class="mc-icon">🌾</span><span class="mc-title">{T('Carbohidratos', 'Carbohydrates')}</span>
                <span class="mc-tip" title="{T('1 gramo de carbohidrato equivale a 4 kcal. No usan un factor de peso: cubren la energía restante hasta tu RCD.', '1 gram of carbohydrate equals 4 kcal. They do not use a weight factor: they cover the remaining energy up to your DCR.')}">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🏃 {T('Principal combustible', 'Main fuel source')}</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🧠 {T('Energía para el cerebro', 'Energy for the brain')}</p>
            <div class="mc-value">⚡ 4 kcal/g</div>
            <div class="mc-sub">{T('Sin factor de peso — cubren el resto de la energía de tu RCD.', 'No weight factor — they cover the rest of your DCR energy.')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # =====================================================================================
    # TABLA 2 — Proyección de Requerimientos (demostración de los 3 niveles) — sin tocar
    # =====================================================================================
    st.markdown(f"#### 📊 {T('Proyección de Requerimientos', 'Projection of Requirements')}")
    st.markdown(f"""
    <div style="text-align:center;color:#8E8E93;font-size:0.8rem;font-weight:700;margin-bottom:8px;">
        {T('Peso → Factores OMS → Proteínas → Grasas → Carbohidratos → Plan nutricional',
           'Weight → WHO Factors → Protein → Fat → Carbohydrates → Nutritional Plan')}
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Prot(g)=peso×Factor → Kcal=g×4 | Grasa(g)=peso×Factor → Kcal=g×9 | "
        "Carb: Kcal = RCD − Kcal Restantes → Gramos = Kcal/4",
        referencia=T("Modelo de reparto de macronutrientes por nivel", "Macronutrient distribution model by level"))}</div>""", unsafe_allow_html=True)
    st.caption(T("Así se calculan los escenarios Mínimo, Intermedio y Máximo basados en tu peso actual.",
                 "This is how the Minimum, Intermediate, and Maximum scenarios are calculated based on your current weight."))
    st.info(f"⚖️ {T('Peso usado en los cálculos', 'Weight used in calculations')}: **{peso_usuario:.2f} kg** · "
            f"🔥 {T('RCD objetivo', 'Target DCR')}: **{rcd_usuario:.2f} {T('kcal/día', 'kcal/day')}**")

    _filas_niveles_html = ""
    _COL_PROT = ("#C2185B", "#FFEBF0")
    _COL_GRAS = ("#1E5631", "#EAFAEE")
    _COL_CARB = ("#8A6D00", "#FFF8E1")
    for _nivel in ["Mínimo", "Intermedio", "Máximo"]:
        _d = niveles_calculados[_nivel]
        _es_actual = (_nivel == nivel_final)
        _borde_sel = "box-shadow:inset 0 2px 0 #FFCC00,inset 0 -2px 0 #FFCC00;" if _es_actual else ""
        _nombre_fila = f"⭐ {_niv(_nivel)}" if _es_actual else _niv(_nivel)
        _badge_tu_nivel = f' <span class="badge-tu-nivel">{T("TU NIVEL", "YOUR LEVEL")}</span>' if _es_actual else ""
        _filas_niveles_html += f"""
        <tr>
            <td style="text-align:left;font-weight:800;{_borde_sel}">{_nombre_fila}{_badge_tu_nivel}</td>
            <td style="background:{_COL_PROT[1]};{_borde_sel}">{FACTORES_PROT[_nivel]:.1f} g/kg</td>
            <td style="background:{_COL_PROT[1]};{_borde_sel}">{_d['gr_prot']:.1f} g</td>
            <td style="background:{_COL_PROT[1]};color:{_COL_PROT[0]};font-weight:800;{_borde_sel}">{_d['kcal_prot']:.0f} kcal/día</td>
            <td style="background:{_COL_GRAS[1]};{_borde_sel}">{FACTORES_GRAS[_nivel]:.1f} g/kg</td>
            <td style="background:{_COL_GRAS[1]};{_borde_sel}">{_d['gr_gras']:.1f} g</td>
            <td style="background:{_COL_GRAS[1]};color:{_COL_GRAS[0]};font-weight:800;{_borde_sel}">{_d['kcal_gras']:.0f} kcal/día</td>
            <td style="background:{_COL_CARB[1]};{_borde_sel}">{_d['kcal_restantes']:.0f} kcal/día</td>
            <td style="background:{_COL_CARB[1]};{_borde_sel}">{_d['gr_carb']:.1f} g</td>
            <td style="background:{_COL_CARB[1]};color:{_COL_CARB[0]};font-weight:800;{_borde_sel}">{_d['kcal_carb']:.0f} kcal/día</td>
        </tr>"""

    _html_tabla_niveles = f"""
    <div style="overflow-x:auto;">
    <table class="macro-niveles-table">
        <thead>
        <tr>
            <th rowspan="2">{T('Nivel', 'Level')}</th>
            <th colspan="3" style="background:{_COL_PROT[0]};">🥩 {T('Proteína', 'Protein')}</th>
            <th colspan="3" style="background:{_COL_GRAS[0]};">🥑 {T('Grasa', 'Fat')}</th>
            <th colspan="3" style="background:{_COL_CARB[0]};">🌾 {T('Carbohidrato', 'Carbohydrate')}</th>
        </tr>
        <tr>
            <th style="background:{_COL_PROT[0]};">{T('Factor', 'Factor')}</th><th style="background:{_COL_PROT[0]};">{T('Gramos', 'Grams')}</th><th style="background:{_COL_PROT[0]};">{T('Kcal/día', 'Kcal/day')}</th>
            <th style="background:{_COL_GRAS[0]};">{T('Factor', 'Factor')}</th><th style="background:{_COL_GRAS[0]};">{T('Gramos', 'Grams')}</th><th style="background:{_COL_GRAS[0]};">{T('Kcal/día', 'Kcal/day')}</th>
            <th style="background:{_COL_CARB[0]};">{T('Kcal Restantes', 'Remaining Kcal')}</th><th style="background:{_COL_CARB[0]};">{T('Gramos', 'Grams')}</th><th style="background:{_COL_CARB[0]};">{T('Kcal/día', 'Kcal/day')}</th>
        </tr>
        </thead>
        <tbody>
        {_filas_niveles_html}
        </tbody>
    </table>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_niveles), unsafe_allow_html=True)
    st.caption(f"⭐ {T('La fila resaltada con borde amarillo es el nivel que corresponde a tu objetivo actual', 'The row highlighted with a yellow border is the level that matches your current goal')} "
               f"(**{T(objetivo_usuario, _OBJ_EN.get(objetivo_usuario, objetivo_usuario))}** → **{_niv(nivel_final)}**).")
    st.caption(T(
        "💡 **Kcal Restantes:** es la suma de la Kcal/día de Proteína + la Kcal/día de Grasa de "
        "ESE mismo nivel (Mínimo, Intermedio o Máximo) — por eso cambia en cada fila. "
        "**Carbohidratos:** no usan un factor de peso; se calculan cubriendo la energía "
        "restante hasta tu Requerimiento Calórico Diario → "
        "`Kcal/día Carbohidrato = RCD − Kcal Restantes` y `Gramos = Kcal/día ÷ 4`.",
        "💡 **Remaining Kcal:** this is the sum of the Kcal/day from Protein + the Kcal/day from Fat "
        "for THAT SAME level (Minimum, Intermediate, or Maximum) — that's why it changes on each row. "
        "**Carbohydrates:** they don't use a weight factor; they're calculated by covering the "
        "remaining energy up to your Daily Caloric Requirement → "
        "`Kcal/day Carbohydrate = DCR − Remaining Kcal` and `Grams = Kcal/day ÷ 4`."
    ))

    st.divider()

    # =====================================================================================
    # TABLA 3 — Tu Plan Nutricional Definitivo (filtro inteligente según tu objetivo)
    # =====================================================================================
    st.markdown(f"#### 🎯 {T('Este será tu plan diario', 'This Will Be Your Daily Plan')}")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        'IF "Bajar de peso" → Mínimo (1.8/0.5) · IF "Mantenerse" → Intermedio (2.1/1.0) · '
        'IF "Subir de peso" → Máximo (2.5/1.5)',
        referencia=T("Filtro inteligente según objetivoUsuario", "Smart filter based on objetivoUsuario"))}</div>""", unsafe_allow_html=True)
    st.caption(T("Basado en tu elección de la página anterior, aquí tienes tus requerimientos exactos para alcanzar tu meta.",
                 "Based on your choice on the previous page, here are your exact requirements to reach your goal."))
    st.success(f"🎯 {T('Objetivo seleccionado', 'Selected Goal')}: **{T(objetivo_usuario, _OBJ_EN.get(objetivo_usuario, objetivo_usuario))}** → "
               f"{T('Nivel aplicado', 'Applied Level')}: **{_niv(nivel_final)}** "
               f"({T('Proteína', 'Protein')} {FACTORES_PROT[nivel_final]:.1f} g/kg · {T('Grasa', 'Fat')} {FACTORES_GRAS[nivel_final]:.1f} g/kg)")

    # ---- Resumen visual: 3 tarjetas grandes + barra de calorías ----
    rp1, rp2, rp3 = st.columns(3)
    for _col_r, _ic_r, _val_r, _lab_r, _col_hex_r, _fon_r in [
        (rp1, "❤️", f"{datos_final['gr_prot']:.0f} g", T("Proteínas", "Protein"), "#C2185B", "#FFEBF0"),
        (rp2, "🥑", f"{datos_final['gr_gras']:.0f} g", T("Grasas", "Fat"), "#1E5631", "#EAFAEE"),
        (rp3, "🌾", f"{datos_final['gr_carb']:.0f} g", T("Carbohidratos", "Carbohydrates"), "#8A6D00", "#FFF8E1"),
    ]:
        with _col_r:
            st.markdown(f"""
            <div style="background:{_fon_r};border-radius:20px;padding:20px;text-align:center;">
                <div style="font-size:1.8rem;">{_ic_r}</div>
                <div style="font-size:1.6rem;font-weight:900;color:{_col_hex_r};margin:4px 0;">{_val_r}</div>
                <div style="font-size:0.82rem;font-weight:700;color:{_col_hex_r};">{_lab_r}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin:14px 0 4px 0;">
        <div style="display:flex;height:22px;border-radius:11px;overflow:hidden;">
            <div style="width:{_pct_prot_final:.1f}%;background:#FF2D55;"></div>
            <div style="width:{_pct_gras_final:.1f}%;background:#34C759;"></div>
            <div style="width:{_pct_carb_final:.1f}%;background:#FFCC00;"></div>
        </div>
        <div style="text-align:center;margin-top:6px;font-weight:800;color:#17301F;">
            {total_kcal_final:.0f} {T('kcal', 'kcal')} — 100%</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Gráfico donut ----
    fig_donut_macro = go.Figure(data=[go.Pie(
        labels=[f"❤️ {T('Proteínas', 'Protein')}", f"🥑 {T('Grasas', 'Fat')}", f"🌾 {T('Carbohidratos', 'Carbohydrates')}"],
        values=[datos_final["kcal_prot"], datos_final["kcal_gras"], datos_final["kcal_carb"]],
        hole=0.62,
        marker=dict(colors=["#FF2D55", "#34C759", "#FFCC00"]),
        textinfo="label+percent",
        textfont=dict(size=13),
    )])
    fig_donut_macro.update_layout(
        annotations=[dict(text=f"🍽<br><b>{total_kcal_final:.0f}</b><br>{T('kcal', 'kcal')}", x=0.5, y=0.5,
                           font=dict(size=15, color="#17301F"), showarrow=False)],
        showlegend=False, height=340, margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_donut_macro, use_container_width=True)
    st.caption(T("El gráfico muestra de dónde vienen principalmente tus calorías diarias.",
                 "The chart shows where your daily calories mainly come from."))

    _html_tabla_final = f"""
    <table class="macro-final-table">
        <thead>
        <tr><th style="text-align:left;">{T('Macronutriente', 'Macronutrient')}</th><th>{T('Gramos', 'Grams')} (g)</th><th>{T('Kcal/día', 'Kcal/day')}</th></tr>
        </thead>
        <tbody>
        <tr>
            <td style="text-align:left;">🥩 {T('Proteína', 'Protein')}</td>
            <td>{datos_final['gr_prot']:.1f} g</td>
            <td>{datos_final['kcal_prot']:.0f} {T('kcal/día', 'kcal/day')}</td>
        </tr>
        <tr>
            <td style="text-align:left;">🥑 {T('Grasa', 'Fat')}</td>
            <td>{datos_final['gr_gras']:.1f} g</td>
            <td>{datos_final['kcal_gras']:.0f} {T('kcal/día', 'kcal/day')}</td>
        </tr>
        <tr>
            <td style="text-align:left;">🌾 {T('Carbohidrato', 'Carbohydrate')}</td>
            <td>{datos_final['gr_carb']:.1f} g</td>
            <td>{datos_final['kcal_carb']:.0f} {T('kcal/día', 'kcal/day')}</td>
        </tr>
        <tr class="fila-total">
            <td style="text-align:left;">{T('TOTAL', 'TOTAL')}</td>
            <td>{total_gr_final:.1f} g</td>
            <td>{total_kcal_final:.0f} {T('kcal/día', 'kcal/day')}
                <span style="display:inline-block;margin-left:10px;background:#FFCC00;color:#5C4700;
                    font-weight:900;font-size:0.8rem;padding:4px 12px;border-radius:999px;
                    letter-spacing:0.02em;">→ {T('RCD', 'DCR')}</span>
            </td>
        </tr>
        </tbody>
    </table>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_final), unsafe_allow_html=True)

    if abs(total_kcal_final - rcd_usuario) < 1:
        st.markdown(f"""
        <div style="background:linear-gradient(120deg,#34C759 0%,#1E5631 100%);color:#FFFFFF;
                    border-radius:20px;padding:20px 26px;margin-top:14px;text-align:center;
                    font-weight:900;font-size:1.05rem;box-shadow:0 14px 32px rgba(52,199,89,0.35);">
            ✅ {T('El total de calorías coincide exactamente con tu Requerimiento Calórico Diario (RCD).', 'The total calories match your Daily Caloric Requirement (DCR) exactly.')}
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # =====================================================================================
    # ¿POR QUÉ NO TODOS SE CALCULAN IGUAL? — versión corta, tipo clínica
    # =====================================================================================
    st.markdown(f"#### 💡 {T('¿Por qué no todos se calculan igual?', 'Why are they calculated differently?')}")
    wp1, wp2, wp3 = st.columns(3)
    with wp1:
        st.markdown(f"""<div style="background:#FFEBF0;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">❤️</div><b style="color:#C2185B;">{T('Proteínas', 'Protein')}</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">{T('Dependen de tu peso corporal.', 'They depend on your body weight.')}</p>
        </div>""", unsafe_allow_html=True)
    with wp2:
        st.markdown(f"""<div style="background:#EAFAEE;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">🥑</div><b style="color:#1E5631;">{T('Grasas', 'Fat')}</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">{T('También dependen de tu peso.', 'They also depend on your weight.')}</p>
        </div>""", unsafe_allow_html=True)
    with wp3:
        st.markdown(f"""<div style="background:#FFF8E1;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">🌾</div><b style="color:#8A6D00;">{T('Carbohidratos', 'Carbohydrates')}</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">{T('Se calculan con las calorías restantes hasta completar tu RCD.', 'They are calculated from the remaining calories needed to complete your DCR.')}</p>
        </div>""", unsafe_allow_html=True)

    st.write("")

    # =====================================================================================
    # ¿SABÍAS QUE? — curiosidades rotativas
    # =====================================================================================
    _curiosidades_macro = [
        ("📚", T("El cuerpo puede almacenar muy poca proteína. Por eso necesita consumirla regularmente.",
                 "The body can store very little protein. That's why it needs to be consumed regularly.")),
        ("🧠", T("El cerebro utiliza principalmente glucosa como fuente de energía.",
                 "The brain mainly uses glucose as its energy source.")),
        ("🥑", T("Las grasas aportan más del doble de energía por gramo que proteínas y carbohidratos.",
                 "Fat provides more than double the energy per gram compared to protein and carbohydrates.")),
    ]
    _idx_curio = int(datetime.now().timestamp() // 8) % len(_curiosidades_macro)
    _ic_curio, _txt_curio = _curiosidades_macro[_idx_curio]
    st.markdown(f"""
    <div style="background:#F5F5F7;border-radius:16px;padding:14px 18px;display:flex;gap:12px;align-items:center;">
        <div style="font-size:1.4rem;">{_ic_curio}</div>
        <div style="font-size:0.84rem;color:#3C3C43;"><b>{T('¿Sabías que?', 'Did you know?')}</b> {_txt_curio}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    caja_util(T(
        "Las proteínas y grasas se calculan según tu peso corporal (gramos por kilo), porque son "
        "nutrientes estructurales que dependen de tu masa, no de cuánta energía gastas. Los "
        "carbohidratos, en cambio, son la variable de ajuste: llenan el resto de tu energía diaria "
        "hasta llegar exactamente a tu RCD. 🍽️",
        "Protein and fat are calculated based on your body weight (grams per kilogram), because they "
        "are structural nutrients that depend on your mass, not on how much energy you burn. "
        "Carbohydrates, on the other hand, are the adjustment variable: they fill in the rest of your "
        "daily energy until they exactly reach your DCR. 🍽️"
    ), emoji="🍽️", color="#FFFDE7", borde="#FBC02D")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "7.-PORCIONES":
    hoja_header(7, T(
        "Tu Requerimiento Calórico Diario se reparte en 5 momentos del día usando porcentajes "
        "preestablecidos, para mantener tu metabolismo activo y evitar la ansiedad.",
        "Your Daily Caloric Requirement is distributed across 5 times of the day using preset "
        "percentages, to keep your metabolism active and prevent anxiety."
    ))
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Energía(comida) = RCD × % preestablecido (Desayuno 25% · Merienda 5% · Almuerzo 40% · "
        "Merienda 5% · Cena 25%)",
        referencia=T("Distribución calórica por comidas", "Caloric distribution by meal"))}</div>""", unsafe_allow_html=True)

    # =====================================================================================
    # RCD del usuario (ya calculado y ajustado a su objetivo en la Hoja 5)
    # =====================================================================================
    _rcd_comidas = rcd_final

    # ---- Traducción de nombres de comidas (claves internas se mantienen en español) ----
    _COMIDA_EN = {
        "Desayuno": "Breakfast", "Merienda 1": "Morning Snack", "Almuerzo": "Lunch",
        "Merienda 2": "Afternoon Snack", "Cena": "Dinner",
    }

    def _comida_nombre(nombre):
        return T(nombre, _COMIDA_EN[nombre])

    _html_rcd_hero = f"""
    <div class="rcd-hero-card">
        <div class="rcd-hero-decor d1">🔥</div>
        <div class="rcd-hero-decor d2">🍎</div>
        <div class="rcd-label">⚡ {T('Tu Requerimiento Calórico Diario', 'Your Daily Caloric Requirement')}</div>
        <div class="rcd-value">🎯 {_rcd_comidas:.2f} <span style="font-size:1.3rem;font-weight:700;">{T('kcal', 'kcal')}</span></div>
        <div class="rcd-sub">{T(
            "Para mantener tu metabolismo activo y evitar la ansiedad, hemos distribuido tus "
            "calorías totales a lo largo del día. Cada comida representa un porcentaje ideal de tu "
            "RCD. Los valores que ves en la tabla resultan de multiplicar tu RCD total por el "
            "porcentaje correspondiente a cada comida.",
            "To keep your metabolism active and prevent anxiety, we've distributed your total "
            "calories throughout the day. Each meal represents an ideal percentage of your DCR. "
            "The values you see in the table come from multiplying your total DCR by the "
            "percentage assigned to each meal."
        )}</div>
        <div class="rcd-hero-badges">
            <span class="rcd-hero-badge">🌅 {_comida_nombre('Desayuno')} 25%</span>
            <span class="rcd-hero-badge">🍎 {_comida_nombre('Merienda 1')} · 5%</span>
            <span class="rcd-hero-badge">🍽️ {_comida_nombre('Almuerzo')} 40%</span>
            <span class="rcd-hero-badge">🥪 {_comida_nombre('Merienda 2')} · 5%</span>
            <span class="rcd-hero-badge">🌙 {_comida_nombre('Cena')} 25%</span>
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_rcd_hero), unsafe_allow_html=True)

    # =====================================================================================
    # Distribución por comida: Energía (kcal) = RCD × Porcentaje de esa comida
    # =====================================================================================
    _ICONOS_COMIDA = {
        "Desayuno": "🌅", "Merienda 1": "🍎", "Almuerzo": "🍽️", "Merienda 2": "🥪", "Cena": "🌙",
    }
    _PORCENTAJES_COMIDA = {
        "Desayuno": 0.25, "Merienda 1": 0.05, "Almuerzo": 0.40, "Merienda 2": 0.05, "Cena": 0.25,
    }

    _filas_comidas_html = ""
    _suma_kcal_comidas = 0.0
    for _comida, _pct in _PORCENTAJES_COMIDA.items():
        _kcal_comida = _rcd_comidas * _pct
        _suma_kcal_comidas += _kcal_comida
        _filas_comidas_html += f"""
        <tr>
            <td class="comida-nombre">{_ICONOS_COMIDA[_comida]} {_comida_nombre(_comida)}</td>
            <td>{_pct*100:.0f}%</td>
            <td>{_kcal_comida:.2f} {T('kcal', 'kcal')}</td>
        </tr>"""

    _filas_comidas_html += f"""
        <tr class="fila-total-comidas">
            <td class="comida-nombre" style="color:#FFFFFF;">🔥 {T('RCD (Total Distribuido)', 'DCR (Total Distributed)')}</td>
            <td>100%</td>
            <td>{_suma_kcal_comidas:.2f} {T('kcal', 'kcal')}</td>
        </tr>"""

    _html_tabla_comidas = f"""
    <div class="comidas-table-wrap">
    <table class="comidas-table">
        <thead>
        <tr><th style="text-align:left;">{T('Comida', 'Meal')}</th><th>{T('Porcentaje', 'Percentage')} (%)</th><th>{T('Energía', 'Energy')} ({T('kcal', 'kcal')})</th></tr>
        </thead>
        <tbody>
        {_filas_comidas_html}
        </tbody>
    </table>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_comidas), unsafe_allow_html=True)

    # =====================================================================================
    # Validación real: comparación explícita entre RCD Calculado y Total Distribuido
    # (margen de error mínimo permitido por decimales de redondeo)
    # =====================================================================================
    _diferencia_validacion = abs(_suma_kcal_comidas - _rcd_comidas)
    _coincide = _diferencia_validacion < 0.5
    _fila_estado_clase = "val-row-estado-ok" if _coincide else "val-row-estado-bad"
    _estado_txt = T("✅ Coinciden", "✅ Match") if _coincide else T("❌ No coinciden", "❌ Don't match")

    _html_val_card = f"""
    <div class="val-card">
        <div class="val-card-title">🔍 {T('Comparación: RCD Calculado vs. Total Distribuido', 'Comparison: Calculated DCR vs. Total Distributed')}</div>
        <table class="val-comparacion-table">
            <tr><td>{T('RCD Calculado', 'Calculated DCR')}</td><td>{_rcd_comidas:.2f} {T('kcal', 'kcal')}</td></tr>
            <tr><td>{T('Total Distribuido', 'Total Distributed')}</td><td>{_suma_kcal_comidas:.2f} {T('kcal', 'kcal')}</td></tr>
            <tr><td>{T('Diferencia', 'Difference')}</td><td>{_diferencia_validacion:.2f} {T('kcal', 'kcal')}</td></tr>
            <tr class="{_fila_estado_clase}"><td>{T('Estado', 'Status')}</td><td>{_estado_txt}</td></tr>
        </table>
        <div class="val-card-title" style="margin-top:4px;">📋 {T('Estado de Validación', 'Validation Status')}</div>
        <div class="val-checklist">
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> {T('RCD Calculado', 'Calculated DCR')} ............. {_rcd_comidas:.2f} {T('kcal', 'kcal')}
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> {T('Total Distribuido', 'Total Distributed')} ......... {_suma_kcal_comidas:.2f} {T('kcal', 'kcal')}
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> {T('Diferencia', 'Difference')} ................ {_diferencia_validacion:.2f} {T('kcal', 'kcal')}
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_val_card), unsafe_allow_html=True)

    if _coincide:
        st.markdown(f"""
        <div class="val-banner-ok">
            <span class="val-banner-icon">🟢</span>
            <div class="val-banner-title">✔ {T('Planificación Energética Correcta', 'Energy Distribution Successfully Validated')}</div>
            <div class="val-banner-sub">{T(
                "Las calorías distribuidas en tus 5 comidas coinciden exactamente con tu "
                "Requerimiento Calórico Diario. ✨ ¡Matemática exacta! Tu día está planificado al 100%.",
                "The calories distributed across your 5 meals match your Daily Caloric Requirement "
                "exactly. ✨ Precise math! Your day is 100% planned."
            )}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="val-banner-error">
            <span class="val-banner-icon">🔴</span>
            <div class="val-banner-title">⚠ {T(
                f'Existe una diferencia de {_diferencia_validacion:.2f} kcal entre el RCD y la distribución diaria.',
                f'There is a difference of {_diferencia_validacion:.2f} kcal between the DCR and the daily distribution.'
            )}</div>
            <div class="val-banner-sub">{T('Revise la planificación.', 'Please review the plan.')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"#### ❓ {T('Preguntas frecuentes sobre los momentos de comida', 'Frequently Asked Questions About Meal Timing')}")
    # Pares (pregunta_es, pregunta_en, respuesta_es, respuesta_en) para mantener el orden y
    # facilitar la traducción completa de preguntas y respuestas del FAQ.
    FAQ_PORCIONES = [
        (
            "¿Por qué es importante el desayuno?",
            "Why is breakfast important?",
            "El desayuno rompe el ayuno de la noche y le da a tu cerebro la glucosa que necesita para "
            "concentrarte desde temprano. Saltarlo se asocia con menor rendimiento escolar y más antojos de "
            "azúcar durante el día. Por eso se le asigna un 25% de tus calorías diarias.",
            "Breakfast breaks the overnight fast and gives your brain the glucose it needs to "
            "concentrate from early on. Skipping it is linked to lower school performance and more "
            "sugar cravings during the day. That's why it's assigned 25% of your daily calories.",
        ),
        (
            "¿Por qué es importante la merienda?",
            "Why are snacks important?",
            "Las meriendas (5% cada una) evitan que llegues con demasiada hambre al almuerzo o la cena, lo "
            "que ayuda a que no comas de más de una sola vez. También mantienen estables tus niveles de "
            "energía y glucosa entre comidas principales.",
            "Snacks (5% each) keep you from arriving too hungry at lunch or dinner, which helps you "
            "avoid overeating in one sitting. They also keep your energy and glucose levels stable "
            "between main meals.",
        ),
        (
            "¿Por qué es importante el almuerzo?",
            "Why is lunch important?",
            "El almuerzo es la comida más grande del día (40%) porque coincide con el momento de mayor "
            "actividad física y mental. Aporta la mayor parte de tu energía, proteínas y nutrientes para "
            "sostenerte durante la tarde.",
            "Lunch is the largest meal of the day (40%) because it coincides with your peak physical "
            "and mental activity. It provides most of your energy, protein, and nutrients to sustain "
            "you through the afternoon.",
        ),
        (
            "¿Por qué es importante la cena?",
            "Why is dinner important?",
            "La cena (25%) repone lo gastado durante el día sin sobrecargar tu digestión antes de dormir. "
            "Una cena balanceada favorece un mejor descanso, y un mejor descanso reduce la ansiedad por "
            "comer dulce al día siguiente.",
            "Dinner (25%) replenishes what was spent during the day without overloading your digestion "
            "before bed. A balanced dinner promotes better rest, and better rest reduces next-day "
            "cravings for sweets.",
        ),
    ]
    _es_ingles = st.session_state.get("idioma", "Español") == "English"
    _preguntas_mostradas = [(fen if _es_ingles else fes) for fes, fen, _, _ in FAQ_PORCIONES]
    _idx_pregunta = st.selectbox(T("Elige una pregunta:", "Choose a question:"), range(len(_preguntas_mostradas)),
                                  format_func=lambda i: _preguntas_mostradas[i], key="faq_porciones")
    _respuesta_mostrada = FAQ_PORCIONES[_idx_pregunta][3] if _es_ingles else FAQ_PORCIONES[_idx_pregunta][2]
    st.info(_respuesta_mostrada)

    caja_util(T(
        "Comer todas tus calorías de una sola vez sería imposible (¡y poco saludable!). Esta hoja te dice "
        "cuánto puedes comer en cada momento del día: desayuno, meriendas, almuerzo y cena, para que "
        "llegues a tu meta sin pasar hambre ni excederte. ⏰🍴",
        "Eating all your calories at once would be impossible (and unhealthy!). This page tells you "
        "how much you can eat at each time of day: breakfast, snacks, lunch, and dinner, so you reach "
        "your goal without going hungry or overeating. ⏰🍴"
    ), emoji="🍽️", color="#E0F7FA", borde="#00ACC1")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "8.-FATSECRET":
    hoja_header(8, subtitulo=T(
        "Descubre la composición nutricional de los alimentos más consumidos en el Perú "
        "utilizando información oficial del INS/CENAN. Busca un alimento y conoce su "
        "aporte de energía y nutrientes de forma clara y sencilla.",
        "Discover the nutritional composition of the most commonly eaten foods in Peru "
        "using official INS/CENAN data. Search for a food and learn about its energy and "
        "nutrient content in a clear and simple way."
    ))

    st.markdown("""
    <style>
    .bpa-card{background:#1C1C1E;border-radius:22px;padding:26px 28px;margin:14px 0;
        box-shadow:0 1px 2px rgba(0,0,0,0.15),0 10px 26px rgba(0,0,0,0.18);color:#F2F2F7;}
    .bpa-card h3{margin:0 0 2px 0;color:#F2F2F7;font-size:1.35rem;font-weight:800;}
    .bpa-sub{color:#9DA3AE;font-size:0.85rem;margin-bottom:16px;}
    .bpa-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px;}
    .bpa-metric{background:#2C2C2E;border-radius:14px;padding:12px 14px;text-align:center;}
    .bpa-metric .lbl{font-size:0.72rem;color:#9DA3AE;font-weight:600;}
    .bpa-metric .val{font-size:1.25rem;font-weight:800;color:#F2F2F7;margin-top:2px;}
    .bpa-source{background:#0F2A3A;border-radius:14px;padding:12px 16px;font-size:0.82rem;color:#7FC7FF;margin-bottom:16px;}
    .bpa-tips{color:#D7D9DE;font-size:0.9rem;margin:4px 0;}
    .bpa-chip{display:inline-block;background:#2C2C2E;color:#D7D9DE;border-radius:999px;padding:6px 14px;
        font-size:0.78rem;font-weight:600;margin-right:8px;margin-top:8px;}
    .bpa-bar-wrap{margin-bottom:16px;}
    .bpa-bar{height:14px;border-radius:999px;overflow:hidden;display:flex;background:#2C2C2E;}
    .bpa-bar-label{display:flex;justify-content:space-between;font-size:0.72rem;color:#9DA3AE;margin-top:6px;}
    .bpa-guide-card{background:#EAFAEE;border-radius:16px;padding:14px 16px;text-align:center;height:100%;}
    .bpa-guide-card .gi{font-size:1.6rem;}
    .bpa-guide-card .gt{font-weight:800;color:#1C1C1E;font-size:0.9rem;margin:6px 0 2px 0;}
    .bpa-guide-card .gd{font-size:0.78rem;color:#5C6B60;}
    .bpa-pro-item{font-size:0.9rem;color:#1C1C1E;margin:4px 0;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"#### 🌐 {T('Buscador FatSecret (externo)', 'FatSecret Search (external)')}")
    consulta_fs = st.text_input(T("Escribe el nombre de un alimento para buscarlo en FatSecret:",
                                   "Type the name of a food to search it on FatSecret:"),
                                 "", key="bpa_buscar_fatsecret")
    if consulta_fs.strip():
        url_fs = f"https://www.fatsecret.es/calor%C3%ADas-nutrici%C3%B3n/search?q={quote(consulta_fs.strip())}"
        _label_fs = T(f"Ver '{consulta_fs}' en FatSecret", f"View '{consulta_fs}' on FatSecret")
        st.link_button(f"🔍 {_label_fs}", url_fs, use_container_width=True)
    else:
        st.link_button(T("🌐 Abrir FatSecret", "🌐 Open FatSecret"), "https://www.fatsecret.es/", use_container_width=True)
    st.markdown(f"""
    <div style="background:#E6F7FA;border-left:5px solid #30B0C7;border-radius:16px;padding:14px 18px;margin:14px 0;">
    <b style="color:#0B7285;">🌐 {T('¿Por qué usamos FatSecret?', 'Why do we use FatSecret?')}</b><br>
    <span style="color:#1C1C1E;font-size:0.9rem;">{T(
        "Es una base de datos externa y muy amplia, con miles de alimentos, marcas y productos "
        "envasados peruanos e internacionales. La usamos como <b>respaldo rápido</b> cuando buscas "
        "un producto comercial específico o algo que no forma parte de nuestra Base Peruana de "
        "Alimentos.",
        "It is a very large external database, with thousands of foods, brands, and packaged "
        "products, both Peruvian and international. We use it as a <b>quick backup</b> when you "
        "search for a specific commercial product or something that isn't part of our Peruvian "
        "Food Database."
    )}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"#### 🔎 {T('Buscador Nutricional · Tabla Peruana de Composición de Alimentos', 'Nutritional Search · Peruvian Food Composition Table')}")
    consulta = st.text_input(T("Escribe el nombre de un alimento (p. ej. 'palta', 'pollo', 'arroz'):",
                                "Type the name of a food (e.g. 'palta', 'pollo', 'arroz'):"),
                              "", key="bpa_buscar")

    resultados = buscar_alimentos(consulta) if consulta.strip() else []

    alimento_sel = None
    if consulta.strip() and resultados:
        opciones = [f"{_nombre_alimento(r['nombre'])} · {GRUPOS_ALIMENTOS[r['grupo_cod']]['icono']} {_grupo_campo(r['grupo_cod'], 'nombre')}" for r in resultados]
        idx_sel = st.selectbox(T("Coincidencias encontradas:", "Matches found:"), range(len(opciones)),
                                format_func=lambda i: opciones[i], key="bpa_sel")
        alimento_sel = resultados[idx_sel]
    elif consulta.strip() and not resultados:
        st.warning(T(
            f"No encontramos '{consulta}' en la Base Peruana de Alimentos (343 alimentos curados de mayor "
            "consumo). Puedes buscarlo en el buscador de FatSecret de arriba como respaldo.",
            f"We couldn't find '{consulta}' in the Peruvian Food Database (343 curated foods of "
            "highest consumption). You can search for it in the FatSecret search above as a backup."
        ))

    if alimento_sel:
        f = alimento_sel
        g_nombre = _grupo_campo(f["grupo_cod"], "nombre")
        g_icono = GRUPOS_ALIMENTOS[f["grupo_cod"]]["icono"]
        g_aporta = _grupo_campo(f["grupo_cod"], "aporta")
        g_tips = _grupo_campo(f["grupo_cod"], "tips")
        nombre_mostrado = _nombre_alimento(f["nombre"])

        def _m(v, suf=""):
            return f"{v:g}{suf}" if v is not None else T("s/d", "n/a")

        kcal, prot, gras, cho, fibra = f["kcal"], f["proteinas"], f["grasas"], f["cho"], f["fibra"]
        _lbl_gras, _lbl_carb, _lbl_prot = T("Grasas", "Fat"), T("Carbohidratos", "Carbohydrates"), T("Proteínas", "Protein")
        partes = [(_lbl_gras, gras, "#FF9500"), (_lbl_carb, cho, "#30B0C7"), (_lbl_prot, prot, "#34C759")]
        total_e = sum((p[1] or 0) * (9 if p[0] == _lbl_gras else 4) for p in partes)
        barras = ""
        etiquetas = []
        if total_e > 0:
            for nombre_p, val, color in partes:
                pct = round(((val or 0) * (9 if nombre_p == _lbl_gras else 4) / total_e) * 100)
                if pct > 0:
                    barras += f'<div style="width:{pct}%;background:{color};"></div>'
                    etiquetas.append(f"{nombre_p} {pct}%")

        st.markdown(f"""
        <div class="bpa-card">
            <h3>{g_icono} {nombre_mostrado}</h3>
            <div class="bpa-sub">{g_nombre} · {T('código', 'code')} {f['codigo']}</div>
            <div class="bpa-sub" style="margin-top:-10px;">{T('Resumen nutricional · por 100 g de porción comestible', 'Nutritional summary · per 100 g of edible portion')}</div>
            <div class="bpa-grid">
                <div class="bpa-metric"><div class="lbl">🔥 {T('Energía', 'Energy')}</div><div class="val">{_m(kcal,' kcal')}</div></div>
                <div class="bpa-metric"><div class="lbl">💪 {T('Proteínas', 'Protein')}</div><div class="val">{_m(prot,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🥑 {T('Grasas', 'Fat')}</div><div class="val">{_m(gras,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🍞 {T('Carbohidratos', 'Carbohydrates')}</div><div class="val">{_m(cho,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🌾 {T('Fibra', 'Fiber')}</div><div class="val">{_m(fibra,' g')}</div></div>
            </div>
            {"<div class='bpa-bar-wrap'><div style='font-size:0.78rem;color:#9DA3AE;margin-bottom:6px;'>" + T('Distribución energética', 'Energy distribution') + "</div><div class='bpa-bar'>" + barras + "</div><div class='bpa-bar-label'>" + " · ".join(etiquetas) + "</div></div>" if barras else ""}
            <div class="bpa-source">📚 {T('Según la Tabla Peruana de Composición de Alimentos (INS/CENAN, 11.ª edición digital, 2025). Valores por 100 g de porción comestible.', 'According to the Peruvian Food Composition Table (INS/CENAN, 11th digital edition, 2025). Values per 100 g of edible portion.')}</div>
            <div style="font-weight:700;color:#F2F2F7;margin-bottom:4px;">{T('¿Qué aporta principalmente?', 'What does it mainly provide?')}</div>
            <div class="bpa-tips">{g_icono} {g_aporta}</div>
            <div style="font-weight:700;color:#F2F2F7;margin:12px 0 4px 0;">{T('Recomendaciones', 'Recommendations')}</div>
            {''.join(f'<div class="bpa-tips">✔ {t}</div>' for t in g_tips)}
            <div>
                <span class="bpa-chip">🍽️ {T('Macronutrientes', 'Macronutrients')}</span>
                <span class="bpa-chip">📋 {T('Dieta', 'Diet')}</span>
                <span class="bpa-chip">⚖️ {T('Control de peso', 'Weight Control')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if f["calcio"] is not None or f["hierro"] is not None or f["vitc"] is not None:
            st.markdown(
                f"<div style='color:#5C6B60;font-size:0.85rem;margin-top:-8px;'>"
                f"{T('Además, cada 100 g aportan:', 'Additionally, each 100 g provides:')} "
                f"{'🦴 ' + T('Calcio', 'Calcium') + ' ' + _m(f['calcio'],' mg') + '  ' if f['calcio'] is not None else ''}"
                f"{'🩸 ' + T('Hierro', 'Iron') + ' ' + _m(f['hierro'],' mg') + '  ' if f['hierro'] is not None else ''}"
                f"{'🍊 ' + T('Vitamina C', 'Vitamin C') + ' ' + _m(f['vitc'],' mg') if f['vitc'] is not None else ''}"
                f"</div>", unsafe_allow_html=True)

    elif not consulta.strip():
        with st.expander(T("🗂️ Ver los 14 grupos de alimentos disponibles", "🗂️ View the 14 Available Food Groups")):
            cols_g = st.columns(4)
            for i, (cod, g) in enumerate(GRUPOS_ALIMENTOS.items()):
                n_items = sum(1 for x in FOOD_DB if x["grupo_cod"] == cod)
                cb, cf = GRUPOS_COLORES.get(cod, ("#8E8E93", "#F2F2F7"))
                with cols_g[i % 4]:
                    st.markdown(f"""
                    <div style="background:{cf};border-left:4px solid {cb};border-radius:12px;
                        padding:10px 12px;margin-bottom:10px;">
                        <div style="font-weight:800;color:{cb};font-size:0.88rem;">{g['icono']} {_grupo_campo(cod, 'nombre')}</div>
                        <div style="color:#5C6B60;font-size:0.78rem;">{n_items} {T('alimentos', 'foods')}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#EAFAEE;border-left:5px solid #34C759;border-radius:16px;padding:14px 18px;margin:14px 0;">
    <b style="color:#1E5631;">🇵🇪 {T('¿Por qué usamos la Tabla Peruana de Composición de Alimentos?', 'Why do we use the Peruvian Food Composition Table?')}</b><br>
    <span style="color:#1C1C1E;font-size:0.9rem;">{T(
        "Es la fuente <b>oficial y nacional</b> (INS/CENAN), elaborada con alimentos y "
        "preparaciones típicas del Perú. Sus valores son más precisos para nuestra población que "
        "una base genérica, por eso es la base principal del buscador, y FatSecret queda como "
        "respaldo complementario.",
        "It is the <b>official, national source</b> (INS/CENAN), built from foods and "
        "preparations typical of Peru. Its values are more accurate for our population than a "
        "generic database, which is why it's the main source for the search tool, with FatSecret "
        "as a complementary backup."
    )}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### 🍽️ {T('Guía Alimentaria Peruana', 'Peruvian Dietary Guidelines')}")
    _guias = GUIAS_ALIMENTARIAS_PERU_EN if st.session_state.get("idioma", "Español") == "English" else GUIAS_ALIMENTARIAS_PERU
    cols_guia = st.columns(3)
    for i, (icono, titulo, desc) in enumerate(_guias):
        with cols_guia[i % 3]:
            st.markdown(f"""
            <div class="bpa-guide-card">
                <div class="gi">{icono}</div>
                <div class="gt">{titulo}</div>
                <div class="gd">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.caption(T("Basado en las Guías Alimentarias para la Población Peruana (MINSA).",
                 "Based on the Dietary Guidelines for the Peruvian Population (MINSA)."))

    st.markdown(f"### 🗂️ {T('Alimentos disponibles en el buscador', 'Available Foods in the Database')}")
    st.caption(T(
        "343 alimentos curados de mayor consumo en el Perú, agrupados por categoría, con su "
        "energía (kcal) por 100 g de porción comestible. Cada grupo tiene su propio color para "
        "ubicarlo más fácil.",
        "343 curated foods of highest consumption in Peru, grouped by category, with their "
        "energy (kcal) per 100 g of edible portion. Each group has its own color to make it "
        "easier to locate."
    ))
    orden_grupos = sorted(GRUPOS_ALIMENTOS.items(), key=lambda kv: -sum(1 for x in FOOD_DB if x["grupo_cod"] == kv[0]))
    for cod, g in orden_grupos:
        g_nombre = _grupo_campo(cod, "nombre")
        items_g = sorted([x for x in FOOD_DB if x["grupo_cod"] == cod], key=lambda x: x["nombre"])
        color_borde, color_fondo = GRUPOS_COLORES.get(cod, ("#8E8E93", "#F2F2F7"))

        filas_html = ""
        vistos = set()
        for it in items_g:
            nombre_limpio = _nombre_alimento(_limpiar_nombre_alimento(it["nombre"]))
            if not nombre_limpio or nombre_limpio.lower() in vistos:
                continue
            vistos.add(nombre_limpio.lower())
            kcal_txt = f"{it['kcal']:g} kcal" if it["kcal"] is not None else T("s/d", "n/a")
            filas_html += (
                f"<tr><td style='padding:9px 16px;border-bottom:1px solid {color_fondo};color:#1C1C1E;font-size:0.86rem;'>"
                f"{nombre_limpio}</td>"
                f"<td style='padding:9px 16px;border-bottom:1px solid {color_fondo};text-align:right;"
                f"font-weight:700;color:{color_borde};white-space:nowrap;font-size:0.86rem;'>{kcal_txt}</td></tr>"
            )

        with st.expander(f"{g['icono']} {g_nombre} · {len(items_g)} {T('alimentos', 'foods')}"):
            st.markdown(f"""
            <div style="border-radius:18px;overflow:hidden;border:1px solid {color_fondo};
                box-shadow:0 1px 2px rgba(0,0,0,0.06),0 6px 18px rgba(0,0,0,0.06);">
              <div style="background:{color_borde};color:#FFFFFF;padding:12px 18px;font-weight:800;
                  font-size:0.95rem;display:flex;justify-content:space-between;align-items:center;">
                <span>{g['icono']} {g_nombre}</span>
                <span style="background:rgba(255,255,255,0.25);border-radius:999px;padding:3px 12px;font-size:0.72rem;">
                    {len(items_g)} {T('alimentos', 'foods')}</span>
              </div>
              <div style="max-height:360px;overflow-y:auto;background:#FFFFFF;">
                <table style="width:100%;border-collapse:collapse;">
                  <thead>
                    <tr style="background:{color_fondo};position:sticky;top:0;">
                      <th style="text-align:left;padding:9px 16px;color:{color_borde};font-size:0.7rem;
                          text-transform:uppercase;letter-spacing:0.03em;">{T('Alimento', 'Food')}</th>
                      <th style="text-align:right;padding:9px 16px;color:{color_borde};font-size:0.7rem;
                          text-transform:uppercase;letter-spacing:0.03em;">{T('Energía / 100 g', 'Energy / 100 g')}</th>
                    </tr>
                  </thead>
                  <tbody>{filas_html}</tbody>
                </table>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"### 📚 {T('Información para profesionales', 'Information for Healthcare Professionals')}")
    with st.container():
        st.markdown(f"""
        <div style="background:#F2F2F7;border-radius:18px;padding:18px 22px;">
        <div class="bpa-pro-item">✔ {T('Valores expresados por 100 g de porción comestible.', 'Values expressed per 100 g of edible portion.')}</div>
        <div class="bpa-pro-item">✔ {T('Basado en la Tabla Peruana de Composición de Alimentos, INS/CENAN.', 'Based on the Peruvian Food Composition Table, INS/CENAN.')}</div>
        <div class="bpa-pro-item">✔ {T('Utilizar porciones individualizadas según el caso.', 'Use individualized portions based on the case.')}</div>
        <div class="bpa-pro-item">✔ {T('Ajustar según edad.', 'Adjust according to age.')}</div>
        <div class="bpa-pro-item">✔ {T('Ajustar según condición clínica.', 'Adjust according to clinical condition.')}</div>
        <div class="bpa-pro-item">✔ {T('Ajustar según evaluación nutricional.', 'Adjust according to nutritional assessment.')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#EAFAEE;border-left:5px solid #1E5631;border-radius:16px;padding:16px 20px;margin-top:14px;">
    <b style="color:#1E5631;">👩‍⚕️ {T('Criterio profesional', 'Professional Criteria')}</b><br>
    <span style="color:#1C1C1E;">{T(
        "Las porciones, intercambios y recomendaciones específicas deben ser definidas por el "
        "nutricionista responsable, considerando la evaluación clínica, nutricional y los "
        "objetivos individuales del paciente.",
        "Specific portions, exchanges, and recommendations should be defined by the responsible "
        "nutritionist, taking into account the clinical and nutritional assessment and the "
        "patient's individual goals."
    )}</span>
    </div>
    """, unsafe_allow_html=True)

    caja_util(T(
        "Busca cualquier alimento peruano de consumo frecuente y obtén al instante su información "
        "nutricional oficial (INS/CENAN): calorías, proteínas, grasas, carbohidratos y fibra por "
        "cada 100 g, junto con recomendaciones prácticas según su grupo alimenticio. Ya no depende "
        "de FatSecret. 🇵🇪🥗",
        "Search for any commonly eaten Peruvian food and instantly get its official nutritional "
        "information (INS/CENAN): calories, protein, fat, carbohydrates, and fiber per 100 g, "
        "along with practical recommendations based on its food group. No longer dependent on "
        "FatSecret. 🇵🇪🥗"
    ), emoji="🇵🇪", color="#E0F2F1", borde="#00796B")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "9.-DIETA":
    hoja_header(9, T(
        "Elige un alimento por macronutriente en cada comida y arma tu menú diario personalizado.",
        "Choose one food per macronutrient for each meal and build your personalized daily menu."
    ))

    # =====================================================================================
    # SECCIÓN 1 — Panel de Resumen de Datos Nutricionales
    # =====================================================================================
    st.markdown(f"""
    <p style="text-align:center;color:#5C6B60;font-size:0.94rem;max-width:720px;margin:0 auto 14px auto;">
    {T(
        "Estos valores han sido calculados previamente en base a tu perfil. A continuación, te presentamos el "
        "resumen de tus requerimientos calóricos diarios y cómo se distribuyen en tu día a día.",
        "These values were previously calculated based on your profile. Below is a summary of your daily "
        "caloric requirements and how they are distributed throughout your day."
    )}
    </p>
    """, unsafe_allow_html=True)

    _ICONOS_COMIDA_D9 = {"Desayuno": "🌅", "Merienda 1": "🍎", "Almuerzo": "🍽️", "Merienda 2": "🥪", "Cena": "🌙"}
    _MOMENTO_EN_D9 = {"Desayuno": "Breakfast", "Merienda 1": "Morning Snack", "Almuerzo": "Lunch",
                      "Merienda 2": "Afternoon Snack", "Cena": "Dinner"}
    _MACRO_EN_D9 = {"Carbohidrato": "Carbohydrate", "Proteína": "Protein", "Grasa": "Fat"}

    def _mom(nombre):
        """Traduce un nombre de comida (clave interna en español) según el idioma elegido."""
        return T(nombre, _MOMENTO_EN_D9.get(nombre, nombre))

    def _mac(nombre):
        """Traduce un nombre de macronutriente (clave interna en español) según el idioma elegido."""
        return T(nombre, _MACRO_EN_D9.get(nombre, nombre))

    _filas_tiempos_html = "".join(
        f"""<div class="rn-tiempos-row"><span>{_ICONOS_COMIDA_D9[_c]} {_mom(_c)}</span>
            <span class="rn-kcal">{porciones[_c]['kcal']:.2f} kcal</span></div>"""
        for _c in porciones
    )

    _html_resumen_nutri = f"""
    <div class="resumen-nutri-wrap">
        <div class="resumen-nutri-card rn-tiempos">
            <div class="rn-title">⏰ {T('Distribución por Tiempos del Día', 'Distribution Throughout the Day')}</div>
            {_filas_tiempos_html}
        </div>
        <div class="resumen-nutri-card rn-macros">
            <div class="rn-title">🍽️ {T('Distribución de Macronutrientes', 'Macronutrient Distribution')}</div>
            <div class="rn-macro-row">🥩 {T('Proteínas', 'Protein')}
                <span class="rn-macro-pill" style="background:#FFEDEC;color:#C0392B;">{gr_prot:.2f} g</span></div>
            <div class="rn-macro-row">🌾 {T('Carbohidratos', 'Carbohydrates')}
                <span class="rn-macro-pill" style="background:#FFF3E0;color:#E67E22;">{gr_carb:.2f} g</span></div>
            <div class="rn-macro-row">🥑 {T('Grasas', 'Fats')}
                <span class="rn-macro-pill" style="background:#EAFAEE;color:#1E5631;">{gr_gras:.2f} g</span></div>
        </div>
        <div class="resumen-nutri-card rn-rcd">
            <div class="rn-title" style="justify-content:center;color:#FFFFFF;">🎯 {T('Requerimiento Calórico Diario', 'Daily Caloric Requirement')}</div>
            <div class="rn-rcd-value">{rcd_final:.2f}</div>
            <div style="font-size:0.85rem;opacity:0.9;">{T('kcal / día', 'kcal / day')}</div>
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_resumen_nutri), unsafe_allow_html=True)

    # =====================================================================================
    # SECCIÓN 2 — Interfaz de Selección de Alimentos
    # =====================================================================================
    st.markdown(f'<div class="selector-menu-title">🍱 {T("¡Personaliza tu Menú! Selecciona tus Alimentos", "Customize Your Menu! Choose Your Foods")}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="selector-menu-sub">{T("Elige una fuente de carbohidrato, proteína y grasa para cada momento del día.", "Choose a source of carbohydrate, protein, and fat for each time of day.")}</p>', unsafe_allow_html=True)

    if genero == "Mujer" and embarazada:
        st.warning("🤰 " + T(
            "Modo Embarazo activo: se ocultaron los alimentos crudos/semicocidos (ceviche, sushi, "
            "tártaros), carnes término medio, huevo crudo, mayonesa casera, embutidos sin cocinar "
            "(jamón serrano) y lácteos artesanales no pasteurizados, por riesgo de Listeria, "
            "Salmonella y Toxoplasma (FDA — Seguridad Alimentaria para Futuras Mamás).",
            "Pregnancy Mode Active: raw/undercooked foods (ceviche, sushi, tartare), medium-rare meats, "
            "raw egg, homemade mayonnaise, uncooked cured meats (serrano ham), and unpasteurized "
            "artisanal dairy have been hidden due to the risk of Listeria, Salmonella, and Toxoplasma "
            "(FDA — Food Safety for Moms-to-Be)."
        ))

    seleccion = {}
    for comida in DIETA:
        st.markdown(f'<div class="comida-momento-banner">{_ICONOS_COMIDA_D9[comida]} {_mom(comida).upper()}</div>',
                    unsafe_allow_html=True)
        _opciones_carb = dieta_filtrada_para(comida, "Carbohidrato", embarazada)
        _opciones_prot = dieta_filtrada_para(comida, "Proteína", embarazada)
        _opciones_gras = dieta_filtrada_para(comida, "Grasa", embarazada)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="macro-select-label carb">🌾 {_mac("Carbohidrato")}</div>', unsafe_allow_html=True)
            carb_sel = st.selectbox(f"{_mac('Carbohidrato')} — {_mom(comida)}", list(_opciones_carb.keys()),
                                     format_func=_dieta_nombre,
                                     key=f"c_{comida}", label_visibility="collapsed")
        with c2:
            st.markdown(f'<div class="macro-select-label prot">🥩 {_mac("Proteína")}</div>', unsafe_allow_html=True)
            prot_sel = st.selectbox(f"{_mac('Proteína')} — {_mom(comida)}", list(_opciones_prot.keys()),
                                     format_func=_dieta_nombre,
                                     key=f"p_{comida}", label_visibility="collapsed")
        with c3:
            st.markdown(f'<div class="macro-select-label gras">🥑 {_mac("Grasa")}</div>', unsafe_allow_html=True)
            gras_sel = st.selectbox(f"{_mac('Grasa')} — {_mom(comida)}", list(_opciones_gras.keys()),
                                     format_func=_dieta_nombre,
                                     key=f"g_{comida}", label_visibility="collapsed")
        seleccion[comida] = {
            "Carbohidrato": carb_sel,
            "Proteína": prot_sel,
            "Grasa": gras_sel,
        }

    # Guardado explícito y estable del plan elegido: no dependemos de que las claves individuales
    # c_/p_/g_ de cada selectbox sigan existiendo o coincidiendo con las opciones filtradas (p.ej.
    # si el modo Embarazo se activa/desactiva y cambia la lista de alimentos disponibles). Este
    # diccionario es la única fuente de verdad que usan luego "Mi Reporte" y el PDF.
    st.session_state["dieta_guardada"] = seleccion

    # % de cada macronutriente dentro del total de calorías de CADA momento (igual que N/S/X del Excel: 50/20/30%)
    PCT_MACRO_MOMENTO = {"Carbohidrato": 0.50, "Proteína": 0.20, "Grasa": 0.30}

    filas = []
    suma_kcal_carb = suma_kcal_prot = suma_kcal_gras = 0
    suma_porcion_carb = suma_porcion_prot = suma_porcion_gras = 0
    suma_gramos_carb = suma_gramos_prot = suma_gramos_gras = 0

    for comida, alimentos in seleccion.items():
        fila = {"Momento": comida}
        for macro, col_prefix in [("Carbohidrato", "Carb"), ("Proteína", "Prot"), ("Grasa", "Gras")]:
            alimento = alimentos[macro]
            kcal_alimento = DIETA[comida][macro][alimento]
            porcion_kcal = round(porciones[comida]["kcal"] * PCT_MACRO_MOMENTO[macro], 2)
            gramos = min(round((porcion_kcal / kcal_alimento) * 100, 1), 400.0)
            fila[macro] = alimento
            fila[f"kcal ({col_prefix})"] = kcal_alimento
            fila[f"Porción corregida ({col_prefix})"] = porcion_kcal
            fila[f"Gramos ({col_prefix})"] = gramos
        filas.append(fila)
        suma_kcal_carb += fila["kcal (Carb)"]; suma_porcion_carb += fila["Porción corregida (Carb)"]
        suma_kcal_prot += fila["kcal (Prot)"]; suma_porcion_prot += fila["Porción corregida (Prot)"]
        suma_kcal_gras += fila["kcal (Gras)"]; suma_porcion_gras += fila["Porción corregida (Gras)"]
        suma_gramos_carb += fila["Gramos (Carb)"]; suma_gramos_prot += fila["Gramos (Prot)"]
        suma_gramos_gras += fila["Gramos (Gras)"]

    total_general = round(suma_porcion_carb + suma_porcion_prot + suma_porcion_gras, 2)

    # =====================================================================================
    # SECCIÓN 3 — Muestra de la Dieta Tipo Menú (3 tablas de color + barra total)
    # =====================================================================================
    st.markdown(f'<div class="menu-titulo-grande">🍽️ {T("MUESTRA DE TU DIETA TIPO MENÚ", "PREVIEW OF YOUR MENU-STYLE DIET")}</div>', unsafe_allow_html=True)

    def _tabla_menu_macro(clase_css, icono, titulo, macro_key, suma_kcal, suma_porcion, suma_gramos):
        """Construye una de las 3 tablas de color (Carbohidrato / Proteína / Grasa) con fila TOTAL."""
        _prefijo = {"Carbohidrato": "Carb", "Proteína": "Prot", "Grasa": "Gras"}[macro_key]
        filas_html = ""
        for f in filas:
            filas_html += f"""
            <tr>
                <td class="dm-momento">{_ICONOS_COMIDA_D9[f['Momento']]} {_mom(f['Momento'])}</td>
                <td>{_dieta_nombre(f[macro_key])}</td>
                <td>{f[f'kcal ({_prefijo})']} kcal</td>
                <td>{f[f'Porción corregida ({_prefijo})']:.1f} kcal</td>
                <td>{f[f'Gramos ({_prefijo})']:.1f} g</td>
            </tr>"""
        filas_html += f"""
            <tr class="dm-total">
                <td class="dm-momento" colspan="2">{T('TOTAL', 'TOTAL')}</td>
                <td>—</td>
                <td>{suma_porcion:.1f} kcal</td>
                <td>{suma_gramos:.1f} g</td>
            </tr>"""
        html = f"""
        <div class="dieta-menu-wrap {clase_css}">
        <table class="dieta-menu-table">
            <thead>
            <tr><th style="text-align:left;">{T('Momento', 'Meal')}</th><th>{icono} {T('Alimento', 'Food')} ({_mac(titulo)})</th>
                <th>{T('Kcal/100g', 'Kcal/100g')}</th><th>{T('Porción Corregida', 'Adjusted Portion')}</th><th>{T('Gramos Finales', 'Final Grams')}</th></tr>
            </thead>
            <tbody>
            {filas_html}
            </tbody>
        </table>
        </div>
        """
        st.markdown(_html_sin_lineas_vacias(html), unsafe_allow_html=True)

    _tabla_menu_macro("carb", "🌾", "Carbohidrato", "Carbohidrato", suma_kcal_carb, suma_porcion_carb, suma_gramos_carb)
    _tabla_menu_macro("prot", "🥩", "Proteína", "Proteína", suma_kcal_prot, suma_porcion_prot, suma_gramos_prot)
    _tabla_menu_macro("gras", "🥑", "Grasa", "Grasa", suma_kcal_gras, suma_porcion_gras, suma_gramos_gras)

    # ---- Barra final destacada: suma total = RCD ----
    _diferencia_total = abs(total_general - rcd_final)
    _check_txt = (T("✅ ¡Coincide exactamente con tu RCD!", "✅ Exactly matches your DCR!") if _diferencia_total < 1
                  else T(f"⚠️ Diferencia de {_diferencia_total:.1f} kcal respecto a tu RCD",
                         f"⚠️ Difference of {_diferencia_total:.1f} kcal from your DCR"))
    _html_barra_total = f"""
    <div class="dieta-total-bar">
        <div class="dt-label">🌾 {T('Carbohidratos', 'Carbohydrates')} + 🥩 {T('Proteínas', 'Protein')} + 🥑 {T('Grasas', 'Fats')}</div>
        <div class="dt-formula">{suma_porcion_carb:.1f} kcal + {suma_porcion_prot:.1f} kcal + {suma_porcion_gras:.1f} kcal</div>
        <div class="dt-value">= {total_general:.1f} kcal</div>
        <div style="font-size:0.9rem;opacity:0.92;">{T('Este total equivale a tu', 'This total equals your')} <b>{T('TOTAL DE CALORÍAS DIARIAS (RCD)', 'TOTAL DAILY CALORIC REQUIREMENT (DCR)')}</b></div>
        <div class="dt-check">{_check_txt}</div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_barra_total), unsafe_allow_html=True)

    st.divider()
    st.markdown(f"#### ❓ {T('Guía para entender tu tabla de dieta', 'Guide to Understanding Your Diet Table')}")
    FAQ_DIETA_ES = {
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
    FAQ_DIETA_EN = {
        "What does the 'kcal' column mean?": (
            "It's the amount of calories that food provides, taken as a reference per 100 grams "
            "of that food (as defined in the project's nutritional database)."
        ),
        "What does 'Adjusted Portion' mean?": (
            "It's how many calories from that time of day (Breakfast, Lunch, etc.) correspond to that "
            "specific macronutrient. For example, if Lunch has 1000 kcal in total, the Adjusted Portion "
            "of Carbohydrate will be 50% of those 1000 kcal, Protein 20%, and Fat 30%."
        ),
        "What does 'Final grams to consume' mean?": (
            "It's the exact amount, in grams, you should eat of THAT specific food to reach the Adjusted "
            "Portion in calories. It's calculated by dividing the Adjusted Portion by the food's kcal and "
            "multiplying by 100."
        ),
        "So, how much do I have to eat at each meal?": (
            "You should prepare the three foods you chose for that time of day (Carbohydrate, Protein, and "
            "Fat), each in the amount of 'Final grams to consume' shown in the table. Together, those three "
            "foods complete the calories that correspond to that meal."
        ),
        "Why does the total match my target calories?": (
            "Because the system distributes your daily caloric target (Sheet 5) first across the 5 times of "
            "day (Sheet 7), and then, within each time, across the 3 macronutrients. Adding everything back "
            "up, the result should match your original caloric target."
        ),
    }
    FAQ_DIETA = FAQ_DIETA_EN if st.session_state.get("idioma", "Español") == "English" else FAQ_DIETA_ES
    pregunta_dieta = st.selectbox(T("Elige una pregunta sobre tu tabla de dieta:", "Choose a question about your diet table:"),
                                   list(FAQ_DIETA.keys()), key="faq_dieta")
    st.info(FAQ_DIETA[pregunta_dieta])

    recursos_externos(9, [
        (T("🌐 Buscar alimentos en FatSecret", "🌐 Search foods on FatSecret"), "https://www.fatsecret.es/"),
    ])
    caja_util(T(
        "Aquí armas tu menú real del día eligiendo alimentos que te gusten, y la app hace toda la "
        "matemática por ti: cada momento del día reparte sus calorías en 50% carbohidratos, 20% proteínas "
        "y 30% grasas, y luego convierte esas calorías a gramos según el alimento específico que elegiste "
        "— exactamente igual que en la hoja de cálculo original. ¡Comer sano también puede ser rico! 😋",
        "Here you build your real menu for the day by choosing foods you like, and the app does all the "
        "math for you: each time of day splits its calories into 50% carbohydrates, 20% protein, and "
        "30% fat, then converts those calories to grams based on the specific food you chose — exactly "
        "like in the original spreadsheet. Eating healthy can taste great too! 😋"
    ), emoji="🍱", color="#FBE9E7", borde="#FF7043")

elif hoja_activa == "12.-APORTE 2: CAFEÍNA" and genero == "Mujer" and embarazada:
    hoja_header(12, subtitulo=T(
        "En el embarazo, el hígado procesa la cafeína mucho más lento (su vida media "
        "sube hasta 15 horas) y atraviesa la placenta libremente. Por eso, en Modo "
        "Embarazo esta hoja deja de calcular horarios de sueño y se convierte en un "
        "tope fijo de consumo diario.",
        "During pregnancy, the liver processes caffeine much more slowly (its half-life "
        "rises to up to 15 hours) and it crosses the placenta freely. That's why, in "
        "Pregnancy Mode, this sheet stops calculating sleep schedules and becomes a "
        "fixed daily intake cap."
    ), tip=T("☕ Máximo 200 mg de cafeína al día", "☕ Maximum 200 mg of caffeine per day"))
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        T("Límite gestacional = 200 mg de cafeína / día (tope fijo, no calculadora de horario)",
          "Gestational limit = 200 mg of caffeine / day (fixed cap, not a schedule calculator)"),
        referencia=T("Organización Mundial de la Salud (OMS) — Recomendaciones sobre Atención Prenatal",
                      "World Health Organization (WHO) — Antenatal Care Recommendations"))}</div>""",
        unsafe_allow_html=True)
    st.error("🚫 " + T(
        "**Máximo 200 mg de cafeína al día.** Superar esta dosis se asocia a restricción del "
        "crecimiento intrauterino y bajo peso al nacer (OMS). Referencia rápida: 1 taza de café "
        "filtrado ≈ 95 mg · 1 taza de té ≈ 47 mg · 1 lata de gaseosa cola ≈ 34 mg · 1 barra de "
        "chocolate negro (50 g) ≈ 25 mg.",
        "**Maximum 200 mg of caffeine per day.** Exceeding this dose is associated with intrauterine "
        "growth restriction and low birth weight (WHO). Quick reference: 1 cup of filtered coffee ≈ "
        "95 mg · 1 cup of tea ≈ 47 mg · 1 can of cola soda ≈ 34 mg · 1 dark chocolate bar (50 g) ≈ 25 mg."
    ))
    st.caption("⚕️ " + T(
        "Esta herramienta es orientativa y no reemplaza la indicación de tu médico "
        "ginecólogo-obstetra o nutricionista.",
        "This tool is for guidance only and does not replace the advice of your "
        "OB-GYN doctor or nutritionist."
    ))

elif hoja_activa == "12.-APORTE 2: CAFEÍNA":
    hoja_header(12, subtitulo=T(
        "Dormir bien también ayuda a cuidar tu alimentación. La cafeína puede permanecer "
        "varias horas en el organismo. Esta herramienta calcula hasta qué hora puedes "
        "consumir café sin afectar tu descanso.",
        "Sleeping well also helps you take care of your diet. Caffeine can stay in your "
        "body for several hours. This tool calculates the latest time you can have "
        "coffee without affecting your rest."
    ), tip=T("🌙 −8 horas antes de dormir", "🌙 −8 hours before sleeping"))
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        T("Hora_Límite_Cafeína = Hora_Dormir − 8 horas", "Caffeine_Cutoff_Time = Bedtime − 8 hours"),
        referencia=T("Principio de Vida Media de la Cafeína (FDA / AASM)",
                      "Caffeine Half-Life Principle (FDA / AASM)"))}</div>""", unsafe_allow_html=True)

    # --- PASO 1: ¿A qué hora sueles dormir? (selector amigable AM/PM) --------------------
    st.markdown(f"##### ① 🛏️ {T('¿A qué hora sueles dormir?', 'What time do you usually go to sleep?')}")
    _opciones_hora, _t_cursor = [], datetime.strptime("00:00", "%H:%M")
    for _ in range(48):
        _opciones_hora.append(_t_cursor)
        _t_cursor += timedelta(minutes=30)
    _etiquetas_hora = [f"🌙 {t.strftime('%I:%M %p').lstrip('0')}" for t in _opciones_hora]
    _idx_default = next((i for i, t in enumerate(_opciones_hora) if t.strftime("%H:%M") == "22:00"), 6)
    _sel_hora = st.selectbox(T("Hora de dormir:", "Bedtime:"), _etiquetas_hora, index=_idx_default, label_visibility="collapsed")
    hora_dormir = _opciones_hora[_etiquetas_hora.index(_sel_hora)].time()
    dt_dormir = datetime.combine(datetime.today(), hora_dormir)
    dt_limite = dt_dormir - timedelta(hours=8)
    _fmt = lambda dt: dt.strftime('%I:%M %p').lstrip('0')

    st.write("")

    # --- PASO 2: ✅ Tu resultado — bloque grande con las 3 preguntas clave ----------------
    st.markdown(f"##### ② ✅ {T('Tu resultado', 'Your result')}")
    st.markdown(f"""
    <div class="cp5-glass-flow">
        <div class="cp5-flow-card" style="background:rgba(27,42,74,0.08);border-color:rgba(27,42,74,0.3);">
            <div class="cp5-flow-label">🛏️ {T('Hora para dormir', 'Bedtime')}</div>
            <div class="cp5-flow-value" style="color:#1B2A4A;">{_fmt(dt_dormir)}</div>
            <div class="cp5-flow-legend">{T('La hora en la que sueles acostarte.', 'The time you usually go to bed.')}</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card" style="background:rgba(255,179,0,0.14);border-color:rgba(255,179,0,0.4);">
            <div class="cp5-flow-label">☕ {T('Último café recomendado', 'Recommended last coffee')}</div>
            <div class="cp5-flow-value" style="color:#B06000;">{_fmt(dt_limite)}</div>
            <div class="cp5-flow-legend">{T('Después de esa hora, la cafeína aún podría estar activa al dormir.', 'After this time, caffeine could still be active while you sleep.')}</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">⏱️ {T('Diferencia recomendada', 'Recommended gap')}</div>
            <div class="cp5-flow-value">{T('8 horas', '8 hours')}</div>
            <div class="cp5-flow-legend">{T('Tiempo mínimo entre tu última cafeína y dormir.', 'Minimum time between your last caffeine and sleeping.')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # --- PASO 3: Línea de tiempo visual ---------------------------------------------------
    st.markdown(f"##### ③ 🗓️ {T('Tu día, en una línea de tiempo', 'Your day, on a timeline')}")
    _linea_tiempo = [
        ("#FFB300", "☀️", T("Mañana", "Morning"), "8:00 AM"),
        ("#FF9500", "☀️", T("Mediodía", "Noon"), "12:00 PM"),
        ("#B06000", "☕", T("Último café", "Last coffee"), _fmt(dt_limite)),
        ("#FF6B35", "🌇", T("Tarde", "Afternoon"), "6:00 PM"),
        ("#1B2A4A", "🌙", T("Dormir", "Sleep"), _fmt(dt_dormir)),
    ]
    _html_lt = ['<div style="max-width:520px;margin:0 auto;">']
    for _i, (_bc, _em, _tt, _hh) in enumerate(_linea_tiempo):
        _es_cafe = _tt == T("Último café", "Last coffee")
        _fondo_lt = "rgba(255,179,0,0.12)" if _es_cafe else "#FFFFFF"
        _html_lt.append(f"""
        <div style="display:flex;align-items:center;gap:14px;background:{_fondo_lt};border-radius:18px;
        padding:12px 18px;box-shadow:0 4px 14px rgba(0,0,0,0.05);border-left:5px solid {_bc};margin-bottom:4px;">
        <div style="font-size:1.5rem;">{_em}</div>
        <div><p style="margin:0;font-weight:800;color:#17301F;font-size:0.85rem;">{_tt}</p>
        <p style="margin:0;color:#17301F;font-size:1rem;font-weight:700;">{_hh}</p></div>
        </div>""")
        if _i < len(_linea_tiempo) - 1:
            _html_lt.append('<div style="text-align:center;font-size:1.3rem;color:#1B2A4A;opacity:0.5;margin:2px 0;">↓</div>')
    _html_lt.append('</div>')
    st.markdown(_html_sin_lineas_vacias("".join(_html_lt)), unsafe_allow_html=True)

    st.write("")

    # --- PASO 4: ¿Por qué ocurre esto? — tres tarjetas ------------------------------------
    st.markdown(f"##### ④ 🤔 {T('¿Por qué ocurre esto?', 'Why does this happen?')}")
    col_p1, col_p2, col_p3 = st.columns(3)
    _porques = [
        (col_p1, "#5856D6", "#ECEBFC", "🧠", T("La cafeína tarda varias horas en desaparecer del cuerpo.",
                                                "Caffeine takes several hours to clear from the body.")),
        (col_p2, "#1B2A4A", "#E9ECF5", "😴", T("Si consumes café muy tarde puede dificultar el sueño.",
                                                "Having coffee too late can make it harder to fall asleep.")),
        (col_p3, "#34C759", "#EAFAEE", "🍎", T("Dormir bien ayuda a controlar el apetito y favorece una alimentación saludable.",
                                                "Sleeping well helps control appetite and supports healthy eating.")),
    ]
    for _col, _borde, _fondo, _emoji, _texto in _porques:
        with _col:
            st.markdown(f"""
            <div class="bento-card" style="background:{_fondo};text-align:center;">
            <div style="font-size:1.6rem;margin-bottom:6px;">{_emoji}</div>
            <p style="margin:0;color:{_borde};font-weight:700;font-size:0.82rem;line-height:1.45;">{_texto}</p>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # --- PASO 5: 🌈 Comparación personalizada --------------------------------------------
    st.markdown(f"##### ⑤ 🌈 {T('Comparación personalizada', 'Personalized comparison')}")
    _hora_verde = dt_limite - timedelta(hours=3)
    _hora_ambar = dt_limite - timedelta(minutes=30)
    _hora_roja = dt_limite + timedelta(hours=3)
    _comparaciones = [
        ("🟢", _hora_verde, T("Muy recomendable", "Highly recommended"),
         T("Hay tiempo de sobra para que tu cuerpo elimine la cafeína antes de dormir.",
           "There's plenty of time for your body to clear the caffeine before you sleep.")),
        ("🟡", _hora_ambar, T("Aún aceptable", "Still acceptable"),
         T("Está muy cerca del límite; en personas sensibles a la cafeína podría retrasar el sueño.",
           "It's very close to the limit; in people sensitive to caffeine it could delay sleep.")),
        ("🔴", _hora_roja, T("Puede afectar el sueño", "May affect sleep"),
         T("La cafeína seguiría activa en tu organismo a la hora de dormir, reduciendo la calidad del descanso.",
           "Caffeine would still be active in your system at bedtime, reducing sleep quality.")),
    ]
    _filas_comp = "".join(f"""
    <div style="display:flex;align-items:center;gap:14px;background:#FFFFFF;border-radius:16px;
    padding:12px 18px;box-shadow:0 4px 14px rgba(0,0,0,0.05);margin-bottom:8px;">
        <div style="font-size:1.3rem;">{_ic}</div>
        <div style="flex:1;">
            <p style="margin:0;font-weight:800;color:#17301F;font-size:0.95rem;">{_fmt(_hh)} → {_tt}</p>
            <p style="margin:2px 0 0 0;color:#5C6B60;font-size:0.8rem;line-height:1.4;">{_txt}</p>
        </div>
    </div>""" for _ic, _hh, _tt, _txt in _comparaciones)
    st.markdown(_html_sin_lineas_vacias(f"""
    <div style="background:#F4F6FB;border-radius:20px;padding:18px 20px;border:1px solid rgba(27,42,74,0.08);">
        <p style="margin:0 0 4px 0;font-weight:900;color:#1B2A4A;font-size:1rem;">☕ {T('Tu horario', 'Your schedule')}</p>
        <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:14px;">
            <div><span style="color:#5C6B60;font-size:0.8rem;">{T('Hora de dormir', 'Bedtime')}</span><br>
            <span style="font-weight:800;color:#1B2A4A;font-size:1.05rem;">{_fmt(dt_dormir)}</span></div>
            <div><span style="color:#5C6B60;font-size:0.8rem;">{T('Último café recomendado', 'Recommended last coffee')}</span><br>
            <span style="font-weight:800;color:#B06000;font-size:1.05rem;">{_fmt(dt_limite)}</span></div>
        </div>
        <p style="margin:0 0 8px 0;font-weight:700;color:#17301F;font-size:0.9rem;">{T('Si tomas café a las...', 'If you have coffee at...')}</p>
        {_filas_comp}
    </div>
    """), unsafe_allow_html=True)

    st.write("")

    # --- PASO 6: 💡 Consejo práctico -------------------------------------------------------
    st.markdown(f"""
    <div style="background:#FFF6E0;border-radius:18px;padding:16px 20px;border-left:5px solid #FFB300;">
    <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">💡 {T('Consejo', 'Tip')}</p>
    <p style="margin:0;color:#5C4A1E;font-size:0.88rem;line-height:1.5;">
    {T('Si un día deseas tomar café más tarde de lo habitual, intenta reducir la cantidad o elegir una bebida '
       'con menos cafeína para disminuir su efecto sobre el sueño.',
       'If one day you want to have coffee later than usual, try reducing the amount or choosing a drink '
       'with less caffeine to lessen its effect on your sleep.')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    recursos_externos(12, [
        (T("☕ Cafeína y sueño (Sleep Foundation)", "☕ Caffeine and sleep (Sleep Foundation)"),
         "https://www.sleepfoundation.org/nutrition/caffeine-and-sleep"),
    ])
    caja_util(T(
        "¿Sabías que dormir mal te da más hambre y más ganas de comer dulce al día siguiente? Esta "
        "herramienta te dice hasta qué hora puedes tomar café sin arruinar tu descanso — y un buen "
        "descanso es tan importante para tu salud como una buena alimentación. ☕😴",
        "Did you know that sleeping poorly makes you hungrier and craves sweets the next day? This "
        "tool tells you the latest time you can have coffee without ruining your rest — and good "
        "rest is just as important for your health as good nutrition. ☕😴"
    ), emoji="🌙", color="#FFF4DE", borde="#1B2A4A")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "13.-LÍNEA DE TIEMPO" and genero == "Mujer" and embarazada:
    # ===== 🌸 Encabezado con degradado suave =====
    st.markdown("""
    <div style="background:linear-gradient(120deg,#FFE1EC 0%,#E1F3FF 55%,#FFFFFF 100%);border-radius:22px;
                padding:26px 28px;margin-bottom:18px;box-shadow:0 6px 18px rgba(0,0,0,0.05);">
        <div style="font-size:1.35rem;font-weight:900;color:#B0205A;margin-bottom:4px;">
            🤰 Seguimiento del Peso durante el Embarazo</div>
        <div style="color:#5C6B78;font-size:0.92rem;line-height:1.5;max-width:640px;">
            Conoce si tu aumento de peso está dentro del rango recomendado para la etapa de
            embarazo que seleccionaste.</div>
    </div>
    """, unsafe_allow_html=True)

    # Canal de Ganancia de Peso Gestacional (IOM / National Research Council — Weight Gain During Pregnancy)
    _CANALES_IOM = [
        (18.5, "Bajo peso (IMC < 18.5)", 12.5, 18.0, "#5AC8FA"),
        (25.0, "Normal (IMC 18.5–24.9)", 11.5, 16.0, "#34C759"),
        (30.0, "Sobrepeso (IMC 25.0–29.9)", 7.0, 11.5, "#FF9500"),
        (999.0, "Obesidad (IMC ≥ 30.0)", 5.0, 9.0, "#FF3B30"),
    ]
    _imc_previo = imc  # IMC previo/actual usado como aproximación del IMC pregestacional
    for _tope, _etq, _min_kg, _max_kg, _color_canal in _CANALES_IOM:
        if _imc_previo < _tope:
            _canal_etiqueta, _canal_min, _canal_max, _canal_color = _etq, _min_kg, _max_kg, _color_canal
            break

    _semanas_totales = 40
    _RANGO_TRIMESTRE = {"Primer trimestre": (1, 13), "Segundo trimestre": (14, 27), "Tercer trimestre": (28, 40)}
    _sem_min_tri, _sem_max_tri = _RANGO_TRIMESTRE.get(trimestre, (1, 13))
    _semana_default = st.session_state.get("semana_embarazo_exacta", (_sem_min_tri + _sem_max_tri) // 2)
    _semana_default = min(max(_semana_default, 1), _semanas_totales)

    _peso_hoy = st.session_state.get("peso_gestacional_hoy", peso)

    # ===== 📋 Tarjetas resumen (fila única) =====
    def _tarjeta_resumen(icono, titulo, valor, sub, color):
        st.markdown(f"""
        <div style="background:#FFFFFF;border-radius:18px;padding:16px 14px;height:118px;
        border:1.5px solid {color}33;box-shadow:0 4px 12px rgba(0,0,0,0.05);
        display:flex;flex-direction:column;justify-content:center;">
        <div style="font-size:1.3rem;">{icono}</div>
        <p style="margin:4px 0 0 0;color:#8E8E93;font-size:0.72rem;font-weight:800;text-transform:uppercase;">{titulo}</p>
        <p style="margin:0;color:{color};font-size:1.15rem;font-weight:800;">{valor}</p>
        <p style="margin:0;color:#8E8E93;font-size:0.7rem;">{sub}</p>
        </div>
        """, unsafe_allow_html=True)

    _c1, _c2, _c3, _c4 = st.columns(4)
    with _c1:
        _tarjeta_resumen("🤰", "Etapa actual", trimestre, f"Semanas {_sem_min_tri}–{_sem_max_tri}", "#B0205A")
    with _c2:
        st.markdown('<p style="margin:0 0 4px 0;color:#8E8E93;font-size:0.72rem;font-weight:800;'
                     'text-transform:uppercase;">📅 Semana del embarazo</p>', unsafe_allow_html=True)
        semana_exacta = st.number_input("Semana del embarazo:", min_value=1, max_value=_semanas_totales,
                                         value=_semana_default, step=1, key="semana_embarazo_exacta",
                                         label_visibility="collapsed")
    with _c3:
        _tarjeta_resumen("⚖️", "Peso actual", f"{_peso_hoy:.1f} kg", "Tu último registro", "#007AFF")

    _kg_ganados = _peso_hoy - peso
    _min_esperado_hoy = (_canal_min / _semanas_totales) * semana_exacta
    _max_esperado_hoy = (_canal_max / _semanas_totales) * semana_exacta
    if _kg_ganados < _min_esperado_hoy - 1:
        _estado_txt, _estado_color, _estado_icono = "Por debajo del rango", "#FF9500", "🟡"
    elif _kg_ganados > _max_esperado_hoy + 1:
        _estado_txt, _estado_color, _estado_icono = "Por encima del rango", "#FF3B30", "🔴"
    else:
        _estado_txt, _estado_color, _estado_icono = "Dentro del rango", "#34C759", "🟢"
    with _c4:
        _tarjeta_resumen(_estado_icono, "Estado", _estado_txt, "Según tu semana", _estado_color)

    st.write("")

    # ===== 💡 Caja informativa =====
    st.markdown("""
    <div style="background:#E9F3FF;border-radius:16px;padding:16px 20px;margin-bottom:16px;
                border:1px solid #B9DBFF;">
    <p style="margin:0 0 6px 0;font-weight:800;color:#0B4DA8;font-size:0.92rem;">
        ℹ️ ¿Cómo funciona este gráfico?</p>
    <p style="margin:0;color:#31465F;font-size:0.85rem;line-height:1.55;">
        El gráfico utiliza la semana exacta de embarazo que registraste.<br>
        Aunque hayas seleccionado el trimestre, el seguimiento del peso se realiza semana por
        semana para ser más preciso.<br>
        Por eso el punto aparece en la semana correspondiente.</p>
    </div>
    """, unsafe_allow_html=True)

    # ===== 📈 Título + badges =====
    st.markdown("##### 📈 Comparación de tu peso con el rango recomendado")
    st.caption("Basado en las recomendaciones del Instituto de Medicina (IOM).")
    _b1, _b2, _b3, _b4 = st.columns(4)
    with _b1:
        st.markdown('<span style="background:#EAF3FF;color:#007AFF;font-weight:800;font-size:0.76rem;'
                     'padding:5px 10px;border-radius:999px;">🔵 Tu peso</span>', unsafe_allow_html=True)
    with _b2:
        st.markdown(f'<span style="background:{_canal_color}22;color:{_canal_color};font-weight:800;'
                     f'font-size:0.76rem;padding:5px 10px;border-radius:999px;">🟩 Zona saludable</span>',
                     unsafe_allow_html=True)
    with _b3:
        st.markdown('<span style="background:#F2F2F7;color:#5C6B78;font-weight:800;font-size:0.76rem;'
                     'padding:5px 10px;border-radius:999px;">⬇️ Mínimo recomendado</span>', unsafe_allow_html=True)
    with _b4:
        st.markdown('<span style="background:#F2F2F7;color:#5C6B78;font-weight:800;font-size:0.76rem;'
                     'padding:5px 10px;border-radius:999px;">⬆️ Máximo recomendado</span>', unsafe_allow_html=True)

    st.write("")

    _sem_eje = list(range(0, _semanas_totales + 1))
    _linea_min = [round((_canal_min / _semanas_totales) * s, 2) for s in _sem_eje]
    _linea_max = [round((_canal_max / _semanas_totales) * s, 2) for s in _sem_eje]

    fig_iom = go.Figure()
    fig_iom.add_trace(go.Scatter(x=_sem_eje, y=[peso + v for v in _linea_max], mode="lines",
                                  name="Máximo recomendado", line=dict(color=_canal_color, width=2, dash="dash")))
    fig_iom.add_trace(go.Scatter(x=_sem_eje, y=[peso + v for v in _linea_min], mode="lines",
                                  name="Mínimo recomendado", line=dict(color=_canal_color, width=2, dash="dash"),
                                  fill="tonexty", fillcolor=_hex_a_rgba(_canal_color, 0.14)))
    fig_iom.add_trace(go.Scatter(x=[semana_exacta], y=[_peso_hoy], mode="markers+text",
                                  name="Tu peso", marker=dict(size=14, color="#007AFF",
                                  line=dict(color="#FFFFFF", width=3)),
                                  text=[f"Semana {semana_exacta}: {_peso_hoy:.1f} kg"], textposition="top center",
                                  textfont=dict(size=13, color="#17301F")))
    fig_iom.update_layout(
        title=dict(text="📈 Comparación de tu peso con el rango saludable", x=0.02, xanchor="left",
                   font=dict(size=17, color="#17301F", family="-apple-system")),
        xaxis_title="Semana de embarazo", yaxis_title="Peso (kg)",
        height=420, margin=dict(t=60, l=10, r=10, b=10),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_iom, use_container_width=True)

    # ===== 🌈 Barra visual tipo progreso =====
    st.markdown("##### 🌈 Tu posición dentro del rango")
    _rango_barra = max(_max_esperado_hoy - _min_esperado_hoy, 0.1)
    _pct_barra = (_kg_ganados - _min_esperado_hoy) / _rango_barra
    _pct_barra = min(max(_pct_barra, -0.3), 1.3)
    _pos_pct = round((_pct_barra + 0.3) / 1.6 * 100, 1)
    st.markdown(f"""
    <div style="position:relative;background:linear-gradient(90deg,#FFCC00 0%,#FFCC00 22%,#34C759 22%,
                #34C759 78%,#FFCC00 78%,#FFCC00 100%);border-radius:999px;height:22px;margin:10px 0 6px 0;">
        <div style="position:absolute;left:{_pos_pct}%;top:-6px;transform:translateX(-50%);
                    width:14px;height:34px;background:#007AFF;border-radius:8px;border:3px solid #FFFFFF;
                    box-shadow:0 2px 6px rgba(0,0,0,0.25);"></div>
    </div>
    <div style="display:flex;justify-content:space-between;color:#8E8E93;font-size:0.76rem;font-weight:700;">
        <span>⬇️ Debajo</span><span>🟩 Saludable</span><span>Encima ⬆️</span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # ===== 📚 Sección desplegable =====
    with st.expander("❓ ¿Por qué cambia el gráfico? — Más información"):
        st.markdown("""
        Durante el embarazo el aumento de peso no ocurre de golpe. Cada semana existe un rango
        recomendado. Por eso esta herramienta compara tu peso con la semana que registraste y no
        únicamente con el trimestre.

        El aumento de peso en el embarazo no sigue un patrón estético: mantenerte dentro de este
        rango médico ayuda a evitar partos prematuros (ganar muy poco) o diabetes gestacional
        (ganar demasiado).
        """)

    st.write("")
    st.markdown("##### 📝 Registra tu peso de esta semana")
    _peso_registro = st.number_input("Tu peso actual (kg):", min_value=20.0, max_value=300.0,
                                      value=float(_peso_hoy), step=0.1, key="peso_gestacional_hoy")
    if _estado_txt == "Dentro del rango":
        st.success("🟢 Tu ganancia de peso está dentro del canal saludable IOM para tu semana de embarazo.")
    else:
        st.warning(f"🟨 {_estado_txt}. Coméntalo con tu médico ginecólogo-obstetra o nutricionista.")

elif hoja_activa == "13.-LÍNEA DE TIEMPO":
    hoja_header(13, "Manteniendo tus hábitos actuales y el plan de calorías calculado, esta es una estimación "
                    "de cómo podría cambiar tu peso con el tiempo.")

    def calcular_proyeccion(calorias_consumidas, tdee, dias=60):
        """Función proyectiva: aplica la fórmula del déficit/superávit calórico y retorna
        (deficit_diario, peso_proyectado_kg) para el número de días indicado."""
        deficit_diario = tdee - calorias_consumidas
        peso_proyectado = (deficit_diario * dias) / 7700
        return deficit_diario, peso_proyectado

    _DIAS_PROY = 60
    deficit_diario, peso_cambio_60 = calcular_proyeccion(rcd_final, rcd, dias=_DIAS_PROY)
    _es_mantener = (objetivo == "Mantenerse" or abs(peso_cambio_60) < 0.05)
    _es_bajar = (not _es_mantener) and peso_cambio_60 > 0
    _peso_final = peso - peso_cambio_60
    _peso_30 = peso - (deficit_diario * 30) / 7700

    _color_tema = "#34C759" if _es_mantener else ("#007AFF" if _es_bajar else "#FF9500")

    # === 1. HERO: 4 tarjetas grandes en una fila, con flecha horizontal entre cada una =====
    _obj_label = "Mantener peso" if _es_mantener else ("Bajar de peso" if _es_bajar else "Subir de peso")
    _tarjetas_hero = [
        ("⚖️", "Peso actual", f"{peso:.1f} kg", "Tu peso registrado hoy."),
        ("🎯", "Objetivo", _obj_label, f"Ajuste aplicado: {ajuste_aplicado*100:.0f}%" if not _es_mantener else "Mantener tu peso estable."),
        ("📅", "Tiempo analizado", f"{_DIAS_PROY} días", "Aproximadamente 2 meses."),
        ("🏁", "Peso estimado", f"{_peso_final:.1f} kg", "Si mantienes el mismo plan."),
    ]
    _cols_hero = st.columns([1, 0.18, 1, 0.18, 1, 0.18, 1])
    for _j, (_ic, _tt, _val, _desc) in enumerate(_tarjetas_hero):
        with _cols_hero[_j * 2]:
            st.markdown(f"""
            <div style="background:#FFFFFF;border-radius:20px;padding:18px 16px;height:150px;
            border:1.5px solid {_color_tema}33;box-shadow:0 4px 14px rgba(0,0,0,0.06);
            display:flex;flex-direction:column;justify-content:center;">
            <div style="font-size:1.5rem;">{_ic}</div>
            <p style="margin:6px 0 2px 0;color:#8E8E93;font-size:0.74rem;font-weight:800;text-transform:uppercase;">{_tt}</p>
            <p style="margin:0 0 4px 0;color:#17301F;font-size:1.25rem;font-weight:800;">{_val}</p>
            <p style="margin:0;color:#8E8E93;font-size:0.72rem;line-height:1.3;">{_desc}</p>
            </div>
            """, unsafe_allow_html=True)
        if _j < 3:
            with _cols_hero[_j * 2 + 1]:
                st.markdown(f"""<div style="height:150px;display:flex;align-items:center;justify-content:center;
                font-size:1.6rem;color:{_color_tema};">→</div>""", unsafe_allow_html=True)

    st.write("")

    # === 2. Secuencia: ¿Cómo cambiaría tu peso? (Hoy → 30 días → 60 días) en una sola fila ===
    st.markdown("##### 📉 ¿Cómo cambiaría tu peso?")
    _secuencia = [("Hoy", peso), ("En 30 días", _peso_30), ("En 60 días", _peso_final)]
    _cols_sec = st.columns([1, 0.18, 1, 0.18, 1])
    for _j, (_tt, _val) in enumerate(_secuencia):
        with _cols_sec[_j * 2]:
            st.markdown(f"""
            <div style="background:{_color_tema}14;border:1.5px solid {_color_tema}44;border-radius:18px;
            padding:16px;text-align:center;">
            <p style="margin:0 0 4px 0;color:#5C6B60;font-size:0.78rem;font-weight:700;">{_tt}</p>
            <p style="margin:0;color:{_color_tema};font-size:1.5rem;font-weight:800;">{_val:.1f} kg</p>
            </div>
            """, unsafe_allow_html=True)
        if _j < 2:
            with _cols_sec[_j * 2 + 1]:
                st.markdown(f"""<div style="height:100%;display:flex;align-items:center;justify-content:center;
                font-size:1.4rem;color:{_color_tema};padding-top:14px;">→</div>""", unsafe_allow_html=True)

    st.write("")

    # === 3. El gráfico, ya como apoyo visual, con título simple =============================
    dias_eje = list(range(0, _DIAS_PROY + 1))
    pesos_dia_completo = [round(peso - (deficit_diario * d) / 7700, 2) for d in dias_eje]

    fig_tiempo = go.Figure()
    fig_tiempo.add_trace(go.Scatter(
        x=dias_eje, y=pesos_dia_completo, mode="lines", name="Peso estimado",
        line=dict(color=_color_tema, width=4, shape="spline"),
    ))
    fig_tiempo.update_traces(fill="tozeroy", fillcolor=_hex_a_rgba(_color_tema, 0.12))

    hitos_x = [0, 30, 60]
    hitos_y = [pesos_dia_completo[0], pesos_dia_completo[30], pesos_dia_completo[60]]
    hitos_txt = ["Hoy", "En 1 mes", "En 2 meses"]
    fig_tiempo.add_trace(go.Scatter(
        x=hitos_x, y=hitos_y, mode="markers+text", name="Hitos",
        marker=dict(size=14, color="#FFFFFF", line=dict(color=_color_tema, width=4)),
        text=[f"{t}<br><b>{v:.1f} kg</b>" for t, v in zip(hitos_txt, hitos_y)],
        textposition="top center", textfont=dict(size=13, color="#17301F", family="-apple-system"),
        showlegend=False,
    ))

    _rango_min = min(pesos_dia_completo) - 3
    _rango_max = max(pesos_dia_completo) + 5
    fig_tiempo.update_layout(
        title=dict(text="Evolución estimada del peso", x=0.02, xanchor="left",
                   font=dict(size=18, color="#17301F", family="-apple-system")),
        xaxis_title="Días a partir de hoy", yaxis_title="Peso estimado (kg)",
        xaxis=dict(dtick=10, gridcolor="#F0F0F0"), yaxis=dict(range=[_rango_min, _rango_max], gridcolor="#F0F0F0"),
        height=400, margin=dict(t=60, l=10, r=10, b=10),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    st.plotly_chart(fig_tiempo, use_container_width=True)
    st.caption("Cada punto representa el peso aproximado si mantienes el mismo consumo de calorías todos los días.")

    st.write("")

    # === 4. ¿Por qué cambia mi peso? =========================================================
    st.markdown(f"""
    <div style="background:#F2F7F3;border-radius:18px;padding:18px 22px;margin-bottom:16px;border:1px solid #D8E6DA;">
    <p style="margin:0 0 8px 0;font-weight:800;color:#1E5631;font-size:1rem;">🤔 ¿Por qué cambia mi peso?</p>
    <p style="margin:0;color:#3C4A3F;font-size:0.88rem;line-height:1.6;">Tu cuerpo necesita una cierta cantidad
    de calorías para mantener su peso (RCD). Cuando consumes menos calorías de las que gastas, utiliza parte de
    sus reservas de energía y tu peso disminuye. Si consumes más de las necesarias, ocurre lo contrario y el
    peso aumenta.</p>
    </div>
    """, unsafe_allow_html=True)

    # === 5. ¿Cómo se calculó esta proyección? — paso a paso con los números reales ==========
    st.markdown("##### 🧮 ¿Cómo se calculó esta proyección?")
    _signo_ajuste = "-" if _es_bajar else ("+" if not _es_mantener else "±")
    _rcd_obj_label = "Nuevo RCD" if not _es_mantener else "RCD objetivo"

    _pasos = [
        ("1", f"Se calcula tu RCD (gasto calórico diario).", f"RCD = {rcd:.0f} kcal"),
        ("2", f"Se aplica tu objetivo ({_obj_label}, {_signo_ajuste}{ajuste_aplicado*100:.0f}%).",
         f"{_rcd_obj_label} = {rcd_final:.0f} kcal"),
        ("3", "Se obtiene el déficit/superávit diario.", f"{rcd:.0f} − {rcd_final:.0f} = {deficit_diario:.0f} kcal/día"),
        ("4", f"Se calcula el total acumulado en {_DIAS_PROY} días.",
         f"{deficit_diario:.0f} × {_DIAS_PROY} = {deficit_diario*_DIAS_PROY:.0f} kcal"),
        ("5", "Se convierte a kilogramos (7,700 kcal ≈ 1 kg de grasa corporal).",
         f"{deficit_diario*_DIAS_PROY:.0f} ÷ 7,700 = {peso_cambio_60:.2f} kg"),
    ]
    for _num, _desc, _formula in _pasos:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;background:#FFFFFF;border-radius:16px;
        padding:12px 18px;margin-bottom:8px;border:1px solid rgba(0,0,0,0.06);box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <div style="min-width:32px;height:32px;border-radius:50%;background:{_color_tema};color:#FFFFFF;
        font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{_num}</div>
        <div style="flex:1;"><p style="margin:0;color:#3C4A3F;font-size:0.85rem;">{_desc}</p>
        <p style="margin:2px 0 0 0;color:{_color_tema};font-weight:800;font-size:0.92rem;font-family:monospace;">{_formula}</p></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{_color_tema}14;border:1.5px solid {_color_tema}55;border-radius:16px;
    padding:14px 18px;margin:8px 0 18px 0;">
    <p style="margin:0;color:#17301F;font-size:0.92rem;"><b>Resultado:</b> {peso:.1f} {'−' if _es_bajar else ('+' if not _es_mantener else '±')}
    {abs(peso_cambio_60):.2f} = <b style="color:{_color_tema};">{_peso_final:.2f} kg</b> — peso estimado en {_DIAS_PROY} días.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Fórmulas generales según el objetivo (solo se muestra la que aplica) ---
    with st.expander("📐 Ver las fórmulas generales"):
        if _es_bajar:
            st.markdown("""
- **Déficit diario** = RCD − RCD objetivo
- **Déficit total** = Déficit diario × Número de días
- **Peso perdido** = Déficit total ÷ 7,700
- **Peso final** = Peso inicial − Peso perdido
            """)
        elif not _es_mantener:
            st.markdown("""
- **Superávit diario** = RCD objetivo − RCD
- **Superávit acumulado** = Superávit diario × Número de días
- **Ganancia estimada** = Superávit acumulado ÷ 7,700
- **Peso final** = Peso inicial + Ganancia estimada
            """)
        else:
            st.markdown("- **Peso final** = Peso inicial (sin déficit ni superávit aplicado)")
        st.caption("Se utiliza el equivalente energético aproximado de 7,700 kcal por kilogramo de grasa corporal, "
                   "ampliamente empleado para estimar cambios de peso. En la práctica, el cuerpo humano es más "
                   "complejo y el ritmo real puede variar entre personas.")

    # === 6. ¿Qué significa esta proyección? (caja azul) =====================================
    st.markdown("""
    <div style="background:#E7F1FE;border-radius:16px;padding:16px 20px;margin-bottom:14px;border:1px solid #B3D2F7;">
    <p style="margin:0;color:#0D47A1;font-size:0.88rem;line-height:1.6;"><b>🟦 ¿Qué significa esta proyección?</b><br>
    Esta proyección supone que mantendrás aproximadamente el mismo nivel de actividad física y el mismo consumo
    de calorías durante todo el período. Si alguno de estos factores cambia, el resultado también cambiará.</p>
    </div>
    """, unsafe_allow_html=True)

    # === 7. Lo que debes saber (caja amarilla) ===============================================
    st.markdown("""
    <div style="background:#FFFDE7;border-radius:16px;padding:16px 20px;margin-bottom:18px;border:1px solid #F3E19B;">
    <p style="margin:0;color:#8A6D00;font-size:0.88rem;line-height:1.6;"><b>⚠️ Lo que debes saber</b><br>
    Ninguna calculadora puede predecir exactamente cuánto peso perderá o ganará una persona. Este resultado es
    una estimación basada en ecuaciones científicas y sirve como una guía para comprender cómo influyen las
    calorías en el peso corporal.</p>
    </div>
    """, unsafe_allow_html=True)

    # === 8. ¿Qué puede hacer que esta proyección cambie? — 4 tarjetas ========================
    st.markdown("##### 🎯 ¿Qué puede hacer que esta proyección cambie?")
    _factores = [
        ("🏃", "Más ejercicio", "Bajarías un poco más rápido.", "#EAFAEE", "#9BD8AE", "#1E5631"),
        ("🍕", "Consumir más calorías", "Bajarías más lento o incluso subirías.", "#FDEBD9", "#F5C48E", "#B0530A"),
        ("😴", "Dormir poco", "Puede dificultar mantener el plan.", "#F3EEFB", "#C6AEE8", "#6A3FA0"),
        ("💧", "Retención de líquidos", "El peso diario puede variar aunque estés perdiendo grasa.", "#E7F1FE", "#B3D2F7", "#0D47A1"),
    ]
    _cols_fact = st.columns(4)
    for _col_f, (_ic, _tt, _txt, _fondo, _borde, _hex) in zip(_cols_fact, _factores):
        with _col_f:
            st.markdown(f"""
            <div style="background:{_fondo};border:1px solid {_borde};border-radius:18px;padding:16px 14px;
            height:150px;">
            <div style="font-size:1.5rem;">{_ic}</div>
            <p style="margin:8px 0 4px 0;font-weight:800;color:{_hex};font-size:0.88rem;">{_tt}</p>
            <p style="margin:0;color:#5C6B60;font-size:0.78rem;line-height:1.4;">{_txt}</p>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    caja_util(f"Esta proyección te muestra, con la misma matemática que usan los nutricionistas, cómo "
              f"avanzarías en {_DIAS_PROY} días si sigues tu plan calórico. Ver el progreso estimado ayuda a "
              f"entender que los resultados reales toman semanas o meses de constancia — ¡tú puedes lograrlo, "
              f"{_nombre_saludo}! 🌱",
              emoji="📈", color="#E8EAF6", borde="#3949AB")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "📄 MI REPORTE":
    hoja_header(14, T("Un informe médico completo, con tus datos, resultados y recomendaciones — listo para imprimir.",
                       "A complete medical report, with your data, results, and recommendations — ready to print."))

    st.markdown(f"""
    <div style="background:#E7F6FD;border-left:5px solid #32ADE6;border-radius:20px;
                padding:16px 24px;margin-bottom:16px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.05);" class="no-print">
    🔒 <b style="color:#1C7DAD;">{T("Privacidad:", "Privacy:")}</b> {T("este reporte se genera únicamente con la información que ingresaste en esta sesión.", "this report is generated solely from the information you entered in this session.")}
    {T("Nada se guarda en un servidor ni queda almacenado al cerrar o recargar la página.", "Nothing is saved on a server or stored when you close or reload the page.")}
    </div>
    """, unsafe_allow_html=True)

    _fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M")
    _etapa_r14_txt = T(etapa, _ETAPA_EN.get(etapa, etapa))

    # --- Encabezado tipo "informe médico" ---
    st.markdown(f"""
    <div class="print-only-report" style="background:#ffffff;border:1px solid rgba(50,173,230,0.25);border-radius:24px;padding:24px 28px;margin-bottom:18px;
                box-shadow:0 1px 2px rgba(0,0,0,0.03), 0 8px 22px rgba(0,0,0,0.06);">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;">
            <div>
                <div style="font-size:1.3rem;font-weight:800;color:#32ADE6;letter-spacing:-0.02em;">📄 {T("Informe de Resultados", "Results Report")} — CIAM&amp;SUNI</div>
                <div style="color:#6C6C70;font-size:0.9rem;">C.E.P. "Santa María Reina", Chiclayo</div>
            </div>
            <div style="text-align:right;color:#6C6C70;font-size:0.85rem;">{T("Generado", "Generated")}: {_fecha_reporte}</div>
        </div>
        <hr style="border:none;border-top:1px solid #F2F2F7;margin:14px 0;">
        <b>{T("Nombre", "Name")}:</b> {_nombre_saludo} &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>{T("Edad", "Age")}:</b> {edad} {T("años", "years")} ({_etapa_r14_txt}) &nbsp;&nbsp;|&nbsp;&nbsp;
        <b>{T("Género", "Gender")}:</b> {T(genero, "Female" if genero == "Mujer" else "Male")}
    </div>
    """, unsafe_allow_html=True)

    # --- Bloque 1: Datos antropométricos ---
    st.markdown(f"#### 📏 {T('Datos antropométricos', 'Anthropometric Data')}")
    r1, r2, r3 = st.columns(3)
    r1.metric(T("Peso", "Weight"), f"{peso:.2f} kg")
    r2.metric(T("Estatura", "Height"), f"{estatura} cm")
    with r3:
        tarjeta_categoria_imc(f"{T('IMC', 'BMI')}: {imc}", _categoria_imc_usuario)

    st.markdown(f"#### 🔥 {T('Requerimiento energético', 'Energy Requirement')}")
    r4, r5, r6 = st.columns(3)
    r4.metric(T("TMB", "BMR"), f"{tmb:.2f} kcal/{T('día', 'day')}")
    r5.metric(T("RCD (gasto diario)", "TDEE (daily expenditure)"), f"{rcd:.2f} kcal/{T('día', 'day')}")
    r6.metric(T("Meta calórica (objetivo)", "Caloric Goal (target)"), f"{rcd_final:.2f} kcal/{T('día', 'day')}")

    st.markdown(f"#### 🍽️ {T('Macronutrientes recomendados', 'Recommended Macronutrients')}")
    r7, r8, r9 = st.columns(3)
    r7.metric(T("Proteínas", "Protein"), f"{gr_prot:.2f} g")
    r8.metric(T("Carbohidratos", "Carbohydrates"), f"{gr_carb:.2f} g")
    r9.metric(T("Grasas", "Fats"), f"{gr_gras:.2f} g")

    # --- Bloque 2: Análisis sanguíneo, si hay datos ---
    st.markdown(f"#### 🩸 {T('Análisis sanguíneo', 'Blood Analysis')}")
    _valores_examen = [hemo, trigli, gluco, coles, hierro]
    _tiene_examen = any(v > 0 for v in _valores_examen)
    if _tiene_examen:
        _cat_hemo_r = clasif_hemoglobina(hemo, etapa, genero)
        _cat_trigli_r = clasif_trigliceridos(trigli)
        _cat_gluco_r = clasif_glucosa(gluco)
        _cat_coles_r = clasif_colesterol(coles)
        _cat_hierro_r = clasif_hierro(hierro, etapa, genero)
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        with rc1: tarjeta_semaforo(_parametro_txt("Hemoglobina"), f"{hemo} g/dL", _categoria_clinica_txt(_cat_hemo_r), valor_num=hemo, etapa=etapa, genero=genero)
        with rc2: tarjeta_semaforo(_parametro_txt("Triglicéridos"), f"{trigli} mg/dL", _categoria_clinica_txt(_cat_trigli_r), valor_num=trigli)
        with rc3: tarjeta_semaforo(_parametro_txt("Glucosa"), f"{gluco} mg/dL", _categoria_clinica_txt(_cat_gluco_r), valor_num=gluco)
        with rc4: tarjeta_semaforo(_parametro_txt("Colesterol"), f"{coles} mg/dL", _categoria_clinica_txt(_cat_coles_r), valor_num=coles)
        with rc5: tarjeta_semaforo(_parametro_txt("Hierro"), f"{hierro} µg/dL", _categoria_clinica_txt(_cat_hierro_r), valor_num=hierro, etapa=etapa, genero=genero)
    else:
        st.info(T("Aún no ingresaste tus valores de análisis sanguíneo en la barra lateral.",
                   "You haven't entered your blood test values in the sidebar yet."))
        _cat_hemo_r = _cat_trigli_r = _cat_gluco_r = _cat_coles_r = _cat_hierro_r = "Introducir datos"

    # --- Bloque 3: Plan de dieta armado (si el usuario visitó la Hoja 9) ---
    # Usamos st.session_state["dieta_guardada"], que la Hoja 9 escribe de forma explícita cada vez
    # que se renderiza (ver comentario allá). Es una única fuente de verdad — no depende de que las
    # 15 claves sueltas de los selectbox (c_/p_/g_ x 5 comidas) sigan existiendo o siendo válidas,
    # por lo que el plan ya NO se reinicia al cambiar de hoja dentro de la misma sesión.
    st.markdown(f"#### 🍱 {T('Tu plan de comidas del día', 'Your Daily Meal Plan')}")
    _dieta_guardada_r = st.session_state.get("dieta_guardada")
    _tiene_dieta = bool(_dieta_guardada_r)

    # ---- Reconstrucción fiel de las 3 tablas de macronutrientes (idéntica lógica a la Hoja 9)
    # a partir del plan guardado. Este mismo cálculo se reutiliza más abajo para armar el PDF,
    # así los datos del reporte en pantalla y los del PDF siempre coinciden. ----
    _ICONOS_COMIDA_R9 = {"Desayuno": "🌅", "Merienda 1": "🍎", "Almuerzo": "🍽️", "Merienda 2": "🥪", "Cena": "🌙"}
    _MOMENTO_EN_R9 = {"Desayuno": "Breakfast", "Merienda 1": "Morning Snack", "Almuerzo": "Lunch",
                      "Merienda 2": "Afternoon Snack", "Cena": "Dinner"}
    _MACRO_EN_R9 = {"Carbohidrato": "Carbohydrate", "Proteína": "Protein", "Grasa": "Fat"}

    def _mom_r14(nombre):
        """Traduce un nombre de comida (clave interna en español) según el idioma elegido."""
        return T(nombre, _MOMENTO_EN_R9.get(nombre, nombre))

    def _mac_r14(nombre):
        """Traduce un nombre de macronutriente (clave interna en español) según el idioma elegido."""
        return T(nombre, _MACRO_EN_R9.get(nombre, nombre))

    _PCT_MACRO_MOMENTO_PDF = {"Carbohidrato": 0.50, "Proteína": 0.20, "Grasa": 0.30}
    _dieta_filas_pdf = []
    _dieta_totales_pdf = {
        "Carbohidrato": {"kcal": 0.0, "porcion": 0.0, "gramos": 0.0},
        "Proteína": {"kcal": 0.0, "porcion": 0.0, "gramos": 0.0},
        "Grasa": {"kcal": 0.0, "porcion": 0.0, "gramos": 0.0},
    }
    if _tiene_dieta:
        for comida in DIETA:
            fila_macro_pdf = {"momento": comida}
            _sel_comida = _dieta_guardada_r.get(comida, {})
            for macro, prefijo_ss in [("Carbohidrato", "c"), ("Proteína", "p"), ("Grasa", "g")]:
                alimento_sel = _sel_comida.get(macro)
                opciones_macro = DIETA[comida][macro]
                if alimento_sel not in opciones_macro:
                    alimento_sel = next(iter(opciones_macro))  # fallback: primera opción disponible
                kcal_alimento = opciones_macro[alimento_sel]
                porcion_kcal = round(porciones[comida]["kcal"] * _PCT_MACRO_MOMENTO_PDF[macro], 2)
                gramos_finales = min(round((porcion_kcal / kcal_alimento) * 100, 1), 400.0) if kcal_alimento else 0.0
                fila_macro_pdf[macro] = {
                    "alimento": alimento_sel, "kcal": kcal_alimento,
                    "porcion": porcion_kcal, "gramos": gramos_finales,
                }
                _dieta_totales_pdf[macro]["kcal"] += kcal_alimento
                _dieta_totales_pdf[macro]["porcion"] += porcion_kcal
                _dieta_totales_pdf[macro]["gramos"] += gramos_finales
            _dieta_filas_pdf.append(fila_macro_pdf)

        def _tabla_reporte_macro(clase_css, icono, titulo, macro_key):
            """Tabla de color (Carbohidrato / Proteína / Grasa) con fila TOTAL, igual que en la Hoja 9."""
            _tot = _dieta_totales_pdf[macro_key]
            filas_html = ""
            for f in _dieta_filas_pdf:
                d = f[macro_key]
                filas_html += f"""
                <tr>
                    <td class="dm-momento">{_ICONOS_COMIDA_R9[f['momento']]} {_mom_r14(f['momento'])}</td>
                    <td>{_nombre_alimento(d['alimento'])}</td>
                    <td>{d['kcal']:.0f} kcal</td>
                    <td>{d['porcion']:.1f} kcal</td>
                    <td>{d['gramos']:.1f} g</td>
                </tr>"""
            filas_html += f"""
                <tr class="dm-total">
                    <td class="dm-momento" colspan="2">TOTAL</td>
                    <td>—</td>
                    <td>{_tot['porcion']:.1f} kcal</td>
                    <td>{_tot['gramos']:.1f} g</td>
                </tr>"""
            html = f"""
            <div class="dieta-menu-wrap {clase_css} print-only-report">
            <table class="dieta-menu-table">
                <thead>
                <tr><th style="text-align:left;">{T('Momento', 'Meal')}</th><th>{icono} {T('Alimento', 'Food')} ({_mac_r14(titulo)})</th>
                    <th>Kcal/100g</th><th>{T('Porción Corregida', 'Adjusted Portion')}</th><th>{T('Gramos Finales', 'Final Grams')}</th></tr>
                </thead>
                <tbody>
                {filas_html}
                </tbody>
            </table>
            </div>
            """
            st.markdown(_html_sin_lineas_vacias(html), unsafe_allow_html=True)

        _tabla_reporte_macro("carb", "🌾", "Carbohidrato", "Carbohidrato")
        _tabla_reporte_macro("prot", "🥩", "Proteína", "Proteína")
        _tabla_reporte_macro("gras", "🥑", "Grasa", "Grasa")
    else:
        st.info(T("Aún no armaste tu plan de comidas en la Hoja 9.-DIETA. Visítala para que aparezca aquí.",
                   "You haven't built your meal plan in Sheet 9.-DIET yet. Visit it so it appears here."))

    # --- Bloque 4: Proyección a 60 días ---
    st.markdown(f"#### 📈 {T('Proyección estimada (60 días)', 'Estimated Projection (60 days)')}")
    _deficit_r = rcd - rcd_final
    _peso_cambio_r = (_deficit_r * 60) / 7700
    _peso_proyectado_r = peso - _peso_cambio_r
    st.metric(T("Peso estimado en 60 días", "Estimated Weight in 60 Days"), f"{_peso_proyectado_r:.1f} kg")

    # =====================================================================================
    # BLOQUE 5: RESUMEN CLÍNICO Y RECOMENDACIONES — estilo informe médico profesional
    # =====================================================================================
    st.divider()
    st.markdown(f"#### 🩺 {T('Resumen clínico y recomendaciones', 'Clinical Summary and Recommendations')}")

    # Construimos una lista de recomendaciones según cada resultado obtenido
    _recomendaciones = []

    # IMC
    if _categoria_imc_usuario == "Peso Saludable":
        _recomendaciones.append(T("Tu IMC se encuentra en un rango saludable. Mantén tus hábitos actuales de alimentación y actividad física.",
                                   "Your BMI is within a healthy range. Keep up your current eating and physical activity habits."))
    elif _categoria_imc_usuario in ["Bajo Peso"]:
        _recomendaciones.append(T("Tu IMC sugiere bajo peso. Conversa con tu médico o nutricionista para evaluar si necesitas aumentar tu ingesta calórica de forma segura.",
                                   "Your BMI suggests you are underweight. Talk to your doctor or nutritionist to assess whether you need to safely increase your caloric intake."))
    elif _categoria_imc_usuario in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"]:
        _recomendaciones.append(T("Tu IMC sugiere un peso por encima del rango saludable, lo que puede aumentar el riesgo de enfermedades crónicas como hipertensión, diabetes tipo 2 y colesterol alto. Se recomienda evaluación con un profesional de la salud.",
                                   "Your BMI suggests a weight above the healthy range, which may increase the risk of chronic diseases such as hypertension, type 2 diabetes, and high cholesterol. A medical evaluation by a healthcare professional is recommended."))

    # Análisis sanguíneo
    if _tiene_examen:
        for _param, _cat in [("Hemoglobina", _cat_hemo_r), ("Triglicéridos", _cat_trigli_r),
                              ("Glucosa", _cat_gluco_r), ("Colesterol", _cat_coles_r), ("Hierro", _cat_hierro_r)]:
            _color_r = CATEGORIA_SEMAFORO.get(_cat, "gris")
            if _color_r in ["ambar", "rojo"]:
                _msg_r = _mensaje_triaje_txt(_param, _cat, _color_r)
                _recomendaciones.append(f"**{_parametro_txt(_param)}** ({_categoria_clinica_txt(_cat)}): {_msg_r}")

    if not _recomendaciones:
        _recomendaciones.append(T("No se detectaron alertas con la información ingresada hasta el momento.",
                                   "No alerts were detected with the information entered so far."))

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
    <b style="color:#FF9500;">{T("Recordar:", "Remember:")}</b> {T(
        "hable sobre su categoría de IMC y sus resultados con su proveedor de "
        "atención médica, ya que estos valores pueden estar relacionados con su salud y bienestar general. Su "
        "proveedor de atención médica podría determinar las posibles razones de los resultados obtenidos y "
        "recomendar apoyo o tratamiento. Este informe es una herramienta de detección orientativa y no pretende "
        "diagnosticar enfermedades ni dolencias.",
        "discuss your BMI category and your results with your healthcare provider, since these values may be "
        "related to your overall health and well-being. Your healthcare provider may be able to determine the "
        "possible reasons for the results obtained and recommend support or treatment. This report is an "
        "informational screening tool and is not intended to diagnose diseases or ailments."
    )}
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption(T("⚕️ Este informe es orientativo y educativo. No reemplaza una evaluación médica o nutricional "
                 "profesional.",
                 "⚕️ This report is informational and educational. It does not replace a professional medical or "
                 "nutritional evaluation."))

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
    # Nota: _dieta_filas_pdf y _dieta_totales_pdf ya se calcularon arriba (Bloque 3), junto con
    # las 3 tablas de color que se muestran en pantalla — se reutilizan aquí tal cual para el PDF.
    _datos_pdf = {
        "fecha": _fecha_reporte,
        "nombre": _nombre_saludo,
        "edad": edad,
        "etapa": etapa,
        "genero": genero,
        "grupo": 'N°04 - 5° "C"',
        "actividad": actividad,
        "peso": peso,
        "estatura": estatura,
        "imc": imc,
        "categoria_imc": _categoria_imc_usuario,
        "percentil": _percentil_usuario,
        "tmb": tmb,
        "rcd": rcd,
        "rcd_final": rcd_final,
        "objetivo": objetivo,
        "embarazada": (genero == "Mujer" and embarazada),
        "trimestre": trimestre if (genero == "Mujer" and embarazada) else "",
        "gr_prot": gr_prot, "cal_prot": cal_prot,
        "gr_carb": gr_carb, "cal_carb": cal_carb,
        "gr_gras": gr_gras, "cal_gras": cal_gras,
        "tiene_examen": _tiene_examen,
        "examen": _examen_pdf,
        "hemo": hemo, "gluco": gluco, "hierro": hierro, "trigli": trigli, "coles": coles,
        "pas": pas, "pad": pad, "spo2": spo2, "temp_corp": temp_corp, "pulso": pulso,
        "tiene_dieta": _tiene_dieta,
        "dieta_filas": _dieta_filas_pdf,
        "dieta_totales": _dieta_totales_pdf,
        "peso_proyectado": _peso_proyectado_r,
        "recomendaciones": _recomendaciones,
    }

    _pdf_bytes = generar_pdf_reporte(_datos_pdf)
    _nombre_archivo = T(f"Informe_CIAMSUNI_{_nombre_saludo}", f"Report_CIAMSUNI_{_nombre_saludo}").replace(" ", "_") + ".pdf"

    st.markdown(f"#### 📥 {T('Descarga tu informe', 'Download Your Report')}")
    st.caption(T("Genera un PDF con estilo de informe clínico (no una captura de la página) que puedes "
                 "guardar, enviar o imprimir directamente desde tu lector de PDF.",
                 "Generates a PDF styled as a clinical report (not a page screenshot) that you can save, "
                 "send, or print directly from your PDF reader."))
    st.download_button(
        T("📄 Descargar Informe en PDF", "📄 Download Report as PDF"),
        data=_pdf_bytes,
        file_name=_nombre_archivo,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

    caja_util(T(
        f"Este es tu informe final, {_nombre_saludo}: reúne en un solo lugar todo lo que calculamos en "
        "las hojas anteriores, con el formato de un informe que te entregarían en un consultorio. "
        "Usa el botón '📄 Descargar Informe en PDF' para obtener un archivo PDF real, listo para "
        "imprimir o compartir. 📄✨",
        f"This is your final report, {_nombre_saludo}: it brings together everything we calculated in "
        "the previous sheets in one place, in the format of a report you'd receive at a clinic. "
        "Use the '📄 Download Report as PDF' button to get a real PDF file, ready to "
        "print or share. 📄✨"
    ), emoji="📄", color="#E0F2F1", borde="#00695C")

elif hoja_activa == "🎓 SOBRE NOSOTRAS":
    # ===== Estilos exclusivos de esta hoja: tarjetas de equipo con hover animado =====
    st.markdown("""
    <style>
    .team-card {
        position: relative; border-radius: 24px; padding: 24px 20px 20px 20px; text-align: center;
        background: var(--tc-bg); border: 1.5px solid var(--tc-color);
        box-shadow: 0 4px 14px rgba(0,0,0,0.06);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        overflow: hidden; height: 100%;
    }
    .team-card:hover { transform: translateY(-4px); box-shadow: 0 16px 32px rgba(0,0,0,0.14); }
    .team-card::after {
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 4px;
        background: var(--tc-color); transform: scaleX(0); transform-origin: left;
        transition: transform 0.3s ease;
    }
    .team-card:hover::after { transform: scaleX(1); }
    .team-avatar {
        width: 74px; height: 74px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 2.1rem; margin: 0 auto 12px auto; background: #FFFFFF; border: 2px solid var(--tc-color);
        transition: transform 0.35s ease;
    }
    .team-card:hover .team-avatar { transform: rotate(-8deg) scale(1.08); }
    .team-name { font-weight: 900; letter-spacing: 0.01em; color: #17301F; font-size: 1.0rem; margin-bottom: 2px; }
    .team-icon-role { font-size: 0.72rem; color: #8A94A6; font-weight: 700; text-transform: uppercase; margin-bottom: 12px; }
    .team-badge {
        display: inline-flex; align-items: center; gap: 6px; background: #FFFFFF; color: var(--tc-color);
        font-weight: 800; font-size: 0.78rem; padding: 7px 16px; border-radius: 999px; margin-bottom: 12px;
        border: 1px solid var(--tc-color);
    }
    .team-chips-label { font-size: 0.68rem; font-weight: 800; color: #6B6B70; text-transform: uppercase;
        letter-spacing: 0.06em; margin-bottom: 6px; }
    .team-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
    .team-chip {
        background: #FFFFFF; color: var(--tc-color); font-weight: 700; font-size: 0.74rem;
        padding: 5px 11px; border-radius: 999px; border: 1px solid rgba(0,0,0,0.06);
    }
    .about-hero-card {
        border-radius: 24px; padding: 22px 24px; text-align: center; background: #FFFFFF;
        border: 1.5px solid rgba(0,0,0,0.05); box-shadow: 0 4px 14px rgba(0,0,0,0.06); height: 100%;
    }
    .about-mini-badge {
        display: inline-block; background: #EAFAEE; color: #1E5631; font-weight: 800; font-size: 0.72rem;
        padding: 5px 12px; border-radius: 999px; margin: 3px;
    }
    .about-stat {
        text-align: center; background: rgba(255,255,255,0.10); border-radius: 18px; padding: 14px 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ===== 1. Encabezado premium =====
    st.markdown(f"""
    <div style="background:linear-gradient(120deg,#F8ECFB 0%,#FFEBF0 55%,#FFFFFF 100%);border-radius:24px;
                padding:26px 30px;margin-bottom:18px;box-shadow:0 6px 18px rgba(0,0,0,0.06);
                border:1px solid rgba(255,45,85,0.08);">
    <h2 style="margin:0;color:#8E24AA;font-weight:900;letter-spacing:-0.02em;">👩‍💻 {T("Conoce al Equipo CIAM&amp;SUNI", "Meet the CIAM&amp;SUNI Team")}</h2>
    <p style="margin:6px 0 0 0;color:#5C6B60;font-size:0.98rem;font-weight:500;">
    {T("Las estudiantes que hicieron posible este proyecto 💚", "The students who made this project possible 💚")}</p>
    </div>
    """, unsafe_allow_html=True)

    # ===== 2. Tarjeta de logo + 3. Misión / Objetivo (apiladas) =====
    col_logo, col_mision_obj = st.columns([1, 2])
    with col_logo:
        _logo_img_tag = ""
        _logo_path = _LOGO_CIRCULAR if _LOGO_CIRCULAR.exists() else (_ESCUDO if _ESCUDO.exists() else None)
        if _logo_path is not None:
            _logo_b64 = _img_b64(_logo_path)
            _logo_img_tag = f'<img src="data:image/png;base64,{_logo_b64}" style="width:88px;height:88px;border-radius:50%;object-fit:cover;margin-bottom:10px;box-shadow:0 4px 14px rgba(0,0,0,0.10);" />'
        st.markdown(f"""
        <div class="about-hero-card">
        {_logo_img_tag}
        <p style="margin:2px 0 0 0;font-weight:900;color:#1E5631;font-size:1.05rem;">🌱 CIAM&amp;SUNI</p>
        <p style="margin:0 0 10px 0;color:#5C6B60;font-size:0.85rem;">{T("Calculadora Nutricional", "Nutritional Calculator")}</p>
        <div>
            <span class="about-mini-badge">💚 {T("Tecnología", "Technology")}</span>
            <span class="about-mini-badge">🥗 {T("Nutrición", "Nutrition")}</span>
            <span class="about-mini-badge">💻 {T("Programación", "Programming")}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)
    with col_mision_obj:
        st.markdown(f"""
        <div class="about-hero-card" style="text-align:left;margin-bottom:14px;">
        <p style="margin:0 0 8px 0;font-weight:900;color:#137333;font-size:1rem;">🌿 {T("Nuestra misión", "Our mission")}</p>
        <p style="margin:0;color:#3C3C43;font-size:0.9rem;line-height:1.55;font-style:italic;">
        "{T("Crear herramientas digitales gratuitas que promuevan hábitos saludables.",
            "Create free digital tools that promote healthy habits.")}"</p>
        </div>
        <div class="about-hero-card" style="text-align:left;">
        <p style="margin:0 0 8px 0;font-weight:900;color:#0B4DA8;font-size:1rem;">🎯 {T("Nuestro objetivo", "Our objective")}</p>
        <p style="margin:0;color:#3C3C43;font-size:0.9rem;line-height:1.55;font-style:italic;">
        "{T("Facilitar el cálculo nutricional para cualquier persona.",
            "Make nutritional calculations accessible to anyone.")}"</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # ===== 4. Tarjetas de integrantes (perfil, color propio, carrera como insignia, hobbies en chips) =====
    caja_titulo(T("👩‍🎓 Las Integrantes", "👩‍🎓 The Team Members"), 13)

    _idioma_equipo = st.session_state.get("idioma", "Español") == "English"
    EQUIPO = [
        {"nombre": "Diana Carolina Cháves Cobián", "avatar": "👩",
         "icono_rol": "🧠 " + T("Psicología", "Psychology"), "rol": "Psicología",
         "color": "#F9A825", "fondo": "#FFF8E1",
         "chips": [T("🎵 Tocar instrumentos", "🎵 Playing instruments")]},
        {"nombre": "Kathia Lizbeth Paz Gonzales", "avatar": "👩",
         "icono_rol": "⚡ " + T("Ingeniería Electrónica", "Electronic Engineering"), "rol": "Ingeniería Electrónica",
         "color": "#E91E8C", "fondo": "#FCE4EC",
         "chips": [T("🕵️ Criminología", "🕵️ Criminology"), T("🎨 Dibujo", "🎨 Drawing")]},
        {"nombre": "Sofía Alejandra Suarez Zulueta", "avatar": "👩",
         "icono_rol": "🏛️ " + T("Arquitectura", "Architecture"), "rol": "Arquitectura",
         "color": "#8E6FCE", "fondo": "#EDE7F6",
         "chips": [T("🎨 Dibujar", "🎨 Drawing"), T("🍳 Cocinar", "🍳 Cooking"), T("🎵 Música", "🎵 Music")]},
        {"nombre": "Ariana Itamar Farro Díaz", "avatar": "👩",
         "icono_rol": "🧬 " + T("Biología", "Biology"), "rol": "Biología",
         "color": "#29B6F6", "fondo": "#E1F5FE",
         "chips": [T("🎮 Videojuegos", "🎮 Video games"), T("🎬 Terror", "🎬 Horror")]},
    ]
    cols_equipo = st.columns(len(EQUIPO))
    for c, miembro in zip(cols_equipo, EQUIPO):
        with c:
            _chips_html = "".join(f'<span class="team-chip">{ch}</span>' for ch in miembro["chips"])
            st.markdown(f"""
            <div class="team-card" style="--tc-color:{miembro['color']};--tc-bg:{miembro['fondo']};">
                <div class="team-avatar">{miembro['avatar']}</div>
                <div class="team-name">{miembro['nombre'].upper()}</div>
                <div class="team-icon-role">{T("Integrante CIAM&amp;SUNI", "CIAM&amp;SUNI Member")}</div>
                <div class="team-badge">{miembro['icono_rol']}</div>
                <div class="team-chips-label">⭐ {T("Intereses &amp; Hobbies", "Interests &amp; Hobbies")}</div>
                <div class="team-chips">{_chips_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    col_a, col_b = st.columns(2)
    col_a.metric(T("Grado y sección", "Grade and Section"), T('5° "C" Secundaria', '5th Grade "C" – Secondary School'))
    col_b.metric(T("Docente", "Teacher"), "Arnadis J. Talavera Oropeza")

    st.write("")

    caja_util(T(
        "Este proyecto fue construido en equipo: cada integrante desarrolló y explicó una parte "
        "distinta de la hoja de cálculo, y luego se unieron todas las piezas en esta app para que "
        "cualquier persona —sin saber de Excel ni de nutrición— pueda usarla fácilmente. 🤝🌱",
        "This project was built as a team: each member developed and explained a different part "
        "of the spreadsheet, and all the pieces were then brought together in this app so that "
        "anyone —without knowing Excel or nutrition— can use it easily. 🤝🌱"
    ), emoji="🎓", color="#FBEAEC", borde="#7A1F2B")

    # ===== 12. Cierre bonito, con fondo degradado =====
    st.markdown(f"""
    <div style="margin-top:8px;background:linear-gradient(120deg,#EAFAEE 0%,#F8ECFB 100%);border-radius:24px;
                padding:26px 30px;text-align:center;box-shadow:0 6px 18px rgba(0,0,0,0.05);">
    <div style="font-size:1.8rem;">🌱</div>
    <p style="margin:8px 0 4px 0;color:#3C3C43;font-size:0.98rem;font-style:italic;line-height:1.6;max-width:520px;margin-left:auto;margin-right:auto;">
    "{T("Pequeños cambios generan grandes resultados. Esperamos que esta herramienta te ayude "
        "a cuidar tu salud de una forma sencilla.",
        "Small changes create big results. We hope this tool helps you take care of your "
        "health in a simple way.")}"</p>
    <p style="margin:10px 0 0 0;color:#1E5631;font-weight:900;">💚 {T("Equipo CIAM&amp;SUNI", "CIAM&amp;SUNI Team")}</p>
    </div>
    """, unsafe_allow_html=True)

# =========================================================================================
# PIE DE PÁGINA — navegación "Anterior / Siguiente" entre secciones
# (complementa a las píldoras del sidebar; conserva el estado ya ingresado por el usuario)
# =========================================================================================
st.markdown("---")
_idx_actual = OPCIONES_HOJAS.index(hoja_activa)
col_prev, col_mid, col_next = st.columns([1, 2, 1])
with col_prev:
    if _idx_actual > 0:
        if st.button(T("← Sección Anterior", "← Previous Section"), use_container_width=True, key="btn_anterior_footer"):
            st.session_state["hoja_activa"] = OPCIONES_HOJAS[_idx_actual - 1]
            st.rerun()
with col_mid:
    st.write("")
with col_next:
    if _idx_actual < len(OPCIONES_HOJAS) - 1:
        if st.button(T("Siguiente Sección →", "Next Section →"), use_container_width=True, type="primary", key="btn_siguiente_footer"):
            st.session_state["hoja_activa"] = OPCIONES_HOJAS[_idx_actual + 1]
            st.rerun()

st.markdown("---")
st.caption(T(
    "Aplicación desarrollada en Streamlit — réplica fiel del Excel 'Grupo n°4 VER.2' (Proyecto Sana "
    "Alimentación) para el proyecto de tesis escolar sobre salud pública en Lambayeque, Grupo N°04. "
    "🔒 Ningún dato ingresado se almacena: toda la información vive solo en tu sesión actual.",
    "Application built with Streamlit — a faithful replica of the 'Grupo n°4 VER.2' Excel sheet (Healthy "
    "Eating Project) for the school thesis project on public health in Lambayeque, Grupo N°04. "
    "🔒 No data you enter is stored: all information lives only in your current session."
))
