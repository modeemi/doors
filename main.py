from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Field, Session, SQLModel, create_engine, select
from enum import Enum
from datetime import datetime, timezone
from argon2 import PasswordHasher


class SpaceEventState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class SpacePublic(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    logo: str = Field(default=None, nullable=False)
    url: str = Field(default=None, nullable=False)
    address: str = Field(default=None, nullable=True)
    lat: float = Field(default=None, nullable=True)
    lon: float = Field(default=None, nullable=True)
    contact_email: str = Field(default=None, nullable=False)


class Space(SpacePublic, table=True):
    basic_auth_password: str = Field()


class SpaceEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="space.id")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True)
    state: SpaceEventState = Field(
        sa_column_kwargs={"default": SpaceEventState.UNKNOWN})


def hash_password(password: str) -> str:
    """Hash password using argon2id"""
    return PasswordHasher().hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    """Verify password using argon2id"""
    try:
        return PasswordHasher().verify(hashed_password, password)
    except:
        return False


def authenticate(credentials: HTTPBasicCredentials, session: Session, space: Space) -> bool:
    """Authenticate user using basic auth"""
    if not space:
        return False
    if not verify_password(space.basic_auth_password, credentials.password):
        return False
    if credentials.username != space.name:
        return False
    return True


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()
security = HTTPBasic()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Create a default space for testing
    with Session(engine) as session:
        space = session.exec(select(Space).where(Space.id == 1)).first()
        if not space:
            # Hash the password using hashlib with blake 2b with salt
            hashed_password = hash_password("dummy_password")
            default_space = Space(
                id=1,
                name="ModeemiDummySpace",
                basic_auth_password=hashed_password,
                logo="https://trey.fi/media/modeemi-logo-ttyy-1.png",
                url="https://modeemi.fi",
                address="Tietotalo, huone TA013, Korkeakoulunkatu 1, FIN-33720 Tampere, Finland",
                lat=61.449940,
                lon=23.857036,
                contact_email="modeemi@example.org"
            )
            session.add(default_space)
            session.commit()
            # Add an initial unknown event
            initial_event = SpaceEvent(
                space_id=1, state=SpaceEventState.UNKNOWN)
            session.add(initial_event)
            session.commit()


@app.get("/space/by_id/{space_id}", response_model=SpacePublic)
def read_space(space_id: int, session: SessionDep) -> Space:
    space = session.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@app.get("/space/by_name/{space_name}", response_model=SpacePublic)
def read_space_by_name(space_name: str, session: SessionDep) -> Space:
    space = session.exec(select(Space).where(Space.name == space_name)).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


@app.post("/space_events/")
def create_space_event(event: SpaceEvent, session: SessionDep, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> SpaceEvent:
    space = session.get(Space, event.space_id)
    if not space or not authenticate(credentials, session, space):
        raise HTTPException(status_code=status.H, detail="Forbidden")
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@app.post("/space_events/{space_id}/open", response_model=SpaceEvent)
def open_space(space_id: int, session: SessionDep, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> SpaceEvent:
    space = session.get(Space, space_id)
    if not authenticate(credentials, session, space):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    event = SpaceEvent(space_id=space_id, state=SpaceEventState.OPEN)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@app.post("/space_events/{space_id}/close", response_model=SpaceEvent)
def close_space(space_id: int, session: SessionDep, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> SpaceEvent:
    space = session.get(Space, space_id)
    if not authenticate(credentials, session, space):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    event = SpaceEvent(space_id=space_id, state=SpaceEventState.CLOSED)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@app.get("/space_events/{space_id}")
def read_space_events(
    space_id: int,
    session: SessionDep,
    skip: int = 0,
    limit: int = Query(default=100, lte=1000)
):
    events = session.exec(
        select(SpaceEvent).where(SpaceEvent.space_id ==
                                 space_id).offset(skip).limit(limit)
    ).all()
    return events


@app.get("/space_events/{space_id}/latest", response_model=SpaceEvent)
def read_latest_space_event(space_id: int, session: SessionDep):
    event = session.exec(
        select(SpaceEvent).where(SpaceEvent.space_id ==
                                 space_id).order_by(SpaceEvent.timestamp.desc())
    ).first()
    if not event:
        raise HTTPException(
            status_code=404, detail="No events found for this space")
    return event


# SpaceAPI response
@app.get("/space/{space_name}/space.json")
def space_api(space_name: str, session: SessionDep):
    space = session.exec(select(Space).where(Space.name == space_name)).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    latest_event = session.exec(
        select(SpaceEvent).where(SpaceEvent.space_id ==
                                 space.id).order_by(SpaceEvent.timestamp.desc())
    ).first()
    state = latest_event.state if latest_event else SpaceEventState.UNKNOWN
    return {
        "api_compatibility": ["15"],
        "space": space.name,
        "logo": space.logo,
        "url": space.url,
        "location": {
            "address": space.address,
            "lat": space.lat,
            "lon": space.lon
        },
        "state": {
            "open": state == SpaceEventState.OPEN,
            "lastchange": int(latest_event.timestamp.timestamp()) if latest_event else None
        },
        "contact": {
            "email": space.contact_email
        }
    }
