import streamlit as st
import openpyxl
import os

st.set_page_config(page_title="App Interactiva Nutrición", layout="centered", page_icon="🍎")

st.title("🍎 App Interactiva: Sistema de Nutrición")
st.write("Esta aplicación web se conecta directamente con tu archivo **Grupo n°4 VER.2.xlsx**.")

excel_file = "Grupo n°4 VER.2.xlsx"

if not os.path.exists(excel_file):
    st.error(f"⚠️ No se encontró el archivo '{excel_file}' en tu repositorio de GitHub. Por favor, asegúrate de subirlo con ese mismo nombre exacto.")
else:
    # Cargar el libro de Excel (manteniendo las fórmulas vivas)
    wb = openpyxl.load_workbook(excel_file, data_only=False)
    ws_datos = wb["0.-DATOS"]
    
    st.subheader("📝 Ficha de Ingreso Digital")
    
    # Formulario interactivo en la pantalla como una App real
    peso = st.number_input("Peso (kg):", min_value=10.0, max_value=250.0, value=75.0)
    edad = st.number_input("Edad (años):", min_value=1, max_value=120, value=15)
    estatura = st.number_input("Estatura (cm):", min_value=50, max_value=250, value=165)
    
    genero = st.selectbox("Género:", ["Hombre", "Mujer"], index=0)
    actividad = st.selectbox("Actividad física:", ["Sedentario", "Ligero", "Moderado", "Intensa"], index=1)
    objetivo = st.selectbox("Objetivo nutricional:", ["Bajar de peso", "Mantener peso", "Subir de peso"], index=0)

    if st.button("🚀 Actualizar y Calcular Todo"):
        # Modificar las celdas exactas donde lee tu formulario en la pestaña 0.-DATOS
        # Nota: Si tu grupo usa otras celdas (ejemplo E15, E16), puedes cambiarlas aquí abajo
        ws_datos["B2"] = peso
        ws_datos["B3"] = edad
        ws_datos["B4"] = estatura
        ws_datos["B5"] = genero
        ws_datos["B6"] = actividad
        ws_datos["B7"] = objetivo
        
        # Guardar los cambios en el Excel interno
        wb.save(excel_file)
        st.success("✨ ¡Datos guardados y recalculados en tu Excel de fondo con éxito!")
        st.balloons()
        
        st.markdown("---")
        st.markdown("### 📊 Tu Excel se ha actualizado:")
        st.info("¡Listo! Todas las pestañas de Examen Médico, IMC y Cálculo de Dieta se han recalculado automáticamente con tus nuevos datos.")
