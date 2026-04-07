import streamlit as st
import pandas as pd
import plotly.express as px
import io
from usuario import get_supabase

if "user_authenticated" not in st.session_state or not st.session_state["user_authenticated"]:
    st.warning("⚠️ Acceso restringido. Por favor inicie sesión.")
    st.stop()

st.set_page_config(page_title="Dashboard Estratégico", layout="wide")

@st.cache_data(ttl=600)
def load_cloud_data(username):
    supabase = get_supabase()
    path = f"{username}_ventas.csv"
    try:
        # Descarga directa del archivo desde el storage de Supabase
        response = supabase.storage.from_("datasets").download(path)
        df = pd.read_csv(io.BytesIO(response))
        
        # Normalización de Fecha
        date_col = 'Fecha y Hora' if 'Fecha y Hora' in df.columns else 'Fecha'
        if date_col in df.columns:
            df['Fecha'] = pd.to_datetime(df[date_col])

        # Cálculo de Ventas
        if 'Cantidad' in df.columns and 'Precio Unitario' in df.columns:
            df['Ventas'] = df['Cantidad'] * df['Precio Unitario']
        
        # Mapeo de Categorías
        product_map = {
            'Espresso': 'Cafetería', 'Capuchino': 'Cafetería', 'Café Latte': 'Cafetería',
            'Brownie': 'Pastelería', 'Croissant': 'Pastelería', 'Galleta': 'Pastelería',
            'Sandwich de Jamón y Queso': 'Salados', 'Jugo de Naranja': 'Bebidas Frías'
            }
        if 'Producto' in df.columns:
            df['Categoria'] = df['Producto'].map(product_map).fillna('Otros')
        return df
    except:
        return pd.DataFrame()

df = load_cloud_data(st.session_state["username"])

if not df.empty:
    st.title(f"📊 Métricas: {st.session_state['name']}")
    
    # Filtros y Gráficos (Tu lógica de visualización se mantiene aquí)
    st.metric("Ventas Totales", f"${df['Ventas'].sum():,.2f}")
    fig = px.line(df.groupby(df['Fecha'].dt.date)['Ventas'].sum().reset_index(), x='Fecha', y='Ventas')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aún no hay datos cargados para su negocio. Contacte al administrador.")