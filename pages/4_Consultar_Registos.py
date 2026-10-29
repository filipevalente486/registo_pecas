import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from database import (
    listar_maquinas, listar_eventos_maquina, formatar_duracao,
)
from auth import esta_logado

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

st.title("📋 Todos os registos")

st.caption(
    "Inclui **produções** (peças) e **inatividades** (paragens) de todas as máquinas."
)

# ---------- Filtros ----------
maquinas = listar_maquinas()
maq_opts = {"Todas": None}
maq_opts.update(dict(zip(maquinas["codigo"], maquinas["id"])))

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    nome_maq = st.selectbox("Máquina", list(maq_opts.keys()))
with c2:
    tipo_filtro = st.selectbox(
        "Tipo", ["Todos", "Só produções", "Só inatividades"]
    )
with c3:
    busca = st.text_input("Buscar peça / obs")

# ---------- Query ----------
maquina_id = maq_opts[nome_maq]
df = listar_eventos_maquina(maquina_id)

# Filtrar tipo
if tipo_filtro == "Só produções":
    df = df[df["tipo"] == "Producao"]
elif tipo_filtro == "Só inatividades":
    df = df[df["tipo"] == "Inatividade"]

# Filtrar busca (peça / motivo)
if busca.strip():
    termo = busca.strip()
    mask = df["referencia"].str.contains(termo, case=False, na=False)
    mask |= df["motivo"].str.contains(termo, case=False, na=False)
    df = df[mask]

if df.empty:
    st.info("Nenhum registo encontrado.")
    st.stop()

# ---------- Calcular duração ----------
df["inicio"] = pd.to_datetime(df["inicio"])
df["fim"] = pd.to_datetime(df["fim"])
agora = pd.Timestamp.now()
df["fim_efetivo"] = df["fim"].fillna(agora)
df["duracao_min"] = (df["fim_efetivo"] - df["inicio"]).dt.total_seconds() / 60

def fmt_dur(minutos, em_aberto):
    txt = formatar_duracao(minutos)
    return txt + " (em aberto)" if em_aberto else txt

df["duracao"] = df.apply(
    lambda r: fmt_dur(r["duracao_min"], pd.isna(r["fim"])),
    axis=1
)

# ---------- Preparar colunas ----------
df["tipo_label"] = df["tipo"].map({
    "Producao": "🏭 Produção",
    "Inatividade": "🚧 Inatividade",
})

df["identificacao"] = df.apply(
    lambda r: (
        r["referencia"]
        if r["tipo"] == "Producao"
        else f"{r['codigo_inat']} — {r['referencia']}"
    ),
    axis=1,
)

# ---------- Métricas ----------
st.divider()

prods = df[df["tipo"] == "Producao"]
inats = df[df["tipo"] == "Inatividade"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total eventos", len(df))
c2.metric("Produções", len(prods))
c3.metric(
    "Tempo produção",
    f"{prods['duracao_min'].sum() / 60:.1f} h" if not prods.empty else "0 h"
)
c4.metric(
    "Tempo inatividade",
    f"{inats['duracao_min'].sum() / 60:.1f} h" if not inats.empty else "0 h"
)

# ---------- Tabela ----------
st.subheader("📋 Eventos")

df_exibir = df.sort_values("inicio", ascending=False).copy()

st.dataframe(
    df_exibir[[
        "id", "tipo_label", "maquina_codigo", "identificacao",
        "inicio", "fim", "duracao", "operador", "motivo"
    ]],
    column_config={
        "id": st.column_config.NumberColumn("ID", width=50, format="%d"),
        "tipo_label": st.column_config.TextColumn("Tipo", width=120),
        "maquina_codigo": st.column_config.TextColumn("Máquina", width=90),
        "identificacao": st.column_config.TextColumn("Peça / Código", width=200),
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

# ---------- Exportar CSV ----------
st.divider()

csv = (
    df_exibir[[
        "id", "tipo_label", "maquina_codigo", "identificacao",
        "inicio", "fim", "duracao", "operador", "motivo"
    ]]
    .to_csv(index=False)
    .encode("utf-8")
)

# ---------- Exportar Excel ----------
st.divider()

# ---------- Exportar Excel ----------
st.divider()

import io
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

colunas_export = [
    "id", "tipo_label", "maquina_codigo", "identificacao",
    "inicio", "fim", "duracao", "operador", "motivo"
]
df_export = df_exibir[colunas_export].copy()

df_export = df_export.rename(columns={
    "id": "ID",
    "tipo_label": "Tipo",
    "maquina_codigo": "Máquina",
    "identificacao": "Peça / Código",
    "inicio": "Início",
    "fim": "Fim",
    "duracao": "Duração",
    "operador": "Operador",
    "motivo": "Obs:",
})

buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    # 1. Escrever os dados
    df_export.to_excel(writer, index=False, sheet_name="Eventos")

    # 2. Obter a worksheet
    ws = writer.sheets["Eventos"]

    # 3. Formatar cabeçalho (linha 1)
    fill_cabecalho = PatternFill("solid", fgColor="4472C4")   # azul
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = fill_cabecalho
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 4. Ajustar largura das colunas automaticamente
    for col_idx, col_name in enumerate(df_export.columns, start=1):
        # Maior entre o cabeçalho e o maior valor da coluna
        max_len = len(str(col_name))
        if len(df_export) > 0:
            max_len = max(max_len, df_export[col_name].astype(str).str.len().max())
        largura = min(max_len + 3, 45)   # +3 de margem, máx 45
        letra = get_column_letter(col_idx)
        ws.column_dimensions[letra].width = largura

    # 5. Congelar a linha do cabeçalho (fica sempre visível ao fazer scroll)
    ws.freeze_panes = "A2"

    # 6. Alinhamento vertical do corpo
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="center")

buffer.seek(0)

st.download_button(
    "⬇️ Exportar Excel (.xlsx)",
    buffer.getvalue(),
    "registos_e_inatividades.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)