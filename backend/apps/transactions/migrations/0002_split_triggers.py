"""PostgreSQL triggers for transaction split total integrity and audit immutability."""

from django.db import migrations

SQL_TRIGGERS = """
-- 1. Deferred constraint trigger to ensure splits sum to transaction total
CREATE OR REPLACE FUNCTION assert_split_total()
RETURNS TRIGGER AS $$
DECLARE
    tx_row RECORD;
    splits_sum BIGINT;
    target_tx_id UUID;
BEGIN
    target_tx_id := COALESCE(NEW.transaction_id, OLD.transaction_id);
    SELECT id, is_split, amount_minor INTO tx_row FROM txn_transaction WHERE id = target_tx_id;
    IF tx_row.is_split THEN
        SELECT COALESCE(SUM(amount_minor), 0) INTO splits_sum
        FROM txn_transaction_split
        WHERE transaction_id = target_tx_id;

        IF splits_sum <> tx_row.amount_minor THEN
            RAISE EXCEPTION 'Splits total % does not match transaction % amount %',
                splits_sum, tx_row.id, tx_row.amount_minor;
        END IF;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_assert_split_total ON txn_transaction_split;
CREATE CONSTRAINT TRIGGER trg_assert_split_total
AFTER INSERT OR UPDATE OR DELETE ON txn_transaction_split
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION assert_split_total();

-- 2. Audit log immutability trigger
CREATE OR REPLACE FUNCTION reject_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Transaction audit logs are append-only and cannot be modified or deleted.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reject_audit_mutation ON txn_transaction_audit;
CREATE TRIGGER trg_reject_audit_mutation
BEFORE UPDATE OR DELETE ON txn_transaction_audit
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
"""

SQL_REVERSE = """
DROP TRIGGER IF EXISTS trg_reject_audit_mutation ON txn_transaction_audit;
DROP FUNCTION IF EXISTS reject_audit_mutation();
DROP TRIGGER IF EXISTS trg_assert_split_total ON txn_transaction_split;
DROP FUNCTION IF EXISTS assert_split_total();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SQL_TRIGGERS, SQL_REVERSE),
    ]
