@"
# 📋 Registo de Peças

Sistema de gestão de produção de peças por máquina.

## ✨ Funcionalidades

- 🔐 Login com 3 perfis (admin, programador, operador)
- 📋 Ordens de produção com tempo previsto vs real
- 🏭 Registo de produção (manual, ordem, inatividade)
- 📊 Previsões vs reais com desvios
- 🌐 Vista global unificada
- 👤 Gestão de conta (alterar password)
- 📥 Exportação para Excel
- 🔒 Licença remota via Google Sheets

## 🛠️ Tecnologias

- Python 3.11+
- Streamlit
- Pandas
- SQLite
- bcrypt
- openpyxl
- extra-streamlit-components

## 🚀 Como correr localmente

``````bash
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
streamlit run app.py