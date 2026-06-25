"""
formatter.py - Formatos, colores y presentación de datos (ACTUALIZADO)
"""

import pandas as pd


class Formatter:
    """Formatea y aplica colores a los resultados"""
    
    COLOR_VERDE = "#90EE90"      # Verde claro
    COLOR_AMARILLO = "#FFD700"   # Amarillo
    COLOR_ROJO = "#FF6B6B"       # Rojo claro
    COLOR_BLANCO = "#FFFFFF"
    
    ESTADO_VERDE = "✅ CUMPLE"
    ESTADO_AMARILLO = "⚠️ FALTA <1H"
    ESTADO_ROJO = "❌ FALTA ≥1H"
    
    @staticmethod
    def _minutos_a_hora_texto(minutos):
        """Convierte minutos a texto HH:MM"""
        horas = abs(minutos) // 60
        mins = abs(minutos) % 60
        signo = '-' if minutos < 0 else ''
        return f"{signo}{horas:02d}:{mins:02d}"
    
    @staticmethod
    def determinar_color_semana(diferencia_minutos):
        """
        Determina color según diferencia semanal
        - Verde: 0 minutos faltantes
        - Amarillo: 1-59 minutos faltantes
        - Rojo: >= 60 minutos faltantes
        """
        if diferencia_minutos >= 0:
            return Formatter.COLOR_VERDE, Formatter.ESTADO_VERDE
        elif -59 <= diferencia_minutos < 0:
            return Formatter.COLOR_AMARILLO, Formatter.ESTADO_AMARILLO
        else:  # <= -60
            return Formatter.COLOR_ROJO, Formatter.ESTADO_ROJO
    
    @staticmethod
    def determinar_color_total(total_minutos_mes):
        """
        Determina color según total mensual
        - Rojo si falta más de 59 minutos en el mes
        - Sino, tomar el color que corresponda por semanas
        """
        if total_minutos_mes <= -60:
            return Formatter.COLOR_ROJO, "❌ FALTA >59 MIN MES"
        elif total_minutos_mes < 0:
            return Formatter.COLOR_AMARILLO, "⚠️ FALTA <1H MES"
        else:
            return Formatter.COLOR_VERDE, "✅ CUMPLE MES"
    
    @staticmethod
    def crear_df_resumen(resultados_todos, filtro_gerencia=None, filtro_juridica=None):
        """
        Crea DataFrame de resumen con colores
        """
        datos = []
        
        for nombre_norm, resultado in resultados_todos.items():
            # Aplicar filtros
            if filtro_gerencia and resultado.get('gerencia') not in filtro_gerencia:
                continue
            if filtro_juridica and resultado.get('c_juridica') not in filtro_juridica:
                continue
            
            # Datos básicos
            fila = {
                'Nombre': resultado['nombre'],
                'Gerencia': resultado.get('gerencia', 'N/A'),
                'C. Jurídica': resultado.get('c_juridica', 'N/A'),
            }
            
            # Agregar semanas
            for semana_num in sorted(resultado['semanas'].keys()):
                semana_info = resultado['semanas'][semana_num]
                diferencia = semana_info['diferencia_minutos']
                texto_semana = Formatter._minutos_a_hora_texto(diferencia)
                
                # Símbolo de estado
                if diferencia >= 0:
                    estado_semana = "✅"
                elif -59 <= diferencia < 0:
                    estado_semana = "⚠️"
                else:
                    estado_semana = "❌"
                
                # Marcar si es semana parcial
                es_parcial = " (P)" if semana_info.get('es_parcial') else ""
                
                fila[f'Sem {semana_num}'] = f"{estado_semana} {texto_semana}{es_parcial}"
            
            # Total mes
            total_minutos = resultado['total_minutos_mes']
            texto_total = Formatter._minutos_a_hora_texto(total_minutos)
            
            if total_minutos <= -60:
                estado_total = "❌"
            elif total_minutos < 0:
                estado_total = "⚠️"
            else:
                estado_total = "✅"
            
            fila['Total Mes'] = f"{estado_total} {texto_total}"
            
            datos.append(fila)
        
        return pd.DataFrame(datos)
    
    @staticmethod
    def crear_df_detalle_semana(dias_info):
        """
        Crea DataFrame detallado de días en una semana
        
        Columns: Día, HoraEntrada, HoraSalida, HorasTrabajadas, Acumulado, Observación
        """
        datos = []
        
        for dia in dias_info:
            fila = {
                'Día': f"{dia['día']} {dia['número']}",
                'Hora Entrada': dia.get('hora_entrada', '-'),
                'Hora Salida': dia.get('hora_salida', '-'),
                'Horas Trabajadas': Formatter._minutos_a_hora_texto(dia['minutos']),
                'Acumulado Semana': Formatter._minutos_a_hora_texto(dia['acumulado']),
                'Observación': dia.get('observacion', '')
            }
            datos.append(fila)
        
        return pd.DataFrame(datos)
    
    @staticmethod
    def aplicar_colores_semana(df, col_semana):
        """Retorna función para colorear celda de semana"""
        def colorear(val):
            if not val or pd.isna(val):
                return f'background-color: {Formatter.COLOR_BLANCO}'
            
            # Extraer minutos del texto "✅ -00:30"
            try:
                parte_texto = str(val).split(' ')[-1]  # Obtiene "-00:30(P)" o "-00:30"
                parte_texto = parte_texto.replace('(P)', '')  # Remover marca de parcial
                
                horas, minutos = map(int, parte_texto.replace('-', '').split(':'))
                diferencia = -(horas * 60 + minutos) if '-' in parte_texto else (horas * 60 + minutos)
                
                color, _ = Formatter.determinar_color_semana(diferencia)
                return f'background-color: {color}'
            except:
                return f'background-color: {Formatter.COLOR_BLANCO}'
        
        return colorear
