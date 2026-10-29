import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from datetime import date, time, datetime
from database import (
    listar_maquinas, listar_estados, listar_eventos_maquina,
    criar_registo, criar_inatividade, atualizar_evento, deletar_evento,
    verificar_sobreposicao, formatar_duracao,
)
from auth import esta_logado, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

st.title("🏭 Registo por Máquina")

# =========================================================
# SELECIONAR MAQUINA
# =========================================================
maquinas = listar_maquinas(só_ativas=False)

if maquinas.empty:
    st.warning("Nenhuma máquina registada. Peça ao admin.")
    st.stop()

# Labels com aviso se inativa
def label_maquina(row):
    base = row["codigo"] if row["codigo"] else row["nome"]
    if pd.notna(row.get("estado_codigo")):
        return f"{base} (🔴 {row['estado_codigo']})"
    return base

opcoes_label = {
    row["id"]: label_maquina(row)
    for _, row in maquinas.iterrows()
}

maquina_id = st.selectbox(
    "Selecione a máquina",
    options=list(opcoes_label.keys()),
    format_func=lambda x: opcoes_label[x],
    key="maquina_sel",
)

maquina = maquinas[maquinas["id"] == maquina_id].iloc[0]
maquina_codigo = maquina["codigo"] or "(sem código)"
maquina_nome = maquina["nome"]

st.divider()

# =========================================================
# NOVO REGISTO — lado a lado (peça OU código de inatividade)
# =========================================================
st.subheader(f"➕ Novo registo — {maquina_codigo}")

estados = listar_estados()
est_inativos = estados[estados["codigo"] != "P00"]

est_opcoes = {None: "— (nenhum)"}
if not est_inativos.empty:
    est_opcoes.update({
        row["id"]: f"{row['codigo']} — {row['descricao']}"
        for _, row in est_inativos.iterrows()
    })

with st.form("novo_evento", clear_on_submit=True):
    col_peca, col_codigo = st.columns(2)
    with col_peca:
        nome_peca = st.text_input(
            "🏭 Nome da peça",
            placeholder="Ex.: Eixo motor",
            key="nova_peca",
        )
    with col_codigo:
        estado_id_inat = st.selectbox(
            "🚧 Código de inatividade",
            options=list(est_opcoes.keys()),
            format_func=lambda x: est_opcoes[x],
            key="nova_inat_est",
        )

    st.caption("⚠️ Preencha apenas **um** dos dois campos acima.")

    # Datas
    st.markdown("**Início**")
    c1, c2 = st.columns(2)
    with c1:
        data_inicio = st.date_input(
            "Data início", value=date.today(),
            format="DD/MM/YYYY", key="di",
        )
    with c2:
        hora_inicio = st.time_input(
            "Hora início", value=time(8, 0), step=60, key="hi",
        )

    st.markdown("**Conclusão**")
    c3, c4 = st.columns(2)
    with c3:
        data_conclusao = st.date_input(
            "Data conclusão", value=date.today(),
            format="DD/MM/YYYY", key="dc",
        )
    with c4:
        hora_conclusao = st.time_input(
            "Hora conclusão", value=time(9, 0), step=60, key="hc",
        )

    fim_aberto = st.checkbox(
        "Deixar em aberto (sem fim definido)",
        value=False,
        key="novo_aberto",
    )

    motivo_inat = st.text_input(
        "Observações (opcional)",
        placeholder="Ex.: Nota sobre a peça ou motivo da paragem",
        key="nova_inat_motivo",
    )

    if st.form_submit_button("💾 Registar", use_container_width=True):
        dt_inicio = datetime.combine(data_inicio, hora_inicio)
        dt_fim = None if fim_aberto else datetime.combine(data_conclusao, hora_conclusao)

        tem_peca = bool(nome_peca.strip())
        tem_codigo = estado_id_inat is not None

        erros = []
        if tem_peca and tem_codigo:
            erros.append("Preencha **apenas um**: peça OU código de inatividade.")
        elif not tem_peca and not tem_codigo:
            erros.append("Preencha **um dos dois**: peça OU código.")

        if not erros and dt_fim and dt_fim <= dt_inicio:
            erros.append("A conclusão tem de ser depois do início.")

        if tem_peca and not erros:
            conflito = verificar_sobreposicao(maquina_id, dt_inicio, dt_fim)
            if conflito:
                ini_c = pd.to_datetime(conflito["inicio"]).strftime("%d/%m/%Y %H:%M")
                fim_c = (
                    pd.to_datetime(conflito["fim"]).strftime("%d/%m/%Y %H:%M")
                    if conflito["fim"] else "em aberto"
                )
                erros.append(
                    f"Período bloqueado — máquina inativa "
                    f"({conflito['estado_codigo']} {conflito['estado_descricao']}) "
                    f"de {ini_c} até {fim_c}."
                )

        if erros:
            for e in erros:
                st.error(e)
        else:
            if tem_peca:
                criar_registo(
                    maquina_id=maquina_id,
                    nome_peca=nome_peca.strip(),
                    inicio=dt_inicio,
                    conclusao=dt_fim,
                    user_id=st.session_state.user_id,
                    motivo=(motivo_inat.strip() if motivo_inat else None),   # 👈 NOVO
                )
                st.success(f"✅ Produção '{nome_peca}' registada!")
            else:
                criar_inatividade(
                    maquina_id=maquina_id,
                    estado_id=estado_id_inat,
                    inicio=dt_inicio,
                    fim=dt_fim,
                    motivo=(motivo_inat.strip() if motivo_inat else None),
                    user_id=st.session_state.user_id,
                )
                st.success("✅ Inatividade registada!")
            st.rerun()

