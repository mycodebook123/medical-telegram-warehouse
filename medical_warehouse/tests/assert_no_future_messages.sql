-- Custom test: no message should have a date in the future.
-- This query must return 0 rows to pass.

select f.message_id, d.full_date
from {{ ref('fct_messages') }} f
join {{ ref('dim_dates') }} d on f.date_key = d.date_key
where d.full_date > current_date