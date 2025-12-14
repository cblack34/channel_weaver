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
        """Test that app has the main command registered."""
        # The main command should be registered
        command_names = [cmd.name for cmd in app.registered_commands if hasattr(cmd, 'name')]
        callback_names = [cmd.callback.__name__ for cmd in app.registered_commands if hasattr(cmd, 'callback')]  # type: ignore[union-attr]

        # Either the command is named 'main' or has a callback named 'main'
        assert "main" in command_names or "main" in callback_names

    def test_app_command_callback_exists(self) -> None:
        """Test that the main command has proper callback."""
        # Find the main command
        main_command = None
        for cmd in app.registered_commands:
            if (hasattr(cmd, 'name') and cmd.name == "main") or \
               (hasattr(cmd, 'callback') and cmd.callback.__name__ == "main"):  # type: ignore[union-attr]
                main_command = cmd
                break

        assert main_command is not None
        assert hasattr(main_command, 'callback')
        assert main_command.callback is not None

    def test_app_callback_is_main_function(self) -> None:
        """Test that the callback is the main function."""
        # Find the main command callback
        callback = None
        for cmd in app.registered_commands:
            if hasattr(cmd, 'callback') and cmd.callback.__name__ == "main":  # type: ignore[union-attr]
                callback = cmd.callback
                break

        assert callback is not None
        assert callback.__name__ == "main"

        # Import main function to verify it's the same
        from src.cli.commands import main as main_func
        assert callback is main_func

    def test_app_imports(self) -> None:
        """Test that app imports are working correctly."""
        # This test ensures that all imports in app.py work
        # If there were import errors, the module wouldn't load
        assert app is not None
        assert hasattr(app, 'registered_commands')