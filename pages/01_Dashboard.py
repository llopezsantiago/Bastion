import streamlit as st
import pandas as pd
import plotly.express as px
import io
from usuario import get_supabase
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Dashboard Estratégico - Bastion", 
    page_icon="📊",
    layout="wide"
)

# --- VERIFICACIÓN DE SESIÓN (Seguridad de Estado) ---
# Usamos .get() para evitar KeyErrors si la sesión se reinicia inesperadamente
if not st.session_state.get("user_authenticated", False):
    st.warning("⚠️ Acceso restringido. Por favor inicie sesión.")
    st.stop()

# --- FUNCIÓN DE CARGA DE DATOS (Robustecida) ---
@st.cache_data(ttl=600)
def load_cloud_data(username):
    """Descarga y procesa el CSV con validación de esquema."""
    supabase = get_supabase()
    path = f"{username}_ventas.csv"
    try:
        response = supabase.storage.from_("datasets").download(path)
        df = pd.read_csv(io.BytesIO(response))
        
        # 1. Validación de Fecha: Garantizamos que la columna exista para el resto de la app
        if 'Marca temporal' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Marca temporal'], errors='coerce')
        else:
            # Si no existe la columna de origen, creamos una vacía para evitar fallos en filtros
            df['Fecha'] = pd.NaT
        
        # 2. Validación de Numéricos
        cols_numericas = ['Cantidad', 'Precio unitario']
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0
        
        # 3. Cálculo de Ventas (solo si existen las columnas necesarias)
        df['Ventas'] = df['Cantidad'] * df['Precio unitario']
            
        return df
    except Exception as e:
        st.error(f"Error crítico al procesar el archivo: {e}")
        return pd.DataFrame()

# Ejecución de carga
df = load_cloud_data(st.session_state.get("username", "unknown"))

# --- VALIDACIÓN ESTRUCTURAL ---
# Verificamos que el DF tenga datos y la columna crítica 'Fecha' sea válida
if df.empty or df['Fecha'].isnull().all():
    st.error("Error: El archivo no tiene el formato esperado o no contiene datos de fecha válidos.")
    st.info("Asegúrese de que el CSV contenga la columna 'Marca temporal'.")
    st.stop()

