# ⏱️ DTPM - Herramienta de Cálculo de Horas

Herramienta web para análisis automático de cumplimiento horario de funcionarios en la Red Movilidad DTPM.

## 📋 Características

✅ **Cálculo automático de horas**
- Suma horas semanales (44 hrs requeridas)
- Detección de marcaciones incompletas
- Análisis mensual de diferencias

✅ **Múltiples archivos**
- Carga y analiza varios meses simultáneamente
- Comparación entre períodos

✅ **Filtros avanzados**
- Por Gerencia
- Por Calidad Jurídica (HONORARIO/CONTRATA)

✅ **Visualización intuitiva**
- Tabla de resumen con colores (Verde/Amarillo/Rojo)
- Detalles por funcionario
- Estadísticas del período

✅ **Exportación flexible**
- CSV para Excel
- Excel formateado
- HTML para publicación web

---

## 🚀 Instalación Rápida

### Opción 1: Streamlit Cloud (Recomendado)

1. **Fork este repositorio en GitHub**
   - Usa el botón "Fork" en la esquina superior derecha

2. **Ir a https://share.streamlit.io**
   - Click en "New app"
   - Selecciona: Repository → Branch → Main file path: `app.py`
   - Click "Deploy"

3. **Listo** - Tu app estará en vivo en ~2-3 minutos

### Opción 2: Instalación Local

1. **Clonar repositorio**
   ```bash
   git clone https://github.com/TU_USUARIO/herramienta-horas-dtpm.git
   cd herramienta-horas-dtpm
   ```

2. **Crear entorno virtual (opcional pero recomendado)**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar aplicación**
   ```bash
   streamlit run app.py
   ```

5. **Acceder**
   - Se abrirá automáticamente en http://localhost:8501

---

## 📁 Estructura de Archivos

```
herramienta-horas-dtpm/
├── app.py                      # Aplicación principal
├── requirements.txt            # Dependencias
├── .streamlit/
│   └── config.toml            # Configuración de tema
├── modules/
│   ├── __init__.py
│   ├── data_loader.py         # Carga y valida Excel
│   ├── calculator.py          # Lógica de cálculo
│   ├── formatter.py           # Formatos y colores
│   └── exporter.py            # Exportación
├── README.md                   # Este archivo
└── .gitignore
```

---

## 📊 Formato del Archivo Excel

### Hoja1: Datos de Marcación

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| Nombre | Nombre funcionario | CLAUDIA ABARCA |
| Número | Día del mes | 1, 2, 3... |
| DiaSemana | Nombre del día | LUNES, MARTES... |
| Semana | Número semana | 1, 2, 3, 4 |
| HoraEntrada | Hora entrada (HH:MM) | 08:30 |
| HoraSalida | Hora salida (HH:MM) | 17:00 |
| C_Juridica | Calidad jurídica | HONORARIO, CONTRATA |
| Observacion | Observaciones especiales | VACACIONES, LIC. MÉDICA |

### Hoja2: Catálogo de Nombres

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| NOMBRE | Nombre funcionario | Claudia Abarca |
| GERENCIA | Gerencia asignada | GAP, GEGC, GP |

---

## 🔧 Reglas de Cálculo

### 1. Horas por Día
- **Lunes a Jueves**: 9 horas (sin aproximaciones)
- **Viernes**: 8 horas (sin aproximaciones)

### 2. Justificaciones
Si hay observación de:
- `LIC. MÉDICA`, `VACACIONES`, `PERMISO MATRIMONIO`, etc. → Cuenta como día completo
- `PERMISO ADM. (MAÑANA)` → 7:30 a 15:00 (cuentan horas después de 15:00)
- `PERMISO ADM. (TARDE)` → Desde 12:30 (cuentan horas antes de 12:30)

### 3. Meta Semanal
- Total semana: 44 horas
- Evaluación: **Cada semana de forma independiente**
- Tolerancia mensual: **Máximo 59 minutos faltantes**

### 4. Colores
- **Verde ✅**: Cumple 44 hrs o diferencia pequeña
- **Amarillo ⚠️**: Falta entre 1-59 minutos
- **Rojo ❌**: Falta 60+ minutos O total mes >59 min

---

## ⚠️ Alertas Automáticas

La herramienta detecta automáticamente:
- Falta de HoraEntrada
- Falta de HoraSalida
- Combinaciones inválidas de permisos
- Incumplimiento mensual >59 minutos

---

## 💻 Requisitos Técnicos

- Python 3.8+
- Navegador web moderno (Chrome, Firefox, Safari, Edge)
- Conexión a internet (si es Streamlit Cloud)

---

## 🐛 Solución de Problemas

### "No se encuentra la columna X"
- Verifica que la columna existe en tu Excel
- Asegúrate de que el nombre sea exacto (mayúsculas/minúsculas)

### "No se carga el archivo"
- Comprueba que el archivo está en formato .xlsx o .xls
- Verifica que tienes Hoja1 y Hoja2

### "Las horas no suman correctamente"
- Revisa que los tiempos estén en formato HH:MM (24 hrs)
- Comprueba que no hay observaciones especiales sin procesar

---

## 📝 Cambios y Mejoras

Para sugerir cambios:
1. Haz un fork del repositorio
2. Crea una rama nueva
3. Haz commit de tus cambios
4. Envía un Pull Request

---

## 📧 Contacto y Soporte

Para dudas o reportar errores:
- Abre un Issue en GitHub
- Contacta al equipo GMI de DTPM

---

## 📄 Licencia

Este proyecto es de uso interno DTPM.

---

**Última actualización:** Junio 2024
