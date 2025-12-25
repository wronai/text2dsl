"""
Testy dla DSL Parser
"""

import pytest
from text2dsl.core.dsl_parser import DSLParser, ParsedCommand, CommandType


class TestDSLParser:
    """Testy parsera DSL"""
    
    def setup_method(self):
        self.parser = DSLParser()
    
    # ==================== Make Commands ====================
    
    def test_parse_make_build(self):
        """Test parsowania 'zbuduj'"""
        result = self.parser.parse("zbuduj")
        assert result.type == CommandType.MAKE
        assert result.action == "build"
    
    def test_parse_make_build_english(self):
        """Test parsowania 'build'"""
        result = self.parser.parse("build")
        assert result.type == CommandType.MAKE
        assert result.action == "build"
    
    def test_parse_make_test(self):
        """Test parsowania 'testy'"""
        result = self.parser.parse("testy")
        assert result.type == CommandType.MAKE
        assert result.action == "test"

    def test_parse_make_run_tests_phrase(self):
        """Test parsowania 'uruchom testy'"""
        result = self.parser.parse("uruchom testy")
        assert result.type == CommandType.MAKE
        assert result.action == "test"
    
    def test_parse_make_clean(self):
        """Test parsowania 'wyczyść'"""
        result = self.parser.parse("wyczyść")
        assert result.type == CommandType.MAKE
        assert result.action == "clean"
    
    def test_parse_make_target(self):
        """Test parsowania celu make"""
        result = self.parser.parse("uruchom cel install")
        assert result.type == CommandType.MAKE
        assert result.target == "install"
    
    # ==================== Git Commands ====================
    
    def test_parse_git_status(self):
        """Test parsowania 'status'"""
        result = self.parser.parse("status")
        assert result.type == CommandType.GIT
        assert result.action == "status"
    
    def test_parse_git_commit(self):
        """Test parsowania 'zatwierdź'"""
        result = self.parser.parse("zatwierdź")
        assert result.type == CommandType.GIT
        assert result.action == "commit"
    
    def test_parse_git_push(self):
        """Test parsowania 'wypchnij'"""
        result = self.parser.parse("wypchnij")
        assert result.type == CommandType.GIT
        assert result.action == "push"
    
    def test_parse_git_pull(self):
        """Test parsowania 'pobierz'"""
        result = self.parser.parse("pobierz")
        assert result.type == CommandType.GIT
        assert result.action == "pull"
    
    def test_parse_git_branch(self):
        """Test parsowania 'gałąź'"""
        result = self.parser.parse("gałąź develop")
        assert result.type == CommandType.GIT
        assert result.action == "branch"
        assert result.target == "develop"
    
    def test_parse_git_checkout(self):
        """Test parsowania 'przełącz'"""
        result = self.parser.parse("przełącz main")
        assert result.type == CommandType.GIT
        assert result.action == "checkout"
        assert result.target == "main"
    
    # ==================== Docker Commands ====================
    
    def test_parse_docker_ps(self):
        """Test parsowania 'kontenery'"""
        result = self.parser.parse("kontenery")
        assert result.type == CommandType.DOCKER
        assert result.action == "ps"
    
    def test_parse_docker_build(self):
        """Test parsowania 'zbuduj obraz'"""
        result = self.parser.parse("zbuduj obraz myapp")
        assert result.type == CommandType.DOCKER
        assert result.action == "build"
        assert result.target == "myapp"
    
    def test_parse_docker_compose(self):
        """Test parsowania 'compose up'"""
        result = self.parser.parse("compose up")
        assert result.type == CommandType.DOCKER
        assert result.action == "compose"
    
    # ==================== Python Commands ====================
    
    def test_parse_python_script(self):
        """Test parsowania 'uruchom skrypt'"""
        result = self.parser.parse("uruchom skrypt main.py")
        assert result.type == CommandType.PYTHON
        assert result.action == "run"
        assert result.target == "main.py"
    
    def test_parse_python_pip(self):
        """Test parsowania 'pip install'"""
        result = self.parser.parse("pip install requests")
        assert result.type == CommandType.PYTHON
        assert result.action == "pip"
    
    def test_parse_python_pytest(self):
        """Test parsowania 'pytest'"""
        result = self.parser.parse("pytest")
        assert result.type == CommandType.PYTHON
        assert result.action == "test"
    
    # ==================== Context Commands ====================
    
    def test_parse_context_next(self):
        """Test parsowania 'dalej'"""
        result = self.parser.parse("dalej")
        assert result.type == CommandType.CONTEXT
        assert result.action == "next"
    
    def test_parse_context_repeat(self):
        """Test parsowania 'powtórz'"""
        # Najpierw wykonaj komendę
        self.parser.parse("zbuduj")
        
        result = self.parser.parse("powtórz")
        assert result.type == CommandType.MAKE  # Powtórzona komenda
    
    def test_parse_context_cancel(self):
        """Test parsowania 'anuluj'"""
        result = self.parser.parse("anuluj")
        assert result.type == CommandType.CONTEXT
        assert result.action == "cancel"
    
    def test_parse_context_confirm(self):
        """Test parsowania 'tak'"""
        result = self.parser.parse("tak")
        assert result.type == CommandType.CONTEXT
        assert result.action == "confirm"
    
    # ==================== Query Commands ====================
    
    def test_parse_query_options(self):
        """Test parsowania 'co mogę zrobić'"""
        result = self.parser.parse("co mogę zrobić?")
        assert result.type == CommandType.QUERY
        assert result.action == "options"
    
    def test_parse_query_help(self):
        """Test parsowania 'pomoc'"""
        result = self.parser.parse("pomoc")
        assert result.type == CommandType.QUERY
        assert result.action == "help"
    
    # ==================== Shell Fallback ====================
    
    def test_parse_shell_ls(self):
        """Test parsowania 'lista plików'"""
        result = self.parser.parse("lista plików")
        # Powinno być rozpoznane jako shell
        assert result.type in [CommandType.SHELL, CommandType.QUERY]
    
    def test_parse_unknown_command(self):
        """Test parsowania nieznanej komendy"""
        result = self.parser.parse("some random command")
        assert result.confidence < 0.5  # Niska pewność
    
    # ==================== Normalization ====================
    
    def test_normalize_case(self):
        """Test normalizacji wielkości liter"""
        result1 = self.parser.parse("ZBUDUJ")
        result2 = self.parser.parse("zbuduj")
        assert result1.type == result2.type
        assert result1.action == result2.action
    
    def test_normalize_whitespace(self):
        """Test normalizacji białych znaków"""
        result = self.parser.parse("  zbuduj   projekt  ")
        assert result.type == CommandType.MAKE
    
    def test_normalize_punctuation(self):
        """Test normalizacji interpunkcji"""
        result = self.parser.parse("zbuduj!")
        assert result.type == CommandType.MAKE
    
    # ==================== Suggestions ====================
    
    def test_get_suggestions_empty(self):
        """Test sugestii dla pustego wejścia"""
        suggestions = self.parser.get_suggestions("")
        assert isinstance(suggestions, list)
    
    def test_get_suggestions_partial(self):
        """Test sugestii dla częściowego wejścia"""
        # Najpierw wykonaj kilka komend
        self.parser.parse("zbuduj")
        self.parser.parse("testy")
        
        suggestions = self.parser.get_suggestions("z")
        assert any("zbuduj" in s for s in suggestions)
    
    # ==================== History ====================
    
    def test_command_history(self):
        """Test historii komend"""
        self.parser.parse("zbuduj")
        self.parser.parse("testy")
        self.parser.parse("wypchnij")
        
        assert len(self.parser.command_history) == 3
        assert self.parser.last_command.action == "push"


class TestParsedCommand:
    """Testy struktury ParsedCommand"""
    
    def test_default_values(self):
        """Test domyślnych wartości"""
        cmd = ParsedCommand(
            type=CommandType.MAKE,
            action="build",
            raw_input="zbuduj"
        )
        
        assert cmd.target is None
        assert cmd.args == []
        assert cmd.flags == {}
        assert cmd.confidence == 1.0
        assert cmd.alternatives == []
    
    def test_with_all_fields(self):
        """Test z wszystkimi polami"""
        cmd = ParsedCommand(
            type=CommandType.GIT,
            action="commit",
            target="main",
            args=["-m", "message"],
            flags={"all": True},
            raw_input="git commit -am message",
            confidence=0.9
        )
        
        assert cmd.type == CommandType.GIT
        assert cmd.action == "commit"
        assert cmd.target == "main"
        assert len(cmd.args) == 2
        assert cmd.flags["all"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
