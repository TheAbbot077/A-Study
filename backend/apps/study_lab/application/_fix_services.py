import sys
with open('backend/apps/study_lab/application/services.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize line endings
content = content.replace('\r\n', '\n')

# Add F import
content = content.replace(
    'from django.db import transaction\nfrom django.utils import timezone',
    'from django.db import transaction\nfrom django.db.models import F\nfrom django.utils import timezone'
)

# Fix models.F -> F
content = content.replace('models.F("version")', 'F("version")')
content = content.replace('models_F("version")', 'F("version")')

# Remove duplicate section at bottom
marker = '# Import models.F for _upsert_availability'
if marker in content:
    idx = content.index(marker)
    content = content[:idx].rstrip() + '\n'

# Remove _original_upsert reference
content = content.replace('_original_upsert = _upsert_availability\n', '')

with open('backend/apps/study_lab/application/services.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('FIXED')