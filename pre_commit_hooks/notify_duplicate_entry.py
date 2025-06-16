import argparse
import json
from typing import Optional
from typing import Sequence
from pathlib import Path
import re


def extract_version(filepath: str) -> str:
    """Extract Alembic version from the filename."""
    return Path(filepath).parents[2].name.strip()

def extract_folder_type(filepath: str) -> str:
    """Extract the folder type from the file path."""
    return Path(filepath).parents[1].name.strip()

def main(argv: Optional[Sequence[str]] = None) -> int:

    def _check_duplicate_entry():
        """ Check duplicate entry based on pkey criteria.

        :param json_entries: List of json entries
        :param pkeys: List of Primary keys
        :return: list of duplicated entry pkey value tuples
        """
        for entry in json_entries:
            pkey_value_tuple = tuple(entry[pkey] for pkey in primary_keys)
            if pkey_value_tuple not in unique_entries[alembic_version][folder_type]:
                unique_entries[alembic_version][folder_type].add(pkey_value_tuple)
            else:
                duplicate_entries[alembic_version][folder_type].add(pkey_value_tuple)

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
    filenames = args['filenames']
    flag = False

    unique_entries = {}
    duplicate_entries = {}

    for json_file in filenames:
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
        if alembic_version not in unique_entries:
            unique_entries[alembic_version] = {'upgrade': set(), 'downgrade': set()}
            duplicate_entries[alembic_version] = {'upgrade': set(), 'downgrade': set()}

        primary_keys = table_uuid_mapping[file_name]
        with open(json_file, encoding='UTF-8') as f:
            json_entries = json.load(f)
        _check_duplicate_entry()

    if duplicate_entries:
        for alembic_version in duplicate_entries:
            for folder_type in duplicate_entries[alembic_version]:
                if duplicate_entries[alembic_version][folder_type]:
                    flag = True
                    print(f"Detected duplicate entries in '{folder_type}' directory for Alembic version '{alembic_version}':")
                    print(f"  - {duplicate_entries[alembic_version][folder_type]}")
    return flag


if __name__ == "__main__":
    exit(main())
