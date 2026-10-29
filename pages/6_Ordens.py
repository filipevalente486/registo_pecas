import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from database import (
    listar_ordens, criar_ordem,
    cancelar_ordem, atualizar_tempo_previsto, formatar_duracao,
)
from auth import esta_logado, is_admin_or_programador, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin_or_programador():
    st.error("Acesso restrito a programadores e administradores.")
    st.stop()

st.title("📋 Ordens de Produção")
st.caption("O programador define a peça e o tempo previsto. A máquina é escolhida pelo operador ao executar.")

# ---------- Criar nova ordem ----------
with st.expander("➕ Nova ordem", expanded=True):
    with st.form("form_nova_ordem", clear_on_submit=True):
        nome_peca = st.text_input("Nome da peça *", placeholder="Ex.: 4580-100")

        st.markdown("**Tempo previsto**")
        c1, c2 = st.columns(2)
        with c1:
            h_prev = st.number_input("Horas", min_value=0, max_value=1000, value=0, step=1)
        with c2:
            m_prev = st.number_input("Minutos", min_value=0, max_value=59, value=0, step=5)

        motivo = st.text_input("Observações (opcional)")

        if st.form_submit_button("💾 Criar ordem", use_container_width=True):
            tempo_min = int(h_prev) * 60 + int(m_prev)
            if not nome_peca.strip():
                st.error("Nome da peça é obrigatório.")
            elif tempo_min == 0:
                st.error("Indique um tempo previsto superior a 0.")
            else:
                criar_ordem(
                    nome_peca=nome_peca.strip(),
                    tempo_previsto_min=tempo_min,
                    programador_id=st.session_state.user_id,
                    motivo=motivo.strip() or None,
                )
                st.success("Ordem criada!")
                st.rerun()

# ---------- Listar ----------
st.divider()
st.subheader("📋 Ordens existentes")

filtro_estado = st.selectbox(
    "Filtrar por estado",
    ["Todas", "pendente", "em_curso", "concluida", "cancelada"],
)

estado_filtro = None if filtro_estado == "Todas" else filtro_estado

# Admin vê todas; programador vê só as suas
filtro_prog = None if is_admin() else st.session_state.user_id
df = listar_ordens(estado=estado_filtro, programador_id=filtro_prog)

if df.empty:
    st.info("Sem ordens para os critérios selecionados.")
else:
    df_exibir = df.copy()
    df_exibir["tempo_previsto"] = df_exibir["tempo_previsto_min"].apply(formatar_duracao)
    df_exibir["estado_label"] = df_exibir["estado"].map({
        "pendente": "⏳ Pendente",
        "em_curso": "▶️ Em curso",
        "concluida": "✅ Concluída",
        "cancelada": "❌ Cancelada",
    })

    st.dataframe(
        df_exibir[[
            "id", "nome_peca", "tempo_previsto", "estado_label",
            "maquina_real_codigo", "programador_nome", "operador_nome",
            "inicio_real", "fim_real",
        ]],
        column_config={
            "id": st.column_config.NumberColumn("ID", width=50),
            "nome_peca": st.column_config.TextColumn("Peça", width=180),
            "tempo_previsto": st.column_config.TextColumn("Previsto", width=100),
            "estado_label": st.column_config.TextColumn("Estado", width=130),
            "maquina_real_codigo": st.column_config.TextColumn("Máquina", width=90),
            "programador_nome": st.column_config.TextColumn("Programador", width=140),
            "operador_nome": st.column_config.TextColumn("Operador", width=140),
            "inicio_real": st.column_config.DatetimeColumn(
                "Início", format="DD/MM/YYYY HH:mm", width=150
            ),
            "fim_real": st.column_config.DatetimeColumn(
                "Fim", format="DD/MM/YYYY HH:mm", width=150
            ),
        },
        hide_index=True,
        use_container_width=False,
    )

    st.divider()
    st.subheader("⚙️ Ações")

    ids = df["id"].tolist()
    labels = dict(zip(df["id"], df["nome_peca"] + " · " + df["estado"]))
    sel = st.selectbox(
        "Selecione uma ordem",
        options=ids,
        format_func=lambda x: f"#{x} — {labels[x]}",
        key="sel_ordem",
    )

    linha = df[df["id"] == sel].iloc[0]

    if linha["estado"] == "pendente":
        c1, c2 = st.columns(2)

        with c1:
            with st.form("form_edit_previsto"):
                st.markdown("**✏️ Alterar tempo previsto**")
                h_e = st.number_input(
                    "Horas", min_value=0, max_value=1000,
                    value=int(linha["tempo_previsto_min"]) // 60,
                    key="edit_h",
                )
                m_e = st.number_input(
                    "Minutos", min_value=0, max_value=59,
                    value=int(linha["tempo_previsto_min"]) % 60, step=5,
                    key="edit_m",
                )
                if st.form_submit_button("💾 Atualizar"):
                    tempo_e = int(h_e) * 60 + int(m_e)
                    if tempo_e > 0:
                        atualizar_tempo_previsto(sel, tempo_e)
                        st.success("Tempo atualizado!")
                        st.rerun()

        with c2:
            st.markdown("**🗑️ Cancelar ordem**")
            if st.button("❌ Cancelar ordem", type="primary", key="btn_cancelar_ordem"):
                cancelar_ordem(sel)
                st.success("Ordem cancelada.")
                st.rerun()
    else:
        st.info(f"Esta ordem já está **{linha['estado']}**. Não pode ser alterada.")