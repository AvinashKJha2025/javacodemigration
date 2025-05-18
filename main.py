from agent.core.repo_manager import RepoManager
from agent.core.file_migrator import FileMigrator
from agent.core.code_refactorer import CodeRefactorer
from agent.core.gradle_builder import GradleBuilder
from agent.core.summary_reporter import SummaryReporter
import yaml
import time
from pathlib import Path


def load_migration_config():
    with open("agent/configuration/migration_configuration.yaml", "r") as f:
        return yaml.safe_load(f)


def main():
    start_time = time.time()
    summary_log = []
    print("🚀 Loading migration configuration...")
    config = load_migration_config()
    project_config = config.get("project", {})
    source_path, target_path = verify_migration_repo_readiness(project_config)
    migration_count, migration_class_map = migrate_files(config, source_path, target_path, summary_log)
    refactored_count_map = refactor_code(config, target_path, summary_log, migration_class_map)
    build_status, output = execute_gradle_build(source_path, target_path)
    write_summary_report(build_status, config, migration_count, refactored_count_map, source_path, start_time,
                         summary_log, target_path)


def verify_migration_repo_readiness(project_config):
    # Initialize and prepare repositories
    repo_manager = RepoManager(project_config)
    repo_manager.prepare_repos()
    source_path = repo_manager.get_source_path()
    target_path = repo_manager.get_target_path()
    # ... Proceed to initialize migrator, refactorer, etc.
    print(f"✅ Repositories ready for migration.\n Source: {source_path} \n Target: {target_path}")
    return source_path, target_path


def migrate_files(config, source_path, target_path, summary_log):
    migrator = FileMigrator(source_path, target_path, config, summary_log)
    migration_count, migration_class_map = migrator.migrate()
    print(f"✅ Migration completed for : {migration_count} files ")
    return migration_count, migration_class_map


def refactor_code(config, target_path, summary_log, migration_class_map):
    properties_file_path = Path("application.properties").resolve()
    java_src_path = target_path / 'src/main/java'
    refactorer = CodeRefactorer(target_path, config, properties_file_path, java_src_path, summary_log,
                                migration_class_map)
    refactorer.package_mappings = config['migration']['package_level_migration_mapping']
    refactored_count_map = refactorer.refactor_codebase()
    print(
        f"Refactored  {refactored_count_map['update_imports_count']} imports, "
        f"{refactored_count_map['replace_injected_reference_count']} replace_injected_reference_count, {refactored_count_map['refactor_env_config_util_count']} refactor_env_config_util_count, "
        f"and added {refactored_count_map['add_reactive_method_prompts_count']} reactive method prompts.")
    return refactored_count_map


def execute_gradle_build(source_path, target_path):
    builder = GradleBuilder(target_path)
    build_success, output = builder.build()
    print(f"✅ Build completed : {output}\n Source: {source_path}\n Target: {target_path}")
    build_status = "Failed" if not build_success else "Success"
    return build_status, output


def write_summary_report(build_status, config, migration_count, refactored_count_map, source_path, start_time,
                         summary_log, target_path):
    reporter = SummaryReporter(
        source_path=source_path,
        target_path=target_path,
        config=config,
        log_lines=summary_log,
        migration_count=migration_count,
        refactored_count_map=refactored_count_map,
        start_time=start_time,
        build_status=build_status,
    )
    reporter.write()


if __name__ == "__main__":
    main()
