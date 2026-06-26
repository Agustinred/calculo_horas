import streamlit as st
import pandas as pd
import io
import re
import unicodedata
from modules.data_loader import DataLoader
from modules.calculator import HorasCalculator
from modules.formatter import Formatter
from modules.exporter import Exporter

st.set_page_config(
    page_title="DTPM - Cálculo de Horas",
    page_icon="⏱️",
    layout="wide"
)

# 🔄 FUNCIÓN DE NORMALIZACIÓN
def normalizar_texto_local(texto):
    if not texto or pd.isna(texto):
        return ""
    
    texto = str(texto).upper()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^A-Z\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
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

# Cargador Opcional para la Base de Permisos
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

# =========================================================================
# 🎯 PROCESAMIENTO DE LA BASE DE PERMISOS EXTERNA (SIMPLIFICADO)
# =========================================================================
df_permisos_dict = {}
debug_df_permisos = pd.DataFrame()

if uploaded_file_permisos:
    try:
        df_permisos_dict, debug_df_permisos = DataLoader.construir_dict_permisos(uploaded_file_permisos)
        
        if df_permisos_dict:
            st.sidebar.success(f"✅ Se cargaron {len(df_permisos_dict)} registros de permisos")
        else:
            st.sidebar.warning("⚠️ No se pudieron procesar permisos. Verifica el formato del archivo.")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error al procesar permisos: {str(e)}")

# =========================================================================
# 🔍 PANEL DE DIAGNÓSTICO EN TIEMPO REAL
# =========================================================================
st.subheader("⚙️ Herramienta de Inspección de Cruces en Memoria")
with st.expander("🔍 Analizar Diccionario Global de Permisos Externos", expanded=False):
    if df_permisos_dict:
        st.write(f"📊 **Total de registros clave construidos en memoria:** {len(df_permisos_dict)}")
        
        # Formulario interactivo para auditar tuplas
        st.write("🧪 **Simulador de Búsqueda Manual de Coincidencias:**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            nombre_prueba = st.text_input(
                "Nombre a evaluar (Normalizado):", 
                placeholder="EJ: claudia alejandra abarca manriquez", 
                key="diag_nom_input"
            )
        with col_d2:
            fecha_prueba = st.text_input(
                "Fecha a evaluar (AAAA-MM-DD):", 
                placeholder="EJ: 2026-01-09", 
                key="diag_fec_input"
            )
            
        if nombre_prueba and fecha_prueba:
            llave_prueba = (nombre_prueba.strip().lower(), fecha_prueba.strip())
            st.markdown("---")
            st.write(f"🔎 *Buscando tupla:* `{llave_prueba}`")
            if llave_prueba in df_permisos_dict:
                minutos = df_permisos_dict[llave_prueba]
                horas = minutos / 60
                st.success(f"✅ ¡COINCIDENCIA ENCONTRADA! Valor: {minutos} minutos ({horas:.1f}h)")
            else:
                st.error("❌ La llave no existe en el diccionario.")
        
        st.write("📋 **Vista previa JSON de las primeras 20 llaves:**")
        muestra_dict = {f"{k[0]} | {k[1]}": f"{v} mins ({v/60:.1f}h)" for k, v in list(df_permisos_dict.items())[:20]}
        st.json(muestra_dict)
    else:
        st.info("💡 No hay datos en el diccionario de permisos. Carga un archivo de permisos para poblar el inspector.")

st.markdown("---")

# =========================================================================
# 🔄 PROCESAMIENTO DE ARCHIVOS PRINCIPALES
# =========================================================================
archivo = archivos_subidos

# Cargar datos
df_hoja1, df_hoja2, fecha_mes, errores = DataLoader.cargar_excel(archivo)

if errores:
    for error in errores:
        st.error(error)
    st.stop()

# Procesar todos los funcionarios
resultados, alertas = HorasCalculator.procesar_todos(df_hoja1, df_hoja2, dict_permisos=df_permisos_dict)

# Crear resumen
df_resumen = Formatter.crear_resumen(resultados)

st.subheader("📊 Resumen General")
st.dataframe(df_resumen, use_container_width=True, hide_index=True)

# =========================================================================
# 📋 VISTA DETALLADA POR FUNCIONARIO
# =========================================================================
st.subheader("👤 Detalles por Funcionario")

# Selector de filtro
col1, col2 = st.columns([2, 1])

with col1:
    filtro_gerencia = st.multiselect(
        "Filtrar por Gerencia:",
        options=sorted(df_resumen['Gerencia'].unique()),
        key="filtro_gerencia"
    )

with col2:
    orden = st.radio(
        "Ordenar por:",
        options=["Nombre", "Diferencia Mes"],
        horizontal=True,
        key="orden_selector"
    )

