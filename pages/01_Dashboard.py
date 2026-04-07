import streamlit as st
import pandas as pd
import plotly.express as px
import io
from usuario import get_supabase

# Configuración de página
st.set_page_config(page_title="Dashboard Estratégico - Bastion", layout="wide")

if "user_authenticated" not in st.session_state or not st.session_state["user_authenticated"]:
    st.warning("⚠️ Acceso restringido. Por favor inicie sesión.")
    st.stop()

@st.cache_data(ttl=600)
def load_cloud_data(username):
    """Descarga y procesa el CSV desde Supabase adaptado a KANAL_ventas."""
    supabase = get_supabase()
    path = f"{username}_ventas.csv"
    try:
        # Descarga del storage
        response = supabase.storage.from_("datasets").download(path)
        df = pd.read_csv(io.BytesIO(response))
        
        # --- ADAPTACIÓN DE COLUMNAS DE GOOGLE SHEETS ---
        
        # 1. Convertir 'Marca temporal' a Fecha
        if 'Marca temporal' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Marca temporal'], errors='coerce')
        
        # 2. Calcular Ventas (Cantidad * Precio unitario)
        if 'Cantidad' in df.columns and 'Precio unitario' in df.columns:
            # Aseguramos que sean números
            df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
            df['Precio unitario'] = pd.to_numeric(df['Precio unitario'], errors='coerce').fillna(0)
            df['Ventas'] = df['Cantidad'] * df['Precio unitario']
            
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        return pd.DataFrame()

# Carga de datos
df = load_cloud_data(st.session_state["username"])

if not df.empty:
    st.title(f"📊 Dashboard: {st.session_state['name']}")
    st.markdown("---")

    # --- MÉTRICAS PRINCIPALES (KPIs) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_ventas = df['Ventas'].sum() if 'Ventas' in df.columns else 0
        st.metric("Ingresos Totales", f"${total_ventas:,.2f}")
        
    with col2:
        total_items = df['Cantidad'].sum() if 'Cantidad' in df.columns else 0
        st.metric("Productos Vendidos", int(total_items))
        
    with col3:
        ticket_promedio = total_ventas / len(df) if len(df) > 0 else 0
        st.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")

    st.markdown("---")

    # --- GRÁFICOS ---
    fila_graficos_1 = st.columns(2)

    with fila_graficos_1[0]:
        st.subheader("📈 Evolución de Ventas")
        if 'Fecha' in df.columns and 'Ventas' in df.columns:
            # Agrupar por día para una línea más limpia
            df_diario = df.groupby(df['Fecha'].dt.date)['Ventas'].sum().reset_index()
            fig_linea = px.line(
                df_diario, 
                x='Fecha', 
                y='Ventas',
                markers=True,
                template="plotly_white",
                color_discrete_sequence=['#FF4B4B']
            )
            st.plotly_chart(fig_linea, use_container_width=True)

    with fila_graficos_1[1]:
        st.subheader("🏆 Productos más Vendidos")
        if 'Producto' in df.columns:
            df_prod = df.groupby('Producto')['Ventas'].sum().sort_values(ascending=False).reset_index()
            fig_barras = px.bar(
                df_prod, 
                x='Ventas', 
                y='Producto', 
                orientation='h',
                color='Ventas',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_barras, use_container_width=True)

    # --- TABLA DE DATOS RECIENTES ---
    st.subheader("📄 Últimas Transacciones")
    st.dataframe(df.sort_values(by='Fecha', ascending=False), use_container_width=True)

else:
    st.title(f"Bienvenido, {st.session_state['name']}")
    st.info("Aún no hay datos registrados para este comercio. Por favor, suba el archivo CSV desde el Panel de Administrador.")
    
    with st.expander("Ayuda: Formato del archivo"):
        st.write("""
        El sistema detectó que su archivo debe contener las siguientes columnas exactas:
        - **Marca temporal** (Fecha y hora)
        - **Producto**
        - **Cantidad**
        - **Precio unitario**
        """)