st.divider()

# =========================================================
# TABELA UNIFICADA
# =========================================================
df = listar_eventos_maquina(maquina_id)

if not df.empty:
    df["inicio"] = pd.to_datetime(df["inicio"])
    df["fim"] = pd.to_datetime(df["fim"])
    agora = pd.Timestamp.now()
    df["fim_efetivo"] = df["fim"].fillna(agora)
    df["duracao_min"] = (df["fim_efetivo"] - df["inicio"]).dt.total_seconds() / 60

    prods = df[df["tipo"] == "Producao"]
    inats = df[df["tipo"] == "Inatividade"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total eventos", len(df))
    c2.metric("Produções", len(prods))
    c3.metric("Tempo produção", f"{prods['duracao_min'].sum() / 60:.1f} h")
    c4.metric("Tempo inatividade", f"{inats['duracao_min'].sum() / 60:.1f} h")

st.subheader(f"📋 Eventos — {maquina_codigo} · {maquina_nome}")

if df.empty:
    st.info("Ainda não há eventos nesta máquina.")
    st.stop()

# Preparar colunas
df_exibir = df.copy()
df_exibir["tipo_label"] = df_exibir["tipo"].map({
    "Producao": "🏭 Produção",
    "Inatividade": "🚧 Inatividade",
})
df_exibir["identificacao"] = df_exibir.apply(
    lambda r: (
        r["referencia"]
        if r["tipo"] == "Producao"
        else f"{r['codigo_inat']} — {r['referencia']}"
    ),
    axis=1,
)

def fmt_duracao_row(row):
    dur = formatar_duracao(row["duracao_min"])
    if pd.isna(row["fim"]):
        return f"{dur} (em aberto)"
    return dur

df_exibir["duracao"] = df_exibir.apply(fmt_duracao_row, axis=1)

st.dataframe(
    df_exibir[[
        "id", "tipo_label", "identificacao", "inicio", "fim",
        "duracao", "operador", "motivo"
    ]],
    column_config={
        "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
        "tipo_label": st.column_config.TextColumn("Tipo", width=120),
        "identificacao": st.column_config.TextColumn("Peça / Código", width=220),
        "inicio": st.column_config.DatetimeColumn(
            "Início", format="DD/MM/YYYY HH:mm", width=150
        ),
        "fim": st.column_config.DatetimeColumn(
            "Fim", format="DD/MM/YYYY HH:mm", width=150
        ),
        "duracao": st.column_config.TextColumn("Duração", width=140),
        "operador": st.column_config.TextColumn("Operador", width=140),
        "motivo": st.column_config.TextColumn("Obs:", width=200),
    },
    hide_index=True,
    use_container_width=False,
)

# =========================================================
# EDITAR / APAGAR
# =========================================================
st.divider()
st.subheader("⚙️ Ações sobre um evento")

df_exibir["evento_key"] = df_exibir["tipo"] + "-" + df_exibir["id"].astype(str)
opcoes_ev = {
    row["evento_key"]: f"{row['tipo_label']} · {row['identificacao']} · {row['inicio'].strftime('%d/%m %H:%M')}"
    for _, row in df_exibir.iterrows()
}

sel_key = st.selectbox(
    "Selecione um evento",
    options=list(df_exibir["evento_key"]),
    format_func=lambda x: opcoes_ev[x],
    key="sel_evento",
)

tipo_sel, id_sel_str = sel_key.rsplit("-", 1)
id_sel = int(id_sel_str)

linha = df_exibir[df_exibir["evento_key"] == sel_key].iloc[0]
pode_alterar = is_admin() or linha["user_id"] == st.session_state.user_id

if not pode_alterar:
    st.info("Só pode alterar/apagar eventos que você criou.")
    st.stop()

col_ed, col_ap = st.columns(2)

# ---------- APAGAR ----------
with col_ap:
    st.markdown("**🗑️ Apagar**")
    key_conf = f"confirmar_apagar_{sel_key}"
    if key_conf not in st.session_state:
        st.session_state[key_conf] = False

    if st.button("🗑️ Apagar evento", type="primary",
                 use_container_width=True, key=f"btn_apagar_{sel_key}"):
        st.session_state[key_conf] = True

    if st.session_state[key_conf]:
        st.warning(f"Apagar #{id_sel} ({tipo_sel})?")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✅ Sim", key=f"btn_apagar_sim_{sel_key}"):
                deletar_evento(tipo_sel, id_sel)
                st.session_state[key_conf] = False
                st.success("Apagado!")
                st.rerun()
        with cb:
            if st.button("❌ Não", key=f"btn_apagar_nao_{sel_key}"):
                st.session_state[key_conf] = False
                st.rerun()

# ---------- EDITAR ----------
with col_ed:
    st.markdown("**✏️ Editar**")
    key_edit = f"modo_edicao_{sel_key}"
    if key_edit not in st.session_state:
        st.session_state[key_edit] = False

    if st.button("✏️ Editar evento", use_container_width=True,
                 key=f"btn_editar_{sel_key}"):
        # Limpar o session_state do motivo para forçar o valor correto
        st.session_state.pop(f"edit_mot_{sel_key}", None)
        st.session_state[key_edit] = True
        st.rerun()

    if st.session_state[key_edit]:
        ini = pd.to_datetime(linha["inicio"])
        fim = pd.to_datetime(linha["fim"]) if pd.notna(linha["fim"]) else None

        with st.form(f"form_editar_{sel_key}"):
            if tipo_sel == "Producao":
                ref_edit = st.text_input(
                    "Nome da peça *",
                    value=linha["referencia"],
                    key=f"edit_ref_{sel_key}",
                )
            else:
                st.text_input(
                    "Código / Descrição",
                    value=linha["identificacao"],
                    disabled=True,
                )
                ref_edit = linha["referencia"]

            # 👇 Observações FORA do if — sempre visível
            motivo_edit = st.text_input(
                "Observações (opcional)",
                value=(linha["motivo"] if pd.notna(linha["motivo"]) else "") or "",
                key=f"edit_mot_{sel_key}",
            )

            st.markdown("**Início**")
            ce1, ce2 = st.columns(2)
            with ce1:
                di = st.date_input(
                    "Data início", value=ini.date(),
                    format="DD/MM/YYYY", key=f"edit_di_{sel_key}",
                )
            with ce2:
                hi = st.time_input(
                    "Hora início", value=ini.time(),
                    step=60, key=f"edit_hi_{sel_key}",
                )

            st.markdown("**Fim**")
            ce3, ce4 = st.columns(2)
            with ce3:
                dc = st.date_input(
                    "Data fim", value=fim.date() if fim else date.today(),
                    format="DD/MM/YYYY", key=f"edit_dc_{sel_key}",
                )
            with ce4:
                hc = st.time_input(
                    "Hora fim", value=fim.time() if fim else time(17, 0),
                    step=60, key=f"edit_hc_{sel_key}",
                )

            fim_aberto_edit = False
            if tipo_sel == "Inatividade":
                fim_aberto_edit = st.checkbox(
                    "Deixar em aberto",
                    value=(fim is None),
                    key=f"edit_aberto_{sel_key}",
                )

            cs, cc = st.columns(2)
            with cs:
                salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
            with cc:
                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

            if salvar:
                dt_ini = datetime.combine(di, hi)
                dt_fim = None if fim_aberto_edit else datetime.combine(dc, hc)

                erros = []
                if tipo_sel == "Producao" and not ref_edit.strip():
                    erros.append("Nome da peça é obrigatório.")
                if dt_fim and dt_fim <= dt_ini:
                    erros.append("Fim tem de ser depois do início.")

                if tipo_sel == "Producao" and not erros:
                    conflito = verificar_sobreposicao(maquina_id, dt_ini, dt_fim)
                    if conflito:
                        ini_c = pd.to_datetime(conflito["inicio"]).strftime("%d/%m/%Y %H:%M")
                        fim_c = (
                            pd.to_datetime(conflito["fim"]).strftime("%d/%m/%Y %H:%M")
                            if conflito["fim"] else "em aberto"
                        )
                        erros.append(
                            f"Sobreposição com inatividade "
                            f"({conflito['estado_codigo']}) "
                            f"de {ini_c} a {fim_c}."
                        )

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    atualizar_evento(
                        tipo_sel, id_sel, ref_edit.strip(),
                        dt_ini, dt_fim, motivo_edit,
                    )
                    st.success("Evento atualizado!")
                    st.session_state[key_edit] = False
                    st.rerun()

            if cancelar:
                st.session_state[key_edit] = False
                st.rerun()