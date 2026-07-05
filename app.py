import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(page_title="Proyecto Sana Alimentación", layout="wide", page_icon="🍎")

st.title("🥦 PROYECTO: SANA ALIMENTACIÓN")
st.subheader("SANTA MARIA REINA 5°\"C\" SECUNDARIA — Región Lambayeque")
st.markdown("*La mejor nutrición es aquella que te hace sentir bien por dentro y por fuera a largo plazo*")
st.caption("Aplicación web interactiva que replica la operatividad completa del Excel 'Grupo n°4 VER.2', "
           "incluyendo teoría clínica, percentiles, metabolismo, ajuste climático de Chiclayo, "
           "embarazo, macronutrientes, porciones y enlace a FatSecret.")
st.markdown("---")

# =========================================================
# SIDEBAR - HOJA 0: DATOS
# =========================================================
st.sidebar.header("📝 Ficha de Ingreso Digital")

etapa = st.sidebar.selectbox(
    "Etapa de vida:",
    ["Niñez (5-11 años)", "Adolescencia (12-17 años)", "Adultez (18-59 años)", "Vejez (60+ años)", "Embarazada"]
)

peso = st.sidebar.number_input("Peso Actual (kg):", min_value=5.0, max_value=250.0, value=58.0, step=0.1)
estatura = st.sidebar.number_input("Estatura (cm):", min_value=50, max_value=250, value=160, step=1)
edad = st.sidebar.number_input("Edad (años):", min_value=1, max_value=120, value=16, step=1)
genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"], index=0)

trimestre = None
if etapa == "Embarazada":
    trimestre = st.sidebar.selectbox("Trimestre de embarazo:", ["1er trimestre", "2do trimestre", "3er trimestre"])

