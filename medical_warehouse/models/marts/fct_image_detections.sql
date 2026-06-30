-- Image detection fact table: joins YOLO detection results with messages,
-- linking each detection back to its channel and date dimensions.

with detections as (

    select * from {{ source('raw', 'yolo_detections') }}

),

final as (

    select
        d.message_id,
        c.channel_key,
        f.date_key,
        d.detected_class,
        d.confidence_score,
        d.image_category
    from detections d
    left join {{ ref('fct_messages') }} f
        on d.message_id = f.message_id
    left join {{ ref('dim_channels') }} c
        on d.channel_name = c.channel_name

)

select * from final