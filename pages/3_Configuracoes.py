"""
Gestão de máquinas (apenas admin).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from database import (
    listar_maquinas, criar_maquina,
    atualizar_maquina, deletar_maquina,
)
from auth import esta_logado, is_admin
# ... (o resto continua igual)

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin():
    st.error("Acesso restrito a administradores.")
    st.stop()

st.title("🔧 Máquinas")

if "maq_modo" not in st.session_state:
    st.session_state.maq_modo = "listar"
if "maq_edicao" not in st.session_state:
    st.session_state.maq_edicao = None


# =========================================================
# LISTAR
# =========================================================
if st.session_state.maq_modo == "listar":
    df = listar_maquinas()

    # Selecionar só as colunas relevantes
    df_exibir = df[["id", "nome", "codigo", "ativa", "estado_codigo", "estado_descricao"]].copy()
    df_exibir["estado"] = df_exibir.apply(
        lambda r: f"🔴 {r['estado_codigo']} — {r['estado_descricao']}"
        if pd.notna(r["estado_codigo"])
        else "🟢 Ativa",
        axis=1
    )

    st.dataframe(
        df_exibir[["id", "nome", "codigo", "ativa", "estado"]],
        column_config={
            "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
            "nome": st.column_config.TextColumn("Nome", width=220),
            "codigo": st.column_config.TextColumn("Código", width=140),
            "ativa": st.column_config.CheckboxColumn("Ativa", width=60),
            "estado": st.column_config.TextColumn("Estado atual", width=260),
        },
        hide_index=True,
        use_container_width=False,
    )

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Nova máquina", use_container_width=True):
            st.session_state.maq_modo = "criar"
            st.rerun()
    with c2:
        ids = df["id"].tolist()
        nomes = dict(zip(df["id"], df["nome"]))
        sel = st.selectbox(
            "Editar / apagar",
            options=[None] + ids,
            format_func=lambda x: "— selecione —" if x is None else f"#{x} {nomes[x]}",
            key="sel_maq",
        )
        if sel is not None:
            ca, cb = st.columns(2)
            with ca:
                if st.button("✏️ Editar", use_container_width=True):
                    st.session_state.maq_modo = "editar"
                    st.session_state.maq_edicao = sel
                    st.rerun()
            with cb:
                if st.button("🗑️ Apagar", type="primary", use_container_width=True):
                    deletar_maquina(sel)
                    st.success("Máquina apagada!")
                    st.session_state.pop("sel_maq", None)
                    st.rerun()


# =========================================================
# CRIAR
# =========================================================
elif st.session_state.maq_modo == "criar":
    st.subheader("➕ Nova máquina")

    with st.form("form_maq_criar", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome *", placeholder="Ex.: CNC 5")
        with c2:
            codigo = st.text_input("Código", placeholder="Ex.: CNC05")

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            if not nome.strip():
                st.error("Nome é obrigatório.")
            else:
                mid = criar_maquina(nome.strip(), codigo.strip())
                st.success(f"Máquina #{mid} criada!")
                st.session_state.maq_modo = "listar"
                st.rerun()
        if cancelar:
            st.session_state.maq_modo = "listar"
            st.rerun()


# =========================================================
# EDITAR
# =========================================================
elif st.session_state.maq_modo == "editar":
    df = listar_maquinas()
    linha = df[df["id"] == st.session_state.maq_edicao]

    if linha.empty:
        st.error("Máquina não encontrada.")
        st.session_state.maq_modo = "listar"
        st.rerun()

    m = linha.iloc[0]
    st.subheader(f"✏️ Editar máquina #{m['id']}")

    with st.form("form_maq_editar"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome *", value=m["nome"])
        with c2:
            codigo = st.text_input("Código", value=m["codigo"] or "")
        ativa = st.checkbox("Ativa", value=bool(m["ativa"]))

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            if not nome.strip():
                st.error("Nome é obrigatório.")
            else:
                atualizar_maquina(m["id"], nome.strip(), codigo.strip(), ativa)
                st.success("Máquina atualizada!")
                st.session_state.maq_modo = "listar"
                st.session_state.maq_edicao = None
                st.rerun()
        if cancelar:
            st.session_state.maq_modo = "listar"
            st.session_state.maq_edicao = None
            st.rerun()