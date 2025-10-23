-- =====================================================
-- Cleanup Duplicate Feedback Data
-- Removes duplicate feedback entries while keeping one
-- Created: January 15, 2025
-- =====================================================

-- View the duplicates before deletion
SELECT
    message_id,
    comment,
    COUNT(*) as duplicate_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM feedback
WHERE comment = 'it should provide answers about githaf''s services rather than redirecting me to website and terms of service.'
GROUP BY message_id, comment
HAVING COUNT(*) > 1;

-- Delete duplicate entries, keeping only the earliest one
DELETE FROM feedback
WHERE id IN (
    SELECT id
    FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY message_id, comment
                ORDER BY created_at ASC
            ) as rn
        FROM feedback
        WHERE comment = 'it should provide answers about githaf''s services rather than redirecting me to website and terms of service.'
    ) t
    WHERE rn > 1
);

-- View remaining feedback statistics
SELECT
    COUNT(*) as total_feedback,
    COUNT(CASE WHEN rating = 0 THEN 1 END) as negative_feedback,
    COUNT(CASE WHEN rating = 1 THEN 1 END) as positive_feedback,
    COUNT(CASE WHEN comment IS NOT NULL THEN 1 END) as feedback_with_comments,
    COUNT(CASE WHEN comment IS NULL THEN 1 END) as feedback_without_comments
FROM feedback;

-- Show remaining negative feedback with comments
SELECT
    f.id,
    f.rating,
    f.comment,
    f.created_at,
    m.content as bot_response
FROM feedback f
LEFT JOIN messages m ON f.message_id = m.id
WHERE f.rating = 0 AND f.comment IS NOT NULL
ORDER BY f.created_at DESC
LIMIT 10;
