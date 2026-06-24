"""
app.py - Aplicación principal Streamlit para cálculo de horas DTPM
"""

import streamlit as st
import pandas as pd
from modules.data_loader import DataLoader
from modules.calculator import HorasCalculator
from modules.formatter import Formatter
from modules.exporter import Exporter
from io import BytesIO


# Configuración de página
st.set_page_config(
    page_title="DTPM - Cálculo de Horas",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .title-section {
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        .alert-box {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        .alert-error {
            background-color: #ffebee;
            border-left: 4px solid #f44336;
            color: #c62828;
        }
        .alert-warning {
            background-color: #fff3e0;
            border-left: 4px solid #ff9800;
            color: #e65100;
        }
        .alert-success {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            color: #2e7d32;
        }
        .metric-container {
            background-color: #f0f2f6;
            padding: 1.5rem;
            border-radius: 0.5rem;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# Inicializar estado de sesión
if 'datos_procesados' not in st.session_state:
    st.session_state.datos_procesados = {}

if 'archivos_cargados' not in st.session_state:
    st.session_state.archivos_cargados = {}


def main():
    """Función principal de la aplicación"""
    
    # Header
    st.markdown("""
        <div class="title-section">
            <h1>⏱️ DTPM - Herramienta de Cálculo de Horas</h1>
            <p>Análisis de cumplimiento horario de funcionarios - Red Movilidad</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Cargar archivos
    st.sidebar.header("📁 Carga de Archivos")
    st.sidebar.markdown("""
        Carga uno o múltiples archivos Excel para comparar diferentes meses.
        
        **Requisitos del archivo:**
        - Debe contener Hoja1 y Hoja2
        - Hoja1: Datos de marcación diaria
        - Hoja2: Nombres y Gerencias
    """)
    
    archivos_subidos = st.sidebar.file_uploader(
        "Selecciona archivo(s) Excel",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key='file_uploader'
    )
    
    # Procesar archivos subidos
    meses_disponibles = []
    
    if archivos_subidos:
        for archivo in archivos_subidos:
            nombre_archivo = archivo.name
            
            # Evitar recargar si ya está en caché
            if nombre_archivo not in st.session_state.archivos_cargados:
                with st.sidebar.status(f"Procesando {nombre_archivo}...", expanded=False):
                    
                    # Cargar datos
                    df_h1, df_h2, fecha_mes, errores = DataLoader.cargar_excel(archivo)
                    
                    if errores:
                        for error in errores:
                            st.sidebar.error(error)
                    else:
                        # Procesar horas
                        resultados, alertas = HorasCalculator.procesar_todos(df_h1, df_h2)
                        
                        st.session_state.archivos_cargados[nombre_archivo] = {
                            'df_hoja1': df_h1,
                            'df_hoja2': df_h2,
                            'fecha_mes': fecha_mes,
                            'resultados': resultados,
                            'alertas': alertas,
                            'nombre_archivo': nombre_archivo
                        }
                        
                        st.sidebar.success(f"✅ {nombre_archivo} cargado")
        
        meses_disponibles = list(st.session_state.archivos_cargados.keys())
    
    # Mostrar archivos cargados
    if meses_disponibles:
        st.sidebar.subheader("📊 Archivos Cargados:")
        for i, mes in enumerate(meses_disponibles, 1):
            st.sidebar.markdown(f"{i}. ✅ {mes}")
        
        # Opción para limpiar caché
        if st.sidebar.button("🗑️ Limpiar caché y recargar"):
            st.session_state.archivos_cargados = {}
            st.session_state.datos_procesados = {}
            st.rerun()
    
    # Sección principal
    if not meses_disponibles:
        col1, col2 = st.columns(2)
        with col1:
            st.info("""
                📤 **Para comenzar:**
                
                1. Prepara tu archivo Excel con:
                   - Hoja1: Datos de marcación
                   - Hoja2: Nombres y Gerencias
                
                2. Carga el archivo en el panel izquierdo
                
                3. Analiza los resultados y exporta en tu formato preferido
            """)
        with col2:
            st.info("""
                ℹ️ **Información:**
                
                - Soporta múltiples archivos
                - Cálculo automático de 44 horas semanales
                - Identificación de marcaciones faltantes
                - Exportación en CSV, Excel, HTML
            """)
        return
    
    # ============================================
    # SECCIÓN 1: SELECCIÓN DE MES
    # ============================================
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📅 Selecciona el mes a analizar:")
        mes_seleccionado = st.selectbox(
            "Archivo",
            options=meses_disponibles,
            key='mes_selector',
            label_visibility="collapsed"
        )
    
    with col2:
        st.write("")  # Espaciador
        if st.button("🔄 Recargar", use_container_width=True):
            st.rerun()
    
    if not mes_seleccionado:
        return
    
    # Obtener datos del mes seleccionado
    datos_mes = st.session_state.archivos_cargados[mes_seleccionado]
    resultados = datos_mes['resultados']
    alertas = datos_mes['alertas']
    fecha_mes = datos_mes['fecha_mes']
    
    # Mostrar fecha
    if fecha_mes:
        st.markdown(f"**Período:** {fecha_mes.strftime('%B de %Y')}", help="Fecha extraída del archivo Excel")
    
    # ============================================
    # SECCIÓN 2: ALERTAS DE MARCACIÓN
    # ============================================
    
    if alertas:
        st.subheader("⚠️ Alertas de Marcación Incompleta")
        with st.expander("Ver alertas (" + str(len(alertas)) + " encontradas)", expanded=len(alertas) <= 5):
            for alerta in alertas:
                st.warning(alerta)
    
    # ============================================
    # SECCIÓN 3: FILTROS
    # ============================================
    
    st.subheader("🔍 Filtros")
    
    col1, col2 = st.columns(2)
    
    # Obtener opciones únicas para filtros
    gerencias_unicas = sorted(set([r['gerencia'] for r in resultados.values() if r.get('gerencia')]))
    juridicas_unicas = sorted(set([r['c_juridica'] for r in resultados.values() if r.get('c_juridica') and r.get('c_juridica') != 'N/A']))
    
    with col1:
        filtro_gerencia = st.multiselect(
            "Gerencia",
            options=gerencias_unicas,
            default=gerencias_unicas,
            key=f'gerencia_{mes_seleccionado}'
        )
    
    with col2:
        filtro_juridica = st.multiselect(
            "Calidad Jurídica",
            options=juridicas_unicas,
            default=juridicas_unicas,
            key=f'juridica_{mes_seleccionado}'
        )
    
    # ============================================
    # SECCIÓN 4: TABLA DE RESUMEN
    # ============================================
    
    st.subheader("📊 Resumen de Cumplimiento Horario")
    
    df_resumen = Formatter.crear_df_resumen(
        resultados,
        filtro_gerencia=filtro_gerencia if filtro_gerencia else None,
        filtro_juridica=filtro_juridica if filtro_juridica else None
    )
    
    if len(df_resumen) == 0:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados")
    else:
        # Mostrar tabla con formato
        st.dataframe(
            df_resumen,
            use_container_width=True,
            height=400
        )
        
        # ============================================
        # SECCIÓN 5: ESTADÍSTICAS
        # ============================================
        
        st.subheader("📈 Estadísticas del Período")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_empleados = len(df_resumen)
        empleados_completos = len([r for r in resultados.values() 
                                  if r.get('gerencia') in filtro_gerencia if filtro_gerencia
                                  and r['total_minutos_mes'] >= 0])
        empleados_incompletos = total_empleados - empleados_completos
        total_minutos_faltantes = sum([r['total_minutos_mes'] for r in resultados.values() 
                                      if r['total_minutos_mes'] < 0 and 
                                      (not filtro_gerencia or r.get('gerencia') in filtro_gerencia)])
        
        with col1:
            st.metric("Total Empleados", total_empleados)
        with col2:
            porcentaje = (empleados_completos / total_empleados * 100) if total_empleados > 0 else 0
            st.metric("Cumplimiento", f"{empleados_completos}/{total_empleados} ({porcentaje:.0f}%)")
        with col3:
            st.metric("Incompletos", empleados_incompletos)
        with col4:
            horas_faltantes = abs(total_minutos_faltantes) // 60
            mins_faltantes = abs(total_minutos_faltantes) % 60
            st.metric("Horas Faltantes Total", f"{horas_faltantes}:{mins_faltantes:02d}")
        
        # ============================================
        # SECCIÓN 6: DETALLES POR FUNCIONARIO
        # ============================================
        
        st.subheader("👤 Detalles por Funcionario")
        
        funcionarios_filtrados = df_resumen['Nombre'].tolist()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            funcionario_seleccionado = st.selectbox(
                "Selecciona funcionario para ver detalles",
                options=funcionarios_filtrados,
                key=f'funcionario_{mes_seleccionado}'
            )
        
        if funcionario_seleccionado:
            # Encontrar el resultado del funcionario
            resultado_funcionario = None
            for nombre_norm, resultado in resultados.items():
                if resultado['nombre'] == funcionario_seleccionado:
                    resultado_funcionario = resultado
                    break
            
            if resultado_funcionario:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Gerencia", resultado_funcionario.get('gerencia', 'N/A'))
                with col2:
                    st.metric("Calidad Jurídica", resultado_funcionario.get('c_juridica', 'N/A'))
                with col3:
                    total_mes = resultado_funcionario['total_minutos_mes']
                    texto_total = Formatter._minutos_a_hora_texto(total_mes)
                    st.metric("Total Mes", texto_total)
                
                # Detalles por semana
                st.markdown("**Desglose Semanal:**")
                
                for semana_num in sorted(resultado_funcionario['semanas'].keys()):
                    semana_info = resultado_funcionario['semanas'][semana_num]
                    diferencia = semana_info['diferencia_minutos']
                    minutos_trabajados = semana_info['minutos_trabajados']
                    
                    color, estado = Formatter.determinar_color_semana(diferencia)
                    texto_diferencia = Formatter._minutos_a_hora_texto(diferencia)
                    texto_trabajado = Formatter._minutos_a_hora_texto(minutos_trabajados)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**Semana {semana_num}**")
                    with col2:
                        st.write(f"Trabajadas: {texto_trabajado}")
                    with col3:
                        st.write(f"Diferencia: {texto_diferencia} {estado}")
        
        # ============================================
        # SECCIÓN 7: EXPORTACIÓN
        # ============================================
        
        st.subheader("📥 Exportar Resultados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Exportar CSV
            csv_data = Exporter.exportar_csv(df_resumen)
            st.download_button(
                label="📄 Descargar CSV",
                data=csv_data,
                file_name=f"horas_{mes_seleccionado.split('.')[0]}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Exportar Excel
            excel_data = Exporter.exportar_excel(df_resumen)
            st.download_button(
                label="📊 Descargar Excel",
                data=excel_data,
                file_name=f"horas_{mes_seleccionado.split('.')[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col3:
            # Exportar HTML
            html_data = Exporter.exportar_html(df_resumen)
            st.download_button(
                label="🌐 Descargar HTML",
                data=html_data,
                file_name=f"horas_{mes_seleccionado.split('.')[0]}.html",
                mime="text/html",
                use_container_width=True
            )


if __name__ == "__main__":
    main()
