"""
Camada de acesso à base de dados (SQLite).

Tabelas:
  - utilizadores : login e permissões
  - maquinas     : máquinas registadas
  - estados      : estados (P00 = ativa, P01+ = inatividade)
  - registos     : produções por máquina
  - inatividades : períodos de paragem por máquina
"""
import sqlite3
import bcrypt
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "registo.db"


# =========================================================
# CONEXÃO
# =========================================================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# =========================================================
# INICIALIZAÇÃO
# =========================================================
def init_db():
    """Cria as tabelas e popula com dados iniciais se a BD estiver vazia."""
    with get_conn() as conn:
        # Utilizadores
        conn.execute("""
            CREATE TABLE IF NOT EXISTS utilizadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'operador', 'programador')),
                nome TEXT NOT NULL,
                ativo INTEGER DEFAULT 1
            )
        """)

        # Estados
        conn.execute("""
            CREATE TABLE IF NOT EXISTS estados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                sistema INTEGER DEFAULT 0
            )
        """)

        # Máquinas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maquinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo TEXT,
                ativa INTEGER DEFAULT 1,
                estado_id INTEGER,
                FOREIGN KEY (estado_id) REFERENCES estados(id)
            )
        """)

        # Registos de produção (conclusao e motivo podem ser NULL)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                maquina_id INTEGER NOT NULL,
                nome_peca TEXT NOT NULL,
                inicio TEXT NOT NULL,
                conclusao TEXT,
                motivo TEXT,
                user_id INTEGER NOT NULL,
                criado_em TEXT NOT NULL,
                ordem_id INTEGER,
                FOREIGN KEY (maquina_id) REFERENCES maquinas(id),
                FOREIGN KEY (user_id) REFERENCES utilizadores(id)
            )
        """)

        # Inatividades (fim e motivo podem ser NULL)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inatividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                maquina_id INTEGER NOT NULL,
                estado_id INTEGER NOT NULL,
                inicio TEXT NOT NULL,
                fim TEXT,
                motivo TEXT,
                user_id INTEGER,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (maquina_id) REFERENCES maquinas(id),
                FOREIGN KEY (estado_id) REFERENCES estados(id),
                FOREIGN KEY (user_id) REFERENCES utilizadores(id)
            )
        """)

        # 6. ⬇️ NOVA TABELA  ordens_producao⬇️
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ordens_producao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_peca TEXT NOT NULL,
                tempo_previsto_min INTEGER NOT NULL,
                programador_id INTEGER NOT NULL,
                estado TEXT NOT NULL DEFAULT 'pendente',
                inicio_real TEXT,
                fim_real TEXT,
                maquina_real_id INTEGER,
                operador_id INTEGER,
                motivo TEXT,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (programador_id) REFERENCES utilizadores(id),
                FOREIGN KEY (maquina_real_id) REFERENCES maquinas(id),
                FOREIGN KEY (operador_id) REFERENCES utilizadores(id)
            )
        """)
        # ⬆️ FIM ⬆️

        # Migração: adicionar colunas se a tabela já existia sem elas
        cols_reg = [c[1] for c in conn.execute("PRAGMA table_info(registos)").fetchall()]
        if "motivo" not in cols_reg:
            conn.execute("ALTER TABLE registos ADD COLUMN motivo TEXT")
        cols_maq = [c[1] for c in conn.execute("PRAGMA table_info(maquinas)").fetchall()]
        if "estado_id" not in cols_maq:
            conn.execute("ALTER TABLE maquinas ADD COLUMN estado_id INTEGER")

        conn.commit()
        
            
        

    seed_inicial()

