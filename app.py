import streamlit as st
import pandas as pd
from modules.data_loader import DataLoader
from modules.calculator import HorasCalculator
from modules.formatter import Formatter
from modules.exporter import Exporter

st.set_page_config(
    page_title="DTPM - Cálculo de Horas",
    page_icon="⏱️",
    layout="wide"
)

st.markdown("""
    <style>
        .title-section {
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="title-section">
        <h1>⏱️ DTPM - Herramienta de Cálculo de Horas</h1>
        <p>Análisis de cumplimiento horario de funcionarios</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("📁 Carga de Archivos")
st.sidebar.info("Carga un archivo Excel con Hoja1 y Hoja2")

archivos_subidos = st.sidebar.file_uploader(
    "Selecciona archivo(s) Excel",
    type=['xlsx', 'xls'],
    accept_multiple_files=False
)

if not archivos_subidos:
    st.info("📤 Carga un archivo Excel para comenzar")
    st.markdown("""
    **Requisitos del archivo:**
    - Hoja1: Datos de marcación (Nombre, DiaSemana, HoraEntrada, HoraSalida, etc.)
    - Hoja2: Catálogo (NOMBRE, GERENCIA)
    """)
    st.stop()

# Procesar archivo
archivo = archivos_subidos

with st.spinner("Procesando archivo..."):
    df_h1, df_h2, fecha_mes, errores = DataLoader.cargar_excel(archivo)
    
    if errores:
        for error in errores:
            st.error(error)
        st.stop()
    
    resultados, alertas = HorasCalculator.procesar_todos(df_h1, df_h2)

st.success("✅ Archivo cargado correctamente")

if fecha_mes:
    st.subheader(f"📅 Período: {fecha_mes.strftime('%B de %Y')}")

# Alertas
if alertas:
    st.subheader(f"⚠️ Alertas de Marcación ({len(alertas)} encontradas)")
    with st.expander("Ver alertas", expanded=len(alertas) <= 5):
        for alerta in alertas:
            st.warning(alerta)

# Filtros
st.subheader("🔍 Filtros")

gerencias_unicas = sorted(set([r['gerencia'] for r in resultados.values() if r.get('gerencia')]))
juridicas_unicas = sorted(set([r['c_juridica'] for r in resultados.values() if r.get('c_juridica') and r.get('c_juridica') != 'N/A']))

col1, col2 = st.columns(2)

with col1:
    filtro_gerencia = st.multiselect(
        "Gerencia",
        options=gerencias_unicas,
        default=gerencias_unicas,
        key="filtro_gerencia"
    )

with col2:
    filtro_juridica = st.multiselect(
        "Calidad Jurídica",
        options=juridicas_unicas,
        default=juridicas_unicas,
        key="filtro_juridica"
    )

# Tabla
st.subheader("📊 Resumen de Cumplimiento Horario")

df_resumen = Formatter.crear_df_resumen(
    resultados,
    filtro_gerencia=filtro_gerencia if filtro_gerencia else None,
    filtro_juridica=filtro_juridica if filtro_juridica else None
)

if len(df_resumen) == 0:
    st.warning("⚠️ No hay datos con los filtros seleccionados")
    st.stop()

st.dataframe(df_resumen, use_container_width=True, height=400)

# Estadísticas
st.subheader("📈 Estadísticas")

col1, col2, col3, col4 = st.columns(4)

total_empleados = len(df_resumen)
empleados_completos = len([r for r in resultados.values() if r['total_minutos_mes'] >= 0])
empleados_incompletos = total_empleados - empleados_completos
total_minutos_faltantes = sum([r['total_minutos_mes'] for r in resultados.values() if r['total_minutos_mes'] < 0])

with col1:
    st.metric("Total Empleados", total_empleados)
with col2:
    porcentaje = (empleados_completos / total_empleados * 100) if total_empleados > 0 else 0
    st.metric("Cumplimiento", f"{empleados_completos}/{total_empleados}")
with col3:
    st.metric("Incompletos", empleados_incompletos)
with col4:
    horas_faltantes = abs(total_minutos_faltantes) // 60
    mins_faltantes = abs(total_minutos_faltantes) % 60
    st.metric("Faltantes Total", f"{horas_faltantes}:{mins_faltantes:02d}")

# Exportar
st.subheader("📥 Exportar Resultados")

col1, col2, col3 = st.columns(3)

with col1:
    csv_data = Exporter.exportar_csv(df_resumen)
    st.download_button(
        "📄 Descargar CSV",
        csv_data,
        f"horas_{archivo.name.split('.')[0]}.csv",
        "text/csv",
        use_container_width=True
    )

with col2:
    excel_data = Exporter.exportar_excel(df_resumen)
    st.download_button(
        "📊 Descargar Excel",
        excel_data,
        f"horas_{archivo.name.split('.')[0]}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col3:
    html_data = Exporter.exportar_html(df_resumen)
    st.download_button(
        "🌐 Descargar HTML",
        html_data,
        f"horas_{archivo.name.split('.')[0]}.html",
        "text/html",
        use_container_width=True
    )
