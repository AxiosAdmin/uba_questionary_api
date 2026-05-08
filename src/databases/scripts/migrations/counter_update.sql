ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS questions_generated_in_cycle INTEGER NOT NULL DEFAULT 0;

ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS questions_generation_cycle_end TIMESTAMP DEFAULT NULL;

UPDATE subscriptions
SET questions_generation_cycle_end = current_period_end
WHERE questions_generation_cycle_end IS NULL;