actividad = st.sidebar.selectbox("Nivel de Actividad Física:", ["Sedentario", "Ligero", "Moderado", "Intensa"], index=2)
objetivo = st.sidebar.selectbox("Objetivo Nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)
hora_dormir = st.sidebar.time_input("¿A qué hora sueles dormir?", value=datetime.strptime("22:30", "%H:%M").time())

st.sidebar.markdown("---")
st.sidebar.info("ℹ️ **¿Cómo saber mi actividad física?**\n"
                 "- **Sedentario**: solo actividades de la vida diaria.\n"
                 "- **Ligero**: ejercicio 1-3 veces/semana.\n"
                 "- **Moderado**: ejercicio 3-5 veces/semana.\n"
                 "- **Intensa**: ejercicio diario o deportista.")

# =========================================================
# CÁLCULOS BASE
# =========================================================
estatura_m = estatura / 100.0
imc = peso / (estatura_m ** 2)

# --- TMB (Mifflin-St Jeor) ---
if genero == "Hombre":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161

# --- Factor de actividad (diferenciado por género, según Excel) ---
factores = {
    "Hombre": {"Sedentario": 1.2, "Ligero": 1.55, "Moderado": 1.8, "Intensa": 2.1},
    "Mujer":  {"Sedentario": 1.2, "Ligero": 1.56, "Moderado": 1.64, "Intensa": 1.82}
}
factor_actividad = factores[genero][actividad]
rcd = tmb * factor_actividad

# --- Ajuste climático Chiclayo (-5%) ---
rcd_chiclayo = rcd * 0.95

# --- Ajuste por objetivo (menores de edad no reciben ajuste drástico) ---
if edad < 18 or etapa == "Niñez (5-11 años)" or etapa == "Adolescencia (12-17 años)":
    ajuste_pct = 0
    rcd_objetivo = rcd_chiclayo
else:
    if objetivo == "Bajar de peso":
        ajuste_pct = -15
    elif objetivo == "Subir de peso":
        ajuste_pct = 30
    else:
        ajuste_pct = 0
    rcd_objetivo = rcd_chiclayo + (rcd_chiclayo * (ajuste_pct / 100))

# --- Ajuste por embarazo ---
ajuste_embarazo = 0
if etapa == "Embarazada":
    if trimestre == "2do trimestre":
        ajuste_embarazo = 340
    elif trimestre == "3er trimestre":
        ajuste_embarazo = 452
    rcd_objetivo = rcd_objetivo + ajuste_embarazo

# --- Macronutrientes (20% Prot / 50% Carb / 30% Grasas) ---
cal_prot = rcd_objetivo * 0.20
cal_carb = rcd_objetivo * 0.50
cal_gras = rcd_objetivo * 0.30
gr_prot = cal_prot / 4
gr_carb = cal_carb / 4
gr_gras = cal_gras / 9

# --- Porciones por comida ---
porciones = {
    "Desayuno (25%)": rcd_objetivo * 0.25,
    "Merienda 1 (5%)": rcd_objetivo * 0.05,
    "Almuerzo (40%)": rcd_objetivo * 0.40,
    "Merienda 2 (5%)": rcd_objetivo * 0.05,
    "Cena (25%)": rcd_objetivo * 0.25
}

# --- Hora límite de cafeína: dormir - 8h (RESIDUO(hora-8/24;1)) ---
dt_dormir = datetime.combine(datetime.today(), hora_dormir)
dt_cafeina = dt_dormir - timedelta(hours=8)
hora_limite_cafeina = dt_cafeina.time()

# =========================================================
# CLASIFICACIONES CLÍNICAS (Hoja 1 - Examen Médico)
# =========================================================
def clasificar_hemoglobina(valor, etapa, genero):
    if valor <= 0:
        return "Sin dato"
    if etapa == "Embarazada":
        if valor < 7: return "Anemia grave"
        elif valor < 11: return "Anemia leve/moderada"
        else: return "Normal"
    if etapa in ["Niñez (5-11 años)"]:
        if valor < 8: return "Anemia grave"
        elif valor < 11.5: return "Anemia leve/moderada"
        else: return "Normal"
    if etapa == "Adolescencia (12-17 años)" and genero == "Mujer":
        if valor < 8: return "Anemia grave"
        elif valor <= 11.9: return "Anemia leve"
        else: return "Normal"
    if etapa == "Adolescencia (12-17 años)" and genero == "Hombre":
        if valor < 8: return "Anemia grave"
        elif valor < 13: return "Anemia leve/moderada"
        else: return "Normal"
    # Adultez / Vejez
    if genero == "Mujer":
        if valor < 8: return "Anemia grave"
        elif valor < 12: return "Anemia leve/moderada"
        else: return "Normal"
    else:
        if valor < 8: return "Anemia grave"
        elif valor < 13: return "Anemia leve/moderada"
        else: return "Normal"

def clasificar_trigliceridos(valor):
    if valor <= 0: return "Sin dato"
    if valor < 150: return "Normal"
    elif valor < 200: return "Límite alto"
    elif valor < 500: return "Alto"
    else: return "Muy alto"

def clasificar_colesterol(valor):
    if valor <= 0: return "Sin dato"
    if valor < 200: return "Deseable"
    elif valor < 240: return "Límite alto"
    else: return "Alto"

def clasificar_glucosa(valor):
    if valor <= 0: return "Sin dato"
    if valor < 70: return "Hipoglucemia"
    elif valor <= 99: return "Normal"
    elif valor <= 125: return "Prediabetes"
    else: return "Diabetes"

def clasificar_hierro(valor):
    if valor <= 0: return "Sin dato"
    if valor < 60: return "Bajo"
    elif valor <= 170: return "Normal"
    else: return "Alto"

# =========================================================
# CLASIFICACIÓN IMC / PERCENTIL
# =========================================================
def clasificar_imc_adulto(imc):
    if imc < 18.5: return "Bajo Peso"
    elif imc < 25: return "Peso Saludable"
    elif imc < 30: return "Sobrepeso"
    elif imc < 35: return "Obesidad Clase 1"
    elif imc < 40: return "Obesidad Clase 2"
    else: return "Obesidad Clase 3"

def clasificar_percentil_aprox(imc):
    """Aproximación simplificada de percentil para niños/adolescentes.
    El Excel original usa BUSCARV contra tablas OMS de percentil por edad y sexo;
    aquí se usa una aproximación referencial basada en rangos de IMC."""
    if imc < 15: return "< P5 — Bajo Peso"
    elif imc < 21: return "P5 a P84 — Peso Saludable"
    elif imc < 26: return "P85 a P94 — Sobrepeso"
    else: return "≥ P95 — Obesidad"

# =========================================================
# NAVEGACIÓN POR PESTAÑAS
# =========================================================
st.subheader("📋 Navegación por Hojas de Evaluación del Sistema")
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📂 0.-DATOS",
    "🩺 1.-EXAMEN MÉDICO",
    "⚖️ 2.-IMC / PERCENTIL",
    "⚡ 3.-TMB Y RCD",
    "🌡️ 4.-CLIMA Y OBJETIVO",
    "🍽️ 5.-MACRONUTRIENTES",
    "🍴 6.-PORCIONES Y FATSECRET",
    "☕ 7.-HORA LÍMITE DE CAFEÍNA"
])

