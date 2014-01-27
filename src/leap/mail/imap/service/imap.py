# -*- coding: utf-8 -*-
# imap.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Imap service initialization
"""
import logging

from twisted.internet.protocol import ServerFactory
from twisted.internet.error import CannotListenError
from twisted.mail import imap4

logger = logging.getLogger(__name__)

from leap.common import events as leap_events
from leap.common.check import leap_assert, leap_assert_type, leap_check
from leap.keymanager import KeyManager
from leap.mail.imap.account import SoledadBackedAccount
from leap.mail.imap.fetch import LeapIncomingMail
from leap.mail.imap.memorystore import MemoryStore
from leap.mail.imap.server import LeapIMAPServer
from leap.soledad.client import Soledad

# The default port in which imap service will run
IMAP_PORT = 1984

# The period between succesive checks of the incoming mail
# queue (in seconds)
INCOMING_CHECK_PERIOD = 60

from leap.common.events.events_pb2 import IMAP_SERVICE_STARTED
from leap.common.events.events_pb2 import IMAP_SERVICE_FAILED_TO_START

######################################################
# Temporary workaround for RecursionLimit when using
# qt4reactor. Do remove when we move to poll or select
# reactor, which do not show those problems. See #4974
import resource
import sys

try:
    sys.setrecursionlimit(10**6)
except Exception:
    print "Error setting recursion limit"
try:
    # Increase max stack size from 8MB to 256MB
    resource.setrlimit(resource.RLIMIT_STACK, (2**28, -1))
except Exception:
    print "Error setting stack size"

######################################################


class IMAPAuthRealm(object):
    """
    Dummy authentication realm. Do not use in production!
    """
    theAccount = None

    def requestAvatar(self, avatarId, mind, *interfaces):
        return imap4.IAccount, self.theAccount, lambda: None


class LeapIMAPFactory(ServerFactory):
    """
    Factory for a IMAP4 server with soledad remote sync and gpg-decryption
    capabilities.
    """

    def __init__(self, uuid, userid, soledad):
        """
        Initializes the server factory.

        :param uuid: user uuid
        :type uuid: str

        :param userid: user id (user@provider.org)
        :type userid: str

        :param soledad: soledad instance
        :type soledad: Soledad
        """
        self._uuid = uuid
        self._userid = userid
        self._soledad = soledad
        self._memstore = MemoryStore()

        theAccount = SoledadBackedAccount(
            uuid, soledad=soledad,
            memstore=self._memstore)
        self.theAccount = theAccount

        # XXX how to pass the store along?

    def buildProtocol(self, addr):
        "Return a protocol suitable for the job."
        imapProtocol = LeapIMAPServer(
            uuid=self._uuid,
            userid=self._userid,
            soledad=self._soledad)
        imapProtocol.theAccount = self.theAccount
        imapProtocol.factory = self
        return imapProtocol


def run_service(*args, **kwargs):
    """
    Main entry point to run the service from the client.

    :returns: the LoopingCall instance that will have to be stoppped
              before shutting down the client, the port as returned by
              the reactor when starts listening, and the factory for
              the protocol.
    """
    from twisted.internet import reactor

    leap_assert(len(args) == 2)
    soledad, keymanager = args
    leap_assert_type(soledad, Soledad)
    leap_assert_type(keymanager, KeyManager)

    port = kwargs.get('port', IMAP_PORT)
    check_period = kwargs.get('check_period', INCOMING_CHECK_PERIOD)
    userid = kwargs.get('userid', None)
    leap_check(userid is not None, "need an user id")
    offline = kwargs.get('offline', False)

    uuid = soledad._get_uuid()
    factory = LeapIMAPFactory(uuid, userid, soledad)

    try:
        tport = reactor.listenTCP(port, factory,
                                  interface="localhost")
        if not offline:
            fetcher = LeapIncomingMail(
                keymanager,
                soledad,
                factory.theAccount,
                check_period,
                userid)
        else:
            fetcher = None
    except CannotListenError:
        logger.error("IMAP Service failed to start: "
                     "cannot listen in port %s" % (port,))
    except Exception as exc:
        logger.error("Error launching IMAP service: %r" % (exc,))
    else:
        # all good.
        # (the caller has still to call fetcher.start_loop)
        logger.debug("IMAP4 Server is RUNNING in port  %s" % (port,))
        leap_events.signal(IMAP_SERVICE_STARTED, str(port))
        return fetcher, tport, factory

    # not ok, signal error.
    leap_events.signal(IMAP_SERVICE_FAILED_TO_START, str(port))
