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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

st.set_page_config(page_title="CIAM&SUNI: Tu Salud, Personalizada", layout="wide", page_icon="🍎")

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


def _norm_txt(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


def buscar_alimentos(consulta, limite=12):
    q = _norm_txt(consulta).strip()
    if not q:
        return []
    exact, word_start, word_mid, contains = [], [], [], []
    for f in FOOD_DB:
        n = _norm_txt(f["nombre"])
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

# Etiqueta/badge corta que acompaña cada encabezado de sección (reemplaza el prefijo "Hoja N:")
BADGE_HOJAS = {
    0: "Configuración", 1: "Módulo Clínico", 2: "Módulo Clínico", 3: "Módulo Energético",
    4: "Módulo Energético", 5: "Control de Peso", 6: "Módulo Nutricional", 7: "Módulo Nutricional",
    8: "Recurso Externo", 9: "Plan Alimenticio", 10: "Módulo Climático", 11: "Aporte Especial",
    12: "Aporte Especial", 13: "Proyección", 14: "Reporte Final", 15: "Equipo",
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

/* ---------- Navegación lateral tipo "Pills" (sidebar, 17 secciones siempre visibles) ---------- */
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
    <b style="color:{borde};">{emoji} ¿Para qué te sirve esto?</b><br>
    <span style="color:#1C1C1E;">{texto}</span>
    </div>
    """, unsafe_allow_html=True)


def hoja_header(idx, subtitulo=None, ilustracion=None, tip=None):
    """Encabezado tipo banner: degradado pastel suave, título profesional SIN el prefijo
    'Hoja N:', subtítulo descriptivo y un badge de color al costado (p. ej. 'Módulo Clínico').
    Admite opcionalmente una ilustración SVG decorativa a la derecha y una burbuja de
    'tip' tipo chat, para las hojas con hero enriquecido (Bento Grid)."""
    numero, titulo, emoji, borde, fondo = COLORES[idx]
    badge = BADGE_HOJAS.get(idx, "Módulo")
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


def formula_badge(formula, autor="", referencia="", icono="ℹ️", texto="Ver fórmula"):
    """Insignia discreta tipo 'chip' que muestra, al pasar el cursor (tooltip nativo del
    navegador vía atributo `title`), la fórmula clínica exacta junto con su autor y su
    referencia científica — cumpliendo la norma clínica 4.1 sin saturar visualmente la
    pantalla. Se usa junto a títulos, métricas o resultados en cada hoja de la app."""
    partes = [f"Fórmula: {formula}"]
    if autor:
        partes.append(f"Autor: {autor}")
    if referencia:
        partes.append(f"Referencia: {referencia}")
    tooltip = " · ".join(partes).replace('"', "'").replace("\n", " ")
    return (f'<span class="formula-badge" title="{tooltip}">{icono} '
            f'<span class="formula-badge-txt">{texto}</span></span>')


def _resolver_imagen(ruta):
    """Busca una imagen probando varias ubicaciones (la ruta indicada, directamente en /assets,
    y en /assets/hojas) y varias extensiones/mayúsculas (.jpg, .JPG, .jpeg, .png, etc.).
    Devuelve la primera ruta que exista, o None si no encuentra nada."""
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
        ["Peso", f"{datos['peso']:.2f} kg"],
        ["Estatura", f"{datos['estatura']} cm"],
        ["IMC", f"{datos['imc']}  —  {datos['categoria_imc']}" + (f"  (Percentil {datos['percentil']})" if datos.get("percentil") else "")],
    ]))

    # ---------------- 2. REQUERIMIENTO ENERGÉTICO ----------------
    story.append(Paragraph("🔥 Requerimiento energético", estilo_seccion))
    story.append(_tabla_datos([
        ["TMB (Tasa Metabólica Basal)", f"{datos['tmb']:.2f} kcal/día"],
        ["RCD (Gasto calórico diario)", f"{datos['rcd']:.2f} kcal/día"],
        ["Meta calórica (según objetivo)", f"{datos['rcd_final']:.2f} kcal/día"],
        ["Objetivo nutricional", f"{datos['objetivo']}"],
    ]))

    # ---------------- 3. MACRONUTRIENTES ----------------
    story.append(Paragraph("🍽️ Macronutrientes recomendados (diarios)", estilo_seccion))
    tabla_macros = Table([
        ["Macronutriente", "Gramos", "Kcal/día", "% del total"],
        ["Proteínas", f"{datos['gr_prot']:.2f} g", f"{datos['cal_prot']:.2f}", "20%"],
        ["Carbohidratos", f"{datos['gr_carb']:.2f} g", f"{datos['cal_carb']:.2f}", "50%"],
        ["Grasas", f"{datos['gr_gras']:.2f} g", f"{datos['cal_gras']:.2f}", "30%"],
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
        ["Peso actual", f"{datos['peso']:.2f} kg"],
        ["Peso estimado en 60 días", f"{datos['peso_proyectado']:.2f} kg"],
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
        f'<div class="bento-pill" style="background:{estilo["hex"]};color:#FFFFFF;margin-top:8px;">⚠️ Requiere atención</div>'
        if es_alerta else
        f'<div class="bento-pill" style="background:{estilo["hex"]}1A;color:{estilo["hex"]};margin-top:8px;">✅ En buen camino</div>'
    )
    st.markdown(f"""
    <div class="bento-card" style="background:{estilo['fondo']};text-align:center;
                border:1.5px solid {estilo['hex']}33;">
        <div class="bento-eyebrow" style="text-align:center;">{titulo}</div>
        <div style="font-size:2.2rem;margin-top:6px;">{_ILUSTRA_CATEGORIA.get(estilo['colorSemaforo'], '⚪')}</div>
        <div style="font-weight:800;font-size:1.15rem;color:{estilo['hex']};letter-spacing:-0.01em;margin-top:2px;">{categoria}</div>
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
_ESCALA_MIN, _ESCALA_MAX = 0, 40


def tabla_categorias_imc_visual(imc_usuario=None):
    """Tabla de alto impacto visual (reemplaza tabla_bonita en esta sección): encabezado con
    icono + subtítulo, cabecera de columnas lila, avatar circular + subtexto por clasificación,
    y en la 3ra columna un indicador de línea con dos puntos marcando el inicio/fin de cada
    rango sobre la escala global (0 a 40+), muy similar a la referencia de diseño."""
    filas_html = []
    for nombre, rango_txt, subtxt, icono, color, ini, fin, riesgo in _CATEGORIAS_IMC_DEF:
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
                <div class="imc-table-title">Categorías generales de IMC</div>
                <div class="imc-table-sub">El Índice de Masa Corporal (IMC) es una guía que relaciona tu peso con tu altura para conocer tu estado nutricional.</div>
            </div>
        </div>
        <div class="imc-table-head" style="grid-template-columns:1.5fr 0.9fr 1.7fr 1fr;">
            <span>🔖 Clasificación</span><span>📝 Rango de IMC</span><span>📊 ¿Dónde te encuentras?</span><span>🚨 Riesgo</span>
        </div>
        {''.join(filas_html)}
        <div class="imc-footer-banner">
            <span class="imc-footer-avatar">👩‍⚕️</span>
            <div style="font-size:0.82rem;color:#5C6B60;max-width:480px;">
                <b style="color:#6A1B9A;">💡 Importante:</b> el IMC es una referencia general.
                Consulta siempre con un profesional de salud para una evaluación completa y recomendaciones personalizadas.
            </div>
            <div class="imc-footer-tip">🛡️ ¡Pequeños cambios hoy, grandes resultados mañana!</div>
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


_PERC_CATEGORIA_COL = {"Bajo Peso": 0, "Peso Saludable": 1, "Sobrepeso": 2, "Obesidad": 3}


def _tarjeta_percentil_genero(genero_tabla, tabla, edad_usuario=None, genero_usuario=None, categoria_usuario=None):
    """Construye una tarjeta de percentiles (Mujer=rosa / Hombre=azul) con cabecera ilustrada,
    columnas P5/P50/P85/P95 con color propio, filas alternadas, la fila del usuario resaltada,
    y además la columna (P5/P50/P85/P95) donde cayó su IMC resaltada con un marco de color."""
    if genero_tabla == "Mujer":
        fondo_banner, color_titulo, icono, badge = "#FCE4EC", "#C2185B", "👧", "♀"
    else:
        fondo_banner, color_titulo, icono, badge = "#E3F2FD", "#1976D2", "👦", "♂"

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

    ths = "".join(
        f'<th style="background:{bg};color:{fg};">{cod}<br><span style="font-weight:600;font-size:0.62rem;">{lbl}</span></th>'
        for cod, lbl, bg, fg in _PERC_COL_ESTILO
    )

    html = f"""
    <div class="perc-card">
        <div class="perc-banner" style="background:{fondo_banner};">
            <span class="perc-banner-icon">{icono}</span>
            <span class="perc-banner-title" style="color:{color_titulo};">{genero_tabla.upper()}</span>
            <span class="perc-badge" style="color:{color_titulo};">{badge}</span>
        </div>
        <div style="max-height:340px;overflow-y:auto;">
        <table class="perc-table">
            <thead><tr><th style="background:#F5F5F7;color:#5C6B60;">Edad<br><span style="font-weight:600;font-size:0.62rem;">(años)</span></th>{ths}</tr></thead>
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


def panel_diagnostico_nutricional(imc, percentil_valor, categoria, con_percentil=True):
    """Sección 1: 'Tu Diagnóstico Nutricional' — 4 tarjetas iguales (IMC, Percentil, Estado,
    Riesgo) seguidas de una frase-resumen grande, en vez del flujo largo de cajas dispersas."""
    estilo = color_categoria_imc(categoria)
    riesgo_txt, riesgo_color = _RIESGO_POR_CATEGORIA.get(categoria, ("—", "#8E8E93"))
    perc_display = f"P{percentil_valor}" if (con_percentil and percentil_valor is not None) else "—"
    tarjetas = [
        ("IMC", str(imc), "⚖️", "#1E5631"),
        ("Percentil", perc_display, "📊", "#1E88E5"),
        ("Estado", categoria, "🩺", estilo["hex"]),
        ("Riesgo", riesgo_txt, "🚨", riesgo_color),
    ]
    _kpis = "".join(f"""
        <div class="diag-kpi">
            <div class="diag-kpi-icon">{ic}</div>
            <div class="diag-kpi-label">{lbl}</div>
            <div class="diag-kpi-val" style="color:{col};">{val}</div>
        </div>""" for lbl, val, ic, col in tarjetas)
    frase = _FRASE_POR_CATEGORIA.get(categoria, "Revisa tus datos para conocer tu diagnóstico nutricional.")
    st.markdown(f"""
    <div class="diag-panel">
        <div class="diag-panel-title">🩺 Tu Diagnóstico Nutricional</div>
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


def escala_horizontal_imc(imc, categoria, etapa, percentil_valor=None):
    """Sección 2: escala horizontal (reemplaza el velocímetro como pieza principal) que muestra
    de un vistazo en qué zona cae el valor del usuario, con una flecha marcando su posición."""
    _es_infantil = etapa in ("Niñez", "Adolescencia") and percentil_valor is not None
    if _es_infantil:
        _nombres_colores = [(n, c) for n, c, _ in _ESCALA_INFANTIL_ZONAS]
        _idx_map = {"Bajo Peso": 0, "Peso Saludable": 1, "Sobrepeso": 2, "Obesidad": 3}
        _idx_activo = _idx_map.get(categoria, 1)
        _pos_pct = {0: 5, 1: 45, 2: 82, 3: 96}.get(_idx_activo, 45)
        _valor_mostrar = f"P{percentil_valor}"
    else:
        _nombres_colores = [(n, c) for n, c, _, _ in _ESCALA_ADULTO_ZONAS]
        _min_v, _max_v = 10.0, 40.0
        _pos_pct = max(2.0, min(98.0, (imc - _min_v) / (_max_v - _min_v) * 100))
        _valor_mostrar = str(imc)

    _segmentos = "".join(f'<div style="flex:1;background:{c};"></div>' for _, c in _nombres_colores)
    _etiquetas = "".join(f"<span>{n}</span>" for n, _ in _nombres_colores)
    estilo = color_categoria_imc(categoria)
    st.markdown(f"""
    <div class="escala-imc-wrap">
        <span class="bento-eyebrow">Dónde te ubicas</span>
        <div style="position:relative;">
            <div class="escala-imc-marker" style="left:{_pos_pct:.1f}%;">
                <div style="font-weight:800;font-size:0.95rem;color:{estilo['hex']};">Tú ({_valor_mostrar})</div>
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
        <span class="bento-eyebrow">👦 Percentil {percentil_valor}</span>
        <div style="font-size:0.82rem;color:#5C6B60;margin-top:4px;">De cada 100 niños de tu misma edad y sexo:</div>
        <div class="perc-visual-grid">{_dots}</div>
        <div style="font-size:0.85rem;color:#17301F;line-height:1.5;">
            <b style="color:#1E88E5;">{_debajo}</b> están por debajo de tu IMC.<br>
            Solo <b style="color:#1E88E5;">{100 - _debajo}</b> tienen un IMC mayor.
        </div>
    </div>
    """, unsafe_allow_html=True)


_ESTADO_CHECKLIST = {
    "Bajo Peso": ["Riesgo de déficit nutricional ↑", "Puede afectar energía y defensas", "Conviene aumentar ingesta calórica de calidad", "Recomendable acudir a nutrición"],
    "Peso Saludable": ["Riesgo cardiovascular bajo", "Riesgo metabólico bajo", "Mantén tus hábitos actuales", "Sigue con controles periódicos"],
    "Sobrepeso": ["Riesgo cardiovascular ↑", "Riesgo metabólico ↑", "Conviene mejorar la alimentación", "Recomendable acudir a nutrición"],
    "Obesidad": ["Riesgo cardiovascular ↑↑", "Riesgo metabólico ↑↑", "Conviene reducir peso", "Recomendable acudir a nutrición"],
}


def tarjeta_estado_nutricional(categoria):
    """Sección 4: tarjeta 'Estado Nutricional' tipo diagnóstico con checklist, en vez de
    mostrar solamente la palabra de la categoría."""
    estilo = color_categoria_imc(categoria)
    _items = _ESTADO_CHECKLIST.get(categoria, _ESTADO_CHECKLIST["Sobrepeso"])
    _lis = "".join(f'<div class="estado-nutri-item"><span>✓</span><span>{it}</span></div>' for it in _items)
    st.markdown(f"""
    <div class="bento-card" style="border-top:4px solid {estilo['hex']};">
        <span class="bento-eyebrow">🩺 Estado Nutricional</span>
        <div style="font-weight:800;font-size:1.2rem;color:{estilo['hex']};margin:4px 0 8px 0;">{categoria}</div>
        {_lis}
    </div>
    """, unsafe_allow_html=True)


def interpretacion_inteligente_imc(imc, categoria, etapa, riesgo_txt):
    """Sección 5: caja 'Interpretación Inteligente' con bullets, en el mismo estilo que el
    resumen clínico del análisis sanguíneo."""
    _puntos = []
    if categoria == "Peso Saludable":
        _puntos = ["Tu peso está dentro del rango saludable para tu edad y estatura.",
                    "El objetivo es mantener tus hábitos actuales.",
                    "Continúa con actividad física regular.",
                    "Mantén una alimentación variada y equilibrada."]
    else:
        _puntos = [f"Existe {'déficit' if categoria == 'Bajo Peso' else 'exceso'} de peso según tu IMC{' y percentil' if etapa in ('Niñez', 'Adolescencia') else ''}.",
                    "El crecimiento y la evolución del peso deben seguir vigilándose.",
                    "Conviene reducir bebidas azucaradas y ultraprocesados." if categoria != "Bajo Peso" else "Conviene aumentar el aporte calórico con alimentos nutritivos.",
                    "Incrementar la actividad física y cuidar las horas de sueño."]
    _bg = "#EAFAEE" if categoria == "Peso Saludable" else "#FFF6E0"
    _color = "#1E5631" if categoria == "Peso Saludable" else "#B8860B"
    _lis = "".join(f"<li>{p}</li>" for p in _puntos)
    st.markdown(f"""
    <div style="background:{_bg};border-radius:18px;padding:16px 20px;margin-top:6px;">
        <div style="font-weight:800;color:{_color};margin-bottom:6px;">🧠 Interpretación Inteligente</div>
        <div style="font-size:0.85rem;color:#3A3A3C;">Según tu IMC{' y tu percentil' if etapa in ('Niñez','Adolescencia') else ''} (riesgo: {riesgo_txt}):</div>
        <ul style="margin:6px 0 0 18px;padding:0;font-size:0.85rem;color:#3A3A3C;line-height:1.7;">{_lis}</ul>
    </div>
    """, unsafe_allow_html=True)


def que_influye_imc():
    """Sección 6: '¿Qué puede influir en tu IMC?' con iconos grandes (reemplaza el bloque
    'Tu IMC puede estar relacionado con', que sonaba a publicidad)."""
    st.markdown('<div class="info3-title" style="margin-top:4px;">🔎 ¿Qué puede influir en tu IMC?</div>', unsafe_allow_html=True)
    fila_dominios_salud([
        ("🥤", "#1E88E5", "Bebidas azucaradas"),
        ("🍔", "#FF9500", "Alimentación"),
        ("🏃", "#34C759", "Actividad física"),
        ("😴", "#AF52DE", "Sueño"),
        ("🧬", "#FF2D55", "Genética"),
    ])


def recordar_alerta_clinica():
    """Sección 7: alerta tipo clínica para el aviso 'El IMC no diagnostica enfermedades'."""
    st.markdown("""
    <div style="background:#FFF9E5;border:1px solid #FFE58F55;border-radius:16px;padding:16px 18px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">💡 Importante</div>
        <div style="font-size:0.85rem;color:#7A5C00;line-height:1.6;">
        El IMC <b>NO</b> diagnostica enfermedades. Es una herramienta de detección.<br>
        Siempre debe interpretarse junto con:<br>
        ✔ Edad &nbsp;&nbsp; ✔ Sexo &nbsp;&nbsp; ✔ Composición corporal &nbsp;&nbsp; ✔ Evaluación clínica
        </div>
    </div>
    """, unsafe_allow_html=True)


def links_uniformes_mas_info():
    """Sección 8: fila de enlaces 'Más información' con estilo uniforme (CDC, OMS, MedlinePlus,
    Mayo Clinic), reemplazando los botones grandes tipo anuncio."""
    st.markdown('<div class="info3-title" style="margin-top:4px;">📚 Más información</div>', unsafe_allow_html=True)
    cl1, cl2, cl3, cl4 = st.columns(4)
    _links = [
        ("📚", "#1565C0", "CDC", "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html"),
        ("❤️", "#C0392B", "OMS", "https://www.who.int/es/news-room/fact-sheets/detail/obesity-and-overweight"),
        ("🥗", "#2E9E4A", "MedlinePlus", "https://medlineplus.gov/spanish/ency/article/007196.htm"),
        ("🏥", "#AF52DE", "Mayo Clinic", "https://www.mayoclinic.org/es/healthy-lifestyle/adult-health/in-depth/bmi-calculator/itt-20084938"),
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


def acciones_desde_hoy():
    """Sección 12: '¿Qué puedes hacer desde hoy?' con tarjetas cortas de hábitos, en vez de
    consejos largos en párrafo."""
    st.markdown("#### 🌱 ¿Qué puedes hacer desde hoy?")
    _cols = st.columns(len(_ACCIONES_DESDE_HOY))
    for _col, (_em, _txt) in zip(_cols, _ACCIONES_DESDE_HOY):
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
        st.success(f"🎯 Tu IMC actual ({imc}) ya está dentro del rango saludable (18.5 – 24.9). ¡Sigue así!")
        return
    _min_v, _max_v, _meta = 10.0, 40.0, 22.0
    _pos_tu = max(2.0, min(98.0, (imc - _min_v) / (_max_v - _min_v) * 100))
    _pos_meta = max(2.0, min(98.0, (_meta - _min_v) / (_max_v - _min_v) * 100))
    _fill_izq, _fill_der = (min(_pos_tu, _pos_meta), max(_pos_tu, _pos_meta))
    _diff = round(abs(imc - _meta), 1)
    st.markdown(f"""
    <div class="bento-card">
        <span class="bento-eyebrow">📈 Progreso hacia un IMC saludable</span>
        <div style="position:relative;">
            <div class="progreso-imc-meta" style="left:{_pos_meta:.1f}%;">🎯 Meta<br>{_meta:g}</div>
            <div class="progreso-imc-track">
                <div class="progreso-imc-fill" style="left:{_fill_izq:.1f}%;width:{max(1.0, _fill_der - _fill_izq):.1f}%;"></div>
            </div>
            <div class="progreso-imc-tu" style="left:{_pos_tu:.1f}%;">📍 Tú<br>{imc:g}</div>
        </div>
        <div style="margin-top:26px;font-size:0.85rem;color:#5C6B60;">
        Faltan aproximadamente <b style="color:#1E5631;">{_diff} puntos de IMC</b> para entrar al rango saludable.
        </div>
    </div>
    """, unsafe_allow_html=True)


def conexion_resto_sistema():
    """Sección 14: enlaces cruzados hacia otras hojas del sistema para que se sienta como
    una sola plataforma y no como hojas aisladas."""
    st.markdown("#### 🔗 ¿Cómo influye este resultado en el resto del sistema?")
    _conexiones = [
        ("🩸", "#FF3B30", "Análisis sanguíneo", "El sobrepeso puede elevar colesterol y triglicéridos."),
        ("🔥", "#FF9500", "TMB", "Tu metabolismo se calculó usando estos datos."),
        ("🍎", "#34C759", "Dieta", "Tu plan alimenticio fue generado considerando tu IMC."),
        ("📈", "#5AC8FA", "Proyección", "Simula cómo cambiaría tu peso con tu meta actual."),
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
    st.markdown("""
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
    """, unsafe_allow_html=True)


def tarjeta_resultado_tmb(tmb_valor):
    """Sección 2: tarjeta grande y limpia con el resultado de la TMB."""
    st.markdown(f"""
    <div class="tmb-resultado-card">
        <span class="bento-eyebrow">🔥 Tu TMB</span>
        <div class="tmb-resultado-num">{tmb_valor:.0f} kcal/día</div>
        <div style="font-size:0.88rem;color:#5C6B60;max-width:420px;margin:0 auto;line-height:1.6;">
        Tu cuerpo necesita aproximadamente <b style="color:#E67E22;">{tmb_valor:.0f} kcal</b> al día
        únicamente para mantener sus funciones vitales.
        </div>
    </div>
    """, unsafe_allow_html=True)


def formula_horizontal_tmb(peso, estatura, edad, genero_activo, tmb_valor):
    """Sección 3: fórmula de Mifflin-St Jeor mostrada de forma horizontal para Hombre y Mujer,
    cada una con su propio color (sin usar azul/rosa) y flechas apuntando a la derecha."""
    _filas = [
        ("Hombre", "🧑", "#00897B", "#E0F2F1",
         [("Peso", f"10 × {peso:g}", f"{10*peso:.1f}"), ("Altura", f"+ 6.25 × {estatura:g}", f"{6.25*estatura:.1f}"),
          ("Edad", f"− 5 × {edad:g}", f"−{5*edad:.1f}"), ("Constante", "+ 5", "+5")],
         (10 * peso) + (6.25 * estatura) - (5 * edad) + 5),
        ("Mujer", "🧑‍🦱", "#D4692B", "#FFF1E6",
         [("Peso", f"10 × {peso:g}", f"{10*peso:.1f}"), ("Altura", f"+ 6.25 × {estatura:g}", f"{6.25*estatura:.1f}"),
          ("Edad", f"− 5 × {edad:g}", f"−{5*edad:.1f}"), ("Constante", "− 161", "−161")],
         (10 * peso) + (6.25 * estatura) - (5 * edad) - 161),
    ]
    for _nombre, _icono, _color, _fondo, _pasos, _res in _filas:
        _es_activo = _nombre == genero_activo
        _boxes = "".join(
            f'<div class="tmb-formula-box" style="background:{_color}1A;color:{_color};">{p}<span class="tmb-box-sub">{op}</span></div>'
            f'<span class="tmb-formula-arrow" style="color:{_color};">→</span>'
            for p, op, val in _pasos
        )
        st.markdown(f"""
        <div class="tmb-formula-genero-wrap" style="{'box-shadow:0 0 0 2px ' + _color + ';' if _es_activo else ''}">
            <div class="tmb-formula-genero-title" style="color:{_color};">{_icono} Fórmula para {_nombre}
                {' <span class=\"bento-pill\" style=\"background:' + _color + ';color:#FFFFFF;\">Tu fórmula</span>' if _es_activo else ''}</div>
            <div class="tmb-formula-flow">
                {_boxes}
                <div class="tmb-formula-box" style="background:{_color};color:#FFFFFF;">= TMB<span class="tmb-box-sub">{_res:.0f} kcal/día</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def tarjeta_quien_creo_formula():
    """Sección 3b (corregida): Mifflin-St Jeor no es una persona, sino el nombre de la
    ecuación publicada en 1990 por un equipo de investigadores."""
    st.markdown("""
    <div class="tmb-quien-card">
        <div style="font-weight:800;color:#5856D6;margin-bottom:6px;">👨‍🔬 ¿Quién desarrolló esta fórmula?</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        La ecuación de <b>Mifflin–St Jeor</b> fue publicada en 1990 por los investigadores
        <b>Mark D. Mifflin</b>, <b>Sachiko T. St Jeor</b> y su equipo. Actualmente es una de las
        fórmulas más utilizadas por nutricionistas y hospitales para estimar la Tasa Metabólica
        Basal, por su buena precisión en adultos.
        </div>
    </div>
    """, unsafe_allow_html=True)


def tarjeta_por_que_mifflin():
    """Sección 4: mini comparación de por qué se usa Mifflin-St Jeor."""
    _items = ["Mayor precisión que fórmulas antiguas.", "Recomendada en nutrición clínica.",
              "Utilizada por profesionales de la salud.", "Sirve para calcular las calorías que necesita el cuerpo en reposo."]
    _lis = "".join(f'<div class="tmb-porque-item"><span>✔</span><span>{it}</span></div>' for it in _items)
    st.markdown(f"""
    <div class="tmb-porque-card">
        <div style="font-weight:800;color:#0E6B4F;margin-bottom:2px;">📚 ¿Por qué usamos Mifflin-St Jeor?</div>
        {_lis}
    </div>
    """, unsafe_allow_html=True)


def flujo_modulos_tmb():
    """Sección 5: flujo horizontal (flechas a la derecha) de los módulos que usan la TMB."""
    st.markdown("""
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
    """, unsafe_allow_html=True)


def central_energetica_tmb(tmb_valor):
    """Ilustración alternativa tipo 'central eléctrica': la TMB alimenta los órganos vitales,
    cada uno con un pequeño indicador luminoso."""
    _organos = [("❤️", "Corazón"), ("🧠", "Cerebro"), ("🫁", "Pulmones"), ("🌡️", "Temperatura"), ("🩸", "Circulación")]
    _leds = "".join(f'<div class="tmb-central-organo"><div style="font-size:1.6rem;">{ic}</div>'
                     f'<div class="tmb-central-led"></div><div class="tmb-central-label">{lb}</div></div>' for ic, lb in _organos)
    st.markdown(f"""
    <div class="tmb-central-wrap">
        <div style="font-size:1.6rem;">⚡</div>
        <div style="font-weight:800;letter-spacing:0.06em;font-size:0.85rem;color:#C7CBE0;">CENTRAL ENERGÉTICA</div>
        <div class="tmb-central-kcal">🔥 {tmb_valor:.0f} kcal</div>
        <div class="tmb-central-organos">{_leds}</div>
    </div>
    """, unsafe_allow_html=True)


def interpretacion_inteligente_tmb(tmb_valor):
    """Sección 6: resumen inteligente breve, dejando claro que la TMB no incluye actividad física."""
    st.markdown(f"""
    <div style="background:#FFF3E0;border-radius:18px;padding:16px 20px;margin-top:6px;">
        <div style="font-weight:800;color:#B8860B;margin-bottom:6px;">🧠 Interpretación Inteligente</div>
        <div style="font-size:0.85rem;color:#3A3A3C;line-height:1.7;">
        Tu organismo necesita aproximadamente <b>{tmb_valor:.0f} kcal</b> al día para mantener sus funciones vitales.<br>
        Este valor <b>NO</b> representa las calorías que necesitas para hacer ejercicio, caminar o estudiar.<br>
        Es la energía mínima necesaria para vivir.
        </div>
    </div>
    """, unsafe_allow_html=True)


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


def _build_panel_macros_creativo(gr_prot_v, gr_gras_v, gr_carb_v, peso_v):
    """Panel de control visual de macronutrientes con diales Altair y banner de reajuste (Prompt 2)."""
    st.markdown("#### 🎛️ Panel de Control de Macros")
    max_prot = max(peso_v * 2.2, 1)
    max_gras = max(peso_v * 1.2, 1)
    pct_prot = gr_prot_v / max_prot
    pct_gras = gr_gras_v / max_gras
    pct_carb = 0.50  # los carbohidratos siempre representan el 50% de tu energía diaria

    m1, m2, m3 = st.columns(3)
    with m1:
        _gauge_altair(pct_prot, "#FF6B5B", f"Tus Ladrillos: {gr_prot_v:.2f} g/día",
                      "Para no perder el músculo que ya tienes.", "prot")
    with m2:
        _gauge_altair(pct_gras, "#FFC93C", f"Tus Hormonas: {gr_gras_v:.2f} g/día",
                      "El 'combustible' que mantiene tu cuerpo funcionando bien. ¡No lo bajes demasiado!", "gras")
    with m3:
        _gauge_altair(pct_carb, "#4FC3F7", f"Tu Energía: {gr_carb_v:.2f} g/día",
                      "El resto de la energía para tu día y entrenamientos.", "carb")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#FF9500 0%,#FFB300 100%);border-radius:20px;
                padding:16px 22px;margin-top:14px;color:white;display:flex;align-items:center;gap:14px;
                box-shadow:0 10px 24px rgba(255,149,0,0.30);">
        <div style="font-size:2rem;">🔄</div>
        <div style="font-size:0.95rem;font-weight:700;line-height:1.4;">
            ⚠️ ¡Atención! Recalcula tu plan cada vez que bajes o subas entre 3 y 5 kg.
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

def _img_b64(path):
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return None

_logo_b64 = _img_b64(_LOGO_ANCHO)

# --- 1. MEMBRETE INSTITUCIONAL — tarjeta grande y exclusiva, con el escudo protagonista ---
st.markdown("""
<div style="background:linear-gradient(120deg,#FFFFFF 0%,#F4F9F4 100%);border-radius:26px;
padding:26px 34px;margin-bottom:14px;box-shadow:0 6px 20px rgba(30,86,49,0.10);
border:1.5px solid rgba(30,86,49,0.14);">
""", unsafe_allow_html=True)
_col_esc, _col_memb = st.columns([1, 4])
with _col_esc:
    if _ESCUDO.exists():
        st.image(str(_ESCUDO), width=150)
    elif _logo_b64:
        st.image(str(_LOGO_ANCHO), use_container_width=True)
with _col_memb:
    st.markdown("""
    <div style="display:flex;flex-direction:column;justify-content:center;height:100%;padding-top:6px;">
    <p style="margin:0;font-weight:800;color:#1E5631;font-size:1.55rem;letter-spacing:-0.01em;
       font-family:Georgia,'Times New Roman',serif;">🏫 C.E.P. "Santa María Reina"</p>
    <p style="margin:2px 0 12px 0;color:#5C6B60;font-size:0.95rem;font-weight:600;">Chiclayo</p>
    <p style="margin:0;color:#8A94A6;font-size:0.82rem;">Proyecto desarrollado para <b style="color:#1E5631;">5.º "C"</b>
    &nbsp;·&nbsp; Área de Ciencia y Tecnología &nbsp;·&nbsp; Grupo N.° 04</p>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- 2. HERO CIAM&SUNI — logotipo único (sin duplicados), descripción clara e ilustración ---
st.markdown("""
<div class="hero-card">
    <div class="hero-emoji-decor">🥗🍎🥦🥛🥑</div>
    <h1>🥗 CIAM&SUNI</h1>
    <p style="margin:0 0 14px 0;font-size:1.15rem;font-weight:700;opacity:0.95;">Tu Salud, Personalizada</p>
    <p class="hero-sub">CIAM&SUNI analiza tu información para estimar tu estado nutricional, calcular tu
    requerimiento energético y ayudarte a comprender cómo influye la alimentación en tu salud, mediante
    explicaciones sencillas y visuales.</p>
</div>
""", unsafe_allow_html=True)

# --- Tarjetas de características (reemplazan los chips: 4 tarjetas claras) ---
st.markdown("""
<div class="feature-row">
    <div class="feature-card">
        <div class="fc-emoji">🍎</div>
        <div class="fc-title">Nutrición personalizada</div>
        <div class="fc-text">Cálculos adaptados a tus propios datos: edad, peso, altura y etapa de vida.</div>
    </div>
    <div class="feature-card">
        <div class="fc-emoji">🧮</div>
        <div class="fc-title">Basado en evidencia científica</div>
        <div class="fc-text">Fórmulas reconocidas (Mifflin-St Jeor, FAO/OMS/UNU) aplicadas paso a paso.</div>
    </div>
    <div class="feature-card">
        <div class="fc-emoji">🌡️</div>
        <div class="fc-title">Adaptado al clima de Chiclayo</div>
        <div class="fc-text">Un ajuste extra que considera el clima cálido de nuestra región.</div>
    </div>
    <div class="feature-card">
        <div class="fc-emoji">📊</div>
        <div class="fc-title">Resultados fáciles de comprender</div>
        <div class="fc-text">Cada cálculo se explica en lenguaje simple: qué significa y qué hacer con él.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 3. "Comienza aquí" — Onboarding Steps rediseñado (Cards Grid + Callout) -------------
st.markdown("""
<div style="margin:18px 0 0 0;">
<p style="margin:0 0 2px 0;font-weight:700;color:#1E5631;font-size:1.35rem;">🚀 ¿Cómo empezar?</p>
<p style="margin:0 0 16px 0;color:#5C6B60;font-size:0.92rem;">Sigue estos simples pasos para obtener tu diagnóstico personalizado.</p>
</div>
""", unsafe_allow_html=True)

_ONBOARD_STEPS = [
    ("1", "📝", "Ingresa tus datos", "Completa tu información personal en el panel izquierdo.",
     "#EAF4FE", "#8FC1F2", "#1565C0"),
    ("2", "🧩", "Explora las secciones", "Navega libremente por las 17 áreas del centro de control.",
     "#F3EEFB", "#C6AEE8", "#6A3FA0"),
    ("3", "🔍", "Revisa tus resultados", "Descubre tus indicadores explicados paso a paso.",
     "#EAFAEE", "#9BD8AE", "#1E5631"),
    ("4", "📄", "Descarga tu PDF", "Obtén tu reporte final completo y listo para guardar.",
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

st.markdown("""
<div style="display:flex;align-items:center;gap:10px;background:#F2F7F3;border:1px solid #D8E6DA;
border-radius:999px;padding:12px 22px;margin:14px 0 4px 0;">
<span style="font-size:1.1rem;">🔒</span>
<span style="color:#3C4A3F;font-size:0.85rem;">Solo tendrás que ingresar tus datos una vez durante esta sesión.
Luego podrás moverte libremente entre todas las secciones cuando quieras.</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p style="text-align:center;color:#5C6B60;font-size:0.9rem;font-style:italic;margin:0 0 18px 0;">
"Cada persona tiene necesidades nutricionales diferentes. Esta aplicación adapta los cálculos utilizando
la información que ingreses, para brindarte resultados personalizados y fáciles de interpretar."</p>
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

st.markdown('<p class="frase-motivadora">🍎 "Comer bien no es una dieta, es un acto de amor hacia ti mismo" 💚</p>', unsafe_allow_html=True)

# --- Acceso directo al Excel original, para que cualquiera pueda abrirlo/descargarlo libremente ---
_POSIBLES_NOMBRES_EXCEL = [
    "Proyecto sana alimentacion - GrupoN4 CIAM&SUNI.xlsx",
    "Proyecto_sana_alimentacion_-_GrupoN4_CIAM_SUNI.xlsx",
    "Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx",
    "Grupo_n_4_VER_2.xlsx", "Grupo_n_4_VER_2__1_.xlsx", "Grupo n°4 VER.2.xlsx", "Grupo_n_4_VER.2.xlsx",
]
def _buscar_excel_original():
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

st.markdown("---")

# =========================================================================================
# NAVEGACIÓN — 17 secciones en un panel lateral fijo (Sidebar Pill Navigation)
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
    "10.-CLIMA CHICLAYO",
    "11.-APORTE 1: EMBARAZO",
    "12.-APORTE 2: CAFEÍNA",
    "13.-LÍNEA DE TIEMPO",
    "📄 MI REPORTE",
    "🎓 SOBRE NOSOTRAS",
]

# Ícono + etiqueta corta para cada píldora del sidebar (17 secciones, siempre visibles)
ETIQUETAS_NAV = {
    "0.-DATOS":                    ("⚙️", "Mis Datos"),
    "1.-ANÁLISIS SANGUÍNEO":       ("🩸", "Análisis Sanguíneo"),
    "1B.-ESTADO FISIOLÓGICO":      ("❤️", "Estado Fisiológico"),
    "2.-IMC Y PERCENTIL":          ("⚖️", "IMC y Percentil"),
    "3.-TMB":                      ("🔥", "TMB"),
    "4.-RCD":                      ("⚡", "RCD"),
    "5.-CONTROL DE PESO":          ("📈", "Control de Peso"),
    "6.-MACRONUTRIENTES":          ("🥗", "Macronutrientes"),
    "7.-PORCIONES":                ("🍎", "Porciones del Día"),
    "8.-FATSECRET":                ("🇵🇪", "Base de Alimentos"),
    "9.-DIETA":                    ("📝", "Dieta"),
    "10.-CLIMA CHICLAYO":          ("🌤️", "Clima Chiclayo"),
    "11.-APORTE 1: EMBARAZO":      ("🤰", "TMB en Embarazo"),
    "12.-APORTE 2: CAFEÍNA":       ("☕", "Límite de Cafeína"),
    "13.-LÍNEA DE TIEMPO":         ("🎯", "¿Cómo cambia tu peso?"),
    "📄 MI REPORTE":               ("📄", "Mi Reporte"),
    "🎓 SOBRE NOSOTRAS":           ("👥", "Sobre Nosotros"),
}

_DEFAULTS_SESION = {
    "nombre_usuario": "", "genero": "Hombre", "peso": 75.0, "estatura": 168, "edad": 9,
    "actividad": "Ligero", "objetivo": "Bajar de peso",
    "ajuste_bajar_sel": "Equilibrado (-20%) ⭐ Recomendado",
    "ajuste_subir_sel": "Equilibrado (+15%) ⭐ Recomendado",
    "spo2": 0.0, "pulso": 0, "temp_corp": 34.0, "pas": 0, "pad": 0,
    "hemo": 0.0, "trigli": 0.0, "gluco": 0.0, "coles": 0.0, "hierro": 0.0,
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

with st.sidebar.expander("📝 Llenar / Editar Mis Datos", expanded=True):
    def _badge_vital(valor, unidad, color_key, etiqueta):
        est = SEMAFORO_ESTILO[color_key]
        st.markdown(f"""<div style="margin-top:4px;display:inline-block;background:{est['fondo']};color:{est['hex']};
                    font-weight:800;font-size:0.78rem;padding:4px 12px;border-radius:999px;">
                    {est['emoji']} {etiqueta}{f' · {valor}{unidad}' if valor not in (0, 0.0) else ''}</div>""",
                    unsafe_allow_html=True)

    # ===== BLOQUE 1: Perfil Básico =====
    st.markdown('<div style="background:linear-gradient(120deg,#EAF3FF 0%,#D6EBFF 100%);border-radius:20px;'
                'padding:18px 22px;margin-bottom:14px;border:1px solid #007AFF22;">'
                '<h4 style="margin:0 0 8px 0;color:#007AFF;">👤 Bloque 1 · Tu Perfil Básico</h4>'
                '<p style="margin:0;color:#3C6E9E;font-size:0.82rem;">Con tu peso, estatura, edad y género '
                'calculamos tu metabolismo (TMB) y detectamos tu etapa de vida — la base de todo tu plan.</p></div>',
                unsafe_allow_html=True)
    b1c1, b1c2 = st.columns(2)
    with b1c1:
        nombre_usuario = st.text_input("¿Cómo te llamas?", value=st.session_state.get("nombre_usuario", ""),
                                        key="nombre_usuario", help="Tu plan se sentirá hecho a tu medida.")
    with b1c2:
        genero = st.radio("Género:", ["Hombre", "Mujer"], horizontal=True, key="genero",
                           format_func=lambda g: ("♂ Hombre" if g == "Hombre" else "♀ Mujer"))
    _nombre_saludo = nombre_display(nombre_usuario, genero)
    if nombre_usuario.strip():
        st.success(f"¡Paz y bien, {_nombre_saludo}! 🌟")
    else:
        st.caption("✍️ Escribe tu nombre.")

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
        peso = st.number_input("Peso (kg):", min_value=20.0, max_value=min(300.0, peso_max_actual),
                                value=min(75.0, peso_max_actual), step=0.1, key="peso",
                                help="Rango válido: 20 a 300 kg.")
    with b1c4:
        estatura = st.number_input("Estatura (cm):", min_value=50, max_value=min(250, estatura_max_actual),
                                    value=min(168, estatura_max_actual), step=1, key="estatura",
                                    help="Rango válido: 50 a 250 cm.")
    with b1c5:
        edad = st.number_input("Edad (años):", min_value=1, max_value=min(120, edad_max_actual),
                                value=9, step=1, key="edad", help="Rango válido: 1 a 120 años.")
    etapa = etapa_desde_edad(edad)
    st.info(f"🔎 Etapa detectada automáticamente: **{etapa}**")

    # ===== BLOQUE 2: Estilo de Vida y Objetivos =====
    st.markdown('<div style="background:linear-gradient(120deg,#EAFAEE 0%,#D2F5DC 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #1E563122;">'
                '<h4 style="margin:0 0 8px 0;color:#1E5631;">🏃 Bloque 2 · Estilo de Vida y Objetivos</h4>'
                '<p style="margin:0;color:#3E7050;font-size:0.82rem;">Tu nivel de actividad y tu meta definen '
                'cuántas calorías gastas al día (RCD) y a qué ritmo ajustamos tu alimentación.</p></div>',
                unsafe_allow_html=True)
    st.caption("🏃 Nivel de Actividad Física (selecciona la que mejor describa tu día a día):")
    actividad = st.radio(
        "Actividad:", ["Sedentaria", "Ligero", "Moderada", "Intensa"],
        index=1, key="actividad", label_visibility="collapsed",
        format_func=lambda a: {
            "Sedentaria": "🪑 Sedentario o Poco Activo (Factor 1.2)",
            "Ligero": "🚶 Ligeramente Activo (Factor 1.375-1.55)",
            "Moderada": "🏃 Moderadamente Activo (Factor 1.55-1.75)",
            "Intensa": "🔥 Muy Activo / Intenso (Factor 1.8-2.1)",
        }[a],
    )
    _DESC_ACTIVIDAD = [
        ("Sedentaria", "🪑", "#8E8E93", "#F2F2F7", "Sedentario o Poco Activo (Factor 1.2)",
         "Días en 'modo reposo'. Pasas la mayor parte del día sentado (oficina, estudio, manejo) y tu "
         "movilidad fuera de estar sentado es mínima o nula."),
        ("Ligero", "🚶", "#34C759", "#EAFAEE", "Ligeramente Activo (Factor 1.375 - 1.55)",
         "Movimiento cotidiano acumulado. Trabajas sentado, pero caminas distancias razonables a diario, "
         "usas transporte público activo, haces compras a pie o labores del hogar de forma constante."),
        ("Moderada", "🏃", "#007AFF", "#EAF3FF", "Moderadamente Activo (Factor 1.55 - 1.75)",
         "Cuerpo en acción la mitad del día. Tienes un trabajo de pie o con desplazamiento constante "
         "(maestro, vendedor, salud) O tu trabajo es sentado pero realizas actividades físicas dinámicas "
         "de forma regular."),
        ("Intensa", "🔥", "#FF3B30", "#FFEDEC", "Muy Activo / Intenso (Factor 1.8 - 2.1)",
         "Alto esfuerzo físico diario. Entrenamientos intensos diarios o trabajos de alta exigencia física "
         "(construcción, agricultura, atletas)."),
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

    objetivo = st.selectbox("🎯 ¿Cuál es tu objetivo principal?", ["Bajar de peso", "Subir de peso", "Mantenerse"],
                             key="objetivo")

    st.caption("⚙️ Ajuste del Ritmo (Velocidad del proceso):")
    if objetivo == "Bajar de peso":
        ajuste_txt = st.selectbox("Ajuste del Ritmo:", label_visibility="collapsed",
            options=["Gradual (-10%)", "Equilibrado (-20%) ⭐ Recomendado", "Intensivo (-30%)"], index=1, key="ajuste_bajar_sel")
    elif objetivo == "Subir de peso":
        ajuste_txt = st.selectbox("Ajuste del Ritmo:", label_visibility="collapsed",
            options=["Gradual (+10%)", "Equilibrado (+15%) ⭐ Recomendado", "Acelerado (+20%)"], index=1, key="ajuste_subir_sel")
    else:
        ajuste_txt = None
        st.caption("Sin ajuste calórico: se mantiene tu RCD.")

    if objetivo in ("Bajar de peso", "Subir de peso"):
        _DESC_AJUSTE = {
            "Bajar de peso": [
                ("Gradual (-10%)", "🌱", "#34C759", "#EAFAEE",
                 "Ideal para quienes están cerca de su peso objetivo o prefieren cambios lentos y sostenibles."),
                ("Equilibrado (-20%) ⭐ Recomendado", "⚡", "#007AFF", "#EAF3FF",
                 "La opción ideal para la mayoría. Permite una pérdida de peso constante manteniendo hábitos saludables."),
                ("Intensivo (-30%)", "🚀", "#FF3B30", "#FFEDEC",
                 "Produce cambios más rápidos. Se recomienda principalmente en personas con obesidad o por "
                 "periodos cortos y con seguimiento."),
            ],
            "Subir de peso": [
                ("Gradual (+10%)", "🌱", "#34C759", "#EAFAEE",
                 "Aumenta las calorías de forma moderada para favorecer una ganancia progresiva."),
                ("Equilibrado (+15%) ⭐ Recomendado", "⚡", "#007AFF", "#EAF3FF",
                 "La opción ideal para la mayoría. Favorece una ganancia constante con menor acumulación de grasa."),
                ("Acelerado (+20%)", "🚀", "#FF3B30", "#FFEDEC",
                 "Pensado para personas con metabolismo muy rápido o que necesitan aumentar peso rápidamente. "
                 "Requiere una alimentación bien planificada."),
            ],
        }[objetivo]
        for _tit_a, _ic_a, _col_a, _fon_a, _desc_a in _DESC_AJUSTE:
            _sel_a = (_tit_a == ajuste_txt)
            _estilo_a = (f"border:2.5px solid {_col_a};box-shadow:0 8px 20px {_col_a}40;transform:translateX(4px);"
                         if _sel_a else "border:1px solid rgba(0,0,0,0.06);")
            st.markdown(f"""
            <div style="background:{_fon_a};border-radius:16px;padding:12px 18px;margin-bottom:8px;{_estilo_a}
                        transition:all 0.2s ease;display:flex;gap:12px;align-items:flex-start;">
                <div style="font-size:1.4rem;">{_ic_a}</div>
                <div><b style="color:{_col_a};">{_tit_a}</b>{' ✓' if _sel_a else ''}<br>
                <span style="font-size:0.84rem;color:#3C3C43;">{_desc_a}</span></div>
            </div>
            """, unsafe_allow_html=True)
        if (objetivo == "Bajar de peso" and ajuste_txt == "Intensivo (-30%)") or \
           (objetivo == "Subir de peso" and ajuste_txt == "Acelerado (+20%)"):
            st.warning("🟨 Este ritmo produce cambios más rápidos: úsalo solo bajo seguimiento o en casos específicos.")

    st.caption("ℹ️ **¿Qué significa este ajuste?** Define qué tan rápido deseas alcanzar tu objetivo, adaptando "
               "tus calorías diarias a partir de tu Requerimiento Calórico Diario (RCD). ⚡ El ritmo Equilibrado "
               "suele ser la opción recomendada, ya que combina buenos resultados con una mejor adherencia a largo plazo.")

    # ===== BLOQUE 3: Monitoreo de Signos Vitales =====
    st.markdown('<div style="background:linear-gradient(120deg,#FFEBEE 0%,#FFD9DE 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #C0392B22;">'
                '<h4 style="margin:0 0 8px 0;color:#C0392B;">💓 Bloque 3 · Monitoreo de Signos Vitales</h4>'
                '<p style="margin:0;color:#8A5252;font-size:0.82rem;">Estos indicadores muestran cómo está '
                'funcionando tu cuerpo en este momento, y ayudan a detectar señales de alerta a tiempo.</p></div>',
                unsafe_allow_html=True)
    spo2 = st.number_input("Oxigenación SpO2 (%):", min_value=0.0, max_value=100.0, value=0.0, step=1.0,
                            key="spo2", help="Normal: 95% a 100%.")
    if spo2 > 0:
        _c = "verde" if spo2 >= 95 else ("rojo" if spo2 < 90 else "ambar")
        _badge_vital(spo2, "%", _c, "Normal" if _c == "verde" else ("Bajo" if _c == "rojo" else "Atención"))

    pulso = st.number_input("Pulso (lpm):", min_value=0, max_value=220, value=0, step=1,
                             key="pulso", help="Ideal en reposo: 60 a 100 lpm.")
    if pulso > 0:
        _c = "verde" if 60 <= pulso <= 100 else "ambar"
        _badge_vital(pulso, " lpm", _c, "Normal" if _c == "verde" else "Atención")

    temp_corp = st.number_input("Temperatura (°C):", min_value=34.0, max_value=42.0, value=34.0, step=0.1,
                                 key="temp_corp", help="Normal: 36.5°C a 37.5°C.")
    if temp_corp > 34.0:
        _c = "verde" if 36.5 <= temp_corp <= 37.5 else "ambar"
        _badge_vital(temp_corp, "°C", _c, "Normal" if _c == "verde" else "Atención")

    st.markdown("**Presión Arterial (mmHg):**")
    pas = st.number_input("Sistólica:", min_value=0, max_value=250, value=0, step=1, key="pas")
    pad = st.number_input("Diastólica:", min_value=0, max_value=150, value=0, step=1, key="pad")
    if pas > 0 and pad > 0:
        if pas < 50 or pas > 300 or pad < 30 or pad > 200:
            st.markdown('<p style="color:#C0392B;font-weight:700;font-size:0.78rem;">'
                         '⚠️ Valor fuera de rango clínico. Por favor verifica tus datos</p>', unsafe_allow_html=True)
        else:
            _c = "verde" if (90 <= pas <= 119 and 60 <= pad <= 79) else "ambar"
            _badge_vital(f"{pas}/{pad}", "", _c, "Normal" if _c == "verde" else "Atención")

    # ===== BLOQUE 4: Perfil Bioquímico (Análisis Sanguíneo) =====
    st.markdown('<div style="background:linear-gradient(120deg,#F3E5F5 0%,#E6CCEB 100%);border-radius:20px;'
                'padding:18px 22px;margin:18px 0 14px 0;border:1px solid #7B1FA222;">'
                '<h4 style="margin:0 0 8px 0;color:#7B1FA2;">🩸 Bloque 4 · Perfil Bioquímico (Análisis Sanguíneo)</h4>'
                '<p style="margin:0;color:#8E5FA3;font-size:0.82rem;">Con tus valores de sangre identificamos '
                'riesgos como anemia, colesterol alto o glucosa elevada, para darte recomendaciones más precisas.</p></div>',
                unsafe_allow_html=True)
    hemo = st.number_input("Hemoglobina (g/dL):", min_value=0.0, max_value=HEMO_MAX, value=0.0, step=0.1,
                            key="hemo", help="Normal: 12-17 g/dL, varía por género.")
    gluco = st.number_input("Glucosa (mg/dL):", min_value=0.0, max_value=GLUCO_MAX, value=0.0, step=1.0,
                             key="gluco", help="Normal en ayunas: 70-100 mg/dL.")
    coles = st.number_input("Colesterol (mg/dL):", min_value=0.0, max_value=COLES_MAX, value=0.0, step=1.0,
                             key="coles", help="Ideal: menor a 200 mg/dL.")
    trigli = st.number_input("Triglicéridos (mg/dL):", min_value=0.0, max_value=TRIGLI_MAX, value=0.0, step=1.0,
                              key="trigli", help="Ideal: menor a 150 mg/dL.")
    hierro = st.number_input("Hierro Sérico (µg/dL):", min_value=0.0, max_value=HIERRO_MAX, value=0.0, step=1.0,
                              key="hierro", help="Normal: 60-170 µg/dL.")

# ---- Sidebar: navegación tipo píldoras verticales coloridas, con las 16 secciones siempre visibles ----
st.sidebar.markdown(
    '<div class="sidebar-nav-title">🧭 Navegación · 17 secciones</div>',
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
    "10.-CLIMA CHICLAYO":          ("#FFB300", "#FFF6E0"),
    "11.-APORTE 1: EMBARAZO":      ("#BF5AF2", "#F7ECFD"),
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
    _icono_nav, _titulo_nav = ETIQUETAS_NAV[_hoja_nav]
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

if objetivo == "Bajar de peso":
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

if genero == "Hombre":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161

factor = FACTOR_ACTIVIDAD[actividad][genero]
rcd = tmb * factor  # Hoja 4: RCD = TMB x Factor de actividad

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
# CONTENIDO PRINCIPAL — la navegación vive en el sidebar (pills verticales); aquí solo se
# pinta la sección actualmente seleccionada.
# =========================================================================================
hoja_activa = st.session_state["hoja_activa"]
_icono_actual, _titulo_actual = ETIQUETAS_NAV[hoja_activa]
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
                file_name=_ruta_excel.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
    else:
        st.info("Para habilitar este botón, coloca el archivo del Excel (por ejemplo "
                "`Proyecto_sana_alimentacion_-_Grupo_n_04_CIAM_SUNI.xlsx`) en la misma carpeta que este script "
                "`app.py` antes de ejecutarlo.")

    st.divider()

    st.markdown("""
    <div style="position:relative;overflow:hidden;background:linear-gradient(120deg,#007AFF 0%,#5AC8FA 45%,#34C759 100%);
                border-radius:28px;padding:30px 34px;color:#FFFFFF;margin-bottom:18px;
                box-shadow:0 18px 40px rgba(0,122,255,0.28);">
        <div style="position:absolute;right:20px;top:50%;transform:translateY(-50%);font-size:5.5rem;opacity:0.18;">📝✨</div>
        <div style="font-size:0.8rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.92;">Paso 1 de tu plan</div>
        <h1 style="margin:6px 0 6px 0;font-weight:900;letter-spacing:-0.02em;">📝 ¡Introduce tus datos!</h1>
        <p style="margin:0;font-size:1rem;opacity:0.96;max-width:600px;">El punto de partida: llena el formulario "📝 Llenar / Editar Mis Datos" en el panel lateral izquierdo (sidebar) — se mantiene visible en todas las hojas. Aquí abajo verás un resumen de lo que ya registraste. 🌈</p>
    </div>
    """, unsafe_allow_html=True)

    col_priv, col_escudo = st.columns([3, 1])
    with col_priv:
        st.markdown("""
        <div style="background:#EAF3FF;border-left:5px solid #007AFF;border-radius:16px;padding:12px 20px;height:100%;">
        🔒 <b style="color:#007AFF;">Tus datos son privados:</b> solo se usan mientras tienes esta página abierta y no se guardan en ningún servidor.
        </div>
        """, unsafe_allow_html=True)
    with col_escudo:
        if _ESCUDO.exists():
            st.image(str(_ESCUDO), width=90)


    st.divider()
    st.markdown("#### 📋 Resumen de tus datos ingresados")

    col_datos, col_sticker = st.columns([2, 1])
    with col_datos:
        _tablas_resumen = [
            (0, "👤 Bloque 1 · Perfil Básico", [
                ("Nombre", _nombre_saludo), ("Género", genero), ("Peso", f"{peso:.2f} kg"),
                ("Estatura", f"{estatura} cm ({estatura_m:.2f} m)"), ("Edad", f"{edad} años"),
                ("Etapa detectada", etapa),
            ]),
            (4, "🏃 Bloque 2 · Estilo de Vida y Objetivos", [
                ("Actividad física", actividad), ("Objetivo", objetivo),
                ("Ajuste (bajar)", f"{ajuste_bajar*100:.0f}%"), ("Ajuste (subir)", f"{ajuste_subir*100:.0f}%"),
            ]),
            (1, "💓 Bloque 3 · Signos Vitales", [
                ("SpO2", f"{spo2:.2f}%" if spo2 > 0 else "Sin dato"),
                ("Pulso", f"{pulso} lpm" if pulso > 0 else "Sin dato"),
                ("Temperatura", f"{temp_corp:.2f}°C" if temp_corp > 34.0 else "Sin dato"),
                ("Presión arterial", f"{pas}/{pad} mmHg" if pas > 0 and pad > 0 else "Sin dato"),
            ]),
            (1, "🩸 Bloque 4 · Perfil Bioquímico", [
                ("Hemoglobina", f"{hemo:.2f} g/dL" if hemo > 0 else "Sin dato"),
                ("Glucosa", f"{gluco:.2f} mg/dL" if gluco > 0 else "Sin dato"),
                ("Colesterol", f"{coles:.2f} mg/dL" if coles > 0 else "Sin dato"),
                ("Triglicéridos", f"{trigli:.2f} mg/dL" if trigli > 0 else "Sin dato"),
                ("Hierro", f"{hierro:.2f} µg/dL" if hierro > 0 else "Sin dato"),
            ]),
        ]
        for _idx_col, _titulo_tabla, _filas_tabla in _tablas_resumen:
            caja_titulo(_titulo_tabla, _idx_col)
            tabla_bonita(pd.DataFrame({"Variable": [f[0] for f in _filas_tabla],
                                        "Valor": [f[1] for f in _filas_tabla]}), _idx_col)
    with col_sticker:
        st.caption(f"¡Bienvenid@, {_nombre_saludo}! 👋")

    st.divider()
    caja_util(f"¡Paz y bien, {_nombre_saludo}! Aquí registras tus datos básicos una sola vez, y toda la app se ajusta "
              "automáticamente a ti: desde tus calorías diarias hasta tu plan de comidas. La etapa de vida se "
              "detecta sola apenas escribes tu edad. ¡Es el punto de partida de todo tu plan personalizado! 🌟",
              emoji="📝", color="#E3F2FD", borde="#2196F3")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "1.-ANÁLISIS SANGUÍNEO":
    hoja_header(1, "No solo mostramos tus números: te explicamos qué significan, por qué ocurren y qué podrías hacer.")

    _cat_hemo = clasif_hemoglobina(hemo, etapa, genero)
    _cat_trigli = clasif_trigliceridos(trigli)
    _cat_gluco = clasif_glucosa(gluco)
    _cat_coles = clasif_colesterol(coles)
    _cat_hierro = clasif_hierro(hierro, etapa, genero)

    st.markdown("#### 🚦 Semáforo Clínico — protocolo de triaje digital")
    st.caption(f"No solo diagnostica: te sugiere una ruta de mejora inmediata, {_nombre_saludo}. 🟢 Normal · 🟡 Alerta · 🔴 Crítico")
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
            "que_mide": "Proteína de los glóbulos rojos que transporta el oxígeno desde los pulmones hacia todo el cuerpo.",
            "recomendaciones": [("🥩", "Alimentos ricos en hierro"), ("🍊", "Vitamina C (mejora la absorción)"), ("🩺", "Evaluación médica si hay síntomas")],
            "riesgo": ["🍖 Baja ingesta de hierro", "🤰 Embarazo", "🩸 Sangrados", "🫘 Déficit nutricional"],
            "curioso": "La hemoglobina puede disminuir durante el embarazo debido al aumento del volumen sanguíneo.",
        },
        "Triglicéridos": {
            "icono": "🫒", "unidad": " mg/dL", "valor": trigli, "categoria": _cat_trigli,
            "que_mide": "Tipo de grasa en la sangre que el cuerpo usa como reserva de energía.",
            "recomendaciones": [("🥑", "Priorizar grasas saludables"), ("🚶", "Actividad física regular"), ("🍬", "Reducir azúcares simples")],
            "riesgo": ["🍩 Exceso de azúcares", "🍺 Consumo de alcohol", "⚖️ Sobrepeso", "🧬 Factores genéticos"],
            "curioso": "Los triglicéridos suben temporalmente después de comer; por eso muchas pruebas piden ayuno.",
        },
        "Glucosa": {
            "icono": "🍬", "unidad": " mg/dL", "valor": gluco, "categoria": _cat_gluco,
            "que_mide": "Nivel de azúcar disponible en la sangre, la principal fuente de energía del cuerpo.",
            "recomendaciones": [("🥗", "Más fibra, menos azúcar simple"), ("🚶", "Actividad física"), ("⏰", "Horarios de comida regulares")],
            "riesgo": ["🍭 Dieta alta en azúcares", "⚖️ Sobrepeso", "🧬 Antecedentes familiares", "😴 Mal descanso"],
            "curioso": "La glucosa aumenta naturalmente después de comer; por eso muchas pruebas se hacen en ayunas.",
        },
        "Colesterol": {
            "icono": "🫀", "unidad": " mg/dL", "valor": coles, "categoria": _cat_coles,
            "que_mide": "Grasa esencial para producir hormonas y formar membranas celulares, en exceso puede obstruir arterias.",
            "recomendaciones": [("🥑", "Priorizar grasas saludables"), ("🚶", "Actividad física"), ("🥗", "Más fibra"), ("🚭", "Evitar tabaco")],
            "riesgo": ["🍟 Grasas saturadas/trans", "🚬 Tabaco", "🧬 Factores genéticos", "⚖️ Sobrepeso"],
            "curioso": "El colesterol no siempre es perjudicial: el organismo lo necesita para producir hormonas.",
        },
        "Hierro": {
            "icono": "⚙️", "unidad": " µg/dL", "valor": hierro, "categoria": _cat_hierro,
            "que_mide": "Mineral esencial para fabricar hemoglobina y transportar oxígeno en el cuerpo.",
            "recomendaciones": [("🥩", "Carnes rojas y legumbres"), ("🍊", "Vitamina C junto a las comidas"), ("☕", "Evitar café/té con las comidas")],
            "riesgo": ["🍖 Baja ingesta de hierro", "🩸 Pérdidas de sangre", "🤰 Embarazo", "🫘 Mala absorción intestinal"],
            "curioso": "El té y el café pueden reducir la absorción de hierro si se toman junto a las comidas.",
        },
    }
    st.markdown("#### 🔎 ¿Qué significa cada resultado?")
    for _param, _info in _INFO_PARAM.items():
        _r = evaluar_estado_clinico(_param, _info["categoria"])
        with st.expander(f"{_info['icono']} {_param} — {_info['valor']}{_info['unidad']} · {_r['emoji']} {_info['categoria']}"):
            st.markdown(f"**🧠 ¿Qué mide?** {_info['que_mide']}")
            st.markdown(f"**📋 ¿Qué significa tu resultado?** {_r['mensajePersonalizado']}")
            _reco_html = " &nbsp; ".join(f"{ic} {tx}" for ic, tx in _info["recomendaciones"])
            st.markdown(f"**✅ Recomendaciones generales (educativas, no médicas):** {_reco_html}")
            if _r["colorSemaforo"] in ("ambar", "rojo"):
                st.markdown(f"**⚠️ Posibles factores relacionados** (no constituye diagnóstico): "
                            + " &nbsp; ".join(_info["riesgo"]))
            st.markdown(f"**💡 ¿Sabías qué?** {_info['curioso']}")

    st.divider()

    # ===== 2. Interpretación Clínica Inteligente (reemplaza el panel de flujo anterior) =====
    st.markdown("#### 🧠 Interpretación Clínica Inteligente")
    _todos = [("Hemoglobina", _cat_hemo), ("Triglicéridos", _cat_trigli), ("Glucosa", _cat_gluco),
              ("Colesterol", _cat_coles), ("Hierro", _cat_hierro)]
    _con_dato = [(p, c) for p, c in _todos if c != "Introducir datos"]
    _verdes = [p for p, c in _con_dato if CATEGORIA_SEMAFORO.get(c, "gris") == "verde"]
    _no_verdes = [(p, c) for p, c in _con_dato if CATEGORIA_SEMAFORO.get(c, "gris") in ("ambar", "rojo")]
    _pct_salud = round((len(_verdes) / len(_con_dato)) * 100) if _con_dato else 0

    if _con_dato:
        icol1, icol2 = st.columns(2)
        with icol1:
            st.success(f"🟢 {len(_verdes)} parámetro(s) normal(es)")
            if _no_verdes:
                st.warning(f"🟡 {len(_no_verdes)} parámetro(s) requiere(n) seguimiento")
            st.markdown("**✔ Fortalezas**")
            st.markdown("\n".join(f"- ✔ {p} adecuada" for p in _verdes) or "- Aún sin fortalezas identificadas.")
        with icol2:
            st.markdown("**⚠ Aspectos a mejorar**")
            if _no_verdes:
                for p, c in _no_verdes:
                    _reco_corta = _INFO_PARAM[p]["recomendaciones"][0]
                    st.markdown(f"- ⚠ {p} ({c}) — sugerencia: {_reco_corta[0]} {_reco_corta[1]}")
            else:
                st.markdown("- Sin aspectos pendientes por ahora. 🎉")
        st.markdown(f"**Nivel general · Salud metabólica: {_pct_salud}%**")
        st.progress(_pct_salud / 100)
    else:
        st.info("Ingresa al menos un valor en la hoja 'Mis Datos' (Bloque 4) para ver tu interpretación clínica.")

    # ===== Mini motor de reglas (no es IA real, solo asociaciones simples) =====
    _insights = []
    if _cat_hemo in ("Anemia leve", "Anemia moderada", "Anemia grave") and _cat_hierro == "Bajo":
        _insights.append("Existe una posible asociación entre tu hemoglobina baja y tu hierro bajo: podría sugerir "
                          "una deficiencia de hierro. Se recomienda acudir al profesional de salud para una valoración clínica.")
    if _cat_gluco in ("Prediabetes", "Diabetes") and _cat_coles in ("Límite alto", "Alto"):
        _insights.append("Tu glucosa y tu colesterol elevados en conjunto suelen asociarse a un mayor riesgo metabólico. "
                          "Se recomienda una valoración médica integral.")
    if _cat_trigli in ("Alto", "Muy alto") and _cat_coles in ("Límite alto", "Alto"):
        _insights.append("Triglicéridos y colesterol elevados juntos pueden asociarse a mayor riesgo cardiovascular. "
                          "Se recomienda consultar a un profesional de salud.")
    if _insights:
        st.markdown("#### 🧠 Posibles asociaciones entre tus resultados")
        for _ins in _insights:
            st.info(f"🧠 {_ins}")

    st.divider()

    st.markdown("#### 🎯 ¿Cómo impacta esto en tu día a día? (Análisis Sanguíneo)")
    ambito_seleccionado = st.selectbox(
        "Elige el ámbito en el que quieres ver reflejado el impacto de tus resultados:",
        ["Escolar/Académico", "Laboral", "Psicológico/Emocional"], key="ambito_sangre"
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
        <b style="color:{_hex_pt};">{_parametro}</b> <span style="color:#1C1C1E;">({_categoria})</span> — <span style="color:#1C1C1E;">{_texto_impacto}</span>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 Ver tablas de referencia clínica completas"):
        panel_referencia_hemo_hierro()
        panel_referencia_trigli_gluco_coles()
    recursos_externos(1, [
        ("🩸 Anemia (MedlinePlus)", "https://medlineplus.gov/spanish/anemia.html"),
        ("🫀 Colesterol (MedlinePlus)", "https://medlineplus.gov/spanish/cholesterol.html"),
        ("💉 Diabetes (OMS)", "https://www.who.int/es/news-room/fact-sheets/detail/diabetes"),
    ])

    st.markdown("""
    <div style="background:#F5F5F7;border-radius:16px;padding:12px 18px;margin-top:14px;font-size:0.8rem;color:#5C6B60;">
    📚 <b>Fuentes consultadas:</b> Organización Mundial de la Salud (OMS) · American Diabetes Association ·
    MedlinePlus · Mayo Clinic · Ministerio de Salud del Perú (MINSA).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:16px;padding:12px 18px;margin-top:10px;font-size:0.82rem;color:#7A4A00;">
    ⚠️ <b>Información importante:</b> esta plataforma tiene fines educativos y de apoyo para la comprensión de
    resultados clínicos. No reemplaza el diagnóstico, tratamiento ni la valoración realizada por un médico o nutricionista.
    </div>
    """, unsafe_allow_html=True)

    caja_util("Un análisis de sangre trae puros números y siglas difíciles de entender (¿12.5 g/dL es bueno o malo?). "
              "Esta hoja traduce esos números a un lenguaje simple: 'Normal', 'Anemia leve', 'Alto', etc., y te explica "
              "qué significan, por qué ocurren y qué podrías hacer. Así sabes de un vistazo si algún valor necesita "
              "atención médica. 🩺❤️",
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
    <p style="margin:0 0 4px 0;font-weight:900;color:#C0392B;font-size:1.85rem;letter-spacing:-0.02em;">❤️ Estado Fisiológico</p>
    <p style="margin:0 0 8px 0;color:#5C2A26;font-weight:700;font-size:0.98rem;">Así está funcionando tu cuerpo en este momento</p>
    <p style="margin:0;color:#7A4A44;font-size:0.88rem;line-height:1.5;">No solo mostramos tus signos vitales: te explicamos qué significan, qué pueden indicar y cuándo
    conviene prestarles atención.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- 3.2 Semáforo fisiológico — dashboard de 4 tarjetas -------------------------------
    st.markdown("##### 🚦 Una vista rápida del estado general de tus signos vitales")
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
            <p style="margin:6px 0 2px 0;color:#5C6B60;font-size:0.76rem;font-weight:700;text-transform:uppercase;">{_tt}</p>
            <p style="margin:0 0 6px 0;font-weight:800;font-size:1.15rem;color:#17301F;">{_val}</p>
            <span style="background:{_st['fondo']};color:{_st['hex']};padding:4px 12px;border-radius:999px;
            font-size:0.74rem;font-weight:800;">{_st['emoji']} {_cat}</span>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # --- 3.3 Detalle: ¿Qué significa cada resultado? (4 sub-tarjetas por signo vital) -----
    st.markdown("##### 🔎 ¿Qué significa cada resultado?")
    _PASTEL_CARD = {
        "mide":  {"fondo": "#EAF4FE", "borde": "#8FC1F2", "titulo": "#1565C0"},
        "signif":{"fondo": "#F3EEFB", "borde": "#C6AEE8", "titulo": "#6A3FA0"},
        "reco":  {"fondo": "#EAFAEE", "borde": "#9BD8AE", "titulo": "#1E5631"},
        "curio": {"fondo": "#FFF6E0", "borde": "#F4D27A", "titulo": "#B8860B"},
    }
    _INFO_VITAL = {
        "Presión Arterial": {
            "icono": "❤️", "valor": f"{pas}/{pad} mmHg" if pas > 0 and pad > 0 else "—", "categoria": _cat_pa, "color": _col_pa,
            "que_mide": "Mide la fuerza con la que el corazón bombea sangre a través de las arterias hacia el resto del cuerpo.",
            "sin_dato": "Aún no ingresaste tu presión arterial. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
            "recomendaciones": [("🥗", "Menos sal, más frutas y verduras"), ("💧", "Buena hidratación"), ("🩺", "Consulta si persiste alta")],
            "curioso": "La postura, el estrés y hasta hablar durante la medición pueden alterar el resultado hasta en 10 mmHg.",
        },
        "Oxigenación (SpO₂)": {
            "icono": "🫁", "valor": f"{spo2:.0f} %" if spo2 > 0 else "—", "categoria": _cat_ox, "color": _col_ox,
            "que_mide": "Indica el porcentaje de oxígeno que transporta tu sangre hacia órganos y músculos.",
            "sin_dato": "Aún no ingresaste tu oxigenación. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
            "recomendaciones": [("🫁", "Respiración profunda"), ("🚭", "Evitar el humo/tabaco"), ("🩺", "Consulta si baja de 95%")],
            "curioso": "La altura geográfica reduce naturalmente el SpO₂; a mayor altitud, el aire tiene menos oxígeno disponible.",
        },
        "Temperatura": {
            "icono": "🌡️", "valor": f"{temp_corp:.1f} °C" if temp_corp > 34.0 else "—", "categoria": _cat_te, "color": _col_te,
            "que_mide": "Refleja qué tan bien tu organismo regula el calor interno para mantener sus funciones vitales.",
            "sin_dato": "Aún no ingresaste tu temperatura. Ve a 'Mis Datos' → Bloque 3 para registrarla.",
            "recomendaciones": [("💧", "Hidratación constante"), ("🛌", "Reposo si hay fiebre"), ("🩺", "Consulta si persiste alta")],
            "curioso": "El ejercicio intenso, la ropa abrigada o el ambiente caluroso pueden subir tu temperatura sin que estés enferma/o.",
        },
        "Pulso": {
            "icono": "💓", "valor": f"{pulso} lpm" if pulso > 0 else "—", "categoria": _cat_pu, "color": _col_pu,
            "que_mide": "Cuenta cuántas veces late tu corazón en un minuto mientras estás en reposo.",
            "sin_dato": "Aún no ingresaste tu pulso. Ve a 'Mis Datos' → Bloque 3 para registrarlo.",
            "recomendaciones": [("🚶", "Actividad física regular"), ("☕", "Moderar la cafeína"), ("🩺", "Consulta si es muy alto/bajo")],
            "curioso": "La cafeína, las emociones fuertes y la fiebre pueden acelerar tu pulso incluso en reposo.",
        },
    }
    for _param, _info in _INFO_VITAL.items():
        _st = SEMAFORO_ESTILO[_info["color"]]
        st.markdown(f"""
        <div style="background:#FFFFFF;border-radius:22px;padding:16px 18px 20px 18px;margin-bottom:14px;
        border:1px solid rgba(0,0,0,0.06);box-shadow:0 4px 14px rgba(0,0,0,0.05);">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
        <span style="font-size:1.3rem;">{_info['icono']}</span>
        <b style="font-size:1.02rem;color:#17301F;">{_param}</b>
        <span style="margin-left:auto;background:{_st['fondo']};color:{_st['hex']};padding:4px 12px;
        border-radius:999px;font-size:0.76rem;font-weight:800;">{_st['emoji']} {_info['valor']} · {_info['categoria']}</span>
        </div>
        """, unsafe_allow_html=True)

        _significado_txt = _info["sin_dato"] if _info["color"] == "gris" else \
            f"Con tu resultado de <b>{_info['valor']}</b>, tu estado se clasifica como <b>{_info['categoria']}</b> {_st['emoji']}."
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
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['mide']['titulo']};font-size:0.84rem;">🧠 ¿Qué mide?</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_info['que_mide']}</p>
            </div>""", unsafe_allow_html=True)
        with _c2:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['signif']['fondo']};border:1px solid {_PASTEL_CARD['signif']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['signif']['titulo']};font-size:0.84rem;">📋 ¿Qué significa tu resultado?</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_significado_txt}</p>
            </div>""", unsafe_allow_html=True)
        with _c3:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['reco']['fondo']};border:1px solid {_PASTEL_CARD['reco']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;overflow:hidden;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['reco']['titulo']};font-size:0.84rem;">✅ Recomendaciones generales</p>
            <div style="line-height:1.9;">{_reco_chips_html}</div>
            </div>""", unsafe_allow_html=True)
        with _c4:
            st.markdown(f"""
            <div style="background:{_PASTEL_CARD['curio']['fondo']};border:1px solid {_PASTEL_CARD['curio']['borde']};
            border-radius:18px;padding:14px 14px;height:170px;">
            <p style="margin:0 0 6px 0;font-weight:800;color:{_PASTEL_CARD['curio']['titulo']};font-size:0.84rem;">💡 ¿Sabías qué?</p>
            <p style="margin:0;font-size:0.8rem;color:#2E2E33;line-height:1.4;">{_info['curioso']}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

    st.write("")

    # --- 3.4 Interpretación Fisiológica Inteligente ---------------------------------------
    st.markdown("##### 🧠 Interpretación Fisiológica Inteligente")
    _todos_vitales = [("Presión Arterial", _col_pa), ("Oxigenación (SpO₂)", _col_ox),
                       ("Temperatura", _col_te), ("Pulso", _col_pu)]
    _con_dato_v = [(p, c) for p, c in _todos_vitales if c != "gris"]
    _rojos_v = [p for p, c in _con_dato_v if c == "rojo"]
    _ambar_v = [p for p, c in _con_dato_v if c == "ambar"]

    if not _con_dato_v:
        st.info("Ingresa tus signos vitales en 'Mis Datos' → Bloque 3 para ver tu interpretación fisiológica.")
    elif _rojos_v:
        _lista_r = ", ".join(_rojos_v)
        st.markdown(f"""
        <div style="background:#FBEAE8;border-radius:20px;padding:18px 24px;border-left:5px solid #C0392B;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#C0392B;">🔴 Atención Requerida</p>
        <p style="margin:0;color:#7A2E27;font-size:0.9rem;line-height:1.5;">
        Se detectó un valor fuera de rango en: <b>{_lista_r}</b>. Puede deberse a distintos factores fisiológicos
        o a una lectura incorrecta del sensor. <i>Recomendación:</i> si la medición persiste o sientes malestar,
        consulta con un profesional de salud.</p>
        </div>
        """, unsafe_allow_html=True)
    elif _ambar_v:
        _lista_a = ", ".join(_ambar_v)
        st.markdown(f"""
        <div style="background:#FDF1E4;border-radius:20px;padding:18px 24px;border-left:5px solid #E67E22;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#E67E22;">🟡 Atención Ligera</p>
        <p style="margin:0;color:#7A5A26;font-size:0.9rem;line-height:1.5;">
        <b>{_lista_a}</b> se encuentra ligeramente fuera del rango habitual. No suele ser motivo de alarma,
        pero conviene observar cómo evoluciona.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#EAFAEE;border-radius:20px;padding:18px 24px;border-left:5px solid #1E5631;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#1E5631;">🟢 Estado General</p>
        <p style="margin:0 0 8px 0;color:#17301F;font-size:0.9rem;">
        {" &nbsp;·&nbsp; ".join(f"{SEMAFORO_ESTILO[c]['emoji']} {p}" for p, c in _con_dato_v)}</p>
        <p style="margin:0;color:#17301F;font-size:0.88rem;"><b>Resultado general:</b> tus signos vitales se
        encuentran dentro de los rangos esperados para una persona en reposo.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # --- 3.5 Impacto en la vida diaria — segmented control --------------------------------
    st.markdown("##### 🎯 Impacto en la vida diaria (Signos Vitales)")
    _IMPACTO_VITAL = {
        "🏫 Colegio": {
            "Presión Arterial": "Puede causar dolor de cabeza, somnolencia o falta de concentración en clase.",
            "Oxigenación (SpO₂)": "Causa fatiga rápida al subir escaleras o caminar; menor resistencia en educación física.",
            "Temperatura": "Rendimiento académico y cognitivo reducido; es recomendable no asistir y descansar.",
            "Pulso": "Sensación de agitación; evita esfuerzos físicos intensos y mantén una buena hidratación.",
        },
        "🏠 Casa": {
            "Presión Arterial": "Puede generar cansancio o mareos al hacer tareas domésticas exigentes.",
            "Oxigenación (SpO₂)": "Sensación de falta de aire al subir escaleras o realizar quehaceres.",
            "Temperatura": "Conviene guardar reposo, hidratarte bien y evitar esfuerzos en casa.",
            "Pulso": "Puede sentirse como palpitaciones; prioriza el descanso y evita sustos o sobresaltos.",
        },
        "🏃 Actividad Física": {
            "Presión Arterial": "Conviene evitar ejercicio intenso hasta que el valor se normalice.",
            "Oxigenación (SpO₂)": "El rendimiento físico baja notablemente; reduce la intensidad del entrenamiento.",
            "Temperatura": "No se recomienda hacer deporte con fiebre; el cuerpo ya está en sobreesfuerzo.",
            "Pulso": "Un pulso elevado en reposo indica que conviene posponer el ejercicio intenso.",
        },
        "💼 Trabajo": {
            "Presión Arterial": "Puede afectar la concentración en tareas que requieren atención sostenida.",
            "Oxigenación (SpO₂)": "Mayor cansancio en jornadas largas o con esfuerzo físico.",
            "Temperatura": "Es preferible descansar en casa en vez de asistir a trabajar.",
            "Pulso": "Evita situaciones de alta presión o estrés hasta que el ritmo se normalice.",
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
                <b style="color:{_st['hex']};">{_param}</b> — <span style="color:#1C1C1E;font-size:0.88rem;">
                {_IMPACTO_VITAL[_ambito_v][_param]}</span>
                </div>
                """, unsafe_allow_html=True)

    st.write("")

    # --- 3.6 Tablas de referencia clínica — filas con highlight dinámico (Bento Grid) ------
    st.markdown("##### 📊 Tablas de Referencia Clínica")
    st.caption("Rangos clínicos oficiales. La fila que corresponde a tu valor actual se enciende con un glow.")

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
            _badge = '<span class="badge-activo">📍 TU VALOR ACTUAL</span>'
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
    _render_tabla_html("❤️", "Presión Arterial", "Fuente: American Heart Association (AHA)",
                        ["Categoría", "Sistólica (mmHg)", "Condición", "Diastólica (mmHg)"], _pa_html)
    if _pa_rango_invalido:
        st.markdown('<p style="color:#C0392B;font-weight:800;font-size:0.85rem;margin-top:-8px;">'
                     '⚠️ Valor fuera de rango clínico. Por favor verifica tus datos</p>', unsafe_allow_html=True)

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
    _render_tabla_html("🫁", "Saturación de Oxígeno (SpO₂)", "Fuente: Organización Mundial de la Salud (OMS)",
                        ["Rango de SpO₂", "Estado Clínico", "Manifestación Fisiológica"], _ox_html)

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
        (["Bebés (0–2 años)", "Rectal / Axilar", "36.6 – 38.0 °C", "≥ 38.0 °C", "&gt; 39.0 °C"], "verde"),
        (["Niños (3–10 años)", "Oral / Axilar", "35.5 – 37.5 °C", "≥ 38.0 °C", "&gt; 39.0 °C"], "verde"),
        (["Adolescentes y Adultos (11–65 años)", "Oral", "36.4 – 37.6 °C", "≥ 38.0 °C", "&gt; 39.5 °C"], "verde"),
        (["Adultos (&gt;65 años)", "Oral", "35.8 – 36.9 °C", "≥ 38.0 °C", "&gt; 39.5 °C"], "verde"),
    ]
    _te_alerta = temp_corp >= 38.0
    _te_html = "".join(
        _fila_ref(_d, _TONO2["verde"]["pastel"], _TONO2["rojo" if _te_alerta else "verde"]["vibrante"],
                  _i == _idx_te_activa)
        for _i, (_d, _t) in enumerate(_te_filas_data)
    )
    _render_tabla_html("🌡️", "Temperatura Corporal (°C)", "Fuente: Rangos clínicos por grupo de edad",
                        ["Grupo de Edad", "Tipo Lectura", "Normal (°C)", "Fiebre (°C)", "Fiebre Alta (°C)"], _te_html)
    if _idx_te_activa is not None and _te_alerta:
        st.markdown('<p style="color:#C0392B;font-weight:800;font-size:0.85rem;margin-top:-8px;">'
                     '⚠️ ¡Atención: Fiebre detectada!</p>', unsafe_allow_html=True)

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
    _render_tabla_html("💓", "Frecuencia Cardíaca (Pulso en Reposo)", "Fuente: American Heart Association (AHA)",
                        ["Grupo de Edad", "Rango Normal en Reposo", "Estado Anormal (Alerta)"], _pu_html)

    st.write("")

    # --- 3.7 Fuentes científicas — chips con enlaces ---------------------------------------
    st.markdown("##### 🔗 Fuentes de consulta médica")
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
    caja_util("Cuando recibes tus signos vitales normalmente solo ves números aislados sin saber si requieren "
              "atención. Esta sección traduce esos valores a un lenguaje claro y accesible, explicando qué "
              "significan y cómo influyen en tu día a día. Es una herramienta informativa pensada para ayudarte "
              "a comprender mejor tu organismo antes de acudir a un profesional de la salud. ❤️🩺",
              emoji="❤️", color="#FFEBEE", borde="#C0392B")
    st.caption("Estos signos vitales se ingresan en 'Mis Datos' → Bloque 3.")

    st.divider()

elif hoja_activa == "2.-IMC Y PERCENTIL":
    hoja_header(2, "El IMC sirve para saber si una persona tiene un peso saludable según su altura y peso. "
                   "En adolescentes y niños se incluye también el Percentil.",
                ilustracion=_ilustracion_imc_svg(), tip="¡Conoce tu IMC y cuida tu salud! 👍")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "IMC = Peso (kg) / [Altura (m)]²",
        referencia="Organización Mundial de la Salud (OMS)")}</div>""", unsafe_allow_html=True)

    _con_percentil = etapa in ["Niñez", "Adolescencia"] and _percentil_usuario is not None
    _riesgo_imc = _categoria_imc_usuario in ["Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3", "Obesidad Clase 3 (Severa)"]
    _riesgo_txt, _ = _RIESGO_POR_CATEGORIA.get(_categoria_imc_usuario, ("—", "#8E8E93"))

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
            cta_pill("🩸", "#FF3B30", "Prueba de riesgo de prediabetes (CDC)",
                     "Responde un breve cuestionario de 1 minuto y conoce tu riesgo.",
                     "Realizar prueba", "https://www.cdc.gov/prediabetes/risktest/index.html")
        with cta2:
            cta_pill("❤️", "#1E88E5", "Riesgos de salud por obesidad (CDC)",
                     "Conoce las enfermedades y condiciones asociadas al sobrepeso y la obesidad.",
                     "Ver más información", "https://www.cdc.gov/healthy-weight-growth/food-activity/overweight-obesity-impacts-health.html")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 9. Tabla de categorías de IMC (con columna de Riesgo) ------------------------------
    tabla_categorias_imc_visual(imc_usuario=imc)

    # --- 13. Progreso hacia una meta saludable ------------------------------------------------
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    progreso_hacia_meta_imc(imc, _categoria_imc_usuario)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 10. Gráfico de percentiles por edad (bandas de colores, ya intuitivo) ---------------
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

    # --- 11. Tabla de percentiles — fila Y columna del usuario resaltadas -------------------
    with st.expander("📊 Ver tabla completa de percentiles (edad 2-20 años)", expanded=False):
        tabla_percentiles_genero_visual(edad_usuario=edad, genero_usuario=genero, categoria_usuario=_categoria_imc_usuario)
        st.markdown("""
        <div style="margin-top:10px;background:#F3EAF7;border-radius:14px;padding:12px 16px;font-size:0.8rem;color:#6A1B9A;">
        💡 <b>¿Cómo usar esta tabla?</b> Busca la fila de tu edad y compara tu IMC con las columnas P5/P50/P85/P95:
        si tu IMC cae antes de P5 estás en Bajo Peso, entre P5 y P85 en Peso Saludable, entre P85 y P95 en Sobrepeso,
        y por encima de P95 en Obesidad. La columna marcada con tu color es la que corresponde a tu resultado actual.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 12. ¿Qué puedes hacer desde hoy? ------------------------------------------------------
    acciones_desde_hoy()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 14. Conexión con el resto del sistema ------------------------------------------------
    conexion_resto_sistema()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    caja_util("El IMC te dice, de forma simple, si tu peso está en un rango saludable para tu altura. "
              "En niños y adolescentes se usa además el 'percentil', que te compara con otros chicos de tu misma "
              "edad y sexo — porque el cuerpo de un niño en crecimiento no se mide igual que el de un adulto. 📏⚖️",
              emoji="⚖️", color="#F3E5F5", borde="#8E24AA")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "3.-TMB":
    hoja_header(3, "Biológicamente, los hombres suelen tener más masa muscular y las mujeres más porcentaje "
                   "de grasa; como el músculo quema más energía, el resultado cambia según el sexo.")

    # --- 1. ¿Qué es la TMB? -------------------------------------------------------------
    st.markdown("#### 😴 ¿Qué es la TMB?")
    ilustracion_que_es_tmb()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 2. ¿Cuál es tu resultado? --------------------------------------------------------
    st.markdown("#### 🔥 ¿Cuál es tu resultado?")
    tarjeta_resultado_tmb(tmb)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 3. ¿Cómo se calculó? — fórmula horizontal Hombre/Mujer, flechas a la derecha ----
    st.markdown("#### 🧪 ¿Cómo se calculó?")
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

# ---------------------------------------------------------------------------------------
elif hoja_activa == "4.-RCD":
    hoja_header(4, subtitulo="El Requerimiento Calórico Diario (RCD) es la cantidad de energía que tu cuerpo "
                             "necesita cada día para funcionar y moverte según tu nivel de actividad actual. "
                             "Se calcula multiplicando tu metabolismo basal (TMB) por un factor de actividad física.")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "RCD = TMB × Factor de Actividad Física",
        autor="OMS / FAO / UNU", referencia="Factor de Actividad Física")}</div>""", unsafe_allow_html=True)

    # ===== 4 tarjetas grandes: TMB → Nivel de actividad → Factor aplicado → RCD =====
    _desc_nivel_rcd = {
        "Sedentario": "Realizas muy poca actividad física durante el día.",
        "Ligero": "Realizas actividad física ligera durante el día.",
        "Moderado": "Realizas actividad física moderada durante el día.",
        "Intenso": "Realizas actividad física intensa durante el día.",
    }
    _tarjetas_grandes_rcd = [
        ("🧍", "Tu metabolismo basal (TMB)", f"{tmb:.0f} kcal/día",
         "La energía que tu cuerpo necesita incluso en reposo.", "#34C759", "#EAFAEE"),
        ("🏃", "Tu nivel de actividad", f"{actividad}",
         _desc_nivel_rcd.get(actividad, "Tu nivel de actividad física habitual durante el día."), "#007AFF", "#EAF3FF"),
        ("📈", "Factor aplicado", f"{factor:.2f}",
         "Coeficiente utilizado para calcular tu gasto diario.", "#AF52DE", "#F6ECFC"),
        ("🔥", "Tu RCD", f"{rcd:.0f} kcal/día",
         "Las calorías aproximadas que necesitas consumir para mantener tu peso.", "#FF9500", "#FFF3E5"),
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
    st.markdown(f"""
    <div class="bento-card" style="margin-bottom:18px;">
        <div class="bento-eyebrow">Resumen del cálculo aplicado</div>
        <div style="display:flex;flex-wrap:wrap;gap:22px;margin-top:10px;">
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🏃 Nivel de actividad</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{actividad}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">📈 Coeficiente aplicado</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#34C759;">{factor:.2f}</div></div>
            <div><div style="font-size:0.72rem;color:#8A94A6;font-weight:800;text-transform:uppercase;">🚻 Sexo del paciente</div>
                 <div style="font-size:1.15rem;font-weight:800;color:#17301F;">{genero}</div></div>
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
    """, unsafe_allow_html=True)

    # ===== 4 tarjetas de nivel de actividad (reemplazan la tabla), con la seleccionada iluminada =====
    st.markdown("#### 🏋️ Nivel de Actividad Física")
    _NIVELES_RCD = [
        ("Sedentario", "Sedentaria", "🪑", 1.2, "#8E8E93", "#F2F2F7"),
        ("Ligero",     "Ligero",     "🚶", FACTOR_ACTIVIDAD["Ligero"][genero],   "#34C759", "#EAFAEE"),
        ("Moderado",   "Moderada",   "🏃", FACTOR_ACTIVIDAD["Moderada"][genero], "#007AFF", "#EAF3FF"),
        ("Intenso",    "Intensa",    "🔥", FACTOR_ACTIVIDAD["Intensa"][genero],  "#FF3B30", "#FFEDEC"),
    ]
    cols_niv = st.columns(4)
    for col_n, (nombre_niv, clave_niv, icono_niv, factor_niv, color_niv, fondo_niv) in zip(cols_niv, _NIVELES_RCD):
        _es_sel = (clave_niv == actividad)
        with col_n:
            _estilo_sel = (f"background:linear-gradient(150deg,{color_niv}22 0%,#FFFFFF 75%);"
                           f"border:2.5px solid {color_niv};box-shadow:0 10px 26px {color_niv}40;transform:translateY(-3px);"
                           if _es_sel else
                           f"background:{fondo_niv};border:1.5px solid rgba(0,0,0,0.05);")
            _badge_sel = (f'<div style="margin-top:8px;background:{color_niv};color:#FFFFFF;font-size:0.68rem;'
                          f'font-weight:800;padding:3px 10px;border-radius:999px;display:inline-block;">✓ SELECCIONADO</div>'
                          if _es_sel else "")
            st.markdown(f"""
            <div style="{_estilo_sel}border-radius:20px;padding:16px 14px;text-align:center;transition:all 0.2s ease;">
                <div style="font-size:1.7rem;">{icono_niv}</div>
                <div style="font-weight:800;color:{color_niv};font-size:0.92rem;margin-top:4px;">{nombre_niv}</div>
                <div style="font-size:0.72rem;color:#8A94A6;font-weight:700;text-transform:uppercase;margin-top:2px;">Factor</div>
                <div style="font-size:1.5rem;font-weight:900;color:{color_niv};letter-spacing:-0.02em;">{factor_niv:.2f}</div>
                {_badge_sel}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ===== ¿Qué significa tu RCD? =====
    st.markdown(f"""
    <div style="background:#FFF3E5;border-left:5px solid #FF9500;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#C06000;font-size:1rem;margin-bottom:6px;">💡 ¿Qué significa tu RCD?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            Si consumes aproximadamente 🔥 <b>{rcd:.0f} kcal al día</b> y mantienes el mismo nivel de actividad
            física, ⚖️ <b>tu peso tenderá a mantenerse estable</b>. Este es tu punto de equilibrio calórico: comes
            la misma energía que gastas, así que no ganas ni pierdes peso.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== ¿Qué representa el factor de actividad? =====
    st.markdown(f"""
    <div style="background:#EAF3FF;border-left:5px solid #007AFF;border-radius:16px;padding:16px 20px;margin-bottom:18px;">
        <div style="font-weight:800;color:#0B4DA8;font-size:1rem;margin-bottom:6px;">📈 ¿Qué representa el factor de actividad?</div>
        <div style="color:#1C1C1E;font-size:0.9rem;line-height:1.6;">
            Mientras más te mueves durante el día, más energía necesita tu cuerpo. Por eso el cálculo utiliza un
            coeficiente que aumenta el gasto calórico según tu nivel de actividad física: multiplica tu TMB para
            reflejar la energía extra que gastas al trabajar, caminar, hacer ejercicio y todas tus actividades diarias.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== ¿Quién recomienda este método? =====
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # ===== Diagrama del cálculo: TMB → × Factor → = RCD =====
    st.markdown("#### 🧮 Diagrama del Cálculo")
    st.markdown(f"""
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
            <div class="cp5-flow-label">🔥 RCD</div>
            <div class="cp5-flow-value" style="color:#E67E22;">{rcd:.2f}</div>
            <div class="cp5-flow-legend">kcal/día — tu gasto calórico diario</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== Fórmula desarrollada, con los números reales del usuario =====
    st.markdown(f"""
    <div style="text-align:center;background:#F7F9F7;border-radius:18px;padding:16px 20px;margin-top:16px;
                font-family:var(--font-round);border:1px solid rgba(0,0,0,0.04);">
        <span style="font-size:1.3rem;font-weight:800;color:#17301F;">{tmb:.2f}</span>
        <span style="font-size:1.1rem;color:#8A94A6;margin:0 10px;">×</span>
        <span style="font-size:1.3rem;font-weight:800;color:#34C759;">{factor:.2f}</span>
        <span style="font-size:1.1rem;color:#8A94A6;margin:0 10px;">=</span>
        <span style="font-size:1.5rem;font-weight:900;color:#E67E22;">{rcd:.2f} kcal</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ===== Resultado final destacado, con fondo degradado naranja-rojo =====
    st.markdown(f"""
    <div style="position:relative;overflow:hidden;background:linear-gradient(120deg,#FF9500 0%,#FF6B35 55%,#FF3B30 100%);
                border-radius:26px;padding:30px 34px;text-align:center;color:#FFFFFF;
                box-shadow:0 18px 40px rgba(255,111,0,0.35);">
        <div style="position:absolute;right:18px;top:50%;transform:translateY(-50%);font-size:5rem;opacity:0.16;">🔥</div>
        <div style="font-size:0.82rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.95;">
            Resultado Final · Requerimiento Calórico Diario</div>
        <div style="font-size:2.6rem;font-weight:900;letter-spacing:-0.02em;margin:8px 0;">🔥 {rcd:.2f} <span style="font-size:1.2rem;font-weight:700;">kcal/día</span></div>
        <div style="font-size:0.86rem;opacity:0.92;">Factor aplicado: <b>{actividad}</b> ({factor:.2f}) · Sexo: <b>{genero}</b></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    with st.expander("📋 Ver tabla completa de factores de actividad (Hombres / Mujeres)"):
        _FILAS_FACTOR_TABLA = [
            ("🪑 Sedentaria", "#8E8E93", "#F2F2F7", 1.2, 1.2),
            ("🚶 Ligero",     "#34C759", "#EAFAEE", FACTOR_ACTIVIDAD["Ligero"]["Hombre"],   FACTOR_ACTIVIDAD["Ligero"]["Mujer"]),
            ("🏃 Moderada",   "#007AFF", "#EAF3FF", FACTOR_ACTIVIDAD["Moderada"]["Hombre"], FACTOR_ACTIVIDAD["Moderada"]["Mujer"]),
            ("🔥 Intensa",    "#FF3B30", "#FFEDEC", FACTOR_ACTIVIDAD["Intensa"]["Hombre"],  FACTOR_ACTIVIDAD["Intensa"]["Mujer"]),
        ]
        _filas_tabla_html = ""
        for _nom, _col, _fon, _fh, _fm in _FILAS_FACTOR_TABLA:
            _es_fila_activa = (_nom.split(" ", 1)[1] == actividad)
            _resalte = f"box-shadow:inset 0 0 0 2px {_col};" if _es_fila_activa else ""
            _filas_tabla_html += f"""
            <tr style="background:{_fon};{_resalte}">
                <td style="text-align:left;font-weight:800;color:{_col};padding:12px 16px;border-radius:12px 0 0 12px;">{_nom}{' ⭐' if _es_fila_activa else ''}</td>
                <td style="text-align:center;font-weight:800;color:#1976D2;padding:12px 16px;">♂ {_fh:.2f}</td>
                <td style="text-align:center;font-weight:800;color:#C2185B;padding:12px 16px;border-radius:0 12px 12px 0;">♀ {_fm:.2f}</td>
            </tr>"""
        st.markdown(_html_sin_lineas_vacias(f"""
        <table style="width:100%;border-collapse:separate;border-spacing:0 8px;font-family:var(--font-round);">
            <thead><tr>
                <th style="text-align:left;padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">Actividad</th>
                <th style="padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">Hombres</th>
                <th style="padding:0 16px;color:#5C6B60;font-size:0.75rem;text-transform:uppercase;">Mujeres</th>
            </tr></thead>
            <tbody>{_filas_tabla_html}</tbody>
        </table>
        """), unsafe_allow_html=True)

    caja_util("Este es el número más importante de toda la app: son las calorías reales que gastas en un día "
              "normal, sumando tu TMB (Hoja 3) más el movimiento que haces según tu nivel de actividad. "
              "Es tu 'punto de equilibrio' calórico. 🏃‍♀️🔥",
              emoji="🔥", color="#E8F5E9", borde="#43A047")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "5.-CONTROL DE PESO":
    hoja_header(5, "En menos de 10 segundos deberías poder responder: ¿cuánto necesitas normalmente?, "
                   "¿qué elegiste?, ¿cuánto debes comer ahora?, ¿qué significa? y ¿es seguro?")
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
            <div style="font-size:0.78rem;font-weight:800;color:#D81B60;text-transform:uppercase;">❤️ Nuevo RCD Objetivo</div>
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
    st.markdown("#### 📊 ¿Qué cambió?")
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
        _texto_expl = (f"Como elegiste **Bajar de peso**, el sistema redujo un **{ajuste_aplicado*100:.0f}%** tus "
                        "calorías diarias. Eso permite que tu cuerpo obtenga parte de la energía usando las "
                        "reservas de grasa, siempre manteniendo un aporte adecuado de nutrientes. "
                        "**No es una dieta extrema. Es un déficit calórico controlado.**")
    elif objetivo == "Subir de peso":
        _texto_expl = (f"Como elegiste **Subir de peso**, el sistema aumentó un **{ajuste_aplicado*100:.0f}%** tus "
                        "calorías diarias. Ese excedente le da a tu cuerpo la energía extra que necesita para "
                        "construir tejido nuevo (músculo). **No es 'comer de más': es un superávit calórico controlado.**")
    else:
        _texto_expl = ("Como elegiste **Mantenerte**, tu RCD Objetivo es igual a tu RCD Inicial: comerás "
                        "aproximadamente lo mismo que gastas, sin déficit ni superávit, para conservar tu peso actual.")
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
    _build_panel_macros_creativo(gr_prot, gr_gras, gr_carb, peso)

    caja_util(f"¡Vamos, {_nombre_saludo}! Aquí se traduce tu meta ('quiero bajar/subir/mantener peso') en un "
              "número exacto de calorías al día (tu RCD Objetivo), sin arriesgar tu salud: nunca por debajo de "
              "tu TMB. Revisa la hoja 'Línea de Tiempo' para ver cómo evolucionaría tu peso con este plan. 🎯",
              emoji="🎯", color="#FCE4EC", borde="#D81B60")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "6.-MACRONUTRIENTES":
    hoja_header(6, "Proteínas y grasas se calculan según tus gramos por kilo de peso corporal; los "
                   "carbohidratos cubren la energía restante hasta completar tu Requerimiento Calórico Diario.")

    # ===== RCD grande y destacado arriba de todo =====
    st.markdown(f"""
    <div style="background:linear-gradient(120deg,#1E5631 0%,#2E7D32 60%,#4CAF50 100%);border-radius:26px;
                padding:26px 30px;text-align:center;color:#FFFFFF;margin-bottom:18px;
                box-shadow:0 16px 36px rgba(30,86,49,0.30);">
        <div style="font-size:0.8rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;opacity:0.92;">
            🔥 Tu Requerimiento Calórico Diario (RCD)</div>
        <div style="font-size:2.8rem;font-weight:900;letter-spacing:-0.02em;margin:6px 0;">{rcd_final:.2f} <span style="font-size:1.1rem;font-weight:700;">kcal/día</span></div>
        <div style="font-size:0.84rem;opacity:0.9;">Sobre este total se reparten tus macronutrientes.</div>
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
    st.markdown("#### 🍽️ ¿Cómo se reparten tus calorías?")
    st.markdown(f"""
    <div style="text-align:center;margin:6px 0 18px 0;">
        <div style="font-size:2.1rem;font-weight:900;color:#17301F;">{rcd_final:.0f} <span style="font-size:1rem;font-weight:700;color:#8E8E93;">kcal</span></div>
        <div style="font-size:1.3rem;color:#8E8E93;margin:2px 0 14px 0;">↓</div>
    </div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;">
        <div style="flex:1;min-width:150px;background:#FFEBF0;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #FF2D5533;">
            <div style="font-size:1.6rem;">❤️</div>
            <div style="font-weight:800;color:#C2185B;margin:4px 0 2px 0;">Proteínas</div>
            <div style="font-size:0.78rem;color:#8A5252;">Construyen</div>
            <div style="font-weight:800;color:#C2185B;margin-top:6px;">4 kcal/g</div>
        </div>
        <div style="flex:1;min-width:150px;background:#EAFAEE;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #34C75933;">
            <div style="font-size:1.6rem;">🥑</div>
            <div style="font-weight:800;color:#1E5631;margin:4px 0 2px 0;">Grasas</div>
            <div style="font-size:0.78rem;color:#3E7050;">Protegen</div>
            <div style="font-weight:800;color:#1E5631;margin-top:6px;">9 kcal/g</div>
        </div>
        <div style="flex:1;min-width:150px;background:#FFF8E1;border-radius:18px;padding:16px;text-align:center;border:1.5px solid #FFCC0055;">
            <div style="font-size:1.6rem;">🌾</div>
            <div style="font-weight:800;color:#8A6D00;margin:4px 0 2px 0;">Carbohidratos</div>
            <div style="font-size:0.78rem;color:#9C8300;">Dan energía</div>
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
            🌍 Recomendación internacional</div>
        <p style="margin:0 0 6px 0;color:#17301F;font-size:0.86rem;">
            Según la Organización Mundial de la Salud (OMS):</p>
        <p style="margin:0 0 4px 0;color:#3C3C43;font-size:0.84rem;">✔ Proteínas y grasas son nutrientes esenciales.</p>
        <p style="margin:0 0 4px 0;color:#3C3C43;font-size:0.84rem;">✔ Los carbohidratos son la principal fuente práctica de energía.</p>
        <p style="margin:0 0 8px 0;color:#3C3C43;font-size:0.84rem;">✔ Una alimentación saludable debe incluir un equilibrio entre los tres macronutrientes.</p>
        <p style="margin:0;color:#8E8E93;font-size:0.7rem;">Referencia: Organización Mundial de la Salud (OMS).</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("🌾 **Dato importante (OMS):** a diferencia de las proteínas y las grasas, los **carbohidratos "
            "no son un nutriente esencial**: el cuerpo puede obtener energía de grasas y proteínas mediante "
            "gluconeogénesis. Se incluyen en la dieta por ser una fuente práctica y eficiente de energía, "
            "pero no son indispensables para sobrevivir ni para una nutrición adecuada.")

    st.divider()

    # =====================================================================================
    # 3. TARJETAS CON PERSONALIDAD — qué función cumple cada macronutriente
    # =====================================================================================
    st.markdown("#### 🧠 ¿Qué hace cada macronutriente?")
    tp1, tp2, tp3 = st.columns(3)
    with tp1:
        st.markdown("""
        <div class="macro-card prot">
            <div class="mc-head"><span class="mc-icon">❤️</span><span class="mc-title">Proteínas</span>
                <span class="mc-tip" title="1 gramo de proteína equivale a 4 kcal. Se calcula multiplicando tu peso (kg) por un factor de 1.8 a 2.5 g/kg.">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🏗 Construyen músculos</p>
            <p style="margin:2px 0;font-size:0.82rem;">🩹 Reparan tejidos</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🛡 Forman enzimas</p>
            <div class="mc-value">⚡ 4 kcal/g</div>
            <div class="mc-sub">Factores (g/kg de peso):<br>Mínimo <b>1.8</b> · Intermedio <b>2.1</b> · Máximo <b>2.5</b></div>
        </div>
        """, unsafe_allow_html=True)
    with tp2:
        st.markdown("""
        <div class="macro-card gras">
            <div class="mc-head"><span class="mc-icon">🥑</span><span class="mc-title">Grasas</span>
                <span class="mc-tip" title="1 gramo de grasa equivale a 9 kcal. Se calcula multiplicando tu peso (kg) por un factor de 0.5 a 1.5 g/kg.">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🧠 Protegen el cerebro</p>
            <p style="margin:2px 0;font-size:0.82rem;">🔥 Reserva energética</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🫀 Ayudan a absorber vitaminas</p>
            <div class="mc-value">⚡ 9 kcal/g</div>
            <div class="mc-sub">Factores (g/kg de peso):<br>Mínimo <b>0.5</b> · Intermedio <b>1.0</b> · Máximo <b>1.5</b></div>
        </div>
        """, unsafe_allow_html=True)
    with tp3:
        st.markdown("""
        <div class="macro-card carb">
            <div class="mc-head"><span class="mc-icon">🌾</span><span class="mc-title">Carbohidratos</span>
                <span class="mc-tip" title="1 gramo de carbohidrato equivale a 4 kcal. No usan un factor de peso: cubren la energía restante hasta tu RCD.">ℹ️</span></div>
            <p style="margin:6px 0 2px 0;font-size:0.82rem;">🏃 Principal combustible</p>
            <p style="margin:2px 0 8px 0;font-size:0.82rem;">🧠 Energía para el cerebro</p>
            <div class="mc-value">⚡ 4 kcal/g</div>
            <div class="mc-sub">Sin factor de peso — cubren el resto de la energía de tu RCD.</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # =====================================================================================
    # TABLA 2 — Proyección de Requerimientos (demostración de los 3 niveles) — sin tocar
    # =====================================================================================
    st.markdown("#### 📊 Proyección de Requerimientos")
    st.markdown(f"""
    <div style="text-align:center;color:#8E8E93;font-size:0.8rem;font-weight:700;margin-bottom:8px;">
        Peso → Factores OMS → Proteínas → Grasas → Carbohidratos → Plan nutricional
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Prot(g)=peso×Factor → Kcal=g×4 | Grasa(g)=peso×Factor → Kcal=g×9 | "
        "Carb: Kcal = RCD − Kcal Restantes → Gramos = Kcal/4",
        referencia="Modelo de reparto de macronutrientes por nivel")}</div>""", unsafe_allow_html=True)
    st.caption("Así se calculan los escenarios Mínimo, Intermedio y Máximo basados en tu peso actual.")
    st.info(f"⚖️ Peso usado en los cálculos: **{peso_usuario:.2f} kg** · 🔥 RCD objetivo: **{rcd_usuario:.2f} kcal/día**")

    _filas_niveles_html = ""
    _COL_PROT = ("#C2185B", "#FFEBF0")
    _COL_GRAS = ("#1E5631", "#EAFAEE")
    _COL_CARB = ("#8A6D00", "#FFF8E1")
    for _nivel in ["Mínimo", "Intermedio", "Máximo"]:
        _d = niveles_calculados[_nivel]
        _es_actual = (_nivel == nivel_final)
        _borde_sel = "box-shadow:inset 0 2px 0 #FFCC00,inset 0 -2px 0 #FFCC00;" if _es_actual else ""
        _nombre_fila = f"⭐ {_nivel}" if _es_actual else _nivel
        _badge_tu_nivel = ' <span class="badge-tu-nivel">TU NIVEL</span>' if _es_actual else ""
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
            <th rowspan="2">Nivel</th>
            <th colspan="3" style="background:{_COL_PROT[0]};">🥩 Proteína</th>
            <th colspan="3" style="background:{_COL_GRAS[0]};">🥑 Grasa</th>
            <th colspan="3" style="background:{_COL_CARB[0]};">🌾 Carbohidrato</th>
        </tr>
        <tr>
            <th style="background:{_COL_PROT[0]};">Factor</th><th style="background:{_COL_PROT[0]};">Gramos</th><th style="background:{_COL_PROT[0]};">Kcal/día</th>
            <th style="background:{_COL_GRAS[0]};">Factor</th><th style="background:{_COL_GRAS[0]};">Gramos</th><th style="background:{_COL_GRAS[0]};">Kcal/día</th>
            <th style="background:{_COL_CARB[0]};">Kcal Restantes</th><th style="background:{_COL_CARB[0]};">Gramos</th><th style="background:{_COL_CARB[0]};">Kcal/día</th>
        </tr>
        </thead>
        <tbody>
        {_filas_niveles_html}
        </tbody>
    </table>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_niveles), unsafe_allow_html=True)
    st.caption("⭐ La fila resaltada con borde amarillo es el nivel que corresponde a tu objetivo actual "
               f"(**{objetivo_usuario}** → **{nivel_final}**).")
    st.caption("💡 **Kcal Restantes:** es la suma de la Kcal/día de Proteína + la Kcal/día de Grasa de "
               "ESE mismo nivel (Mínimo, Intermedio o Máximo) — por eso cambia en cada fila. "
               "**Carbohidratos:** no usan un factor de peso; se calculan cubriendo la energía "
               "restante hasta tu Requerimiento Calórico Diario → "
               "`Kcal/día Carbohidrato = RCD − Kcal Restantes` y `Gramos = Kcal/día ÷ 4`.")

    st.divider()

    # =====================================================================================
    # TABLA 3 — Tu Plan Nutricional Definitivo (filtro inteligente según tu objetivo)
    # =====================================================================================
    st.markdown("#### 🎯 Este será tu plan diario")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        'IF "Bajar de peso" → Mínimo (1.8/0.5) · IF "Mantenerse" → Intermedio (2.1/1.0) · '
        'IF "Subir de peso" → Máximo (2.5/1.5)',
        referencia="Filtro inteligente según objetivoUsuario")}</div>""", unsafe_allow_html=True)
    st.caption("Basado en tu elección de la página anterior, aquí tienes tus requerimientos exactos para alcanzar tu meta.")
    st.success(f"🎯 Objetivo seleccionado: **{objetivo_usuario}** → Nivel aplicado: **{nivel_final}** "
               f"(Proteína {FACTORES_PROT[nivel_final]:.1f} g/kg · Grasa {FACTORES_GRAS[nivel_final]:.1f} g/kg)")

    # ---- Resumen visual: 3 tarjetas grandes + barra de calorías ----
    rp1, rp2, rp3 = st.columns(3)
    for _col_r, _ic_r, _val_r, _lab_r, _col_hex_r, _fon_r in [
        (rp1, "❤️", f"{datos_final['gr_prot']:.0f} g", "Proteínas", "#C2185B", "#FFEBF0"),
        (rp2, "🥑", f"{datos_final['gr_gras']:.0f} g", "Grasas", "#1E5631", "#EAFAEE"),
        (rp3, "🌾", f"{datos_final['gr_carb']:.0f} g", "Carbohidratos", "#8A6D00", "#FFF8E1"),
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
            {total_kcal_final:.0f} kcal — 100%</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Gráfico donut ----
    fig_donut_macro = go.Figure(data=[go.Pie(
        labels=["❤️ Proteínas", "🥑 Grasas", "🌾 Carbohidratos"],
        values=[datos_final["kcal_prot"], datos_final["kcal_gras"], datos_final["kcal_carb"]],
        hole=0.62,
        marker=dict(colors=["#FF2D55", "#34C759", "#FFCC00"]),
        textinfo="label+percent",
        textfont=dict(size=13),
    )])
    fig_donut_macro.update_layout(
        annotations=[dict(text=f"🍽<br><b>{total_kcal_final:.0f}</b><br>kcal", x=0.5, y=0.5,
                           font=dict(size=15, color="#17301F"), showarrow=False)],
        showlegend=False, height=340, margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_donut_macro, use_container_width=True)
    st.caption("El gráfico muestra de dónde vienen principalmente tus calorías diarias.")

    _html_tabla_final = f"""
    <table class="macro-final-table">
        <thead>
        <tr><th style="text-align:left;">Macronutriente</th><th>Gramos (g)</th><th>Kcal/día</th></tr>
        </thead>
        <tbody>
        <tr>
            <td style="text-align:left;">🥩 Proteína</td>
            <td>{datos_final['gr_prot']:.1f} g</td>
            <td>{datos_final['kcal_prot']:.0f} kcal/día</td>
        </tr>
        <tr>
            <td style="text-align:left;">🥑 Grasa</td>
            <td>{datos_final['gr_gras']:.1f} g</td>
            <td>{datos_final['kcal_gras']:.0f} kcal/día</td>
        </tr>
        <tr>
            <td style="text-align:left;">🌾 Carbohidrato</td>
            <td>{datos_final['gr_carb']:.1f} g</td>
            <td>{datos_final['kcal_carb']:.0f} kcal/día</td>
        </tr>
        <tr class="fila-total">
            <td style="text-align:left;">TOTAL</td>
            <td>{total_gr_final:.1f} g</td>
            <td>{total_kcal_final:.0f} kcal/día
                <span style="display:inline-block;margin-left:10px;background:#FFCC00;color:#5C4700;
                    font-weight:900;font-size:0.8rem;padding:4px 12px;border-radius:999px;
                    letter-spacing:0.02em;">→ RCD</span>
            </td>
        </tr>
        </tbody>
    </table>
    """
    st.markdown(_html_sin_lineas_vacias(_html_tabla_final), unsafe_allow_html=True)

    if abs(total_kcal_final - rcd_usuario) < 1:
        st.markdown("""
        <div style="background:linear-gradient(120deg,#34C759 0%,#1E5631 100%);color:#FFFFFF;
                    border-radius:20px;padding:20px 26px;margin-top:14px;text-align:center;
                    font-weight:900;font-size:1.05rem;box-shadow:0 14px 32px rgba(52,199,89,0.35);">
            ✅ El total de calorías coincide exactamente con tu Requerimiento Calórico Diario (RCD).
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # =====================================================================================
    # ¿POR QUÉ NO TODOS SE CALCULAN IGUAL? — versión corta, tipo clínica
    # =====================================================================================
    st.markdown("#### 💡 ¿Por qué no todos se calculan igual?")
    wp1, wp2, wp3 = st.columns(3)
    with wp1:
        st.markdown("""<div style="background:#FFEBF0;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">❤️</div><b style="color:#C2185B;">Proteínas</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">Dependen de tu peso corporal.</p>
        </div>""", unsafe_allow_html=True)
    with wp2:
        st.markdown("""<div style="background:#EAFAEE;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">🥑</div><b style="color:#1E5631;">Grasas</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">También dependen de tu peso.</p>
        </div>""", unsafe_allow_html=True)
    with wp3:
        st.markdown("""<div style="background:#FFF8E1;border-radius:16px;padding:14px;text-align:center;height:100%;">
        <div style="font-size:1.3rem;">🌾</div><b style="color:#8A6D00;">Carbohidratos</b>
        <p style="margin:6px 0 0 0;font-size:0.8rem;color:#3C3C43;">Se calculan con las calorías restantes hasta completar tu RCD.</p>
        </div>""", unsafe_allow_html=True)

    st.write("")

    # =====================================================================================
    # ¿SABÍAS QUE? — curiosidades rotativas
    # =====================================================================================
    _curiosidades_macro = [
        ("📚", "El cuerpo puede almacenar muy poca proteína. Por eso necesita consumirla regularmente."),
        ("🧠", "El cerebro utiliza principalmente glucosa como fuente de energía."),
        ("🥑", "Las grasas aportan más del doble de energía por gramo que proteínas y carbohidratos."),
    ]
    _idx_curio = int(datetime.now().timestamp() // 8) % len(_curiosidades_macro)
    _ic_curio, _txt_curio = _curiosidades_macro[_idx_curio]
    st.markdown(f"""
    <div style="background:#F5F5F7;border-radius:16px;padding:14px 18px;display:flex;gap:12px;align-items:center;">
        <div style="font-size:1.4rem;">{_ic_curio}</div>
        <div style="font-size:0.84rem;color:#3C3C43;"><b>¿Sabías que?</b> {_txt_curio}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    caja_util("Las proteínas y grasas se calculan según tu peso corporal (gramos por kilo), porque son "
              "nutrientes estructurales que dependen de tu masa, no de cuánta energía gastas. Los "
              "carbohidratos, en cambio, son la variable de ajuste: llenan el resto de tu energía diaria "
              "hasta llegar exactamente a tu RCD. 🍽️",
              emoji="🍽️", color="#FFFDE7", borde="#FBC02D")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "7.-PORCIONES":
    hoja_header(7, "Tu Requerimiento Calórico Diario se reparte en 5 momentos del día usando porcentajes "
                   "preestablecidos, para mantener tu metabolismo activo y evitar la ansiedad.")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Energía(comida) = RCD × % preestablecido (Desayuno 25% · Merienda 5% · Almuerzo 40% · "
        "Merienda 5% · Cena 25%)",
        referencia="Distribución calórica por comidas")}</div>""", unsafe_allow_html=True)

    # =====================================================================================
    # RCD del usuario (ya calculado y ajustado a su objetivo en la Hoja 5)
    # =====================================================================================
    _rcd_comidas = rcd_final

    _html_rcd_hero = f"""
    <div class="rcd-hero-card">
        <div class="rcd-hero-decor d1">🔥</div>
        <div class="rcd-hero-decor d2">🍎</div>
        <div class="rcd-label">⚡ Tu Requerimiento Calórico Diario</div>
        <div class="rcd-value">🎯 {_rcd_comidas:.2f} <span style="font-size:1.3rem;font-weight:700;">kcal</span></div>
        <div class="rcd-sub">Para mantener tu metabolismo activo y evitar la ansiedad, hemos distribuido tus
        calorías totales a lo largo del día. Cada comida representa un porcentaje ideal de tu RCD. Los
        valores que ves en la tabla resultan de multiplicar tu RCD total por el porcentaje correspondiente
        a cada comida.</div>
        <div class="rcd-hero-badges">
            <span class="rcd-hero-badge">🌅 Desayuno 25%</span>
            <span class="rcd-hero-badge">🍎 Merienda 1 · 5%</span>
            <span class="rcd-hero-badge">🍽️ Almuerzo 40%</span>
            <span class="rcd-hero-badge">🥪 Merienda 2 · 5%</span>
            <span class="rcd-hero-badge">🌙 Cena 25%</span>
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
            <td class="comida-nombre">{_ICONOS_COMIDA[_comida]} {_comida}</td>
            <td>{_pct*100:.0f}%</td>
            <td>{_kcal_comida:.2f} kcal</td>
        </tr>"""

    _filas_comidas_html += f"""
        <tr class="fila-total-comidas">
            <td class="comida-nombre" style="color:#FFFFFF;">🔥 RCD (Total Distribuido)</td>
            <td>100%</td>
            <td>{_suma_kcal_comidas:.2f} kcal</td>
        </tr>"""

    _html_tabla_comidas = f"""
    <div class="comidas-table-wrap">
    <table class="comidas-table">
        <thead>
        <tr><th style="text-align:left;">Comida</th><th>Porcentaje (%)</th><th>Energía (kcal)</th></tr>
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
    _estado_txt = "✅ Coinciden" if _coincide else "❌ No coinciden"

    _html_val_card = f"""
    <div class="val-card">
        <div class="val-card-title">🔍 Comparación: RCD Calculado vs. Total Distribuido</div>
        <table class="val-comparacion-table">
            <tr><td>RCD Calculado</td><td>{_rcd_comidas:.2f} kcal</td></tr>
            <tr><td>Total Distribuido</td><td>{_suma_kcal_comidas:.2f} kcal</td></tr>
            <tr><td>Diferencia</td><td>{_diferencia_validacion:.2f} kcal</td></tr>
            <tr class="{_fila_estado_clase}"><td>Estado</td><td>{_estado_txt}</td></tr>
        </table>
        <div class="val-card-title" style="margin-top:4px;">📋 Estado de Validación</div>
        <div class="val-checklist">
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> RCD Calculado ............. {_rcd_comidas:.2f} kcal
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> Total Distribuido ......... {_suma_kcal_comidas:.2f} kcal
<span class="{'val-ok' if _coincide else 'val-bad'}">{'✔' if _coincide else '✖'}</span> Diferencia ................ {_diferencia_validacion:.2f} kcal
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_val_card), unsafe_allow_html=True)

    if _coincide:
        st.markdown("""
        <div class="val-banner-ok">
            <span class="val-banner-icon">🟢</span>
            <div class="val-banner-title">✔ Planificación Energética Correcta</div>
            <div class="val-banner-sub">Las calorías distribuidas en tus 5 comidas coinciden exactamente
            con tu Requerimiento Calórico Diario. ✨ ¡Matemática exacta! Tu día está planificado al 100%.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="val-banner-error">
            <span class="val-banner-icon">🔴</span>
            <div class="val-banner-title">⚠ Existe una diferencia de {_diferencia_validacion:.2f} kcal
            entre el RCD y la distribución diaria.</div>
            <div class="val-banner-sub">Revise la planificación.</div>
        </div>
        """, unsafe_allow_html=True)

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

