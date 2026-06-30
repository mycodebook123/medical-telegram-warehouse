-- Channel dimension, aggregating channel-level stats from staged messages

with channel_stats as (

    select
        channel_name,
        min(message_date)                  as first_post_date,
        max(message_date)                  as last_post_date,
        count(*)                            as total_posts,
        avg(views)                          as avg_views
    from {{ ref('stg_telegram_messages') }}
    group by channel_name

),

final as (

    select
        row_number() over (order by channel_name)        as channel_key,
        channel_name,
        case
            when channel_name = 'CheMed123' then 'Medical'
            when channel_name = 'lobelia4cosmetics' then 'Cosmetics'
            when channel_name = 'tikvahpharma1' then 'Pharmaceutical'
            else 'Other'
        end                                                as channel_type,
        first_post_date,
        last_post_date,
        total_posts,
        round(avg_views::numeric, 2)                       as avg_views
    from channel_stats

)

select * from final