import shutil
import time
import json
from pathlib import Path

class SummaryReporter:
    def __init__(self, source_path, target_path, config, log_lines, migration_count, refactored_count_map, start_time,
                 build_status):
        self.source_path = source_path
        self.target_path = target_path
        self.class_mappings = config.get("migration", {}).get("class_level_migration_mapping", {})
        self.package_mappings = config.get("migration", {}).get("package_level_migration_mapping", {})
        self.excluded_files = config.get("migration", {}).get("class_exclusion_list", [])
        self.log_lines = log_lines
        self.migration_count = migration_count
        self.refactored_count_map = refactored_count_map
        self.start_time = start_time
        self.end_time = time.time()
        self.build_status = build_status

    def write(self):
        elapsed_minutes = round((self.end_time - self.start_time) / 60, 2)
        # Estimate manual times for different operations
        class_migrations = [line for line in self.log_lines if line.startswith("Migrated class:")]
        package_file_copies = [line for line in self.log_lines if line.startswith("Copied file:")]

        # Assign estimated manual time for each type (in minutes)
        class_migration_time = len(class_migrations) * 5  # class-level migration is more effort
        package_copy_time = len(package_file_copies) * 2  # package file copy and update

        # Assign estimated manual time for each type (in minutes)
        update_imports_time = self.refactored_count_map['update_imports_count'] * 1
        replace_injected_reference_time = self.refactored_count_map['replace_injected_reference_count'] * 2
        refactor_env_config_util_time = self.refactored_count_map['refactor_env_config_util_count'] * 2
        add_reactive_method_prompts_time = self.refactored_count_map['add_reactive_method_prompts_count'] * 2

        manual_estimate = class_migration_time + package_copy_time + update_imports_time + replace_injected_reference_time + refactor_env_config_util_time + add_reactive_method_prompts_time
        savings = max(manual_estimate - elapsed_minutes, 0)
        efficiency_gain = round((savings / manual_estimate) * 100, 2) if manual_estimate else 100.0

        report_path = self.target_path / "migration_summary.txt"
        with open(report_path, "w", encoding="utf-8") as report:
            report.write("=== Migration Summary Report ===\n")
            report.write(f"\nSource Path: {self.source_path}")
            report.write(f"\nTarget Path: {self.target_path}")
            report.write(f"\nElapsed Time (Automated): {elapsed_minutes} minutes")
            report.write(f"\nBuild Status: {self.build_status}\n")

            report.write("\n-- Migration Inputs --\n")
            report.write(json.dumps({
                "class_level_mapping": self.class_mappings,
                "package_level_mapping": self.package_mappings,
                "excluded_files": self.excluded_files
            }, indent=2))

            report.write("\n-- Changes Made --\n")
            for line in self.log_lines:
                report.write(f"{line}\n")
            report.write("\n-- Refactored Counts --\n")
            report.write(json.dumps(self.refactored_count_map, indent=2))
            report.write("\n-- Migration Counts --\n")
            report.write(json.dumps({"migration_count": self.migration_count}, indent=2))

            report.write("\n-- Estimated Time Savings & Efficiency --\n")
            report.write(f"Manual Migration Estimate: {manual_estimate} minutes\n")
            report.write(f"Actual Time Taken: {elapsed_minutes} minutes\n")
            report.write(f"Time Saved: {savings} minutes\n")
            report.write(f"Efficiency Gain: {efficiency_gain}%\n")

        print(f"📝 Migration summary saved to {report_path}")
        # Create a local copy of the migration summary
        local_copy_path = Path("migration_summary.txt").resolve()
        shutil.copy2(report_path, local_copy_path)
        print(f"📝 Local copy of migration summary saved to {local_copy_path}")
