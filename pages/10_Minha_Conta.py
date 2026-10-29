import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from database import alterar_password
from auth import esta_logado, verificar_password_atual, validar_password

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

st.title("👤 Minha Conta")

# ---------- Informação ----------
st.subheader("Informação")
col1, col2 = st.columns(2)
col1.markdown(f"**Utilizador:** `{st.session_state.username}`")
col2.markdown(f"**Perfil:** `{st.session_state.role}`")
st.markdown(f"**Nome:** {st.session_state.user_nome}")

st.divider()

# ---------- Alterar password ----------
st.subheader("🔐 Alterar password")

st.markdown(
    """
    **Regras da password:**
    - ✅ Mínimo **8 caracteres**
    - ✅ Pelo menos **1 letra maiúscula** (A-Z)
    - ✅ Pelo menos **1 letra minúscula** (a-z)
    - ✅ Pelo menos **1 número** (0-9)
    - ✅ Pelo menos **1 caractere especial** (!@#$%&*...)
    """
)

with st.form("form_alterar_password", clear_on_submit=True):
    password_atual = st.text_input("Password atual *", type="password")
    nova_password = st.text_input("Nova password *", type="password")
    confirmar_password = st.text_input("Confirmar nova password *", type="password")

    if st.form_submit_button("💾 Alterar password", use_container_width=True):
        erros = []

        # Validação básica
        if not password_atual or not nova_password or not confirmar_password:
            erros.append("Preencha todos os campos.")
        elif not verificar_password_atual(st.session_state.user_id, password_atual):
            erros.append("Password atual incorreta.")
        elif nova_password != confirmar_password:
            erros.append("As passwords novas não coincidem.")
        elif nova_password == password_atual:
            erros.append("A nova password deve ser diferente da atual.")
        else:
            # Validação de força
            erros_forca = validar_password(nova_password)
            erros.extend(erros_forca)

        if erros:
            for e in erros:
                st.error(e)
        else:
            alterar_password(st.session_state.user_id, nova_password)
            st.success("✅ Password alterada com sucesso! Use a nova nos próximos logins.")