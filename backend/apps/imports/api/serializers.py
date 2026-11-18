"""Serializers for Import jobs, records, and duplicate resolution."""

from __future__ import annotations

from rest_framework import serializers

from apps.imports.models import (
    DuplicateCandidate,
    DuplicateCandidateDecision,
    ImportJob,
    ImportRecord,
)


class DuplicateCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DuplicateCandidate
        fields = [
            "id",
            "existing_transaction_id",
            "score",
            "reasons",
            "decision",
            "decided_at",
        ]


class ImportRecordSerializer(serializers.ModelSerializer):
    duplicate_candidates = DuplicateCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = ImportRecord
        fields = [
            "id",
            "row_number",
            "raw",
            "normalized",
            "status",
            "action",
            "errors",
            "duplicate_candidates",
        ]


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = [
            "id",
            "account_id",
            "file_name",
            "file_format",
            "status",
            "mapping",
            "row_count",
            "valid_count",
            "invalid_count",
            "duplicate_count",
            "imported_count",
            "error_summary",
            "created_at",
            "finished_at",
        ]


class DuplicateResolveSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField(required=True)
    decision = serializers.ChoiceField(
        choices=[DuplicateCandidateDecision.IMPORT, DuplicateCandidateDecision.SKIP],
        required=True,
    )
