# Project Setup

### Configure the environment
```bash
cp .env.example .env
```

### Create the directories
```bash
mkdir -p ./dags ./logs ./plugins ./config
```

### Initialize the database (run once)
```bash
docker compose up airflow-init
```

### Run everything
```bash
docker compose up -d
```

### Get admin user password
```bash
docker logs -f airflow-api-server
```

### (Optional) Scale workers
```bash
docker compose up -d --scale airflow-worker=3
```

### (Optional) Activate Flower
```bash
docker compose --profile flower up -d
```

### Generate the necessary keys
```bash
# Fernet Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# API Secret Key
python -c "import secrets; print(secrets.token_hex(64))"
# Webserver Secret Key
python -c "import secrets; print(secrets.token_hex(32))"
```
