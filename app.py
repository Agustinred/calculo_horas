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

# 🔄 FUNCIÓN DE NORMALIZACIÓN ULTRA ESTRICTA (Nombres, Mayúsculas, Tildes, Espacios, Puntos)
def normalizar_texto_local(texto):
    if not texto or pd.isna(texto):
        return ""
    
    # 1. Convertir a string y pasar a mayúsculas
    texto = str(texto).upper()
    
    # 2. Remover tildes, diéresis y acentos complejos
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    
    # 3. Remover puntos, comas, guiones y cualquier carácter que no sea letra o espacio
    texto = re.sub(r'[^A-Z\s]', ' ', texto)
    
    # 4. Colapsar múltiples espacios o espacios dobles en uno solo y limpiar extremos
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

# Nuevo Cargador Opcional para la Base de Permisos
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

# Procesamiento de la Base de Permisos Externa con Orden Solicitado
df_permisos_dict = {}
debug_df_permisos = pd.DataFrame()

if uploaded_file_permisos:
    try:
        df_p = pd.read_excel(uploaded_file_permisos)
        
        # Sanitizar columnas de nombres separados eliminando espacios extras
        df_p['Nombres'] = df_p['Nombres'].fillna('').astype(str).str.strip()
        df_p['ApellidoPaterno'] = df_p['ApellidoPaterno'].fillna('').astype(str).str.strip()
        df_p['ApellidoMaterno'] = df_p['ApellidoMaterno'].fillna('').astype(str).str.strip()
        
        # 🧩 CONCATENACIÓN: Nombres + ApellidoPaterno + ApellidoMaterno
        df_p['Nombre_Completo_Raw'] = (
            df_p['Nombres'] + " " + 
            df_p['ApellidoPaterno'] + " " + 
            df_p['ApellidoMaterno']
        )
        
        # Aplicar la nueva normalización estricta sobre el nombre armado
        df_p['Nombre_Normalizado'] = df_p['Nombre_Completo_Raw'].apply(normalizar_texto_local)
        
        # Forzar la lectura estricta y remover zonas horarias para evitar desfases de días
        if 'FechaInicio' in df_p.columns:
            fechas_transformadas = pd.to_datetime(df_p['FechaInicio'], errors='coerce')
            if fechas_transformadas.dt.tz is not None:
                fechas_transformadas = fechas_transformadas.dt.tz_convert(None)
            df_p['Fecha_Str'] = fechas_transformadas.dt.strftime('%Y-%m-%d')
        else:
            st.sidebar.error("⚠️ No se encontró la columna 'FechaInicio' en el archivo de permisos.")
            df_p['Fecha_Str'] = None
        
        # Guardar copia para la tabla de diagnóstico inferior
        debug_df_permisos = df_p.copy()
        
        # Poblar diccionario optimizado de mapeo guardando fechas exactas reales
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
                
        st.sidebar.success(f"✅ Se cargaron {len(df_permisos_dict)} registros de permisos basados en 'FechaInicio'.")
    except Exception as e:
        st.sidebar.error(f"⚠️ Nota sobre permisos: No se pudo procesar el archivo opcional ({e})")

