"""
Testy dla warstw wykonawczych (text2make, text2shell, text2git, etc.)
"""

import pytest
from pathlib import Path
import tempfile
import os


class TestText2Shell:
    """Testy dla Text2Shell"""
    
    def setup_method(self):
        from text2dsl.layers.text2shell import Text2Shell
        self.shell = Text2Shell()
    
    def test_run_echo(self):
        """Test podstawowej komendy echo"""
        result = self.shell.run("echo 'hello'")
        assert result.success
        assert "hello" in result.output
    
    def test_run_pwd(self):
        """Test komendy pwd"""
        result = self.shell.run("pwd")
        assert result.success
        assert len(result.output) > 0
    
    def test_run_ls(self):
        """Test komendy ls"""
        result = self.shell.run("ls -la")
        assert result.success
    
    def test_translate_polish_command(self):
        """Test tłumaczenia polskiego polecenia"""
        bash = self.shell.translate_to_bash("pokaż pliki")
        assert "ls" in bash
    
    def test_translate_english_command(self):
        """Test tłumaczenia angielskiego polecenia"""
        bash = self.shell.translate_to_bash("show files")
        # Powinno zostać jako jest lub przetłumaczone
        assert len(bash) > 0
    
    def test_dangerous_command_blocked(self):
        """Test blokowania niebezpiecznych komend"""
        result = self.shell.run("rm -rf /")
        assert not result.success
        assert "zablokowana" in result.error.lower()
    
    def test_cd(self):
        """Test zmiany katalogu"""
        original = self.shell.pwd()
        
        # Zmień na /tmp
        success = self.shell.cd("/tmp")
        assert success
        assert self.shell.pwd() == "/tmp"
        
        # Wróć
        self.shell.cd(original)
    
    def test_alias(self):
        """Test aliasów"""
        self.shell.add_alias("ll", "ls -la", "Long listing")
        
        result = self.shell.run("ll")
        assert result.success
    
    def test_history(self):
        """Test historii komend"""
        self.shell.run("echo 1")
        self.shell.run("echo 2")
        
        history = self.shell.get_history(2)
        assert len(history) == 2
    
    def test_get_suggestions(self):
        """Test sugestii"""
        suggestions = self.shell.get_suggestions()
        assert len(suggestions) > 0