# o seed inicial , é composto pelos nomes de um admin e alguns operadores e programadores para o arranque sempre que não existir a bd
def seed_inicial():
    """Cria utilizadores, estados e máquinas iniciais se a BD estiver vazia."""
    with get_conn() as conn:
        # Utilizadores
        n = conn.execute("SELECT COUNT(*) FROM utilizadores").fetchone()[0]
        if n == 0:
            utilizadores = [
                ("admin",       "admin123",       "admin",       "Administrador"),
                ("joao",        "joao123",        "operador",    "João Silva"),
                ("maria",       "maria123",       "operador",    "Maria Santos"),
                ("pedro",       "pedro123",       "operador",    "Pedro Costa"),
                ("carlos", "carlos123", "programador", "Carlos Sousa"),
                ("ana", "ana123", "programador", "Ana Sousa"),

            ]
            for username, pwd, role, nome in utilizadores:
                h = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                conn.execute(
                    "INSERT INTO utilizadores (username, password_hash, role, nome) "
                    "VALUES (?, ?, ?, ?)",
                    (username, h, role, nome)
                )

        # Estados iniciais (P00 = sistema, não editável)
        n = conn.execute("SELECT COUNT(*) FROM estados").fetchone()[0]
        if n == 0:
            estados = [
                ("P00", "Ativa", 1),
                ("P01", "Faltam dados no programa", 0),
                ("P02", "Aguarda ponte rolante", 0),
                ("P03", "Avaria mecânica", 0),
                ("P04", "Avaria elétrica", 0),
                ("P05", "Avaria hidráulica", 0),
            ]
            for codigo, descricao, sistema in estados:
                conn.execute(
                    "INSERT INTO estados (codigo, descricao, sistema) VALUES (?, ?, ?)",
                    (codigo, descricao, sistema)
                )

        # Máquinas iniciais (estado P00)
        n = conn.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0]
        if n == 0:
            row = conn.execute("SELECT id FROM estados WHERE codigo = 'P00'").fetchone()
            estado_p00 = row[0] if row else None

            maquinas = [
                ("CNC 1", "CNC01"),
                ("CNC 2", "CNC02"),
                ("Prensa A", "PRE01"),
                ("Torno 3", "TOR03"),
            ]
            for nome, codigo in maquinas:
                conn.execute(
                    "INSERT INTO maquinas (nome, codigo, ativa, estado_id) "
                    "VALUES (?, ?, 1, ?)",
                    (nome, codigo, estado_p00)
                )

        conn.commit()

# =========================================================
# UTILIZADORES
# =========================================================
def buscar_utilizador_por_username(username):
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM utilizadores WHERE username = ?",
            conn, params=(username,)
        )
        return df.iloc[0] if not df.empty else None

def listar_utilizadores():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT id, username, role, nome, ativo FROM utilizadores ORDER BY id",
            conn
        )

def criar_utilizador(username, password, role, nome):
    h = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO utilizadores (username, password_hash, role, nome) "
                "VALUES (?, ?, ?, ?)",
                (username, h, role, nome)
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

def atualizar_utilizador(user_id, username, role, nome, ativo, nova_password=None):
    with get_conn() as conn:
        if nova_password:
            h = bcrypt.hashpw(nova_password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "UPDATE utilizadores SET username=?, role=?, nome=?, ativo=?, password_hash=? "
                "WHERE id=?",
                (username, role, nome, int(ativo), h, int(user_id))
            )
        else:
            conn.execute(
                "UPDATE utilizadores SET username=?, role=?, nome=?, ativo=? WHERE id=?",
                (username, role, nome, int(ativo), int(user_id))
            )
        conn.commit()

def deletar_utilizador(user_id):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM utilizadores WHERE id = ?", (int(user_id),))
        conn.commit()
        return cur.rowcount

# =========================================================
# MÁQUINAS
# =========================================================
def listar_maquinas(só_ativas=False):
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT id, nome, codigo, ativa FROM maquinas ORDER BY nome",
            conn
        )

        inats = pd.read_sql_query(
            """SELECT i.maquina_id, e.codigo, e.descricao, i.inicio
               FROM inatividades i
               JOIN estados e ON e.id = i.estado_id
               WHERE i.fim IS NULL""",
            conn
        )
        mapa_estado = {
            row["maquina_id"]: (row["codigo"], row["descricao"])
            for _, row in inats.iterrows()
        }

        df["estado_codigo"] = df["id"].map(
            lambda x: mapa_estado.get(x, (None, None))[0]
        )
        df["estado_descricao"] = df["id"].map(
            lambda x: mapa_estado.get(x, (None, None))[1]
        )

        if só_ativas:
            df = df[df["estado_codigo"].isna()]

        return df.reset_index(drop=True)

