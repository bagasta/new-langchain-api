# Google Sign-In Setup Guide

To enable Google Sign-In for this project, you need to configure a project in the Google Cloud Console. You do **not** need Firebase for this implementation; it uses standard Google OAuth 2.0.

## 1. Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.

## 2. Configure OAuth Consent Screen
1. Navigate to **APIs & Services > OAuth consent screen**.
2. Select **External** (unless you are testing only within your organization) and click **Create**.
3. Fill in the required app information (App name, User support email, Developer contact information).
4. Click **Save and Continue**.
5. (Optional) Add scopes if needed, but the default `email`, `profile`, and `openid` are usually sufficient for login.
6. Add test users (your email) if the app is in "Testing" status.

## 3. Create Credentials
1. Navigate to **APIs & Services > Credentials**.
2. Click **Create Credentials** and select **OAuth client ID**.
3. Select **Web application** as the application type.
4. Name your client (e.g., "LangChain API").
5. **Authorized JavaScript origins**:
   - Add the URL of your frontend (e.g., `http://localhost:3000`).
6. **Authorized redirect URIs**:
   - Add the callback URL of your API.
   - For local development, this is typically: `http://localhost:8000/api/v1/auth/google/callback`
   - (Adjust the port/domain if you are using a different setup).
7. Click **Create**.

## 4. Configure Environment Variables
Copy the **Client ID** and **Client Secret** and update your `.env` file:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

> [!IMPORTANT]
> Ensure `GOOGLE_REDIRECT_URI` matches exactly what you entered in the Google Cloud Console.

## 5. Usage
- **Login**: Direct users to `GET /api/v1/auth/google/login`.
- **Callback**: Google will redirect back to `/api/v1/auth/google/callback`, which will process the login and create/return the user session.
