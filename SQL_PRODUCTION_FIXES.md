# SQL Queries to Fix Production Database

**Date**: November 3, 2025
**Issue**: date and date_str fields mismatch in scrape_runs table
**Solution**: Update database to ensure consistent date formatting

---

## Overview

The production database has `date_str` values from the website headers that may not match the actual dates extracted from them. The code has been fixed, but you may want to update the historical data for consistency.

---

## SQL Queries

### Option 1: Extract date from date_str (Recommended)

This approach parses the `date_str` column (which contains "Sunday, Nov 03, 2024" format) and extracts the date portion.

```sql
-- Check current state first (optional)
SELECT id, date_str, run_at
FROM scrape_runs
ORDER BY run_at DESC
LIMIT 5;

-- Option 1A: PostgreSQL approach (parsing date_str)
-- This extracts the date from the date_str column assuming format: "Day, Mon DD, YYYY"
UPDATE scrape_runs
SET date_str = TO_CHAR(
    TO_TIMESTAMP(
        SUBSTRING(date_str FROM ',\s*(\w+\s+\d+,\s*\d+)'),
        'Mon DD, YYYY'
    ),
    'Day, Mon DD, YYYY'
)
WHERE date_str IS NOT NULL
AND date_str ~ '^\w+,\s*\w+\s+\d+,\s*\d+$';

-- Option 1B: Simpler alternative using run_at timestamp
-- This sets date_str to be derived from run_at (when scrape actually executed)
-- You might NOT want this since date_str represents website header (publication date)
-- UPDATE scrape_runs
-- SET date_str = TO_CHAR(run_at AT TIME ZONE 'UTC', 'Day, Mon DD, YYYY')
-- WHERE date_str IS NOT NULL;

-- Verify the update
SELECT id, date_str, run_at
FROM scrape_runs
ORDER BY run_at DESC
LIMIT 5;
```

### Option 2: Keep as-is (if website headers are correct)

