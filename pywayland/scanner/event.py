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

from .argument import Argument
from .description import Description
from .element import Element, Attribute, Child
from .method import Method


class Event(Method, Element):
    """Scanner for event objects (server-side method)

    Required attributes: `name`

    Optional attributes: `since`

    Child elements: `description` and `arg``
    """
    method_type = 'event'

    attributes = [
        Attribute('name', True),
        Attribute('since', False)
    ]

    children = [
        Child('description', Description, False, False),
        Child('arg', Argument, False, True)
    ]

    @property
    def method_args(self):
        """Generator of the arguments to the method

        All arguments to be sent to `._post_event` must be passed in
        """
        for arg in self.arg:
            yield arg.name

    @property
    def interface_types(self):
        """Generator of the types (for the wl_interface)"""
        for arg in self.arg:
            if arg.interface:
                yield arg.interface_class
            else:
                yield 'None'

    def output_doc_params(self, printer):
        """Aguments documented as parameters

        All arguments are event parameters.
        """
        for arg in self.arg:
            arg.output_doc_param(printer)

    def output_doc_ret(self, printer):
        """Aguments documented as return values

        Nothing is returned from event calls.
        """
        return

    def output_body(self, printer):
        """Output the body of the event to the printer"""
        args = ', '.join([str(self.opcode)] + list(self.method_args))
        printer('self._post_event({})'.format(args))
