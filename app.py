import streamlit as st
from usuario import hash_password, login_user, add_user, get_all_usernames
from storage_supabase import upload_to_supabase

st.set_page_config(page_title="Bastion Data Analyst - Acceso", layout="centered")

if "user_authenticated" not in st.session_state:
    st.session_state["user_authenticated"] = False

if not st.session_state["user_authenticated"]:
    st.title("🔐 Bastion Login")
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            # Verificación contra Supabase
            resultado = login_user(usuario, hash_password(contraseña))
            if resultado:
                st.session_state["user_authenticated"] = True
                st.session_state["username"] = resultado['username']
                st.session_state["name"] = resultado['name']
                st.session_state["role"] = resultado['role']
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
else:
    name = st.session_state["name"]
    role = st.session_state["role"]

    st.sidebar.success(f"Conectado como: {name}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if role == "admin":
        st.title("🛡️ Panel de Control Maestro")
        t1, t2 = st.tabs(["📁 Cargar Datos", "👤 Gestionar Usuarios"])

        with t1:
            st.subheader("Subir Actualización (.csv)")
            clientes = get_all_usernames()
            if clientes:
                target = st.selectbox("Seleccione el Comercio:", clientes)
                archivo = st.file_uploader(f"Dataset para {target}", type=["csv"])
                if archivo and st.button("Actualizar en la Nube"):
                    if upload_to_supabase(archivo, f"{target}_ventas.csv"):
                        st.success("✅ Archivo actualizado correctamente.")
                        st.cache_data.clear()
            else:
                st.info("Primero cree un usuario tipo 'cliente'.")

        with t2:
            st.subheader("Nuevo Acceso")
            with st.form("registro"):
                u = st.text_input("ID de Usuario")
                p = st.text_input("Clave", type="password")
                n = st.text_input("Nombre del Negocio")
                r = st.selectbox("Tipo de Cuenta", ["cliente", "admin"])
                if st.form_submit_button("Registrar"):
                    if add_user(u, p, n, r):
                        st.success(f"Usuario {u} creado.")
                    else:
                        st.error("Error: El ID ya existe.")
    else:
        st.title(f"Bienvenid@, {name}")
        st.info("Use el menú lateral para navegar hacia su Dashboard de ventas.")