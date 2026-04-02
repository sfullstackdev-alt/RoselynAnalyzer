"""Tests for main module."""

from roselyn_analyzer import main, __version__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_main(capsys):
    """Test main function output."""
    main()
    captured = capsys.readouterr()
    assert "Welcome to Roselyn Analyzer!" in captured.out
