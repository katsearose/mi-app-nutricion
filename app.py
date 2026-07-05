import streamlit as st
import pandas as pd

st.set_page_config(page_title="Proyecto Sana Alimentación", layout="wide", page_icon="🍎")

st.title("PROYECTO: SANA ALIMENTACIÓN")
st.subheader("SANTA MARIA REINA 5\"C\" SECUNDARIA")

st.markdown("*La mejor nutrición es aquella que te hace sentir bien por dentro y por fuera a largo plazo*")
st.write("Esta aplicación web interactiva procesa los datos en tiempo real")
st.markdown("---")

st.sidebar.header("📝 Ficha de Ingreso Digital")
peso = st.sidebar.number_input("Peso Actual (kg):", min_value=10.0, max_value=250.0, value=58.0, step=0.1)
estatura = st.sidebar.number_input("Estatura (cm):", min_value=50, max_value=250, value=160, step=1)
edad = st.sidebar.number_input("Edad (años):", min_value=1, max_value=120, value=16, step=1)
genero = st.sidebar.selectbox("Género:", ["Mujer", "Hombre"], index=0)
actividad = st.sidebar.selectbox("Nivel de Actividad Física:", ["Sedentario", "Ligero", "Moderado", "Intenso"], index=2)
objetivo = st.sidebar.selectbox("Objetivo Nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)

estatura_m = estatura / 100.0
imc = peso / (estatura_m ** 2)

if imc < 18.5:
    estado_imc = "Bajo peso"
elif 18.5 <= imc < 25:
    estado_imc = "Normopeso / Saludable"
elif 25 <= imc < 30:
    estado_imc = "Sobrepeso"
else:
    estado_imc = "Obesidad"

if genero == "Mujer":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5

dict_actividad = {
    "Sedentario": 1.2,
    "Ligero": 1.375,
    "Moderado": 1.55,
    "Intenso": 1.725
}
gasto_total = tmb * dict_actividad[actividad]

if objetivo == "Bajar de peso":
    calorias_objetivo = gasto_total - 400
elif objetivo == "Subir de peso":
    calorias_objetivo = gasto_total + 400
else:
    calorias_objetivo = gasto_total

st.subheader("📋 Navegación por Hojas de Evaluación del Sistema")
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 0.- DATOS", 
    "🩺 1.- EXAMEN MEDICO", 
    "⚖️ 2.- IMC", 
    "⚡ 3.- TASA METABÓLICA", 
    "📊 4.- REQUERIMIENTO MACROS", 
    "🍽️ 5.- PLAN DE DIETA"
])

with tab0:
    st.markdown("### Hoja 0: Variables Generales de Control")
    df_hoja0 = pd.DataFrame({
        "Variable": ["Peso Corporal", "Estatura Ingresada", "Edad Cronológica", "Género", "Factor de Actividad", "Meta Principal"],
        "Valor": [f"{peso} kg", f"{estatura} cm", f"{edad} años", genero, actividad, objetivo]
    })
    st.table(df_hoja0)

with tab1:
    st.markdown("### Hoja 1: Ficha Clínico - Nutricional Estructurada")
    datos_examen = {
        "Parámetro Clínico": ["Hemoglobina", "Triglicéridos", "Glucosa", "Colesterol", "Hierro"],
        "Rango de Referencia": ["12.0 - 16.0 g/dL", "Menor a 150 mg/dL", "70 - 100 mg/dL", "Menor a 200 mg/dL", "60 - 170 µg/dL"],
        "Estado Ideal": ["Normal", "Normal", "Normal", "Normal", "Normal"]
    }
    st.table(pd.DataFrame(datos_examen))

with tab2:
    st.markdown("### Hoja 2: Diagnóstico del Índice de Masa Corporal")
    col_imc1, col_imc2 = st.columns(2)
    with col_imc1:
        st.metric(label="Tu Índice de Masa Corporal (IMC)", value=f"{imc:.2f} kg/m²")
    with col_imc2:
        st.metric(label="Clasificación Oficial", value=estado_imc)
        
    tabla_rangos_imc = pd.DataFrame({
        "Clasificación OMS": ["Bajo Peso", "Normopeso (Saludable)", "Sobrepeso", "Obesidad"],
        "Rango de IMC": ["Menor a 18.5", "18.5 a 24.9", "25.0 a 29.9", "Mayor a 30.0"],
        "Tu Estado": ["⬅️" if estado_imc == "Bajo peso" else "", 
                      "⬅️" if estado_imc == "Normopeso / Saludable" else "", 
                      "⬅️" if estado_imc == "Sobrepeso" else "", 
                      "⬅️" if estado_imc == "Obesidad" else ""]
    })
    st.table(tabla_rangos_imc)

with tab3:
    st.markdown("### Hoja 3: Cálculo de Tasa Metabólica")
    datos_tmb = pd.DataFrame({
        "Concepto Energético": ["Tasa Metabólica Basal (Reposo)", "Factor de Actividad Multiplicador", "Gasto Energético Total Diario"],
        "Cálculo (kcal)": [f"{tmb:.1f}", f"x {dict_actividad[actividad]}", f"{gasto_total:.1f}"]
    })
    st.table(datos_tmb)

with tab4:
    st.markdown("### Hoja 4: Requerimiento de Macronutrientes")
    st.metric(label="Calorías Meta Según Objetivo", value=f"{int(calorias_objetivo)} kcal")
    
    prot_g = (calorias_objetivo * 0.25) / 4
    carb_g = (calorias_objetivo * 0.50) / 4
    gras_g = (calorias_objetivo * 0.25) / 9
    
    datos_macros = pd.DataFrame({
        "Macronutriente": ["Proteínas (25%)", "Carbohidratos (50%)", "Grasas (25%)"],
        "Aporte en Gramos": [f"{prot_g:.1f} g", f"{carb_g:.1f} g", f"{gras_g:.1f} g"],
        "Aporte en Kcal": [f"{calorias_objetivo * 0.25:.1f} kcal", f"{calorias_objetivo * 0.50:.1f} kcal", f"{calorias_objetivo * 0.25:.1f} kcal"]
    })
    st.table(datos_macros)

with tab5:
    st.markdown("### Hoja 5: Plan de Dieta (Ejemplo de Distribución)")
    datos_dieta = pd.DataFrame({
        "Comida": ["Desayuno", "Almuerzo", "Cena"],
        "Proteína": [f"{prot_g * 0.30:.1f} g", f"{prot_g * 0.40:.1f} g", f"{prot_g * 0.30:.1f} g"],
        "Carbohidrato": [f"{carb_g * 0.30:.1f} g", f"{carb_g * 0.50:.1f} g", f"{carb_g * 0.20:.1f} g"],
        "Grasas": [f"{gras_g * 0.33:.1f} g", f"{gras_g * 0.33:.1f} g", f"{gras_g * 0.34:.1f} g"]
    })
    st.table(datos_dieta)
