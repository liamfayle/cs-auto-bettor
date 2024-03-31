from pathlib import Path
current_directory = Path(__file__).parent.parent
current_directory_str = str(current_directory).replace('\\', '/')
import sys
sys.path.append(current_directory_str)

from models.models import *
from sqlalchemy import or_


def get_open_positions():
    session = Session()
    values = session.query(Position).filter(Position.status=='open').all()
    session.close()
    return values


def get_closed_positions():
    session = Session()
    values = session.query(Position).filter(or_(Position.status=='lost', Position.status=='won')).all()
    session.close()
    return values