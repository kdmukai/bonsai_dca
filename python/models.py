import datetime
import dateutil
import os

from decimal import Decimal
from pathlib import Path
from peewee import *
from playhouse.sqlite_ext import JSONField


data_dir = os.path.join(Path.home(), ".bonsai_dca")
Path(data_dir).mkdir(parents=True, exist_ok=True)
DATABASE = os.path.join(data_dir, "data.db")

# Create a database instance that will manage the connection and
# execute queries
db = SqliteDatabase(DATABASE)


def create_tables():
    # Called on every launch
    def table_exists(name):
        with db:
            c = db.cursor()
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}'")
            result = c.fetchone()
            return result is not None and name in result 

    with db:
        if not table_exists('apicredential'):
            db.create_tables([APICredential])
        if not table_exists('dcaschedule'):
            db.create_tables([DCASchedule])
        if not table_exists('order'):
            db.create_tables([Order])


# Create a base class all our models will inherit, which defines
# the database we'll be using.
class BaseModel(Model):
    class Meta:
        database = db



class APICredential(BaseModel):
    EXCHANGE__COINBASE = 'coinbase'
    EXCHANGE__GEMINI = 'gemini'
    EXCHANGE__PAXOS = 'paxos'

    exchange = CharField()
    client_key = CharField()
    client_secret = CharField()
    created = DateTimeField(default=datetime.datetime.now)

    @property
    def client_key_last_six(self):
        return self.client_key[-6:]



class DCASchedule(BaseModel):
    """
        A schedule whose `is_active == True` will appear in the UI but the `is_paused`
        toggle decides whether or not to keep running it.

        But when `is_active` == False, the schedule is essentially hidden from the UI
        and only retained for historial purposes.
    """
    DAYS = "day(s)"
    HOURS = "hour(s)"
    MINUTES = "minute(s)"

    credential = ForeignKeyField(APICredential, backref='schedules')
    is_active = BooleanField(default=True)
    is_paused = BooleanField(default=False)
    market_name = CharField()
    order_side = CharField()
    amount = DecimalField()
    amount_currency = CharField()
    repeat_duration = IntegerField()
    repeat_timescale = CharField()
    created = DateTimeField(default=datetime.datetime.now)
    last_run = DateTimeField(null=True)

    @property
    def next_run(self):
        last_run = self.last_run
        if not last_run:
            last_run = datetime.datetime.now()

        if self.repeat_timescale == DCASchedule.DAYS:
            td = datetime.timedelta(days=self.repeat_duration)
        elif self.repeat_timescale == DCASchedule.HOURS:
            td = datetime.timedelta(hours=self.repeat_duration)
        else:
            td = datetime.timedelta(minutes=self.repeat_duration)

        return last_run + td

    @property
    def is_time_to_run(self):
        if not self.is_active:
            return False

        if not self.last_run:
            return True

        return datetime.datetime.now() > self.next_run

    def undo_last_run(self):
        if self.repeat_timescale == DCASchedule.DAYS:
            td = datetime.timedelta(days=self.repeat_duration)
        elif self.repeat_timescale == DCASchedule.HOURS:
            td = datetime.timedelta(hours=self.repeat_duration)
        else:
            td = datetime.timedelta(minutes=self.repeat_duration)
        self.last_run - td
        self.save()


class Order(BaseModel):
    STATUS__OPEN = 'open'
    STATUS__INSUFFICIENT_FUNDS = 'insufficient funds'
    STATUS__MIN_ORDER_SIZE = 'min order size not met'
    STATUS__CANCELLED = 'cancelled'
    STATUS__REJECTED = 'rejected'
    STATUS__COMPLETE = 'complete'

    schedule = ForeignKeyField(DCASchedule, backref='orders', null=True)
    credential = ForeignKeyField(APICredential, backref='orders')
    order_id = CharField(null=True)     # Null if order attempt fails
    status = CharField(default=STATUS__OPEN)
    market_name = CharField()
    order_side = CharField()
    amount = DecimalField()
    amount_currency = CharField()
    raw_data = JSONField()
    is_live = BooleanField(default=True)
    created = DateTimeField(default=datetime.datetime.now)
    updated = DateTimeField(null=True)



