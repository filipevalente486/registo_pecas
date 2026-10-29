import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from database import (
    listar_estados, criar_estado,
    atualizar_estado, deletar_estado,
)
from auth import esta_logado, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin():
    st.error("Acesso restrito a administradores.")
    st.stop()

st.title("🚦 Estados de Máquina")

st.caption(
    "Estados indicam o motivo de uma máquina estar **ativa** (P00) "
    "ou **inativa** (outros códigos). O P00 é automático e não pode ser apagado."
)

if "est_modo" not in st.session_state:
    st.session_state.est_modo = "listar"
if "est_edicao" not in st.session_state:
    st.session_state.est_edicao = None


# ---------- LISTAR ----------
if st.session_state.est_modo == "listar":
    df = listar_estados()

    # Formatar para exibir
    df_exibir = df.copy()
    df_exibir["tipo"] = df_exibir["sistema"].map({1: "🔒 Sistema", 0: "✏️ Personalizado"})

    st.dataframe(
        df_exibir[["id", "codigo", "descricao", "tipo"]],
        column_config={
            "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
            "codigo": st.column_config.TextColumn("Código", width=90),
            "descricao": st.column_config.TextColumn("Descrição", width=300),
            "tipo": st.column_config.TextColumn("Tipo", width=140),
        },
        hide_index=True,
        use_container_width=False,
    )

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Novo estado", use_container_width=True):
            st.session_state.est_modo = "criar"
            st.rerun()
    with c2:
        # Só permite editar/apagar estados personalizados (sistema = 0)
        df_personalizados = df[df["sistema"] == 0]

        if df_personalizados.empty:
            st.info("Sem estados personalizados para editar.")
        else:
            ids = df_personalizados["id"].tolist()
            labels = dict(zip(
                df_personalizados["id"],
                df_personalizados["codigo"] + " — " + df_personalizados["descricao"]
            ))
            sel = st.selectbox(
                "Editar / apagar",
                options=[None] + ids,
                format_func=lambda x: "— selecione —" if x is None else labels[x],
                key="sel_estado",
            )
            if sel is not None:
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state.est_modo = "editar"
                        st.session_state.est_edicao = sel
                        st.rerun()
                with cb:
                    if st.button("🗑️ Apagar", type="primary", use_container_width=True):
                        deletar_estado(sel)
                        st.success("Estado apagado!")
                        st.session_state.pop("sel_estado", None)
                        st.rerun()


# ---------- CRIAR ----------
elif st.session_state.est_modo == "criar":
    st.subheader("➕ Novo estado")

    with st.form("form_estado_criar", clear_on_submit=True):
        codigo = st.text_input(
            "Código *",
            placeholder="Ex.: P06",
            max_chars=10,
        ).strip().upper()
        descricao = st.text_input(
            "Descrição *",
            placeholder="Ex.: Avaria pneumática",
        ).strip()

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            if not codigo or not descricao:
                st.error("Código e descrição são obrigatórios.")
            elif codigo == "P00":
                st.error("O código P00 é reservado ao sistema.")
            else:
                eid = criar_estado(codigo, descricao)
                if eid is None:
                    st.error("Esse código já existe.")
                else:
                    st.success(f"Estado {codigo} criado!")
                    st.session_state.est_modo = "listar"
                    st.rerun()

        if cancelar:
            st.session_state.est_modo = "listar"
            st.rerun()


# ---------- EDITAR ----------
elif st.session_state.est_modo == "editar":
    df = listar_estados()
    linha = df[df["id"] == st.session_state.est_edicao]

    if linha.empty:
        st.error("Estado não encontrado.")
        st.session_state.est_modo = "listar"
        st.rerun()

    est = linha.iloc[0]
    st.subheader(f"✏️ Editar estado {est['codigo']}")

    st.info("O código não pode ser alterado. Só a descrição pode ser editada.")

    with st.form("form_estado_editar"):
        st.text_input("Código", value=est["codigo"], disabled=True)
        descricao = st.text_input("Descrição *", value=est["descricao"])

        ca, cb = st.columns([1, 5])
        with ca:
            salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        with cb:
            cancelar = st.form_submit_button("❌ Cancelar")

        if salvar:
            if not descricao.strip():
                st.error("Descrição é obrigatória.")
            else:
                atualizar_estado(est["id"], descricao.strip())
                st.success("Estado atualizado!")
                st.session_state.est_modo = "listar"
                st.session_state.est_edicao = None
                st.rerun()

        if cancelar:
            st.session_state.est_modo = "listar"
            st.session_state.est_edicao = None
            st.rerun()