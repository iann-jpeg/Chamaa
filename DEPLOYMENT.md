# CHAMAA deployment

## Render backend

1. Create a Render Web Service from this repository.
2. Render reads `render.yaml`.
3. Set `MONGODB_URI` to an Atlas SRV URI.
4. Set `MONGODB_DB_NAME` to `chamaa`.
5. Set `DJANGO_ALLOWED_HOSTS` to the Render hostname and any custom backend domain.
6. Set `CSRF_TRUSTED_ORIGINS` to the HTTPS frontend and backend origins.
7. Set `CORS_ALLOWED_ORIGINS` to the Vercel frontend origin.
8. Deploy and run migrations.

Example:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Local development may use SQLite when `MONGODB_URI` is absent. Render production must set `MONGODB_URI`; otherwise the health endpoint reports SQLite locally.

## MongoDB Atlas

- Create an Atlas database user with least-privilege access to the CHAMAA database.
- Allow only required Render egress IPs or configure Atlas network access for the deployment.
- Use the TLS SRV URI in `MONGODB_URI`.
- Never commit the URI or database password.

## Vercel frontend

Deploy the `frontend/` directory to Vercel.

Set the Vercel environment variable:

```text
RENDER_BACKEND_URL=https://your-chamaa-service.onrender.com
```

The catch-all proxy forwards the existing Django templates, authentication forms, CSRF-protected posts and static URLs to Render.
