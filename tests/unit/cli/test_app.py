"""Unit tests for CLI app configuration."""

from __future__ import annotations


from src.cli.app import app


class TestAppConfiguration:
    """Tests for Typer app configuration."""

    def test_app_is_typer_instance(self) -> None:
        """Test that app is a Typer instance."""
        import typer
        assert isinstance(app, typer.Typer)

    def test_app_has_registered_commands(self) -> None:
        """Test that app has registered commands."""
        assert hasattr(app, 'registered_commands')
        assert len(app.registered_commands) > 0

    def test_app_has_main_command(self) -> None:
        """Test that app has the process command registered."""
        # The process command should be registered
        command_names = [cmd.name for cmd in app.registered_commands if hasattr(cmd, 'name')]
        callback_names = [cmd.callback.__name__ for cmd in app.registered_commands if hasattr(cmd, 'callback')]  # type: ignore[union-attr]

        # Either the command is named 'process' or has a callback named 'process'
        assert "process" in command_names or "process" in callback_names

    def test_app_command_callback_exists(self) -> None:
        """Test that the process command has proper callback."""
        # Find the process command
        process_command = None
        for cmd in app.registered_commands:
            if (hasattr(cmd, 'name') and cmd.name == "process") or \
               (hasattr(cmd, 'callback') and cmd.callback.__name__ == "process"):  # type: ignore[union-attr]
                process_command = cmd
                break

        assert process_command is not None
        assert hasattr(process_command, 'callback')
        assert process_command.callback is not None

    def test_app_callback_is_main_function(self) -> None:
        """Test that the callback is the main function."""
        # Find the main command callback
        callback = None
        for cmd in app.registered_commands:
            if hasattr(cmd, 'callback') and cmd.callback.__name__ == "process":  # type: ignore[union-attr]
                callback = cmd.callback
                break

        assert callback is not None
        assert callback.__name__ == "process"

        # Import process function to verify it's the same
        from src.cli.commands import process as process_func
        assert callback is process_func

    def test_app_imports(self) -> None:
        """Test that app imports are working correctly."""
        # This test ensures that all imports in app.py work
        # If there were import errors, the module wouldn't load
        assert app is not None
        assert hasattr(app, 'registered_commands')