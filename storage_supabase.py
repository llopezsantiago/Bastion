import streamlit as st
from supabase import create_client, Client

def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def upload_to_supabase(file, filename):
    """Sube o sobrescribe el archivo en el bucket 'datasets'."""
    supabase = get_supabase_client()
    try:
        bucket_name = "datasets"
        file.seek(0)
        content = file.read()
        
        # 'upsert': true permite que el admin actualice el archivo cuantas veces quiera
        supabase.storage.from_(bucket_name).upload(
            path=filename, 
            file=content,
            file_options={"upsert": "true"}
        )
        return True
    except Exception as e:
        st.error(f"Error al subir archivo a Supabase: {e}")
        return False