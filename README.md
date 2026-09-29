# Transaction Monitoring and Fraud Detection (Synthetic Data)

A small, readable project that shows how rule-based transaction monitoring works for a mobile money or digital lending setting. It builds a fake transaction table, runs four common fraud checks over it, turns the hits into an account risk score, and measures how well the alerts line up with the fraud I planted.

I work as a fraud analyst, and I wanted a public project that shows how I think about detection rules without touching any real customer or case data. Everything in here is generated from random numbers.

## What it does

1. **Generates data** (`src/generate_data.py`): 2,000 accounts over 60 days, roughly 50,000 transactions. About 5% of accounts behave like busy merchants (more volume, bigger amounts) so the rules have legitimate noise to deal with. 3% of accounts get one fraud pattern each.
2. **Runs four rules** (`src/rules.py`):
   - **Structuring**: 3 or more deposits between 85,000 and 100,000 KES inside 48 hours.
   - **Velocity**: 10 or more transactions from one account inside an hour.
   - **Pass-through**: a deposit of 200,000 KES or more where 90% or more leaves again within an hour.
   - **Night-time large movements**: 2 or more transfers of 50,000 KES or more between midnight and 5am within 24 hours.
3. **Scores accounts** (`src/score.py`): each rule counts once per account and carries a weight. A score of 40 or more opens a case. A score of 25 or more goes to a quick review queue.
4. **Checks the work**: the generator knows which accounts are fraudulent, so the pipeline reports precision, recall and false positive rate.
5. **SQL versions** (`sql/detection_queries.sql`): the structuring and velocity checks written in plain SQL. A test confirms the SQL and Python flag the same accounts.

## Run it

```bash
git clone https://github.com/Basuben/transaction-monitoring-fraud-detection.git
cd transaction-monitoring-fraud-detection
pip install -r requirements.txt
python -m src.run_pipeline
pytest
```

The pipeline prints the metrics and writes `outputs/transactions.csv`, `outputs/account_scores.csv` and `outputs/metrics.json`.

## Results on the default run (seed 42)

| View | Flagged accounts | Fraud caught | False alarms | Precision | Recall |
|---|---|---|---|---|---|
| Alerts (score 40+) | 30 | 30 of 60 | 0 | 1.00 | 0.50 |
| Review queue (score 25+) | 61 | 60 of 60 | 1 | 0.98 | 1.00 |

Structuring and pass-through accounts reach alert level on their own. Velocity and night-time patterns score 30 and 25 on their own, so they land in the review queue unless another rule also fires. That was a deliberate choice: those two patterns are also what a busy merchant can look like, and I would rather have an analyst glance at them than open a full case.

## Read these numbers carefully

The fraud in this dataset was written to match the rules, so the results look cleaner than anything you would see on real data. Treat them as proof that the pipeline works end to end, not as a claim about real-world accuracy. Real fraud is messier, labels are late and incomplete, and thresholds need tuning against actual customer behaviour.

## Ideas for next steps

- Tune thresholds against a labelled sample instead of picking them by hand.
- Add a rule for new accounts moving large amounts soon after opening.
- Add a simple model (logistic regression on account features) and compare it with the rules.
- Track alert volume per rule so noisy rules get spotted early.

## Layout

```
src/            data generator, rules, scoring, pipeline
sql/            SQL versions of two rules
tests/          unit tests and a SQL parity test
outputs/        generated files (ignored by git)
```

## About

Built by Collins Basuben, Nairobi, Kenya. Background in finance, fraud investigation and AML/CFT compliance. [LinkedIn](https://linkedin.com/in/collinsbasuben7b3568194)

Released under the MIT license.
