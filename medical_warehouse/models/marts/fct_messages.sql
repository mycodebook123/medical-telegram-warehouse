-- Fact table: one row per message, linked to channel and date dimensions

with messages as (

    select * from {{ ref('stg_telegram_messages') }}

),

final as (

    select
        m.message_id,
        c.channel_key,
        to_char(m.message_date::date, 'YYYYMMDD')::int    as date_key,
        m.message_text,
        m.message_length,
        m.views,
        m.forwards,
        m.has_image
    from messages m
    left join {{ ref('dim_channels') }} c
        on m.channel_name = c.channel_name

)

select * from final