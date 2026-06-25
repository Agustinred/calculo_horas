import streamlit as st

st.set_page_config(page_title="DTPM - Test", page_icon="⏱️")

st.title("⏱️ DTPM - Herramienta de Cálculo de Horas")
st.write("✅ App cargada correctamente")

st.subheader("🧪 Diagnóstico de módulos:")

# Test 1: Importar data_loader
try:
    from modules.data_loader import DataLoader
    st.success("✅ data_loader.py importado correctamente")
except Exception as e:
    st.error(f"❌ Error en data_loader.py: {str(e)}")

# Test 2: Importar calculator
try:
    from modules.calculator import HorasCalculator
    st.success("✅ calculator.py importado correctamente")
except Exception as e:
    st.error(f"❌ Error en calculator.py: {str(e)}")

# Test 3: Importar formatter
try:
    from modules.formatter import Formatter
    st.success("✅ formatter.py importado correctamente")
except Exception as e:
    st.error(f"❌ Error en formatter.py: {str(e)}")

# Test 4: Importar exporter
try:
    from modules.exporter import Exporter
    st.success("✅ exporter.py importado correctamente")
except Exception as e:
    st.error(f"❌ Error en exporter.py: {str(e)}")

st.subheader("Si ves 4 checkmarks verdes, todo está bien ✅")
