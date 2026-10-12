# TaskBoard

Application de gestion de tâches utilisée pour le TP Docker (Compose → Swarm).

```
navigateur ──► frontend (React servi par nginx :80)
                  │  /api/*  (reverse proxy)
                  ▼
               backend (Flask + gunicorn :5000) ──► db (MySQL 8.4 :3306)
                                                └─► redis (Redis 7.4 :6379)
```

## Arborescence

```
backend/    API Flask (app.py, requirements.txt)
frontend/   SPA React/Vite + nginx.conf (reverse proxy /api → backend:5000)
db/         init.sql (schéma + données initiales)
```

## Backend — variables d'environnement

| Variable        | Défaut      | Rôle                                   |
|-----------------|-------------|----------------------------------------|
| `DB_HOST`       | `db`        | Hôte MySQL                             |
| `DB_PORT`       | `3306`      | Port MySQL                             |
| `DB_NAME`       | `taskboard` | Base de données                        |
| `DB_USER`       | `taskboard` | Utilisateur MySQL                      |
| `DB_PASSWORD`   | *(vide)*    | Mot de passe MySQL                     |
| `REDIS_HOST`    | `redis`     | Hôte Redis                             |
| `REDIS_PORT`    | `6379`      | Port Redis                             |
| `APP_VERSION`   | `dev`       | Version affichée dans l'interface      |
| `FAIL_HEALTH`   | *(vide)*    | Si défini, `/api/health` renvoie 503   |

Toute variable `X` peut être fournie via un fichier : `X_FILE=/chemin/vers/fichier`
(compatible avec les *Docker secrets*, ex. `DB_PASSWORD_FILE=/run/secrets/db_password`).

Lancement en production : `gunicorn --bind 0.0.0.0:5000 --workers 2 app:app`

## API

| Méthode  | Route              | Description                                                |
|----------|--------------------|------------------------------------------------------------|
| `GET`    | `/api/health`      | État DB + Redis (200 ou 503)                               |
| `GET`    | `/api/info`        | Hostname du conteneur, version, compteur de visites (Redis) |
| `GET`    | `/api/tasks`       | Liste des tâches (cache Redis 30 s, champ `source`)        |
| `POST`   | `/api/tasks`       | Créer une tâche `{"title": "..."}`                          |
| `PATCH`  | `/api/tasks/<id>`  | Basculer l'état terminé                                    |
| `DELETE` | `/api/tasks/<id>`  | Supprimer                                                  |

## Frontend

- Build : `npm ci && npm run build` → fichiers statiques dans `dist/`
- `nginx.conf` sert `dist/` et redirige `/api/` vers `http://backend:5000`.
- Dev local (optionnel) : `npm run dev` (proxy `/api` → `localhost:5000`).

## Base de données

`db/init.sql` doit être exécuté au premier démarrage de MySQL
(l'image officielle exécute les scripts de `/docker-entrypoint-initdb.d/` lorsque le volume de données est vide).
