import pytest

from fantech_he68.framework import LightingProtocol, UnsupportedProtocolFeature


def test_unknown_lighting_feature_refuses_to_send_a_command() -> None:
    with pytest.raises(UnsupportedProtocolFeature, match="requires an experimentally captured"):
        LightingProtocol().set_effect("breathing")
