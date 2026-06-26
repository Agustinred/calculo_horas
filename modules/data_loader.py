"""
data_loader.py - Carga y valida archivos Excel
ACTUALIZADO: Incluye función para construir diccionario de permisos
"""

import pandas as pd
import streamlit as st
from datetime import datetime
import unicodedata
import re


class DataLoader:
    """Carga y valida archivos Excel de horas"""
    
    COLUMNAS_REQUERIDAS = {
        'Nombre', 'Número', 'DiaSemana', 'Semana', 
        'HoraEntrada', 'HoraSalida', 'Observacion'
    }
    
    COLUMNAS_HOJA2 = {'NOMBRE', 'GERENCIA'}
    
    @staticmethod
    def normalizar_texto(texto):
        """Normaliza texto: minúsculas, sin tildes, espacios extras"""
        if not isinstance(texto, str):
            return ""
        # Minúsculas
        texto = texto.lower().strip()
        # Remover tildes
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                       if unicodedata.category(c) != 'Mn')
        # Remover espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)
        return texto
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def cargar_excel(archivo):
        """
        Carga y valida archivo Excel
        Retorna: (df_hoja1, df_hoja2, fecha_mes, errores)
        """
        errores = []
        
        try:
            # Leer ambas hojas
            excel_file = pd.ExcelFile(archivo)
            
            # Validar que existan las hojas
            if 'Hoja1' not in excel_file.sheet_names:
                errores.append("❌ No se encontró 'Hoja1' en el Excel")
                return None, None, None, errores
            
            if 'Hoja2' not in excel_file.sheet_names:
                errores.append("❌ No se encontró 'Hoja2' en el Excel")
                return None, None, None, errores
            
            # Leer Hoja1 y Hoja2
            df_hoja1 = pd.read_excel(excel_file, sheet_name='Hoja1')
            df_hoja2 = pd.read_excel(excel_file, sheet_name='Hoja2')
            
            # Limpiar nombres de columnas (espacios, mayúsculas)
            df_hoja1.columns = df_hoja1.columns.str.strip()
            df_hoja2.columns = df_hoja2.columns.str.strip()
            
            # Validar columnas Hoja1
            columnas_presentes = set(df_hoja1.columns)
            faltantes = DataLoader.COLUMNAS_REQUERIDAS - columnas_presentes
            
            if faltantes:
                errores.append(f"❌ Columnas faltantes en Hoja1: {', '.join(faltantes)}")
                return None, None, None, errores
            
            # Validar columnas Hoja2
            if not DataLoader.COLUMNAS_HOJA2.issubset(set(df_hoja2.columns)):
                errores.append(f"❌ Hoja2 debe tener columnas: NOMBRE, GERENCIA")
                return None, None, None, errores
            
            # Extraer fecha de referencia (Mes y Año base del reporte)
            fecha_mes = DataLoader._extraer_fecha(df_hoja1)
            
            # Limpiar datos básicos
            df_hoja1 = DataLoader._limpiar_hoja1(df_hoja1)
            df_hoja2 = DataLoader._limpiar_hoja2(df_hoja2)
            
            # ✨ NUEVA LÓGICA: Construir dinámicamente la columna 'Fecha' para evitar KeyError en app.py y calculator.py
            if fecha_mes is not None and 'Número' in df_hoja1.columns:
                def construir_fecha(num_dia):
                    try:
                        if pd.isna(num_dia):
                            return None
                        # Convertir a entero limpio por si viene como flotante desde Excel
                        dia = int(float(num_dia))
                        return pd.Timestamp(year=fecha_mes.year, month=fecha_mes.month, day=dia)
                    except:
                        return None
                
                df_hoja1['Fecha'] = df_hoja1['Número'].apply(construir_fecha)
            
            return df_hoja1, df_hoja2, fecha_mes, []
        
        except Exception as e:
            errores.append(f"❌ Error al cargar archivo: {str(e)}")
            return None, None, None, errores
    
    @staticmethod
    def _extraer_fecha(df):
        """Extrae mes/año de la hoja1"""
        try:
            # Buscar en las primeras filas cualquier objeto de fecha
            for col in df.columns:
                for valor in df[col].head(10):
                    if isinstance(valor, (pd.Timestamp, datetime)):
                        return valor
            return None
        except:
            return None
    
    @staticmethod
    def _limpiar_hoja1(df):
        """Limpia y valida datos de Hoja1"""
        df = df.copy()
        
        # Convertir Nombre a minúsculas sin tildes
        df['Nombre_Normalizado'] = df['Nombre'].apply(DataLoader.normalizar_texto)
        
        # Validar que no haya filas vacías en la columna crítica
        df = df.dropna(subset=['Nombre'])
        
        # Convertir tiempos a formato HH:MM
        df['HoraEntrada'] = df['HoraEntrada'].apply(DataLoader._validar_hora)
        df['HoraSalida'] = df['HoraSalida'].apply(DataLoader._validar_hora)
        
        # Llenar observaciones nulas con vacío
        df['Observacion'] = df['Observacion'].fillna('')
        
        return df
    
    @staticmethod
    def _limpiar_hoja2(df):
        """Limpia y valida datos de Hoja2"""
        df = df.copy()
        
        # Normalizar nombres
        df['Nombre_Normalizado'] = df['NOMBRE'].apply(DataLoader.normalizar_texto)
        
        # Limpiar gerencias
        df['GERENCIA'] = df['GERENCIA'].str.strip()
        
        return df
    
    @staticmethod
    def _validar_hora(valor):
        """Valida y convierte hora a formato HH:MM"""
        if pd.isna(valor):
            return None
        
        # Si ya es string
        if isinstance(valor, str):
            if valor.strip() == '':
                return None
            # Intentar parsear
            try:
                # Formato HH:MM
                partes = valor.split(':')
                if len(partes) == 2:
                    h, m = int(partes[0]), int(partes[1])
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        return f"{h:02d}:{m:02d}"
            except:
                pass
        
        # Si es datetime
        if isinstance(valor, pd.Timestamp):
            return valor.strftime('%H:%M')
        
        return None
    
    # ========================================================================
    # 🆕 NUEVA FUNCIÓN: Construir diccionario de permisos desde Excel
    # ========================================================================
    @staticmethod
    def construir_dict_permisos(archivo_permisos):
        """
        Construye diccionario: {(nombre_normalizado, fecha): minutos_totales}
        
        Este diccionario se usa en calculator.py para buscar permisos por:
        - Nombre del funcionario (normalizado)
        - Fecha del permiso (formato YYYY-MM-DD)
        
        Args:
            archivo_permisos: Objeto file de Streamlit o path a archivo Excel
            
        Returns:
            dict: {(nombre_normalizado, YYYY-MM-DD): minutos_totales}
            dict: {nombre_normalizado: lista de (fecha, horas)} para diagnóstico
        """
        dict_permisos = {}
        debug_df_permisos = pd.DataFrame()
        
        if not archivo_permisos:
            return dict_permisos, debug_df_permisos
        
        try:
            # Leer archivo de permisos
            df_p = pd.read_excel(archivo_permisos)
            
            # Validar que existan las columnas críticas
            cols_requeridas = {'ApellidoPaterno', 'ApellidoMaterno', 'Nombres', 'FechaInicio', 'CantidadEnHora'}
            if not cols_requeridas.issubset(set(df_p.columns)):
                return {}, debug_df_permisos
            
            registros_procesados = 0
            
            for idx, row in df_p.iterrows():
                try:
                    # 1️⃣ Construir nombre: Nombres ApellidoPaterno ApellidoMaterno
                    nombres = str(row['Nombres']).strip() if pd.notna(row['Nombres']) else ""
                    ap_paterno = str(row['ApellidoPaterno']).strip() if pd.notna(row['ApellidoPaterno']) else ""
                    ap_materno = str(row['ApellidoMaterno']).strip() if pd.notna(row['ApellidoMaterno']) else ""
                    
                    nombre_completo = f"{nombres} {ap_paterno} {ap_materno}".strip()
                    nombre_normalizado = DataLoader.normalizar_texto(nombre_completo)
                    
                    if not nombre_normalizado:
                        continue
                    
                    # 2️⃣ Extraer fecha (formato ISO: YYYY-MM-DD)
                    fecha_raw = row['FechaInicio']
                    if pd.isna(fecha_raw):
                        continue
                        
                    try:
                        fecha_obj = pd.to_datetime(fecha_raw)
                        fecha_str = fecha_obj.strftime('%Y-%m-%d')
                    except:
                        continue
                    
                    # 3️⃣ Convertir CantidadEnHora a minutos
                    # CantidadEnHora viene en formato "HH:MM" (ej: "08:00", "09:00", "01:00")
                    cantidad_raw = row['CantidadEnHora']
                    
                    if pd.isna(cantidad_raw):
                        minutos = 0
                    else:
                        try:
                            cantidad_str = str(cantidad_raw).strip()
                            
                            # Si es formato HH:MM
                            if ':' in cantidad_str:
                                partes = cantidad_str.split(':')
                                horas = int(partes[0])
                                mins = int(partes[1])
                                minutos = horas * 60 + mins
                            else:
                                # Si es número decimal
                                horas = float(cantidad_str)
                                minutos = int(horas * 60)
                        except (ValueError, TypeError, IndexError):
                            minutos = 0
                    
                    if minutos <= 0:
                        continue
                    
                    # 4️⃣ Crear llave y sumar en diccionario
                    llave = (nombre_normalizado, fecha_str)
                    
                    if llave in dict_permisos:
                        dict_permisos[llave] += minutos  # Acumular si hay múltiples registros
                    else:
                        dict_permisos[llave] = minutos
                    
                    registros_procesados += 1
                        
                except Exception as e:
                    continue
            
            # Guardar copia para diagnóstico
            debug_df_permisos = df_p.copy()
            debug_df_permisos['Nombre_Normalizado'] = debug_df_permisos.apply(
                lambda row: DataLoader.normalizar_texto(
                    f"{row['Nombres']} {row['ApellidoPaterno']} {row['ApellidoMaterno']}"
                ), axis=1
            )
            
            return dict_permisos, debug_df_permisos
            
        except Exception as e:
            return {}, pd.DataFrame()
