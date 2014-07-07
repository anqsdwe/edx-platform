# pylint: disable=C0111

from lettuce import step
from lettuce import world
from lettuce import before
from pymongo import MongoClient
from nose.tools import assert_equals
from nose.tools import assert_in

REQUIRED_EVENT_FIELDS = [
    'agent',
    'event',
    'event_source',
    'event_type',
    'host',
    'ip',
    'page',
    'time',
    'username'
]


@before.all
def connect_to_mongodb():
    world.mongo_client = MongoClient()
    world.event_collection = world.mongo_client['track']['events']


@before.each_scenario
def reset_captured_events(_scenario):
    world.event_collection.drop()


@before.outline
def reset_between_outline_scenarios(_scenario, order, outline, reasons_to_fail):
    world.event_collection.drop()



@step('([aA]n?|\d+) "(.*)" (server|browser) events? is emitted$')
def n_events_are_emitted(_step, count, event_type, event_source):

    # Ensure all events are written out to mongo before querying.
    world.mongo_client.fsync()

    criteria = {
        'event_type': event_type,
        'event_source': event_source,
        'agent': {
            '$ne': 'python/splinter'
        }
    }

    cursor = world.event_collection.find(criteria)
    number_events = 1
    try:
        number_events = int(count)
    except:
        pass
    assert_equals(cursor.count(), number_events)

    event = cursor.next()

    expected_field_values = {
        "username": world.scenario_dict['USER'].username,
        "event_type": event_type,
    }
    for key, value in expected_field_values.iteritems():
        assert_equals(event[key], value)

    for field in REQUIRED_EVENT_FIELDS:
        assert_in(field, event)
