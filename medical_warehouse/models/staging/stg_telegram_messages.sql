-- Staging model: cleans and standardizes raw Telegram messages

with source as (

    select * from {{ source('raw', 'telegram_messages') }}

),

cleaned as (

    select
        message_id,
        channel_name,
        message_date::timestamp                       as message_date,
        trim(message_text)                             as message_text,
        coalesce(has_media, false)                      as has_media,
        image_path,
        coalesce(views, 0)                               as views,
        coalesce(forwards, 0)                            as forwards,
        length(trim(message_text))                       as message_length,
        case when image_path is not null then true else false end as has_image,
        loaded_at

    from source
    where message_text is not null
      and trim(message_text) != ''

)

select * from cleaned