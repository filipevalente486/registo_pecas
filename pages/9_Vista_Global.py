import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import listar_maquinas, listar_vista_global, formatar_duracao
from auth import esta_logado, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin():
    st.error("Acesso restrito a administradores.")
    st.stop()

st.title("🌐 Vista Global")
st.caption("Todos os eventos: registos manuais, ordens executadas, ordens pendentes, ordens em curso e inatividades.")

# =========================================================
# FILTROS
# =========================================================
st.subheader("🔍 Filtros")

maquinas = listar_maquinas()
maq_opcoes = {"Todas": None}
maq_opcoes.update({
    row["codigo"]: row["id"] for _, row in maquinas.iterrows()
})

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    maq_sel = st.selectbox("Máquina", list(maq_opcoes.keys()), key="vg_maq")
with c2:
    data_de = st.date_input(
        "De",
        value=date.today() - timedelta(days=30),
        format="DD/MM/YYYY",
        key="vg_data_de",
    )
with c3:
    data_ate = st.date_input(
        "Até",
        value=date.today(),
        format="DD/MM/YYYY",
        key="vg_data_ate",
    )

st.markdown("**Tipos de evento a mostrar**")

tc1, tc2, tc3, tc4, tc5 = st.columns(5)
with tc1:
    ver_manual = st.checkbox("📝 Manual", value=True, key="vg_manual")
with tc2:
    ver_ordem_exec = st.checkbox("📋 Ordem executada", value=True, key="vg_ordem_exec")
with tc3:
    ver_pendente = st.checkbox("⏳ Pendente", value=True, key="vg_pendente")
with tc4:
    ver_em_curso = st.checkbox("▶️ Em curso", value=True, key="vg_em_curso")
with tc5:
    ver_inat = st.checkbox("🚧 Inatividade", value=True, key="vg_inat")

tipos_a_mostrar = []
if ver_manual:
    tipos_a_mostrar.append("manual")
if ver_ordem_exec:
    tipos_a_mostrar.append("ordem_executada")
if ver_pendente:
    tipos_a_mostrar.append("pendente")
if ver_em_curso:
    tipos_a_mostrar.append("em_curso")
if ver_inat:
    tipos_a_mostrar.append("inatividade")

if not tipos_a_mostrar:
    st.warning("Selecione pelo menos um tipo de evento.")
    st.stop()

# =========================================================
# CARREGAR DADOS
# =========================================================
df = listar_vista_global(
    maquina_id=maq_opcoes[maq_sel],
    data_de=data_de.strftime("%Y-%m-%d") if data_de else None,
    data_ate=data_ate.strftime("%Y-%m-%d") if data_ate else None,
)

df = df[df["tipo"].isin(tipos_a_mostrar)]

if df.empty:
    st.info("Nenhum evento para os filtros selecionados.")
    st.stop()

# =========================================================
# MÉTRICAS
# =========================================================
st.divider()

df["inicio"] = pd.to_datetime(df["inicio"])
df["fim"] = pd.to_datetime(df["fim"])
agora = pd.Timestamp.now()
df["fim_efetivo"] = df["fim"].fillna(agora)
df["duracao_min"] = (df["fim_efetivo"] - df["inicio"]).dt.total_seconds() / 60

total = len(df)
n_manual = len(df[df["tipo"] == "manual"])
n_ordem_exec = len(df[df["tipo"] == "ordem_executada"])
n_pendente = len(df[df["tipo"] == "pendente"])
n_em_curso = len(df[df["tipo"] == "em_curso"])
n_inat = len(df[df["tipo"] == "inatividade"])

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total", total)
c2.metric("📝 Manual", n_manual)
c3.metric("📋 Executadas", n_ordem_exec)
c4.metric("⏳ Pendentes", n_pendente)
c5.metric("▶️ Em curso", n_em_curso)
c6.metric("🚧 Inativ.", n_inat)

tempo_total = df["duracao_min"].sum() / 60
tempo_medio = df["duracao_min"].mean() / 60

