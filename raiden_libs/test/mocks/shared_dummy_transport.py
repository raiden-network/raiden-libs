import json
import logging
from typing import Union
from collections import defaultdict

import jsonschema
import gevent

from raiden_libs.messages import Message
from raiden_libs.exceptions import MessageFormatError

log = logging.getLogger(__name__)


class SharedDummyTransport:
    """A shared transport that implements required methods to mock a wire."""
    def __init__(self):
        super().__init__()
        self.is_running = gevent.event.Event()
        self.message_callbacks = defaultdict(list)
        self.received_messages = defaultdict(list)
        self.sent_messages = defaultdict(list)

    def _run(self):
        self.is_running.wait()

    def add_message_callback(self, callback, target_node: str = None):
        self.message_callbacks[target_node].append(callback)

    def run_message_callbacks(self, data, target_node: str = None):
        """Called whenever a message is received"""
        # ignore if message is not a JSON
        try:
            json_msg = json.loads(data)
        except json.decoder.JSONDecodeError as ex:
            log.error('Error when reading JSON: %s', str(ex))
            return

        # ignore message if JSON schema validation fails
        try:
            deserialized_msg = Message.deserialize(json_msg)
        except (
            jsonschema.exceptions.ValidationError,
            MessageFormatError
        ) as ex:
            log.error('Error when deserializing message: %s', str(ex))
            return

        for callback in self.message_callbacks[target_node]:
            callback(deserialized_msg)

    def send_message(  # type: ignore
            self,
            message: Union[str, Message],
            target_node: str = None
    ):
        """Wrapper that serializes Message type to a string, then sends it"""
        assert isinstance(message, (str, Message))
        if isinstance(message, Message):
            message_str = message.serialize_full()
        else:
            message_str = message

        self.transmit_data(message_str, target_node)

    def receive_fake_data(self, data: str, target_node: str = None):
        """ Fakes that `data` was received and calls all callbacks. """
        self.received_messages[target_node].append(data)
        self.run_message_callbacks(data, target_node)

    def transmit_data(  # type: ignore
            self,
            data: str,
            target_node: str = None
    ):
        """Implements `transmit_data` method of the `Transport` class. """
        if target_node is None:
            for key in self.received_messages.keys():
                self.received_messages[key].append(data)
                self.run_message_callbacks(data, key)
        else:
            self.received_messages[target_node].append(data)
            self.run_message_callbacks(data, target_node)
