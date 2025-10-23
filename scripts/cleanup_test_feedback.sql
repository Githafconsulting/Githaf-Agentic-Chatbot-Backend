-- =====================================================
-- Cleanup Test/Mock Feedback Data
-- Removes any test feedback entries from the database
-- Created: January 2025
-- =====================================================

-- This script will remove feedback entries that appear to be test data
-- Run this in your Supabase SQL Editor to clean up test data

-- Delete feedback with test-related comments
DELETE FROM feedback
WHERE comment LIKE '%test%'
   OR comment LIKE '%mock%'
   OR comment LIKE '%dummy%'
   OR comment LIKE '%example%';

-- Optional: If you want to remove ALL feedback and start fresh
-- Uncomment the following line (WARNING: This deletes ALL feedback!)
-- DELETE FROM feedback;

-- View remaining feedback count
SELECT
    COUNT(*) as total_feedback,
    COUNT(CASE WHEN rating = 0 THEN 1 END) as negative_feedback,
    COUNT(CASE WHEN rating = 1 THEN 1 END) as positive_feedback,
    COUNT(CASE WHEN comment IS NOT NULL THEN 1 END) as feedback_with_comments
FROM feedback;

-- Show feedback insights after cleanup
SELECT
    f.id,
    f.rating,
    f.comment,
    f.created_at,
    m.content as bot_response
FROM feedback f
LEFT JOIN messages m ON f.message_id = m.id
WHERE f.rating = 0
ORDER BY f.created_at DESC
LIMIT 10;
