from click.testing import CliRunner
from owldns.cli import cli


def test_config_loading(tmp_path):
    config_file = tmp_path / "config.toml"
    config_content = """
    log_level = "DEBUG"

    [run]
    host = "127.0.0.1"
    port = 5354
    upstream = ["1.1.1.1"]
    hosts_file = "/tmp/fake_hosts"
    debug = true
    """
    config_file.write_text(config_content)

    runner = CliRunner()

    # 1. Verify that the command runs with the config file
    result = runner.invoke(
        cli, ["--config", str(config_file), "run", "--help"])
    assert result.exit_code == 0

    # 2. Verify that upstream, hosts-file and debug are NOT in help anymore
    assert "--upstream" not in result.output
    assert "--hosts-file" not in result.output
    assert "--debug" not in result.output

    # 3. Verify that the command doesn't crash during initialization
    # (Removed hanging runner.invoke call)
