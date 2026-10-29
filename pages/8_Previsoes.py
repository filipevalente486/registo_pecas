import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import io
import streamlit as st
import pandas as pd
from database import listar_maquinas, relatorio_previsto_real, formatar_duracao
from auth import esta_logado, is_admin_or_programador, is_admin

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

if not is_admin_or_programador():
    st.error("Acesso restrito a programadores e administradores.")
    st.stop()

st.title("📊 Previsões vs Reais")

# Admin vê tudo; programador vê só as suas
filtro_prog = None if is_admin() else st.session_state.user_id
df = relatorio_previsto_real(programador_id=filtro_prog)

if df.empty:
    st.info("Ainda não há ordens concluídas.")
    st.stop()

# ---------- Filtros ----------
st.subheader("🔍 Filtros")

maquinas = listar_maquinas()
maq_opcoes = {"Todas": None}
maq_opcoes.update(dict(zip(maquinas["codigo"], maquinas["codigo"])))

c1, c2 = st.columns(2)
with c1:
    maq_sel = st.selectbox("Máquina", list(maq_opcoes.keys()))
with c2:
    peca_busca = st.text_input("Peça (contém)", placeholder="Ex.: 4580")

# Aplicar filtros
df_filtrado = df.copy()

if maq_opcoes[maq_sel] is not None:
    df_filtrado = df_filtrado[df_filtrado["maquina_real"] == maq_sel]

if peca_busca.strip():
    df_filtrado = df_filtrado[
        df_filtrado["nome_peca"].str.contains(peca_busca.strip(), case=False, na=False)
    ]

if df_filtrado.empty:
    st.info("Nenhum registo para os filtros selecionados.")
    st.stop()

# ---------- Métricas ----------
st.divider()

total = len(df_filtrado)
adiantadas = len(df_filtrado[df_filtrado["desvio_min"] < 0])
no_prazo = len(df_filtrado[df_filtrado["desvio_min"] == 0])
atrasadas = len(df_filtrado[df_filtrado["desvio_min"] > 0])
desvio_medio_pct = df_filtrado["desvio_pct"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total", total)
c2.metric("Adiantadas", adiantadas)
c3.metric("No prazo", no_prazo)
c4.metric("Atrasadas", atrasadas)
c5.metric("Desvio médio", f"{desvio_medio_pct:+.1f}%")

# ---------- Tabela ----------
st.subheader("📋 Detalhe das ordens concluídas")

df_exibir = df_filtrado.copy()
df_exibir["previsto_str"] = df_exibir["tempo_previsto_min"].apply(formatar_duracao)
df_exibir["real_str"] = df_exibir["tempo_real_min"].apply(formatar_duracao)
df_exibir["desvio_str"] = df_exibir["desvio_min"].apply(
    lambda m: f"{'+' if m > 0 else ''}{formatar_duracao(abs(m))}" if m != 0 else "0"
)
df_exibir["desvio_pct_str"] = df_exibir["desvio_pct"].apply(
    lambda p: f"{'+' if p > 0 else ''}{p:.1f}%"
)

st.dataframe(
    df_exibir[[
        "id", "nome_peca", "maquina_real",
        "previsto_str", "real_str", "desvio_str", "desvio_pct_str",
        "programador_nome", "operador_nome",
        "inicio_real", "fim_real"
    ]],
    column_config={
        "id": st.column_config.NumberColumn("ID", width=50),
        "nome_peca": st.column_config.TextColumn("Peça", width=160),
        "maquina_real": st.column_config.TextColumn("Máquina", width=90),
        "previsto_str": st.column_config.TextColumn("Previsto", width=100),
        "real_str": st.column_config.TextColumn("Real", width=100),
        "desvio_str": st.column_config.TextColumn("Desvio", width=100),
        "desvio_pct_str": st.column_config.TextColumn("Desvio %", width=90),
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

# ---------- Exportar Excel ----------
st.divider()
st.subheader("📥 Exportar")

colunas_export = [
    "id", "nome_peca", "maquina_real",
    "previsto_str", "real_str", "desvio_str", "desvio_pct_str",
    "programador_nome", "operador_nome",
    "inicio_real", "fim_real",
]
df_export = df_exibir[colunas_export].copy()

df_export = df_export.rename(columns={
    "id": "ID",
    "nome_peca": "Peça",
    "maquina_real": "Máquina",
    "previsto_str": "Tempo Previsto",
    "real_str": "Tempo Real",
    "desvio_str": "Desvio",
    "desvio_pct_str": "Desvio %",
    "programador_nome": "Programador",
    "operador_nome": "Operador",
    "inicio_real": "Início Real",
    "fim_real": "Fim Real",
})

from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_export.to_excel(writer, index=False, sheet_name="Previsoes")
    ws = writer.sheets["Previsoes"]

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

sufixo_maq = "" if maq_sel == "Todas" else f"_{maq_sel}"
sufixo_peca = "" if not peca_busca.strip() else f"_{peca_busca.strip()}"
nome_ficheiro = f"previsoes{sufixo_maq}{sufixo_peca}.xlsx"

st.download_button(
    f"⬇️ Exportar Excel ({len(df_export)} registos)",
    buffer.getvalue(),
    nome_ficheiro,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)