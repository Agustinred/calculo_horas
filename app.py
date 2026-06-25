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

# Función interna de normalización para asegurar consistencia en el cruce
def normalizar_texto_local(texto):
    if not texto or pd.isna(texto):
        return ""
    import unicodedata
    texto = str(texto).strip().upper()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

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
    accept_multiple_files=False,
    key="uploader_asistencia"
)

# Nuevo Cargador Opcional para la Base de Permisos (Desagregada)
uploaded_file_permisos = st.sidebar.file_uploader(
    "Selecciona archivo de Permisos (Opcional)",
    type=['xlsx', 'xls'],
    accept_multiple_files=False,
    key="uploader_permisos"
)

if not archivos_subidos:
    st.info("📤 Carga un archivo Excel para comenzar")
    st.markdown("""
    **Requisitos del archivo:**
    - Hoja1: Datos de marcación (Nombre, DiaSemana, HoraEntrada, HoraSalida, etc.)
    - Hoja2: Catálogo (NOMBRE, GERENCIA)
    """)
    st.stop()

# Procesamiento de la Base de Permisos Externa (si fue cargada)
df_permisos_dict = {}

if uploaded_file_permisos:
    try:
        df_p = pd.read_excel(uploaded_file_permisos)
        
        # Sanitizar columnas de nombres separados de la captura real
        df_p['Nombres'] = df_p['Nombres'].fillna('').astype(str).str.strip()
        df_p['ApellidoPaterno'] = df_p['ApellidoPaterno'].fillna('').astype(str).str.strip()
        df_p['ApellidoMaterno'] = df_p['ApellidoMaterno'].fillna('').astype(str).str.strip()
        
        # Concatenar Nombre Completo (Nombres + Apellidos)
        df_p['Nombre_Completo_Raw'] = (
            df_p['Nombres'] + " " + 
            df_p['ApellidoPaterno'] + " " + 
            df_p['ApellidoMaterno']
        ).str.replace(r'\s+', ' ', regex=True).str.strip()
        
        # Normalizar string para coincidencia exacta con Hoja1
        df_p['Nombre_Normalizado'] = df_p['Nombre_Completo_Raw'].apply(normalizar_texto_local)
        
        # Formatear FechaInicio a string YYYY-MM-DD
        df_p['Fecha_Str'] = pd.to_datetime(df_p['FechaInicio'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Poblar diccionario optimizado de mapeo
        for _, row in df_p.iterrows():
            if pd.isna(row['Fecha_Str']) or not row['Nombre_Normalizado']:
                continue
                
            key = (row['Nombre_Normalizado'], row['Fecha_Str'])
            cantidad_raw = row['CantidadEnHora']
            minutos = 0
            
            if pd.notna(cantidad_raw):
                cantidad_str = str(cantidad_raw).strip()
                partes = cantidad_str.split(':')
                
                if len(partes) >= 2:
                    try:
                        minutos = int(partes[0]) * 60 + int(partes[1])
                    except ValueError:
                        minutos = 0
                else:
                    try:
                        minutos = int(float(cantidad_str) * 60)
                    except ValueError:
                        minutos = 0
            
            if key in df_permisos_dict:
                df_permisos_dict[key] += minutos
            else:
                df_permisos_dict[key] = minutos
                
        st.sidebar.success(f"✅ Se cargaron {len(df_permisos_dict)} registros de permisos.")
    except Exception as e:
        st.sidebar.error(f"⚠️ Nota sobre permisos: No se pudo procesar el archivo opcional ({e})")

# Procesar archivo principal de asistencia
archivo = archivos_subidos

with st.spinner("Procesando archivo..."):
    df_h1, df_h2, fecha_mes, errores = DataLoader.cargar_excel(archivo)
    
    if errores:
        for error in errores:
            st.error(error)
        st.stop()
    
    # 🛠️ SANITIZACIÓN DE DATOS ANTES DE PASAR A LA CALCULADORA 🛠️
    if 'DiaPalabra' in df_h1.columns:
        df_h1['DiaSemana'] = df_h1['DiaPalabra'].astype(str)
    else:
        columnas_lower = {c.lower(): c for c in df_h1.columns}
        if 'diapalabra' in columnas_lower:
            df_h1['DiaSemana'] = df_h1[columnas_lower['diapalabra']].astype(str)
            
    if 'Observacion' in df_h1.columns:
        df_h1['Observacion'] = df_h1['Observacion'].fillna('').astype(str).str.strip()
        
    # Garantizar columnas de normalización en el DataFrame principal
    if 'Nombre_Normalizado' not in df_h1.columns:
        df_h1['Nombre_Normalizado'] = df_h1['Nombre'].apply(normalizar_texto_local)
        
    if 'Nombre_Normalizado' not in df_h2.columns:
        col_cat_nombre = 'NOMBRE' if 'NOMBRE' in df_h2.columns else 'Nombre'
        if col_cat_nombre in df_h2.columns:
            df_h2['Nombre_Normalizado'] = df_h2[col_cat_nombre].apply(normalizar_texto_local)

    # 🔄 CONTROL DE EXCEPCIONES Y LLAMADA COMPATIBLE CON LA CALCULADORA 🔄
    try:
        # Intenta pasar el diccionario completo si la función ya fue actualizada en calculator.py
        resultados, alertas = HorasCalculator.procesar_todos(df_h1, df_h2, dict_permisos=df_permisos_dict)
    except TypeError:
        # Si calculator.py no se ha actualizado todavía, procesa normalmente sin tumbar la app
        resultados, alertas = HorasCalculator.procesar_todos(df_h1, df_h2)
        if df_permisos_dict:
            st.warning("⚠️ El archivo de permisos se cargó, pero `modules/calculator.py` aún no está modificado para procesarlo.")

st.success("✅ Archivo cargado correctamente")

if fecha_mes:
    st.subheader(f"📅 Período: {fecha_mes.strftime('%B de %Y')}")

# Alertas
if alertas:
    st.subheader(f"⚠️ Alertas de Marcación ({len(alertas)} encontradas)")
    with st.expander("Ver alertas", expanded=len(alertas) <= 5):
        for alerta in alertas:
            st.warning(alerta)

# FILTROS
st.subheader("🔍 Filtros")

gerencias_unicas = sorted(set([r['gerencia'] for r in resultados.values() if r.get('gerencia')]))
juridicas_unicas = sorted(set([r['c_juridica'] for r in resultados.values() if r.get('c_juridica') and r.get('c_juridica') != 'N/A']))
nombres_unicos = sorted(set([r['nombre'] for r in resultados.values()]))

col1, col2, col3 = st.columns(3)

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

with col3:
    filtro_nombre = st.multiselect(
        "Nombre",
        options=nombres_unicos,
        default=nombres_unicos,
        key="filtro_nombre"
    )

# TABLA DE RESUMEN
st.subheader("📊 Resumen de Cumplimiento Horario")

df_resumen = Formatter.crear_df_resumen(
    resultados,
    filtro_gerencia=filtro_gerencia if filtro_gerencia else None,
    filtro_juridica=filtro_juridica if filtro_juridica else None
)

if filtro_nombre:
    df_resumen = df_resumen[df_resumen['Nombre'].isin(filtro_nombre)]

if len(df_resumen) == 0:
    st.warning("⚠️ No hay datos con los filtros seleccionados")
    st.stop()

st.dataframe(df_resumen, use_container_width=True, height=400)

# ESTADÍSTICAS
st.subheader("📈 Estadísticas")

col1, col2, col3, col4 = st.columns(4)

total_empleados = len(df_resumen)
empleados_completos = len([r for r in resultados.values() 
                          if r['nombre'] in df_resumen['Nombre'].values 
                          and r['total_minutos_mes'] >= 0])
empleados_incompletos = total_empleados - empleados_completos
total_minutos_faltantes = sum([r['total_minutos_mes'] for r in resultados.values() 
                              if r['nombre'] in df_resumen['Nombre'].values
                              and r['total_minutos_mes'] < 0])

with col1:
    st.metric("Total Empleados", total_empleados)
with col2:
    st.metric("Cumplimiento", f"{empleados_completos}/{total_empleados}")
with col3:
    st.metric("Incompletos", empleados_incompletos)
with col4:
    horas_faltantes = abs(total_minutos_faltantes) // 60
    mins_faltantes = abs(total_minutos_faltantes) % 60
    st.metric("Faltantes Total", f"{horas_faltantes}:{mins_faltantes:02d}")

# VISTA DETALLADA POR FUNCIONARIO
st.subheader("👤 Detalles por Funcionario")

funcionarios_filtrados = df_resumen['Nombre'].tolist()

if len(funcionarios_filtrados) > 0:
    funcionario_seleccionado = st.selectbox(
        "Selecciona funcionario para ver detalles",
        options=funcionarios_filtrados,
        key="funcionario_selector"
    )
    
    if funcionario_seleccionado:
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
                
                if total_mes <= -60:
                    estado = "❌"
                elif total_mes < 0:
                    estado = "⚠️"
                else:
                    estado = "✅"
                
                st.metric("Total Mes", f"{estado} {texto_total}")
            
            st.markdown("---")
            st.markdown("**📋 Detalles de Horas:**")
            
            semanas_disponibles = sorted(resultado_funcionario['semanas'].keys())
            col1, col2 = st.columns([2, 1])
            
            with col1:
                opcion_vista = st.radio(
                    "Vista:",
                    options=["Seleccionar Semana", "Ver Todas las Semanas"],
                    horizontal=True,
                    key="opcion_vista"
                )
            
            if opcion_vista == "Seleccionar Semana":
                semana_seleccionada = st.selectbox(
                    "Semana:",
                    options=semanas_disponibles,
                    key="semana_selector"
                )
                semanas_a_mostrar = [semana_seleccionada]
            else:
                semanas_a_mostrar = semanas_disponibles
            
            for semana_num in semanas_a_mostrar:
                semana_info = resultado_funcionario['semanas'][semana_num]
                diferencia = semana_info['diferencia_minutos']
                minutos_trabajados = semana_info['minutos_trabajados']
                meta = semana_info['minutos_esperados']
                es_parcial = semana_info.get('es_parcial', False)
                
                color, estado = Formatter.determinar_color_semana(diferencia)
                texto_diferencia = Formatter._minutos_a_hora_texto(diferencia)
                texto_trabajado = Formatter._minutos_a_hora_texto(minutos_trabajados)
                texto_meta = Formatter._minutos_a_hora_texto(meta)
                
                marca_parcial = " (Semana Parcial)" if es_parcial else ""
                
                st.markdown(f"""
                <div style="background-color: {color}; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <h4>Semana {semana_num}{marca_parcial}</h4>
                    <p><strong>Trabajadas:</strong> {texto_trabajado} | <strong>Meta:</strong> {texto_meta} | <strong>Diferencia:</strong> {texto_diferencia} {estado}</p>
                </div>
                """, unsafe_allow_html=True)
                
                df_detalle = Formatter.crear_df_detalle_semana(semana_info['días'])
                st.dataframe(df_detalle, use_container_width=True, hide_index=True)
                st.markdown("---")

# EXPORTACIÓN
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
