"""PostgreSQL constraint triggers for ledger integrity:
1. Immutability of posted journal entries.
2. Deferred balance assertion: sum of postings per currency must be zero for posted entries.
3. Deferred posting currency assertion: posting currency must match ledger account currency.
"""

from django.db import migrations

SQL_TRIGGERS = """
-- 1. Immutability trigger on journal_entry
CREATE OR REPLACE FUNCTION reject_posted_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'posted' THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Posted journal entries cannot be deleted (entry %)', OLD.id;
        ELSIF TG_OP = 'UPDATE' THEN
            IF NEW.status = 'reversed' AND NEW.reversed_by_entry_id IS NOT NULL THEN
                IF NEW.effective_date <> OLD.effective_date OR
                   NEW.entry_type <> OLD.entry_type OR
                   NEW.workspace_id <> OLD.workspace_id OR
                   NEW.ledger_seq <> OLD.ledger_seq THEN
                    RAISE EXCEPTION 'Only status and reversed_by_entry_id may be updated when reversing (entry %)', OLD.id;
                END IF;
            ELSE
                RAISE EXCEPTION 'Posted journal entries are immutable (entry %)', OLD.id;
            END IF;
        END IF;
    ELSIF OLD.status = 'reversed' THEN
        RAISE EXCEPTION 'Reversed journal entries are immutable (entry %)', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reject_posted_entry_mutation ON journal_entry;
CREATE TRIGGER trg_reject_posted_entry_mutation
BEFORE UPDATE OR DELETE ON journal_entry
FOR EACH ROW EXECUTE FUNCTION reject_posted_entry_mutation();


-- 2. Deferred constraint trigger to ensure balanced journal entries per currency
CREATE OR REPLACE FUNCTION assert_journal_entry_balances()
RETURNS TRIGGER AS $$
DECLARE
    unbalanced_record RECORD;
    entry_row RECORD;
BEGIN
    SELECT status, id INTO entry_row FROM journal_entry WHERE id = NEW.journal_entry_id;
    IF entry_row.status = 'posted' THEN
        FOR unbalanced_record IN
            SELECT currency_code, SUM(amount_minor) AS balance
            FROM posting
            WHERE journal_entry_id = NEW.journal_entry_id
            GROUP BY currency_code
            HAVING SUM(amount_minor) <> 0
        LOOP
            RAISE EXCEPTION 'Journal entry % is unbalanced for currency %: sum = %',
                entry_row.id, unbalanced_record.currency_code, unbalanced_record.balance;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_assert_journal_entry_balances ON posting;
CREATE CONSTRAINT TRIGGER trg_assert_journal_entry_balances
AFTER INSERT OR UPDATE ON posting
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION assert_journal_entry_balances();


-- 3. Deferred constraint trigger to ensure posting currency matches ledger account currency
CREATE OR REPLACE FUNCTION assert_posting_currency()
RETURNS TRIGGER AS $$
DECLARE
    acc_currency CHAR(3);
BEGIN
    SELECT currency_code INTO acc_currency FROM ledger_account WHERE id = NEW.ledger_account_id;
    IF acc_currency <> NEW.currency_code THEN
        RAISE EXCEPTION 'Posting currency % does not match ledger account % currency %',
            NEW.currency_code, NEW.ledger_account_id, acc_currency;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_assert_posting_currency ON posting;
CREATE CONSTRAINT TRIGGER trg_assert_posting_currency
AFTER INSERT OR UPDATE ON posting
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION assert_posting_currency();
"""

SQL_REVERSE = """
DROP TRIGGER IF EXISTS trg_assert_posting_currency ON posting;
DROP FUNCTION IF EXISTS assert_posting_currency();
DROP TRIGGER IF EXISTS trg_assert_journal_entry_balances ON posting;
DROP FUNCTION IF EXISTS assert_journal_entry_balances();
DROP TRIGGER IF EXISTS trg_reject_posted_entry_mutation ON journal_entry;
DROP FUNCTION IF EXISTS reject_posted_entry_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SQL_TRIGGERS, SQL_REVERSE),
    ]
