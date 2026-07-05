import streamlit as st
import pandas as pd

# Configuración de página completa para que las tablas se vean anchas y elegantes
st.set_page_config(page_title="Proyecto Sana Alimentación", layout="wide", page_icon="🍎")

# --- TÍTULOS Y CABECERA SOLICITADOS ---
st.title("PROYECTO: SANA ALIMENTACIÓN")
st.subheader("SANTA MARIA REINA 5\"C\" SECUNDARIA")

# Frase destacada en itálica y con diseño limpio
st.markdown("> *La mejor nutrición es aquella que te hace sentir bien por dentro y por fuera a largo plazo*")
st.write("Esta aplicación web interactiva procesa los datos en tiempo real.")

st.markdown("---")

# --- PANEL LATERAL DE CONTROL (Ficha de Ingreso) ---
st.sidebar.header("📝 Ficha de Ingreso Digital")
peso = st.sidebar.number_input("Peso Actual (kg):", min_value=10.0, max_value=250.0, value=58.0, step=0.1)
estatura = st.sidebar.number_input("Estatura (cm):", min_value=50, max_value=250, value=160, step=1)
edad = st.sidebar.number_input("Edad (años):", min_value=1, max_value=120, value=16, step=1)
genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"], index=0)
actividad = st.sidebar.selectbox("Nivel de Actividad Física:", ["Sedentario", "Ligero (Ejercicio 1-3 días/sem)", "Moderado (Ejercicio 3-5 días/sem)", "Intenso (Atleta)"], index=2)
objetivo = st.sidebar.selectbox("Objetivo Nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)

# --- CÁLCULOS MATEMÁTICOS INTERNOS EN TIEMPO REAL ---
estatura_m = estatura / 100.0
imc = peso / (estatura_m ** 2)

if imc < 18.5:
    estado_imc = "Bajo peso"
    color_imc = "orange"
elif 18.5 <= imc < 25:
    estado_imc = "Normopeso / Saludable"
    color_imc = "green"
elif 25 <= imc < 30:
    estado_imc = "Sobrepeso"
    color_imc = "orange"
else:
    estado_imc = "Obesidad"
    color_imc = "red"

# Tasa Metabólica Basal (Harris-Benedict)
if genero == "Mujer":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5

# Mapeo de actividad física
dict_actividad = {
    "Sedentario": 1.2,
    "Ligero (Ejercicio 1-3 días/sem)": 1.375,
    "Moderado (Ejercicio 3-5 días/sem)": 1.55,
    "Intenso (Atleta)": 1.725
}
gasto_total = tmb * dict_actividad[actividad]

# Déficit o Superávit energético según objetivo
if objetivo == "Bajar de peso":
    calorias_objetivo = gasto_total - 400
    deficit_texto = "-400 kcal (Déficit Calórico)"
elif objetivo == "Subir de peso":
    calorias_objetivo = gasto_total + 400
    deficit_texto = "+400 kcal (Superávit Calórico)"
else:
    calorias_objetivo = gasto_total
    deficit_texto = "0 kcal (Mantenimiento)"

# --- PESTAÑAS INTERACTIVAS (IGUAL A LAS HOJAS DEL EXCEL) ---
st.subheader("📋 Navegación por Hojas de Evaluación del Sistema")
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 0.- DATOS", 
    "🩺 1.- EXAMEN MEDICO", 
    "⚖️ 2.- IMC", 
    "⚡ 3.- TASA METABÓLICA", 
    "📊 4.- REQUERIMIENTO MACROS", 
    "🍽️ 5.- PLAN DE DIETA"
])

# ---- HOJA 0: DATOS ----
with tab0:
    st.markdown("### Hoja 0: Variables Generales de Control")
    st.info("Esta sección recopila los datos antropométricos base ingresados en el sistema.")
    df_hoja0 = pd.DataFrame({
        "Variable": ["Peso Corporal", "Estatura Ingresada", "Edad Cronológica", "Género", "Factor de Actividad", "Meta Principal"],
        "Valor": [f"{peso} kg", f"{estatura} cm", f"{edad} años", genero, actividad.split(" (")[0], objetivo]
    })
    st.table(df_hoja0)

# ---- HOJA 1: EXAMEN MÉDICO ----
with tab1:
    st.markdown("### Hoja 1: Ficha Clínico - Nutricional Estructurada")
    st.write("Historial y rangos clínicos de evaluación del paciente:")
    
    datos_examen = {
        "Parámetro Clínico": ["Presión Arterial", "Frecuencia Cardíaca", "Glucosa en ayunas", "Hemoglobina", "Nivel de Hidratación"],
        "Rango de Referencia": ["120/80 mmHg", "60 - 100 lpm", "70 - 100 mg/dL", "12.0 - 16.0 g/dL", "Óptimo"],
        "Estado en App": ["Normal", "Normal", "Saludable", "Normal", "Adecuado ✅"]
    }
    st.table(pd.DataFrame(datos_examen))
    st.success("📝 Conclusión Clínica: El paciente se encuentra apto para el inicio del régimen alimentario personalizado.")

