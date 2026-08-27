from pathlib import Path

from c2_imugs2.contracts.docs import build_docs_navigation, generate_contract_documents


def on_config(config, **kwargs):
    """Generate grouped pages and derive navigation from extracted contracts."""

    repo_root = Path(config.config_file_path).resolve().parent
    generate_contract_documents(repo_root)
    config["nav"] = build_docs_navigation(repo_root)
    return config


def on_pre_build(config, **kwargs):
    """Refresh generated contracts before every build and live-server rebuild."""

    repo_root = Path(config.config_file_path).resolve().parent
    generate_contract_documents(repo_root)
