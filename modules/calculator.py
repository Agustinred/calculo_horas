"""
modules/calculator.py
Calculador de asistencia optimizado con soporte para cruce de permisos externos por hora.
"""

import pandas as pd
from datetime import datetime
import re


class HorasCalculator:
    """Calcula horas trabajadas por funcionario incorporando cruces externos"""
    
    # Observaciones que aseguran el piso de un día completo
    JUSTIFICACIONES_COMPLETAS = [
        "licencia médica", "lic. médica", "lic med",
        "per. con goce", "permiso con goce", "con goce",
        "per. compl. día", "permiso completo",
        "permiso matrimonio", "matrimonio",
        "vacaciones", "año nuevo", "viernes santo", "sabado santo",
        "feriado", "día feriado", "justificado"
    ]
    
    # Observaciones que cuentan como media jornada
    JUSTIFICACIONES_PARCIALES = {
        "permiso adm. (mañana)": "mañana",
        "permiso adm. (tarde)": "tarde",
        "permiso adm mañana": "mañana",
        "permiso adm tarde": "tarde"
    }
    
    @staticmethod
    def _hora_a_minutos(hora_str):
        """Convierte HH:MM a minutos de forma segura"""
        if not hora_str or pd.isna(hora_str):
            return 0
        hora_str = str(hora_str).strip()
        if not hora_str or hora_str.lower() in ['none', 'nan', 'nat']:
            return 0
        try:
            partes = hora_str.split(':')
            h, m = int(partes[0]), int(partes[1])
            return h * 60 + m
        except:
            return 0
    
    @staticmethod
    def _minutos_a_hora(minutos):
        """Convierte minutos a HH:MM"""
        horas = abs(minutos) // 60
        mins = abs(minutos) % 60
        signo = '-' if minutos < 0 else ''
        return f"{signo}{horas:02d}:{mins:02d}"
    
    @staticmethod
    def _obtener_horas_esperadas(dia_semana):
        """Retorna horas esperadas según día de la semana, excluyendo fines de semana"""
        dia_semana = str(dia_semana).strip().lower()
        if "sábado" in dia_semana or "sabado" in dia_semana or "domingo" in dia_semana:
            return 0  
        elif "viernes" in dia_semana:
            return 8 * 60  
        else:
            return 9 * 60  
    
    @staticmethod
    def _es_justificacion_completa(observacion):
        """Verifica si la observación justifica un día completo"""
        if not observacion or pd.isna(observacion):
            return False
        
        obs_lower = str(observacion).strip().lower()
        for justificacion in HorasCalculator.JUSTIFICACIONES_COMPLETAS:
            if justificacion in obs_lower:
                return True
        return False
    
    @staticmethod
    def _obtener_justificacion_parcial(observacion):
        """Retorna tipo de justificación parcial (mañana/tarde) si aplica"""
        if not observacion or pd.isna(observacion):
            return None
        
        obs_lower = str(observacion).strip().lower()
        for just_key, just_value in HorasCalculator.JUSTIFICACIONES_PARCIALES.items():
            if just_key in obs_lower:
                return just_value
        return None
    
    @staticmethod
    def calcular_horas_dia(row, fecha_completa_str=None, dict_permisos=None):
        """
        Calcula horas de un día específico priorizando marcas reales y aplicando pisos/cruces por justificación
        """
        alerta = None
        dict_permisos = dict_permisos or {}
        
        hora_entrada_raw = row.get('HoraEntrada')
        hora_salida_raw = row.get('HoraSalida')
        
        hora_entrada = str(hora_entrada_raw).strip() if pd.notna(hora_entrada_raw) else ""
        hora_salida = str(hora_salida_raw).strip() if pd.notna(hora_salida_raw) else ""
        
        if hora_entrada.lower() in ['none', 'nan', 'nat', '']: hora_entrada = ""
        if hora_salida.lower() in ['none', 'nan', 'nat', '']: hora_salida = ""
        
        observacion = row.get('Observacion', '')
        obs_lower = str(observacion).strip().lower() if pd.notna(observacion) else ""
        
        dia_semana = row.get('DiaSemana', '')
        dia_lower = str(dia_semana).strip().lower()
        
        numero_dia = row.get('Número')
        nombre_normalizado = row.get('Nombre_Normalizado', row.get('Nombre', ''))
        nombre_display = row.get('Nombre', '')
        
        horas_esperadas = HorasCalculator._obtener_horas_esperadas(dia_semana)
        
        # 1. EVALUAR SI HAY UNA COMBINACIÓN COMPLETA PRIMERO
        if ("permiso adm" in obs_lower or "per. adm" in obs_lower) and ("mañana" in obs_lower) and ("lic" in obs_lower) and ("tarde" in obs_lower):
            return horas_esperadas, 0, None

        # 2. CALCULAR MARCAS REALES TRABAJADAS
        minutos_reales = 0
        tiene_marcas = (hora_entrada != "" and hora_salida != "")
        
        if tiene_marcas:
            entrada_min = HorasCalculator._hora_a_minutos(hora_entrada)
            salida_min = HorasCalculator._hora_a_minutos(hora_salida)
            minutos_reales = max(0, salida_min - entrada_min)
            
        # 3. CRUCE ESTRICTO: PERMISO COMPLEMENTARIO POR HORAS (Búsqueda flexible para evitar fallos por puntos o espacios)
        es_permiso_horas = False
        if "per" in obs_lower and "compl" in obs_lower and "horas" in obs_lower:
            es_permiso_horas = True
        elif "permiso" in obs_lower and "horas" in obs_lower:
            es_permiso_horas = True

        if es_permiso_horas:
            minutos_permiso_externo = 0
            if fecha_completa_str:
                try:
                    ts = pd.to_datetime(fecha_completa_str)
                    fmt_ymd = ts.strftime('%Y-%m-%d')
                    fmt_dmy = ts.strftime('%d-%m-%Y')
                    
                    llave_ymd = (nombre_normalizado, fmt_ymd)
                    llave_dmy = (nombre_normalizado, fmt_dmy)
                    
                    minutos_permiso_externo = dict_permisos.get(llave_ymd, dict_permisos.get(llave_dmy, 0))
                except:
                    llave_cruce = (nombre_normalizado, fecha_completa_str)
                    minutos_permiso_externo = dict_permisos.get(llave_cruce, 0)
            
            total_dia = minutos_reales + minutos_permiso_externo
            return total_dia, minutos_permiso_externo, None

        # 4. EVALUAR JUSTIFICACIÓN PARCIAL (MEDIA JORNADA)
        just_parcial = HorasCalculator._obtener_justificacion_parcial(observacion)
        if just_parcial in ["mañana", "tarde"]:
            if "viernes" in dia_lower:
                minutos_bonificados = 4 * 60       
            else:
                minutos_bonificados = (4 * 60) + 30  
            
            return (minutos_bonificados + minutos_reales), 0, None

        # 5. EVALUAR JUSTIFICACIÓN COMPLETA
        if HorasCalculator._es_justificacion_completa(observacion):
            if tiene_marcas and minutos_reales > horas_esperadas:
                return minutos_reales, 0, None
            return horas_esperadas, 0, None

        # 6. CASO NORMAL
        if tiene_marcas:
            return minutos_reales, 0, None
        
        # 7. MANEJO DE FALTAS DE MARCACIÓN
        if hora_entrada == "" or hora_salida == "":
            if "no hábil" in obs_lower or "no habil" in obs_lower or "sabado" in dia_lower or "sábado" in dia_lower or "domingo" in dia_lower:
                return 0, 0, None
            
            if hora_entrada == "" and hora_salida != "":
                alerta = f"{nombre_display} - Día {numero_dia} ({dia_semana}): Falta HoraEntrada"
            elif hora_entrada != "" and hora_salida == "":
                alerta = f"{nombre_display} - Día {numero_dia} ({dia_semana}): Falta HoraSalida"
            elif hora_entrada == "" and hora_salida == "":
                alerta = f"{nombre_display} - Día {numero_dia} ({dia_semana}): Falta Marcación Completa (Entrada y Salida)"
                
            return 0, 0, alerta
        
        return 0, 0, None
    
    @staticmethod
    def _es_semana_parcial(df_semana, numero_semana, df_empleado_completo):
        """Detecta si una semana es parcial (inicio o fin de mes)"""
        dias_en_semana = df_semana['DiaPalabra'].astype(str).str.lower().tolist()
        numeros_dias = sorted(df_semana['Número'].tolist())
        
        if not numeros_dias:
            return False, 5, 44 * 60
        
        es_primera_semana = 'lunes' not in dias_en_semana[0].lower() if dias_en_semana else False
        es_ultima_semana = len(df_semana[~df_semana['DiaPalabra'].astype(str).str.lower().str.contains('sabado|sábado|domingo')]) < 5
        
        if es_primera_semana or es_ultima_semana:
            meta_minutos = 0
            for _, row in df_semana.iterrows():
                meta_minutos += HorasCalculator._obtener_horas_esperadas(row['DiaSemana'])
            return True, len(df_semana), meta_minutos
        
        return False, 5, 44 * 60
    
    @staticmethod
    def procesar_funcionario(df_empleado, dict_permisos=None):
        """Procesa un empleado completo mapeando fechas exactas para los cruces"""
        resultados = {
            'nombre': df_empleado['Nombre'].iloc[0] if len(df_empleado) > 0 else 'Desconocido',
            'semanas': {},
            'total_minutos_mes': 0,
            'alertas': [],
            'dias_por_semana': {}
        }
        
        for semana_num in sorted(df_empleado['Semana'].unique()):
            if pd.isna(semana_num):
                continue
            
            df_semana = df_empleado[df_empleado['Semana'] == semana_num].sort_values('Número')
            es_parcial, dias_esperados, meta_calculada = HorasCalculator._es_semana_parcial(
                df_semana, semana_num, df_empleado
            )
            
            meta_semanal_final = meta_calculada if es_parcial else (44 * 60)
            minutos_semana = 0
            dias_info = []
            acumulado = 0
            
            for _, row in df_semana.iterrows():
                fecha_str = None
                if 'Fecha' in row and pd.notna(row['Fecha']):
                    try:
                        fecha_str = pd.to_datetime(row['Fecha']).strftime('%Y-%m-%d')
                    except:
                        fecha_str = str(row['Fecha']).split()[0]
                
                # Modificado para recibir minutos_externos retornados explícitamente
                minutos_dia, minutos_externos, alerta = HorasCalculator.calcular_horas_dia(
                    row, fecha_completa_str=fecha_str, dict_permisos=dict_permisos
                )
                
                minutos_semana += minutos_dia
                acumulado += minutos_dia
                
                if alerta:
                    resultados['alertas'].append(alerta)
                
                dias_info.append({
                    'día': row['DiaSemana'],
                    'número': row['Número'],
                    'hora_entrada': row.get('HoraEntrada', ''),
                    'hora_salida': row.get('HoraSalida', ''),
                    'minutos': minutos_dia,
                    'acumulado': acumulado,
                    'minutos_externos': minutos_externos,  # Guardamos el valor exacto para la UI
                    'observacion': row.get('Observacion', '')
                })
            
            diferencia_minutos = minutos_semana - meta_semanal_final
            resultados['semanas'][int(semana_num)] = {
                'minutos_trabajados': minutos_semana,
                'minutos_esperados': meta_semanal_final,
                'diferencia_minutos': diferencia_minutos,
                'días': dias_info,
                'es_parcial': es_parcial
            }
            resultados['dias_por_semana'][int(semana_num)] = dias_info
            
            if diferencia_minutos < 0:
                resultados['total_minutos_mes'] += diferencia_minutos
        
        return resultados

    @staticmethod
    def procesar_todos(df_hoja1, df_hoja2, dict_permisos=None):
        """Procesa todos los empleados del mes aplicando el diccionario de permisos corregido"""
        resultados_todos = {}
        alertas_globales = []
        
        for nombre_unico in df_hoja1['Nombre_Normalizado'].unique():
            df_empleado = df_hoja1[df_hoja1['Nombre_Normalizado'] == nombre_unico]
            
            resultado = HorasCalculator.procesar_funcionario(df_empleado, dict_permisos=dict_permisos)
            
            gerencia_match = df_hoja2[df_hoja2['Nombre_Normalizado'] == nombre_unico]
            if len(gerencia_match) > 0:
                resultado['gerencia'] = gerencia_match['GERENCIA'].iloc[0]
                c_juridica = df_empleado['C_Juridica'].iloc[0] if 'C_Juridica' in df_empleado.columns else 'N/A'
                resultado['c_juridica'] = c_juridica
            else:
                resultado['gerencia'] = 'Desconocida'
                resultado['c_juridica'] = 'N/A'
            
            resultados_todos[nombre_unico] = resultado
            alertas_globales.extend(resultado['alertas'])
        
        return resultados_todos, alertas_globales
