import re
from pathlib import Path


class CodeRefactorer:
    def __init__(self, target_path: Path, config: dict, properties_file_path: Path, java_src_path: Path,
                 summary_log: list = [], migration_class_map: dict = {}):
        self.target_path = target_path
        self.java_src_path = target_path / "src/main/java"
        self.config = config
        self.refactorings = config.get("migration", {}).get("refactorings", [])
        self.properties_file_path = properties_file_path
        self.package_mappings = config.get("migration", {}).get("package_mappings", {})
        self.property_rewrites = config.get("migration", {}).get("property_rewrites", [])
        self.excluded_files = set(config.get("migration", {}).get("excluded_files", []))
        self.extracted_properties = set()
        self.reactive_types = ['Mono', 'Flux', 'WebClient']
        self.java_src_path = java_src_path
        self.summary_log = summary_log
        self.migration_class_map = migration_class_map
        self.reactive_prompt_counts = 0;
        self.update_package_statement_count = 0
        self.update_imports_count = 0
        self.replace_property_access_count = 0
        self.refactor_env_config_util_count = 0
        self.add_reactive_method_prompts_count = 0

    def refactor_codebase(self):
        for file_path in self.java_src_path.rglob('*.java'):
            # Check if the file is present in the migration_class_map
            if not any(file_path.name.replace(".java", "") in key for key in self.migration_class_map.keys()):
                print(f"🚫 Skipping file not in migration map: {file_path.name}")
                continue
            if file_path.name in self.excluded_files:
                print(f"🚫 Skipping excluded file: {file_path.name}")
                continue
            self.refactor_file(file_path)
        refactored_count_map = {}
        refactored_count_map['update_imports_count'] = self.update_imports_count
        refactored_count_map['replace_injected_reference_count'] = self.replace_property_access_count
        refactored_count_map['refactor_env_config_util_count'] = self.refactor_env_config_util_count
        refactored_count_map['add_reactive_method_prompts_count'] = self.add_reactive_method_prompts_count

        return refactored_count_map

    def refactor_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Update imports
        content = self.update_imports(content)

        # Refactor EnvConfigUtil to Environment
        content = self.refactor_env_config_util_and_imports(content, file_path.name)

        # Handle reactive methods and replace with synchronous versions
        content = self.add_reactive_method_prompts(content)

        # If content changed, write it back to the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def update_package_statement(self, file_path, content):
        try:
            relative_path = file_path.relative_to(self.java_src_path).parent
            current_package = ".".join(relative_path.parts)

            for source_pkg, target_pkg in self.package_mappings.items():
                if content.startswith('package ' + source_pkg):
                    content = re.sub(rf'(?m)^package\s+{re.escape(source_pkg)};', f'package {target_pkg};', content)
                    print(f"✅ Updated package: {source_pkg} -> {target_pkg} in {file_path}")
                    self.summary_log.append(f"Updated package: {source_pkg} -> {target_pkg} in {file_path}")
                    self.update_package_statement_count += 1
                    break
        except Exception as e:
            print(f"⚠️ Failed to resolve package for {file_path}: {e}")
        return content

    def update_imports(self, content):
        for source_pkg, target_pkg in self.package_mappings.items():
            class_name = self.extract_class_name(content)
            if source_pkg in content:
                content = re.sub(rf'import\s+{re.escape(source_pkg)}', f'import {target_pkg}', content)
                self.summary_log.append(
                    f"Updated source project import to target project import: {source_pkg} -> {target_pkg} for class {class_name} ")
                self.update_imports_count += 1

        return content

    def extract_class_name(self, content):
        # Regular expression to match 'public class <class_name>'
        match = re.search(r'\bpublic\s+class\s+(\w+)', content)
        if match:
            return match.group(1)  # Return the class name
        return None  # Return None if no match is found

    def refactor_env_config_util_and_imports1(self, content):
        # Replace import statement
        if re.search(r'import\s+com\.avinash\.poc\.target\.config\.EnvConfigUtil;', content):
            content = re.sub(r'import\s+com\.avinash\.poc\.target\.config\.EnvConfigUtil;',
                             'import org.springframework.core.env.Environment;', content)
            self.update_imports_count += 1
            class_name = self.extract_class_name(content)
            self.summary_log.append(
                'Updated source project import to target project import: com.avinash.poc.target.config.EnvConfigUtil -> org.springframework.core.env.Environment for class ' + class_name)

        # Replace field declaration
        if re.search(r'private\s+EnvConfigUtil\s+envConfigUtil;', content):
            content = re.sub(r'private\s+EnvConfigUtil\s+envConfigUtil;', 'private Environment environment;', content)
            self.replace_property_access_count += 1

        # Replace method calls
        env_config_util_calls = re.findall(r'envConfigUtil\.getProperty\(', content)
        if env_config_util_calls:
            self.refactor_env_config_util_count += len(env_config_util_calls)  # Increment by the number of matches
            content = re.sub(r'envConfigUtil\.getProperty\(', 'environment.getProperty(', content)

        # Inject Environment bean if not already present
        if 'environment.getProperty' in content and '@Autowired' not in content:
            content = re.sub(r'(public class \w+\s*{)', r'\1\n\n    @Autowired\n    private Environment environment;\n',
                             content)

        return content

    def refactor_env_config_util_and_imports(self, content, file_name):
            for refactoring in self.refactorings:
                if refactoring["file"] not in content:
                    continue

                # Replace import statements
                for source_import, target_import in refactoring.get("import_mapping", {}).items():
                    if source_import in content:
                        content = re.sub(rf'import\s+{re.escape(source_import)};', f'import {target_import};', content)
                        self.update_imports_count += 1
                        self.summary_log.append(f"Updated import: {source_import} -> {target_import}")

                # Replace instance variables
                for source_instance, target_instance in refactoring.get("instance_mapping", {}).items():
                    if source_instance in content:
                        content = re.sub(rf'private\s+{re.escape(source_instance)}\s+\w+;',
                                         f'private {target_instance} environment;', content)
                        self.replace_property_access_count += 1
                        self.summary_log.append(f"Replaced instance: {source_instance} -> {target_instance}")

                # Replace method calls
                for source_method, target_method in refactoring.get("method_mapping", {}).items():
                    method_calls = re.findall(rf'{re.escape(source_method)}\(', content)
                    if method_calls:
                        self.refactor_env_config_util_count += len(method_calls)
                        content = re.sub(rf'{re.escape(source_method)}\(', f'{target_method}(', content)
                        self.summary_log.append(f"Replaced method: {source_method} -> {target_method}")

            return content

    def add_reactive_method_prompts(self, content):
        pattern = r'(public|private|protected)\s+(Mono|Flux|WebClient)<[^>]+>\s+(\w+)\s*\((.*?)\)\s*{'
        matches = list(re.finditer(pattern, content, re.DOTALL))

        for match in reversed(matches):  # reverse to avoid offset issues on insert
            start = match.start()
            method_name = match.group(3)
            prompt = f"\n    // TODO: Copilot, convert this reactive method '{method_name}' to a synchronous, non-reactive version.\n"
            content = content[:start] + prompt + content[start:]
            self.add_reactive_method_prompts_count += 1
            self.summary_log.append(
                f"Added TODO Prompt for reactive to nonreactive conversion in method :  {method_name}")
        return content

    def write_extracted_properties(self):
        if not self.extracted_properties:
            print("ℹ️ No properties to write.")
            return

        with open(self.properties_file_path, 'a') as f:
            for prop in sorted(self.extracted_properties):
                f.write(f"{prop}=TBD\n")
        print(f"📝 Written {len(self.extracted_properties)} properties to {self.properties_file_path}")