# Aplicar filtros
if filtro_gerencia:
    df_filtrado = df_resumen[df_resumen['Gerencia'].isin(filtro_gerencia)]
else:
    df_filtrado = df_resumen

# Ordenar
if orden == "Diferencia Mes":
    df_filtrado = df_filtrado.sort_values('Diferencia Mes')
else:
    df_filtrado = df_filtrado.sort_values('Nombre')

funcionarios_filtrados = df_filtrado['Nombre'].unique().tolist()

if funcionarios_filtrados:
    funcionario_seleccionado = st.selectbox(
        "Selecciona un funcionario:",
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
            nombre_norm_func = DataLoader.normalizar_texto(resultado_funcionario['nombre'])
            
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
                
                # ====================================================================================
                # 🔬 DETECTOR DE CRUCES DE PERMISOS CON DIAGNÓSTICO
                # ====================================================================================
                horas_permiso_lista = []
                diagnostico_llaves_intentadas = []
                diagnostico_estado_cruce = []

                # Mapeo de días para obtener la fecha real
                lista_dias_interna = (
                    resultado_funcionario.get('dias_por_semana', {}).get(semana_num, []) or 
                    resultado_funcionario.get('dias_por_semana', {}).get(str(semana_num), [])
                )
                mapa_por_dia_mes = {}
                for dia_datos in lista_dias_interna:
                    if 'Fecha' in dia_datos and pd.notna(dia_datos['Fecha']):
                        dt_obj = pd.to_datetime(dia_datos['Fecha'])
                        mapa_por_dia_mes[dt_obj.day] = dt_obj.strftime('%Y-%m-%d')

                for idx, fila in df_detalle.iterrows():
                    minutos_p = 0
                    texto_dia_columna = str(fila.get('Día', '')).upper()
                    match_numero = re.search(r'\d+', texto_dia_columna)
                    
                    llave_buscada = "N/A"
                    estado_rastreo = "❌ No se pudo determinar fecha"
                    
                    if match_numero:
                        dia_mes = int(match_numero.group())
                        
                        # Intentar obtener la fecha real del mapeo
                        if dia_mes in mapa_por_dia_mes:
                            fecha_real = mapa_por_dia_mes[dia_mes]
                            llave_buscada = f"('{nombre_norm_func}', '{fecha_real}')"
                            
                            # Buscar en diccionario con nombre normalizado (minúsculas)
                            if (nombre_norm_func, fecha_real) in df_permisos_dict:
                                minutos_p = df_permisos_dict[(nombre_norm_func, fecha_real)]
                                horas_p = minutos_p / 60
                                estado_rastreo = f"✅ MATCH ({minutos_p} min / {horas_p:.1f}h)"
                            else:
                                estado_rastreo = "❌ No encontrado"
                        else:
                            estado_rastreo = f"❌ Día {dia_mes} no en datos"

                    if minutos_p > 0:
                        horas_permiso_lista.append(f"{minutos_p // 60:02d}:{minutos_p % 60:02d}")
                    else:
                        horas_permiso_lista.append("00:00")
                        
                    diagnostico_llaves_intentadas.append(llave_buscada)
                    diagnostico_estado_cruce.append(estado_rastreo)

                df_detalle['Permiso Externo (Horas)'] = horas_permiso_lista
                df_detalle['🔬 Llave Buscada'] = diagnostico_llaves_intentadas
                df_detalle['⚙️ Resultado del Cruce'] = diagnostico_estado_cruce

                st.dataframe(df_detalle, use_container_width=True, hide_index=True)
                st.markdown("---")
                # ====================================================================================

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

# Panel de diagnóstico secundario
st.markdown("---")
st.subheader("🛠️ Panel de Diagnóstico Secundario")
with st.expander("🔎 Ver detalles secundarios del funcionario seleccionado"):
    if 'funcionario_seleccionado' in locals() and funcionario_seleccionado:
        nombre_a_diagnosticar = DataLoader.normalizar_texto(funcionario_seleccionado)
        if nombre_a_diagnosticar:
            st.write(f"### Análisis enfocado en: `{nombre_a_diagnosticar}`")
            if not debug_df_permisos.empty:
                df_perm_filtrado = debug_df_permisos[
                    debug_df_permisos['Nombre_Normalizado'] == nombre_a_diagnosticar
                ]
                if not df_perm_filtrado.empty:
                    st.dataframe(df_perm_filtrado[[
                        'Nombres', 'ApellidoPaterno', 'ApellidoMaterno',
                        'Nombre_Normalizado', 'FechaInicio', 'CantidadEnHora'
                    ]], use_container_width=True, hide_index=True)
                else:
                    st.info("No hay registros de permisos para este funcionario")
            else:
                st.info("No hay datos de permisos cargados")
