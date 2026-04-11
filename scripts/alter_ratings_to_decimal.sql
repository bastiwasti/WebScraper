-- Alter rating columns in event_ratings table to use NUMERIC(3,1) for decimal ratings
-- This script should be run after the existing event_ratings table is created

ALTER TABLE webscraper.event_ratings ALTER COLUMN rating TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_inhaltlich TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ort TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ausstattung TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_interaktion TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_kosten TYPE NUMERIC(3,1);

-- Also alter the rating column in events_distinct table
ALTER TABLE webscraper.events_distinct ALTER COLUMN rating TYPE NUMERIC(3,1);
