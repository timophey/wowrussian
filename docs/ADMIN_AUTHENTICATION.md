# Admin Authentication: Admin Key to Role-Based Transition

## Overview

The system supports two authentication methods for admin access:

1. **Admin Key (Legacy)**: A shared secret key passed via `X-Admin-Key` header or `admin_key` query parameter
2. **Role-Based (Recommended)**: JWT token authentication with `admin` role assigned to the user

## User Roles

Users can have one of two roles:

- **`user`**: Regular user with access to their own projects only
- **`admin`**: Administrator with full access to user management and all projects

## Migration from Admin Key to Role-Based Admin

### Why Migrate?

The admin key method requires passing a secret key with every request. Role-based authentication:
- Uses standard JWT tokens (same as regular login)
- Provides better audit trails (actions are tied to specific users)
- Supports multiple administrators
- Is more secure (no shared secrets)

### Migration Process

1. **Prerequisites**: You must have access to the admin secret key (`ADMIN_SECRET_KEY` in environment)

2. **Execute Migration**: Call the migration endpoint with the admin key:

   ```bash
   curl -X POST "http://localhost:8000/api/admin/migrate-admin-role?admin_key=YOUR_SECRET_KEY"
   ```

   Or via the admin panel UI:
   - Log in to the admin panel with the admin key
   - Click "Migrate to Role" button

3. **Result**: The first user (ID=1) will be assigned the `admin` role

4. **After Migration**: 
   - Log in normally with email/password
   - The admin panel will show "Role-based Admin" badge
   - All admin endpoints now accept JWT tokens with `Authorization: Bearer <token>` header

## API Endpoints

### Admin Authentication

All admin endpoints support both authentication methods:

**Legacy (Admin Key)**:
```
GET /api/admin/users?admin_key=YOUR_SECRET_KEY
```

**Role-Based (JWT)**:
```
GET /api/admin/users
Authorization: Bearer <jwt_token>
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users with roles |
| POST | `/api/admin/users` | Create a new user |
| DELETE | `/api/admin/users/{id}` | Delete a user |
| PATCH | `/api/admin/users/{id}/role` | Update user role |
| GET | `/api/admin/users/{id}/projects` | View user's projects |
| POST | `/api/admin/migrate-admin-role` | Migrate first user to admin role |

### Updating User Role

```bash
curl -X PATCH "http://localhost:8000/api/admin/users/2/role" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{"role": "admin"}'
```

Valid roles: `"user"`, `"admin"`

## Database Schema

The `users` table now includes a `role` column:

```sql
ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'user';
```

For PostgreSQL, this uses a proper ENUM type:
```sql
CREATE TYPE userrole AS ENUM ('user', 'admin');
```

## Frontend Integration

The admin panel (`AdminPage.js`) automatically detects the authentication method:

- If the logged-in user has `role: "admin"`, it uses JWT token authentication
- Otherwise, it falls back to admin key authentication
- A "Migrate to Role" button is available for key-based admins

## Security Notes

1. **Admin Key**: Should be stored securely in environment variables (`ADMIN_SECRET_KEY`)
2. **JWT Tokens**: Expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 minutes)
3. **Role Checks**: All admin endpoints verify the user's role before allowing access
4. **Primary Admin**: User ID 1 cannot be deleted or demoted (safety measure)

## Troubleshooting

### "Admin privileges required" Error

This means your user doesn't have the `admin` role. Solutions:
1. Log in with a user that has admin role
2. Use the admin key method
3. Run the migration endpoint

### "Invalid or missing admin key" Error

The admin key is incorrect or missing. Check your `ADMIN_SECRET_KEY` environment variable.

### Migration Fails

Ensure:
- The admin key is correct
- At least one user exists in the system
- The database migration (011) has been applied
