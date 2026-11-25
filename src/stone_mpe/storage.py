"""SQLite é a fonte única consultada pelo agente; Parquet é o artefato analítico."""
from __future__ import annotations

import sqlite3

import pandas as pd

from stone_mpe import config

CATEG_DDL = """
CREATE TABLE IF NOT EXISTS categorizations (
  post_id TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model TEXT,
  input_modalities TEXT,
  valid INTEGER NOT NULL,
  error TEXT,
  raw_json TEXT,
  created_at TEXT,
  tipo_post TEXT, duracao_faixa TEXT, formato_video TEXT,
  hook_primeiros_3s TEXT, tipo_hook TEXT, forca_hook_0a10 INTEGER,
  tema_principal TEXT,
  tem_rosto INTEGER, criador_e_empreendedor_real INTEGER, prova_social INTEGER,
  texto_na_tela INTEGER, legenda_tamanho TEXT, ritmo_cortes_0a10 INTEGER,
  tom TEXT, usa_linguagem_regional INTEGER, clareza_mensagem_0a10 INTEGER,
  tem_cta INTEGER, tipo_cta TEXT, oferta_ou_beneficio_explicito INTEGER,
  elementos_top5 TEXT,
  PRIMARY KEY (post_id, prompt_version)
)
"""


def categ_join(alias: str = "c") -> tuple[str, tuple]:
    """JOIN com a melhor categorização válida por post: Nível 2 se existir, senão Nível 1."""
    l1 = config.get("categorization.prompt_version", "v1")
    l2 = config.get("level2.prompt_version", "v1-n2")
    sql = f"""JOIN (SELECT * FROM categorizations x WHERE x.valid = 1 AND (x.prompt_version = ? OR
                  (x.prompt_version = ? AND NOT EXISTS (SELECT 1 FROM categorizations y
                   WHERE y.post_id = x.post_id AND y.valid = 1 AND y.prompt_version = ?)))) {alias}
              ON {alias}.post_id = p.post_id"""
    return sql, (l2, l1, l2)


def connect() -> sqlite3.Connection:
    p = config.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.execute(CATEG_DDL)
    return conn


def write_table(df: pd.DataFrame, name: str) -> None:
    with connect() as conn:
        df.to_sql(name, conn, if_exists="replace", index=False)


def read_sql(sql: str, params: tuple | dict = ()) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def table_exists(name: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None
