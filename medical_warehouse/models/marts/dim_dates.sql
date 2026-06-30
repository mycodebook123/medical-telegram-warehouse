-- Date dimension, generated from the range of message dates in the data

with date_spine as (

    select generate_series(
        (select min(message_date::date) from {{ ref('stg_telegram_messages') }}),
        (select max(message_date::date) from {{ ref('stg_telegram_messages') }}),
        interval '1 day'
    )::date as full_date

),

final as (

    select
        to_char(full_date, 'YYYYMMDD')::int          as date_key,
        full_date,
        extract(dow from full_date)::int               as day_of_week,
        to_char(full_date, 'Day')                       as day_name,
        extract(week from full_date)::int               as week_of_year,
        extract(month from full_date)::int              as month,
        to_char(full_date, 'Month')                      as month_name,
        extract(quarter from full_date)::int            as quarter,
        extract(year from full_date)::int               as year,
        case when extract(dow from full_date) in (0, 6) then true else false end as is_weekend
    from date_spine

)

select * from final