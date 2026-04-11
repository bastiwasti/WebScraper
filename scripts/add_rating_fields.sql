-- Add rating fields to events_distinct table (decimal ratings 1-5)
-- This script should be run manually before using the rating feature

ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_inhaltlich NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_ort NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_ausstattung NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_interaktion NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_kosten NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ADD COLUMN IF NOT EXISTS rating_reason TEXT;
