class HasFocus:
    pass


def Condition(*args, **kwargs):
    return True


Always = IsDone = HasFocus


def has_focus(*args, **kwargs):
    class Foo:
        def __init__(self, *args, **kwargs):
            def func(*args, **kwargs):
                pass

            setattr(func, "__name__", "")
            self.func = func

        def __or__(self, other):
            return True

        __and__ = __or__

    return Foo()


has_selection = (
    has_suggestion
) = vi_insert_mode = vi_mode = has_completions = emacs_insert_mode = True
