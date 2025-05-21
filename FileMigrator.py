import shutil
import os
from pathlib import Path
import re
import time


class FileMigrator:
    def __init__(self, source_path: Path, target_path: Path, config: dict, summary_log: list = []):
        self.source_path = source_path
        self.target_path = target_path
        self.config = config
        self.excluded_files = set(config.get("migration", {}).get("class_exclusion_list", []))
        self.allowed_extensions = set(config.get("migration", {}).get("allowed_extensions", [".java"]))
        self.class_mappings = config.get("migration", {}).get("class_level_migration_mapping", {})
        self.package_mappings = config.get("migration", {}).get("package_level_migration_mapping", {})
        self.migrated_class_files = set()
        self.summary_log = summary_log
        self.start_time = time.time()
        self.migrated_class_count = 0
        self.migration_class_map = {}
        self.created_dirs = set()

    def migrate(self):
        print("\n📦 Starting code migration...")
        src_root = self.source_path / "src/main/java"
        tgt_root = self.target_path / "src/main/java"

        if self.class_mappings:
            for src_class, tgt_class in self.class_mappings.items():
                self._migrate_class(src_class, tgt_class)

        if self.package_mappings:
            expanded_mappings = self._expand_package_mappings(src_root, self.package_mappings)
            for src_package, tgt_package in expanded_mappings.items():
                src_dir = self._package_to_path(src_root, src_package)
                tgt_dir = self._package_to_path(tgt_root, tgt_package)
                if not src_dir.exists():
                    print(f"⚠️ Source directory does not exist: {src_dir}")
                    continue
                print(f"📦 Package-level migration from {src_dir} → {tgt_dir}")
                self._copy_java_files(src_dir, tgt_dir, src_package)

        self._cleanup_empty_dirs(tgt_root)

        print("✅ Migration complete.\n")
        return self.migrated_class_count, self.migration_class_map

    def _expand_package_mappings(self, root: Path, mappings: dict) -> dict:
        result = {}
        for src_pkg, tgt_pkg in mappings.items():
            src_path = self._package_to_path(root, src_pkg)
            if not src_path.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(src_path):
                rel_path = Path(dirpath).relative_to(root)
                nested_src_pkg = ".".join(rel_path.parts)
                nested_tgt_pkg = nested_src_pkg.replace(src_pkg, tgt_pkg, 1)
                result[nested_src_pkg] = nested_tgt_pkg
        return result

    def _package_to_path(self, root: Path, package: str) -> Path:
        return root / Path(package.replace(".", "/"))

    def _fqcn_to_path(self, fqcn: str) -> Path:
        parts = fqcn.split(".")
        if parts[-1].endswith(".java"):
            filename = parts[-1]
            package_parts = parts[:-1]
        else:
            filename = f"{parts[-1]}.java"
            package_parts = parts[:-1]
        return Path(*package_parts) / filename

    def _migrate_class(self, src_fqcn: str, tgt_fqcn: str):
        src_path = self.source_path / "src/main/java" / self._fqcn_to_path(src_fqcn)
        tgt_path = self.target_path / "src/main/java" / self._fqcn_to_path(tgt_fqcn)

        if src_path.name in self.excluded_files or src_path.suffix not in self.allowed_extensions:
            print(f"🚫 Skipping excluded or invalid file: {src_path.name}")
            return

        tgt_path.parent.mkdir(parents=True, exist_ok=True)
        self.created_dirs.add(tgt_path.parent)
        shutil.copy2(src_path, tgt_path)

        new_package = str(tgt_path.parent.relative_to(self.target_path / "src/main/java")).replace(os.sep, ".")
        with open(tgt_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = self._update_package_statement(content, new_package)
        with open(tgt_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.migrated_class_files.add(src_path.resolve())
        self.summary_log.append(f"Migrated class: {src_fqcn} → {tgt_fqcn}")
        self.migration_class_map[src_fqcn] = tgt_fqcn
        print(f"📁 Class migrated {src_path} → {tgt_path}")
        self.migrated_class_count += 1

    def _copy_java_files(self, src_dir: Path, tgt_dir: Path, src_package: str):
        tgt_dir.mkdir(parents=True, exist_ok=True)
        self.created_dirs.add(tgt_dir)

        for file in src_dir.glob("*.java"):
            if file.name in self.excluded_files:
                print(f"🚫 Skipping excluded file: {file.name}")
                continue
            if file.suffix not in self.allowed_extensions:
                print(f"🚫 Skipping file with disallowed extension: {file.name}")
                continue
            if file.resolve() in self.migrated_class_files:
                print(f"♻️ Already migrated (class-level): {file.name}")
                continue

            target_file = tgt_dir / file.name
            shutil.copy2(file, target_file)
            print(f"📁 Migrate File {file.name} from source project to target project")

            new_package = str(tgt_dir.relative_to(self.target_path / "src/main/java")).replace(os.sep, ".")
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            content = self._update_package_statement(content, new_package)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"📦 Update package for file {file.name}")

            self.migrated_class_files.add(file.resolve())
            self.summary_log.append(f"Copied file: {file.name} from package {src_package} to package {new_package}")
            self.migration_class_map[
                src_package + '.' + file.name.replace(".java", "")] = new_package + '.' + file.name.replace(".java", "")
            print(f"📁 Copied & refactored {file} → {target_file}")
            self.migrated_class_count += 1

    def _update_package_statement(self, content: str, new_package: str) -> str:
        return re.sub(r'^\s*package\s+[\w\.]+;', f'package {new_package};', content, count=1, flags=re.MULTILINE)

    def _cleanup_empty_dirs(self, root: Path):
        for dir_path in sorted(self.created_dirs, key=lambda x: len(str(x)), reverse=True):
            if dir_path.exists() and not any(dir_path.iterdir()):
                print(f"🧹 Removing empty package: {dir_path}")
                dir_path.rmdir()
                self.summary_log.append(f"Removed empty package: {dir_path.relative_to(root)}")