def criar_maquina(nome, codigo):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO maquinas (nome, codigo) VALUES (?, ?)",
            (nome, codigo)
        )
        conn.commit()
        return cur.lastrowid

def atualizar_maquina(maquina_id, nome, codigo, ativa):
    with get_conn() as conn:
        conn.execute(
            "UPDATE maquinas SET nome=?, codigo=?, ativa=? WHERE id=?",
            (nome, codigo, int(ativa), int(maquina_id))
        )
        conn.commit()

def deletar_maquina(maquina_id):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM maquinas WHERE id = ?", (int(maquina_id),))
        conn.commit()
        return cur.rowcount

def buscar_maquina(maquina_id):
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM maquinas WHERE id = ?",
            conn, params=(int(maquina_id),)
        )
        return df.iloc[0] if not df.empty else None

# =========================================================
# REGISTOS (produção)
# =========================================================
def criar_registo(maquina_id, nome_peca, inicio, conclusao, user_id, motivo=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO registos
               (maquina_id, nome_peca, inicio, conclusao, motivo, user_id, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                int(maquina_id),
                nome_peca,
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                conclusao.strftime("%Y-%m-%d %H:%M:%S") if conclusao else None,
                motivo,
                int(user_id),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        return cur.lastrowid

def listar_registos(maquina_id):
    with get_conn() as conn:
        return pd.read_sql_query(
            """SELECT r.id, r.nome_peca, r.inicio, r.conclusao, r.motivo,
                      r.user_id, r.ordem_id, u.nome AS user_nome
               FROM registos r
               LEFT JOIN utilizadores u ON u.id = r.user_id
               WHERE r.maquina_id = ?
               ORDER BY r.inicio DESC""",
            conn, params=(int(maquina_id),)
        )

def deletar_registo(registo_id):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM registos WHERE id = ?", (int(registo_id),))
        conn.commit()
        return cur.rowcount

def atualizar_registo(registo_id, nome_peca, inicio, conclusao, motivo=None):
    """Atualiza um registo existente."""
    with get_conn() as conn:
        cur = conn.execute(
            """UPDATE registos
               SET nome_peca = ?, inicio = ?, conclusao = ?, motivo = ?
               WHERE id = ?""",
            (
                nome_peca,
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                conclusao.strftime("%Y-%m-%d %H:%M:%S") if conclusao else None,
                motivo,
                int(registo_id),
            )
        )
        conn.commit()
        return cur.rowcount


# =========================================================
# ESTADOS - 🍔🍟🍕🧂🥓
# =========================================================
def listar_estados():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM estados ORDER BY codigo",
            conn
        )

def criar_estado(codigo, descricao):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO estados (codigo, descricao, sistema) VALUES (?, ?, 0)",
                (codigo, descricao)
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

def atualizar_estado(estado_id, descricao):
    with get_conn() as conn:
        conn.execute(
            "UPDATE estados SET descricao = ? WHERE id = ? AND sistema = 0",
            (descricao, int(estado_id))
        )
        conn.commit()

def deletar_estado(estado_id):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM estados WHERE id = ? AND sistema = 0",
            (int(estado_id),)
        )
        conn.commit()
        return cur.rowcount

