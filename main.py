import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

st.set_page_config(
  page_title="Análisis SUBE: Colectivos",
  page_icon="🚌",
  layout="wide"
)

st.title("🚌 Análisis SUBE - Solo Colectivos")

# --- Rutas ---
DATA_PATH = Path("data")
FILES = {
  2025: DATA_PATH / "dat-ab-usos-2025.csv",
  2026: DATA_PATH / "dat-ab-usos-2026.csv"
}

# --- Diccionario para meses y días en español ---
MESES_ES = {
  1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
  7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

DIAS_ES = {
  0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
}

@st.cache_data
def load_data(year):
  if not FILES[year].exists():
    return pd.DataFrame()
  
  df = pd.read_csv(FILES[year], parse_dates=["DIA_TRANSPORTE"])
  df = df[df["TIPO_TRANSPORTE"] == "COLECTIVO"]
  
  # Nuevas columnas temporales
  df['Mes_Nombre'] = df['DIA_TRANSPORTE'].dt.month.map(MESES_ES)
  df['Mes_Num'] = df['DIA_TRANSPORTE'].dt.month
  df['Dia_Semana_Nombre'] = df['DIA_TRANSPORTE'].dt.dayofweek.map(DIAS_ES)
  df['Dia_Semana_Num'] = df['DIA_TRANSPORTE'].dt.dayofweek
  df['Dia_Mes_Str'] = df['DIA_TRANSPORTE'].dt.strftime('%d ') + df['DIA_TRANSPORTE'].dt.month.map(lambda x: MESES_ES[x][:3])
  
  return df

# --- Sidebar: Filtros ---
st.sidebar.header("Filtros Generales")
year = st.sidebar.selectbox("Año", options=[2025, 2026], index=1)

df_base = load_data(year)

if not df_base.empty:
  # 1. Filtro Municipio
  municipios = sorted(df_base["MUNICIPIO"].dropna().unique())
  default_index = municipios.index("CORONEL ROSALES") if "CORONEL ROSALES" in municipios else 0
  municipio = st.sidebar.selectbox("Municipio", options=municipios, index=default_index)
  
  df_mun = df_base[df_base["MUNICIPIO"] == municipio]

  # Nuevo Filtro de Meses
  st.sidebar.divider()
  meses_disponibles = df_mun.sort_values("Mes_Num")["Mes_Nombre"].unique()
  meses_seleccionados = st.sidebar.multiselect(
    "Seleccionar Meses",
    options=meses_disponibles,
    default=list(meses_disponibles)
  )
  
  # Aplicamos filtro de meses antes de seguir
  df_mun = df_mun[df_mun["Mes_Nombre"].isin(meses_seleccionados)]

  st.sidebar.divider()
  st.sidebar.header("Empresas y Líneas")
  
  # 2. Filtro Empresas
  empresas_disponibles = sorted(df_mun["NOMBRE_EMPRESA"].dropna().unique())
  empresas_seleccionadas = st.sidebar.multiselect(
    "Seleccionar Empresas",
    options=empresas_disponibles,
    default=empresas_disponibles
  )

  df_emp = df_mun[df_mun["NOMBRE_EMPRESA"].isin(empresas_seleccionadas)]

  # 3. Filtro Líneas
  lineas_disponibles = sorted(df_emp["LINEA"].dropna().unique())
  lineas_seleccionadas = st.sidebar.multiselect(
    "Seleccionar Líneas",
    options=lineas_disponibles,
    default=lineas_disponibles
  )

  # Filtrado Final
  df_final = df_emp[df_emp["LINEA"].isin(lineas_seleccionadas)].copy()

  if df_final.empty:
    st.warning("⚠️ No hay datos de colectivos para los filtros seleccionados.")
  else:
    df_final = df_final.sort_values("DIA_TRANSPORTE")

    # --- Métricas ---
    total_viajes = df_final["CANTIDAD"].sum()
    dias = df_final["DIA_TRANSPORTE"].nunique()
    promedio_diario = total_viajes / dias if dias > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total viajes (Colectivo)", f"{total_viajes:,}".replace(",", "."))
    col2.metric("Días registrados", dias)
    col3.metric("Promedio diario", f"{promedio_diario:,.0f}".replace(",", "."))

    st.divider()

    # --- Gráficos de Barras Apiladas ---
    st.subheader(f"Uso de Colectivos en {municipio}")
    tab1, tab2 = st.tabs(["📊 Por Líneas", "🏢 Por Empresa"])
    
    # Preparamos el orden del eje X para que no se desordenen los meses
    orden_eje_x = df_final.sort_values("DIA_TRANSPORTE")["Dia_Mes_Str"].unique()

    with tab1:
      df_diario_linea = df_final.groupby(["DIA_TRANSPORTE", "Dia_Mes_Str", "LINEA"], as_index=False)["CANTIDAD"].sum()
      fig_bar_linea = px.bar(
        df_diario_linea, x="Dia_Mes_Str", y="CANTIDAD", color="LINEA",
        title="Viajes diarios apilados por LÍNEA",
        labels={"CANTIDAD": "Viajes", "Dia_Mes_Str": "Día", "LINEA": "Línea"},
        category_orders={"Dia_Mes_Str": orden_eje_x}
      )
      st.plotly_chart(fig_bar_linea, width='stretch')

    with tab2:
      df_diario_emp = df_final.groupby(["DIA_TRANSPORTE", "Dia_Mes_Str", "NOMBRE_EMPRESA"], as_index=False)["CANTIDAD"].sum()
      fig_bar_emp = px.bar(
        df_diario_emp, x="Dia_Mes_Str", y="CANTIDAD", color="NOMBRE_EMPRESA",
        title="Viajes diarios apilados por EMPRESA",
        labels={"CANTIDAD": "Viajes", "Dia_Mes_Str": "Día", "NOMBRE_EMPRESA": "Empresa"},
        category_orders={"Dia_Mes_Str": orden_eje_x}
      )
      st.plotly_chart(fig_bar_emp, width='stretch')

    st.divider()

    # --- Análisis de Impacto ---
    col_pie, col_table = st.columns([1, 2])
    
    df_resumen = df_final.groupby(["NOMBRE_EMPRESA", "LINEA"]).agg(
      Viajes=("CANTIDAD", "sum"),
      Dias=("DIA_TRANSPORTE", "nunique")
    ).reset_index()
    df_resumen["Promedio"] = (df_resumen["Viajes"] / df_resumen["Dias"]).round(0)

    with col_pie:
      st.write("**Market Share por Línea**")
      fig_pie = px.pie(df_resumen, values="Viajes", names="LINEA", hole=0.3)
      fig_pie.update_layout(showlegend=False)
      st.plotly_chart(fig_pie, width='stretch')

    with col_table:
      st.write("**Detalle de Rendimiento**")
      st.dataframe(df_resumen.sort_values("Viajes", ascending=False), width='stretch', hide_index=True)
    st.divider()
    
    st.subheader("📅 Promedio de Viajes por Día de la Semana")
    
    # Calculamos el promedio: Total de viajes en cada fecha / Cantidad de veces que ocurrió ese día
    # Paso 1: Sumar total por cada día calendario
    df_diario_total = df_final.groupby(["DIA_TRANSPORTE", "Dia_Semana_Nombre", "Dia_Semana_Num"])["CANTIDAD"].sum().reset_index()
    
    # Paso 2: Promediar por tipo de día (Lunes, Martes, etc.)
    df_semana_avg = df_diario_total.groupby(["Dia_Semana_Nombre", "Dia_Semana_Num"])["CANTIDAD"].mean().reset_index()
    df_semana_avg = df_semana_avg.sort_values("Dia_Semana_Num")
    
    fig_dias = px.bar(
      df_semana_avg,
      x="Dia_Semana_Nombre",
      y="CANTIDAD",
      title="¿Qué días se viaja más? (Promedio diario)",
      labels={"CANTIDAD": "Promedio de Viajes", "Dia_Semana_Nombre": "Día"},
      color="CANTIDAD",
      color_continuous_scale="Blues",
      text_auto='.0f' # type: ignore
    )
    st.plotly_chart(fig_dias, width='stretch')

else:
  st.error("No se pudo cargar la base de datos.")