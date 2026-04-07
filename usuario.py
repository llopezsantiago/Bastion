import streamlit as st
from supabase import create_client, Client
import hashlib

def get_supabase():
    """Conexión principal a la base de datos de Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def hash_password(password):
    """Encripta la contraseña usando SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def login_user(username, password):
    """Verifica credenciales en la tabla 'userstable' de Supabase."""
    supabase = get_supabase()
    try:
        # Busca el usuario que coincida con nombre y hash de contraseña
        response = supabase.table("userstable").select("*").eq("username", username).eq("password", password).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error de autenticación: {e}")
        return None

def add_user(username, password, name, role="cliente"):
    """Crea un nuevo usuario en la base de datos remota."""
    supabase = get_supabase()
    data = {
        "username": username,
        "password": hash_password(password),
        "name": name,
        "role": role
    }
    try:
        supabase.table("userstable").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")
        return False

def get_all_usernames():
    """Obtiene la lista de clientes para el selector del Administrador."""
    supabase = get_supabase()
    try:
        response = supabase.table("userstable").select("username").eq("role", "cliente").execute()
        return [row['username'] for row in response.data]
    except Exception:
        return []

def inicializacion_db():
    """No requiere lógica local ya que la tabla se crea en el panel de Supabase."""
    pass