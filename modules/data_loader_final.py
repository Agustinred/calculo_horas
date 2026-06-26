"""
modules/data_loader.py
Cargador de datos Excel y constructor de diccionario de permisos externos
"""

import pandas as pd
import unicodedata
import re


class DataLoader:
    """Carga y procesa datos de Excel"""
    
    @staticmethod
    def normalizar_texto(texto):
        """Normaliza un texto a minúsculas sin tildes para matching"""
        if not texto or pd.isna(texto):
            return ""
        
        texto = str(texto).lower().strip()
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        texto = re.sub(r'\s+', ' ', texto)
        
        return texto
    
    @staticmethod
    def cargar_excel(archivo):
        """
        Carga Hoja1 (marcación) y Hoja2 (catálogo) de un Excel
        Retorna: (df_hoja1, df_hoja2, fecha_mes, errores)
        """
        errores = []
        df_hoja1 = pd.DataFrame()
        df_hoja2 = pd.DataFrame()
        fecha_mes = None
        
        try:
            xl_file = pd.ExcelFile(archivo)
            hojas_disponibles = xl_file.sheet_names
            
            # Validar Hoja1
            if 'Hoja1' not in hojas_disponibles:
                errores.append("⚠️ No se encontró 'Hoja1' en el archivo")
                return df_hoja1, df_hoja2, fecha_mes, errores
            
            df_hoja1 = pd.read_excel(archivo, sheet_name='Hoja1')
            
            # Validar Hoja2
            if 'Hoja2' not in hojas_disponibles:
                errores.append("⚠️ No se encontró 'Hoja2' en el archivo")
            else:
                df_hoja2 = pd.read_excel(archivo, sheet_name='Hoja2')
            
            # Normalizar nombres en Hoja1
            if 'Nombre' in df_hoja1.columns:
                df_hoja1['Nombre_Normalizado'] = df_hoja1['Nombre'].apply(DataLoader.normalizar_texto)
            
            # Normalizar nombres en Hoja2
            if 'NOMBRE' in df_hoja2.columns:
                df_hoja2['Nombre_Normalizado'] = df_hoja2['NOMBRE'].apply(DataLoader.normalizar_texto)
            
            # Extraer mes de la primera fecha si existe
            if 'fecha' in df_hoja1.columns:
                try:
                    primera_fecha = pd.to_datetime(df_hoja1['fecha'].iloc[0])
                    fecha_mes = primera_fecha.strftime('%B %Y')
                except:
                    fecha_mes = "Desconocido"
            
            return df_hoja1, df_hoja2, fecha_mes, errores
        
        except Exception as e:
            errores.append(f"❌ Error al cargar Excel: {str(e)}")
            return df_hoja1, df_hoja2, fecha_mes, errores
    
    @staticmethod
    def construir_dict_permisos(archivo_permisos):
        """
        Construye un diccionario de permisos externos por hora
        Estructura: {(nombre_normalizado, 'YYYY-MM-DD'): minutos}
        
        Retorna: (dict_permisos, debug_df_permisos)
        """
        dict_permisos = {}
        debug_df_permisos = pd.DataFrame()
        
        try:
            df_permisos = pd.read_excel(archivo_permisos, sheet_name=0)
            
            # Validar columnas requeridas
            columnas_requeridas = ['ApellidoPaterno', 'ApellidoMaterno', 'Nombres', 'FechaInicio', 'CantidadEnHora']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df_permisos.columns]
            
            if columnas_faltantes:
                print(f"⚠️ Columnas faltantes: {columnas_faltantes}")
                return dict_permisos, debug_df_permisos
            
            # Procesar cada registro
            registros_procesados = []
            
            for idx, row in df_permisos.iterrows():
                try:
                    # Construir nombre completo normalizado
                    apellido_p = str(row['ApellidoPaterno']).strip() if pd.notna(row['ApellidoPaterno']) else ''
                    apellido_m = str(row['ApellidoMaterno']).strip() if pd.notna(row['ApellidoMaterno']) else ''
                    nombres = str(row['Nombres']).strip() if pd.notna(row['Nombres']) else ''
                    
                    nombre_completo = f"{nombres} {apellido_p} {apellido_m}".strip()
                    nombre_normalizado = DataLoader.normalizar_texto(nombre_completo)
                    
                    # Procesar fecha
                    fecha_inicio = row['FechaInicio']
                    if pd.isna(fecha_inicio):
                        continue
                    
                    try:
                        fecha_ts = pd.to_datetime(fecha_inicio)
                        fecha_str = fecha_ts.strftime('%Y-%m-%d')
                    except:
                        fecha_str = str(fecha_inicio).split()[0]
                    
                    # Procesar cantidad en horas (puede venir como "HH:MM" o decimal)
                    cantidad_str = str(row['CantidadEnHora']).strip()
                    minutos = 0
                    
                    if ':' in cantidad_str:
                        # Formato HH:MM
                        try:
                            partes = cantidad_str.split(':')
                            horas = int(partes[0])
                            mins = int(partes[1])
                            minutos = (horas * 60) + mins
                        except:
                            continue
                    else:
                        # Formato decimal
                        try:
                            horas_decimal = float(cantidad_str)
                            minutos = int(horas_decimal * 60)
                        except:
                            continue
                    
                    # Crear llave y agregar al diccionario
                    llave = (nombre_normalizado, fecha_str)
                    
                    if llave in dict_permisos:
                        dict_permisos[llave] += minutos
                    else:
                        dict_permisos[llave] = minutos
                    
                    # Guardar para debug
                    registros_procesados.append({
                        'Nombres': nombres,
                        'ApellidoPaterno': apellido_p,
                        'ApellidoMaterno': apellido_m,
                        'Nombre_Normalizado': nombre_normalizado,
                        'FechaInicio': fecha_str,
                        'CantidadEnHora': cantidad_str,
                        'Minutos': minutos
                    })
                
                except Exception as e:
                    print(f"⚠️ Error procesando fila {idx}: {str(e)}")
                    continue
            
            debug_df_permisos = pd.DataFrame(registros_procesados)
            
            return dict_permisos, debug_df_permisos
        
        except Exception as e:
            print(f"❌ Error al cargar permisos: {str(e)}")
            return dict_permisos, debug_df_permisos
