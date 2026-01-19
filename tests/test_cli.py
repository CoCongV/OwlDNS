from unittest.mock import patch, MagicMock
from owldns.cli import main


def test_cli_parsing_records():
    # Mocking argparse.ArgumentParser.parse_args
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        mock_parse.return_value = MagicMock(
            host="127.0.0.1",
            port=5353,
            upstream="8.8.8.8",
            record=["test.com=1.1.1.1"],
            reload=False,
            hosts_file=None
        )

        # Mocking OwlDNSServer.start and asyncio.run to avoid real running
        with patch('owldns.cli.OwlDNSServer') as mock_server:
            with patch('asyncio.run') as mock_run:
                main()

                # Check if server was initialized with correct records
                mock_server.assert_called_once_with(
                    host="127.0.0.1",
                    port=5353,
                    records={"test.com": "1.1.1.1"},
                    upstream="8.8.8.8",
                    hosts_file=None
                )
                mock_run.assert_called_once()


def test_cli_default_records():
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        mock_parse.return_value = MagicMock(
            host="127.0.0.1",
            port=5353,
            upstream="8.8.8.8",
            record=None,
            reload=False,
            hosts_file=None
        )
        with patch('owldns.cli.OwlDNSServer') as mock_server:
            with patch('asyncio.run'):
                main()
                assert mock_server.call_args[1]['records'] == {
                    "example.com": "1.2.3.4"}


def test_cli_exception_handling():
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        mock_parse.return_value = MagicMock(
            host="127.0.0.1",
            port=5353,
            upstream="8.8.8.8",
            record=None,
            reload=False,
            hosts_file=None
        )
        with patch('owldns.cli.OwlDNSServer'):
            with patch('asyncio.run') as mock_run:
                mock_run.side_effect = Exception("Runtime error")
                # This should catch the exception and print it
                main()


def test_cli_invalid_record_format():
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        mock_parse.return_value = MagicMock(
            host="127.0.0.1",
            port=5353,
            upstream="8.8.8.8",
            record=["invalid_format"],
            reload=False,
            hosts_file=None
        )
        with patch('owldns.cli.OwlDNSServer'):
            with patch('asyncio.run'):
                # Should print warning (lines 37-38)
                main()
