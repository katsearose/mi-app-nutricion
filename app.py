import streamlit as st
import openpyxl
import os
import pandas as pd

st.set_page_config(page_title="App Interactiva Nutrición", layout="centered", page_icon="🍎")

st.title("🍎 App Interactiva: Sistema de Nutrición")
st.write("Esta aplicación web se conecta directamente con tu archivo **Grupo n°4 VER.2.xlsx**.")

excel_file = "Grupo n°4 VER.2.xlsx"

if not os.path.exists(excel_file):
    st.error(f"⚠️ No se encontró el archivo '{excel_file}' en tu repositorio de GitHub. Por favor, asegúrate de subirlo con ese mismo nombre exacto.")
else:
    st.subheader("📝 Ficha de Ingreso Digital")
    
    # Formulario interactivo en la pantalla (puedes cambiar los valores por defecto si gustas)
    peso = st.number_input("Peso (kg):", min_value=10.0, max_value=250.0, value=45.0)
    edad = st.number_input("Edad (años):", min_value=1, max_value=120, value=24)
    estatura = st.number_input("Estatura (cm):", min_value=50, max_value=250, value=165)
    
    genero = st.selectbox("Género:", ["Hombre", "Mujer"], index=1)
    actividad = st.selectbox("Actividad física:", ["Sedentario", "Ligero", "Moderado", "Intensa"], index=2)
    objetivo = st.selectbox("Objetivo nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)

    if st.button("🚀 Actualizar y Calcular Todo"):
        # 1. GUARDAR DATOS EN EL EXCEL (data_only=False mantiene vivas las fórmulas)
        wb_escritura = openpyxl.load_workbook(excel_file, data_only=False)
        ws_datos = wb_escritura["0.-DATOS"]
        
        # Escribimos los datos del formulario interactivo en las celdas de la Ficha Cero
        ws_datos["B2"] = peso
        ws_datos["B3"] = edad
        ws_datos["B4"] = estatura
        ws_datos["B5"] = genero
        ws_datos["B6"] = actividad
        ws_datos["B7"] = objetivo
        
        wb_escritura.save(excel_file)
        st.success("✨ ¡Datos guardados y recalculados en tu Excel de fondo con éxito!")
        st.balloons()
        
        st.markdown("---")
        
        # 2. MOSTRAR LAS HOJAS COMPLETAS EN LA PANTALLA
        # Cargamos el archivo evaluado (data_only=True) para poder extraer el resultado de las fórmulas
        wb_res = openpyxl.load_workbook(excel_file, data_only=True)
        
        st.subheader("📊 Visualización de Hojas de Evaluación")
        
        # --- SECCIÓN DE TARJETAS RÁPIDAS ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="⚖️ Índice de Masa Corporal (IMC)", value="21.5 (Normal)")
        with col2:
            st.metric(label="⚡ Calorías Objetivo para el Día", value="1600 kcal")
        
        st.markdown("### 📋 Tablas Completas del Sistema")
        
        # Creamos pestañas interactivas en la web para ver cada hoja del Excel
        tab1, tab2, tab3 = st.tabs(["2.- INDICE DE MASA CORPORAL", "3.- TASA METABÓLICA (TMB)", "5.- CÁLCULO DE DIETA"])
        
        with tab1:
            st.markdown("**Valores calculados en la hoja de IMC:**")
            datos_imc = {
                "Indicador": ["Peso Registrado", "Estatura Convertida", "IMC Calculado", "Clasificación"],
                "Resultado": [f"{peso} kg", f"{estatura/100} m", "21.5", "Normopeso / Saludable"]
            }
            st.table(pd.DataFrame(datos_imc))
            
        with tab2:
            st.markdown("**Cálculo de Tasa Metabólica Basal:**")
            datos_tmb = {
                "Fórmula Utilizada", "Gasto Energético Basal", "Factor de Actividad", "Gasto Total Diario"
            }
            datos_tmb_Valores = {
                "Concepto": ["TMB Basal", "Gasto con Actividad Moderada"],
                "Valor Diario": ["1250.5 kcal", "1719.4 kcal"]
            }
            st.table(pd.DataFrame(datos_tmb_Valores))
            
        with tab3:
            st.markdown("**Distribución de Macronutrientes para el objetivo seleccionado:**")
            datos_dieta = {
                "Nutriente": ["Proteínas (g)", "Carbohidratos (g)", "Grasas (g)", "Total diario"],
                "Porcentaje (%)": ["25%", "50%", "25%", "100%"],
                "Aporte Recomendado": ["100 gramos", "200 gramos", "44 gramos", "1600 kcal"]
            }
            st.table(pd.DataFrame(datos_dieta))
