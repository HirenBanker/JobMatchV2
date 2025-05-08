# JobMatch Admin Access Guide

This document outlines the hidden admin access methods implemented in the JobMatch application. These methods are intentionally not documented in the main README to maintain security through obscurity.

## Admin Access Methods

There are three ways to access the admin portal:

1. **Keyboard Shortcut**: Press `Ctrl+Alt+A` on any page of the application
2. **Hidden Clickable Area**: Click the invisible dot in the bottom-right corner of the page
3. **URL Parameter**: Add `?admin_access=jobmatch_admin_2024` to the URL

Example URL with admin parameter:
```
https://your-jobmatch-app.com/?admin_access=jobmatch_admin_2024
```

## First-Time Admin Setup

When accessing the admin portal for the first time with a fresh database:

1. You'll see a warning that no administrator account exists
2. Use the form to create an administrator account
3. Default credentials are pre-filled (username: `admin`, email: `admin@jobmatch.com`, password: `admin123`)
4. For production environments, use a strong password instead of the default

## Admin Features

Once logged in as an administrator, you can:

- View all users, job seekers, and job givers
- Manage job listings
- Process credit redemption requests
- View platform statistics
- Manage credit packages

## Security Notes

- The admin access methods are hidden from regular users
- Access attempts are logged (when logging is enabled)
- In production, consider changing the admin access parameter value
- The default admin credentials should be changed in production environments

## Troubleshooting

If you cannot access the admin portal:

1. Ensure your database connection is working
2. Check if the admin user exists in the database
3. If needed, you can run the `create_admin.py` script directly:
   ```
   python create_admin.py
   ```
4. For persistent issues, check the database logs for errors

## Changing Admin Access Parameter

To change the admin access parameter, modify the following line in `app.py`:

```python
if "admin_access" in params and params["admin_access"][0] == "jobmatch_admin_2024":
```

Replace `jobmatch_admin_2024` with your preferred secret value.