st.divider()
c1, c2 = st.columns(2)
c1.metric("Tempo total", f"{tempo_total:.1f} h" if pd.notna(tempo_total) else "—")
c2.metric("Tempo médio", f"{tempo_medio:.1f} h" if pd.notna(tempo_medio) else "—")

# =========================================================
# TABELA
# =========================================================
st.divider()
st.subheader("📋 Eventos")

df_exibir = df.copy()

mapa_labels = {
    "manual": "📝 Manual",
    "ordem_executada": "📋 Ordem executada",
    "pendente": "⏳ Pendente",
    "em_curso": "▶️ Em curso",
    "inatividade": "🚧 Inatividade",
}
df_exibir["tipo_label"] = df_exibir["tipo"].map(mapa_labels)

def fmt_dur(row):
    if pd.isna(row["fim"]):
        if row["tipo"] in ("pendente", "em_curso"):
            return "—"
        return f"{formatar_duracao(row['duracao_min'])} (em aberto)"
    return formatar_duracao(row["duracao_min"])

df_exibir["duracao"] = df_exibir.apply(fmt_dur, axis=1)
df_exibir = df_exibir.sort_values("inicio", ascending=False)

st.dataframe(
    df_exibir[[
        "ref_id", "tipo_label", "maquina_codigo", "descricao",
        "inicio", "fim", "duracao",
        "operador", "programador", "observacoes", "ordem_id"
    ]],
    column_config={
        "ref_id": st.column_config.NumberColumn("ID", width=50, format="%d"),
        "tipo_label": st.column_config.TextColumn("Tipo", width=160),
        "maquina_codigo": st.column_config.TextColumn("Máquina", width=90),
        "descricao": st.column_config.TextColumn("Peça / Descrição", width=220),
        "inicio": st.column_config.DatetimeColumn(
            "Início", format="DD/MM/YYYY HH:mm", width=150
        ),
        "fim": st.column_config.DatetimeColumn(
            "Fim", format="DD/MM/YYYY HH:mm", width=150
        ),
        "duracao": st.column_config.TextColumn("Duração", width=120),
        "operador": st.column_config.TextColumn("Operador", width=140),
        "programador": st.column_config.TextColumn("Programador", width=140),
        "observacoes": st.column_config.TextColumn("Obs:", width=200),
        "ordem_id": st.column_config.NumberColumn("Ordem #", width=80, format="%d"),
    },
    hide_index=True,
    width="content",
)

# =========================================================
# EXPORTAR EXCEL
# =========================================================
st.divider()
st.subheader("📥 Exportar")

import io
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

colunas_export = [
    "ref_id", "tipo_label", "maquina_codigo", "descricao",
    "inicio", "fim", "duracao",
    "operador", "programador", "observacoes", "ordem_id"
]
df_export = df_exibir[colunas_export].copy()

df_export = df_export.rename(columns={
    "ref_id": "ID",
    "tipo_label": "Tipo",
    "maquina_codigo": "Máquina",
    "descricao": "Peça / Descrição",
    "inicio": "Início",
    "fim": "Fim",
    "duracao": "Duração",
    "operador": "Operador",
    "programador": "Programador",
    "observacoes": "Obs:",
    "ordem_id": "Ordem #",
})

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_export.to_excel(writer, index=False, sheet_name="Vista_Global")
    ws = writer.sheets["Vista_Global"]

    fill_cabecalho = PatternFill("solid", fgColor="4472C4")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = fill_cabecalho
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for col_idx, col_name in enumerate(df_export.columns, start=1):
        max_len = len(str(col_name))
        if len(df_export) > 0:
            max_len = max(max_len, df_export[col_name].astype(str).str.len().max())
        largura = min(max_len + 3, 45)
        letra = get_column_letter(col_idx)
        ws.column_dimensions[letra].width = largura

    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="center")

buffer.seek(0)

st.download_button(
    f"⬇️ Exportar Excel ({len(df_export)} eventos)",
    buffer.getvalue(),
    "vista_global.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="stretch",
)