# ---------------------------------------------------------
with tab0:
    st.markdown("### Hoja 0: Variables Generales de Control")
    df_hoja0 = pd.DataFrame({
        "Variable": ["Etapa de Vida", "Peso Corporal", "Estatura Ingresada", "Edad Cronológica",
                     "Género", "Factor de Actividad", "Meta Principal", "Hora de dormir"],
        "Valor": [etapa, f"{peso} kg", f"{estatura} cm", f"{edad} años",
                  genero, f"{actividad} (x{factor_actividad})", objetivo, hora_dormir.strftime("%H:%M")]
    })
    st.table(df_hoja0)
    if etapa == "Embarazada":
        st.info(f"Trimestre seleccionado: **{trimestre}**")

# ---------------------------------------------------------
with tab1:
    st.markdown("### Hoja 1: Ficha Clínico-Nutricional Estructurada")
    st.caption("El sistema clasifica cada parámetro mediante lógica condicional (SI anidada) "
               "según etapa de vida y género, tal como en el Excel original.")

    col_a, col_b = st.columns(2)
    with col_a:
        hemo = st.number_input("Hemoglobina (g/dL)", min_value=0.0, value=0.0, step=0.1)
        trigli = st.number_input("Triglicéridos (mg/dL)", min_value=0.0, value=0.0, step=1.0)
        gluco = st.number_input("Glucosa (mg/dL)", min_value=0.0, value=0.0, step=1.0)
    with col_b:
        coles = st.number_input("Colesterol (mg/dL)", min_value=0.0, value=0.0, step=1.0)
        hierro = st.number_input("Hierro (µg/dL)", min_value=0.0, value=0.0, step=1.0)

    datos_examen = pd.DataFrame({
        "Parámetro Clínico": ["Hemoglobina", "Triglicéridos", "Glucosa", "Colesterol", "Hierro"],
        "Valor Ingresado": [f"{hemo} g/dL", f"{trigli} mg/dL", f"{gluco} mg/dL", f"{coles} mg/dL", f"{hierro} µg/dL"],
        "Rango de Referencia": ["12.0 - 16.0 g/dL (adulto)", "< 150 mg/dL", "70 - 99 mg/dL", "< 200 mg/dL", "60 - 170 µg/dL"],
        "Diagnóstico del Sistema": [
            clasificar_hemoglobina(hemo, etapa, genero),
            clasificar_trigliceridos(trigli),
            clasificar_glucosa(gluco),
            clasificar_colesterol(coles),
            clasificar_hierro(hierro)
        ]
    })
    st.table(datos_examen)

