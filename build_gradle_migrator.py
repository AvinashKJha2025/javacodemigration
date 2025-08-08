#!/usr/bin/env python3
"""
BuildGradleMigrator - A Python class for migrating build.gradle files from source to target projects.
"""

import re
import os
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum


class SectionType(Enum):
    """Enum for different types of Gradle sections."""
    PLUGINS = "plugins"
    DEPENDENCIES = "dependencies"
    REPOSITORIES = "repositories"
    CONFIGURATIONS = "configurations"
    TASKS = "tasks"
    ANDROID = "android"
    JAVA = "java"
    KOTLIN = "kotlin"
    CUSTOM = "custom"


@dataclass
class GradleSection:
    """Data class to represent a Gradle section."""
    name: str
    content: List[str]
    start_line: int
    end_line: int
    section_type: SectionType
    indentation: str = ""


@dataclass
class MigrationChange:
    """Data class to represent a migration change."""
    section_name: str
    change_type: str  # "ADD" or "UPDATE"
    description: str
    details: List[str]


class BuildGradleMigrator:
    """
    A class to migrate build.gradle files from source to target projects.
    
    This class handles:
    1. Reading and parsing build.gradle files
    2. Identifying sections and their content (including custom sections)
    3. Migrating missing sections from source to target
    4. Updating existing sections with new content
    5. Validation and summarization of changes
    """
    
    def __init__(self, build_source_gradle_path: str, build_target_gradle_path: str):
        """
        Initialize the BuildGradleMigrator.
        
        Args:
            build_source_gradle_path: Path to the source build.gradle file
            build_target_gradle_path: Path to the target build.gradle file
        """
        self.build_source_gradle_path = build_source_gradle_path
        self.build_target_gradle_path = build_target_gradle_path
        self.source_sections: Dict[str, GradleSection] = {}
        self.target_sections: Dict[str, GradleSection] = {}
        self.migration_changes: List[MigrationChange] = []
        self.validation_errors: List[str] = []
        
    def read_gradle_file(self, file_path: str) -> List[str]:
        """
        Read a Gradle file and return its lines.
        
        Args:
            file_path: Path to the Gradle file
            
        Returns:
            List of lines from the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
    
    def identify_sections(self, lines: List[str]) -> Dict[str, GradleSection]:
        """
        Identify sections in a Gradle file (including custom sections).
        
        Args:
            lines: List of lines from the Gradle file
            
        Returns:
            Dictionary mapping section names to GradleSection objects
        """
        sections = {}
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('/*'):
                i += 1
                continue
            
            # Check for section start - handle both standard and custom sections
            # This regex will match: sectionName { or customSectionName {
            section_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\{', line)
            if section_match:
                section_name = section_match.group(1)
                start_line = i
                content = [lines[i]]
                brace_count = 1
                i += 1
                
                # Find the end of the section
                while i < len(lines) and brace_count > 0:
                    content.append(lines[i])
                    brace_count += lines[i].count('{') - lines[i].count('}')
                    i += 1
                
                # Create the section
                sections[section_name] = GradleSection(
                    name=section_name,
                    content=content,
                    start_line=start_line,
                    end_line=i-1,
                    section_type=self._determine_section_type(section_name)
                )
            else:
                i += 1
        
        return sections
    
    def _determine_section_type(self, section_name: str) -> SectionType:
        """
        Determine the type of a section based on its name.
        
        Args:
            section_name: Name of the section
            
        Returns:
            SectionType enum value
        """
        section_name_lower = section_name.lower()
        
        if section_name_lower in ['plugins', 'plugin']:
            return SectionType.PLUGINS
        elif section_name_lower in ['dependencies', 'dependency']:
            return SectionType.DEPENDENCIES
        elif section_name_lower in ['repositories', 'repository']:
            return SectionType.REPOSITORIES
        elif section_name_lower in ['configurations', 'configuration']:
            return SectionType.CONFIGURATIONS
        elif section_name_lower in ['tasks', 'task']:
            return SectionType.TASKS
        elif section_name_lower == 'android':
            return SectionType.ANDROID
        elif section_name_lower == 'java':
            return SectionType.JAVA
        elif section_name_lower == 'kotlin':
            return SectionType.KOTLIN
        else:
            # All other sections are considered custom
            return SectionType.CUSTOM
    
    def parse_gradle_files(self):
        """
        Parse both source and target Gradle files to identify sections.
        """
        try:
            # Read source file
            source_lines = self.read_gradle_file(self.build_source_gradle_path)
            self.source_sections = self.identify_sections(source_lines)
            
            # Read target file
            target_lines = self.read_gradle_file(self.build_target_gradle_path)
            self.target_sections = self.identify_sections(target_lines)
            
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Error reading Gradle file: {e}")
        except Exception as e:
            raise Exception(f"Error parsing Gradle files: {e}")
    
    def migrate_sections(self):
        """
        Migrate sections from source to target.
        """
        # Find sections that exist in source but not in target
        source_only_sections = set(self.source_sections.keys()) - set(self.target_sections.keys())
        
        for section_name in source_only_sections:
            self._migrate_new_section(section_name)
        
        # Find sections that exist in both source and target
        common_sections = set(self.source_sections.keys()) & set(self.target_sections.keys())
        
        for section_name in common_sections:
            self._migrate_existing_section(section_name)
    
    def _migrate_new_section(self, section_name: str):
        """
        Migrate a new section from source to target.
        
        Args:
            section_name: Name of the section to migrate
        """
        source_section = self.source_sections[section_name]
        
        # Read target file
        target_lines = self.read_gradle_file(self.build_target_gradle_path)
        
        # Add migration comment
        migration_comment = "// Section Added in migration from source project\n"
        
        # Insert the new section at the end of the file
        insert_position = len(target_lines)
        
        # Find the last closing brace to place before it
        for i in range(len(target_lines) - 1, -1, -1):
            if target_lines[i].strip() == '}':
                insert_position = i
                break
        
        # Prepare the new section content
        new_section_content = [migration_comment] + source_section.content + ['\n']
        
        # Insert the new section
        target_lines[insert_position:insert_position] = new_section_content
        
        # Write back to target file
        with open(self.build_target_gradle_path, 'w', encoding='utf-8') as file:
            file.writelines(target_lines)
        
        # Extract meaningful content for detailed reporting
        def extract_content_lines(section_content):
            content_lines = []
            for line in section_content:
                stripped = line.strip()
                if (stripped and 
                    not stripped.startswith('//') and 
                    not stripped.startswith('/*') and 
                    not stripped.startswith('{') and 
                    not stripped.startswith('}') and
                    not stripped.endswith('{') and
                    not stripped.endswith('}')):
                    content_lines.append(stripped)
            return content_lines
        
        content_details = extract_content_lines(source_section.content)
        
        # Record the change with detailed information
        self.migration_changes.append(MigrationChange(
            section_name=section_name,
            change_type="ADD",
            description=f"Added new section '{section_name}' from source project",
            details=[f"Added complete section with {len(source_section.content)} lines"] + content_details
        ))
    
    def _migrate_existing_section(self, section_name: str):
        """
        Migrate content to an existing section.
        
        Args:
            section_name: Name of the section to update
        """
        source_section = self.source_sections[section_name]
        target_section = self.target_sections[section_name]
        
        # Read target file
        target_lines = self.read_gradle_file(self.build_target_gradle_path)
        
        # Extract meaningful content lines (skip braces, comments, empty lines)
        def extract_content_lines(section_content):
            content_lines = []
            for line in section_content:
                stripped = line.strip()
                if (stripped and 
                    not stripped.startswith('//') and 
                    not stripped.startswith('/*') and 
                    not stripped.startswith('{') and 
                    not stripped.startswith('}') and
                    not stripped.endswith('{') and
                    not stripped.endswith('}')):
                    content_lines.append(stripped)
            return content_lines
        
        source_content_lines = extract_content_lines(source_section.content)
        target_content_lines = extract_content_lines(target_section.content)
        
        # Find new content (lines that exist in source but not in target)
        new_content = []
        for line in source_content_lines:
            if line not in target_content_lines:
                new_content.append(line)
        
        if not new_content:
            return  # No new content to add
        
        # Add migration comment before the section
        migration_comment = "// Section updated in migration from source to target\n"
        
        # Find the section start in target file
        section_start = target_section.start_line
        
        # Insert migration comment before the section
        target_lines.insert(section_start, migration_comment)
        
        # Find the position to insert new content (after the opening brace)
        insert_position = section_start + 1
        for i in range(section_start, len(target_lines)):
            if '{' in target_lines[i]:
                insert_position = i + 1
                break
        
        # Prepare new content with individual line comments
        new_content_lines = []
        for content in new_content:
            if content and not content.startswith('//'):
                new_content_lines.append(f"    // Added as part of migration from source to target\n")
                new_content_lines.append(f"    {content}\n")
        
        # Insert the new content
        target_lines[insert_position:insert_position] = new_content_lines
        
        # Write back to target file
        with open(self.build_target_gradle_path, 'w', encoding='utf-8') as file:
            file.writelines(target_lines)
        
        # Record the change with detailed information
        self.migration_changes.append(MigrationChange(
            section_name=section_name,
            change_type="UPDATE",
            description=f"Updated section '{section_name}' with new content from source",
            details=new_content
        ))
    
    def validate_gradle_structure(self) -> bool:
        """
        Validate the final generated build_target.gradle file.
        
        Returns:
            True if validation passes, False otherwise
        """
        try:
            target_lines = self.read_gradle_file(self.build_target_gradle_path)
            content = ''.join(target_lines)
            
            # Check for balanced braces
            brace_count = 0
            for char in content:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count < 0:
                        self.validation_errors.append("Unbalanced braces detected")
                        return False
            
            if brace_count != 0:
                self.validation_errors.append(f"Unbalanced braces: {brace_count} unclosed braces")
                return False
            
            # Check for duplicate sections
            sections = self.identify_sections(target_lines)
            section_names = [section.name for section in sections.values()]
            duplicates = [name for name in set(section_names) if section_names.count(name) > 1]
            
            if duplicates:
                self.validation_errors.append(f"Duplicate sections found: {', '.join(duplicates)}")
                return False
            
            return True
            
        except Exception as e:
            self.validation_errors.append(f"Validation error: {e}")
            return False
    
    def generate_summary(self) -> str:
        """
        Generate a summary of all migration changes.
        
        Returns:
            Summary string
        """
        summary = "=== BuildGradle Migration Summary ===\n\n"
        
        if not self.migration_changes:
            summary += "No changes were made during migration.\n"
            return summary
        
        # Group changes by type
        added_sections = [change for change in self.migration_changes if change.change_type == "ADD"]
        updated_sections = [change for change in self.migration_changes if change.change_type == "UPDATE"]
        
        if added_sections:
            summary += "=== Added Sections ===\n"
            for change in added_sections:
                summary += f"Section: {change.section_name}\n"
                summary += f"Description: {change.description}\n"
                # Add detailed content information
                for i, detail in enumerate(change.details[1:], 1):  # Skip the first detail (line count)
                    summary += f"  Change-{i}: {detail}\n"
                summary += "\n"
        
        if updated_sections:
            summary += "=== Updated Sections ===\n"
            for change in updated_sections:
                summary += f"Section: {change.section_name}\n"
                summary += f"Description: {change.description}\n"
                for i, detail in enumerate(change.details, 1):
                    summary += f"Change-{i}: {detail}\n"
                summary += "\n"
        
        # Validation results
        summary += "=== Validation Results ===\n"
        if self.validation_errors:
            summary += "Validation FAILED:\n"
            for error in self.validation_errors:
                summary += f"  - {error}\n"
        else:
            summary += "Validation PASSED: All checks completed successfully.\n"
        
        return summary
    
    def run_migration(self) -> str:
        """
        Run the complete migration process.
        
        Returns:
            Summary of the migration process
        """
        try:
            # Step 1: Parse both Gradle files
            print("Step 1: Parsing Gradle files...")
            self.parse_gradle_files()
            
            # Step 2: Migrate sections
            print("Step 2: Migrating sections...")
            self.migrate_sections()
            
            # Step 3: Validate the result
            print("Step 3: Validating migrated file...")
            validation_passed = self.validate_gradle_structure()
            
            # Step 4: Generate summary
            print("Step 4: Generating summary...")
            summary = self.generate_summary()
            
            # Step 5: Write summary to file
            print("Step 5: Writing summary to file...")
            with open('build_gradle_migration_result.txt', 'w', encoding='utf-8') as f:
                f.write(summary)
            
            return summary
            
        except Exception as e:
            return f"Migration failed with error: {e}"


def main():
    """
    Main function to demonstrate usage of BuildGradleMigrator.
    """
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python build_gradle_migrator.py <source_gradle_path> <target_gradle_path>")
        sys.exit(1)
    
    source_path = sys.argv[1]
    target_path = sys.argv[2]
    
    try:
        migrator = BuildGradleMigrator(source_path, target_path)
        summary = migrator.run_migration()
        print(summary)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