# ---------------------------------------------------------------------------------------
elif hoja_activa == "8.-FATSECRET":
    hoja_header(8, subtitulo="Descubre la composición nutricional de los alimentos más consumidos en el Perú "
                             "utilizando información oficial del INS/CENAN. Busca un alimento y conoce su "
                             "aporte de energía y nutrientes de forma clara y sencilla.")

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

    st.markdown("#### 🌐 Buscador FatSecret (externo)")
    consulta_fs = st.text_input("Escribe el nombre de un alimento para buscarlo en FatSecret:",
                                 "", key="bpa_buscar_fatsecret")
    if consulta_fs.strip():
        url_fs = f"https://www.fatsecret.es/calor%C3%ADas-nutrici%C3%B3n/search?q={quote(consulta_fs.strip())}"
        st.link_button(f"🔍 Ver '{consulta_fs}' en FatSecret", url_fs, use_container_width=True)
    else:
        st.link_button("🌐 Abrir FatSecret", "https://www.fatsecret.es/", use_container_width=True)
    st.markdown("""
    <div style="background:#E6F7FA;border-left:5px solid #30B0C7;border-radius:16px;padding:14px 18px;margin:14px 0;">
    <b style="color:#0B7285;">🌐 ¿Por qué usamos FatSecret?</b><br>
    <span style="color:#1C1C1E;font-size:0.9rem;">Es una base de datos externa y muy amplia, con miles de alimentos,
    marcas y productos envasados peruanos e internacionales. La usamos como <b>respaldo rápido</b> cuando buscas un
    producto comercial específico o algo que no forma parte de nuestra Base Peruana de Alimentos.</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🔎 Buscador Nutricional · Tabla Peruana de Composición de Alimentos")
    consulta = st.text_input("Escribe el nombre de un alimento (p. ej. 'palta', 'pollo', 'arroz'):",
                              "", key="bpa_buscar")

    resultados = buscar_alimentos(consulta) if consulta.strip() else []

    alimento_sel = None
    if consulta.strip() and resultados:
        opciones = [f"{r['nombre']} · {GRUPOS_ALIMENTOS[r['grupo_cod']]['icono']} {GRUPOS_ALIMENTOS[r['grupo_cod']]['nombre']}" for r in resultados]
        idx_sel = st.selectbox("Coincidencias encontradas:", range(len(opciones)),
                                format_func=lambda i: opciones[i], key="bpa_sel")
        alimento_sel = resultados[idx_sel]
    elif consulta.strip() and not resultados:
        st.warning(f"No encontramos '{consulta}' en la Base Peruana de Alimentos (343 alimentos curados de mayor "
                   "consumo). Puedes buscarlo en el buscador de FatSecret de arriba como respaldo.")

    if alimento_sel:
        f = alimento_sel
        g = GRUPOS_ALIMENTOS[f["grupo_cod"]]

        def _m(v, suf=""):
            return f"{v:g}{suf}" if v is not None else "s/d"

        kcal, prot, gras, cho, fibra = f["kcal"], f["proteinas"], f["grasas"], f["cho"], f["fibra"]
        partes = [("Grasas", gras, "#FF9500"), ("Carbohidratos", cho, "#30B0C7"), ("Proteínas", prot, "#34C759")]
        total_e = sum((p[1] or 0) * (9 if p[0] == "Grasas" else 4) for p in partes)
        barras = ""
        etiquetas = []
        if total_e > 0:
            for nombre_p, val, color in partes:
                pct = round(((val or 0) * (9 if nombre_p == "Grasas" else 4) / total_e) * 100)
                if pct > 0:
                    barras += f'<div style="width:{pct}%;background:{color};"></div>'
                    etiquetas.append(f"{nombre_p} {pct}%")

        st.markdown(f"""
        <div class="bpa-card">
            <h3>{g['icono']} {f['nombre']}</h3>
            <div class="bpa-sub">{g['nombre']} · código {f['codigo']}</div>
            <div class="bpa-sub" style="margin-top:-10px;">Resumen nutricional · por 100 g de porción comestible</div>
            <div class="bpa-grid">
                <div class="bpa-metric"><div class="lbl">🔥 Energía</div><div class="val">{_m(kcal,' kcal')}</div></div>
                <div class="bpa-metric"><div class="lbl">💪 Proteínas</div><div class="val">{_m(prot,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🥑 Grasas</div><div class="val">{_m(gras,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🍞 Carbohidratos</div><div class="val">{_m(cho,' g')}</div></div>
                <div class="bpa-metric"><div class="lbl">🌾 Fibra</div><div class="val">{_m(fibra,' g')}</div></div>
            </div>
            {"<div class='bpa-bar-wrap'><div style='font-size:0.78rem;color:#9DA3AE;margin-bottom:6px;'>Distribución energética</div><div class='bpa-bar'>" + barras + "</div><div class='bpa-bar-label'>" + " · ".join(etiquetas) + "</div></div>" if barras else ""}
            <div class="bpa-source">📚 Según la Tabla Peruana de Composición de Alimentos (INS/CENAN, 11.ª edición digital, 2025). Valores por 100 g de porción comestible.</div>
            <div style="font-weight:700;color:#F2F2F7;margin-bottom:4px;">¿Qué aporta principalmente?</div>
            <div class="bpa-tips">{g['icono']} {g['aporta']}</div>
            <div style="font-weight:700;color:#F2F2F7;margin:12px 0 4px 0;">Recomendaciones</div>
            {''.join(f'<div class="bpa-tips">✔ {t}</div>' for t in g['tips'])}
            <div>
                <span class="bpa-chip">🍽️ Macronutrientes</span>
                <span class="bpa-chip">📋 Dieta</span>
                <span class="bpa-chip">⚖️ Control de peso</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if f["calcio"] is not None or f["hierro"] is not None or f["vitc"] is not None:
            st.markdown(
                f"<div style='color:#5C6B60;font-size:0.85rem;margin-top:-8px;'>"
                f"Además, cada 100 g aportan: "
                f"{'🦴 Calcio ' + _m(f['calcio'],' mg') + '  ' if f['calcio'] is not None else ''}"
                f"{'🩸 Hierro ' + _m(f['hierro'],' mg') + '  ' if f['hierro'] is not None else ''}"
                f"{'🍊 Vitamina C ' + _m(f['vitc'],' mg') if f['vitc'] is not None else ''}"
                f"</div>", unsafe_allow_html=True)

    elif not consulta.strip():
        with st.expander("🗂️ Ver los 14 grupos de alimentos disponibles"):
            cols_g = st.columns(4)
            for i, (cod, g) in enumerate(GRUPOS_ALIMENTOS.items()):
                n_items = sum(1 for x in FOOD_DB if x["grupo_cod"] == cod)
                cb, cf = GRUPOS_COLORES.get(cod, ("#8E8E93", "#F2F2F7"))
                with cols_g[i % 4]:
                    st.markdown(f"""
                    <div style="background:{cf};border-left:4px solid {cb};border-radius:12px;
                        padding:10px 12px;margin-bottom:10px;">
                        <div style="font-weight:800;color:{cb};font-size:0.88rem;">{g['icono']} {g['nombre']}</div>
                        <div style="color:#5C6B60;font-size:0.78rem;">{n_items} alimentos</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#EAFAEE;border-left:5px solid #34C759;border-radius:16px;padding:14px 18px;margin:14px 0;">
    <b style="color:#1E5631;">🇵🇪 ¿Por qué usamos la Tabla Peruana de Composición de Alimentos?</b><br>
    <span style="color:#1C1C1E;font-size:0.9rem;">Es la fuente <b>oficial y nacional</b> (INS/CENAN), elaborada
    con alimentos y preparaciones típicas del Perú. Sus valores son más precisos para nuestra población que una
    base genérica, por eso es la base principal del buscador, y FatSecret queda como respaldo complementario.</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🍽️ Guía Alimentaria Peruana")
    cols_guia = st.columns(3)
    for i, (icono, titulo, desc) in enumerate(GUIAS_ALIMENTARIAS_PERU):
        with cols_guia[i % 3]:
            st.markdown(f"""
            <div class="bpa-guide-card">
                <div class="gi">{icono}</div>
                <div class="gt">{titulo}</div>
                <div class="gd">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.caption("Basado en las Guías Alimentarias para la Población Peruana (MINSA).")

    st.markdown("### 🗂️ Alimentos disponibles en el buscador")
    st.caption("343 alimentos curados de mayor consumo en el Perú, agrupados por categoría, con su energía "
               "(kcal) por 100 g de porción comestible. Cada grupo tiene su propio color para ubicarlo más fácil.")
    orden_grupos = sorted(GRUPOS_ALIMENTOS.items(), key=lambda kv: -sum(1 for x in FOOD_DB if x["grupo_cod"] == kv[0]))
    for cod, g in orden_grupos:
        items_g = sorted([x for x in FOOD_DB if x["grupo_cod"] == cod], key=lambda x: x["nombre"])
        color_borde, color_fondo = GRUPOS_COLORES.get(cod, ("#8E8E93", "#F2F2F7"))

        filas_html = ""
        vistos = set()
        for it in items_g:
            nombre_limpio = _limpiar_nombre_alimento(it["nombre"])
            if not nombre_limpio or nombre_limpio.lower() in vistos:
                continue
            vistos.add(nombre_limpio.lower())
            kcal_txt = f"{it['kcal']:g} kcal" if it["kcal"] is not None else "s/d"
            filas_html += (
                f"<tr><td style='padding:9px 16px;border-bottom:1px solid {color_fondo};color:#1C1C1E;font-size:0.86rem;'>"
                f"{nombre_limpio}</td>"
                f"<td style='padding:9px 16px;border-bottom:1px solid {color_fondo};text-align:right;"
                f"font-weight:700;color:{color_borde};white-space:nowrap;font-size:0.86rem;'>{kcal_txt}</td></tr>"
            )

        with st.expander(f"{g['icono']} {g['nombre']} · {len(items_g)} alimentos"):
            st.markdown(f"""
            <div style="border-radius:18px;overflow:hidden;border:1px solid {color_fondo};
                box-shadow:0 1px 2px rgba(0,0,0,0.06),0 6px 18px rgba(0,0,0,0.06);">
              <div style="background:{color_borde};color:#FFFFFF;padding:12px 18px;font-weight:800;
                  font-size:0.95rem;display:flex;justify-content:space-between;align-items:center;">
                <span>{g['icono']} {g['nombre']}</span>
                <span style="background:rgba(255,255,255,0.25);border-radius:999px;padding:3px 12px;font-size:0.72rem;">
                    {len(items_g)} alimentos</span>
              </div>
              <div style="max-height:360px;overflow-y:auto;background:#FFFFFF;">
                <table style="width:100%;border-collapse:collapse;">
                  <thead>
                    <tr style="background:{color_fondo};position:sticky;top:0;">
                      <th style="text-align:left;padding:9px 16px;color:{color_borde};font-size:0.7rem;
                          text-transform:uppercase;letter-spacing:0.03em;">Alimento</th>
                      <th style="text-align:right;padding:9px 16px;color:{color_borde};font-size:0.7rem;
                          text-transform:uppercase;letter-spacing:0.03em;">Energía / 100 g</th>
                    </tr>
                  </thead>
                  <tbody>{filas_html}</tbody>
                </table>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### 📚 Información para profesionales")
    with st.container():
        st.markdown("""
        <div style="background:#F2F2F7;border-radius:18px;padding:18px 22px;">
        <div class="bpa-pro-item">✔ Valores expresados por 100 g de porción comestible.</div>
        <div class="bpa-pro-item">✔ Basado en la Tabla Peruana de Composición de Alimentos, INS/CENAN.</div>
        <div class="bpa-pro-item">✔ Utilizar porciones individualizadas según el caso.</div>
        <div class="bpa-pro-item">✔ Ajustar según edad.</div>
        <div class="bpa-pro-item">✔ Ajustar según condición clínica.</div>
        <div class="bpa-pro-item">✔ Ajustar según evaluación nutricional.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#EAFAEE;border-left:5px solid #1E5631;border-radius:16px;padding:16px 20px;margin-top:14px;">
    <b style="color:#1E5631;">👩‍⚕️ Criterio profesional</b><br>
    <span style="color:#1C1C1E;">Las porciones, intercambios y recomendaciones específicas deben ser definidas por el
    nutricionista responsable, considerando la evaluación clínica, nutricional y los objetivos individuales del
    paciente.</span>
    </div>
    """, unsafe_allow_html=True)

    caja_util("Busca cualquier alimento peruano de consumo frecuente y obtén al instante su información "
              "nutricional oficial (INS/CENAN): calorías, proteínas, grasas, carbohidratos y fibra por cada "
              "100 g, junto con recomendaciones prácticas según su grupo alimenticio. Ya no depende de FatSecret. 🇵🇪🥗",
              emoji="🇵🇪", color="#E0F2F1", borde="#00796B")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "9.-DIETA":
    hoja_header(9, "Elige un alimento por macronutriente en cada comida y arma tu menú diario personalizado.")

    # =====================================================================================
    # SECCIÓN 1 — Panel de Resumen de Datos Nutricionales
    # =====================================================================================
    st.markdown("""
    <p style="text-align:center;color:#5C6B60;font-size:0.94rem;max-width:720px;margin:0 auto 14px auto;">
    Estos valores han sido calculados previamente en base a tu perfil. A continuación, te presentamos el
    resumen de tus requerimientos calóricos diarios y cómo se distribuyen en tu día a día.
    </p>
    """, unsafe_allow_html=True)

    _ICONOS_COMIDA_D9 = {"Desayuno": "🌅", "Merienda 1": "🍎", "Almuerzo": "🍽️", "Merienda 2": "🥪", "Cena": "🌙"}
    _filas_tiempos_html = "".join(
        f"""<div class="rn-tiempos-row"><span>{_ICONOS_COMIDA_D9[_c]} {_c}</span>
            <span class="rn-kcal">{porciones[_c]['kcal']:.2f} kcal</span></div>"""
        for _c in porciones
    )

    _html_resumen_nutri = f"""
    <div class="resumen-nutri-wrap">
        <div class="resumen-nutri-card rn-tiempos">
            <div class="rn-title">⏰ Distribución por Tiempos del Día</div>
            {_filas_tiempos_html}
        </div>
        <div class="resumen-nutri-card rn-macros">
            <div class="rn-title">🍽️ Distribución de Macronutrientes</div>
            <div class="rn-macro-row">🥩 Proteínas
                <span class="rn-macro-pill" style="background:#FFEDEC;color:#C0392B;">{gr_prot:.2f} g</span></div>
            <div class="rn-macro-row">🌾 Carbohidratos
                <span class="rn-macro-pill" style="background:#FFF3E0;color:#E67E22;">{gr_carb:.2f} g</span></div>
            <div class="rn-macro-row">🥑 Grasas
                <span class="rn-macro-pill" style="background:#EAFAEE;color:#1E5631;">{gr_gras:.2f} g</span></div>
        </div>
        <div class="resumen-nutri-card rn-rcd">
            <div class="rn-title" style="justify-content:center;color:#FFFFFF;">🎯 Requerimiento Calórico Diario</div>
            <div class="rn-rcd-value">{rcd_final:.2f}</div>
            <div style="font-size:0.85rem;opacity:0.9;">kcal / día</div>
        </div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_resumen_nutri), unsafe_allow_html=True)

    # =====================================================================================
    # SECCIÓN 2 — Interfaz de Selección de Alimentos
    # =====================================================================================
    st.markdown('<div class="selector-menu-title">🍱 ¡Personaliza tu Menú! Selecciona tus Alimentos</div>',
                unsafe_allow_html=True)
    st.markdown('<p class="selector-menu-sub">Elige una fuente de carbohidrato, proteína y grasa para cada '
                'momento del día.</p>', unsafe_allow_html=True)

    seleccion = {}
    for comida in DIETA:
        st.markdown(f'<div class="comida-momento-banner">{_ICONOS_COMIDA_D9[comida]} {comida.upper()}</div>',
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="macro-select-label carb">🌾 Carbohidrato</div>', unsafe_allow_html=True)
            carb_sel = st.selectbox(f"Carbohidrato — {comida}", list(DIETA[comida]["Carbohidrato"].keys()),
                                     key=f"c_{comida}", label_visibility="collapsed")
        with c2:
            st.markdown('<div class="macro-select-label prot">🥩 Proteína</div>', unsafe_allow_html=True)
            prot_sel = st.selectbox(f"Proteína — {comida}", list(DIETA[comida]["Proteína"].keys()),
                                     key=f"p_{comida}", label_visibility="collapsed")
        with c3:
            st.markdown('<div class="macro-select-label gras">🥑 Grasa</div>', unsafe_allow_html=True)
            gras_sel = st.selectbox(f"Grasa — {comida}", list(DIETA[comida]["Grasa"].keys()),
                                     key=f"g_{comida}", label_visibility="collapsed")
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
        filas.append(fila)
        suma_kcal_carb += fila["kcal (Carb)"]; suma_porcion_carb += fila["Porción corregida (Carb)"]
        suma_kcal_prot += fila["kcal (Prot)"]; suma_porcion_prot += fila["Porción corregida (Prot)"]
        suma_kcal_gras += fila["kcal (Gras)"]; suma_porcion_gras += fila["Porción corregida (Gras)"]

    total_general = round(suma_porcion_carb + suma_porcion_prot + suma_porcion_gras, 2)

    # =====================================================================================
    # SECCIÓN 3 — Muestra de la Dieta Tipo Menú (3 tablas de color + barra total)
    # =====================================================================================
    st.markdown('<div class="menu-titulo-grande">🍽️ MUESTRA DE TU DIETA TIPO MENÚ</div>', unsafe_allow_html=True)

    def _tabla_menu_macro(clase_css, icono, titulo, macro_key, suma_kcal, suma_porcion):
        """Construye una de las 3 tablas de color (Carbohidrato / Proteína / Grasa) con fila TOTAL."""
        _prefijo = {"Carbohidrato": "Carb", "Proteína": "Prot", "Grasa": "Gras"}[macro_key]
        filas_html = ""
        for f in filas:
            filas_html += f"""
            <tr>
                <td class="dm-momento">{_ICONOS_COMIDA_D9[f['Momento']]} {f['Momento']}</td>
                <td>{f[macro_key]}</td>
                <td>{f[f'kcal ({_prefijo})']} kcal</td>
                <td>{f[f'Porción corregida ({_prefijo})']:.1f} kcal</td>
                <td>{f[f'Gramos ({_prefijo})']:.1f} g</td>
            </tr>"""
        filas_html += f"""
            <tr class="dm-total">
                <td class="dm-momento" colspan="2">TOTAL</td>
                <td>{suma_kcal:.0f} kcal</td>
                <td>{suma_porcion:.1f} kcal</td>
                <td>—</td>
            </tr>"""
        html = f"""
        <div class="dieta-menu-wrap {clase_css}">
        <table class="dieta-menu-table">
            <thead>
            <tr><th style="text-align:left;">Momento</th><th>{icono} Alimento ({titulo})</th>
                <th>Kcal</th><th>Porción Corregida</th><th>Gramos Finales</th></tr>
            </thead>
            <tbody>
            {filas_html}
            </tbody>
        </table>
        </div>
        """
        st.markdown(_html_sin_lineas_vacias(html), unsafe_allow_html=True)

    _tabla_menu_macro("carb", "🌾", "Carbohidrato", "Carbohidrato", suma_kcal_carb, suma_porcion_carb)
    _tabla_menu_macro("prot", "🥩", "Proteína", "Proteína", suma_kcal_prot, suma_porcion_prot)
    _tabla_menu_macro("gras", "🥑", "Grasa", "Grasa", suma_kcal_gras, suma_porcion_gras)

    # ---- Barra final destacada: suma total = RCD ----
    _diferencia_total = abs(total_general - rcd_final)
    _check_txt = ("✅ ¡Coincide exactamente con tu RCD!" if _diferencia_total < 1
                  else f"⚠️ Diferencia de {_diferencia_total:.1f} kcal respecto a tu RCD")
    _html_barra_total = f"""
    <div class="dieta-total-bar">
        <div class="dt-label">🌾 Carbohidratos + 🥩 Proteínas + 🥑 Grasas</div>
        <div class="dt-formula">{suma_porcion_carb:.1f} kcal + {suma_porcion_prot:.1f} kcal + {suma_porcion_gras:.1f} kcal</div>
        <div class="dt-value">= {total_general:.1f} kcal</div>
        <div style="font-size:0.9rem;opacity:0.92;">Este total equivale a tu <b>TOTAL DE CALORÍAS DIARIAS (RCD)</b></div>
        <div class="dt-check">{_check_txt}</div>
    </div>
    """
    st.markdown(_html_sin_lineas_vacias(_html_barra_total), unsafe_allow_html=True)

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

# ---------------------------------------------------------------------------------------
elif hoja_activa == "10.-CLIMA CHICLAYO":
    hoja_header(10, subtitulo="Sí, aunque el cambio suele ser pequeño: así ajusta la app tu gasto calórico "
                               "según el clima cálido de tu ciudad.", tip="☀️ Ajuste de −5%")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "RCD_Ajustado = TMB × Factor_Actividad × 0.95",
        referencia="Corrección Térmica de Clima Cálido — factor 5% por temperatura ambiental promedio")}</div>""",
        unsafe_allow_html=True)

    _ajuste_kcal = rcd - rcd_chiclayo

    # --- 1. ¿El clima influye en las calorías que gasta tu cuerpo? ---------------------
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # --- 2. Comparación visual: Antes → Ajuste → Resultado -----------------------------
    st.markdown("#### 📊 De tu cálculo general al resultado para Chiclayo")
    st.markdown(f"""
    <div class="cp5-glass-flow">
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">🌍 Cálculo general</div>
            <div class="cp5-flow-value">{rcd:.0f} kcal</div>
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
            <div class="cp5-flow-value" style="color:#E67E22;">{rcd_chiclayo:.0f} kcal</div>
            <div class="cp5-flow-legend">Tu gasto energético ya ajustado al clima. ☀️</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Este cálculo usa el RCD base de la Hoja 4 (antes del ajuste por objetivo).")

    # --- 3. ¿Qué significa esto? + ¿Debo comer menos? -----------------------------------
    col_signif, col_duda = st.columns(2)
    with col_signif:
        st.markdown("""
        <div class="bento-card" style="border-left:5px solid #FFB300;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#B06000;">🤔 ¿Qué significa esto?</p>
        <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
        Debido al clima cálido de Chiclayo, tu cuerpo gasta ligeramente menos energía para mantener
        su temperatura. Por eso el cálculo ajusta aproximadamente un <b>5%</b> de tu gasto energético diario.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_duda:
        st.markdown("""
        <div class="bento-card" style="border-left:5px solid #34C759;">
        <p style="margin:0 0 6px 0;font-weight:800;color:#137333;">❓ ¿Debo comer menos porque hace calor?</p>
        <p style="margin:0;color:#3C3C43;line-height:1.5;font-size:0.92rem;">
        <b>No necesariamente.</b> Este ajuste solo mejora la precisión del cálculo. La diferencia suele ser
        pequeña y no significa que debas dejar de alimentarte ni hacer dietas por vivir en un clima cálido.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # --- 4. ¿Cómo aprovechar este conocimiento? — tres tarjetas -------------------------
    st.markdown("#### 🌴 ¿Cómo aprovechar este conocimiento?")
    col_h, col_c, col_a = st.columns(3)
    _tarjetas_clima = [
        (col_h, "#5AC8FA", "#E9F8FF", "💧", "Mantente hidratado",
         "Las altas temperaturas aumentan la pérdida de agua mediante el sudor."),
        (col_c, "#34C759", "#EAFAEE", "🥗", "Prefiere comidas ligeras",
         "Las frutas y verduras ayudan a mantener una buena hidratación."),
        (col_a, "#FF9500", "#FFF3E5", "🚶", "Sigue activo",
         "Aunque haga calor, caminar y hacer actividad física sigue siendo importante para tu salud."),
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

    # --- 5. ¿Cómo responde tu cuerpo cuando hace calor? — mini infografía ---------------
    st.markdown("#### ☀️ ¿Cómo responde tu cuerpo cuando hace calor?")
    _pasos_calor = [
        ("#FFB300", "☀️", "Hace más calor", "La temperatura ambiental sube en tu entorno."),
        ("#5AC8FA", "💧", "Sudas más", "Tu piel libera calor a través del sudor."),
        ("#FF3B30", "❤️", "Tu cuerpo trabaja para mantener su temperatura", "El organismo regula su termostato interno."),
        ("#34C759", "🍉", "Necesitas hidratarte correctamente", "Repones el agua que pierdes con el calor."),
        ("#FF9500", "📊", "El cálculo ajusta ligeramente tu gasto", "Aproximadamente un 5% menos de energía diaria."),
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

    # --- 6. Base científica ---------------------------------------------------------------
    st.markdown("""
    <div style="background:#FFF6E0;border-radius:18px;padding:16px 20px;margin-bottom:10px;
    border-left:5px solid #FFB300;">
    <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">📖 Base científica</p>
    <p style="margin:0;color:#5C4A1E;font-size:0.9rem;line-height:1.5;">
    Este cálculo utiliza información sobre adaptación fisiológica al clima cálido descrita por organismos
    internacionales como la FAO y estudios sobre gasto energético humano.</p>
    </div>
    """, unsafe_allow_html=True)
    recursos_externos(10, [
        ("📄 Ver referencias (FAO/OMS/UNU)", "https://www.fao.org/"),
        ("☀️ Clima de Chiclayo (Senamhi)", "https://www.senamhi.gob.pe/"),
    ])
    caja_util("Vivir en un lugar caluroso como Chiclayo también afecta cuántas calorías gasta tu cuerpo. Este "
              "dato extra te da una versión más realista y localizada de tu gasto calórico, pensada "
              "específicamente para nuestra región. ☀️🌴",
              emoji="🌡️", color="#FFF8E1", borde="#F9A825")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "11.-APORTE 1: EMBARAZO":
    hoja_header(11, subtitulo="El embarazo cambia las necesidades de energía del cuerpo. Aquí calculamos "
                               "cuántas calorías necesitas según tu etapa de gestación.", tip="🤰 Por trimestre")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "TMB(mujer) + ajuste por trimestre: 1er trim. +0 kcal · 2do trim. +340 kcal/día · 3er trim. +452 kcal/día",
        autor="MD Mifflin, ST St Jeor et al. (1990)",
        referencia="Ecuación de Mifflin-St Jeor + ajuste gestacional")}</div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#F8ECFB;border-radius:16px;padding:12px 18px;margin-bottom:14px;
    border-left:5px solid #BA68C8;font-size:0.86rem;color:#5C2A6B;">
    📌 Esta calculadora está pensada exclusivamente para mujeres embarazadas y utiliza recomendaciones
    específicas para esta etapa.</div>
    """, unsafe_allow_html=True)

    st.markdown("##### 👩 Tus datos")
    nombre_emb = st.text_input("Nombre:", "")
    c1, c2, c3 = st.columns(3)
    with c1:
        edad_emb = st.number_input("Edad:", min_value=10, max_value=60, value=27, step=1, key="edad_emb")
    with c2:
        peso_emb = st.number_input("Peso (kg):", min_value=30.0, max_value=PESO_MAX["Mujer"], value=68.0, step=0.1, key="peso_emb")
    with c3:
        altura_emb = st.number_input("Altura (cm):", min_value=100, max_value=ESTATURA_MAX["Mujer"], value=162, step=1, key="altura_emb")
    trimestre = st.selectbox("🤰 Selecciona tu trimestre:", ["Primer trimestre", "Segundo trimestre", "Tercer trimestre"])
    ajuste_trim = {"Primer trimestre": 0, "Segundo trimestre": 340, "Tercer trimestre": 452}[trimestre]

    tmb_base_emb = (10 * peso_emb) + (6.25 * altura_emb) - (5 * edad_emb) - 161
    tmb_emb = tmb_base_emb + ajuste_trim
    _nombre_disp = nombre_emb.strip() if nombre_emb.strip() else "ti"

    # --- Flujo visual: datos → trimestre → TMB → aporte → resultado ---------------------
    st.markdown("#### 🔎 De tus datos a tu resultado")
    _pasos_emb = [
        ("#5AC8FA", "👩", "Datos ingresados", f"{edad_emb:.0f} años · {peso_emb:.0f} kg · {altura_emb:.0f} cm"),
        ("#BA68C8", "🤰", "Trimestre", trimestre),
        ("#FF9500", "🔥", "TMB calculada", f"{tmb_base_emb:.0f} kcal/día"),
        ("#34C759", "🍽️", "Calorías adicionales", f"+{ajuste_trim} kcal"),
        ("#FF2D55", "❤️", "Resultado recomendado", f"{tmb_emb:.0f} kcal/día"),
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
    st.markdown(f"""
    <div class="bento-card" style="border-left:5px solid #FF2D55;margin-top:16px;">
    <p style="margin:0 0 6px 0;font-weight:800;color:#C2185B;">🤔 ¿Qué significa este resultado?</p>
    <p style="margin:0;color:#3C3C43;line-height:1.55;font-size:0.92rem;">
    Tu cuerpo necesita aproximadamente <b>{tmb_emb:.0f} kcal al día</b> para mantener sus funciones vitales
    (respirar, mantener la temperatura corporal, funcionamiento de órganos, etc.), sin considerar la
    actividad física.</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # --- ¿Por qué cambia según el trimestre? — tres tarjetas -----------------------------
    st.markdown("#### 🤰 ¿Por qué cambia según el trimestre?")
    _tri_data = [
        ("Primer trimestre", "#4CAF50", "#EAFAEE", "🌱", "Primer trimestre",
         "No suelen necesitarse calorías adicionales. Lo más importante es mantener una alimentación "
         "equilibrada y cubrir todos los nutrientes esenciales."),
        ("Segundo trimestre", "#FF9500", "#FFF3E5", "👶", "Segundo trimestre",
         "El bebé comienza un crecimiento más rápido. Generalmente se requieren alrededor de "
         "340 kcal adicionales al día."),
        ("Tercer trimestre", "#FF2D55", "#FFEBF0", "❤️", "Tercer trimestre",
         "Es la etapa de mayor crecimiento fetal. Las necesidades energéticas aumentan aproximadamente "
         "452 kcal por día."),
    ]
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
            {'<p style="margin:8px 0 0 0;font-weight:800;color:'+_borde+';font-size:0.72rem;">✓ TU ETAPA ACTUAL</p>' if _sel else ''}
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # --- ¿Por qué aumentan las calorías? — mini infografía -------------------------------
    st.markdown("#### 🔥 ¿Por qué aumentan las calorías?")
    _pasos_porque = [
        ("#BA68C8", "🤰", "El bebé crece"),
        ("#FF9500", "🦴", "Se forman nuevos tejidos"),
        ("#FF2D55", "❤️", "Trabaja más el organismo"),
        ("#FF3B30", "🔥", "Se necesita más energía"),
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
    st.markdown("#### 📊 Antes y después del ajuste")
    st.markdown(f"""
    <div class="cp5-glass-flow">
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">🔥 TMB Base</div>
            <div class="cp5-flow-value">{tmb_base_emb:.0f} kcal</div>
            <div class="cp5-flow-legend">Tu gasto energético sin ajuste gestacional.</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card" style="background:rgba(186,104,200,0.10);border-color:rgba(186,104,200,0.35);">
            <div class="cp5-flow-label">👶 Aporte por embarazo</div>
            <div class="cp5-flow-value" style="color:#8E24AA;">+{ajuste_trim} kcal</div>
            <div class="cp5-flow-legend">Energía extra para {trimestre.lower()}.</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card" style="background:rgba(255,45,85,0.12);border-color:rgba(255,45,85,0.4);">
            <div class="cp5-flow-label">❤️ Resultado para {_nombre_disp}</div>
            <div class="cp5-flow-value" style="color:#C2185B;">{tmb_emb:.0f} kcal</div>
            <div class="cp5-flow-legend">Tu gasto energético recomendado hoy.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 🍽 Recuerda: prioriza calidad, no solo cantidad ----------------------------------
    st.markdown("#### 🍽️ Recuerda")
    st.markdown("""
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
    """, unsafe_allow_html=True)

    st.write("")

    # --- ¿Qué puedes hacer desde hoy? -----------------------------------------------------
    st.markdown("#### ✅ ¿Qué puedes hacer desde hoy?")
    _acciones_emb = [
        ("#0277BD", "#E9F8FF", "🥛", "Consumir lácteos"),
        ("#137333", "#EAFAEE", "🥬", "Incluir verduras diariamente"),
        ("#1976D2", "#E3F2FD", "🐟", "Proteínas de buena calidad"),
        ("#00B8D9", "#E1FBF9", "💧", "Mantener buena hidratación"),
        ("#FF9500", "#FFF3E5", "🚶", "Actividad física autorizada"),
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
    st.markdown("""
    <div style="background:#FFF3E5;border-radius:18px;padding:16px 20px;border-left:5px solid #FF9500;">
    <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">⚠️ Importante</p>
    <p style="margin:0;color:#5C4A1E;font-size:0.88rem;line-height:1.5;">
    Las necesidades nutricionales durante el embarazo varían entre cada mujer. Este cálculo es una
    estimación educativa y no reemplaza la evaluación realizada por un obstetra o nutricionista.</p>
    </div>
    """, unsafe_allow_html=True)

    caja_util("Durante el embarazo el cuerpo necesita energía extra para que el bebé se desarrolle sanamente. "
              "Esta calculadora te dice cuántas calorías adicionales necesitas según el trimestre en que estás, "
              "sin tener que adivinarlo ni arriesgar tu nutrición ni la de tu bebé. 🤰💕",
              emoji="👶", color="#F8ECFB", borde="#BA68C8")

# ---------------------------------------------------------------------------------------
elif hoja_activa == "12.-APORTE 2: CAFEÍNA":
    hoja_header(12, subtitulo="Dormir bien también ayuda a cuidar tu alimentación. La cafeína puede permanecer "
                               "varias horas en el organismo. Esta herramienta calcula hasta qué hora puedes "
                               "consumir café sin afectar tu descanso.", tip="🌙 −8 horas antes de dormir")
    st.markdown(f"""<div class="formula-badge-row">{formula_badge(
        "Hora_Límite_Cafeína = Hora_Dormir − 8 horas",
        referencia="Principio de Vida Media de la Cafeína (FDA / AASM)")}</div>""", unsafe_allow_html=True)

    # --- PASO 1: ¿A qué hora sueles dormir? (selector amigable AM/PM) --------------------
    st.markdown("##### ① 🛏️ ¿A qué hora sueles dormir?")
    _opciones_hora, _t_cursor = [], datetime.strptime("19:00", "%H:%M")
    for _ in range(15):
        _opciones_hora.append(_t_cursor)
        _t_cursor += timedelta(minutes=30)
    _etiquetas_hora = [f"🌙 {t.strftime('%I:%M %p').lstrip('0')}" for t in _opciones_hora]
    _idx_default = next((i for i, t in enumerate(_opciones_hora) if t.strftime("%H:%M") == "22:00"), 6)
    _sel_hora = st.selectbox("Hora de dormir:", _etiquetas_hora, index=_idx_default, label_visibility="collapsed")
    hora_dormir = _opciones_hora[_etiquetas_hora.index(_sel_hora)].time()
    dt_dormir = datetime.combine(datetime.today(), hora_dormir)
    dt_limite = dt_dormir - timedelta(hours=8)
    _fmt = lambda dt: dt.strftime('%I:%M %p').lstrip('0')

    st.write("")

    # --- PASO 2: ✅ Tu resultado — bloque grande con las 3 preguntas clave ----------------
    st.markdown("##### ② ✅ Tu resultado")
    st.markdown(f"""
    <div class="cp5-glass-flow">
        <div class="cp5-flow-card" style="background:rgba(27,42,74,0.08);border-color:rgba(27,42,74,0.3);">
            <div class="cp5-flow-label">🛏️ Hora para dormir</div>
            <div class="cp5-flow-value" style="color:#1B2A4A;">{_fmt(dt_dormir)}</div>
            <div class="cp5-flow-legend">La hora en la que sueles acostarte.</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card" style="background:rgba(255,179,0,0.14);border-color:rgba(255,179,0,0.4);">
            <div class="cp5-flow-label">☕ Último café recomendado</div>
            <div class="cp5-flow-value" style="color:#B06000;">{_fmt(dt_limite)}</div>
            <div class="cp5-flow-legend">Después de esa hora, la cafeína aún podría estar activa al dormir.</div>
        </div>
        <div class="cp5-flow-arrow">→</div>
        <div class="cp5-flow-card">
            <div class="cp5-flow-label">⏱️ Diferencia recomendada</div>
            <div class="cp5-flow-value">8 horas</div>
            <div class="cp5-flow-legend">Tiempo mínimo entre tu última cafeína y dormir.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # --- PASO 3: Línea de tiempo visual ---------------------------------------------------
    st.markdown("##### ③ 🗓️ Tu día, en una línea de tiempo")
    _linea_tiempo = [
        ("#FFB300", "☀️", "Mañana", "8:00 AM"),
        ("#FF9500", "☀️", "Mediodía", "12:00 PM"),
        ("#B06000", "☕", "Último café", _fmt(dt_limite)),
        ("#FF6B35", "🌇", "Tarde", "6:00 PM"),
        ("#1B2A4A", "🌙", "Dormir", _fmt(dt_dormir)),
    ]
    _html_lt = ['<div style="max-width:520px;margin:0 auto;">']
    for _i, (_bc, _em, _tt, _hh) in enumerate(_linea_tiempo):
        _es_cafe = _tt == "Último café"
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
    st.markdown("##### ④ 🤔 ¿Por qué ocurre esto?")
    col_p1, col_p2, col_p3 = st.columns(3)
    _porques = [
        (col_p1, "#5856D6", "#ECEBFC", "🧠", "La cafeína tarda varias horas en desaparecer del cuerpo."),
        (col_p2, "#1B2A4A", "#E9ECF5", "😴", "Si consumes café muy tarde puede dificultar el sueño."),
        (col_p3, "#34C759", "#EAFAEE", "🍎", "Dormir bien ayuda a controlar el apetito y favorece una alimentación saludable."),
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

    # --- PASO 5: ¿Qué cambia si modifico mi hora de dormir? — mini tabla -----------------
    st.markdown("##### ⑤ 🔄 ¿Qué cambia si modifico mi hora de dormir?")
    _tabla_ejemplos = [("9:00 PM", "1:00 PM"), ("10:00 PM", "2:00 PM"),
                        ("11:00 PM", "3:00 PM"), ("12:00 AM", "4:00 PM")]
    _hora_actual_txt = _fmt(dt_dormir)
    _filas_html = []
    for _dormir_txt, _cafe_txt in _tabla_ejemplos:
        _es_actual = _dormir_txt == _hora_actual_txt
        _bg = "background:rgba(255,179,0,0.18);font-weight:800;" if _es_actual else ""
        _filas_html.append(f"""<tr style="{_bg}">
            <td style="padding:10px 16px;border-bottom:1px solid #F0E9DC;">🛏️ {_dormir_txt}</td>
            <td style="padding:10px 16px;border-bottom:1px solid #F0E9DC;">☕ {_cafe_txt}</td>
            </tr>""")
    st.markdown(_html_sin_lineas_vacias(f"""
    <div style="background:#FFFFFF;border-radius:18px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,0.05);
    border:1px solid rgba(27,42,74,0.08);">
    <table style="width:100%;border-collapse:collapse;font-size:0.88rem;color:#17301F;">
    <thead><tr style="background:#1B2A4A;color:#FFFFFF;">
    <th style="padding:10px 16px;text-align:left;">Si duermes...</th>
    <th style="padding:10px 16px;text-align:left;">Último café recomendado</th>
    </tr></thead>
    <tbody>{"".join(_filas_html)}</tbody>
    </table></div>
    """), unsafe_allow_html=True)

    st.write("")

    # --- PASO 6: 💡 Consejo práctico -------------------------------------------------------
    st.markdown("""
    <div style="background:#FFF6E0;border-radius:18px;padding:16px 20px;border-left:5px solid #FFB300;">
    <p style="margin:0 0 4px 0;font-weight:800;color:#B06000;">💡 Consejo</p>
    <p style="margin:0;color:#5C4A1E;font-size:0.88rem;line-height:1.5;">
    Si un día deseas tomar café más tarde de lo habitual, intenta reducir la cantidad o elegir una bebida
    con menos cafeína para disminuir su efecto sobre el sueño.</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    recursos_externos(12, [
        ("☕ Cafeína y sueño (Sleep Foundation)", "https://www.sleepfoundation.org/nutrition/caffeine-and-sleep"),
    ])
    caja_util("¿Sabías que dormir mal te da más hambre y más ganas de comer dulce al día siguiente? Esta "
              "herramienta te dice hasta qué hora puedes tomar café sin arruinar tu descanso — y un buen "
              "descanso es tan importante para tu salud como una buena alimentación. ☕😴",
              emoji="🌙", color="#FFF4DE", borde="#1B2A4A")

# ---------------------------------------------------------------------------------------
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
    r1.metric("Peso", f"{peso:.2f} kg")
    r2.metric("Estatura", f"{estatura} cm")
    with r3:
        if etapa in ["Niñez", "Adolescencia"]:
            tarjeta_categoria_imc(f"IMC: {imc}", _categoria_imc_usuario)
        else:
            tarjeta_categoria_imc(f"IMC: {imc}", _categoria_imc_usuario)

    st.markdown("#### 🔥 Requerimiento energético")
    r4, r5, r6 = st.columns(3)
    r4.metric("TMB", f"{tmb:.2f} kcal/día")
    r5.metric("RCD (gasto diario)", f"{rcd:.2f} kcal/día")
    r6.metric("Meta calórica (objetivo)", f"{rcd_final:.2f} kcal/día")

    st.markdown("#### 🍽️ Macronutrientes recomendados")
    r7, r8, r9 = st.columns(3)
    r7.metric("Proteínas", f"{gr_prot:.2f} g")
    r8.metric("Carbohidratos", f"{gr_carb:.2f} g")
    r9.metric("Grasas", f"{gr_gras:.2f} g")

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
        with rc1: tarjeta_semaforo("Hemoglobina", f"{hemo} g/dL", _cat_hemo_r, valor_num=hemo, etapa=etapa, genero=genero)
        with rc2: tarjeta_semaforo("Triglicéridos", f"{trigli} mg/dL", _cat_trigli_r, valor_num=trigli)
        with rc3: tarjeta_semaforo("Glucosa", f"{gluco} mg/dL", _cat_gluco_r, valor_num=gluco)
        with rc4: tarjeta_semaforo("Colesterol", f"{coles} mg/dL", _cat_coles_r, valor_num=coles)
        with rc5: tarjeta_semaforo("Hierro", f"{hierro} µg/dL", _cat_hierro_r, valor_num=hierro, etapa=etapa, genero=genero)
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

# =========================================================================================
# PIE DE PÁGINA — navegación "Anterior / Siguiente" entre secciones
# (complementa a las píldoras del sidebar; conserva el estado ya ingresado por el usuario)
# =========================================================================================
st.markdown("---")
_idx_actual = OPCIONES_HOJAS.index(hoja_activa)
col_prev, col_mid, col_next = st.columns([1, 2, 1])
with col_prev:
    if _idx_actual > 0:
        if st.button("← Sección Anterior", use_container_width=True, key="btn_anterior_footer"):
            st.session_state["hoja_activa"] = OPCIONES_HOJAS[_idx_actual - 1]
            st.rerun()
with col_mid:
    st.markdown(
        f"<div style='text-align:center;color:#8E8E93;font-size:0.85rem;padding-top:10px;'>"
        f"Sección {_idx_actual + 1} de {len(OPCIONES_HOJAS)}"
        f"</div>", unsafe_allow_html=True
    )
with col_next:
    if _idx_actual < len(OPCIONES_HOJAS) - 1:
        if st.button("Siguiente Sección →", use_container_width=True, type="primary", key="btn_siguiente_footer"):
            st.session_state["hoja_activa"] = OPCIONES_HOJAS[_idx_actual + 1]
            st.rerun()

st.markdown("---")
st.caption("Aplicación desarrollada en Streamlit — réplica fiel del Excel 'Grupo n°4 VER.2' (Proyecto Sana "
           "Alimentación) para el proyecto de tesis escolar sobre salud pública en Lambayeque, Grupo N°04. "
           "🔒 Ningún dato ingresado se almacena: toda la información vive solo en tu sesión actual.")
