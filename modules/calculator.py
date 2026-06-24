"""
calculator.py - Lógica de cálculo de horas trabajadas
"""

import pandas as pd
from datetime import datetime, timedelta
import re


class HorasCalculator:
    """Calcula horas trabajadas por funcionario"""
    
    # Observaciones que cuentan como día completo
    JUSTIFICACIONES_COMPLETAS = [
        "licencia médica", "lic. médica", "lic med",
        "per. con goce", "permiso con goce", "con goce",
        "per. compl. día", "permiso completo",
        "permiso matrimonio", "matrimonio",
        "vacaciones", "año nuevo", "viernes santo", "sabado santo",
        "feriado", "día feriado"
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
        """Convierte HH:MM a minutos"""
        if not hora_str or pd.isna(hora_str):
            return 0
        try:
            h, m = map(int, str(hora_str).split(':'))
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
        """Retorna horas esperadas según día de la semana"""
        dia_semana = str(dia_semana).strip().lower()
        if "viernes" in dia_semana:
            return 8 * 60  # 8 horas en minutos
        else:
            return 9 * 60  # 9 horas en minutos (Lun-Jue)
    
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
    def calcular_horas_dia(row):
        """
        Calcula horas de un día específico
        Retorna: (horas_minutos, alerta_ausencia)
        """
        alerta = None
        
        hora_entrada = row.get('HoraEntrada')
        hora_salida = row.get('HoraSalida')
        observacion = row.get('Observacion', '')
        dia_semana = row.get('DiaSemana', '')
        numero_dia = row.get('Número')
        nombre = row.get('Nombre', '')
        
        # Caso 1: Justificación completa (vacaciones, licencia, etc)
        if HorasCalculator._es_justificacion_completa(observacion):
            horas_esperadas = HorasCalculator._obtener_horas_esperadas(dia_semana)
            return horas_esperadas, None
        
        # Caso 2: Justificación parcial
        just_parcial = HorasCalculator._obtener_justificacion_parcial(observacion)
        if just_parcial:
            entrada_min = HorasCalculator._hora_a_minutos(hora_entrada)
            salida_min = HorasCalculator._hora_a_minutos(hora_salida)
            
            if just_parcial == "mañana":
                # Permiso mañana: 7:30 a 15:00 = 7.5 horas (450 min)
                # Se cuenta solo la tarde (15:00 - HoraSalida)
                if salida_min > 0:
                    minutos_tarde = salida_min - (15 * 60)  # 15:00 = 900 min
                    return minutos_tarde, None
                else:
                    alerta = f"{nombre} - Día {numero_dia} ({dia_semana}): Permiso mañana pero falta HoraSalida"
                    return 0, alerta
            
            elif just_parcial == "tarde":
                # Permiso tarde: desde 12:30 = 750 min
                # Se cuenta solo la mañana (HoraEntrada - 12:30)
                if entrada_min > 0:
                    minutos_mañana = (12 * 60 + 30) - entrada_min
                    return minutos_mañana, None
                else:
                    alerta = f"{nombre} - Día {numero_dia} ({dia_semana}): Permiso tarde pero falta HoraEntrada"
                    return 0, alerta
        
        # Caso 3: Entrada y salida normal
        if hora_entrada and hora_salida:
            entrada_min = HorasCalculator._hora_a_minutos(hora_entrada)
            salida_min = HorasCalculator._hora_a_minutos(hora_salida)
            minutos_trabajados = salida_min - entrada_min
            return minutos_trabajados, None
        
        # Caso 4: Falta marcación y no hay justificación
        if not hora_entrada or not hora_salida:
            if not hora_entrada:
                alerta = f"{nombre} - Día {numero_dia} ({dia_semana}): Falta HoraEntrada"
            else:
                alerta = f"{nombre} - Día {numero_dia} ({dia_semana}): Falta HoraSalida"
            return 0, alerta
        
        return 0, None
    
    @staticmethod
    def procesar_funcionario(df_empleado):
        """
        Procesa un empleado completo y calcula:
        - Horas por semana
        - Diferencia semanal
        - Total mensual
        - Alertas
        """
        resultados = {
            'nombre': df_empleado['Nombre'].iloc[0] if len(df_empleado) > 0 else 'Desconocido',
            'semanas': {},
            'total_minutos_mes': 0,
            'alertas': []
        }
        
        # Agrupar por semana
        for semana_num in sorted(df_empleado['Semana'].unique()):
            if pd.isna(semana_num):
                continue
            
            df_semana = df_empleado[df_empleado['Semana'] == semana_num]
            
            minutos_semana = 0
            dias_info = []
            
            for _, row in df_semana.iterrows():
                minutos_dia, alerta = HorasCalculator.calcular_horas_dia(row)
                minutos_semana += minutos_dia
                
                if alerta:
                    resultados['alertas'].append(alerta)
                
                dias_info.append({
                    'día': row['DiaSemana'],
                    'número': row['Número'],
                    'minutos': minutos_dia
                })
            
            # Calcular diferencia semanal (44 horas = 2640 minutos)
            diferencia_minutos = minutos_semana - (44 * 60)
            
            resultados['semanas'][int(semana_num)] = {
                'minutos_trabajados': minutos_semana,
                'minutos_esperados': 44 * 60,
                'diferencia_minutos': diferencia_minutos,
                'días': dias_info
            }
            
            resultados['total_minutos_mes'] += diferencia_minutos
        
        return resultados
    
    @staticmethod
    def procesar_todos(df_hoja1, df_hoja2):
        """Procesa todos los empleados del mes"""
        resultados_todos = {}
        alertas_globales = []
        
        # Agrupar por nombre
        for nombre_unico in df_hoja1['Nombre_Normalizado'].unique():
            df_empleado = df_hoja1[df_hoja1['Nombre_Normalizado'] == nombre_unico]
            
            resultado = HorasCalculator.procesar_funcionario(df_empleado)
            
            # Obtener gerencia desde Hoja2
            gerencia_match = df_hoja2[df_hoja2['Nombre_Normalizado'] == nombre_unico]
            if len(gerencia_match) > 0:
                resultado['gerencia'] = gerencia_match['GERENCIA'].iloc[0]
                # Buscar C_Juridica (suponiendo que está en la Hoja1)
                c_juridica = df_empleado['C_Juridica'].iloc[0] if 'C_Juridica' in df_empleado.columns else 'N/A'
                resultado['c_juridica'] = c_juridica
            else:
                resultado['gerencia'] = 'Desconocida'
                resultado['c_juridica'] = 'N/A'
            
            resultados_todos[nombre_unico] = resultado
            alertas_globales.extend(resultado['alertas'])
        
        return resultados_todos, alertas_globales