# =========================================================
# INATIVIDADES
# =========================================================
def criar_inatividade(maquina_id, estado_id, inicio, fim, motivo=None, user_id=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO inatividades
               (maquina_id, estado_id, inicio, fim, motivo, user_id, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                int(maquina_id),
                int(estado_id),
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                fim.strftime("%Y-%m-%d %H:%M:%S") if fim else None,
                motivo,
                int(user_id) if user_id else None,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        conn.commit()
        return cur.lastrowid

def fechar_inatividade(inatividade_id, fim):
    with get_conn() as conn:
        conn.execute(
            "UPDATE inatividades SET fim = ? WHERE id = ?",
            (fim.strftime("%Y-%m-%d %H:%M:%S"), int(inatividade_id))
        )
        conn.commit()

def listar_inatividades(maquina_id=None):
    with get_conn() as conn:
        sql = """
            SELECT i.id, i.maquina_id, m.codigo AS maquina_codigo, m.nome AS maquina_nome,
                   i.estado_id, e.codigo AS estado_codigo, e.descricao AS estado_descricao,
                   i.inicio, i.fim, i.motivo, u.nome AS user_nome
            FROM inatividades i
            LEFT JOIN maquinas m ON m.id = i.maquina_id
            LEFT JOIN estados e ON e.id = i.estado_id
            LEFT JOIN utilizadores u ON u.id = i.user_id
        """
        params = []
        if maquina_id is not None:
            sql += " WHERE i.maquina_id = ?"
            params.append(int(maquina_id))
        sql += " ORDER BY i.inicio DESC"
        return pd.read_sql_query(sql, conn, params=params)

def deletar_inatividade(inatividade_id):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM inatividades WHERE id = ?",
            (int(inatividade_id),)
        )
        conn.commit()
        return cur.rowcount

# =========================================================
# EVENTOS UNIFICADOS (produção + inatividade)
# =========================================================
def listar_eventos_maquina(maquina_id=None):
    """Devolve todos os eventos (producoes + inatividades)."""
    with get_conn() as conn:
        if maquina_id is None:
            sql = """
                SELECT * FROM (
                    SELECT
                        p.id AS id, 'Producao' AS tipo,
                        p.nome_peca AS referencia, NULL AS codigo_inat,
                        p.inicio AS inicio, p.conclusao AS fim,
                        p.user_id AS user_id, p.motivo AS motivo,
                        m.codigo AS maquina_codigo, m.nome AS maquina_nome
                    FROM registos p
                    LEFT JOIN maquinas m ON m.id = p.maquina_id

                    UNION ALL

                    SELECT
                        i.id AS id, 'Inatividade' AS tipo,
                        e.descricao AS referencia, e.codigo AS codigo_inat,
                        i.inicio AS inicio, i.fim AS fim,
                        i.user_id AS user_id, i.motivo AS motivo,
                        m.codigo AS maquina_codigo, m.nome AS maquina_nome
                    FROM inatividades i
                    JOIN estados e ON e.id = i.estado_id
                    LEFT JOIN maquinas m ON m.id = i.maquina_id
                )
                ORDER BY inicio DESC
            """
            df = pd.read_sql_query(sql, conn)
        else:
            sql = """
                SELECT * FROM (
                    SELECT
                        p.id AS id, 'Producao' AS tipo,
                        p.nome_peca AS referencia, NULL AS codigo_inat,
                        p.inicio AS inicio, p.conclusao AS fim,
                        p.user_id AS user_id, p.motivo AS motivo,
                        m.codigo AS maquina_codigo, m.nome AS maquina_nome
                    FROM registos p
                    LEFT JOIN maquinas m ON m.id = p.maquina_id
                    WHERE p.maquina_id = ?

                    UNION ALL

                    SELECT
                        i.id AS id, 'Inatividade' AS tipo,
                        e.descricao AS referencia, e.codigo AS codigo_inat,
                        i.inicio AS inicio, i.fim AS fim,
                        i.user_id AS user_id, i.motivo AS motivo,
                        m.codigo AS maquina_codigo, m.nome AS maquina_nome
                    FROM inatividades i
                    JOIN estados e ON e.id = i.estado_id
                    LEFT JOIN maquinas m ON m.id = i.maquina_id
                    WHERE i.maquina_id = ?
                )
                ORDER BY inicio DESC
            """
            df = pd.read_sql_query(
                sql, conn, params=(int(maquina_id), int(maquina_id))
            )

        if not df.empty:
            users = pd.read_sql_query(
                "SELECT id, nome FROM utilizadores", conn
            )
            mapa_users = dict(zip(users["id"], users["nome"]))
            df["operador"] = df["user_id"].map(mapa_users)
        else:
            df["operador"] = None

        return df

def atualizar_evento(tipo, evento_id, referencia, inicio, fim, motivo=None):
    """Atualiza um evento (producao ou inatividade)."""
    with get_conn() as conn:
        if tipo == "Producao":
            cur = conn.execute(
                """UPDATE registos
                   SET nome_peca = ?, inicio = ?, conclusao = ?, motivo = ?
                   WHERE id = ?""",
                (
                    referencia,
                    inicio.strftime("%Y-%m-%d %H:%M:%S"),
                    fim.strftime("%Y-%m-%d %H:%M:%S") if fim else None,
                    motivo,
                    int(evento_id),
                )
            )
        elif tipo == "Inatividade":
            cur = conn.execute(
                """UPDATE inatividades
                   SET inicio = ?, fim = ?, motivo = ?
                   WHERE id = ?""",
                (
                    inicio.strftime("%Y-%m-%d %H:%M:%S"),
                    fim.strftime("%Y-%m-%d %H:%M:%S") if fim else None,
                    motivo,
                    int(evento_id),
                )
            )
        else:
            return 0
        conn.commit()
        return cur.rowcount

def deletar_evento(tipo, evento_id):
    with get_conn() as conn:
        if tipo == "Producao":
            cur = conn.execute(
                "DELETE FROM registos WHERE id = ?", (int(evento_id),)
            )
        elif tipo == "Inatividade":
            cur = conn.execute(
                "DELETE FROM inatividades WHERE id = ?", (int(evento_id),)
            )
        else:
            return 0
        conn.commit()
        return cur.rowcount

def verificar_sobreposicao(maquina_id, inicio, conclusao):
    """Verifica se [inicio, conclusao] se sobrepoe a algum periodo de inatividade."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT i.id, i.inicio, i.fim, i.motivo,
                      e.codigo AS estado_codigo, e.descricao AS estado_descricao
               FROM inatividades i
               JOIN estados e ON e.id = i.estado_id
               WHERE i.maquina_id = ?
               ORDER BY i.inicio""",
            (int(maquina_id),)
        ).fetchall()

    if conclusao is None:
        ini_novo = inicio.strftime("%Y-%m-%d %H:%M:%S")
        fim_novo = "9999-12-31 23:59:59"
    else:
        ini_novo = inicio.strftime("%Y-%m-%d %H:%M:%S")
        fim_novo = conclusao.strftime("%Y-%m-%d %H:%M:%S")

    for row in rows:
        i_ini = row[1]
        i_fim = row[2] if row[2] else "9999-12-31 23:59:59"
        if ini_novo < i_fim and fim_novo > i_ini:
            return {
                "id": row[0], "inicio": i_ini, "fim": row[2],
                "motivo": row[3], "estado_codigo": row[4],
                "estado_descricao": row[5],
            }
    return None

