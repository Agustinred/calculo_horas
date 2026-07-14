"""
modules/exporter.py
Exportador de resultados en diferentes formatos
"""

import pandas as pd
import io


class Exporter:
    """Exporta resultados en diferentes formatos"""
    
    @staticmethod
    def exportar_csv(df_resumen):
        """Exporta resumen a CSV"""
        return df_resumen.to_csv(index=False).encode('utf-8')
    
    @staticmethod
    def exportar_excel(df_resumen):
        """Exporta resumen a Excel"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def exportar_permisos_excel(df_permisos):
        """Exporta el detalle de permisos (original + manuales) a Excel"""
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_permisos.to_excel(writer, sheet_name='Permisos', index=False)

        output.seek(0)
        return output.getvalue()

    @staticmethod
    def exportar_html(df_resumen):
        """Exporta resumen a HTML"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reporte de Horas</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                h1 {
                    color: #333;
                    border-bottom: 3px solid #1f77b4;
                    padding-bottom: 10px;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                th {
                    background-color: #1f77b4;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                }
                td {
                    padding: 10px 12px;
                    border-bottom: 1px solid #ddd;
                }
                tr:hover {
                    background-color: #f9f9f9;
                }
                .estado-ok {
                    color: green;
                    font-weight: bold;
                }
                .estado-warning {
                    color: orange;
                    font-weight: bold;
                }
                .estado-error {
                    color: red;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <h1>📊 Reporte de Cumplimiento Horario - DTPM</h1>
        """
        
        # Agregar tabla
        html += df_resumen.to_html(index=False, border=0)
        
        html += """
        </body>
        </html>
        """
        
        return html.encode('utf-8')
