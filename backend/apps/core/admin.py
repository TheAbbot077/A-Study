from django.contrib import admin

from apps.core.models import BusinessEventDelivery, BusinessEventRecord


@admin.register(BusinessEventRecord)
class BusinessEventRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "event_type", "source_entity_type", "source_entity_id", "tenant", "occurred_at", "created_at"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["id", "event_type", "source_entity_type", "source_entity_id"]
    readonly_fields = ["id", "event_type", "source_entity_type", "source_entity_id", "tenant", "safe_payload", "occurred_at", "correlation_id", "causation_event_id", "created_at", "updated_at"]


@admin.register(BusinessEventDelivery)
class BusinessEventDeliveryAdmin(admin.ModelAdmin):
    list_display = ["id", "event", "consumer_key", "status", "attempt_count", "last_attempt_at", "next_attempt_at", "delivered_at"]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = ["id", "consumer_key", "event__id", "event__event_type"]
    readonly_fields = ["id", "event", "consumer_key", "status", "attempt_count", "last_attempt_at", "next_attempt_at", "processing_started_at", "delivered_at", "failure_code", "failure_detail_safe", "created_at", "updated_at"]