# =========================================================
# UTILITÁRIOS
# =========================================================
def formatar_duracao(minutos):
    """Formata minutos. Aceita None/NaN (devolve 'em aberto')."""
    import math
    if minutos is None or (isinstance(minutos, float) and math.isnan(minutos)):
        return "em aberto"
    m = int(minutos)
    if m < 60:
        return f"{m}min"
    h, r = divmod(m, 60)
    if h < 24:
        return f"{h}h {r:02d}min" if r else f"{h}h"
    dias, h_rest = divmod(h, 24)
    texto_dias = f"{dias} dia" + ("s" if dias > 1 else "")
    if h_rest:
        return f"{texto_dias} e {h_rest}h"
    return texto_dias

# =========================================================
# ORDENS DE PRODUÇÃO
# =========================================================
def criar_ordem(nome_peca, tempo_previsto_min, programador_id, motivo=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO ordens_producao
               (nome_peca, tempo_previsto_min, programador_id, motivo, estado, criado_em)
               VALUES (?, ?, ?, ?, 'pendente', ?)""",
            (
                nome_peca,
                int(tempo_previsto_min),
                int(programador_id),
                motivo,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        conn.commit()
        return cur.lastrowid


    with get_conn() as conn:
        sql = """
            SELECT o.*,
                   mr.codigo AS maquina_real_codigo,
                   mr.nome AS maquina_real_nome,
                   up.nome AS programador_nome,
                   uo.nome AS operador_nome
            FROM ordens_producao o
            LEFT JOIN maquinas mr ON mr.id = o.maquina_real_id
            LEFT JOIN utilizadores up ON up.id = o.programador_id
            LEFT JOIN utilizadores uo ON uo.id = o.operador_id
            WHERE 1=1
        """
        params = []
        if estado:
            sql += " AND o.estado = ?"
            params.append(estado)
        sql += " ORDER BY o.criado_em DESC"
        return pd.read_sql_query(sql, conn, params=params)

def listar_ordens(estado=None, programador_id=None):
    with get_conn() as conn:
        sql = """
            SELECT o.*,
                   mr.codigo AS maquina_real_codigo,
                   mr.nome AS maquina_real_nome,
                   up.nome AS programador_nome,
                   uo.nome AS operador_nome
            FROM ordens_producao o
            LEFT JOIN maquinas mr ON mr.id = o.maquina_real_id
            LEFT JOIN utilizadores up ON up.id = o.programador_id
            LEFT JOIN utilizadores uo ON uo.id = o.operador_id
            WHERE 1=1
        """
        params = []
        if estado:
            sql += " AND o.estado = ?"
            params.append(estado)
        if programador_id is not None:
            sql += " AND o.programador_id = ?"
            params.append(int(programador_id))
        sql += " ORDER BY o.criado_em DESC"
        return pd.read_sql_query(sql, conn, params=params)

def buscar_ordem(ordem_id):
    with get_conn() as conn:
        df = pd.read_sql_query(
            """SELECT o.*,
                      mr.codigo AS maquina_real_codigo,
                      up.nome AS programador_nome,
                      uo.nome AS operador_nome
               FROM ordens_producao o
               LEFT JOIN maquinas mr ON mr.id = o.maquina_real_id
               LEFT JOIN utilizadores up ON up.id = o.programador_id
               LEFT JOIN utilizadores uo ON uo.id = o.operador_id
               WHERE o.id = ?""",
            conn, params=(int(ordem_id),)
        )
        return df.iloc[0] if not df.empty else None


def iniciar_ordem(ordem_id, maquina_real_id, operador_id):
    """Operador escolhe a máquina e marca início."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE ordens_producao
               SET estado = 'em_curso',
                   inicio_real = ?,
                   maquina_real_id = ?,
                   operador_id = ?
               WHERE id = ? AND estado = 'pendente'""",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(maquina_real_id),
                int(operador_id),
                int(ordem_id),
            )
        )
        conn.commit()


def terminar_ordem(ordem_id, motivo=None):
    with get_conn() as conn:
        conn.execute(
            """UPDATE ordens_producao
               SET estado = 'concluida',
                   fim_real = ?,
                   motivo = COALESCE(?, motivo)
               WHERE id = ? AND estado = 'em_curso'""",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                motivo,
                int(ordem_id),
            )
        )
        conn.commit()


def cancelar_ordem(ordem_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE ordens_producao SET estado = 'cancelada' WHERE id = ? AND estado = 'pendente'",
            (int(ordem_id),)
        )
        conn.commit()


def atualizar_tempo_previsto(ordem_id, tempo_previsto_min, motivo=None):



    """Só o programador. Só se a ordem estiver pendente."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE ordens_producao
               SET tempo_previsto_min = ?, motivo = COALESCE(?, motivo)
               WHERE id = ? AND estado = 'pendente'""",
            (int(tempo_previsto_min), motivo, int(ordem_id))
        )
        conn.commit()


    with get_conn() as conn:


        df = pd.read_sql_query(
            """SELECT o.id, o.nome_peca,
                      mr.codigo AS maquina_real,
                      o.tempo_previsto_min,
                      o.inicio_real,
                      o.fim_real,
                      up.nome AS programador_nome,
                      uo.nome AS operador_nome
               FROM ordens_producao o
               LEFT JOIN maquinas mr ON mr.id = o.maquina_real_id
               LEFT JOIN utilizadores up ON up.id = o.programador_id
               LEFT JOIN utilizadores uo ON uo.id = o.operador_id
               WHERE o.estado = 'concluida'
               ORDER BY o.fim_real DESC""",
            conn
        )

        if not df.empty:
            df["inicio_real"] = pd.to_datetime(df["inicio_real"])
            df["fim_real"] = pd.to_datetime(df["fim_real"])
            df["tempo_real_min"] = (
                (df["fim_real"] - df["inicio_real"]).dt.total_seconds() / 60
            ).round().astype(int)
            df["desvio_min"] = df["tempo_real_min"] - df["tempo_previsto_min"]
            df["desvio_pct"] = (
                df["desvio_min"] / df["tempo_previsto_min"] * 100
            ).round(1)

        return df

def relatorio_previsto_real(programador_id=None):
    with get_conn() as conn:
        sql = """
            SELECT o.id, o.nome_peca, mr.codigo AS maquina_real,
                   o.tempo_previsto_min, o.inicio_real, o.fim_real,
                   up.nome AS programador_nome, uo.nome AS operador_nome
            FROM ordens_producao o
            LEFT JOIN maquinas mr ON mr.id = o.maquina_real_id
            LEFT JOIN utilizadores up ON up.id = o.programador_id
            LEFT JOIN utilizadores uo ON uo.id = o.operador_id
            WHERE o.estado = 'concluida'
        """
        params = []
        if programador_id is not None:
            sql += " AND o.programador_id = ?"
            params.append(int(programador_id))
        sql += " ORDER BY o.fim_real DESC"
        df = pd.read_sql_query(sql, conn, params=params)

        if not df.empty:
            df["inicio_real"] = pd.to_datetime(df["inicio_real"])
            df["fim_real"] = pd.to_datetime(df["fim_real"])
            df["tempo_real_min"] = (
                (df["fim_real"] - df["inicio_real"]).dt.total_seconds() / 60
            ).round().astype(int)
            df["desvio_min"] = df["tempo_real_min"] - df["tempo_previsto_min"]
            df["desvio_pct"] = (
                df["desvio_min"] / df["tempo_previsto_min"] * 100
            ).round(1)

        return df


# =========================================================
# REGISTAR + CONCLUIR ORDEM (num só passo)
# =========================================================
def registar_e_concluir_ordem(ordem_id, maquina_id, inicio, fim, user_id, motivo=None):
    """
    Cria um registo em `registos` E conclui a ordem em `ordens_producao`.
    - nome_peca vem da ordem (trancado para o operador)
    - maquina_id pode ser diferente da planeada (mas não há planeada agora)
    """
    with get_conn() as conn:
        # 1. Ler a ordem
        row = conn.execute(
            "SELECT nome_peca, estado FROM ordens_producao WHERE id = ?",
            (int(ordem_id),)
        ).fetchone()

        if not row or row[1] not in ("pendente", "em_curso"):
            return None  # ordem inválida ou já concluída

        nome_peca = row[0]

        # 2. Criar o registo em `registos`
        cur = conn.execute(
            """INSERT INTO registos
               (maquina_id, nome_peca, inicio, conclusao, motivo,
                user_id, criado_em, ordem_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                int(maquina_id),
                nome_peca,
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                fim.strftime("%Y-%m-%d %H:%M:%S"),
                motivo,
                int(user_id),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(ordem_id),
            )
        )
        registo_id = cur.lastrowid

        # 3. Concluir a ordem
        conn.execute(
            """UPDATE ordens_producao
               SET estado = 'concluida',
                   inicio_real = ?,
                   fim_real = ?,
                   maquina_real_id = ?,
                   operador_id = ?,
                   motivo = COALESCE(?, motivo)
               WHERE id = ?""",
            (
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                fim.strftime("%Y-%m-%d %H:%M:%S"),
                int(maquina_id),
                int(user_id),
                motivo,
                int(ordem_id),
            )
        )
        conn.commit()
        return registo_id


