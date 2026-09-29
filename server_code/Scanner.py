import asyncio
import importlib

import anvil.server
from user_scanner.core.engine import check
from user_scanner.core.helpers import (
    get_site_name,
    is_loud,
    is_valid_email,
    load_categories,
)
from user_scanner.core.result import Result


_SCAN_TYPES = {"username": False, "email": True}


def _get_categories(scan_type):
    is_email = _SCAN_TYPES[scan_type]
    return load_categories(is_email=is_email, no_nsfw=True)


@anvil.server.callable
def get_scan_catalog(scan_type, category=None):
    if not isinstance(scan_type, str) or scan_type not in _SCAN_TYPES:
        return {"ok": False, "message": "Choose username or email scanning."}

    categories = _get_categories(scan_type)
    if category is None:
        return {
            "ok": True,
            "categories": [
                {"value": name, "label": name.replace("_", " ").title()}
                for name in sorted(categories, key=str.casefold)
            ],
        }

    category_entry = next(
        (
            entry
            for name, entry in categories.items()
            if name.casefold() == str(category).casefold()
        ),
        None,
    )
    if category_entry is None:
        return {"ok": False, "message": "Choose a category from the list."}

    return {
        "ok": True,
        "modules": [
            {"value": path.stem, "label": path.stem.replace("_", " ").title()}
            for path in sorted(
                category_entry.glob("*.py"), key=lambda path: path.stem.casefold()
            )
            if path.name != "__init__.py"
        ],
    }


@anvil.server.callable
def scan_module(target, scan_type, category, module_name):
    if not isinstance(scan_type, str) or scan_type not in _SCAN_TYPES:
        return {"ok": False, "message": "Choose username or email scanning."}

    if not isinstance(target, str):
        return {"ok": False, "message": "Enter a username or email address."}
    target = target.strip()
    if scan_type == "email":
        if not is_valid_email(target):
            return {"ok": False, "message": "Enter a valid email address."}
    elif (
        not target
        or len(target) > 64
        or any(character.isspace() for character in target)
        or any(character in target for character in "/?#")
    ):
        return {
            "ok": False,
            "message": "Enter a username up to 64 characters without spaces or / ? #.",
        }

    if not isinstance(category, str) or not isinstance(module_name, str):
        return {"ok": False, "message": "Choose a category and platform."}

    categories = _get_categories(scan_type)
    category_name = next(
        (name for name in categories if name.casefold() == category.casefold()),
        None,
    )
    if category_name is None:
        return {"ok": False, "message": "Choose a category from the list."}

    category_path = categories[category_name]
    module_path = next(
        (
            path
            for path in category_path.glob("*.py")
            if path.name != "__init__.py" and path.stem == module_name
        ),
        None,
    )
    if module_path is None:
        return {"ok": False, "message": "Choose a platform from the list."}

    mode_folder = "email_scan" if _SCAN_TYPES[scan_type] else "user_scan"
    scan_module_object = importlib.import_module(
        f"user_scanner.{mode_folder}.{category_name}.{module_path.stem}"
    )

    site_name = get_site_name(scan_module_object)
    if is_loud(site_name, is_email=_SCAN_TYPES[scan_type]):
        result = Result.skipped().update(
            username=target,
            site_name=site_name,
            category=category_name.title(),
            is_email=_SCAN_TYPES[scan_type],
        )
    else:
        result = asyncio.run(check(scan_module_object, target))

    return {"ok": True, "results": [result.to_dict()]}
