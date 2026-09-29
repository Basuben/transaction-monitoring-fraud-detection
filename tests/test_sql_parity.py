"""The SQL versions of the rules should flag the same accounts as the Python versions."""
import re
import sqlite3
from pathlib import Path

from src.generate_data import generate
from src.rules import structuring, velocity


def _run_sql(df):
    conn = sqlite3.connect(":memory:")
    out = df[["txn_id", "account_id", "timestamp", "amount_kes", "txn_type"]].copy()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_sql("transactions", conn, index=False)
    sql = Path("sql/detection_queries.sql").read_text()
    sql = re.sub(r"--.*", "", sql)
    queries = [q.strip() for q in sql.split(";") if q.strip()]
    return [{r[0] for r in conn.execute(q)} for q in queries]


def test_sql_matches_python_rules():
    df = generate(n_accounts=300, days=30, seed=7)
    sql_struct, sql_vel = _run_sql(df)
    assert sql_struct == set(df.loc[structuring(df), "account_id"])
    assert sql_vel == set(df.loc[velocity(df), "account_id"])
    assert sql_struct and sql_vel