# ---------------------------------------------------------
with tab2:
    st.markdown("### Hoja 2: Diagnóstico del Índice de Masa Corporal")
    col_imc1, col_imc2 = st.columns(2)
    with col_imc1:
        st.metric(label="Tu Índice de Masa Corporal (IMC)", value=f"{imc:.2f} kg/m²")
        st.latex(r"IMC = \frac{Peso\ (kg)}{Altura\ (m)^2}")
    with col_imc2:
        if etapa in ["Niñez (5-11 años)", "Adolescencia (12-17 años)"]:
            categoria = clasificar_percentil_aprox(imc)
            st.metric(label="Clasificación por Percentil (aprox.)", value=categoria)
            st.warning("En niños y adolescentes el Excel original cruza el IMC con tablas OMS de "
                       "percentil por edad y sexo (función BUSCARV). Esta app usa una aproximación "
                       "referencial; para el valor exacto consulta la tabla oficial de percentiles.")
        else:
            categoria = clasificar_imc_adulto(imc)
            st.metric(label="Clasificación Oficial (OMS - Adultos)", value=categoria)

    tabla_rangos_imc = pd.DataFrame({
        "Clasificación OMS (Adultos)": ["Bajo Peso", "Peso Saludable", "Sobrepeso", "Obesidad Clase 1", "Obesidad Clase 2", "Obesidad Clase 3"],
        "Rango de IMC": ["< 18.5", "18.5 - 24.9", "25.0 - 29.9", "30.0 - 34.9", "35.0 - 39.9", "≥ 40.0"]
    })
    st.table(tabla_rangos_imc)

    tabla_percentiles = pd.DataFrame({
        "Percentil (Niños/Adolescentes)": ["< P5", "P5 - P84", "P85 - P94", "≥ P95"],
        "Clasificación": ["Bajo Peso", "Peso Saludable", "Sobrepeso", "Obesidad"]
    })
    st.table(tabla_percentiles)

# ---------------------------------------------------------
with tab3:
    st.markdown("### Hoja 3: Cálculo de Tasa Metabólica Basal (TMB) y RCD")
    st.markdown("**Fórmula de Mifflin-St Jeor**")
    if genero == "Hombre":
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) + 5")
    else:
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) - 161")

    datos_tmb = pd.DataFrame({
        "Concepto Energético": ["Tasa Metabólica Basal (Reposo)", "Factor de Actividad Multiplicador", "Requerimiento Calórico Diario (RCD)"],
        "Cálculo (kcal)": [f"{tmb:.1f}", f"x {factor_actividad}", f"{rcd:.1f}"]
    })
    st.table(datos_tmb)
    st.latex(r"RCD = TMB \times Factor\ de\ Actividad")

# ---------------------------------------------------------
with tab4:
    st.markdown("### Hoja 4: Ajuste Climático (Chiclayo) y Objetivo Nutricional")
    st.info("Según la FAO, vivir en climas cálidos y desérticos continuos como **Chiclayo** genera una "
             "adaptación biológica: el cuerpo reduce su TMB para evitar producir calor interno excesivo. "
             "Por ello se aplica un factor de **0.95**, restando un 5% al gasto calórico diario total.")
    st.latex(r"RCD_{Chiclayo} = RCD \times 0.95")
    st.metric("RCD ajustado al clima de Chiclayo", f"{rcd_chiclayo:.1f} kcal/día")

    st.markdown("---")
    st.markdown(f"**Objetivo seleccionado:** {objetivo}")
    if edad < 18 or etapa in ["Niñez (5-11 años)", "Adolescencia (12-17 años)"]:
        st.warning("A diferencia de los adultos, el cuerpo de los menores necesita energía constante "
                   "para el desarrollo de órganos y huesos, por lo que **no se aplica un ajuste calórico "
                   "drástico** sin supervisión médica/nutricional.")
    else:
        st.markdown(f"**Ajuste aplicado por objetivo:** {ajuste_pct}%")

    if etapa == "Embarazada":
        st.success(f"Ajuste por embarazo ({trimestre}): **+{ajuste_embarazo} kcal**")

    st.metric("RCD Final (con clima + objetivo + embarazo si aplica)", f"{rcd_objetivo:.1f} kcal/día")

