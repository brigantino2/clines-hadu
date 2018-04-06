import types
import weakref

from PyQt4 import QtCore, QtGui


# The following code has been borrowed here:
# http://stackoverflow.com/questions/24689800/async-like-pattern-in-pyqt-or-cleaner-background-call-pattern
# It provides a child->parent thread-communication mechanism.


class ref(object):

    """A weak method implementation
    """

    def __init__(self, method):
        try:
            if method.im_self is not None:
                # bound method
                self._obj = weakref.ref(method.im_self)
            else:
                # unbound method
                self._obj = None
            self._func = method.im_func
            self._class = method.im_class
        except AttributeError:
            # not a method
            self._obj = None
            self._func = method
            self._class = None

    def __call__(self):
        """Return a new bound-method like the original, or the
        original function if refers just to a function or unbound
        method.
        Returns None if the original object doesn't exist
        """
        if self.is_dead():
            return None
        if self._obj is not None:
            # we have an instance: return a bound method
            return types.MethodType(self._func, self._obj(), self._class)
        else:
            # we don't have an instance: return just the function
            return self._func

    def is_dead(self):
        """
        Returns True if the referenced callable was a bound method and
        the instance no longer exists. Otherwise, return False.
        """
        return self._obj is not None and self._obj() is None

    def __eq__(self, other):
        try:
            return type(self) is type(other) and self() == other()
        except:
            return False

    def __ne__(self, other):
        return not self == other


class proxy(ref):

    """
    Exactly like ref, but calling it will cause the referent method to
    be called with the same arguments. If the referent's object no longer lives,
    ReferenceError is raised.

    If quiet is True, then a ReferenceError is not raise and the callback
    silently fails if it is no longer valid.
    """

    def __init__(self, method, quiet=False):
        super(proxy, self).__init__(method)
        self._quiet = quiet

    def __call__(self, *args, **kwargs):
        func = ref.__call__(self)
        if func is None:
            if self._quiet:
                return
            else:
                raise ReferenceError('object is dead')
        else:
            return func(*args, **kwargs)

    def __eq__(self, other):
        try:
            func1 = ref.__call__(self)
            func2 = ref.__call__(other)
            return type(self) == type(other) and func1 == func2
        except:
            return False


class CallbackEvent(QtCore.QEvent):

    """A custom QEvent that contains a callback reference.

    Also provides class methods for conveniently executing
    arbitrary callback, to be dispatched to the event loop.
    """
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, func, *args, **kwargs):
        super(CallbackEvent, self).__init__(self.EVENT_TYPE)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def callback(self):
        """
        Convenience method to run the callable.

        Equivalent to:
            self.func(*self.args, **self.kwargs)
        """
        self.func(*self.args, **self.kwargs)

    @classmethod
    def post_to(cls, receiver, func, *args, **kwargs):
        """
        Post a callable to be delivered to a specific
        receiver as a CallbackEvent.

        It is the responsibility of this receiver to
        handle the event and choose to call the callback.
        """
        # We can create a weak proxy reference to the
        # callback so that if the object associated with
        # a bound method is deleted, it won't call a dead method
        if not isinstance(func, proxy):
            reference = proxy(func, quiet=True)
        else:
            reference = func
        event = cls(reference, *args, **kwargs)

        # post the event to the given receiver
        QtGui.QApplication.postEvent(receiver, event)
