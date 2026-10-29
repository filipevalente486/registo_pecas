"""
Autenticação: login, logout, verificação de permissões.
"""
import bcrypt
import streamlit as st
from database import buscar_utilizador_por_username, init_db


def verificar_login(username, password):
    user = buscar_utilizador_por_username(username)
    if user is None:
        return None
    if not bool(user["ativo"]):
        return None
    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user
    return None


def fazer_login(user):
    st.session_state.user_id   = int(user["id"])
    st.session_state.username  = user["username"]
    st.session_state.user_nome = user["nome"]
    st.session_state.role      = user["role"]


def fazer_logout():
    for k in ["user_id", "username", "user_nome", "role"]:
        st.session_state.pop(k, None)


def esta_logado():
    return "user_id" in st.session_state


def is_admin():
    return st.session_state.get("role") == "admin"


def is_operador():
    return st.session_state.get("role") == "operador"


def is_programador():
    return st.session_state.get("role") == "programador"


def is_admin_or_operador():
    return st.session_state.get("role") in ("admin", "operador")


def is_admin_or_programador():
    return st.session_state.get("role") in ("admin", "programador")


def utilizador_ainda_ativo():
    if "user_id" not in st.session_state:
        return False
    user = buscar_utilizador_por_username(st.session_state.username)
    return user is not None and bool(user["ativo"])


def validar_password(password):
    erros = []
    if len(password) < 8:
        erros.append("A password deve ter pelo menos **8 caracteres**.")
    if not any(c.isupper() for c in password):
        erros.append("A password deve ter pelo menos **1 letra maiúscula** (A-Z).")
    if not any(c.islower() for c in password):
        erros.append("A password deve ter pelo menos **1 letra minúscula** (a-z).")
    if not any(c.isdigit() for c in password):
        erros.append("A password deve ter pelo menos **1 número** (0-9).")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        erros.append("A password deve ter pelo menos **1 caractere especial** (!@#$%&*...).")
    return erros


def verificar_password_atual(user_id, password):
    from database import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM utilizadores WHERE id = ?",
            (int(user_id),)
        ).fetchone()
    if not row:
        return False
    return bcrypt.checkpw(password.encode(), row[0].encode())


# =========================================================
# COOKIES
# =========================================================
def ler_cookie(controller, nome):
    """Lê um cookie. Devolve None se não existir."""
    try:
        return controller.get(nome)
    except (TypeError, KeyError, AttributeError):
        return None


def guardar_cookie(controller, nome, valor, dias=365):
    """Guarda um cookie por X dias."""
    try:
        controller.set(nome, valor, max_age=dias*24*60*60)
        return True
    except (TypeError, AttributeError):
        return False


def apagar_cookie(controller, nome):
    """Remove um cookie."""
    try:
        if controller.get(nome) is not None:
            controller.remove(nome)
    except (TypeError, KeyError, AttributeError):
        pass


def guardar_cookie_login(controller, user_id, username, dias=30):
    """Guarda o login em cookie."""
    guardar_cookie(controller, "registo_user_id", str(user_id), dias)
    guardar_cookie(controller, "registo_username", username, dias)


def apagar_cookies_login(controller):
    """Remove os cookies de login (mantém o de aceitar cookies)."""
    apagar_cookie(controller, "registo_user_id")
    apagar_cookie(controller, "registo_username")


def tentar_login_automatico(controller):
    """Tenta fazer login automático a partir do cookie."""
    user_id = ler_cookie(controller, "registo_user_id")
    username = ler_cookie(controller, "registo_username")

    if not user_id or not username:
        return False

    user = buscar_utilizador_por_username(username)
    if user is None or not bool(user["ativo"]):
        apagar_cookies_login(controller)
        return False

    fazer_login(user)
    return True


# =========================================================
# LOGIN PAGE
# =========================================================
def pagina_login(controller=None):
    init_db()

    st.markdown(
        """
        <div style="text-align:center;margin-top:60px">
            <h1>📋 Registo de Peças</h1>
            <p style="color:gray">Registo diário de peças por máquina</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Utilizador")
            password = st.text_input("Senha", type="password")
            lembrar = st.checkbox("Lembrar-me por 30 dias", value=False)
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                user = verificar_login(username.strip(), password)
                if user is not None:
                    fazer_login(user)

                    if lembrar and controller is not None:
                        guardar_cookie_login(controller, user["id"], user["username"])

                    st.rerun()
                else:
                    st.error("Credenciais inválidas ou utilizador inativo.")