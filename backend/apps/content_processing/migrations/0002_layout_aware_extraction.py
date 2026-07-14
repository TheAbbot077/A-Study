import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("content_processing", "0001_initial")]

    operations = [
        migrations.CreateModel(name="SourceDocumentProfile", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("pipeline_version", models.CharField(max_length=100)),
            ("source_filename", models.CharField(max_length=512)), ("file_extension", models.CharField(blank=True, max_length=32)), ("declared_content_type", models.CharField(blank=True, max_length=128)),
            ("detected_format", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX"), ("unknown", "Unknown")], max_length=32)), ("detected_mime_type", models.CharField(blank=True, max_length=128)),
            ("file_size_bytes", models.BigIntegerField()), ("source_checksum", models.CharField(max_length=128)), ("signature_summary", models.JSONField(default=dict)), ("page_count", models.PositiveIntegerField(blank=True, null=True)),
            ("encrypted", models.BooleanField(default=False)), ("password_required", models.BooleanField(default=False)), ("corrupt", models.BooleanField(default=False)), ("native_text_available", models.BooleanField(default=False)),
            ("native_text_quality", models.CharField(choices=[("high", "High"), ("moderate", "Moderate"), ("low", "Low"), ("none", "None"), ("unresolved", "Unresolved")], default="unresolved", max_length=32)), ("text_classification", models.CharField(choices=[("native_text", "Native Text"), ("scanned", "Scanned"), ("mixed", "Mixed"), ("empty_or_unresolved", "Empty Or Unresolved")], default="empty_or_unresolved", max_length=32)), ("ocr_requirement", models.CharField(choices=[("not_required", "Not Required"), ("recommended", "Recommended"), ("required", "Required"), ("unavailable", "Unavailable"), ("failed", "Failed")], default="not_required", max_length=32)),
            ("ocr_pages_recommended", models.JSONField(blank=True, default=list)), ("language_hints", models.JSONField(blank=True, default=list)), ("parser_recommendation", models.CharField(blank=True, max_length=128)),
            ("inspection_method", models.CharField(max_length=128)), ("inspector_name", models.CharField(max_length=128)), ("inspector_version", models.CharField(max_length=64)), ("inspection_confidence", models.FloatField(default=0)),
            ("warnings", models.JSONField(blank=True, default=list)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_profiles", to="content_processing.processingattempt")),
            ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_profiles", to="content_processing.contentprocessingjob")),
            ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_document_profiles", to="academic.learningresource")),
            ("stored_file", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="source_document_profiles", to="storage.storedfile")),
        ], options={"db_table": "content_processing_source_profile"}),
        migrations.CreateModel(name="DocumentExtraction", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("pipeline_version", models.CharField(max_length=100)), ("source_checksum", models.CharField(max_length=128)),
            ("extractor_name", models.CharField(max_length=128)), ("extractor_version", models.CharField(max_length=64)), ("ocr_engine", models.CharField(blank=True, max_length=128)), ("ocr_engine_version", models.CharField(blank=True, max_length=64)),
            ("extraction_method", models.CharField(choices=[("pdf_native", "PDF Native"), ("pdf_ocr", "PDF OCR"), ("pdf_mixed", "PDF Mixed"), ("docx_native", "DOCX Native"), ("unknown", "Unknown")], max_length=32)), ("page_count", models.PositiveIntegerField(blank=True, null=True)), ("native_text_pages", models.PositiveIntegerField(default=0)), ("ocr_pages", models.PositiveIntegerField(default=0)),
            ("block_count", models.PositiveIntegerField(default=0)), ("text_character_count", models.PositiveIntegerField(default=0)), ("warning_count", models.PositiveIntegerField(default=0)), ("result_checksum", models.CharField(max_length=128)),
            ("status", models.CharField(choices=[("completed", "Completed"), ("completed_with_warnings", "Completed With Warnings"), ("failed", "Failed")], default="completed", max_length=32)), ("created_at", models.DateTimeField(auto_now_add=True)), ("completed_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="document_extractions", to="content_processing.processingattempt")),
            ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="document_extractions", to="content_processing.contentprocessingjob")),
            ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="document_extractions", to="academic.learningresource")),
            ("source_document_profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="extractions", to="content_processing.sourcedocumentprofile")),
            ("stored_file", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="document_extractions", to="storage.storedfile")),
        ], options={"db_table": "content_processing_document_extraction"}),
        migrations.CreateModel(name="ExtractedBlock", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("pipeline_version", models.CharField(max_length=100)), ("page_reference", models.JSONField(blank=True, default=dict)),
            ("sequence_number", models.PositiveIntegerField()), ("page_sequence_number", models.PositiveIntegerField(default=0)), ("block_type", models.CharField(choices=[("title", "Title"), ("heading_1", "Heading 1"), ("heading_2", "Heading 2"), ("heading_3", "Heading 3"), ("paragraph", "Paragraph"), ("list_item", "List Item"), ("table", "Table"), ("table_row", "Table Row"), ("table_cell", "Table Cell"), ("caption", "Caption"), ("header", "Header"), ("footer", "Footer"), ("page_number", "Page Number"), ("toc_entry", "TOC Entry"), ("image", "Image"), ("footnote", "Footnote"), ("endnote", "Endnote"), ("equation", "Equation"), ("unknown", "Unknown")], max_length=32)), ("evidence_origin", models.CharField(choices=[("source_explicit", "Source Explicit"), ("layout_inferred", "Layout Inferred"), ("style_inferred", "Style Inferred"), ("ocr_inferred", "OCR Inferred"), ("parser_default", "Parser Default"), ("unknown", "Unknown")], max_length=32)),
            ("raw_text", models.TextField(blank=True)), ("normalized_text", models.TextField(blank=True)), ("character_count", models.PositiveIntegerField(default=0)), ("geometry", models.JSONField(blank=True, default=dict)),
            ("typography", models.JSONField(blank=True, default=dict)), ("structural_hints", models.JSONField(blank=True, default=dict)), ("source_method", models.CharField(max_length=64)),
            ("table_reference", models.CharField(blank=True, max_length=128)), ("image_reference", models.CharField(blank=True, max_length=128)), ("confidence", models.FloatField(default=0)), ("metadata", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extracted_blocks", to="content_processing.processingattempt")),
            ("document_extraction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks", to="content_processing.documentextraction")),
            ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extracted_blocks", to="content_processing.contentprocessingjob")),
            ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="extracted_blocks", to="academic.learningresource")),
            ("source_document_profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="blocks", to="content_processing.sourcedocumentprofile")),
            ("stored_file", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="extracted_blocks", to="storage.storedfile")),
        ], options={"db_table": "content_processing_extracted_block", "ordering": ["sequence_number"]}),
        migrations.AddConstraint(model_name="sourcedocumentprofile", constraint=models.UniqueConstraint(fields=("job", "attempt", "source_checksum", "pipeline_version", "inspector_version"), name="cp_profile_identity_unique")),
        migrations.AddConstraint(model_name="sourcedocumentprofile", constraint=models.CheckConstraint(condition=models.Q(inspection_confidence__gte=0, inspection_confidence__lte=1), name="cp_profile_confidence_range")),
        migrations.AddConstraint(model_name="documentextraction", constraint=models.UniqueConstraint(fields=("job", "attempt", "source_checksum", "pipeline_version", "extractor_version"), name="cp_extraction_identity_unique")),
        migrations.AddConstraint(model_name="extractedblock", constraint=models.UniqueConstraint(fields=("document_extraction", "sequence_number"), name="cp_block_sequence_unique")),
        migrations.AddConstraint(model_name="extractedblock", constraint=models.CheckConstraint(condition=models.Q(confidence__gte=0, confidence__lte=1), name="cp_block_confidence_range")),
        migrations.AddIndex(model_name="extractedblock", index=models.Index(fields=["job", "attempt"], name="cp_block_job_attempt_idx")),
        migrations.AddIndex(model_name="extractedblock", index=models.Index(fields=["document_extraction", "block_type"], name="cp_block_type_idx")),
    ]
