from wechat_link.models import InboundMediaRef, InboundMessageItem, WeixinMessage


def test_weixin_message_parses_image_file_video_and_voice_items() -> None:
    message = WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "to_user_id": "bot@im.bot",
            "context_token": "ctx-1",
            "item_list": [
                {
                    "type": 2,
                    "image_item": {
                        "media": {
                            "encrypt_query_param": "image-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "mid_size": 32,
                    },
                },
                {
                    "type": 4,
                    "file_item": {
                        "media": {
                            "encrypt_query_param": "file-download-param",
                        },
                        "file_name": "report.md",
                        "len": "18",
                    },
                },
                {
                    "type": 5,
                    "video_item": {
                        "media": {
                            "encrypt_query_param": "video-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "video_size": 64,
                        "thumb_media": {
                            "encrypt_query_param": "thumb-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "thumb_size": 16,
                        "thumb_width": 120,
                        "thumb_height": 80,
                    },
                },
                {
                    "type": 3,
                    "voice_item": {
                        "media": {
                            "encrypt_query_param": "voice-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "encode_type": 6,
                        "sample_rate": 16000,
                        "playtime": 1200,
                        "text": "voice transcript",
                    },
                },
            ],
        }
    )

    items = message.items()

    assert [item.kind for item in items] == ["image", "file", "video", "voice"]
    assert items[0].media == InboundMediaRef(
        encrypt_query_param="image-download-param",
        aes_key="MDEyMzQ1Njc4OWFiY2RlZg==",
        encrypt_type=1,
    )
    assert items[0].size == 32
    assert items[1].file_name == "report.md"
    assert items[1].size == 18
    assert items[2].thumb_media == InboundMediaRef(
        encrypt_query_param="thumb-download-param",
        aes_key="MDEyMzQ1Njc4OWFiY2RlZg==",
        encrypt_type=1,
    )
    assert items[2].width == 120
    assert items[2].height == 80
    assert items[3].text == "voice transcript"
    assert items[3].sample_rate == 16000
    assert message.media_items() == items


def test_weixin_message_kind_prefers_text_but_exposes_media_items() -> None:
    message = WeixinMessage.from_dict(
        {
            "item_list": [
                {"type": 1, "text_item": {"text": "hello"}},
                {
                    "type": 2,
                    "image_item": {
                        "media": {
                            "encrypt_query_param": "image-download-param",
                        }
                    },
                },
            ]
        }
    )

    items = message.items()

    assert message.kind() == "text"
    assert message.text() == "hello"
    assert items[0] == InboundMessageItem(kind="text", type=1, text="hello")
    assert [item.kind for item in message.media_items()] == ["image"]
