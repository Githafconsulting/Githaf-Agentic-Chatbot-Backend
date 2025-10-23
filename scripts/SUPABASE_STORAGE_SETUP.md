# Supabase Storage Setup Instructions

## Overview
This guide will help you set up the Supabase Storage bucket for storing document files (PDFs, DOCX, TXT).

## Option 1: Automatic Setup (via SQL Migration)

The SQL migration script `migrate_documents_schema.sql` includes commands to create the storage bucket automatically.

**Run the migration:**
```sql
-- Execute the entire migrate_documents_schema.sql file in Supabase SQL Editor
```

The migration will create:
- Bucket name: `documents`
- Privacy: Private (requires authentication)
- File size limit: 10MB
- Allowed types: PDF, TXT, DOCX, DOC

---

## Option 2: Manual Setup (via Supabase Dashboard)

If the SQL bucket creation doesn't work (some Supabase plans require dashboard setup), follow these steps:

### Step 1: Navigate to Storage
1. Open your Supabase project dashboard
2. Click **Storage** in the left sidebar
3. Click **New bucket** button

### Step 2: Configure Bucket
Fill in the following settings:

| Setting | Value |
|---------|-------|
| **Name** | `documents` |
| **Public bucket** | ❌ No (uncheck) |
| **File size limit** | `10485760` (10MB in bytes) |
| **Allowed MIME types** | See below |

**Allowed MIME types:**
```
application/pdf
text/plain
application/vnd.openxmlformats-officedocument.wordprocessingml.document
application/msword
```

### Step 3: Set Up Policies

After creating the bucket, set up access policies:

#### Policy 1: Allow authenticated uploads
```sql
CREATE POLICY "Authenticated users can upload documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents');
```

#### Policy 2: Allow authenticated reads
```sql
CREATE POLICY "Authenticated users can read documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents');
```

#### Policy 3: Allow authenticated updates
```sql
CREATE POLICY "Authenticated users can update documents"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'documents');
```

#### Policy 4: Allow authenticated deletes
```sql
CREATE POLICY "Authenticated users can delete documents"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents');
```

### Step 4: Get Storage Configuration

After setup, note these values for your `.env` file:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=documents
```

---

## Verification

### Test Upload (Python)
```python
from supabase import create_client

client = create_client(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-service-role-key"
)

# Test upload
with open("test.pdf", "rb") as f:
    response = client.storage.from_("documents").upload(
        path="test/test.pdf",
        file=f,
        file_options={"content-type": "application/pdf"}
    )

print(response)

# Get public URL (will require auth to access)
url = client.storage.from_("documents").get_public_url("test/test.pdf")
print(f"File URL: {url}")

# Delete test file
client.storage.from_("documents").remove(["test/test.pdf"])
```

### Test from Backend
```bash
cd backend
python -c "
from app.core.database import get_supabase_client
client = get_supabase_client()

# List buckets
buckets = client.storage.list_buckets()
print('Available buckets:', [b.name for b in buckets])

# Check if documents bucket exists
docs_bucket = [b for b in buckets if b.name == 'documents']
if docs_bucket:
    print('✅ documents bucket found!')
else:
    print('❌ documents bucket not found')
"
```

---

## Troubleshooting

### Issue: "Bucket not found"
**Solution:** Ensure the bucket name is exactly `documents` (lowercase, no spaces)

### Issue: "Permission denied"
**Solution:**
1. Check that you're using the **service_role** key, not the anon key
2. Verify RLS policies are set up correctly
3. Ensure bucket policies exist

### Issue: "File type not allowed"
**Solution:** Add the MIME type to allowed types in bucket settings

### Issue: "File too large"
**Solution:** Increase file size limit in bucket settings (default 10MB)

---

## Storage Pricing

**Supabase Free Tier:**
- 1GB storage included
- 2GB bandwidth/month

**Paid Plans:**
- $0.021 per GB storage/month
- $0.09 per GB bandwidth

**Estimate for your use case:**
- 100 PDFs × 500KB average = 50MB (~$0.001/month)
- Very affordable!

---

## Next Steps

After storage is set up:
1. ✅ Run database migration: `migrate_documents_schema.sql`
2. ✅ Create backend storage service: `app/services/storage_service.py`
3. ✅ Update document service to use storage
4. ✅ Test file upload via API
