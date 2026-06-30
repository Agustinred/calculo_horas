import pandas as pd


class HorasCalculator:
    """
    Calcula horas trabajadas por funcionario.
    
    IMPORTANTE sobre las columnas del Excel:
    - DiaSemana: NÚMERO (1=Lunes, 2=Martes, ..., 6=Sábado, 7=Domingo)
    - DiaPalabra: TEXTO (LUNES, MARTES, ..., SABADO, DOMINGO)
    - fecha: número entero Excel (días desde 1899-12-30)
    
    Siempre usar DiaPalabra para detectar el día de la semana.
    """

    JUSTIFICACIONES_COMPLETAS = [
        "licencia médica", "lic. médica", "lic med",
        "per. con goce", "permiso con goce", "con goce",
        "per. compl. día", "permiso completo",
        "permiso matrimonio", "matrimonio",
        "vacaciones", "año nuevo", "viernes santo", "sabado santo",
        "feriado", "día feriado", "justificado",
        "permiso postnatal",
        "per. comple. (horas), jornada medio día"
    ]

    JUSTIFICACIONES_PARCIALES = {
        "permiso adm. (mañana)": "mañana",
        "permiso adm. (tarde)": "tarde",
        "permiso adm mañana": "mañana",
        "permiso adm tarde": "tarde"
    }

    @staticmethod
    def _hora_a_minutos(hora_str):
        if not hora_str or pd.isna(hora_str):
            return 0
        hora_str = str(hora_str).strip()
        if hora_str.lower() in ['none', 'nan', 'nat', '']:
            return 0
        try:
            partes = hora_str.split(':')
            return int(partes[0]) * 60 + int(partes[1])
        except:
            return 0

    @staticmethod
    def _minutos_a_hora(minutos):
        horas = abs(minutos) // 60
        mins = abs(minutos) % 60
        signo = '-' if minutos < 0 else ''
        return f"{signo}{horas:02d}:{mins:02d}"

    @staticmethod
    def _es_fin_de_semana(dia_palabra):
        """Detecta si un día es sábado o domingo usando DiaPalabra (texto)"""
        d = str(dia_palabra).strip().upper()
        return d in ['SABADO', 'SÁBADO', 'DOMINGO']

    @staticmethod
    def _obtener_horas_esperadas(dia_palabra):
        """
        Retorna minutos esperados según DiaPalabra (texto).
        SABADO / DOMINGO → 0
        VIERNES          → 480 (8h)
        resto            → 540 (9h)
        """
        d = str(dia_palabra).strip().upper()
        if d in ['SABADO', 'SÁBADO', 'DOMINGO']:
            return 0
        elif d == 'VIERNES':
            return 8 * 60
        else:
            return 9 * 60

    @staticmethod
    def _es_justificacion_completa(observacion):
        if not observacion or pd.isna(observacion):
            return False
        obs = str(observacion).strip().lower()
        return any(j in obs for j in HorasCalculator.JUSTIFICACIONES_COMPLETAS)

    @staticmethod
    def _obtener_justificacion_parcial(observacion):
        if not observacion or pd.isna(observacion):
            return None
        obs = str(observacion).strip().lower()
        for key, val in HorasCalculator.JUSTIFICACIONES_PARCIALES.items():
            if key in obs:
                return val
        return None

    @staticmethod
    def _convertir_fecha(valor_fecha):
        """
        Convierte el campo 'fecha' del Excel a string YYYY-MM-DD.
        La columna 'fecha' viene como número serial de Excel (numpy.int64).
        Ejemplo: 46031 → 2026-01-09
        Fórmula: fecha = 1899-12-30 + serial días
        """
        if valor_fecha is None or pd.isna(valor_fecha):
            return None
        try:
            # Siempre convertir a int de Python (maneja numpy.int64, float, etc.)
            serial = int(valor_fecha)
            ts = pd.Timestamp('1899-12-30') + pd.Timedelta(days=serial)
            return ts.strftime('%Y-%m-%d')
        except:
            try:
                return pd.to_datetime(valor_fecha).strftime('%Y-%m-%d')
            except:
                return None

    @staticmethod
    def calcular_horas_dia(row, fecha_str=None, dict_permisos=None):
        """
        Calcula minutos trabajados en un día.
        Retorna: (minutos_totales, minutos_externos, alerta_o_None)
        """
        dict_permisos = dict_permisos or {}

        hora_entrada = str(row.get('HoraEntrada', '')).strip() if pd.notna(row.get('HoraEntrada')) else ""
        hora_salida  = str(row.get('HoraSalida',  '')).strip() if pd.notna(row.get('HoraSalida'))  else ""
        if hora_entrada.lower() in ['none', 'nan', 'nat']: hora_entrada = ""
        if hora_salida.lower()  in ['none', 'nan', 'nat']: hora_salida  = ""

        observacion      = str(row.get('Observacion', '')).strip() if pd.notna(row.get('Observacion')) else ""
        dia_palabra      = str(row.get('DiaPalabra', '')).strip().upper()
        nombre_norm      = str(row.get('Nombre_Normalizado', '')).strip()
        nombre_display   = str(row.get('Nombre', '')).strip()
        numero_dia       = row.get('Número', '')

        horas_esperadas = HorasCalculator._obtener_horas_esperadas(dia_palabra)
        es_finde        = HorasCalculator._es_fin_de_semana(dia_palabra)

        # --- Buscar permiso externo ---
        minutos_externos = 0
        if fecha_str and nombre_norm:
            llave = (nombre_norm, fecha_str)
            minutos_externos = dict_permisos.get(llave, 0)

        # --- Fin de semana: siempre 0 ---
        if es_finde:
            return 0, 0, None

        # --- Calcular minutos reales si hay marcas ---
        tiene_marcas = (hora_entrada != "" and hora_salida != "")
        minutos_reales = 0
        if tiene_marcas:
            minutos_reales = max(0, HorasCalculator._hora_a_minutos(hora_salida) - HorasCalculator._hora_a_minutos(hora_entrada))

        # --- Justificación parcial (media jornada) ---
        just_parcial = HorasCalculator._obtener_justificacion_parcial(observacion)
        if just_parcial in ["mañana", "tarde"]:
            bonificados = 4 * 60 if dia_palabra == 'VIERNES' else (4 * 60 + 30)
            return bonificados + minutos_reales + minutos_externos, minutos_externos, None

        # --- Justificación completa (día entero cubierto) ---
        if HorasCalculator._es_justificacion_completa(observacion):
            base = max(minutos_reales, horas_esperadas) if tiene_marcas else horas_esperadas
            return base + minutos_externos, minutos_externos, None

        # --- Caso normal con marcas ---
        if tiene_marcas:
            return minutos_reales + minutos_externos, minutos_externos, None

        # --- Sin marcas y no es fin de semana ---
        if "no hábil" in observacion.lower() or "no habil" in observacion.lower():
            return 0, 0, None

        if minutos_externos > 0:
            return minutos_externos, minutos_externos, None

        alerta = f"{nombre_display} - Día {numero_dia} ({dia_palabra}): Falta Marcación"
        return 0, 0, alerta

    @staticmethod
    def procesar_funcionario(df_empleado, dict_permisos=None):
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

            # Meta: sumar horas esperadas SOLO de días laborables (excluye sábado/domingo via DiaPalabra)
            meta_semanal = 0
            dias_laborables = 0
            for _, row in df_semana.iterrows():
                h = HorasCalculator._obtener_horas_esperadas(row.get('DiaPalabra', ''))
                meta_semanal += h
                if h > 0:
                    dias_laborables += 1

            es_parcial = dias_laborables < 5

            minutos_semana = 0
            dias_info = []
            acumulado = 0

            for _, row in df_semana.iterrows():
                # Convertir fecha desde número Excel
                fecha_str = HorasCalculator._convertir_fecha(row.get('fecha'))

                minutos_dia, minutos_ext, alerta = HorasCalculator.calcular_horas_dia(
                    row, fecha_str=fecha_str, dict_permisos=dict_permisos
                )

                minutos_semana += minutos_dia
                acumulado += minutos_dia

                if alerta:
                    resultados['alertas'].append(alerta)

                dias_info.append({
                    'día':          row.get('DiaPalabra', ''),
                    'número':       row.get('Número', ''),
                    'hora_entrada': row.get('HoraEntrada', ''),
                    'hora_salida':  row.get('HoraSalida', ''),
                    'minutos':      minutos_dia,
                    'acumulado':    acumulado,
                    'minutos_externos': minutos_ext,
                    'observacion':  row.get('Observacion', ''),
                    'Fecha':        fecha_str
                })

            diferencia = minutos_semana - meta_semanal
            resultados['semanas'][int(semana_num)] = {
                'minutos_trabajados': minutos_semana,
                'minutos_esperados':  meta_semanal,
                'diferencia_minutos': diferencia,
                'días':               dias_info,
                'es_parcial':         es_parcial
            }
            resultados['dias_por_semana'][int(semana_num)] = dias_info

            if diferencia < 0:
                resultados['total_minutos_mes'] += diferencia

        return resultados

    @staticmethod
    def procesar_todos(df_hoja1, df_hoja2, dict_permisos=None):
        resultados_todos = {}
        alertas_globales = []

        df_hoja1 = df_hoja1.copy()

        # --- Tolerar variantes de encabezado: 'Numero' (sin tilde) vs 'Número' ---
        if 'Número' not in df_hoja1.columns:
            for variante in ['Numero', 'NUMERO', 'numero', 'número']:
                if variante in df_hoja1.columns:
                    df_hoja1 = df_hoja1.rename(columns={variante: 'Número'})
                    break

        if 'Nombre_Normalizado' not in df_hoja1.columns:
            df_hoja1['Nombre_Normalizado'] = df_hoja1['Nombre'].apply(
                lambda x: str(x).lower().strip() if pd.notna(x) else ''
            )

        if 'Nombre_Normalizado' not in df_hoja2.columns:
            df_hoja2 = df_hoja2.copy()
            col = 'NOMBRE' if 'NOMBRE' in df_hoja2.columns else 'Nombre'
            df_hoja2['Nombre_Normalizado'] = df_hoja2[col].apply(
                lambda x: str(x).lower().strip() if pd.notna(x) else ''
            )

        for nombre_unico in df_hoja1['Nombre_Normalizado'].unique():
            if pd.isna(nombre_unico) or nombre_unico == '':
                continue

            df_emp = df_hoja1[df_hoja1['Nombre_Normalizado'] == nombre_unico]
            resultado = HorasCalculator.procesar_funcionario(df_emp, dict_permisos=dict_permisos)

            match = df_hoja2[df_hoja2['Nombre_Normalizado'] == nombre_unico]
            if len(match) > 0:
                resultado['gerencia']   = match['GERENCIA'].iloc[0] if 'GERENCIA' in match.columns else 'N/A'
                resultado['c_juridica'] = df_emp['C_Juridica'].iloc[0] if 'C_Juridica' in df_emp.columns else 'N/A'
            else:
                resultado['gerencia']   = 'Desconocida'
                resultado['c_juridica'] = 'N/A'

            resultados_todos[nombre_unico] = resultado
            alertas_globales.extend(resultado['alertas'])

        return resultados_todos, alertas_globales
