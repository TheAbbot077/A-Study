# Storage Security Model

PI-9.2 hardens the storage bounded context so every `StoredFile` carries an explicit security context.

## Ownership and tenant context

- `StoredFile.owner` identifies the owning learner or staff actor when the file is privately uploaded.
- `StoredFile.tenant` records an institution context when one is deterministically available.
- `StoredFile.security_scope` controls the access rule applied by `ResolveStoredFileAccessService`.

## Access policy

- Private learner files are visible to the owner only.
- Institution-shared files are visible only within the matching institution context.
- Legacy unrestricted access is not inferred.
- Any row without a valid security context is treated fail-closed.

## API behavior

- Uploads derive ownership from the authenticated actor.
- List and object access are scoped through the canonical access resolver.
- Stored file events and logs emit identifiers only.

## Production security

- Production settings refuse missing or known-default `DJANGO_SECRET_KEY` values.
- The production path must use an explicit, non-default secret key.
