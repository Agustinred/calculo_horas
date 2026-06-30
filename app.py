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
# 🎯 PROCESAMIENTO DE LA BASE DE PERMISOS EXTERNA (silencioso, sin UI aquí)
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
df_resumen = Formatter.crear_df_resumen(resultados)

# =========================================================================
# 🔍 FILTROS GLOBALES (aplican a Resumen General y a Detalles por Funcionario)
# =========================================================================
st.subheader("🔍 Filtros")

col_f1, col_f2 = st.columns(2)

with col_f1:
    filtro_gerencia = st.multiselect(
        "Filtrar por Gerencia:",
        options=sorted(df_resumen['Gerencia'].dropna().unique()),
        key="filtro_gerencia"
    )

with col_f2:
    filtro_juridica = st.multiselect(
        "Filtrar por Calidad Jurídica:",
        options=sorted(df_resumen['Calidad Jurídica'].dropna().unique()),
        key="filtro_juridica"
    )

# Aplicar filtros globales (selección vacía = sin filtro, se muestra todo)
df_resumen_filtrado = df_resumen.copy()

if filtro_gerencia:
    df_resumen_filtrado = df_resumen_filtrado[df_resumen_filtrado['Gerencia'].isin(filtro_gerencia)]

if filtro_juridica:
    df_resumen_filtrado = df_resumen_filtrado[df_resumen_filtrado['Calidad Jurídica'].isin(filtro_juridica)]

st.subheader("📊 Resumen General")
st.dataframe(df_resumen_filtrado, use_container_width=True, hide_index=True)

# =========================================================================
# 📋 VISTA DETALLADA POR FUNCIONARIO
# =========================================================================
st.subheader("👤 Detalles por Funcionario")

orden = st.radio(
    "Ordenar por:",
    options=["Nombre", "Diferencia Mes"],
    horizontal=True,
    key="orden_selector"
)

# Ordenar usando el mismo set ya filtrado por los filtros globales
if orden == "Diferencia Mes":
    df_filtrado = df_resumen_filtrado.sort_values('Diferencia Mes')
else:
    df_filtrado = df_resumen_filtrado.sort_values('Nombre')

funcionarios_filtrados = df_filtrado['Nombre'].unique().tolist()

if not funcionarios_filtrados:
    st.warning("⚠️ No hay funcionarios que coincidan con los filtros seleccionados")

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
                # 🔬 CRUCE DE PERMISOS (cálculo interno, sin mostrar columnas de diagnóstico)
                # ====================================================================================
                horas_permiso_lista = []

                # Obtener datos de días desde resultado_funcionario
                lista_dias_interna = (
                    resultado_funcionario.get('dias_por_semana', {}).get(semana_num, []) or
                    resultado_funcionario.get('dias_por_semana', {}).get(str(semana_num), [])
                )

                # Mapeo: número_día → datos_día (para búsqueda rápida)
                mapa_dias = {int(dia['número']): dia for dia in lista_dias_interna}

                for idx, fila in df_detalle.iterrows():
                    minutos_p = 0
                    texto_dia_columna = str(fila.get('Día', '')).upper()

                    # Extraer el número del día del mes (segundo número si hay dos)
                    numeros = re.findall(r'\d+', texto_dia_columna)
                    dia_mes = None

                    if len(numeros) >= 2:
                        dia_mes = int(numeros[1])
                    elif len(numeros) == 1:
                        dia_mes = int(numeros[0])

                    if dia_mes and dia_mes in mapa_dias:
                        dia_datos = mapa_dias[dia_mes]
                        minutos_p = dia_datos.get('minutos_externos', 0)

                    if minutos_p > 0:
                        horas_permiso_lista.append(f"{minutos_p // 60:02d}:{minutos_p % 60:02d}")
                    else:
                        horas_permiso_lista.append("00:00")

                df_detalle['Permiso Externo (Horas)'] = horas_permiso_lista

                st.dataframe(df_detalle, use_container_width=True, hide_index=True)
                st.markdown("---")
                # ====================================================================================

# EXPORTACIÓN
st.subheader("📥 Exportar Resultados")

col1, col2, col3 = st.columns(3)

with col1:
    csv_data = Exporter.exportar_csv(df_resumen_filtrado)
    st.download_button(
        "📄 Descargar CSV",
        csv_data,
        f"horas_{archivo.name.split('.')[0]}.csv",
        "text/csv",
        use_container_width=True
    )

with col2:
    excel_data = Exporter.exportar_excel(df_resumen_filtrado)
    st.download_button(
        "📊 Descargar Excel",
        excel_data,
        f"horas_{archivo.name.split('.')[0]}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col3:
    html_data = Exporter.exportar_html(df_resumen_filtrado)
    st.download_button(
        "🌐 Descargar HTML",
        html_data,
        f"horas_{archivo.name.split('.')[0]}.html",
        "text/html",
        use_container_width=True
    )

# =========================================================================
# 🔍 BÚSQUEDA Y REVISIÓN DE PERMISOS COMPLEMENTARIOS (al final, fase de pruebas)
# =========================================================================
st.markdown("---")
st.subheader("🔍 Búsqueda y revisión de permisos complementarios")
with st.expander("Analizar Diccionario Global de Permisos Externos", expanded=False):
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
                placeholder="EJ: 2026-01-30",
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
