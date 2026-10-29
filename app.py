"""
Registo de Peças — ponto de entrada.
"""
import streamlit as st
import requests
from pathlib import Path
from streamlit_cookies_controller import CookieController
from auth import (
    esta_logado, pagina_login, fazer_logout,
    is_admin, is_operador, is_programador,
    utilizador_ainda_ativo,
    tentar_login_automatico,
    apagar_cookies_login,
    ler_cookie,
    guardar_cookie,
)

# =========================================================
# LICENÇA REMOTA
# =========================================================
LICENSE_KEY = "SIMOLDES-001"
LICENSE_SHEET_ID = "1KGEhHySXCqLNBBnepNzXSF4k5XKH7bXpdp6Y2jE83Z0"
LICENSE_URL = f"https://docs.google.com/spreadsheets/d/{LICENSE_SHEET_ID}/gviz/tq?tqx=out:csv"


@st.cache_data(ttl=3600)
def verificar_licenca():
    try:
        r = requests.get(LICENSE_URL, timeout=10)
        r.raise_for_status()
        linhas = r.text.strip().split("\n")
        for linha in linhas[1:]:
            if not linha.strip():
                continue
            partes = [p.strip().strip('"') for p in linha.split(",")]
            if len(partes) >= 3 and partes[0] == LICENSE_KEY:
                return partes[2].upper() == "TRUE"
        return False
    except Exception:
        return False


if not verificar_licenca():
    st.error("⛔ Licença inválida ou revogada. Contacte o fornecedor.")
    st.stop()

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="Registo de Peças",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# CONTROLLER DE COOKIES
# =========================================================
cookie_manager = CookieController()

# Esperar que o controller carregue
if "cookies_loaded" not in st.session_state:
    st.session_state.cookies_loaded = False

if not st.session_state.cookies_loaded:
    try:
        cookie_manager.get("teste_inicial")
        st.session_state.cookies_loaded = True
    except (TypeError, AttributeError):
        st.rerun()

# =========================================================
# BANNER RGPD
# =========================================================
aceitou_sessao = st.session_state.get("cookies_aceites_sessao", False)
cookie_aceite = ler_cookie(cookie_manager, "registo_cookies_aceites")

if not aceitou_sessao and not cookie_aceite:
    st.warning(
        "🍪 **Este site usa cookies essenciais** para guardar o seu login.\n\n"
        "Ao continuar, aceita a utilização de cookies."
    )

    col_aceitar, col_recusar = st.columns(2)

    with col_aceitar:
        if st.button("✅ Aceitar cookies", use_container_width=True, key="btn_aceitar_cookies"):
            st.session_state.cookies_aceites_sessao = True
            guardar_cookie(cookie_manager, "registo_cookies_aceites", "sim", 365)
            st.rerun()

    with col_recusar:
        if st.button("❌ Recusar", use_container_width=True, key="btn_recusar_cookies"):
            st.error("Sem cookies não pode usar a app. Contacte o administrador.")
            st.stop()

    st.stop()

# =========================================================
# LOGIN
# =========================================================
if not esta_logado():
    if not tentar_login_automatico(cookie_manager):
        pagina_login(cookie_manager)
        st.stop()

if not utilizador_ainda_ativo():
    st.error("A sua conta foi desativada. Contacte o administrador.")
    fazer_logout()
    apagar_cookies_login(cookie_manager)
    st.stop()

# =========================================================
# NAVEGAÇÃO POR ROLE
# =========================================================
if is_admin():
    paginas = [
        st.Page("pages/home.py", title="🏠 Início", default=True),
        st.Page("pages/9_Vista_Global.py", title="🌐 Vista global"),
        st.Page("pages/6_Ordens.py", title="📋 Ordens de produção"),
        st.Page("pages/7_Criar_Registo.py", title="🏭 Criar registo"),
        st.Page("pages/8_Previsoes.py", title="📊 Previsões vs reais"),
        st.Page("pages/2_Operadores.py", title="👥 Utilizadores"),
        st.Page("pages/3_Configuracoes.py", title="🔧 Máquinas"),
        st.Page("pages/5_Estados.py", title="🚦 Estados"),
        st.Page("pages/10_Minha_Conta.py", title="👤 Minha conta"),
    ]
elif is_programador():
    paginas = [
        st.Page("pages/home.py", title="🏠 Início", default=True),
        st.Page("pages/6_Ordens.py", title="📋 Ordens de produção"),
        st.Page("pages/8_Previsoes.py", title="📊 Previsões vs reais"),
        st.Page("pages/10_Minha_Conta.py", title="👤 Minha conta"),
    ]
elif is_operador():
    paginas = [
        st.Page("pages/home.py", title="🏠 Início", default=True),
        st.Page("pages/7_Criar_Registo.py", title="🏭 Criar registo"),
        st.Page("pages/4_Consultar_Registos.py", title="📋 Consultar registos"),
        st.Page("pages/10_Minha_Conta.py", title="👤 Minha conta"),
    ]
else:
    paginas = [st.Page("pages/home.py", title="🏠 Início", default=True)]

pg = st.navigation(paginas, position="hidden")

# =========================================================
# SIDEBAR
# =========================================================
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=200)
        st.divider()

    st.markdown(f"### 👤 {st.session_state.user_nome}")
    st.caption(f"@{st.session_state.username} · {st.session_state.role}")
    st.divider()

    for p in paginas:
        st.page_link(p, label=p.title)

    st.divider()

    if st.button("🚪 Sair", use_container_width=True, key="app_btn_sair"):
        apagar_cookies_login(cookie_manager)
        fazer_logout()
        st.rerun()

# =========================================================
# CONTEÚDO
# =========================================================
pg.run()