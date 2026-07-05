import streamlit as st
import pandas as pd

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS
# ==========================================
st.set_page_config(page_title="Sana Alimentación - 5°C", layout="wide", page_icon="🍎")

st.markdown("""
    <style>
    .titulo-principal { font-size:36px; font-weight:800; color:#1E3A8A; text-align:center; text-transform: uppercase; }
    .sub-colegio { font-size:24px; font-weight:700; color:#B91C1C; text-align:center; margin-bottom:10px; }
    .frase { font-size:18px; font-style:italic; color:#4B5563; text-align:center; margin-bottom:30px; }
    
    /* Cajas de Colores para Teoría y Resultados */
    .caja { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 6px solid; font-size: 16px; }
    .caja-hemo { background-color: #FDF2F2; border-color: #DC2626; color: #7F1D1D; } /* Rosa/Rojo */
    .caja-hierro { background-color: #F0FDF4; border-color: #16A34A; color: #14532D; } /* Verde */
    .caja-trig { background-color: #FFFDF2; border-color: #D97706; color: #78350F; } /* Amarillo */
    .caja-glucosa { background-color: #F0F9FF; border-color: #0284C7; color: #0C4A6E; } /* Celeste */
    .caja-colesterol { background-color: #FAF5FF; border-color: #9333EA; color: #581C87; } /* Morado */
    
    .alerta-roja { background-color: #FEE2E2; color: #991B1B; padding: 10px; border-radius: 5px; font-weight: bold; }
    .alerta-verde { background-color: #DCFCE7; color: #166534; padding: 10px; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="titulo-principal">PROYECTO: SANA ALIMENTACIÓN</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-colegio">SANTA MARIA REINA 5"C" SECUNDARIA</div>', unsafe_allow_html=True)
st.markdown('<div class="frase">"La mejor nutrición es aquella que te hace sentir bien por dentro y por fuera a largo plazo"</div>', unsafe_allow_html=True)

# ==========================================
# 2. MOTOR LÓGICO Y VARIABLES GLOBALES
# ==========================================
st.sidebar.header("📥 PANEL DE DATOS CLÍNICOS")

# Ficha de ingreso
peso = st.sidebar.number_input("Peso (kg):", 10.0, 200.0, 60.0, step=0.1)
estatura_cm = st.sidebar.number_input("Estatura (cm):", 50, 250, 160)
edad = st.sidebar.number_input("Edad (años):", 1, 100, 16)
genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"])
actividad = st.sidebar.selectbox("Actividad Física:", ["Sedentario", "Ligero", "Moderado", "Intenso"], index=1)
objetivo = st.sidebar.selectbox("Objetivo:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=1)

# Variables especiales de la investigación
embarazo = st.sidebar.selectbox("Estado de Embarazo (Solo mujeres):", ["No aplica", "1er Trimestre", "2do Trimestre", "3er Trimestre"])
clima = st.sidebar.selectbox("Factor Climático:", ["Templado (Estándar)", "Cálido (Chiclayo/Costa Norte)"])

# Cálculos Base
estatura_m = estatura_cm / 100.0
imc = peso / (estatura_m ** 2)

# Fórmulas de Mifflin-St Jeor
if genero == "Hombre":
    tmb_base = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) + 5
else:
    tmb_base = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) - 161

# Ajuste por Clima (Cálido reduce requerimiento)
factor_clima = 0.95 if clima == "Cálido (Chiclayo/Costa Norte)" else 1.0
tmb_clima = tmb_base * factor_clima

# Factor de Actividad
factores_act = {"Sedentario": 1.2, "Ligero": 1.375, "Moderado": 1.55, "Intenso": 1.725}
get = tmb_clima * factores_act[actividad]

# Ajuste por Embarazo
if genero == "Mujer":
    if embarazo == "2do Trimestre": get += 340
    elif embarazo == "3er Trimestre": get += 452

# Ajuste por Objetivo
if objetivo == "Bajar de peso": cal_final = get - 400
elif objetivo == "Subir de peso": cal_final = get + 400
else: cal_final = get

# ==========================================
# 3. NAVEGACIÓN DE PESTAÑAS (13 HOJAS)
# ==========================================
tabs = st.tabs([
    "0. DATOS", "1. EXAMEN MÉDICO", "2. IMC", "3. TMB", "4. REQUERIMIENTO", 
    "5. OBJETIVOS", "6. MACROS", "7. PORCIONES", "8. FATSECRET", 
    "9. DIETA", "10. CLIMA", "11. APORTE 1", "12. APORTE 2"
])

# --- HOJA 0: DATOS ---
with tabs[0]:
    st.markdown("### 📋 Resumen de Variables Antropométricas")
    df_datos = pd.DataFrame({
        "Variable": ["Peso", "Estatura", "Edad", "Género", "IMC Actual", "Objetivo", "Clima"],
        "Valor": [f"{peso} kg", f"{estatura_cm} cm", f"{edad} años", genero, f"{imc:.1f}", objetivo, clima]
    })
    st.table(df_datos)

# --- HOJA 1: EXAMEN MÉDICO (Interactivo) ---
with tabs[1]:
    st.markdown("### 🩺 Evaluación Clínica Interactiva")
    st.write("Selecciona los valores de tus análisis de laboratorio para recibir un diagnóstico nutricional:")
    
    col1, col2 = st.columns(2)
    with col1:
        val_hemo = st.number_input("Ingresa tu Hemoglobina (g/dL):", 5.0, 20.0, 12.0)
        val_glucosa = st.number_input("Ingresa tu Glucosa (mg/dL):", 50, 300, 90)
    with col2:
        val_trig = st.number_input("Ingresa tus Triglicéridos (mg/dL):", 50, 600, 150)
        val_col = st.number_input("Ingresa tu Colesterol (mg/dL):", 100, 500, 180)

    # Lógica Clínica Dinámica
    st.markdown("#### 🔬 Resultados del Análisis:")
    
    # Hemoglobina
    if val_hemo < 12.0 and genero == "Mujer": diag_hemo, clase_hemo = "Anemia Detectada", "alerta-roja"
    elif val_hemo < 13.0 and genero == "Hombre": diag_hemo, clase_hemo = "Anemia Detectada", "alerta-roja"
    else: diag_hemo, clase_hemo = "Niveles Normales", "alerta-verde"
    
    st.markdown(f"""
    <div class="caja caja-hemo">
        <b>🩸 Hemoglobina ({val_hemo} g/dL) -> <span class='{clase_hemo}'>{diag_hemo}</span></b><br>
        <i>Proteína rica en hierro que transporta el oxígeno. Fundamental evaluar en adolescentes y mujeres gestantes.</i>
    </div>
    """, unsafe_allow_html=True)

    # Glucosa
    if val_glucosa < 100: diag_glu, clase_glu = "Normal", "alerta-verde"
    elif 100 <= val_glucosa < 126: diag_glu, clase_glu = "Prediabetes", "alerta-roja"
    else: diag_glu, clase_glu = "Diabetes", "alerta-roja"

    st.markdown(f"""
    <div class="caja caja-glucosa">
        <b>🍬 Glucosa ({val_glucosa} mg/dL) -> <span class='{clase_glu}'>{diag_glu}</span></b><br>
        <i>Principal fuente de energía celular. Medida en ayunas.</i>
    </div>
    """, unsafe_allow_html=True)

# --- HOJA 2: IMC ---
with tabs[2]:
    st.markdown("### ⚖️ Índice de Masa Corporal y Percentiles")
    
    col_imc1, col_imc2 = st.columns(2)
    with col_imc1:
        st.metric("IMC Calculado", f"{imc:.2f} kg/m²")
    with col_imc2:
        if imc < 18.5: st.error("Clasificación: Bajo Peso")
        elif 18.5 <= imc <= 24.9: st.success("Clasificación: Normopeso (Saludable)")
        elif 25 <= imc <= 29.9: st.warning("Clasificación: Sobrepeso")
        else: st.error("Clasificación: Obesidad")

    st.markdown("#### Tabla OMS Referencial (Adolescentes)")
    df_oms = pd.DataFrame({
        "Edad": ["15 años", "16 años", "17 años"],
        "P5 (Bajo Peso)": ["< 16.5", "< 16.8", "< 17.2"],
        "P50 (Normal)": ["19.0 - 23.5", "19.5 - 24.2", "20.0 - 24.9"],
        "P85 (Sobrepeso)": ["> 23.6", "> 24.3", "> 25.0"]
    })
    st.table(df_oms)

# --- HOJA 3: TMB & HOJA 4: REQUERIMIENTO ---
with tabs[3]:
    st.markdown("### ⚡ Tasa Metabólica Basal (Mifflin-St Jeor)")
    st.write("Cálculo de la energía mínima requerida en reposo absoluto.")
    st.info(f"**TMB Base:** {tmb_base:.1f} kcal/día")
    if clima == "Cálido (Chiclayo/Costa Norte)":
        st.warning(f"🌡️ Ajuste por clima cálido aplicado (Factor 0.95): **{tmb_clima:.1f} kcal/día**")

with tabs[4]:
    st.markdown("### 🔋 Gasto Energético Total (GET)")
    st.write(f"Multiplicado por tu factor de actividad física ({actividad}):")
    st.success(f"**Requerimiento de Mantenimiento:** {get:.1f} kcal/día")

# --- HOJA 5: OBJETIVOS & HOJA 6: MACROS ---
with tabs[5]:
    st.markdown("### 🎯 Calorías Objetivo")
    st.write(f"Para tu meta de **{objetivo}**:")
    st.metric(label="Calorías Finales Diarias", value=f"{int(cal_final)} kcal")

with tabs[6]:
    st.markdown("### 📊 Distribución de Macronutrientes")
    st.write("Estructura clínica recomendada (25% Proteínas, 50% Carbohidratos, 25% Grasas):")
    
    prot_g = (cal_final * 0.25) / 4
    carb_g = (cal_final * 0.50) / 4
    gras_g = (cal_final * 0.25) / 9
    
    df_macros = pd.DataFrame({
        "Macronutriente": ["Proteínas (🥩)", "Carbohidratos (🌾)", "Grasas (🥑)"],
        "Kcal aportadas": [f"{cal_final*0.25:.1f}", f"{cal_final*0.50:.1f}", f"{cal_final*0.25:.1f}"],
        "Gramos diarios": [f"{prot_g:.1f} g", f"{carb_g:.1f} g", f"{gras_g:.1f} g"]
    })
    st.table(df_macros)

# --- HOJAS RESTANTES (Estructura preparada para la investigación) ---
with tabs[7]: st.markdown("### 🍱 7. Cálculo de Porciones\n*Sección destinada a la conversión de gramos a medidas caseras (tazas, cucharadas).*")
with tabs[8]: st.markdown("### 📱 8. Integración FatSecret\n*Búsqueda de valores nutricionales precisos según base de datos.*")
with tabs[9]: st.markdown("### 🍽️ 9. Plan de Dieta Diario\n*Estructuración de 5 comidas: Desayuno, Media Mañana, Almuerzo, Media Tarde, Cena.*")
with tabs[10]: st.markdown("### 🌴 10. Estudio del Clima\n*Justificación científica de la reducción de la TMB en entornos de alta temperatura.*")
with tabs[11]: st.markdown("### 📑 11. Aporte de Investigación 1\n*Anexos teóricos del proyecto.*")
with tabs[12]: st.markdown("### 📑 12. Aporte de Investigación 2\n*Conclusiones y bibliografía.*")
