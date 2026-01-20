from owldns.utils import parse_upstream_server


def test_parse_upstream_server_full():
    s = "server 1.1.1.1 --group china --proxy 127.0.0.1:1080"
    res = parse_upstream_server(s)
    assert res == {
        "address": "1.1.1.1",
        "group": "china",
        "proxy": "127.0.0.1:1080"
    }


def test_parse_upstream_server_no_proxy():
    s = "server 8.8.8.8 --group international"
    res = parse_upstream_server(s)
    assert res == {
        "address": "8.8.8.8",
        "group": "international",
        "proxy": None
    }


def test_parse_upstream_server_no_group():
    s = "server 9.9.9.9 --proxy 10.0.0.1:8080"
    res = parse_upstream_server(s)
    assert res == {
        "address": "9.9.9.9",
        "group": None,
        "proxy": "10.0.0.1:8080"
    }


def test_parse_upstream_server_basic():
    s = "server 114.114.114.114"
    res = parse_upstream_server(s)
    assert res == {
        "address": "114.114.114.114",
        "group": None,
        "proxy": None
    }


def test_parse_upstream_server_invalid():
    s = "invalid format"
    res = parse_upstream_server(s)
    assert res == {
        "address": None,
        "group": None,
        "proxy": None
    }


def test_load_config_with_upstreams_strict(tmp_path):
    from owldns.utils import load_config
    config_file = tmp_path / "config.toml"
    config_content = """
    [run]
    upstream = [
        "server 1.1.1.1 --group china",
        "8.8.8.8"
    ]
    """
    config_file.write_text(config_content)

    data = load_config(str(config_file))
    upstreams = data["run"]["upstream"]

    # "8.8.8.8" should be ignored now as it doesn't start with 'server '
    assert len(upstreams) == 1
    assert upstreams[0] == {"address": "1.1.1.1",
                            "group": "china", "proxy": None}
