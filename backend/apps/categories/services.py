"""Category services: creation, hierarchy validation, and safe archival with reassignment."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.categories.models import Category

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


class CategoryError(ValueError):
    """Base error for category domain errors."""


class CategoryDepthExceededError(CategoryError):
    """Category hierarchy cannot exceed 2 levels."""


class CategoryInUseError(CategoryError):
    """Category has active transactions and cannot be deleted or archived without reassignment."""


def create_category(
    *,
    workspace: Workspace,
    name: str,
    kind: str,
    parent_id: uuid.UUID | None = None,
    icon: str | None = None,
    color: str | None = None,
    is_system: bool = False,
    sort_order: int = 0,
) -> Category:
    """Create a category enforcing the 2-level hierarchy depth limit and kind matching."""
    parent = None
    if parent_id:
        parent = Category.objects.get(id=parent_id, workspace=workspace)
        if parent.parent_id is not None:
            raise CategoryDepthExceededError(
                "Subcategories cannot have subcategories (maximum depth is 2 levels)."
            )
        if parent.kind != kind:
            raise ValueError(
                f"Subcategory must have the same kind as parent "
                f"(parent is '{parent.kind}', requested '{kind}')."
            )

    return Category.objects.create(
        workspace=workspace,
        name=name.strip(),
        kind=kind,
        parent=parent,
        icon=icon,
        color=color,
        is_system=is_system,
        sort_order=sort_order,
    )


def archive_category(
    *,
    workspace: Workspace,
    category_id: uuid.UUID,
    reassign_to_category_id: uuid.UUID | None = None,
) -> Category:
    """Safely archive a category, requiring reassignment if transactions or splits reference it."""
    with transaction.atomic():
        cat = Category.objects.select_for_update().get(id=category_id, workspace=workspace)
        if cat.is_archived:
            return cat

        # Check references in active transactions and splits
        tx_count = cat.transactions.filter(is_archived=False).count()
        split_count = cat.splits.filter(transaction__is_archived=False).count()

        if tx_count > 0 or split_count > 0:
            if not reassign_to_category_id:
                raise CategoryInUseError(
                    f"Category '{cat.name}' has {tx_count + split_count} active transaction(s) "
                    "and cannot be archived without reassignment."
                )

            reassign_cat = Category.objects.get(id=reassign_to_category_id, workspace=workspace)
            if reassign_cat.id == cat.id:
                raise ValueError(
                    "Cannot reassign transactions to the same category being archived."
                )
            if reassign_cat.kind != cat.kind:
                raise ValueError("Cannot reassign transactions to a category of different kind.")

            cat.transactions.filter(is_archived=False).update(category=reassign_cat)
            cat.splits.filter(transaction__is_archived=False).update(category=reassign_cat)

        cat.is_archived = True
        cat.archived_at = timezone.now()
        cat.save(update_fields=["is_archived", "archived_at", "updated_at"])

        # Archive child subcategories as well
        cat.children.filter(is_archived=False).update(
            is_archived=True,
            archived_at=timezone.now(),
        )

        return cat
