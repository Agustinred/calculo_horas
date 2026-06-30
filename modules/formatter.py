"""
modules/formatter.py
Formateador de datos para presentación en Streamlit
"""

import pandas as pd


class Formatter:
    """Formatea resultados de cálculo de horas para presentación"""
    
    @staticmethod
    def _minutos_a_hora_texto(minutos):
        """Convierte minutos a formato HH:MM con signo si es negativo"""
        horas = abs(minutos) // 60
        mins = abs(minutos) % 60
        signo = '-' if minutos < 0 else ''
        return f"{signo}{horas:02d}:{mins:02d}"
    
    @staticmethod
    def determinar_color_semana(diferencia_minutos):
        """
        Determina color de fondo, texto de estado y color de acento
        según la diferencia de horas. Paleta institucional (tonos suaves,
        sin colores saturados), adecuada para reportes formales.
        """
        if diferencia_minutos <= -60:
            return "#FBEAEA", "No cumple", "#B3261E"
        elif diferencia_minutos < 0:
            return "#FDF3E2", "Atención", "#B26A00"
        else:
            return "#E9F3EC", "Cumple", "#2E7D46"
    
    @staticmethod
    def crear_df_resumen(resultados):
        """Crea un DataFrame de resumen general de todos los funcionarios"""
        datos_resumen = []
        
        for nombre_norm, resultado in resultados.items():
            nombre = resultado.get('nombre', 'Desconocido')
            gerencia = resultado.get('gerencia', 'N/A')
            c_juridica = resultado.get('c_juridica', 'N/A')
            total_minutos = resultado.get('total_minutos_mes', 0)
            
            # Contar semanas completas y parciales
            semanas = resultado.get('semanas', {})
            semanas_completas = sum(1 for s in semanas.values() if not s.get('es_parcial', False))
            semanas_parciales = sum(1 for s in semanas.values() if s.get('es_parcial', False))
            
            # Calcular totales
            total_trabajado = sum(s['minutos_trabajados'] for s in semanas.values())
            total_meta = sum(s['minutos_esperados'] for s in semanas.values())
            
            texto_diferencia = Formatter._minutos_a_hora_texto(total_minutos)
            
            _, estado, _ = Formatter.determinar_color_semana(total_minutos)
            
            datos_resumen.append({
                'Nombre': nombre,
                'Gerencia': gerencia,
                'Calidad Jurídica': c_juridica,
                'Semanas Completas': semanas_completas,
                'Semanas Parciales': semanas_parciales,
                'Total Trabajado': Formatter._minutos_a_hora_texto(total_trabajado),
                'Meta Total': Formatter._minutos_a_hora_texto(total_meta),
                'Diferencia Mes': texto_diferencia,
                'Estado': estado
            })
        
        df_resumen = pd.DataFrame(datos_resumen)
        return df_resumen
    
    @staticmethod
    def crear_df_detalle_semana(dias_info):
        """Crea un DataFrame de detalle de días de una semana"""
        datos_dias = []
        
        for dia in dias_info:
            minutos = dia.get('minutos', 0)
            horas = minutos // 60
            mins = minutos % 60
            
            acumulado = dia.get('acumulado', 0)
            acum_horas = acumulado // 60
            acum_mins = acumulado % 60
            
            datos_dias.append({
                'Día': f"{dia.get('día', '')} {dia.get('número', '')}",
                'Hora Entrada': dia.get('hora_entrada', ''),
                'Hora Salida': dia.get('hora_salida', ''),
                'Horas Trabajadas': f"{horas:02d}:{mins:02d}",
                'Acumulado Semana': f"{acum_horas:02d}:{acum_mins:02d}",
                'Observación': dia.get('observacion', ''),
                'Permiso Externo (Horas)': '00:00'  # Se actualizará dinámicamente en app.py
            })
        
        df_detalle = pd.DataFrame(datos_dias)
        return df_detalle
