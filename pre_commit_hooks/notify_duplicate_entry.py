import argparse
import json
from typing import Optional
from typing import Sequence
from pathlib import Path
import re
from collections import defaultdict


def extract_version(filepath: str) -> str:
    """Extract Alembic version from the filename."""
    return Path(filepath).parents[2].name.strip()

def extract_folder_type(filepath: str) -> str:
    """Extract the folder type from the file path (upgrade/downgrade)."""
    return Path(filepath).parents[1].name.strip()

def extract_operation_type(filepath: str) -> str:
    """Extract the operation type from the file path (insert/update/delete)."""
    return Path(filepath).parent.name.strip()

def get_parallel_files(staged_file: str) -> list:
    """Get all parallel files with the same table name within the same parent folder.
    
    :param staged_file: Path to the staged file
    :return: List of all related file paths within the same parent folder
    """
    path = Path(staged_file)
    file_name = path.name
    parent_folder = path.parents[1]
    parallel_files = []
    
    for operation_type in ['insert', 'update', 'delete']:
        operation_path = parent_folder / operation_type
        target_file = operation_path / file_name
        if target_file.exists():
            parallel_files.append(str(target_file))
    
    return parallel_files

def main(argv: Optional[Sequence[str]] = None) -> int:

    def _check_duplicate_entry():
        """ Check duplicate entry based on pkey criteria.

        :param json_entries: List of json entries
        :param pkeys: List of Primary keys
        :return: list of duplicated entry pkey value tuples
        """
        for entry in json_entries:
            pkey_value_tuple = tuple(entry[pkey] for pkey in primary_keys)
            key = (alembic_version, folder_type, operation_type)
            
            if pkey_value_tuple not in unique_entries[key]:
                unique_entries[key].add(pkey_value_tuple)
            else:
                duplicate_entries[key].add(pkey_value_tuple)
            
            cross_operation_entries[(alembic_version, file_name, folder_type)][pkey_value_tuple].add(operation_type)

    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', type=str,
                        help='Names of the JSON files to check duplicate entries'
                        )
    table_uuid_mapping = {
        'action': ['uuid'],
        'env_property_group': ['uuid'],
        'environment': ['uuid'],
        'environment_property': ['code'],
        'report_summary': ['uuid'],
        'runner': ['uuid'],
        'scenario': ['uuid'],
        'sla': ['uuid'],
        'sla_scenario_association': ['sla', 'scenario'],
        'tag': ['uuid'],
        'tag_action_association': ['tag_uuid', 'action_uuid'],
        'tag_case_association': ['test_case_uuid', 'tag_uuid'],
        'teams': ['uuid'],
        'test_case': ['uuid'],
        'test_suit': ['uuid'],
        'test_supported_version': ['test_case_uuid', 'version'],
        'testcase_workload_association': ['uuid'],
        'user': ['uuid'],
        'user_tokens': ['user_token'],
        'workflow_task': ['workflow_id'],
        'context': ['uuid'],
        'test_sla_association': ['test_case', 'sla'],
        'teams_association': ['user_uuid', 'team_uuid'],
        'teams_resource_permission': ['team_uuid', 'resource_name'],
        'label': ['uuid'],
        'authentication_config_rules': ['auth_type'],
        'authentication': ['uuid'],
        'user_authentication_association':
            ['user_uuid', 'authentication_uuid'],
    }

    args = vars(parser.parse_args(argv))
    staged_filenames = args['filenames']
    flag = False

    unique_entries = defaultdict(set)
    duplicate_entries = defaultdict(set)
    cross_operation_entries = defaultdict(lambda: defaultdict(set))
    
    all_files_to_check = set()
    for staged_file in staged_filenames:
        parallel_files = get_parallel_files(staged_file)
        all_files_to_check.update(parallel_files)

    for json_file in all_files_to_check:
        file_name = Path(json_file).stem
        if file_name not in table_uuid_mapping:
            print(
                f"Table {file_name} has no primary key specified to validate "
                f"duplicate entries. Please update the plugin code in "
                f"https://github.com/VoerEirAB/pre-commit-hooks.git"
            )
            continue

        alembic_version = extract_version(json_file)
        folder_type = extract_folder_type(json_file)
        operation_type = extract_operation_type(json_file)

        primary_keys = table_uuid_mapping[file_name]
        
        try:
            with open(json_file, encoding='UTF-8') as f:
                json_entries = json.load(f)
            _check_duplicate_entry()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not read {json_file}: {e}")
            continue

    if duplicate_entries:
        for key in duplicate_entries:
            if duplicate_entries[key]:
                alembic_version, folder_type, operation_type = key
                flag = True
                print(f"\n Detected duplicate entries within the same file:")
                print(f"  Version: {alembic_version}")
                print(f"  Location: {folder_type}/{operation_type}/")
                print(f"  Duplicates: {duplicate_entries[key]}")
    
    for (alembic_version, file_name, folder_type), entries in cross_operation_entries.items():
        for pkey_value, operation_types in entries.items():
            if len(operation_types) > 1:
                flag = True
                print(f"\n Detected entry in multiple {folder_type} operations:")
                print(f"  Version: {alembic_version}")
                print(f"  Table: {file_name}.json")
                print(f"  Entry: {pkey_value}")
                print(f"  Operations: {', '.join(sorted(operation_types))}")
                    
    return flag


if __name__ == "__main__":
    exit(main())