class TestText2Make:
    """Testy dla Text2Make"""
    
    def setup_method(self):
        from text2dsl.layers.text2make import Text2Make
        
        # Utwórz tymczasowy katalog z Makefile
        self.temp_dir = tempfile.mkdtemp()
        self.makefile_path = Path(self.temp_dir) / "Makefile"
        self.makefile_path.write_text("""
.PHONY: all build test clean

# Build the project
all: build

# Build target
build:
\t@echo "Building..."

# Run tests
test:
\t@echo "Testing..."

# Clean up
clean:
\t@echo "Cleaning..."
""")
        
        self.make = Text2Make(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_has_makefile(self):
        """Test wykrywania Makefile"""
        assert self.make.has_makefile()
    
    def test_get_targets(self):
        """Test pobierania celów"""
        targets = self.make.get_targets()
        target_names = [t.name for t in targets]
        
        assert "all" in target_names
        assert "build" in target_names
        assert "test" in target_names
        assert "clean" in target_names
    
    def test_run_target(self):
        """Test wykonania celu"""
        result = self.make.run("build")
        assert result.success
        assert "Building" in result.output
    
    def test_run_default_target(self):
        """Test wykonania domyślnego celu"""
        result = self.make.run()
        assert result.success
    
    def test_resolve_natural_command(self):
        """Test rozwiązywania naturalnych komend"""
        target = self.make.resolve_natural_command("zbuduj")
        assert target in ["build", "all"]
        
        target = self.make.resolve_natural_command("testy")
        assert target == "test"
    
    def test_get_suggestions(self):
        """Test sugestii"""
        suggestions = self.make.get_suggestions()
        assert len(suggestions) > 0
    
    def test_dry_run(self):
        """Test dry-run"""
        result = self.make.run("build", dry_run=True)
        assert result.success


class TestText2Git:
    """Testy dla Text2Git"""
    
    def setup_method(self):
        from text2dsl.layers.text2git import Text2Git
        
        # Utwórz tymczasowe repo git
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        os.system("git init")
        os.system("git config user.email 'test@test.com'")
        os.system("git config user.name 'Test'")
        
        # Utwórz początkowy plik i commit
        Path(self.temp_dir, "README.md").write_text("# Test")
        os.system("git add .")
        os.system("git commit -m 'Initial commit'")
        
        self.git = Text2Git(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_repo(self):
        """Test wykrywania repo"""
        assert self.git.is_repo()
    
    def test_get_status(self):
        """Test pobierania statusu"""
        status = self.git.get_status()
        assert status is not None
        assert status.branch is not None
    
    def test_get_branches(self):
        """Test pobierania gałęzi"""
        branches = self.git.get_branches()
        assert len(branches) >= 1  # Przynajmniej main/master
    
    def test_get_log(self):
        """Test pobierania historii"""
        commits = self.git.get_log(5)
        assert len(commits) >= 1
        assert commits[0].message == "Initial commit"
    
    def test_add_and_status(self):
        """Test dodawania plików"""
        # Utwórz nowy plik
        Path(self.temp_dir, "new_file.txt").write_text("content")
        
        # Sprawdź status
        status = self.git.get_status()
        assert "new_file.txt" in status.untracked
        
        # Dodaj
        result = self.git.add("new_file.txt")
        assert result.success
        
        # Sprawdź ponownie
        status = self.git.get_status()
        assert "new_file.txt" in status.staged
    
    def test_execute_natural_status(self):
        """Test naturalnego polecenia status"""
        result = self.git.execute_natural("status")
        assert result.success
    
    def test_get_suggestions(self):
        """Test sugestii"""
        suggestions = self.git.get_suggestions()
        assert len(suggestions) > 0


class TestText2Docker:
    """Testy dla Text2Docker (bez uruchamiania Dockera)"""
    
    def setup_method(self):
        from text2dsl.layers.text2docker import Text2Docker
        
        self.temp_dir = tempfile.mkdtemp()
        
        # Utwórz Dockerfile
        Path(self.temp_dir, "Dockerfile").write_text("""
FROM python:3.9-slim
WORKDIR /app
COPY . .
CMD ["python", "main.py"]
""")
        
        # Utwórz docker-compose.yml
        Path(self.temp_dir, "docker-compose.yml").write_text("""
version: '3'
services:
  web:
    build: .
    ports:
      - "8080:80"
  db:
    image: postgres:13
""")
        
        self.docker = Text2Docker(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_has_dockerfile(self):
        """Test wykrywania Dockerfile"""
        assert self.docker.has_dockerfile()
    
    def test_has_compose(self):
        """Test wykrywania docker-compose"""
        assert self.docker.has_compose()
    
    def test_get_compose_services(self):
        """Test pobierania serwisów compose"""
        services = self.docker.get_compose_services()
        assert "web" in services
        assert "db" in services
    
    def test_get_suggestions(self):
        """Test sugestii"""
        suggestions = self.docker.get_suggestions()
        assert len(suggestions) > 0


class TestText2Python:
    """Testy dla Text2Python"""
    
    def setup_method(self):
        from text2dsl.layers.text2python import Text2Python
        
        self.temp_dir = tempfile.mkdtemp()
        
        # Utwórz requirements.txt
        Path(self.temp_dir, "requirements.txt").write_text("pytest\nblack\n")
        
        # Utwórz prosty skrypt
        Path(self.temp_dir, "main.py").write_text("print('Hello')")
        
        self.python = Text2Python(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_python_version(self):
        """Test pobierania wersji Python"""
        version = self.python.get_python_version()
        assert "Python" in version or "python" in version.lower()
    
    def test_run_script(self):
        """Test uruchamiania skryptu"""
        result = self.python.run_script("main.py")
        assert result.success
        assert "Hello" in result.output
    
    def test_run_module(self):
        """Test uruchamiania modułu"""
        result = self.python.run_module("json.tool", "--help")
        # Może się nie udać, ale nie powinno crashować
        assert isinstance(result.success, bool)
    
    def test_translate_natural_test(self):
        """Test rozpoznawania naturalnego polecenia 'testy'"""
        result = self.python.execute_natural("testy")
        # pytest może nie być zainstalowany, ale powinno być rozpoznane
        assert "pytest" in result.operation or "test" in result.operation
    
    def test_get_suggestions(self):
        """Test sugestii"""
        suggestions = self.python.get_suggestions()
        assert len(suggestions) > 0


class TestContextManager:
    """Testy dla ContextManager"""
    
    def setup_method(self):
        from text2dsl.core.context_manager import ContextManager
        
        self.temp_dir = tempfile.mkdtemp()
        
        # Utwórz strukturę projektu
        Path(self.temp_dir, "Makefile").write_text(".PHONY: all\nall:\n\t@echo ok")
        (Path(self.temp_dir) / ".git").mkdir()
        Path(self.temp_dir, ".git/HEAD").write_text("ref: refs/heads/main")
        
        self.context = ContextManager(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_project_detected(self):
        """Test wykrywania projektu"""
        assert self.context.project is not None
        assert self.context.project.has_makefile
        assert self.context.project.has_git
    
    def test_get_contextual_options(self):
        """Test opcji kontekstowych"""
        options = self.context.get_contextual_options()
        assert "make" in options or "git" in options
    
    def test_update_state(self):
        """Test aktualizacji stanu"""
        self.context.update_state("MAKE", "build")
        
        assert self.context.state.last_command_type == "MAKE"
        assert self.context.state.last_target == "build"
        assert self.context.state.command_count == 1
    
    def test_change_directory(self):
        """Test zmiany katalogu"""
        original = self.context.working_dir
        
        success = self.context.change_directory("/tmp")
        assert success
        assert str(self.context.working_dir) == "/tmp"
        
        # Wróć
        self.context.change_directory(str(original))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
