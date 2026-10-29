import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from datetime import date, time, datetime
from database import (
    listar_maquinas, listar_ordens, listar_registos, listar_estados,
    criar_registo, criar_inatividade, registar_e_concluir_ordem,
    atualizar_registo, deletar_registo, formatar_duracao,
)
from auth import esta_logado, is_admin_or_operador, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin_or_operador():
    st.error("Acesso restrito a operadores e administradores.")
    st.stop()

st.title("🏭 Criar Registo")

maquinas = listar_maquinas(só_ativas=False)
if maquinas.empty:
    st.warning("Nenhuma máquina ativa.")
    st.stop()

maq_opcoes = {
    row["id"]: (row["codigo"] if row["codigo"] else row["nome"])
    for _, row in maquinas.iterrows()
}

# =========================================================
# FORMULÁRIO ÚNICO
# =========================================================
st.subheader("➕ Novo registo")

TIPO_MANUAL = "📝 Trabalho manual"
TIPO_ORDEM = "📋 Ordem pendente"
TIPO_INAT = "🚧 Inatividade"

tipo = st.radio(
    "Tipo de registo",
    [TIPO_MANUAL, TIPO_ORDEM, TIPO_INAT],
    horizontal=True,
    key="tipo_registo",
)

with st.form("form_registo", clear_on_submit=True):
    if tipo == TIPO_MANUAL:
        nome_peca = st.text_input("Nome da peça *", placeholder="Ex.: Eixo motor")
        ordem_id = None
        estado_id = None

    elif tipo == TIPO_ORDEM:
        pendentes = listar_ordens(estado="pendente")
        if pendentes.empty:
            st.warning("Sem ordens pendentes.")
            st.stop()

        pendentes = pendentes.copy()
        pendentes["tempo_previsto"] = pendentes["tempo_previsto_min"].apply(formatar_duracao)
        ordem_opcoes = {
            row["id"]: f"#{row['id']} — {row['nome_peca']} (previsto: {row['tempo_previsto']})"
            for _, row in pendentes.iterrows()
        }
        ordem_id = st.selectbox(
            "Ordem *",
            options=list(ordem_opcoes.keys()),
            format_func=lambda x: ordem_opcoes[x],
            key="sel_ordem",
        )
        ordem_info = pendentes[pendentes["id"] == ordem_id].iloc[0]
        st.text_input(
            "Peça (definida pelo programador)",
            value=ordem_info["nome_peca"],
            disabled=True,
        )
        st.caption(
            f"Programador: **{ordem_info['programador_nome']}** · "
            f"Previsto: **{ordem_info['tempo_previsto']}**"
        )
        nome_peca = ordem_info["nome_peca"]
        estado_id = None

    else:  # TIPO_INAT
        estados = listar_estados()
        est_inativos = estados[estados["codigo"] != "P00"]
        if est_inativos.empty:
            st.warning("Sem estados de inatividade. Peça ao admin.")
            st.stop()

        est_opcoes = {
            row["id"]: f"{row['codigo']} — {row['descricao']}"
            for _, row in est_inativos.iterrows()
        }
        estado_id = st.selectbox(
            "Motivo *",
            options=list(est_opcoes.keys()),
            format_func=lambda x: est_opcoes[x],
            key="sel_estado",
        )
        nome_peca = None
        ordem_id = None

    maquina_id = st.selectbox(
        "Máquina *",
        options=list(maq_opcoes.keys()),
        format_func=lambda x: maq_opcoes[x],
        key="maq_sel",
    )

    st.markdown("**Início**")
    c1, c2 = st.columns(2)
    with c1:
        di = st.date_input("Data início", value=date.today(), format="DD/MM/YYYY", key="di")
    with c2:
        hi = st.time_input("Hora início", value=time(8, 0), step=60, key="hi")

    st.markdown("**Fim**")
    c3, c4 = st.columns(2)
    with c3:
        df = st.date_input("Data fim", value=date.today(), format="DD/MM/YYYY", key="df")
    with c4:
        hf = st.time_input("Hora fim", value=time(9, 0), step=60, key="hf")

    fim_aberto = st.checkbox(
        "Deixar em aberto (sem fim definido)",
        value=False,
        key="fim_aberto",
    )

    motivo = st.text_input("Observações (opcional)", key="motivo")

    if st.form_submit_button("💾 Registar", use_container_width=True):
        dt_ini = datetime.combine(di, hi)
        dt_fim = None if fim_aberto else datetime.combine(df, hf)

        erros = []
        if dt_fim and dt_fim <= dt_ini:
            erros.append("O fim tem de ser depois do início.")
        if tipo == TIPO_MANUAL and not nome_peca.strip():
            erros.append("Nome da peça é obrigatório.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            if tipo == TIPO_MANUAL:
                criar_registo(
                    maquina_id=maquina_id,
                    nome_peca=nome_peca.strip(),
                    inicio=dt_ini,
                    conclusao=dt_fim,
                    user_id=st.session_state.user_id,
                    motivo=motivo.strip() or None,
                )
                st.success(f"✅ '{nome_peca}' registada!")

            elif tipo == TIPO_ORDEM:
                reg_id = registar_e_concluir_ordem(
                    ordem_id=ordem_id,
                    maquina_id=maquina_id,
                    inicio=dt_ini,
                    fim=dt_fim if dt_fim else dt_ini,
                    user_id=st.session_state.user_id,
                    motivo=motivo.strip() or None,
                )
                if reg_id:
                    st.success(f"✅ Ordem #{ordem_id} concluída! Registo #{reg_id} criado.")
                else:
                    st.error("Erro ao concluir a ordem.")
                    st.stop()

            else:  # TIPO_INAT
                criar_inatividade(
                    maquina_id=maquina_id,
                    estado_id=estado_id,
                    inicio=dt_ini,
                    fim=dt_fim,
                    motivo=motivo.strip() or None,
                    user_id=st.session_state.user_id,
                )
                st.success("✅ Inatividade registada!")

            st.rerun()

# =========================================================
# TABELA DE REGISTOS + AÇÕES
# =========================================================
st.divider()
st.subheader("📋 Registos desta máquina")

maq_view = st.selectbox(
    "Ver registos da máquina",
    options=list(maq_opcoes.keys()),
    format_func=lambda x: maq_opcoes[x],
    key="view_maq",
)

df_regs = listar_registos(maq_view)

if df_regs.empty:
    st.info("Ainda não há registos nesta máquina.")
    st.stop()

# Calcular duração
df_regs["inicio"] = pd.to_datetime(df_regs["inicio"])
df_regs["conclusao"] = pd.to_datetime(df_regs["conclusao"])
df_regs["duracao_min"] = (df_regs["conclusao"] - df_regs["inicio"]).dt.total_seconds() / 60

# Métricas (protegidas contra NaN)
tempo_total = df_regs["duracao_min"].sum() / 60
tempo_medio = df_regs["duracao_min"].mean() / 60

c1, c2, c3 = st.columns(3)
c1.metric("Total", len(df_regs))
c2.metric("Tempo total", f"{tempo_total:.1f} h" if pd.notna(tempo_total) else "—")
c3.metric("Tempo médio", f"{tempo_medio:.1f} h" if pd.notna(tempo_medio) else "—")

# Exibir tabela
df_exibir = df_regs.copy()
df_exibir["duracao"] = df_exibir["duracao_min"].apply(formatar_duracao)
df_exibir["origem"] = df_exibir.apply(
    lambda r: f"📋 Ordem #{int(r['ordem_id'])}" if pd.notna(r.get("ordem_id")) else "📝 Manual",
    axis=1,
)

st.dataframe(
    df_exibir[["id", "origem", "nome_peca", "inicio", "conclusao", "duracao", "user_nome", "motivo"]],
    column_config={
        "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
        "origem": st.column_config.TextColumn("Origem", width=130),
        "nome_peca": st.column_config.TextColumn("Peça", width=180),
        "inicio": st.column_config.DatetimeColumn("Início", format="DD/MM/YYYY HH:mm", width=150),
        "conclusao": st.column_config.DatetimeColumn("Fim", format="DD/MM/YYYY HH:mm", width=150),
        "duracao": st.column_config.TextColumn("Duração", width=110),
        "user_nome": st.column_config.TextColumn("Operador", width=140),
        "motivo": st.column_config.TextColumn("Obs:", width=200),
    },
    hide_index=True,
    use_container_width=False,
)

# =========================================================
# AÇÕES — EDITAR / APAGAR
# =========================================================
st.divider()
st.subheader("⚙️ Ações sobre um registo")

ids = df_regs["id"].tolist()
labels = dict(zip(
    df_regs["id"],
    df_regs["nome_peca"] + " (" + df_regs["inicio"].dt.strftime("%d/%m %H:%M") + ")",
))

reg_id = st.selectbox(
    "Selecione um registo",
    options=ids,
    format_func=lambda x: f"#{x} — {labels[x]}",
    key="sel_registo",
)

linha = df_regs[df_regs["id"] == reg_id].iloc[0]
pode_alterar = is_admin() or linha["user_id"] == st.session_state.user_id

if not pode_alterar:
    st.info("Só pode alterar/apagar registos que você criou.")
    st.stop()

# Se o registo veio de uma ordem, bloquear edição (só admin)
tem_ordem = pd.notna(linha.get("ordem_id"))

col_ed, col_ap = st.columns(2)

# ---------- APAGAR ----------
with col_ap:
    st.markdown("**🗑️ Apagar**")
    key_conf = f"confirmar_apagar_{reg_id}"
    if key_conf not in st.session_state:
        st.session_state[key_conf] = False

    if st.button("🗑️ Apagar registo", type="primary",
                 use_container_width=True, key=f"btn_apagar_{reg_id}"):
        st.session_state[key_conf] = True

    if st.session_state[key_conf]:
        st.warning(f"Apagar registo #{reg_id}?")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ Sim", key=f"btn_apagar_sim_{reg_id}"):
                deletar_registo(reg_id)
                st.session_state[key_conf] = False
                st.success("Registo apagado!")
                st.rerun()
        with cb:
            if st.button("❌ Não", key=f"btn_apagar_nao_{reg_id}"):
                st.session_state[key_conf] = False
                st.rerun()

# ---------- EDITAR ----------
with col_ed:
    st.markdown("**✏️ Editar**")

    if tem_ordem and not is_admin():
        st.info("Este registo veio de uma ordem. Só admin pode editar.")
    else:
        key_edit = f"modo_edicao_{reg_id}"
        if key_edit not in st.session_state:
            st.session_state[key_edit] = False

        if st.button("✏️ Editar registo", use_container_width=True, key=f"btn_editar_{reg_id}"):
            st.session_state[key_edit] = True
            st.rerun()

        if st.session_state[key_edit]:
            ini = pd.to_datetime(linha["inicio"])
            fim = pd.to_datetime(linha["conclusao"]) if pd.notna(linha["conclusao"]) else None

            with st.form(f"form_editar_{reg_id}"):
                nome_peca_edit = st.text_input(
                    "Nome da peça *",
                    value=linha["nome_peca"],
                    key=f"edit_peca_{reg_id}",
                )

                st.markdown("**Início**")
                ce1, ce2 = st.columns(2)
                with ce1:
                    di_e = st.date_input(
                        "Data início", value=ini.date(),
                        format="DD/MM/YYYY", key=f"edit_di_{reg_id}",
                    )
                with ce2:
                    hi_e = st.time_input(
                        "Hora início", value=ini.time(),
                        step=60, key=f"edit_hi_{reg_id}",
                    )

                st.markdown("**Fim**")
                ce3, ce4 = st.columns(2)
                with ce3:
                    df_e = st.date_input(
                        "Data fim", value=fim.date() if fim else date.today(),
                        format="DD/MM/YYYY", key=f"edit_df_{reg_id}",
                    )
                with ce4:
                    hf_e = st.time_input(
                        "Hora fim", value=fim.time() if fim else time(9, 0),
                        step=60, key=f"edit_hf_{reg_id}",
                    )

                fim_aberto_e = st.checkbox(
                    "Deixar em aberto", value=(fim is None),
                    key=f"edit_aberto_{reg_id}",
                )

                motivo_e = st.text_input(
                    "Observações (opcional)",
                    value=linha["motivo"] or "",
                    key=f"edit_motivo_{reg_id}",
                )

                cs, cc = st.columns(2)
                with cs:
                    salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
                with cc:
                    cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

                if salvar:
                    dt_ini = datetime.combine(di_e, hi_e)
                    dt_fim = None if fim_aberto_e else datetime.combine(df_e, hf_e)

                    erros = []
                    if not nome_peca_edit.strip():
                        erros.append("Nome da peça é obrigatório.")
                    if dt_fim and dt_fim <= dt_ini:
                        erros.append("O fim tem de ser depois do início.")

                    if erros:
                        for e in erros:
                            st.error(e)
                    else:
                        atualizar_registo(
                            registo_id=reg_id,
                            nome_peca=nome_peca_edit.strip(),
                            inicio=dt_ini,
                            conclusao=dt_fim,
                            motivo=motivo_e.strip() or None,
                        )
                        st.success("Registo atualizado!")
                        st.session_state[key_edit] = False
                        st.rerun()

                if cancelar:
                    st.session_state[key_edit] = False
                    st.rerun()