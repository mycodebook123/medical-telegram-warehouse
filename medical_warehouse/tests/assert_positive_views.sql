-- Custom test: view counts and forward counts must be non-negative.
-- This query must return 0 rows to pass.

select message_id, views, forwards
from {{ ref('fct_messages') }}
where views < 0 or forwards < 0