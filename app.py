import streamlit as st
import pandas as pd

st.set_page_config(page_title="Proyecto Sana Alimentación", layout="wide")

st.title("🥦 Proyecto Sana Alimentación")
st.markdown("¡Bienvenido al sistema de evaluación nutricional! Basado en el Excel oficial del Grupo N°4.")

# Crear las "hojas" del Excel como pestañas de Streamlit
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab10 = st.tabs([
    "0.-DATOS", "1.-EXAMEN MEDICO", "2.-IMC", "3.-TMB", 
    "4.-RCD", "5.-OBJETIVO", "6.-MACRONUTRIENTES", "7.-PORCIONES", "10.-CLIMA CHICLAYO"
])

# --- HOJA 0: DATOS ---
with tab0:
    st.header("¡INTRODUCE TUS DATOS!")
    
    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (en kg)", min_value=1.0, value=75.0, step=0.1)
        edad = st.number_input("Edad (en años)", min_value=1, value=9, step=1)
        estatura = st.number_input("Estatura (en cm)", min_value=50, value=168, step=1)
        genero = st.selectbox("Género", ["Hombre", "Mujer"])
        
    with col2:
        actividad = st.selectbox("Actividad Física", ["Sedentario", "Ligero", "Moderado", "Intensa"])
        objetivo = st.selectbox("Objetivo", ["Bajar de peso", "Mantener peso", "Subir de peso"])
        etapa = st.selectbox("Etapa", ["Adolescencia", "Adulto"])
        
    st.info("¿Cómo saber mi actividad física?\n- **Sedentario**: Solo actividades de la vida diaria.\n- **Ligero**: Ejercicio 1-3 veces/semana.\n- **Moderado**: Ejercicio 3-5 veces/semana.\n- **Intensa**: Ejercicio diario o deportista.")

# --- HOJA 1: EXAMEN MEDICO ---
with tab1:
    st.header("EXAMEN MÉDICO DE SANGRE")
    st.markdown("Datos opcionales para categorizar tu nivel de salud.")
    hemo = st.number_input("Hemoglobina (g/dL)", value=0.0)
    trigli = st.number_input("Triglicéridos (mg/dL)", value=0.0)
    gluco = st.number_input("Glucosa (mg/dL)", value=0.0)
    coles = st.number_input("Colesterol (mg/dL)", value=0.0)
    hierro = st.number_input("Hierro (µg/dL)", value=0.0)

# --- HOJA 2: IMC ---
with tab2:
    st.header("ÍNDICE DE MASA CORPORAL (IMC)")
    altura_m = estatura / 100
    imc = peso / (altura_m ** 2)
    
    st.metric("Resultado IMC", round(imc, 2))
    st.latex(r"IMC = \frac{Peso (kg)}{Altura (m)^2}")
    
    if etapa == "Adolescencia":
        st.warning(f"Como estás en la etapa de {etapa}, el IMC se evalúa mediante **Percentiles** según la edad y género. Te recomendamos revisar la tabla de la OMS para tu percentil exacto.")
    else:
        if imc < 18.5: categoria = "Bajo Peso"
        elif imc < 25: categoria = "Peso Saludable"
        elif imc < 30: categoria = "Sobrepeso"
        elif imc < 35: categoria = "Obesidad de Clase 1"
        elif imc < 40: categoria = "Obesidad de Clase 2"
        else: categoria = "Obesidad de Clase 3"
        st.success(f"Categoría para adultos: **{categoria}**")

# --- HOJA 3: TMB ---
with tab3:
    st.header("TASA METABÓLICA BASAL (TMB)")
    st.markdown("Fórmula de Mifflin-St Jeor.")
    
    if genero == "Hombre":
        tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) + 5
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) + 5")
    else:
        tmb = (10 * peso) + (6.25 * estatura) - (5 * edad) - 161
        st.latex(r"TMB = (10 \times Peso) + (6.25 \times Altura) - (5 \times Edad) - 161")
        
    st.metric("Tu TMB es:", f"{round(tmb)} kcal/día")

