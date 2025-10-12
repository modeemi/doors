
## How to dev

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
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