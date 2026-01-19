import pytest
from owldns.utils import load_hosts


def test_load_hosts_basic(tmp_path):
    hosts_content = """
    # Comments are ignored
    127.0.0.1  localhost mypc
    ::1        localhost
    192.168.1.5 server.local
    """
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text(hosts_content)

    records = load_hosts(str(hosts_file))

    assert records["localhost"] in ["127.0.0.1", "::1"]
    assert records["mypc"] == "127.0.0.1"
    assert records["server.local"] == "192.168.1.5"


def test_load_hosts_invalid_file():
    # Should not raise but return empty dict and print error
    records = load_hosts("non_existent_file")
    assert records == {}
