import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from database import (
    listar_utilizadores, criar_utilizador,
    atualizar_utilizador, deletar_utilizador,
)
from auth import esta_logado, is_admin, validar_password,

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin():
    st.error("Acesso restrito a administradores.")
    st.stop()

st.title("👥 Utilizadores")

ROLES = ["operador", "programador", "admin"]
ROLE_LABELS = {
    "operador": "👷 Operador",
    "programador": "👨‍💻 Programador",
    "admin": "👑 Administrador",
}

if "user_modo" not in st.session_state:
    st.session_state.user_modo = "listar"
if "user_edicao" not in st.session_state:
    st.session_state.user_edicao = None


# =========================================================
# LISTAR
# =========================================================
if st.session_state.user_modo == "listar":
    df = listar_utilizadores()

    df_exibir = df.copy()
    df_exibir["perfil"] = df_exibir["role"].map(ROLE_LABELS)

    st.dataframe(
        df_exibir[["id", "username", "perfil", "nome", "ativo"]],
        column_config={
            "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
            "username": st.column_config.TextColumn("Utilizador", width=140),
            "perfil": st.column_config.TextColumn("Perfil", width=160),
            "nome": st.column_config.TextColumn("Nome", width=220),
            "ativo": st.column_config.CheckboxColumn("Ativo", width=60),
        },
        hide_index=True,
        use_container_width=False,
    )

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Novo utilizador", use_container_width=True):
            st.session_state.user_modo = "criar"
            st.rerun()
    with c2:
        ids = df["id"].tolist()
        nomes = dict(zip(df["id"], df["username"]))
        sel = st.selectbox(
            "Editar / apagar",
            options=[None] + ids,
            format_func=lambda x: "— selecione —" if x is None else f"#{x} {nomes[x]}",
            key="sel_user",
        )
        if sel is not None:
            ca, cb = st.columns(2)
            with ca:
                if st.button("✏️ Editar", use_container_width=True):
                    st.session_state.user_modo = "editar"
                    st.session_state.user_edicao = sel
                    st.rerun()
            with cb:
                if st.button("🗑️ Apagar", type="primary", use_container_width=True):
                    if sel == st.session_state.user_id:
                        st.error("Não pode apagar o seu próprio utilizador.")
                    else:
                        deletar_utilizador(sel)
                        st.success("Utilizador apagado!")
                        st.session_state.pop("sel_user", None)
                        st.rerun()


# =========================================================
# CRIAR
# =========================================================
elif st.session_state.user_modo == "criar":
    st.subheader("➕ Novo utilizador")

    with st.form("form_user_criar", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Utilizador *")
            nome = st.text_input("Nome completo *")
        with c2:
            password = st.text_input("Senha *", type="password")
            role = st.selectbox(
                "Perfil",
                ROLES,
                format_func=lambda x: ROLE_LABELS[x],
            )

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

if salvar:
    if not username or not nome or not password:
        st.error("Preencha todos os campos obrigatórios.")
    else:
        erros_forca = validar_password(password)
        if erros_forca:
            for e in erros_forca:
                st.error(e)
        else:
            uid = criar_utilizador(username.strip(), password, role, nome.strip())
            if uid is None:
                st.error("Esse nome de utilizador já existe.")
            else:
                st.success(f"Utilizador #{uid} criado!")
                st.session_state.user_modo = "listar"
                st.rerun()
        if cancelar:
            st.session_state.user_modo = "listar"
            st.rerun()


# =========================================================
# EDITAR
# =========================================================
elif st.session_state.user_modo == "editar":
    df = listar_utilizadores()
    linha = df[df["id"] == st.session_state.user_edicao]

    if linha.empty:
        st.error("Utilizador não encontrado.")
        st.session_state.user_modo = "listar"
        st.rerun()

    user = linha.iloc[0]
    st.subheader(f"✏️ Editar utilizador #{user['id']} — {user['username']}")

    with st.form("form_user_editar"):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Utilizador *", value=user["username"])
            nome = st.text_input("Nome completo *", value=user["nome"])
        with c2:
            nova_pass = st.text_input(
                "Nova senha (deixe vazio para manter)",
                type="password",
            )
            role_atual = user["role"] if user["role"] in ROLES else "operador"
            role = st.selectbox(
                "Perfil",
                ROLES,
                index=ROLES.index(role_atual),
                format_func=lambda x: ROLE_LABELS[x],
            )
        ativo = st.checkbox("Ativo", value=bool(user["ativo"]))

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            if not username or not nome:
                st.error("Preencha os campos obrigatórios.")
            elif user["id"] == st.session_state.user_id and not ativo:
                st.error("Não pode desativar o seu próprio utilizador.")
            elif user["id"] == st.session_state.user_id and role != "admin":
                st.error("Não pode remover o seu próprio perfil de administrador.")
            else:
                atualizar_utilizador(
                    user["id"], username.strip(), role, nome.strip(),
                    ativo, nova_pass if nova_pass else None,
                )
                st.success("Utilizador atualizado!")
                st.session_state.user_modo = "listar"
                st.session_state.user_edicao = None
                st.rerun()
        if cancelar:
            st.session_state.user_modo = "listar"
            st.session_state.user_edicao = None
            st.rerun()