# Generated by Django 2.2.13 on 2020-06-18 10:44

from django.db import migrations
from django.db import connection
from drf_actions.app_settings import ACTION_QUEUE, ACTION_ROUTE


def init_schema():
    query = "CREATE SCHEMA IF NOT EXISTS rabbitmq;"

    with connection.cursor() as cursor:
        cursor.execute(query)


def init_send_message():
    query = """create or replace function rabbitmq.send_message(channel text, routing_key text, message text)
            returns void as $$ select	pg_notify(channel, routing_key || '|' || message); $$ stable language sql;"""

    with connection.cursor() as cursor:
        cursor.execute(query)


def init_on_row_change():
    query = f"""create or replace function rabbitmq.on_row_change() returns trigger as $$
      declare
        routing_key text;
        row record;
      begin
        routing_key := '{ACTION_ROUTE}';
        if (TG_OP = 'DELETE') then
            row := old;
        elsif (TG_OP = 'UPDATE') then
            row := new;
        elsif (TG_OP = 'INSERT') then
            row := new;
        end if;
        -- change 'events' to the desired channel/exchange name
        perform rabbitmq.send_message('{ACTION_QUEUE}', routing_key, row_to_json(row)::text);
        return null;
      end;
    $$ stable language plpgsql;"""

    with connection.cursor() as cursor:
        cursor.execute(query)


def init_trigger():
    drop_query = (
        f"DROP TRIGGER IF EXISTS send_change_event ON drf_actions_eventjournal;"
    )
    query = """create trigger send_change_event after insert or update or delete on drf_actions_eventjournal 
    for each row execute procedure rabbitmq.on_row_change();"""
    with connection.cursor() as cursor:
        cursor.execute(drop_query)
        cursor.execute(query)


def init_listen_events(apps, schema_editor):
    init_schema()
    init_send_message()
    init_on_row_change()
    init_trigger()


class Migration(migrations.Migration):
    dependencies = [
        ("drf_actions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(init_listen_events),
    ]
