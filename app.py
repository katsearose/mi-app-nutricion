import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="App Interactiva Nutrición", layout="centered", page_icon="🍎")

st.title("🍎 App Interactiva: Sistema de Nutrición")
st.write("Esta aplicación web interactiva procesa los datos en tiempo real para tu proyecto de 5° 'C'.")

# Formulario interactivo en la pantalla
st.subheader("📝 Ficha de Ingreso Digital")
col_f1, col_f2 = st.columns(2)

with col_f1:
    peso = st.number_input("Peso (kg):", min_value=10.0, max_value=250.0, value=45.0, step=0.1)
    edad = st.number_input("Edad (años):", min_value=1, max_value=120, value=24, step=1)
    estatura = st.number_input("Estatura (cm):", min_value=50, max_value=250, value=165, step=1)

with col_f2:
    genero = st.selectbox("Género:", ["Mujer", "Hombre"], index=0)
    actividad = st.selectbox("Actividad física:", ["Sedentario", "Ligero", "Moderado", "Intensa"], index=2)
    objetivo = st.selectbox("Objetivo nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)

st.markdown("---")

# CÁLCULOS EN VIVO (Simulando las fórmulas exactas de tu Excel)
estatura_m = estatura / 100.0
imc = peso / (estatura_m ** 2)

if imc < 18.5:
    clasificacion_imc = "Bajo peso"
elif 18.5 <= imc < 25:
    clasificacion_imc = "Normopeso / Saludable"
elif 25 <= imc < 30:
    clasificacion_imc = "Sobrepeso"
else:
    clasificacion_imc = "Obesidad"

# Fórmula de Harris-Benedict para TMB
if genero == "Mujer":
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
else:
    tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5

# Factor de actividad
factores = {"Sedentario": 1.2, "Ligero": 1.375, "Moderado": 1.55, "Intensa": 1.725}
gasto_total = tmb * factores[actividad]

# Calorías objetivo según plan
if objetivo == "Bajar de peso":
    calorias_final = gasto_total - 350
elif objetivo == "Subir de peso":
    calorias_final = gasto_total + 350
else:
    calorias_final = gasto_total

# --- MOSTRAR LOS RESULTADOS EN PANTALLA ---
st.subheader("📊 Visualización de Hojas de Evaluación")

# Tarjetas principales
col1, col2 = st.columns(2)
with col1:
    st.metric(label="⚖️ Índice de Masa Corporal (IMC)", value=f"{imc:.1f}", delta=clasificacion_imc, delta_color="normal")
with col2:
    st.metric(label="⚡ Calorías Objetivo Diarias", value=f"{int(calorias_final)} kcal")

st.markdown("### 📋 Tablas Completas del Sistema")

# Creación de las pestañas interactivas solicitadas
tab1, tab2, tab3 = st.tabs(["2.- INDICE DE MASA CORPORAL", "3.- TASA METABÓLICA (TMB)", "5.- CÁLCULO DE DIETA"])

with tab1:
    st.markdown("**Valores calculados para la hoja de IMC:**")
    datos_imc = {
        "Indicador": ["Peso Registrado", "Estatura Convertida", "IMC Calculado", "Estado Nutricional"],
        "Resultado": [f"{peso} kg", f"{estatura_m:.2f} m", f"{imc:.1f}", clasificacion_imc]
    }
    st.table(pd.DataFrame(datos_imc))
    
with tab2:
    st.markdown("**Cálculo de Tasa Metabólica Basal (Fórmulas del Grupo):**")
    datos_tmb_valores = {
        "Concepto": ["TMB Basal (Reposo)", "Factor de Actividad Aplicado", "Gasto Energético Total"],
        "Valor Diario": [f"{tmb:.1f} kcal", f"{factores[actividad]} ({actividad})", f"{gasto_total:.1f} kcal"]
    }
    st.table(pd.DataFrame(datos_tmb_valores))
    
with tab3:
    st.markdown("**Distribución de Macronutrientes sugerida para la dieta:**")
    # Distribución estándar basada en las calorías finales
    prot_g = (calorias_final * 0.25) / 4
    carb_g = (calorias_final * 0.50) / 4
    gras_g = (calorias_final * 0.25) / 9
    
    datos_dieta = {
        "Nutriente": ["Proteínas", "Carbohidratos", "Grasas", "Total Diario"],
        "Porcentaje (%)": ["25%", "50%", "25%", "100%"],
        "Aporte Recomendado": [f"{prot_g:.1f} g", f"{carb_g:.1f} g", f"{gras_g:.1f} g", f"{int(calorias_final)} kcal"]
    }
    st.table(pd.DataFrame(datos_dieta))