# =========================================================
# VISTA GLOBAL UNIFICADA
# =========================================================
def listar_vista_global(maquina_id=None, data_de=None, data_ate=None):
    """
    Devolve todos os eventos do sistema:
    - Registos (manuais + ordens executadas)
    - Ordens pendentes/em curso
    - Inatividades
    """
    with get_conn() as conn:
        sql_registos = """
            SELECT
                r.id AS ref_id,
                CASE
                    WHEN r.ordem_id IS NOT NULL THEN 'ordem_executada'
                    ELSE 'manual'
                END AS tipo,
                m.codigo AS maquina_codigo,
                m.nome AS maquina_nome,
                r.nome_peca AS descricao,
                r.inicio AS inicio,
                r.conclusao AS fim,
                r.motivo AS observacoes,
                u.nome AS operador,
                NULL AS programador,
                r.ordem_id AS ordem_id
            FROM registos r
            LEFT JOIN maquinas m ON m.id = r.maquina_id
            LEFT JOIN utilizadores u ON u.id = r.user_id
            WHERE 1=1
        """
        params_reg = []
        if maquina_id is not None:
            sql_registos += " AND r.maquina_id = ?"
            params_reg.append(int(maquina_id))
        if data_de:
            sql_registos += " AND DATE(r.inicio) >= ?"
            params_reg.append(data_de)
        if data_ate:
            sql_registos += " AND DATE(r.inicio) <= ?"
            params_reg.append(data_ate)

        sql_ordens = """
            SELECT
                o.id AS ref_id,
                o.estado AS tipo,
                NULL AS maquina_codigo,
                NULL AS maquina_nome,
                o.nome_peca AS descricao,
                o.criado_em AS inicio,
                NULL AS fim,
                o.motivo AS observacoes,
                NULL AS operador,
                up.nome AS programador,
                NULL AS ordem_id
            FROM ordens_producao o
            LEFT JOIN utilizadores up ON up.id = o.programador_id
            WHERE o.estado IN ('pendente', 'em_curso')
        """
        params_ord = []
        if data_de:
            sql_ordens += " AND DATE(o.criado_em) >= ?"
            params_ord.append(data_de)
        if data_ate:
            sql_ordens += " AND DATE(o.criado_em) <= ?"
            params_ord.append(data_ate)

        sql_inat = """
            SELECT
                i.id AS ref_id,
                'inatividade' AS tipo,
                m.codigo AS maquina_codigo,
                m.nome AS maquina_nome,
                e.descricao AS descricao,
                i.inicio AS inicio,
                i.fim AS fim,
                i.motivo AS observacoes,
                u.nome AS operador,
                NULL AS programador,
                NULL AS ordem_id
            FROM inatividades i
            LEFT JOIN maquinas m ON m.id = i.maquina_id
            LEFT JOIN estados e ON e.id = i.estado_id
            LEFT JOIN utilizadores u ON u.id = i.user_id
            WHERE 1=1
        """
        params_inat = []
        if maquina_id is not None:
            sql_inat += " AND i.maquina_id = ?"
            params_inat.append(int(maquina_id))
        if data_de:
            sql_inat += " AND DATE(i.inicio) >= ?"
            params_inat.append(data_de)
        if data_ate:
            sql_inat += " AND DATE(i.inicio) <= ?"
            params_inat.append(data_ate)

        sql_final = f"""
            SELECT * FROM (
                {sql_registos}
                UNION ALL
                {sql_ordens}
                UNION ALL
                {sql_inat}
            )
            ORDER BY inicio DESC
        """
        params = params_reg + params_ord + params_inat
        return pd.read_sql_query(sql_final, conn, params=params)


def alterar_password(user_id, nova_password):
    """Atualiza a password de um utilizador."""
    import bcrypt
    h = bcrypt.hashpw(nova_password.encode(), bcrypt.gensalt()).decode()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE utilizadores SET password_hash = ? WHERE id = ?",
            (h, int(user_id))
        )
        conn.commit()
        return cur.rowcount
def contar_total():
    """Devolve contagens para o painel do admin."""
    with get_conn() as conn:
        n_prod = conn.execute("SELECT COUNT(*) FROM registos").fetchone()[0]
        n_maq  = conn.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0]
        n_user = conn.execute("SELECT COUNT(*) FROM utilizadores").fetchone()[0]
        return {"producoes": n_prod, "maquinas": n_maq, "utilizadores": n_user}