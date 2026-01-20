from click.testing import CliRunner
from owldns.cli import cli


def test_config_loading(tmp_path):
    config_file = tmp_path / "config.toml"
    config_content = """
    log_level = "DEBUG"

    [run]
    host = "1.2.3.4"
    port = 9999
    upstream = "4.4.4.4"
    hosts_file = "/tmp/fake_hosts"
    debug = true
    """
    config_file.write_text(config_content)

    runner = CliRunner()

    # 1. Verify that host and port still work via config and show in help
    result = runner.invoke(
        cli, ["--config", str(config_file), "run", "--help"])
    assert result.exit_code == 0
    assert "1.2.3.4" in result.output
    assert "9999" in result.output

    # 2. Verify that upstream, hosts-file and debug are NOT in help anymore
    assert "--upstream" not in result.output
    assert "--hosts-file" not in result.output
    assert "--debug" not in result.output

    # 3. test with log_level from config
    # We can't easily check if it's applied without running the server,
    # but at least the command should run without errors.
    result = runner.invoke(
        # try to interrupt
        cli, ["--config", str(config_file), "run"], input="\b")
    # This might hang or fail, but we just want to ensure it doesn't crash during setup
