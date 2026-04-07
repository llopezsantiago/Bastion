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

# --- VERIFICACIÓN DE SESIÓN ---
if "user_authenticated" not in st.session_state or not st.session_state["user_authenticated"]:
    st.warning("⚠️ Acceso restringido. Por favor inicie sesión.")
    st.stop()

# --- FUNCIÓN DE CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_cloud_data(username):
    """Descarga y procesa el CSV desde Supabase adaptado a KANAL_ventas."""
    supabase = get_supabase()
    path = f"{username}_ventas.csv"
    try:
        response = supabase.storage.from_("datasets").download(path)
        df = pd.read_csv(io.BytesIO(response))
        
        # Procesamiento de Fechas
        if 'Marca temporal' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Marca temporal'], errors='coerce')
        
        # Procesamiento de Valores Numéricos y Cálculos
        if 'Cantidad' in df.columns and 'Precio unitario' in df.columns:
            df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
            df['Precio unitario'] = pd.to_numeric(df['Precio unitario'], errors='coerce').fillna(0)
            df['Ventas'] = df['Cantidad'] * df['Precio unitario']
            
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        return pd.DataFrame()

# Carga inicial de datos
df = load_cloud_data(st.session_state["username"])

# Validación de datos existentes
if df.empty:
    st.error("No hay datos disponibles para mostrar.")
    st.stop()

# ==========================================
# 3. BARRA LATERAL (CENTER CONTROL)
# ==========================================
with st.sidebar:
    # Encabezado Personalizado con Estilo
    st.title("🛡️ Bastion Data")
    st.subheader(f"Analista: {st.session_state['name']}")
    st.markdown("---")
    
    # --- SECCIÓN DE FILTROS ---
    st.markdown("### 🔍 Panel de Filtros")
    
    # 1. Filtro de Rango de Fechas (Esencial para Business Analytics)
    min_date = df['Fecha'].min().to_pydatetime()
    max_date = df['Fecha'].max().to_pydatetime()
    
    date_range = st.date_input(
        "Seleccione Periodo:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # 2. Filtro de Producto (Multiselect mejorado)
    productos_disponibles = sorted(df["Producto"].unique())
    producto_selected = st.multiselect(
        "Filtrar por Producto:", 
        options=productos_disponibles, 
        default=productos_disponibles,
        help="Seleccione uno o varios productos para comparar"
    )

    st.markdown("---")
    
    # --- SECCIÓN DE USUARIO Y CONFIGURACIÓN ---
    with st.expander("👤 Cuenta y Soporte"):
        st.write(f"**Usuario:** {st.session_state['username']}")
        if st.button("Cerrar Sesión", use_container_width=True, type="secondary"):
            st.session_state["user_authenticated"] = False
            st.rerun()

# ==========================================
# LÓGICA DE FILTRADO (REACTIVA)
# ==========================================

# Aplicar filtro de fecha (solo si se seleccionó un rango válido)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Fecha'].dt.date >= start_date) & (df['Fecha'].dt.date <= end_date)
    df_selection = df.loc[mask]
else:
    df_selection = df.copy()

# Aplicar filtro de producto
df_selection = df_selection[df_selection["Producto"].isin(producto_selected)]

# ==========================================
# CUERPO PRINCIPAL DEL DASHBOARD
# ==========================================

if not df_selection.empty:
    st.title(f"📊 Dashboard: {st.session_state['name']}")
    st.caption("Análisis estratégico de ventas y rendimiento operativo.")
    st.markdown("---")

    # --- MÉTRICAS PRINCIPALES (KPIs sobre df_selection) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_ventas = df_selection['Ventas'].sum()
        st.metric("Ingresos Totales", f"${total_ventas:,.2f}")
        
    with col2:
        total_items = df_selection['Cantidad'].sum()
        st.metric("Productos Vendidos", int(total_items))
        
    with col3:
        ticket_promedio = total_ventas / len(df_selection) if len(df_selection) > 0 else 0
        st.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")

    st.markdown("---")

    # --- GRÁFICOS (utilizando df_selection) ---
    fila_graficos_1 = st.columns(2)

    with fila_graficos_1[0]:
        st.subheader("📈 Evolución de Ventas")
        if 'Fecha' in df_selection.columns:
            # Agrupar por día para visualización clara
            df_diario = df_selection.groupby(df_selection['Fecha'].dt.date)['Ventas'].sum().reset_index()
            fig_linea = px.line(
                df_diario, 
                x='Fecha', 
                y='Ventas',
                markers=True,
                template="plotly_white",
                color_discrete_sequence=['#FF4B4B']
            )
            fig_linea.update_layout(hovermode="x unified")
            st.plotly_chart(fig_linea, use_container_width=True)

    with fila_graficos_1[1]:
        st.subheader("🏆 Productos más Vendidos")
        if 'Producto' in df_selection.columns:
            df_prod = df_selection.groupby('Producto')['Ventas'].sum().sort_values(ascending=True).reset_index()
            fig_barras = px.bar(
                df_prod, 
                x='Ventas', 
                y='Producto', 
                orientation='h',
                color='Ventas',
                color_continuous_scale='Reds'
            )
            # Invertimos el eje Y para que el mejor producto aparezca arriba
            fig_barras.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_barras, use_container_width=True)

    # --- TABLA DE DATOS RECIENTES ---
    st.subheader("📄 Últimas Transacciones (Filtradas)")
    st.dataframe(
        df_selection.sort_values(by='Fecha', ascending=False), 
        use_container_width=True,
        hide_index=True
    )

else:
    # Caso donde los filtros dejan el dashboard sin datos
    st.warning("No hay datos que coincidan con los filtros seleccionados.")
    if st.button("Restablecer filtros"):
        st.rerun()