-- The same checks as src/rules.py, written in plain SQL (tested on SQLite).
-- Table: transactions(txn_id, account_id, timestamp, amount_kes, txn_type)
-- timestamp format: 'YYYY-MM-DD HH:MM:SS'

-- 1. Structuring: 3 or more deposits between 85,000 and 100,000 KES within 48 hours
SELECT DISTINCT account_id FROM (
  SELECT a.account_id, a.txn_id
  FROM transactions a
  JOIN transactions b
    ON b.account_id = a.account_id
   AND b.txn_type = 'deposit'
   AND b.amount_kes >= 85000 AND b.amount_kes < 100000
   AND b.timestamp BETWEEN datetime(a.timestamp, '-48 hours') AND a.timestamp
  WHERE a.txn_type = 'deposit'
    AND a.amount_kes >= 85000 AND a.amount_kes < 100000
  GROUP BY a.account_id, a.txn_id
  HAVING COUNT(*) >= 3
);

-- 2. Velocity: 10 or more transactions from one account within an hour
SELECT DISTINCT account_id FROM (
  SELECT a.account_id, a.txn_id
  FROM transactions a
  JOIN transactions b
    ON b.account_id = a.account_id
   AND b.timestamp BETWEEN datetime(a.timestamp, '-1 hours') AND a.timestamp
  GROUP BY a.account_id, a.txn_id
  HAVING COUNT(*) >= 10
);