# --- HOJA 4: RCD ---
with tab4:
    st.header("REQUERIMIENTO CALÓRICO DIARIO (RCD)")
    
    # Factores según Excel
    factores = {
        "Hombre": {"Sedentario": 1.2, "Ligero": 1.55, "Moderado": 1.8, "Intensa": 2.1},
        "Mujer": {"Sedentario": 1.2, "Ligero": 1.56, "Moderado": 1.64, "Intensa": 1.82}
    }
    factor = factores[genero][actividad]
    rcd = tmb * factor
    
    st.markdown(f"**Factor de actividad aplicado ({actividad}):** {factor}")
    st.latex(r"RCD = TMB \times Factor\ de\ actividad")
    st.metric("Resultado RCD:", f"{round(rcd)} kcal/día")

# --- HOJA 5: OBJETIVO ---
with tab5:
    st.header("CÁLCULO PARA SUBIR, MANTENER O BAJAR EL PESO")
    
    # Lógica de Excel: menores de edad no deben hacer ajuste drástico sin supervisión
    if edad < 18:
        ajuste = 0
        rcd_final = rcd
        st.info("A diferencia de los adultos, el cuerpo de los menores necesita energía constante para el desarrollo de órganos y huesos. El ajuste calórico debe ser controlado.")
    else:
        if objetivo == "Bajar de peso": ajuste = -15  # -15%
        elif objetivo == "Subir de peso": ajuste = 15   # +15%
        else: ajuste = 0
        rcd_final = rcd + (rcd * (ajuste/100))
        
    st.markdown(f"**Objetivo:** {objetivo}")
    if edad >= 18: st.markdown(f"**Ajuste aplicado:** {ajuste}%")
    st.metric("Resultado Final (RCD Ajustado):", f"{round(rcd_final)} kcal/día")

# --- HOJA 6: MACRONUTRIENTES ---
with tab6:
    st.header("CÁLCULO DE LOS MACRONUTRIENTES")
    st.markdown("Distribución: 20% Proteínas, 50% Carbohidratos, 30% Grasas")
    
    cal_prot = rcd_final * 0.20
    cal_carb = rcd_final * 0.50
    cal_gras = rcd_final * 0.30
    
    gr_prot = cal_prot / 4
    gr_carb = cal_carb / 4
    gr_gras = cal_gras / 9
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Proteínas (20%)", f"{round(gr_prot, 1)} g", f"{round(cal_prot, 1)} kcal")
    col2.metric("Carbohidratos (50%)", f"{round(gr_carb, 1)} g", f"{round(cal_carb, 1)} kcal")
    col3.metric("Grasas (30%)", f"{round(gr_gras, 1)} g", f"{round(cal_gras, 1)} kcal")

# --- HOJA 7: PORCIONES ---
with tab7:
    st.header("CÁLCULO DE LAS PORCIONES DEL DÍA")
    porciones = {
        "Desayuno (25%)": rcd_final * 0.25,
        "Merienda 1 (5%)": rcd_final * 0.05,
        "Almuerzo (40%)": rcd_final * 0.40,
        "Merienda 2 (5%)": rcd_final * 0.05,
        "Cena (25%)": rcd_final * 0.25
    }
    
    for comida, calorias in porciones.items():
        st.write(f"**{comida}:** {round(calorias, 1)} kcal")

# --- HOJA 10: CLIMA CHICLAYO ---
with tab10:
    st.header("GASTO ENERGÉTICO AJUSTADO AL CLIMA DE CHICLAYO")
    st.markdown("""
    Según la FAO, vivir en climas cálidos y desérticos continuos como **Chiclayo** genera una adaptación biológica. 
    El cuerpo reduce su tasa metabólica basal para evitar producir calor interno excesivo. 
    Por ello, se aplica un factor de **0.95**, restando automáticamente un (5%) al gasto calórico diario total.
    """)
    
    st.latex(r"RCD_{Chiclayo} = RCD \times 0.95")
    rcd_chiclayo = rcd_final * 0.95
    st.metric("Gasto energético ajustado al clima de Chiclayo:", f"{round(rcd_chiclayo, 1)} kcal/día")
