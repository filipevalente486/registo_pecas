import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from auth import esta_logado, is_admin, is_operador, is_programador

if not esta_logado():
    st.warning("Faça login primeiro.")
    st.stop()

st.title("🏠 Início")
st.success(f"Bem-vindo, **{st.session_state.user_nome}**!")

st.caption(f"@{st.session_state.username} · {st.session_state.role}")

st.divider()

# =========================================================
# ADMIN
# =========================================================
if is_admin():
    st.subheader("👑 Painel de Administração")

    st.markdown(
        """
        Como **administrador**, tem acesso a todas as funcionalidades do sistema.
        """
    )

    # ---------- Produção e registos ----------
    st.markdown("### 📊 Produção e registos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **🌐 Vista global**
            
            Todos os eventos do sistema: registos manuais, ordens executadas,
            ordens pendentes, ordens em curso e inatividades.
            """
        )

    with col2:
        st.markdown(
            """
            **📋 Ordens de produção**
            
            Criar e gerir ordens de produção (peça + tempo previsto).
            O operador executa e o sistema calcula o desvio.
            """
        )

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(
            """
            **🏭 Criar registo**
            
            Registar produção manual, executar ordens pendentes ou
            registar inatividade de máquinas.
            """
        )

    with col4:
        st.markdown(
            """
            **📊 Previsões vs reais**
            
            Comparar tempos previstos com tempos reais.
            Filtrar por máquina, peça e exportar para Excel.
            """
        )

    st.divider()

    # ---------- Gestão ----------
    st.markdown("### ⚙️ Gestão")

    col5, col6, col7 = st.columns(3)

    with col5:
        st.markdown(
            """
            **👥 Utilizadores**
            
            Criar, editar e desativar utilizadores.
            Atribuir perfis: admin, programador ou operador.
            """
        )

    with col6:
        st.markdown(
            """
            **🔧 Máquinas**
            
            Gerir o parque de máquinas.
            Adicionar, editar e desativar máquinas.
            """
        )

    with col7:
        st.markdown(
            """
            **🚦 Estados**
            
            Gerir os códigos de estado (P00 a P05).
            P00 = ativa, outros = inatividade com motivo.
            """
        )

    st.divider()

    # ---------- Conta ----------
    st.markdown("### 👤 A minha conta")

    st.markdown(
        """
        **👤 Minha conta**
        
        Ver os seus dados e alterar a sua password.
        """
    )

    st.divider()

    # ---------- Resumo rápido ----------
    st.subheader("📈 Resumo rápido")

    from database import listar_maquinas, listar_utilizadores, contar_total

    try:
        totais = contar_total()
        c1, c2, c3 = st.columns(3)
        c1.metric("Máquinas", totais.get("maquinas", 0))
        c2.metric("Utilizadores", totais.get("utilizadores", 0))
        c3.metric("Registos", totais.get("producoes", 0))
    except Exception:
        # Se a função contar_total não existir, ignora
        pass


# =========================================================
# PROGRAMADOR
# =========================================================
elif is_programador():
    st.subheader("👨‍💻 Painel do Programador")

    st.markdown(
        """
        Como **programador**, pode criar ordens de produção com tempo previsto
        e acompanhar os desvios face ao tempo real.
        """
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **📋 Ordens de produção**
            
            Criar ordens com peça + tempo previsto.
            Acompanhar o estado (pendente, em curso, concluída).
            """
        )

    with col2:
        st.markdown(
            """
            **📊 Previsões vs reais**
            
            Comparar tempos previstos com tempos reais.
            Filtrar por máquina, peça e exportar para Excel.
            """
        )

    st.divider()

    st.markdown("### 👤 A minha conta")

    st.markdown(
        """
        **👤 Minha conta**
        
        Ver os seus dados e alterar a sua password.
        """
    )


# =========================================================
# OPERADOR
# =========================================================
elif is_operador():
    st.subheader("👷 Painel do Operador")

    st.markdown(
        """
        Como **operador**, pode registar a produção das máquinas
        e acompanhar o histórico.
        """
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **🏭 Criar registo**
            
            Registar produção manual, executar ordens pendentes ou
            registar inatividade de máquinas.
            """
        )

    with col2:
        st.markdown(
            """
            **📋 Consultar registos**
            
            Ver o histórico de registos da máquina.
            Filtrar por máquina e exportar para Excel.
            """
        )

    st.divider()

    st.markdown("### 👤 A minha conta")

    st.markdown(
        """
        **👤 Minha conta**
        
        Ver os seus dados e alterar a sua password.
        """
    )


# =========================================================
# ROLE DESCONHECIDO
# =========================================================
else:
    st.warning("Perfil não reconhecido. Contacte o administrador.")