# =========================================================================
# 🔍 PANEL DE DIAGNÓSTICO EN TIEMPO REAL (INTEGRADO EN INTERFAZ WEB)
# =========================================================================
st.subheader("⚙️ Herramienta de Inspección de Cruces en Memoria")
with st.expander("🔍 Analizar Diccionario Global de Permisos Externos", expanded=False):
    if df_permisos_dict:
        st.write(f"📊 **Total de registros llave construidos en memoria:** {len(df_permisos_dict)}")
        
        # Formulario interactivo rápido para auditar si una tupla matemática exacta existe
        st.write("🧪 **Simulador de Búsqueda Manual de Coincidencias:**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            nombre_prueba = st.text_input("Nombre a evaluar (Normalizado):", placeholder="EJ: CLAUDIA ALEJANDRA ABARCA MANRIQUEZ", key="diag_nom_input")
        with col_d2:
            fecha_prueba = st.text_input("Fecha a evaluar (AAAA-MM-DD):", placeholder="EJ: 2026-01-09", key="diag_fec_input")
            
        if nombre_prueba and fecha_prueba:
            llave_prueba = (nombre_prueba.strip().upper(), fecha_prueba.strip())
            st.markdown("---")
            st.write(f"🔎 *Buscando tupla matemática:* `{llave_prueba}`")
            if llave_prueba in df_permisos_dict:
                st.success(f"✅ ¡COINCIDENCIA ENCONTRADA EN DICCIONARIO! Valor: {df_permisos_dict[llave_prueba]} minutos.")
            else:
                st.error("❌ La llave no existe tal cual en el diccionario. Revisa espacios o formatos de fecha.")
        
        st.write("📋 **Vista previa en formato JSON de las primeras 20 llaves en memoria:**")
        muestra_dict = {str(k): f"{v} mins" for k, v in list(df_permisos_dict.items())[:20]}
        st.json(muestra_dict)
    else:
        st.info("💡 No hay datos en el diccionario de permisos. Carga un archivo de permisos en la barra lateral para poblar el inspector.")
st.markdown("---")
# =========================================================================

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
        
    # Buscar dinámicamente la columna Nombre en la asistencia
    col_nombre_asist = [c for c in df_h1.columns if 'nombre' in str(c).lower()]
    if col_nombre_asist:
        df_h1['Nombre_Normalizado'] = df_h1[col_nombre_asist[0]].apply(normalizar_texto_local)
    else:
        df_h1['Nombre_Normalizado'] = df_h1['Nombre'].apply(normalizar_texto_local)
        
    col_cat_nombre = 'NOMBRE' if 'NOMBRE' in df_h2.columns else 'Nombre'
    if col_cat_nombre in df_h2.columns:
        df_h2['Nombre_Normalizado'] = df_h2[col_cat_nombre].apply(normalizar_texto_local)

    # 🔄 CONTROL DE EXCEPCIONES Y LLAMADA COMPATIBLE CON LA CALCULADORA 🔄
    try:
        resultados, alertas = HorasCalculator.procesar_todos(df_h1, df_h2, dict_permisos=df_permisos_dict)
    except TypeError:
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
            nombre_norm_func = normalizar_texto_local(resultado_funcionario['nombre'])
            
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
                semanas_a_mostrar = weeks = semanas_disponibles
            
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
                
# =====================================================================
                # 🔄 CRUCE EXACTO E INYECCIÓN DE PERMISOS (CORREGIDO SIN DESFASES)
                # =====================================================================
                horas_permiso_lista = []
                
                # Crear un mapa rápido de Fecha -> Observación/Datos desde el motor de cálculo
                mapa_fechas_calculadas = {}
                lista_dias_interna = resultado_funcionario.get('dias_por_semana', {}).get(semana_num, [])
                
                for dia_datos in lista_dias_interna:
                    if 'Fecha' in dia_datos and pd.notna(dia_datos['Fecha']):
                        f_str = pd.to_datetime(dia_datos['Fecha']).strftime('%Y-%m-%d')
                        mapa_fechas_calculadas[f_str] = dia_datos

                # Construimos la lista de permisos alineada PERFECTAMENTE con las filas de df_detalle
                for idx, fila in df_detalle.iterrows():
                    minutos_p = 0
                    
                    if idx < len(lista_dias_interna):
                        dia_datos = lista_dias_interna[idx]
                        obs_dia = str(dia_datos.get('observacion', '')).strip().lower()
                        
                        if 'Fecha' in dia_datos and pd.notna(dia_datos['Fecha']):
                            fecha_exacta_str = pd.to_datetime(dia_datos['Fecha']).strftime('%Y-%m-%d')
                            llave_exacta = (nombre_norm_func, fecha_exacta_str)
                            
                            minutos_p = df_permisos_dict.get(llave_exacta, 0)
                    
                    if minutos_p > 0:
                        horas_permiso_lista.append(f"{minutos_p // 60:02d}:{minutos_p % 60:02d}")
                    else:
                        horas_permiso_lista.append("00:00")
                
                # Inyección limpia en el DataFrame visual
                columnas = list(df_detalle.columns)
                if 'Permiso Externo (Horas)' in columnas:
                    df_detalle['Permiso Externo (Horas)'] = horas_permiso_lista
                elif 'Observación' in columnas:
                    idx_obs = columnas.index('Observación')
                    df_detalle.insert(idx_obs, 'Permiso Externo (Horas)', horas_permiso_lista)
                else:
                    df_detalle['Permiso Externo (Horas)'] = horas_permiso_lista
                
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

# =====================================================================
# 🛠️ PANEL DE DIAGNÓSTICO FILTRADO EXACTO (SIN MEZCLAR OTRAS PERSONAS) 🛠️
# =====================================================================
st.markdown("---")
st.subheader("🛠️ Panel de Diagnóstico e Inspección de Datos")
with st.expander("🔎 Haz clic aquí para inspeccionar las llaves de cruce exactas"):
    
    nombre_a_diagnosticar = normalizar_texto_local(funcionario_seleccionado) if funcionarios_filtrados else ""
    
    if nombre_a_diagnosticar:
        st.write(f"### Análisis enfocado en: `{nombre_a_diagnosticar}`")
        
        st.write("### 1. Inspección de Datos en Asistencia (Hoja 1):")
        if 'df_h1' in locals():
            col_nombre_real = [c for c in df_h1.columns if 'nombre' in str(c).lower()]
            if col_nombre_real:
                col_a_usar = col_nombre_real[0]
                df_asist_filtrado = df_h1[df_h1['Nombre_Normalizado'] == nombre_a_diagnosticar]
                
                if not df_asist_filtrado.empty:
                    st.success(f"🔍 ¡Funcionario encontrado de forma exacta en Asistencia!")
                    st.write(f"**Nombre Crudo original:** `{df_asist_filtrado[col_a_usar].iloc[0]}`")
                    st.write(f"**Nombre Normalizado:** `{df_asist_filtrado['Nombre_Normalizado'].iloc[0]}`")
                    columnas_existentes = [col_a_usar, 'Nombre_Normalizado'] + [c for c in ['Fecha', 'DiaSemana', 'DiaPalabra'] if c in df_h1.columns]
                    st.dataframe(df_asist_filtrado[columnas_existentes].head(5))
                else:
                    st.error(f"❌ El nombre exacto `{nombre_a_diagnosticar}` no está en la base de asistencia.")
                    
        st.write("### 2. Inspección en Archivo de Permisos:")
        if not debug_df_permisos.empty:
            df_perm_filtrado = debug_df_permisos[debug_df_permisos['Nombre_Normalizado'] == nombre_a_diagnosticar]
            if not df_perm_filtrado.empty:
                st.success(f"🔍 ¡Registros encontrados en Permisos!")
                st.dataframe(df_perm_filtrado[['Nombre_Completo_Raw', 'Nombre_Normalizado', 'Fecha_Str', 'CantidadEnHora']])
            else:
                st.error(f"❌ No hay registros que coincidan exactamente con `{nombre_a_diagnosticar}` en los permisos.")

        st.write("### 3. Claves activas en el diccionario de cruce:")
        if df_permisos_dict:
            claves_funcionario = {k: v for k, v in df_permisos_dict.items() if k[0] == nombre_a_diagnosticar}
            if claves_funcionario:
                st.write("Claves generadas para este funcionario (Estructura: `(Nombre, Fecha)` -> Minutos):")
                st.json({str(k): f"{v} minutos" for k, v in claves_funcionario.items()})
            else:
                st.warning("No se generaron llaves válidas en el diccionario para este nombre.")
    else:
        st.info("Carga los archivos para ver el diagnóstico detallado de un funcionario.")