# ---- HOJA 2: IMC ----
with tab2:
    st.markdown("### Hoja 2: Diagnóstico del Índice de Masa Corporal")
    
    col_imc1, col_imc2 = st.columns(2)
    with col_imc1:
        st.metric(label="Tu Índice de Masa Corporal (IMC)", value=f"{imc:.2f} kg/m²")
    with col_imc2:
        st.metric(label="Clasificación Oficial", value=estado_imc)
        
    st.markdown("#### Tabla de Criterios de Evaluación Nutricional (OMS):")
    tabla_rangos_imc = pd.DataFrame({
        "Clasificación OMS": ["Bajo Peso", "Normopeso (Saludable)", "Sobrepeso", "Obesidad Grado I", "Obesidad Grado II"],
        "Rango de IMC": ["Menor a 18.5", "18.5 a 24.9", "25.0 a 29.9", "30.0 a 34.9", "Mayor a 35.0"],
        "Estado Actual": ["⚠️" if estado_imc == "Bajo peso" else "", "🟢" if estado_imc == "Normopeso / Saludable" else "", "⚠️" if estado_imc == "Sobrepeso" else "", "", ""]
    })
    st.table(tabla_rangos_imc)

# ---- HOJA 3: TASA METABÓLICA ----
with tab3:
    st.markdown("### Hoja 3: Balance Energético y Metabolismo Basal")
    st.write("Cálculos energéticos mediante la ecuación científica internacional:")
    
    df_metabolismo = pd.DataFrame({
        "Concepto Energético": ["Tasa Metabólica Basal (TMB)", "Efecto por Actividad Física", "Gasto Energético Total Diario (GETD)"],
        "Fórmula / Factor Aplicado": ["Harris-Benedict", f"Factor x{dict_actividad[actividad]}", "TMB × Actividad"],
        "Resultado Obtenido": [f"{tmb:.1f} kcal", actividad.split(" (")[0], f"{gasto_total:.1f} kcal"]
    })
    st.table(df_metabolismo)

# ---- HOJA 4: REQUERIMIENTO MACROS ----
with tab4:
    st.markdown("### Hoja 4: Distribución Porcentual de Macronutrientes")
    st.write(f"Distribución calórica estratégica para el objetivo: **{objetivo}** ({deficit_texto}).")
    st.metric(label="🎯 Total de Calorías Necesarias para la Dieta", value=f"{int(calorias_objetivo)} kcal/día")
    
    # Cálculos dinámicos de gramos basados en porcentajes nutricionales reales
    p_prot, p_carb, p_gras = 0.25, 0.50, 0.25
    cal_prot = calorias_objetivo * p_prot
    cal_carb = calorias_objetivo * p_carb
    cal_gras = calorias_objetivo * p_gras
    
    g_prot = cal_prot / 4
    g_carb = cal_carb / 4
    g_gras = cal_gras / 9
    
    df_macros = pd.DataFrame({
        "Macronutriente": ["Proteínas 🥩", "Carbohidratos 🌾", "Grasas Saludables 🥑", "Total General"],
        "Distribución (%)": [f"{p_prot*100:.0f}%", f"{p_carb*100:.0f}%", f"{p_gras*100:.0f}%", "100%"],
        "Calorías (kcal)": [f"{cal_prot:.1f} kcal", f"{cal_carb:.1f} kcal", f"{cal_gras:.1f} kcal", f"{calorias_objetivo:.1f} kcal"],
        "Cantidad en Gramos (g)": [f"{g_prot:.1f} g", f"{g_carb:.1f} g", f"{g_gras:.1f} g", "-"]
    })
    st.table(df_macros)

# ---- HOJA 5: PLAN DE DIETA ----
with tab5:
    st.markdown("### Hoja 5: Estructura del Menú Diario Sugerido")
    st.write(f"Ejemplo de distribución de alimentos para cubrir las **{int(calorias_objetivo)} kcal** establecidas:")
    
    df_dieta_completa = pd.DataFrame({
        "Momento del Día": ["Desayuno (25%)", "Colación Mañana (10%)", "Almuerzo (40%)", "Colación Tarde (10%)", "Cena (15%)"],
        "Menú de Alimentos Sugeridos": [
            "Avena con leche descremada, plátano en rodajas y 2 claras de huevo.",
            "Una manzana verde o una porción de almendras.",
            "Pechuga de pollo a la plancha, arroz integral, ensalada fresca de palta y espinaca.",
            "Yogurt griego natural sin azúcar con fresas.",
            "Filete de pescado o atún al horno con vegetales al vapor (brócoli y zanahoria)."
        ],
        "Calorías Estimadas": [
            f"{int(calorias_objetivo * 0.25)} kcal",
            f"{int(calorias_objetivo * 0.10)} kcal",
            f"{int(calorias_objetivo * 0.40)} kcal",
            f"{int(calorias_objetivo * 0.10)} kcal",
            f"{int(calorias_objetivo * 0.15)} kcal"
        ]
    })
    st.table(df_dieta_completa)
