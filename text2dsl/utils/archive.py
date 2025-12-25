"""
Archive/Export utilities for text2dsl

Umożliwia:
- Eksport całego projektu jako archiwum ZIP/TAR
- Pobieranie wybranych plików
- Tworzenie kopii zapasowych
"""

import os
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ExportResult:
    """Wynik eksportu"""
    success: bool
    path: str
    size_bytes: int
    files_count: int
    error: Optional[str] = None


class ArchiveManager:
    """
    Menedżer archiwów dla text2dsl
    
    Użycie:
        manager = ArchiveManager("/path/to/project")
        
        # Eksport do ZIP
        result = manager.export_zip("backup.zip")
        
        # Eksport wybranych plików
        result = manager.export_files(["src/", "Makefile"], "partial.zip")
    """
    
    # Domyślne wzorce do wykluczenia
    DEFAULT_EXCLUDES = [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".env",
        "*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        "*.log",
    ]
    
    def __init__(self, source_dir: Optional[str] = None):
        self.source_dir = Path(source_dir or os.getcwd()).resolve()
        self.excludes = self.DEFAULT_EXCLUDES.copy()
    
    def _should_exclude(self, path: Path) -> bool:
        """Sprawdza czy ścieżka powinna być wykluczona"""
        path_str = str(path)
        name = path.name
        
        for pattern in self.excludes:
            if pattern.startswith("*"):
                # Wzorzec z gwiazdką (np. *.pyc)
                if name.endswith(pattern[1:]):
                    return True
            else:
                # Dokładne dopasowanie nazwy
                if name == pattern or pattern in path_str:
                    return True
        
        return False
    
    def _collect_files(self, base_path: Path, relative_to: Optional[Path] = None) -> List[Path]:
        """Zbiera listę plików do archiwizacji"""
        files = []
        relative_to = relative_to or base_path
        
        if base_path.is_file():
            return [base_path]
        
        for item in base_path.rglob("*"):
            if item.is_file() and not self._should_exclude(item):
                files.append(item)
        
        return files
    
    def export_zip(
        self,
        output_path: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> ExportResult:
        """
        Eksportuje projekt do archiwum ZIP
        
        Args:
            output_path: Ścieżka do pliku ZIP (opcjonalna)
            include_patterns: Wzorce plików do włączenia
            exclude_patterns: Dodatkowe wzorce do wykluczenia
            
        Returns:
            ExportResult z informacjami o eksporcie
        """
        # Dodaj dodatkowe wykluczenia
        if exclude_patterns:
            self.excludes.extend(exclude_patterns)
        
        # Ustal ścieżkę wyjściową
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{self.source_dir.name}_{timestamp}.zip"
        
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = self.source_dir / output_path
        
        try:
            files_count = 0
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self._collect_files(self.source_dir):
                    # Ścieżka względna w archiwum
                    arc_name = file_path.relative_to(self.source_dir)
                    
                    # Filtruj po wzorcach include
                    if include_patterns:
                        if not any(str(arc_name).startswith(p.rstrip('/')) for p in include_patterns):
                            continue
                    
                    zipf.write(file_path, arc_name)
                    files_count += 1
            
            size = output_path.stat().st_size
            
            return ExportResult(
                success=True,
                path=str(output_path),
                size_bytes=size,
                files_count=files_count
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                path=str(output_path),
                size_bytes=0,
                files_count=0,
                error=str(e)
            )
    
    def export_tar(
        self,
        output_path: Optional[str] = None,
        compression: str = "gz"
    ) -> ExportResult:
        """
        Eksportuje projekt do archiwum TAR
        
        Args:
            output_path: Ścieżka do pliku TAR
            compression: Kompresja (gz, bz2, xz, none)
            
        Returns:
            ExportResult z informacjami o eksporcie
        """
        # Ustal rozszerzenie i tryb
        ext_map = {"gz": ".tar.gz", "bz2": ".tar.bz2", "xz": ".tar.xz", "none": ".tar"}
        mode_map = {"gz": "w:gz", "bz2": "w:bz2", "xz": "w:xz", "none": "w"}
        
        ext = ext_map.get(compression, ".tar.gz")
        mode = mode_map.get(compression, "w:gz")
        
        # Ustal ścieżkę wyjściową
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{self.source_dir.name}_{timestamp}{ext}"
        
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = self.source_dir / output_path
        
        try:
            files_count = 0
            
            with tarfile.open(output_path, mode) as tar:
                for file_path in self._collect_files(self.source_dir):
                    arc_name = file_path.relative_to(self.source_dir)
                    tar.add(file_path, arc_name)
                    files_count += 1
            
            size = output_path.stat().st_size
            
            return ExportResult(
                success=True,
                path=str(output_path),
                size_bytes=size,
                files_count=files_count
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                path=str(output_path),
                size_bytes=0,
                files_count=0,
                error=str(e)
            )
    
    def export_files(
        self,
        files: List[str],
        output_path: str,
        format: str = "zip"
    ) -> ExportResult:
        """
        Eksportuje wybrane pliki/katalogi
        
        Args:
            files: Lista plików/katalogów do eksportu
            output_path: Ścieżka do archiwum
            format: Format archiwum (zip, tar, tar.gz)
            
        Returns:
            ExportResult
        """
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = self.source_dir / output_path
        
        try:
            files_count = 0
            
            if format == "zip":
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_pattern in files:
                        file_path = self.source_dir / file_pattern
                        
                        if file_path.is_file():
                            zipf.write(file_path, file_path.name)
                            files_count += 1
                        elif file_path.is_dir():
                            for f in self._collect_files(file_path):
                                arc_name = f.relative_to(self.source_dir)
                                zipf.write(f, arc_name)
                                files_count += 1
            else:
                mode = "w:gz" if format == "tar.gz" else "w"
                with tarfile.open(output_path, mode) as tar:
                    for file_pattern in files:
                        file_path = self.source_dir / file_pattern
                        
                        if file_path.exists():
                            tar.add(file_path, file_path.name)
                            files_count += 1
            
            size = output_path.stat().st_size
            
            return ExportResult(
                success=True,
                path=str(output_path),
                size_bytes=size,
                files_count=files_count
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                path=str(output_path),
                size_bytes=0,
                files_count=0,
                error=str(e)
            )
    
    def list_files(self) -> List[str]:
        """Zwraca listę plików w projekcie"""
        files = []
        for file_path in self._collect_files(self.source_dir):
            relative = file_path.relative_to(self.source_dir)
            files.append(str(relative))
        return sorted(files)
    
    def get_project_size(self) -> int:
        """Zwraca całkowity rozmiar projektu w bajtach"""
        total = 0
        for file_path in self._collect_files(self.source_dir):
            total += file_path.stat().st_size
        return total
    
    def format_size(self, size_bytes: int) -> str:
        """Formatuje rozmiar do czytelnej postaci"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


def create_project_archive(
    source_dir: str,
    output_path: Optional[str] = None,
    format: str = "zip"
) -> ExportResult:
    """
    Funkcja pomocnicza do szybkiego tworzenia archiwum projektu
    
    Args:
        source_dir: Katalog źródłowy
        output_path: Ścieżka wyjściowa (opcjonalna)
        format: Format archiwum (zip, tar, tar.gz)
        
    Returns:
        ExportResult
    """
    manager = ArchiveManager(source_dir)
    
    if format == "zip":
        return manager.export_zip(output_path)
    elif format in ["tar", "tar.gz"]:
        compression = "gz" if format == "tar.gz" else "none"
        return manager.export_tar(output_path, compression)
    else:
        return ExportResult(
            success=False,
            path="",
            size_bytes=0,
            files_count=0,
            error=f"Nieobsługiwany format: {format}"
        )
