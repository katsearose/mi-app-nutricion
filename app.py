import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote

st.set_page_config(page_title="Proyecto Sana Alimentación", layout="wide", page_icon="🍎")

# =========================================================================================
# ESTILOS Y AYUDAS VISUALES
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
div[data-testid="stMetricValue"] { color: #2e7d32; }
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

def clasif_percentil(imc, edad, genero):
    tabla = PERCENTIL_HOMBRE if genero == "Hombre" else PERCENTIL_MUJER
    if edad not in tabla:
        return None, "Edad fuera de tabla (2-20 años)"
    p5, p50, p85, p95 = tabla[edad]
    if imc < p5: percentil, cat = "< 5", "Bajo Peso"
    elif imc < p50: percentil, cat = "50", "Peso Saludable"
    elif imc < p85: percentil, cat = "85", "Sobrepeso"
    else: percentil, cat = "95", "Obesidad"
    return percentil, cat

def clasif_imc_adulto(imc):
    if imc < 18.5: return "Bajo Peso"
    elif imc <= 24.9: return "Peso Saludable"
    elif imc <= 29.9: return "Sobrepeso"
    elif imc <= 34.9: return "Obesidad Clase 1"
    elif imc <= 39.9: return "Obesidad Clase 2"
    else: return "Obesidad Clase 3"

# =========================================================================================
# ENCABEZADO
# =========================================================================================
st.markdown("""
<div class="big-title">
<h1>🥦 Proyecto Sana Alimentación</h1>
<p style="margin-bottom:0;">C.E.P. "Santa María Reina" — 5° "C" Secundaria — Grupo N°04 🌱</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<p class="frase-motivadora">🍎 "Comer bien no es una dieta, es un acto de amor hacia ti mismo" 💚</p>', unsafe_allow_html=True)
st.caption("Una réplica interactiva del Excel oficial del proyecto, explicada paso a paso para que cualquier persona la entienda 😊")
try:
    st.image("https://source.unsplash.com/1200x260/?healthy,food,fruits", use_container_width=True)
except Exception:
    pass
st.markdown("---")

# =========================================================================================
# SIDEBAR — HOJA 0.-DATOS
# =========================================================================================
st.sidebar.header("📝 ¡Introduce tus datos!")
peso = st.sidebar.number_input("Peso (en kg):", min_value=1.0, value=75.0, step=0.1)
edad = st.sidebar.number_input("Edad (en años):", min_value=1, value=9, step=1)
estatura = st.sidebar.number_input("Estatura (en cm):", min_value=30, value=168, step=1)
genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"], index=1)
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
    ajuste_bajar = 0.0
    ajuste_subir = 0.0

etapa = st.sidebar.selectbox("Etapa:", ["Niñez", "Adolescencia", "Adultez", "Vejez"], index=1)

st.sidebar.markdown("---")
st.sidebar.info("ℹ️ **¿Cómo saber mi actividad física?**\n\n"
                 "**Sedentaria:** solo actividades de la vida diaria (estudiar, dormir).\n\n"
                 "**Ligero:** ejercicio 1-3 veces por semana.\n\n"
                 "**Moderada:** ejercicio 3-5 veces por semana.\n\n"
                 "**Intensa:** ejercicio diario de alta intensidad o deportista de competencia.")

st.sidebar.markdown("---")
st.sidebar.subheader("Datos adicionales (Hoja 1 - Examen médico)")
hemo = st.sidebar.number_input("Hemoglobina (g/dL):", min_value=0.0, value=0.0, step=0.1)
trigli = st.sidebar.number_input("Triglicéridos (mg/dL):", min_value=0.0, value=0.0, step=1.0)
gluco = st.sidebar.number_input("Glucosa (mg/dL):", min_value=0.0, value=0.0, step=1.0)
coles = st.sidebar.number_input("Colesterol (mg/dL):", min_value=0.0, value=0.0, step=1.0)
hierro = st.sidebar.number_input("Hierro (µg/dL):", min_value=0.0, value=0.0, step=1.0)

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

# Hoja 5: ajuste según objetivo (usa el % elegido en el sidebar, igual que T22/V22 del Excel)
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

# Hoja 6: Macronutrientes (sobre las calorías recomendadas del objetivo, NO sobre el RCD base)
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

# Hoja 10: Gasto energético ajustado al clima de Chiclayo (independiente, usa el RCD BASE, no el ajustado por objetivo)
rcd_chiclayo = rcd * 0.95

# =========================================================================================
# NAVEGACIÓN
# =========================================================================================
st.subheader("📋 Navegación por Hojas del Sistema (idéntica al Excel)")
tabs = st.tabs([
    "0.-DATOS", "1.-EXAMEN MÉDICO", "2.-IMC Y PERCENTIL", "3.-TMB", "4.-RCD",
    "5.-OBJETIVO", "6.-MACRONUTRIENTES", "7.-PORCIONES", "8.-FATSECRET",
    "9.-DIETA", "10.-CLIMA CHICLAYO", "11.-APORTE 1: EMBARAZO", "12.-APORTE 2: CAFEÍNA"
])

# ---------------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("### Hoja 0: ¡Introduce tus datos!")
    df0 = pd.DataFrame({
        "Variable": ["Peso", "Edad", "Estatura", "Estatura (m)", "Género", "Actividad física",
                     "Objetivo", "Ajuste (bajar)", "Ajuste (subir)", "Etapa"],
        "Valor": [f"{peso} kg", f"{edad} años", f"{estatura} cm", f"{estatura_m}", genero, actividad,
                  objetivo, f"{ajuste_bajar*100:.0f}%", f"{ajuste_subir*100:.0f}%", etapa]
    })
    st.table(df0)
    caja_util("Aquí registras tus datos básicos una sola vez, y toda la app se ajusta automáticamente a ti: "
              "desde tus calorías diarias hasta tu plan de comidas. ¡Es el punto de partida de todo tu plan personalizado! 🌟",
              emoji="📝", color="#E3F2FD", borde="#2196F3")

# ---------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("### Hoja 1: Examen Médico de Sangre")
    st.caption("Categoriza tus datos según su nivel correspondiente, exactamente como las fórmulas SI anidadas del Excel.")
    df_examen = pd.DataFrame({
        "Parámetro": ["Hemoglobina", "Triglicéridos", "Glucosa", "Colesterol", "Hierro"],
        "Valor": [f"{hemo} g/dL", f"{trigli} mg/dL", f"{gluco} mg/dL", f"{coles} mg/dL", f"{hierro} µg/dL"],
        "Resultado obtenido": [
            clasif_hemoglobina(hemo, etapa, genero),
            clasif_trigliceridos(trigli),
            clasif_glucosa(gluco),
            clasif_colesterol(coles),
            clasif_hierro(hierro, etapa, genero)
        ]
    })
    st.table(df_examen)

    with st.expander("📊 Ver tablas de referencia clínica completas"):
        st.markdown("**Hemoglobina**")
        st.table(pd.DataFrame({
            "Grupo Poblacional": ["Niños 5–11 años", "Adolescentes", "Mujeres", "Hombres", "Mujeres embarazadas"],
            "Normal": ["≥ 11,5 g/dL", "≥ 12,0 g/dL", "≥ 12,0 g/dL", "≥ 13,0 g/dL", "≥ 11,0 g/dL"],
            "Anemia leve": ["11,0 – 11,4", "11,0 – 11,9", "11,0 – 11,9", "12,0 – 12,9", "10,0 – 10,9"],
            "Anemia moderada": ["8,0 – 10,9", "8,0 – 10,9", "8,0 – 10,9", "8,0 – 10,9", "7,0 – 9,9"],
            "Anemia grave": ["< 8,0", "< 8,0", "< 8,0", "< 8,0", "< 7,0"]
        }))
        st.markdown("**Hierro**")
        st.table(pd.DataFrame({
            "Grupo poblacional": ["Niños y adolescentes", "Mujeres", "Hombres"],
            "Bajo": ["< 50", "< 50", "< 65"], "Normal": ["50-120", "50-170", "65-175"],
            "Alto": ["> 120", "> 170", "> 175"]
        }))
        st.markdown("**Triglicéridos / Glucosa / Colesterol**")
        st.table(pd.DataFrame({
            "Triglicéridos": ["Normal < 150", "Límite alto 150–199", "Alto 200–499", "Muy alto ≥ 500"],
            "Glucosa": ["Hipoglucemia < 70", "Normal 70–99", "Prediabetes 100–125", "Diabetes ≥ 126"],
            "Colesterol": ["Deseable < 200", "Límite alto 200–239", "Alto ≥ 240", ""]
        }))
    st.warning("⚠️ Nota de fidelidad al Excel: la fórmula original de Hemoglobina no contempla el caso "
               "'Mujer' en etapa Adultez/Vejez, por lo que en ese caso el sistema (igual que el Excel) "
               "devuelve **'Revisa Datos'**.")
    caja_util("Un análisis de sangre trae puros números y siglas difíciles de entender (¿12.5 g/dL es bueno o malo?). "
              "Esta hoja traduce esos números a un lenguaje simple: 'Normal', 'Anemia leve', 'Alto', etc. "
              "Así sabes de un vistazo si algún valor necesita atención médica. 🩺❤️",
              emoji="🩸", color="#FFEBEE", borde="#E53935")

# ---------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("### Hoja 2: Índice de Masa Corporal y Percentil")
    st.caption("El IMC sirve para saber si una persona tiene un peso saludable según su altura y peso. "
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

    st.markdown("**Categorías generales de IMC**")
    st.table(pd.DataFrame({
        "Clasificación": ["Bajo Peso", "Peso Saludable", "Sobrepeso", "Obesidad", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3 (Severa)"],
        "Rango de IMC": ["Menos de 18.5", "18.5 a 24.9", "25 a 29.9", "30 o más", "30 a 34.9", "35 a 39.9", "40 o más"]
    }))
    with st.expander("📊 Ver tabla completa de percentiles (edad 2-20 años)"):
        cm, ch = st.columns(2)
        with cm:
            st.markdown("**Mujer**")
            st.dataframe(pd.DataFrame(PERCENTIL_MUJER, index=["P5 (Bajo Peso)", "P50 (Saludable)", "P85 (Sobrepeso)", "P95 (Obesidad)"]).T)
        with ch:
            st.markdown("**Hombre**")
            st.dataframe(pd.DataFrame(PERCENTIL_HOMBRE, index=["P5 (Bajo Peso)", "P50 (Saludable)", "P85 (Sobrepeso)", "P95 (Obesidad)"]).T)
    caja_util("El IMC te dice, de forma simple, si tu peso está en un rango saludable para tu altura. "
              "En niños y adolescentes se usa además el 'percentil', que te compara con otros chicos de tu misma "
              "edad y sexo — porque el cuerpo de un niño en crecimiento no se mide igual que el de un adulto. 📏⚖️",
              emoji="⚖️", color="#F3E5F5", borde="#8E24AA")

# ---------------------------------------------------------------------------------------
with tabs[3]:
    st.markdown("### Hoja 3: Tasa Metabólica Basal (TMB)")
    st.caption("Fórmula de Mifflin-St Jeor. Biológicamente, los hombres suelen tener más masa muscular y "
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
    st.markdown("### Hoja 4: Requerimiento Calórico Diario (RCD)")
    st.latex(r"RCD = TMB \times Factor\ de\ Actividad")
    st.table(pd.DataFrame({
        "Actividad": ["Sedentaria", "Ligero", "Moderada", "Intensa"],
        "Hombres": [1.2, 1.55, 1.8, 2.1],
        "Mujeres": [1.2, 1.56, 1.64, 1.82]
    }))
    st.metric(f"Factor aplicado ({actividad}, {genero})", factor)
    st.metric("Resultado RCD", f"{rcd:.0f} kcal/día")
    caja_util("Este es el número más importante de toda la app: son las calorías reales que gastas en un día "
              "normal, sumando tu TMB (Hoja 3) más el movimiento que haces según tu nivel de actividad. "
              "Es tu 'punto de equilibrio' calórico. 🏃‍♀️🔥",
              emoji="🔥", color="#E8F5E9", borde="#43A047")

# ---------------------------------------------------------------------------------------
with tabs[5]:
    st.markdown("### Hoja 5: Cálculo para Subir, Mantener o Bajar el Peso")
    st.info("A diferencia de los adultos, el cuerpo de los menores necesita energía constante no solo para "
            "moverse, sino para el desarrollo de órganos y huesos. Por ello, cualquier ajuste calórico debe "
            "ser controlado para jamás arriesgar su correcto desarrollo biológico.")
    st.table(pd.DataFrame({
        "Objetivo nutricional": [objetivo],
        "Ajuste calórico aplicado": [f"{ajuste_aplicado*100:.0f}%"],
        "RCD (Hoja 4)": [f"{rcd:.0f}"],
        "Resultado final": [f"{rcd_final:.0f} kcal/día"]
    }))
    st.metric("Plazo estimado del cambio", plazo)
    st.caption("El porcentaje define la velocidad e impacto del cambio: 0% mantiene el peso, valores mayores "
               "aceleran el proceso, siempre evitando descompensaciones, fatiga crónica o alteración del crecimiento.")
    caja_util("Aquí se traduce tu meta ('quiero bajar/subir/mantener peso') en un número exacto de calorías al "
              "día. Es el paso que conecta tu objetivo personal con la ciencia: sin este ajuste, no sabrías "
              "cuánto comer realmente para lograr lo que quieres. 🎯",
              emoji="🎯", color="#FCE4EC", borde="#D81B60")

# ---------------------------------------------------------------------------------------
with tabs[6]:
    st.markdown("### Hoja 6: Cálculo de los Macronutrientes")
    st.caption("Se usan las calorías recomendadas según el objetivo nutricional (Hoja 5), no el RCD base.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Proteínas (20%)", f"{gr_prot:.1f} g", f"{cal_prot:.1f} kcal/día")
    col2.metric("Carbohidratos (50%)", f"{gr_carb:.1f} g", f"{cal_carb:.1f} kcal/día")
    col3.metric("Grasas (30%)", f"{gr_gras:.1f} g", f"{cal_gras:.1f} kcal/día")
    st.table(pd.DataFrame({
        "Resumen energético": ["Proteínas", "Carbohidratos", "Grasas", "Total"],
        "Valor (kcal)": [f"{cal_prot:.1f}", f"{cal_carb:.1f}", f"{cal_gras:.1f}", f"{cal_prot+cal_carb+cal_gras:.1f}"]
    }))
    caja_util("No basta con contar calorías: también importa DE QUÉ están hechas. Esta hoja reparte tu meta "
              "calórica en proteínas (para músculos), carbohidratos (para energía) y grasas (para hormonas y "
              "órganos), en gramos concretos que puedes usar al armar tus platos. 🍗🍚🥑",
              emoji="🍽️", color="#FFFDE7", borde="#FBC02D")

# ---------------------------------------------------------------------------------------
with tabs[7]:
    st.markdown("### Hoja 7: Cálculo de las Porciones del Día")
    st.caption("Se toma el RCD final (según objetivo) y se multiplica por el factor de cada comida.")
    st.table(pd.DataFrame({
        "Comida": list(porciones.keys()),
        "Factor": [f"{v['pct']*100:.0f}%" for v in porciones.values()],
        "Calorías asignadas": [f"{v['kcal']:.1f} kcal" for v in porciones.values()]
    }))
    caja_util("Comer todas tus calorías de una sola vez sería imposible (¡y poco saludable!). Esta hoja te dice "
              "cuánto puedes comer en cada momento del día: desayuno, meriendas, almuerzo y cena, para que "
              "llegues a tu meta sin pasar hambre ni excederte. ⏰🍴",
              emoji="🍽️", color="#E0F7FA", borde="#00ACC1")

# ---------------------------------------------------------------------------------------
with tabs[8]:
    st.markdown("### Hoja 8: Página FatSecret")
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
        st.markdown(f"🔍 [Ver **{alimento}** en FatSecret]({url})")
    caja_util("Cuando no sepas cuántas calorías tiene un alimento, no tienes que adivinar: escribe su nombre "
              "aquí y con un clic vas directo a su ficha nutricional completa en FatSecret. Así armas tu dieta "
              "con información real, no con suposiciones. 🔍🥗",
              emoji="🌐", color="#E8F5E9", borde="#2E7D32")

# ---------------------------------------------------------------------------------------
with tabs[9]:
    st.markdown("### Hoja 9: Plan de Dieta Semanal")
    st.caption("Elige un alimento por macronutriente en cada comida. El sistema redistribuye proporcionalmente "
               "las calorías de cada alimento elegido para que la suma coincida exactamente con tu meta de macros "
               "(igual que la fórmula =ROUND((valor/suma)*meta, 2) del Excel).")

    seleccion = {}
    for comida in DIETA:
        st.markdown(f"**{comida.upper()}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            carb_sel = st.selectbox(f"Carbohidrato — {comida}", list(DIETA[comida]["Carbohidrato"].keys()), key=f"c_{comida}")
        with c2:
            prot_sel = st.selectbox(f"Proteína — {comida}", list(DIETA[comida]["Proteína"].keys()), key=f"p_{comida}")
        with c3:
            gras_sel = st.selectbox(f"Grasa — {comida}", list(DIETA[comida]["Grasa"].keys()), key=f"g_{comida}")
        seleccion[comida] = {
            "Carbohidrato": (carb_sel, DIETA[comida]["Carbohidrato"][carb_sel]),
            "Proteína": (prot_sel, DIETA[comida]["Proteína"][prot_sel]),
            "Grasa": (gras_sel, DIETA[comida]["Grasa"][gras_sel]),
        }

    suma_carb = sum(v["Carbohidrato"][1] for v in seleccion.values())
    suma_prot = sum(v["Proteína"][1] for v in seleccion.values())
    suma_gras = sum(v["Grasa"][1] for v in seleccion.values())

    filas = []
    total_general = 0
    for comida, datos in seleccion.items():
        porc_carb = round((datos["Carbohidrato"][1] / suma_carb) * cal_carb, 2) if suma_carb else 0
        porc_prot = round((datos["Proteína"][1] / suma_prot) * cal_prot, 2) if suma_prot else 0
        porc_gras = round((datos["Grasa"][1] / suma_gras) * cal_gras, 2) if suma_gras else 0
        total_comida = porc_carb + porc_prot + porc_gras
        total_general += total_comida
        filas.append({
            "Momento": comida,
            "Carbohidrato": datos["Carbohidrato"][0], "kcal base": datos["Carbohidrato"][1], "Porción corregida": porc_carb,
            "Proteína": datos["Proteína"][0], "kcal base ": datos["Proteína"][1], "Porción corregida ": porc_prot,
            "Grasa": datos["Grasa"][0], "kcal base  ": datos["Grasa"][1], "Porción corregida  ": porc_gras,
            "Total comida (kcal)": round(total_comida, 2)
        })
    st.table(pd.DataFrame(filas))
    st.metric("Total de calorías diarias (dieta armada)", f"{total_general:.1f} kcal")
    st.metric("Comparación con calorías meta (Hoja 5)", f"{rcd_final:.1f} kcal")
    if abs(total_general - rcd_final) < 1:
        st.success("✅ La dieta armada coincide con la meta calórica del objetivo nutricional.")
    caja_util("Aquí armas tu menú real del día eligiendo alimentos que te gusten, y la app hace toda la "
              "matemática por ti: ajusta las porciones para que, sin importar qué elijas, siempre termines "
              "exactamente en tu meta de calorías y macronutrientes. ¡Comer sano también puede ser rico! 😋",
              emoji="🍱", color="#FBE9E7", borde="#FF7043")

# ---------------------------------------------------------------------------------------
with tabs[10]:
    st.markdown("### Hoja 10: Gasto Energético Ajustado al Clima de Chiclayo")
    st.info("Según la FAO, vivir en climas cálidos y desérticos continuos como Chiclayo genera una adaptación "
            "biológica: el cuerpo reduce su tasa metabólica basal para evitar producir calor interno excesivo. "
            "Por ello, se aplica un factor de **0.95**, restando automáticamente un 5% al gasto calórico diario total.")
    st.latex(r"RCD_{Chiclayo} = RCD \times 0.95")
    st.caption("Este cálculo usa el RCD base de la Hoja 4 (antes del ajuste por objetivo), igual que en el Excel original.")
    st.metric("Gasto energético ajustado al clima de Chiclayo", f"{rcd_chiclayo:.1f} kcal/día")
    caja_util("Vivir en un lugar caluroso como Chiclayo también afecta cuántas calorías gasta tu cuerpo. Este "
              "dato extra te da una versión más realista y localizada de tu gasto calórico, pensada "
              "específicamente para nuestra región. ☀️🌴",
              emoji="🌡️", color="#FFF8E1", borde="#F9A825")

# ---------------------------------------------------------------------------------------
with tabs[11]:
    st.markdown("### Aporte N°01: Tasa Metabólica Basal en Embarazo")
    st.caption("Calculadora independiente (igual que en el Excel), no conectada a los datos generales de la Hoja 0.")
    nombre_emb = st.text_input("Nombre:", "")
    c1, c2, c3 = st.columns(3)
    with c1:
        edad_emb = st.number_input("Edad:", min_value=10, max_value=60, value=27, step=1, key="edad_emb")
    with c2:
        peso_emb = st.number_input("Peso (kg):", min_value=30.0, value=68.0, step=0.1, key="peso_emb")
    with c3:
        altura_emb = st.number_input("Altura (cm):", min_value=100, value=162, step=1, key="altura_emb")
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
              emoji="👶", color="#FCE4EC", borde="#EC407A")

# ---------------------------------------------------------------------------------------
with tabs[12]:
    st.markdown("### Aporte N°02: Hora Límite de Cafeína")
    st.caption("La cafeína tarda entre 5 y 6 horas en reducirse a la mitad en el cuerpo. Calcular de 8 a 10 horas "
               "antes de acostarse asegura que el estimulante baje lo suficiente para no bloquear los receptores "
               "cerebrales del sueño, protegiendo el descanso profundo.")
    hora_dormir = st.time_input("Hora de dormir:", value=datetime.strptime("22:00", "%H:%M").time())
    dt_dormir = datetime.combine(datetime.today(), hora_dormir)
    dt_limite = dt_dormir - timedelta(hours=8)
    st.latex(r"Hora\ L\'imite = RESIDUO\left(Hora\_Dormir - \frac{8}{24}\,;\,1\right)")
    st.metric("Hora límite recomendada para tomar cafeína", dt_limite.time().strftime("%H:%M"))
    st.info("Un buen descanso es fundamental en la dieta, ya que regula las hormonas del hambre y reduce la "
            "ansiedad por comer dulce al día siguiente.")
    caja_util("¿Sabías que dormir mal te da más hambre y más ganas de comer dulce al día siguiente? Esta "
              "herramienta te dice hasta qué hora puedes tomar café sin arruinar tu descanso — y un buen "
              "descanso es tan importante para tu salud como una buena alimentación. ☕😴",
              emoji="🌙", color="#EDE7F6", borde="#5E35B1")

st.markdown("---")
st.caption("Aplicación desarrollada en Streamlit — réplica fiel del Excel 'Grupo n°4 VER.2' (Proyecto Sana "
           "Alimentación) para el proyecto de tesis escolar sobre salud pública en Lambayeque, Grupo N°04.")
