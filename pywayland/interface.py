# Copyright 2015 Sean Vig
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from weakref import WeakKeyDictionary

from typing import List  # noqa: F401

from pywayland import ffi

from .dispatcher import Dispatcher
from .message import Message

weakkeydict = WeakKeyDictionary()  # type: WeakKeyDictionary


class classproperty:
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class InterfaceMeta(type):
    """Metaclass for Interfaces

    Initializes empty lists for events and requests for the given class.
    """
    def __init__(self, name, bases, dct):
        self.events = []
        self.requests = []

        # Initialize the interface cdata
        self._ptr = ffi.new("struct wl_interface *")


class Interface(metaclass=InterfaceMeta):
    """Wrapper class for wl_wayland structs

    Base class for interfaces that are defined by the wayland.xml class and
    generated by the scanner.  Sub-classes should use the
    :class:`InterfaceMeta` metaclass, which will define subclass.events and
    subclass.requests, the lists of the methods on this interface.  These class
    variables are populated by the :func:`Interface.event` and
    :func:`Interface.request` decorators.
    """

    _ptr = None
    name = None  # type: str
    version = None  # type: int

    @classproperty
    def proxy_class(interface):
        """Return a proxy class for the given interface

        :returns: :class:`~pywayland.client.proxy.Proxy` class for the given
                  interface
        """
        from pywayland.client.proxy import Proxy

        # Use the name of the interface to construct the class name
        class_name = '{}Proxy'.format(interface.__name__)
        # Extract the requests
        # TODO: add the enums to the class as well
        dct = {msg.name: msg.py_func for msg in interface.requests}
        # Construct a dispatcher
        dispacter_name = '{}Dispatcher'.format(interface.__name__)
        dispacter_class = type(dispacter_name, (Dispatcher,), {})
        # Add the interface and dispacter as a class attribute
        dct['_interface'] = interface
        dct['dispatcher'] = dispacter_class(interface.events)

        # Return the new class
        return type(class_name, (Proxy,), dct)

    @classproperty
    def resource_class(interface):
        """Return a resource class for the given interface

        :returns: :class:`~pywayland.server.resource.Resource` class for the
                  given interface
        """
        from pywayland.server.resource import Resource

        # Use the name of the interface to construct the class name
        class_name = '{}Resource'.format(interface.__name__)
        # Extract the events
        dct = {msg.name: msg.py_func for msg in interface.events}
        # Construct a dispacter
        dispacter_name = '{}Dispatcher'.format(interface.__name__)
        dispacter_class = type(dispacter_name, (Dispatcher,), {})
        # Add the interface and dispacter as a class attribute
        dct['_interface'] = interface
        dct['dispatcher'] = dispacter_class(interface.requests, destructor=True)

        # Return the new class
        return type(class_name, (Resource,), dct)

    @classproperty
    def global_class(interface):
        """Return a global object for the given interface

        :returns: :class:`~pywayland.server.globals.Global` class for the given
                  interface
        """
        from pywayland.server.globals import Global

        # Use the name of the interface to construct the class name
        class_name = '{}Global'.format(interface.__name__)

        # Return the new class with the interface added as a class attribute
        return type(class_name, (Global,), {'_interface': interface})

    @classmethod
    def event(cls, signature, types):
        """Decorator for interface events

        Adds the decorated method to the list of events of the interface
        (server-side method).

        :param signature: Encodes the types of the arguments to the decorated
                          function.
        :type signature: `string`
        :param types: List of the types of any objects included in the argument
                      list, None if otherwise.
        :type types: `list`
        """
        def wrapper(func):
            cls.events.append(Message(func, signature, types))
            return func
        return wrapper

    @classmethod
    def request(cls, signature, types):
        """Decorator for interface requests

        Adds the decorated method to the list of requests of the interface
        (client-side method).

        :param signature: Encodes the types of the arguments to the decorated
                          function.
        :type signature: `string`
        :param types: List of the types of any objects included in the argument
                      list, None if otherwise.
        :type types: list
        """
        def wrapper(func):
            cls.requests.append(Message(func, signature, types))
            return func
        return wrapper

    @classmethod
    def _gen_c(cls):
        """Creates the wl_interface C struct

        Generates the CFFI cdata for the wl_interface struct given by the
        interface.
        """
        cls._ptr.name = name = ffi.new('char[]', cls.name.encode())
        cls._ptr.version = cls.version

        # Determine the number of methods to assign and assign them
        cls._ptr.method_count = len(cls.requests)
        cls._ptr.methods = methods_ptr = ffi.new("struct wl_message[]", len(cls.requests))
        # Iterate over the methods
        for i, message in enumerate(cls.requests):
            # First, generate the wl_message cdata
            msg_buf = ffi.buffer(message._ptr)
            methods_buf = ffi.buffer(methods_ptr + i)
            # Copy the contents of the cdata into the allocated cdata
            methods_buf[:] = msg_buf

        cls._ptr.event_count = len(cls.events)
        cls._ptr.events = events_ptr = ffi.new("struct wl_message[]", len(cls.events))
        # Iterate over the methods
        for i, message in enumerate(cls.events):
            # First, generate the wl_message cdata
            msg_buf = ffi.buffer(message._ptr)
            events_buf = ffi.buffer(events_ptr + i)
            # Copy the contents of the cdata into the allocated cdata
            events_buf[:] = msg_buf

        weakkeydict[cls._ptr] = (name, methods_ptr, events_ptr)