# ---------------------------------------------------------
with tab5:
    st.markdown("### Hoja 5: Requerimiento de Macronutrientes")
    st.markdown("Distribución teórica: **20% Proteínas · 50% Carbohidratos · 30% Grasas**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Proteínas (20%)", f"{gr_prot:.1f} g", f"{cal_prot:.1f} kcal")
    col2.metric("Carbohidratos (50%)", f"{gr_carb:.1f} g", f"{cal_carb:.1f} kcal")
    col3.metric("Grasas (30%)", f"{gr_gras:.1f} g", f"{cal_gras:.1f} kcal")

    st.markdown("---")
    st.latex(r"Gramos\ Prote\'inas = \frac{Calor\'ias \times 0.20}{4}")
    st.latex(r"Gramos\ Carbohidratos = \frac{Calor\'ias \times 0.50}{4}")
    st.latex(r"Gramos\ Grasas = \frac{Calor\'ias \times 0.30}{9}")

    datos_macros = pd.DataFrame({
        "Macronutriente": ["Proteínas (20%)", "Carbohidratos (50%)", "Grasas (30%)"],
        "Aporte en Gramos": [f"{gr_prot:.1f} g", f"{gr_carb:.1f} g", f"{gr_gras:.1f} g"],
        "Aporte en Kcal": [f"{cal_prot:.1f} kcal", f"{cal_carb:.1f} kcal", f"{cal_gras:.1f} kcal"]
    })
    st.table(datos_macros)

# ---------------------------------------------------------
with tab6:
    st.markdown("### Hoja 6: Distribución de Porciones por Comida")
    st.caption("El gasto calórico total se reparte en 5 momentos de alimentación.")
    df_porciones = pd.DataFrame({
        "Comida": list(porciones.keys()),
        "Calorías asignadas": [f"{v:.1f} kcal" for v in porciones.values()]
    })
    st.table(df_porciones)

    st.markdown("---")
    st.markdown("### 🔗 Buscador Nutricional FatSecret")
    st.caption("El Excel usa la función HIPERVINCULO para enlazar cada alimento a FatSecret y consultar "
               "porciones (g/ml), azúcares, sodio y fibra. Escribe un alimento para generar el enlace.")
    alimento = st.text_input("Nombre del alimento (ej. arroz, pollo a la plancha, palta):", "")
    if alimento.strip():
        url_busqueda = f"https://www.fatsecret.com/calorias-nutricion/search?q={alimento.strip().replace(' ', '+')}"
        st.markdown(f"🔗 [Buscar **{alimento}** en FatSecret]({url_busqueda})")

    st.markdown("---")
    st.markdown("### 📊 Total consolidado del día (función SUM)")
    total_dia = sum(porciones.values())
    st.metric("Suma total de calorías del día", f"{total_dia:.1f} kcal")

# ---------------------------------------------------------
with tab7:
    st.markdown("### Hoja 7: Hora Límite de Consumo de Cafeína")
    st.caption("La cafeína tarda entre 5 y 6 horas en reducirse a la mitad en el cuerpo humano. "
               "El sistema resta 8 horas a tu hora de dormir para proteger el descanso profundo.")
    st.latex(r"Hora\ L\'imite = RESIDUO\left(Hora\_Dormir - \frac{8}{24}\,;\,1\right)")
    st.metric("Tu hora límite recomendada para tomar cafeína", hora_limite_cafeina.strftime("%H:%M"))
    st.info(f"Duermes aproximadamente a las **{hora_dormir.strftime('%H:%M')}**, por lo que se recomienda "
            f"evitar el café después de las **{hora_limite_cafeina.strftime('%H:%M')}** para no bloquear "
            f"los receptores del sueño.")

st.markdown("---")
st.caption("Aplicación desarrollada en Streamlit — réplica funcional del Excel 'Grupo n°4 VER.2' "
           "para el proyecto de tesis escolar sobre salud pública en Lambayeque.")