If the website headers are the source of truth (tenders' actual release dates), don't change anything. The application now handles it correctly on read.

```sql
-- Just verify everything is consistent
SELECT id,
       date_str,
       run_at,
       COUNT(*) as tender_count
FROM scrape_runs
LEFT JOIN scraped_tender_queries ON scraped_tender_queries.scrape_run_id = scrape_runs.id
LEFT JOIN scraped_tenders ON scraped_tenders.query_id = scraped_tender_queries.id
GROUP BY scrape_runs.id, date_str, run_at
ORDER BY run_at DESC;
```

### Option 3: Manual inspection and selective updates

```sql
-- View all dates that have potential inconsistencies
SELECT
    id,
    date_str,
    run_at,
    -- Extract month/day/year from date_str for comparison
    CASE
        WHEN date_str ~ '\d+,\s*\d+$'
        THEN SUBSTRING(date_str FROM '\d+,\s*(\d+)$')
        ELSE 'PARSE_ERROR'
    END as extracted_day
FROM scrape_runs
WHERE date_str IS NOT NULL
ORDER BY run_at DESC
LIMIT 20;

-- Update specific records that you identify as wrong
UPDATE scrape_runs
SET date_str = 'Sunday, Nov 03, 2024'  -- Set to correct value
WHERE id = 'YOUR-UUID-HERE'
AND date_str = 'Saturday, Oct 25, 2025';  -- Old incorrect value
```

---

## Step-by-Step Instructions

### 1. Connect to PostgreSQL

```bash
# From your machine with psql access
psql -h <DATABASE_HOST> -U <USERNAME> -d <DATABASE_NAME> -p 5432

# Or use your existing connection method
```

### 2. Check Current State

```sql
-- See the first few records with potential date mismatch
SELECT
    id,
    date_str,
    run_at,
    (SELECT COUNT(*) FROM scraped_tender_queries WHERE scrape_run_id = scrape_runs.id) as query_count,
    (SELECT COUNT(*) FROM scraped_tenders
     WHERE query_id IN (SELECT id FROM scraped_tender_queries WHERE scrape_run_id = scrape_runs.id)
    ) as tender_count
FROM scrape_runs
ORDER BY run_at DESC
LIMIT 10;

-- Count how many need updating
SELECT COUNT(*) as total_scrape_runs FROM scrape_runs;
```

### 3. Backup Before Updating (Recommended)

```sql
-- Create a backup table with current state
CREATE TABLE scrape_runs_backup_2025_11_03 AS SELECT * FROM scrape_runs;

-- Verify backup created
SELECT COUNT(*) FROM scrape_runs_backup_2025_11_03;
```

### 4. Apply the Fix

**Option A: If date_str format is consistent ("Sunday, Nov 03, 2024" style):**

```sql
-- This validates format and updates only valid entries
UPDATE scrape_runs
SET date_str = TO_CHAR(
    TO_DATE(
        -- Extract the date part: "Nov 03, 2024" from "Sunday, Nov 03, 2024"
        SUBSTRING(date_str FROM ',\s*(.+)$'),
        'Mon DD, YYYY'
    ),
    'Day, Mon DD, YYYY'
)
WHERE date_str IS NOT NULL
AND date_str ~ '^\w+,\s+\w+\s+\d{1,2},\s+\d{4}$'
AND date_str NOT LIKE '%' || TO_CHAR(run_at, 'Mon DD, YYYY') || '%';
```

**Option B: Simple validation without changes:**

```sql
-- Just verify consistency without modifying
SELECT
    id,
    date_str,
    TO_CHAR(run_at, 'Day, Mon DD, YYYY') as derived_from_run_at,
    CASE
        WHEN date_str ~ '\w+,\s+\w+\s+\d{1,2},\s+\d{4}'
        THEN 'VALID_FORMAT'
        ELSE 'INVALID_FORMAT'
    END as format_status
FROM scrape_runs
ORDER BY run_at DESC
LIMIT 20;
```

### 5. Verify Changes

```sql
-- Check updated records
SELECT
    id,
    date_str,
    run_at,
    TO_CHAR(run_at, 'Day, Mon DD, YYYY') as expected_format
FROM scrape_runs
WHERE date_str IS NOT NULL
ORDER BY run_at DESC
LIMIT 10;

-- Count changes
SELECT COUNT(*) as updated_records FROM scrape_runs WHERE date_str IS NOT NULL;
```

### 6. Rollback if Needed

```sql
-- If something went wrong, restore from backup
TRUNCATE TABLE scrape_runs CASCADE;
INSERT INTO scrape_runs SELECT * FROM scrape_runs_backup_2025_11_03;

-- Clean up after verification
DROP TABLE scrape_runs_backup_2025_11_03;
```

---

## Important Notes

### ⚠️ Before Running Any Updates

1. **Backup First**: Always create `scrape_runs_backup_YYYY_MM_DD` before modifications
2. **Test on Staging**: Run queries on staging environment first
3. **Off-Peak Hours**: Execute updates during low-traffic periods
4. **Verify Format**: Check sample records to confirm date_str format

### 📋 Format Reference

**Input Format** (current in database):
```
"Sunday, Nov 02, 2025"
"Saturday, Oct 25, 2025"
```

**What Code Expects** (after parsing):
```
Date: 2025-11-02 (YYYY-MM-DD)
Date_str: "Sunday, Nov 02, 2025" (Day, Mon DD, YYYY)
```

### ✅ Validation Checklist

After running updates:
- [ ] Backup created successfully
- [ ] SELECT query shows consistent formats
- [ ] UPDATE completed without errors
- [ ] Verification query shows expected results
- [ ] API /dates endpoint returns correct data
- [ ] Frontend date selector displays correctly

---

## Why the Database State Matters

The `date_str` column represents **when the tenders were released** (from website header), while `run_at` represents **when the scraper ran**. These can be different:

| Field | Represents | Example |
|-------|-----------|---------|
| `date_str` | Website publication date | "Saturday, Oct 25, 2025" (tender release) |
| `run_at` | Actual scrape execution time | 2025-11-03 09:45:43 (when scraper ran) |
| `date` (API) | Extracted from date_str | "2025-10-25" (YYYY-MM-DD format) |

So for the most part, **you should NOT change existing date_str values** unless they're actually malformed. The application now correctly handles this.

---

## If You Have Issues

### Issue: Parse errors with unusual date formats

```sql
-- View all unique date_str formats to identify problems
SELECT DISTINCT date_str, COUNT(*) as count
FROM scrape_runs
WHERE date_str IS NOT NULL
GROUP BY date_str
ORDER BY count DESC;

-- Find records with problematic formats
SELECT id, date_str, run_at
FROM scrape_runs
WHERE date_str NOT REGEXP '^\w+,\s+\w+\s+\d+,\s+\d{4}$'
ORDER BY run_at DESC;
```

### Issue: Too many records to update

```sql
-- Update in batches (safer for large tables)
-- Batch 1: Update first 1000 records
UPDATE scrape_runs
SET date_str = ... -- your update logic here
WHERE id IN (
    SELECT id FROM scrape_runs
    WHERE date_str IS NOT NULL
    ORDER BY run_at DESC
    LIMIT 1000
);

-- Batch 2: Update next 1000, etc.
UPDATE scrape_runs
SET date_str = ... -- your update logic here
WHERE id IN (
    SELECT id FROM scrape_runs
    WHERE date_str IS NOT NULL
    ORDER BY run_at DESC
    LIMIT 1000 OFFSET 1000
);
```

---

## Recommendation

Since the application code now correctly handles date parsing from `date_str`, **you can optionally leave the database unchanged**. The API will return consistent dates regardless.

However, if you want the database to be "clean" for future audits, use **Option 1A** above to standardize the format.

---

## Testing the Fix

After any changes, verify with this query:

```sql
-- Test: Get dates for API response
SELECT
    id,
    date_str as "date_str (website header)",
    run_at as "run_at (scrape time)",
    TO_CHAR(run_at, 'YYYY-MM-DD') as "date (in API response)",
    (SELECT COUNT(*) FROM scraped_tender_queries WHERE scrape_run_id = scrape_runs.id) as "query_count"
FROM scrape_runs
WHERE date_str IS NOT NULL
ORDER BY run_at DESC
LIMIT 5;

-- Expected output:
-- date_str should be readable date: "Sunday, Nov 03, 2025"
-- run_at should be timestamp: "2025-11-03 09:45:43.113847"
-- date (API) should be: "2025-11-03"
```

---

*Last updated: November 3, 2025*
*For questions, refer to TENDERIQ_DATE_CONSISTENCY_FIX.md*
