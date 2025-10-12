import typer
from getpass import getpass
from sqlmodel import Session, select
from main import Space, hash_password, engine

app = typer.Typer()


@app.command()
def create_space(
    name: str = typer.Option(None, help="Space name"),
    logo: str = typer.Option(None, help="Logo URL"),
    url: str = typer.Option(None, help="Website URL"),
    address: str = typer.Option(None, help="Address"),
    lat: float = typer.Option(None, help="Latitude"),
    lon: float = typer.Option(None, help="Longitude"),
    contact_email: str = typer.Option(None, help="Contact email"),
    password: str = typer.Option(
        None, help="Basic auth password (leave empty to prompt)")
):
    """Create a new space interactively or via CLI options."""
    if not name:
        name = typer.prompt("Space name")
    if logo is None:
        logo = typer.prompt("Logo URL (optional)", default=None)
    if url is None:
        url = typer.prompt("Website URL (optional)", default=None)
    if address is None:
        address = typer.prompt("Address (optional)", default=None)
    if lat is None:
        lat_str = typer.prompt("Latitude (optional)", default=None)
        lat = float(lat_str) if lat_str else None
    if lon is None:
        lon_str = typer.prompt("Longitude (optional)", default=None)
        lon = float(lon_str) if lon_str else None
    if contact_email is None:
        contact_email = typer.prompt("Contact email (optional)", default=None)
    if not password:
        password = getpass("Basic auth password: ")
    hashed_password = hash_password(password)

    with Session(engine) as session:
        existing = session.exec(
            select(Space).where(Space.name == name)).first()
        if existing:
            typer.echo("A space with this name already exists.")
            raise typer.Exit(code=1)
        space = Space(
            name=name,
            logo=logo,
            url=url,
            address=address,
            lat=lat,
            lon=lon,
            contact_email=contact_email,
            basic_auth_password=hashed_password
        )
        session.add(space)
        session.commit()
        typer.echo(f"Space '{name}' created with id {space.id}")


@app.command()
def delete_space(
    space_id: int = typer.Argument(..., help="ID of the space to delete"),
    yes: bool = typer.Option(False, "--yes", "-y",
                             help="Confirm deletion without prompting")
):
    """Delete a space by its ID."""
    with Session(engine) as session:
        space = session.get(Space, space_id)
        if not space:
            typer.echo("Space not found.")
            raise typer.Exit(code=1)
        if yes or typer.confirm(f"Are you sure you want to delete the space '{space.name}' (ID: {space.id})?"):
            session.delete(space)
            session.commit()
            typer.echo(f"Space '{space.name}' deleted.")
        else:
            typer.echo("Deletion cancelled.")


if __name__ == "__main__":
    app()
