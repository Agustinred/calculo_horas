"""
data_loader.py - Carga y valida archivos Excel
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
