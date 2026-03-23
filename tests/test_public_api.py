import wechat_link
from wechat_link import Client
from wechat_link.client import Client as ClientFromModule


def test_top_level_exports_client():
    assert Client is ClientFromModule
    assert Client.__name__ == "Client"


def test_legacy_client_name_is_not_exported():
    assert not hasattr(wechat_link, "WeChatLinkClient")