# ==========================================
# 3. BARRA LATERAL (CONTROL SEGURO)
# ==========================================
with st.sidebar:
    st.title("🛡️ Bastion Data")
    # Uso seguro de session_state
    user_name = st.session_state.get('name', 'Usuario')
    st.subheader(f"Analista: {user_name}")
    st.markdown("---")
    
    st.markdown("### 🔍 Panel de Filtros")
    
    # Cálculo seguro de fechas (eliminando nulos para evitar errores en .min())
    df_dates = df.dropna(subset=['Fecha'])
    min_date = df_dates['Fecha'].min().to_pydatetime()
    max_date = df_dates['Fecha'].max().to_pydatetime()
    
    date_range = st.date_input(
        "Seleccione Periodo:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtro de Producto con validación de existencia
    if 'Producto' in df.columns:
        productos_disponibles = sorted(df["Producto"].unique())
        producto_selected = st.multiselect(
            "Filtrar por Producto:", 
            options=productos_disponibles, 
            default=productos_disponibles
        )
    else:
        st.error("Columna 'Producto' no encontrada.")
        st.stop()

    st.markdown("---")
    
    with st.expander("👤 Cuenta"):
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.clear() # Limpia todo el estado por seguridad
            st.rerun()

# ==========================================
# LÓGICA DE FILTRADO (CONTROL DE TUPLAS)
# ==========================================

# Corrección de error de selección parcial: st.date_input devuelve len=1 mientras se elige el rango
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Fecha'].dt.date >= start_date) & (df['Fecha'].dt.date <= end_date)
    df_selection = df.loc[mask].copy()
else:
    # Si el rango está incompleto (ej. solo seleccionó fecha inicio), no filtramos aún
    df_selection = df.copy()

df_selection = df_selection[df_selection["Producto"].isin(producto_selected)]

# ==========================================
# CUERPO PRINCIPAL
# ==========================================

if not df_selection.empty:
    st.title(f"📊 Dashboard: {user_name}")
    st.markdown("---")

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ingresos Totales", f"${df_selection['Ventas'].sum():,.2f}")
    with col2:
        st.metric("Productos Vendidos", int(df_selection['Cantidad'].sum()))
    with col3:
        # Evitamos división por cero si df_selection tiene filas pero todas filtradas a 0
        total_rows = len(df_selection)
        ticket = df_selection['Ventas'].sum() / total_rows if total_rows > 0 else 0
        st.metric("Ticket Promedio", f"${ticket:,.2f}")

    st.markdown("---")

    # --- GRÁFICOS (Manteniendo mejoras visuales previas con lógica robusta) ---
    fila_graficos = st.columns(2)

    with fila_graficos[0]:
        st.subheader("📈 Evolución de Ingresos y Análisis de Tendencia")
        # --- PROCESAMIENTO ANALÍTICO ---
        df_diario = df_selection.groupby(df_selection['Fecha'].dt.date)['Ventas'].sum().reset_index()

        # Media móvil para tendencia
        df_diario['Media_Movil'] = df_diario['Ventas'].rolling(window=7, min_periods=1).mean()

        # Identificación de puntos clave para anotaciones
        max_ventas = df_diario['Ventas'].max()
        fecha_max = df_diario.loc[df_diario['Ventas'].idxmax(), 'Fecha']
        promedio_diario = df_diario['Ventas'].mean()

        # --- MEJORA DEL GRÁFICO ---
        fig_linea = px.line(
            df_diario, 
            x='Fecha', 
            y='Ventas', 
            template="plotly_white", 
            markers=True,
            color_discrete_sequence=["#1E3575"],
            #title="📈 Evolución de Ingresos y Análisis de Tendencia"
        )

        # 1. Capa de Tendencia (Línea punteada)
        fig_linea.add_scatter(
            x=df_diario['Fecha'], 
            y=df_diario['Media_Movil'], 
            mode='lines', 
            name='Tendencia (7d)', 
            line=dict(color='#A2A9B1', width=2, dash='dot')
        )

        # 2. Línea de Referencia (Promedio del Periodo)
        fig_linea.add_hline(
            y=promedio_diario, 
            line_dash="dash", 
            line_color="#1D4499", 
            annotation_text=f"Promedio: ${promedio_diario:,.0f}", 
            annotation_position="bottom right"
        )

        # 3. Anotación del Punto Máximo (Hito de Ventas)
        fig_linea.add_annotation(
            x=fecha_max, 
            y=max_ventas,
            text="Récord de Ventas",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            bgcolor="#1E7525",
            font=dict(color="white")
        )

        # 4. Estética Avanzada y Tooltips
        fig_linea.update_traces(
            fill='tozeroy', 
            fillcolor='rgba(30, 53, 117, 0.1)', # Azul muy tenue para el área
            line=dict(width=3),
            hovertemplate="<b>Fecha:</b> %{x}<br><b>Ventas:</b> $%{y:,.2f}<extra></extra>"
        )

        fig_linea.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                title="",
                rangeslider=dict(visible=True, thickness=0.04),
                type="date"
            ),
            yaxis=dict(
                title="Ventas Diarias ($)",
                tickprefix="$",
                tickformat=",",
                gridcolor="#F0F2F6"
            ),
            margin=dict(l=0, r=0, t=80, b=0)
        )

        st.plotly_chart(fig_linea, use_container_width=True)

    with fila_graficos[1]:
        st.subheader("🏆 Ranking de Productos: Ingresos y Cuota de Mercado")

        # --- PROCESAMIENTO ANALÍTICO AVANZADO ---
        # Se utiliza 'Ventas' para el count, evitando conflictos de indexación con 'Producto'
        df_prod = df_selection.groupby('Producto').agg(
            Ventas=('Ventas', 'sum'),
            Frecuencia=('Ventas', 'count') 
        ).reset_index()

        # Validación de división por cero y cálculo de participación
        total_v = df_prod['Ventas'].sum()
        df_prod['Porcentaje'] = df_prod['Ventas'].apply(lambda x: (x / total_v * 100) if total_v > 0 else 0)

        # Ordenamos para asegurar que el ranking sea descendente visualmente
        df_prod = df_prod.sort_values(by='Ventas', ascending=True)

        # --- CREACIÓN DEL GRÁFICO ---
        fig_barras = px.bar(
            df_prod, 
            x='Ventas', 
            y='Producto', 
            orientation='h', 
            color='Ventas',
            color_continuous_scale='Blues',
            # Etiqueta combinada: Monto ($) y Porcentaje (%)
            text=df_prod.apply(lambda row: f"${row['Ventas']:,.0f} ({row['Porcentaje']:.1f}%)", axis=1),
            # Pasamos explícitamente las columnas extra para el tooltip
            hover_data=['Porcentaje', 'Frecuencia']
        )

        # 1. Ajustes Estéticos y de Interactividad
        fig_barras.update_traces(
            textposition='outside', 
            cliponaxis=False, # Fundamental: evita que el texto fuera de la barra se corte
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5,
            opacity=0.9,
            # customdata[0] = Porcentaje, customdata[1] = Frecuencia
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Ingresos: $%{x:,.2f}<br>"
                "Participación: %{customdata[0]:.1f}%<br>"
                "Ventas realizadas: %{customdata[1]}"
                "<extra></extra>" # Oculta la traza secundaria por defecto
            )
        )

        # 2. Refinamiento del Layout
        fig_barras.update_layout(
            xaxis_title="Ventas Totales ($)",
            yaxis_title=None,
            coloraxis_showscale=False, 
            margin=dict(l=20, r=100, t=60, b=20), # Margen derecho (r) ampliado a 100 para las etiquetas
            yaxis={'categoryorder':'total ascending'},
            showlegend=False,
            height=500, 
            font=dict(size=12),
            plot_bgcolor='rgba(0,0,0,0)' 
        )

        # 3. Línea de Referencia (Promedio de Ventas)
        promedio_v = df_prod['Ventas'].mean()
        fig_barras.add_vline(
            x=promedio_v, 
            line_dash="dot", 
            line_color="#FF4B4B", 
            annotation_text="Venta Promedio", 
            annotation_position="bottom right"
        )

        # Renderizado final
        st.plotly_chart(fig_barras, use_container_width=True)

    # --- TABLA ---
    st.subheader("📄 Detalle de Operaciones")
    st.dataframe(df_selection.sort_values(by='Fecha', ascending=False), use_container_width=True, hide_index=True)

else:
    st.warning("No hay datos para los filtros seleccionados.")
    #if st.button("Restablecer"): st.rerun()