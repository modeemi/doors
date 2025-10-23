Python server that receives door events, sends Telegram messages based on them and exposes [SpaceAPI](https://spaceapi.io/) endpoints.


## How to dev

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

OpenAPI docs will be at [http://localhost:8000/docs](http://localhost:8000/docs)

## Creating a new space

You can use `manage.py` to add a new space to the database:

```
python manage.py create-space --help
```

## Deleting a space

```
python manage.py delete-space --help
```

## Setting space status
```
curl -X POST "http://localhost:8000/space_events/1/open" -u ModeemiDummySpace:dummy_password
curl -X POST "http://localhost:8000/space_events/1/close" -u ModeemiDummySpace:dummy_password
```

## Test

```
pytest
```


## How to run prod

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fastapi run main.py
```