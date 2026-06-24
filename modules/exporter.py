"""
exporter.py - Exportación de resultados
"""

import pandas as pd
from io import BytesIO
import xlsxwriter


class Exporter:
    """Exporta resultados en diferentes formatos"""
    
    @staticmethod
    def exportar_csv(df):
        """Exporta DataFrame a CSV"""
        return df.to_csv(index=False)
    
    @staticmethod
    def exportar_excel(df):
        """Exporta DataFrame a Excel con formatos"""
        excel_buffer = BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Obtener workbook y worksheet para aplicar formatos
            workbook = writer.book
            worksheet = writer.sheets['Resumen']
            
            # Definir formatos
            formato_verde = workbook.add_format({
                'bg_color': '#90EE90',
                'border': 1
            })
            formato_amarillo = workbook.add_format({
                'bg_color': '#FFD700',
                'border': 1
            })
            formato_rojo = workbook.add_format({
                'bg_color': '#FF6B6B',
                'border': 1
            })
            
            # Ajustar ancho de columnas
            worksheet.set_column('A:A', 30)  # Nombre
            worksheet.set_column('B:B', 20)  # Gerencia
            worksheet.set_column('C:C', 15)  # C. Jurídica
            
            # Aplicar formatos a las semanas
            for row_num, row_data in enumerate(df.values, 1):
                for col_num, valor in enumerate(row_data):
                    if isinstance(valor, str) and ('✅' in str(valor) or '⚠️' in str(valor) or '❌' in str(valor)):
                        if '✅' in str(valor):
                            worksheet.write(row_num, col_num, valor, formato_verde)
                        elif '⚠️' in str(valor):
                            worksheet.write(row_num, col_num, valor, formato_amarillo)
                        elif '❌' in str(valor):
                            worksheet.write(row_num, col_num, valor, formato_rojo)
        
        return excel_buffer.getvalue()
    
    @staticmethod
    def exportar_html(df):
        """Exporta DataFrame a HTML interactivo"""
        html = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DTPM - Reporte de Horas</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f5f5f5;
                    padding: 20px;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                
                h1 {
                    color: #1f77b4;
                    margin-bottom: 10px;
                    text-align: center;
                }
                
                .subtitle {
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 14px;
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                
                th {
                    background-color: #1f77b4;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }
                
                td {
                    padding: 12px;
                    border-bottom: 1px solid #ddd;
                }
                
                tr:hover {
                    background-color: #f9f9f9;
                }
                
                .verde { background-color: #90EE90; }
                .amarillo { background-color: #FFD700; }
                .rojo { background-color: #FF6B6B; }
                
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                    border-top: 1px solid #ddd;
                    padding-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⏱️ DTPM - Reporte de Cumplimiento de Horas</h1>
                <p class="subtitle">Análisis de cumplimiento horario de funcionarios</p>
                
        """
        
        # Agregar tabla
        html += df.to_html(classes='tabla', index=False)
        
        html += """
                <div class="footer">
                    <p>Reporte generado automáticamente por DTPM - Herramienta de Cálculo de Horas</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
